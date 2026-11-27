"""Opt-in loopback Streamable HTTP MCP (legacy lifecycle, JSON responses only)."""
import argparse, hmac, json, os, re, secrets, threading, time, ssl
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from server import Store, BoundedHTTPServer, SLUG
from mcp_server import Session, MemoryTools, MAX_LINE, dump

HTTP_VERSIONS=('2025-11-25','2025-06-18','2025-03-26')
MAX_SESSIONS=32
SESSION_IDLE=900

class Sessions:
    def __init__(self,tools,clock=time.monotonic):
        self.tools=tools;self.clock=clock;self.items={};self.lock=threading.Lock()
    def prune(self):
        now=self.clock()
        for key in list(self.items):
            if now-self.items[key][2]>=SESSION_IDLE: del self.items[key]
    def create(self,msg):
        with self.lock:
            self.prune()
            if len(self.items)>=MAX_SESSIONS: return 503,None,None
            session=Session(self.tools)
            version=msg.get('params',{}).get('protocolVersion') if isinstance(msg.get('params'),dict) else None
            if version not in HTTP_VERSIONS: return 400,None,None
            reply=session.handle(msg)
            if not reply or 'result' not in reply: return 400,None,reply
            key=secrets.token_urlsafe(32)
            self.items[key]=(session,version,self.clock())
            return 200,key,reply
    def dispatch(self,key,version,msg=None,delete=False):
        with self.lock:
            self.prune()
            if key not in self.items: return 404,None
            session,negotiated,_=self.items[key]
            if version is not None and version!=negotiated: return 400,None
            if delete:
                del self.items[key];return 204,None
            self.items[key]=(session,negotiated,self.clock())
            if msg is None: return 405,None
            if msg.get('method')=='initialize': return 400,None
            if 'id' not in msg and msg.get('method')=='notifications/initialized' and session.phase!='initializing': return 400,None
            reply=session.handle(msg)
            return (202,None) if reply is None else (200,reply)

class Handler(BaseHTTPRequestHandler):
    def setup(self):
        self.request.settimeout(10)
        if isinstance(self.request,ssl.SSLSocket): self.request.do_handshake()
        super().setup();self.connection.settimeout(10)
    def log_message(self,*args): pass
    def respond(self,status,payload=None,session_id=None):
        raw=b'' if payload is None else dump(payload).encode('utf-8')
        self.send_response(status)
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Content-Length',str(len(raw)))
        self.send_header('Connection','close')
        if raw: self.send_header('Content-Type','application/json')
        if status==401: self.send_header('WWW-Authenticate','Bearer')
        if status==405: self.send_header('Allow','POST, DELETE')
        if session_id: self.send_header('Mcp-Session-Id',session_id)
        self.end_headers();self.close_connection=True
        if raw: self.wfile.write(raw)
    def guard(self):
        if self.path!='/mcp': self.respond(404);return False
        # Native clients only. Reject all browser origins, including null.
        if self.headers.get_all('Origin') or self.headers.get_all('Host')!=[self.headers.get('Host')] or (self.headers.get('Host') or '').lower() not in self.server.allowed_hosts:
            self.respond(403);return False
        values=self.headers.get_all('Authorization',[])
        if len(values)!=1 or not hmac.compare_digest(values[0].encode(),('Bearer '+self.server.agent_token).encode()):
            self.respond(401);return False
        return True
    def session_headers(self):
        keys=self.headers.get_all('Mcp-Session-Id',[])
        versions=self.headers.get_all('MCP-Protocol-Version',[])
        if len(keys)>1 or len(versions)>1 or (keys and not re.fullmatch(r'[A-Za-z0-9_-]{43}',keys[0])) or (versions and versions[0] not in HTTP_VERSIONS):
            raise ValueError()
        return keys[0] if keys else None,versions[0] if versions else None
    def do_POST(self):
        if not self.guard(): return
        try:
            key,version=self.session_headers()
            accept={x.split(';')[0].strip().lower() for x in self.headers.get('Accept','').split(',')}
            if not {'application/json','text/event-stream'}<=accept:
                return self.respond(406)
            if self.headers.get_content_type()!='application/json': return self.respond(415)
            lengths=self.headers.get_all('Content-Length',[])
            if self.headers.get('Transfer-Encoding') or len(lengths)!=1 or not re.fullmatch(r'[0-9]{1,7}',lengths[0]): raise ValueError()
            n=int(lengths[0])
            if not 0<n<=MAX_LINE: return self.respond(413)
            raw=self.rfile.read(n)
            if len(raw)!=n: raise ValueError()
            msg=json.loads(raw.decode('utf-8'))
            if not isinstance(msg,dict) or msg.get('jsonrpc')!='2.0' or not isinstance(msg.get('method'),str): raise ValueError()
            if 'id' in msg and type(msg['id']) not in (int,str): raise ValueError()
            if not key:
                if msg['method']!='initialize' or 'id' not in msg: return self.respond(400)
                if version is not None and (not isinstance(msg.get('params'),dict) or version!=msg['params'].get('protocolVersion')): return self.respond(400)
                status,created,reply=self.server.sessions.create(msg)
                return self.respond(status,reply,created)
            status,reply=self.server.sessions.dispatch(key,version,msg)
            return self.respond(status,reply)
        except (ValueError,UnicodeError,RecursionError): return self.respond(400)
        except TimeoutError: return self.respond(408)
    def session_method(self,delete=False):
        if not self.guard(): return
        try: key,version=self.session_headers()
        except ValueError: return self.respond(400)
        if not key: return self.respond(400)
        status,_=self.server.sessions.dispatch(key,version,delete=delete)
        return self.respond(status)
    def do_GET(self): self.session_method()
    def do_DELETE(self): self.session_method(True)

def valid_authority(value):
    if not isinstance(value,str) or len(value)>259: return False
    match=re.fullmatch(r'([A-Za-z0-9](?:[A-Za-z0-9.-]{0,251}[A-Za-z0-9])?)(?::([0-9]{1,5}))?',value)
    return bool(match and '..' not in match[1] and (match[2] is None or 1<=int(match[2])<=65535))

class TLSHTTPServer(BoundedHTTPServer):
    def __init__(self,address,handler,context):
        self.context=context
        super().__init__(address,handler)
    def get_request(self):
        sock,addr=super().get_request()
        try:
            # Handshake occurs in a bounded request worker, not the accept loop.
            return self.context.wrap_socket(sock,server_side=True,do_handshake_on_connect=False),addr
        except BaseException:
            sock.close()
            raise
    def handle_error(self,request,address):
        # TLS disconnects and malformed clients do not expose credentials or stack traces.
        pass

def make_http_server(store,port,token,projects,allow_write=False,*,tls=None,authority=None):
    if not isinstance(token,str) or not re.fullmatch(r'[A-Za-z0-9_-]{32,256}',token):
        raise ValueError('Set DEVMEMORY_AGENT_TOKEN to a separate random URL-safe secret (32+ characters)')
    if not projects or any(not SLUG.fullmatch(p) for p in projects):
        raise ValueError('Explicit project allowlist required')
    if (tls is None)!=(authority is None): raise ValueError('TLS and explicit authority must be configured together')
    if tls is not None and not valid_authority(authority): raise ValueError('Invalid MCP host authority')
    server=TLSHTTPServer(('0.0.0.0',port),Handler,tls) if tls is not None else BoundedHTTPServer(('127.0.0.1',port),Handler)
    server.agent_token=token
    server.allowed_hosts={authority.lower()} if tls is not None else {'127.0.0.1:'+str(server.server_port),'localhost:'+str(server.server_port)}
    server.sessions=Sessions(MemoryTools(store,projects,allow_write))
    return server

def main():
    parser=argparse.ArgumentParser(description='Loopback-only MCP HTTP; use a trusted SSH tunnel for remote clients')
    parser.add_argument('--data',required=True)
    parser.add_argument('--port',type=int,default=8100)
    parser.add_argument('--project',action='append',required=True)
    parser.add_argument('--allow-write',action='store_true')
    a=parser.parse_args()
    path=Path(a.data)/'memory.sqlite3'
    if not path.is_file(): parser.error('Existing memory.sqlite3 required')
    token=os.getenv('DEVMEMORY_AGENT_TOKEN','')
    if token and token in (os.getenv('DEVMEMORY_TOKEN'),os.getenv('DEVMEMORY_GITHUB_TOKEN')):
        parser.error('Use a distinct agent token')
    try: server=make_http_server(Store(path),a.port,token,a.project,a.allow_write)
    except ValueError as e: parser.error(str(e))
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()
if __name__=='__main__': main()
