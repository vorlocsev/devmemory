"""HA app-managed TLS MCP. Disabled by default; failures leave Ingress available."""
import json, ssl, threading
from pathlib import Path
from mcp_http import make_http_server, valid_authority

DISABLED={'state':'disabled','projects':[],'allow_write':False}
ERROR={'state':'configuration_error','projects':[],'allow_write':False}
class ManagedMCP:
    def __init__(self,server):
        self.server=server
        self.thread=threading.Thread(target=server.serve_forever,daemon=True,name='mcp-https')
        self.thread.start()
    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

def start_managed(store,data,github_token='',config_dir='/config',port=8100):
    path=Path(data)/'options.json'
    if not path.exists(): return None,dict(DISABLED)
    server=None
    try:
        with path.open('rb') as file: raw=file.read(65537)
        if len(raw)>65536: raise ValueError()
        options=json.loads(raw)
        if not isinstance(options,dict): raise ValueError()
        enabled=options.get('mcp_enabled',False)
        if enabled is False: return None,dict(DISABLED)
        if enabled is not True: raise ValueError()
        token=options.get('mcp_token','')
        authority=options.get('mcp_host','')
        projects=options.get('mcp_projects','')
        allow_write=options.get('mcp_allow_write',False)
        if not isinstance(projects,str) or len(projects)>4096 or type(allow_write) is not bool: raise ValueError()
        projects=[p.strip() for p in projects.split(',')]
        if len(projects)>32 or len(set(projects))!=len(projects) or not valid_authority(authority): raise ValueError()
        if token==github_token: raise ValueError()
        context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.minimum_version=ssl.TLSVersion.TLSv1_2
        context.load_cert_chain(str(Path(config_dir)/'mcp.crt'),str(Path(config_dir)/'mcp.key'))
        server=make_http_server(store,port,token,projects,allow_write,tls=context,authority=authority)
        return ManagedMCP(server),{'state':'enabled','projects':projects,'allow_write':allow_write,'authority':authority,'tls':True}
    except (OSError,ValueError,TypeError,RecursionError):
        if server: server.server_close()
        return None,dict(ERROR)
