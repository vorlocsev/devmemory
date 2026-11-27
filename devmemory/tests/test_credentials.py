import tempfile, unittest, sys, threading, urllib.request, urllib.error, json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from server import make_server

class CredentialBoundaryTests(unittest.TestCase):
    def test_auth_status_and_backup_never_return_token(self):
        secret='github_pat_'+'B'*40
        with tempfile.TemporaryDirectory() as d:
            s=make_server('127.0.0.1',0,d,'standalone','x'*40,secret)
            t=threading.Thread(target=s.serve_forever,daemon=True);t.start()
            base='http://127.0.0.1:'+str(s.server_port)
            try:
                for path in ('/api/github/auth','/api/backup'):
                    with self.assertRaises(urllib.error.HTTPError) as err: urllib.request.urlopen(base+path,timeout=3)
                    self.assertEqual(err.exception.code,403)
                    req=urllib.request.Request(base+path,headers={'Authorization':'Bearer '+'x'*40})
                    with urllib.request.urlopen(req,timeout=3) as r: raw=r.read()
                    self.assertNotIn(secret.encode(),raw)
                    if path.endswith('/auth'): self.assertEqual(json.loads(raw),{'configured':True})
                self.assertNotIn(secret.encode(),(Path(d)/'memory.sqlite3').read_bytes())
            finally: s.shutdown();s.server_close();t.join()
