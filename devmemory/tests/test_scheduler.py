import tempfile, unittest, sys, threading
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from server import Store
from github_scheduler import run_sync,scheduler_tick,SyncDeferred,SyncBusy
from github_sync import GitHubRateLimit

class SchedulerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.s=Store(Path(self.tmp.name)/'db'); self.lock=threading.Lock(); self.now=10000; self.calls=[]
        for p in ('alpha','beta'):
            self.s.add_project({'slug':p,'name':p})
            self.s.bind_github({'project':p,'repository':'owner/'+p})
    def clock(self): return self.now
    def fetch(self,repo):
        self.calls.append(repo)
        return [dict(title='CI',body='Fixture',source='https://github.com/'+repo,sha='a'*40)]
    def tick(self): return scheduler_tick(self.s,self.lock,self.fetch,self.clock)
    def manual(self,p,fetcher=None): return run_sync(self.s,self.lock,p,fetcher=fetcher or self.fetch,clock=self.clock)
    def configure(self,p,minutes): return self.s.configure_github({'project':p,'interval_minutes':minutes},self.now)
    def test_opt_in_and_restart(self):
        self.assertIsNone(self.tick());self.assertEqual(self.calls,[])
        self.configure('alpha',60);self.configure('beta',60)
        self.now+=3600;self.assertEqual(self.tick()['inserted'],1)
        self.assertIsNone(self.tick())
        self.s=Store(self.s.path);self.now+=300
        self.assertEqual(self.tick()['inserted'],1)
        self.assertEqual(self.calls,['owner/alpha','owner/beta'])
        self.assertEqual(self.s.github_settings('alpha')['history'][0]['state'],'success')
    def test_manual_shared_gate_and_backoff(self):
        self.manual('alpha')
        with self.assertRaises(SyncDeferred): self.manual('beta')
        self.now+=300
        def fail(repo): raise GitHubRateLimit('rate limit')
        with self.assertRaises(GitHubRateLimit): self.manual('beta',fail)
        self.assertEqual(self.s.github_settings('beta')['history'][0]['state'],'error')
        self.now+=3599
        with self.assertRaises(SyncDeferred): self.manual('alpha')
        self.now+=1;self.assertEqual(self.manual('alpha')['duplicates'],1)
    def test_disable_and_rebind(self):
        self.configure('alpha',60);self.configure('alpha',0)
        self.now+=3600;self.assertIsNone(self.tick())
        self.configure('alpha',60)
        self.s.bind_github({'project':'alpha','repository':'owner/new'})
        self.assertEqual(self.s.github_settings('alpha')['interval_minutes'],0)
        self.now+=3600;self.assertIsNone(self.tick())
    def test_bounded_history_and_interrupted(self):
        for i in range(22):
            self.manual('alpha');self.now+=300
        self.assertEqual(len(self.s.github_settings('alpha')['history']),20)
        self.s.begin_github('alpha',False,self.now)
        self.s.recover_github()
        self.assertEqual(self.s.github_settings('alpha')['history'][0]['state'],'interrupted')
    def test_restore_never_enables_polling(self):
        self.configure('alpha',60);self.manual('alpha')
        restored=Store(Path(self.tmp.name)/'restored')
        restored.restore(self.s.backup())
        self.assertEqual(restored.github_binding('alpha')['repository'],'owner/alpha')
        self.assertEqual(restored.github_settings('alpha')['interval_minutes'],0)
        self.assertEqual(restored.github_settings('alpha')['history'],[])
    def test_busy_and_interval_validation(self):
        for value in (True,1,15,1441,'60'):
            with self.assertRaises(ValueError): self.configure('alpha',value)
        with self.lock:
            with self.assertRaises(SyncBusy): self.manual('alpha')
        self.assertEqual(self.calls,[])
