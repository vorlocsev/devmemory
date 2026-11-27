import tempfile, unittest, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from server import Store
from mcp_server import MemoryTools, dump, MAX_RESULT
class MCPBoundsTests(unittest.TestCase):
    def test_unicode_context_byte_budget(self):
        with tempfile.TemporaryDirectory() as d:
            store=Store(Path(d)/'memory.sqlite3')
            store.add_project({'slug':'alpha','name':'Alpha'})
            store.add(dict(project='alpha',kind='note',status='reported',title='Unicode',body='😀'*50000))
            result=MemoryTools(store,['alpha']).call('get_context',{'project':'alpha'})
            self.assertLessEqual(len(dump(result)),MAX_RESULT)
            self.assertIn('[Context limited by MCP response byte budget.]',result['context'])
