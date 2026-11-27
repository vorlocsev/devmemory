import tempfile, unittest, sys, json, ssl, http.client, subprocess, shutil
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from server import Store
from mcp_managed import start_managed

TOKEN='agent_test_'+'C'*40
class ManagedTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.store=Store(self.root/'memory.sqlite3')
        self.store.add_project({'slug':'alpha','name':'Alpha'})
        self.options={'mcp_enabled':True,'mcp_token':TOKEN,'mcp_host':'localhost:8100','mcp_projects':'alpha','mcp_allow_write':False}
    def start(self,options,github_token=''):
        (self.root/'options.json').write_text(json.dumps(options))
        return start_managed(self.store,self.root,github_token,self.root,0)
    def test_disabled_invalid_and_missing_cert(self):
        self.assertEqual(self.start({'mcp_enabled':False})[1]['state'],'disabled')
        for options in (self.options,dict(self.options,mcp_projects=''),dict(self.options,mcp_enabled='true')):
            managed,status=self.start(options)
            self.assertIsNone(managed);self.assertEqual(status['state'],'configuration_error')
            self.assertNotIn(TOKEN,json.dumps(status))
    @unittest.skipUnless(shutil.which('openssl'),'openssl required for TLS fixture')
    def test_real_https_listener(self):
        subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-days','1','-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost','-keyout',str(self.root/'mcp.key'),'-out',str(self.root/'mcp.crt')],check=True,capture_output=True,timeout=20)
        managed,status=self.start(self.options)
        self.assertIsNotNone(managed);self.addCleanup(managed.close)
        self.assertEqual(status['state'],'enabled');self.assertNotIn(TOKEN,json.dumps(status))
        ctx=ssl.create_default_context(cafile=str(self.root/'mcp.crt'))
        port=managed.server.server_port
        init={'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-11-25','capabilities':{},'clientInfo':{'name':'fixture','version':'1'}}}
        def req(auth,host='localhost:8100'):
            conn=http.client.HTTPSConnection('localhost',port,context=ctx,timeout=4)
            headers={'Host':host,'Accept':'application/json, text/event-stream','Content-Type':'application/json'}
            if auth:headers['Authorization']='Bearer '+TOKEN
            try:
                conn.request('POST','/mcp',json.dumps(init),headers)
                r=conn.getresponse();r.read();return r.status
            finally:conn.close()
        self.assertEqual(req(False),401);self.assertEqual(req(True,'wrong:8100'),403);self.assertEqual(req(True),200)
        plain=http.client.HTTPConnection('localhost',port,timeout=3)
        try:
            with self.assertRaises((OSError,http.client.HTTPException)):
                plain.request('POST','/mcp',json.dumps(init));plain.getresponse()
        finally:plain.close()
        self.assertIsNone(self.start(self.options,TOKEN)[0])
