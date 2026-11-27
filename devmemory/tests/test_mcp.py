import json, tempfile, subprocess, sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from server import Store
from mcp_server import MemoryTools, Session, ToolError, MAX_LINE
import io
from mcp_server import serve

class MCPTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.store=Store(Path(self.tmp.name)/'memory.sqlite3')
        for p in ('alpha','beta'): self.store.add_project({'slug':p,'name':p})
        self.store.add(dict(project='alpha',kind='blocker',status='reported',title='Проверка ядра',body='Fixture'))
        self.store.add(dict(project='beta',kind='decision',status='reported',title='Secret other project',body='Fixture'))
    def test_scope_and_read_only(self):
        tools=MemoryTools(self.store,['alpha'])
        self.assertNotIn('add_memory',tools.tools)
        self.assertEqual([x['slug'] for x in tools.call('list_projects',{})['rows']],['alpha'])
        for name in ('get_context','get_blockers','get_decisions','get_ci_evidence','search_memory'):
            with self.assertRaises(ToolError): tools.call(name,{'project':'beta'})
        self.assertEqual(len(tools.call('search_memory',{'project':'alpha','query':'провер'})['rows']),1)
        self.assertEqual(len(tools.call('get_blockers',{'project':'alpha'})['rows']),1)
        self.assertEqual(tools.call('get_decisions',{'project':'alpha'})['rows'],[])
    def test_append_never_verified(self):
        tools=MemoryTools(self.store,['alpha'],True)
        d=dict(project='alpha',kind='evidence',title='CI',body='Claim')
        with self.assertRaises(ToolError): tools.call('add_memory',dict(d,status='verified'))
        tools.call('add_memory',d)
        self.assertEqual(self.store.entries('alpha','Claim')[0]['status'],'reported')
    def test_bounds_and_paging(self):
        for i in range(3): self.store.add(dict(project='alpha',kind='note',status='reported',title='Large',body='😀'*50000))
        tools=MemoryTools(self.store)
        r=tools.call('search_memory',{'project':'alpha','limit':2})
        self.assertEqual(r['next_offset'],2)
        self.assertTrue(r['rows'][0]['body_truncated'])
        with self.assertRaises(ToolError): tools.call('search_memory',{'project':'alpha','limit':True})
        out=io.BytesIO()
        serve(Session(tools),io.BytesIO(b'x'*(MAX_LINE+1)+b'\n'),out)
        self.assertEqual(out.getvalue(),b'')
    def test_wire_subprocess(self):
        messages=[
            {'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-11-25','capabilities':{},'clientInfo':{'name':'fixture','version':'1'}}},
            {'jsonrpc':'2.0','method':'notifications/initialized'},
            {'jsonrpc':'2.0','id':2,'method':'tools/list'},
            {'jsonrpc':'2.0','id':3,'method':'tools/call','params':{'name':'search_memory','arguments':{'project':'alpha','query':'провер'}}},
            {'jsonrpc':'2.0','id':4,'method':'tools/call','params':{'name':'get_context','arguments':{'project':'beta'}}},
            {'jsonrpc':'2.0','id':5,'method':'ping'},
        ]
        script=Path(__file__).resolve().parents[1]/'mcp_server.py'
        p=subprocess.run([sys.executable,str(script),'--data',self.tmp.name,'--project','alpha'],input='\n'.join(map(json.dumps,messages))+'\n',text=True,capture_output=True,timeout=15,check=True)
        self.assertEqual(p.stderr,'')
        replies=[json.loads(line) for line in p.stdout.splitlines()]
        self.assertEqual([r['id'] for r in replies],[1,2,3,4,5])
        self.assertEqual(replies[0]['result']['protocolVersion'],'2025-11-25')
        self.assertEqual(len(replies[1]['result']['tools']),6)
        self.assertFalse(replies[2]['result']['isError'])
        self.assertEqual(len(json.loads(replies[2]['result']['content'][0]['text'])['rows']),1)
        self.assertTrue(replies[3]['result']['isError'])
        self.assertEqual(replies[4]['result'],{})
