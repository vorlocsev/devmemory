import json, tempfile, threading, unittest, sys, http.client
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from server import Store
from mcp_http import make_http_server, Sessions, MAX_SESSIONS, SESSION_IDLE
from mcp_server import MemoryTools

TOKEN='agent_test_'+'A'*40
VERSION='2025-11-25'
INIT={'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':VERSION,'capabilities':{},'clientInfo':{'name':'fixture','version':'1'}}}
def call(name,args): return {'jsonrpc':'2.0','id':2,'method':'tools/call','params':{'name':name,'arguments':args}}

class HTTPMCPTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.store=Store(Path(self.tmp.name)/'memory.sqlite3')
        for p in ('alpha','beta'): self.store.add_project({'slug':p,'name':p})
        self.server=make_http_server(self.store,0,TOKEN,['alpha'])
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.addCleanup(self.stop)
    def stop(self):
        self.server.shutdown();self.server.server_close();self.thread.join()
    def req(self,msg=None,key=None,method='POST',extra=None,auth=True):
        headers={'Accept':'application/json, text/event-stream','Content-Type':'application/json'}
        if auth: headers['Authorization']='Bearer '+TOKEN
        if key: headers.update({'Mcp-Session-Id':key,'MCP-Protocol-Version':VERSION})
        headers.update(extra or {})
        c=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=3)
        try:
            c.request(method,'/mcp',body=json.dumps(msg) if msg is not None else None,headers=headers)
            r=c.getresponse();raw=r.read()
            return r.status,r.getheader('Mcp-Session-Id'),json.loads(raw) if raw else None
        finally:c.close()
    def start(self):
        status,key,reply=self.req(INIT)
        self.assertEqual(status,200);self.assertEqual(reply['result']['protocolVersion'],VERSION)
        self.assertEqual(self.req({'jsonrpc':'2.0','method':'notifications/initialized'},key)[0],202)
        return key
    def test_auth_and_origin_host(self):
        self.assertEqual(self.req(INIT,auth=False)[0],401)
        self.assertEqual(self.req(INIT,extra={'Origin':'https://evil.example'})[0],403)
        self.assertEqual(self.req(INIT,extra={'Host':'evil.example'})[0],403)
        with self.assertRaises(ValueError): make_http_server(self.store,0,TOKEN,[])
        with self.assertRaises(ValueError): make_http_server(self.store,0,'short',['alpha'])
    def test_session_lifecycle_and_scope(self):
        key=self.start()
        status,_,r=self.req(call('list_projects',{}),key)
        self.assertEqual(status,200)
        self.assertEqual([x['slug'] for x in json.loads(r['result']['content'][0]['text'])['rows']],['alpha'])
        self.assertTrue(self.req(call('get_context',{'project':'beta'}),key)[2]['result']['isError'])
        self.assertTrue(self.req(call('add_memory',{'project':'alpha'}),key)[2]['result']['isError'])
        self.assertEqual(self.req(call('list_projects',{}),key,auth=False)[0],401)
        self.assertEqual(self.req(call('list_projects',{}),key,extra={'MCP-Protocol-Version':'2025-06-18'})[0],400)
        self.assertEqual(self.req(key=key,method='GET')[0],405)
        self.assertEqual(self.req(key=key,method='DELETE')[0],204)
        self.assertEqual(self.req(call('list_projects',{}),key)[0],404)
    def test_headers_and_invalid_json_shape(self):
        self.assertEqual(self.req(INIT,extra={'Accept':'application/json'})[0],406)
        self.assertEqual(self.req(INIT,extra={'Content-Type':'text/plain'})[0],415)
        self.assertEqual(self.req([INIT])[0],400)
        self.assertEqual(self.req(call('list_projects',{}))[0],400)
        self.assertEqual(self.req(INIT,extra={'MCP-Protocol-Version':'2026-07-28'})[0],400)
    def test_session_limit_and_expiry(self):
        now=[100]
        sessions=Sessions(MemoryTools(self.store,['alpha']),lambda:now[0])
        for i in range(MAX_SESSIONS): self.assertEqual(sessions.create(INIT)[0],200)
        self.assertEqual(sessions.create(INIT)[0],503)
        now[0]+=SESSION_IDLE
        self.assertEqual(sessions.create(INIT)[0],200)
        self.assertEqual(len(sessions.items),1)
