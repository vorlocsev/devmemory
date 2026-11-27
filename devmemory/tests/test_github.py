import tempfile, unittest, sys, json, io, urllib.error
from unittest.mock import patch, MagicMock
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from server import Store
from github_sync import fetch_snapshot, normalize_repo, GitHubError, load_token, request_json, make_fetcher, NoRedirect

A='a'*40
B='b'*40
def fixture(path,conclusion='success'):
    if '/commits?' in path: return [{'sha':A,'commit':{'message':'fixture'}}]
    if '/pulls?' in path: return [{'number':7,'title':'PR fixture','state':'open','head':{'sha':B,'repo':{'full_name':'fork/demo'}},'base':{'ref':'main'}}]
    if '/actions/runs?' in path: return {'workflow_runs':[{'id':123,'run_attempt':1,'head_sha':A,'name':'CI','status':'completed','conclusion':conclusion,'event':'pull_request'}]}
    raise AssertionError(path)

class GitHubTests(unittest.TestCase):
    def test_token_config(self):
        token='github_pat_'+'A'*40
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'options.json'
            p.write_text(json.dumps({'github_token':token}))
            self.assertEqual(load_token('ingress',d,{}),token)
            self.assertEqual(load_token('standalone',d,{'DEVMEMORY_GITHUB_TOKEN':token}),token)
            self.assertEqual(load_token('standalone',d,{}),'')
            p.write_text('{"github_token":"invalid-secret"}')
            with self.assertRaisesRegex(ValueError,'Invalid GitHub credential configuration'): load_token('ingress',d,{})
    def test_token_only_on_fixed_get(self):
        token='github_pat_'+'A'*40
        response=MagicMock()
        response.__enter__.return_value.read.return_value=b'[]'
        with patch('github_sync.urllib.request.build_opener') as build:
            build.return_value.open.return_value=response
            self.assertEqual(request_json('/repos/a/b/commits?per_page=5',token),[])
            req=build.return_value.open.call_args.args[0]
            self.assertEqual(req.full_url,'https://api.github.com/repos/a/b/commits?per_page=5')
            self.assertEqual(req.get_method(),'GET')
            self.assertEqual(req.get_header('Authorization'),'Bearer '+token)
            self.assertIsInstance(build.call_args.args[1],NoRedirect)
            self.assertIsNone(NoRedirect().redirect_request(None,None,302,None,None,'https://example.com'))
            for path in ('https://evil.example','/repos/a/../commits?per_page=5','/repos/a/b/issues'):
                with self.assertRaises(GitHubError): request_json(path,token)
            self.assertEqual(build.return_value.open.call_count,1)
    def test_credential_redaction(self):
        token='github_pat_'+'A'*40
        with patch('github_sync.request_json') as req:
            req.side_effect=lambda p,token='': [{'sha':A,'commit':{'message':token}}] if '/commits?' in p else fixture(p)
            rows=make_fetcher(token)('owner/repo')
            self.assertNotIn(token,json.dumps(rows))
            self.assertIn('[REDACTED]',rows[0]['body'])
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
            restored=Store(Path(d)/'restored')
            self.assertEqual(restored.restore(before),{'projects':2,'entries':4})
            self.assertEqual(restored.github_binding('alpha')['repository'],'owner/repo')
            self.assertEqual(restored.sync_github('alpha',sync)['duplicates'],3)
            self.assertEqual(restored.backup(),before)
            def fail(repo): raise GitHubError('offline')
            with self.assertRaises(GitHubError): s.sync_github('alpha',fail)
            self.assertEqual(s.backup(),before)
