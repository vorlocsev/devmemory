import tempfile, unittest, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from server import Store
from github_sync import fetch_snapshot, normalize_repo, GitHubError

A='a'*40
B='b'*40
def fixture(path,conclusion='success'):
    if '/commits?' in path: return [{'sha':A,'commit':{'message':'fixture'}}]
    if '/pulls?' in path: return [{'number':7,'title':'PR fixture','state':'open','head':{'sha':B,'repo':{'full_name':'fork/demo'}},'base':{'ref':'main'}}]
    if '/actions/runs?' in path: return {'workflow_runs':[{'id':123,'run_attempt':1,'head_sha':A,'name':'CI','status':'completed','conclusion':conclusion,'event':'pull_request'}]}
    raise AssertionError(path)

class GitHubTests(unittest.TestCase):
    def test_validate_repo(self):
        for bad in ['https://github.com/a/b','a/..','a/b?x=1','a/b/c','a@b/c']:
            with self.assertRaises(ValueError): normalize_repo(bad)
        self.assertEqual(normalize_repo('Owner/Repo'),'owner/repo')
    def test_snapshot_exact_sha(self):
        records=fetch_snapshot('owner/repo',fixture)
        self.assertEqual([x['sha'] for x in records],[A,B,A])
        self.assertIn('fork/demo',records[1]['body'])
        self.assertIn('checkout SHA and hardware acceptance not verified',records[2]['body'])
        self.assertIn('Conclusion: success',records[2]['body'])
    def test_bad_response(self):
        with self.assertRaises(GitHubError): fetch_snapshot('owner/repo',lambda _: {})
    def test_dedup_and_isolation(self):
        with tempfile.TemporaryDirectory() as d:
            s=Store(Path(d)/'db')
            for p in ['alpha','beta']: s.add_project({'slug':p,'name':p})
            s.bind_github({'project':'alpha','repository':'owner/repo'})
            sync=lambda repo:fetch_snapshot(repo,fixture)
            self.assertEqual(s.sync_github('alpha',sync)['inserted'],3)
            self.assertEqual(s.sync_github('alpha',sync)['duplicates'],3)
            self.assertEqual(s.entries('beta'),[])
            self.assertEqual(len(s.entries('alpha','fixture')),2)
            changed=lambda repo:fetch_snapshot(repo,lambda p:fixture(p,'failure'))
            self.assertEqual(s.sync_github('alpha',changed)['inserted'],1)
            self.assertEqual(len(s.entries('alpha','CI')),3) # two CI runs and PR disclaimer
            self.assertEqual(Store(s.path).github_binding('alpha')['repository'],'owner/repo')
            before=s.backup()
            def fail(repo): raise GitHubError('offline')
            with self.assertRaises(GitHubError): s.sync_github('alpha',fail)
            self.assertEqual(s.backup(),before)
