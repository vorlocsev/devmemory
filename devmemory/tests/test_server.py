import json, tempfile, threading, unittest, sys, urllib.request, urllib.error
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from server import Store,make_server,CONTEXT_CHARS,MAX_WORKERS,PAGE_SIZE,canonical,MAX_BACKUP
import hashlib, sqlite3

class StorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup); self.path=Path(self.tmp.name)/'db'; self.s=Store(self.path)
        for p in ['alpha','beta']: self.s.add_project({'slug':p,'name':p})
    def entry(self,**kw): return dict(project='alpha',kind='note',status='reported',title='Проверка ядра',body='Сборка прошивки',**kw)
    def test_backup_roundtrip(self):
        self.s.add(self.entry()); self.s.add(dict(self.entry(),project='beta',title='Other'))
        backup=self.s.backup(); dest=Store(Path(self.tmp.name)/'restored')
        self.assertEqual(dest.restore(backup),{'projects':2,'entries':2})
        self.assertEqual(dest.backup(),backup)
        self.assertEqual(dest.entries('alpha','провер'),self.s.entries('alpha','провер'))
        self.assertEqual(dest.entries('beta','провер'),[])
        with self.assertRaises(sqlite3.IntegrityError): dest.restore(backup)
        self.assertEqual(dest.backup(),backup)
    def test_backup_corruption_and_invalid_rows(self):
        self.s.add(self.entry()); backup=self.s.backup()
        dest=Store(Path(self.tmp.name)/'restored')
        backup['payload']['entries'][0]['project']='missing'
        with self.assertRaisesRegex(ValueError,'checksum'): dest.restore(backup)
        backup['sha256']=hashlib.sha256(canonical(backup['payload'])).hexdigest()
        with self.assertRaises(ValueError): dest.restore(backup)
        self.assertEqual(dest.projects(),[])
    def test_backup_duplicate_id_atomic(self):
        self.s.add(self.entry()); backup=self.s.backup()
        backup['payload']['entries']*=2
        backup['sha256']=hashlib.sha256(canonical(backup['payload'])).hexdigest()
        dest=Store(Path(self.tmp.name)/'restored')
        with self.assertRaises(ValueError): dest.restore(backup)
        self.assertEqual(dest.projects(),[])
    def test_backup_size_bound(self):
        for i in range(22): self.s.add(dict(self.entry(),body='😀'*50000))
        with self.assertRaisesRegex(ValueError,'4 MiB'): self.s.backup()
    def test_cyrillic_search(self):
        self.s.add(self.entry()); self.assertEqual(len(self.s.entries('alpha','провер ядра')),1)
    def test_project_isolation(self):
        self.s.add(self.entry()); self.assertEqual(self.s.entries('beta','ядра'),[])
    def test_persistence(self):
        self.s.add(self.entry()); self.assertEqual(len(Store(self.path).entries('alpha')),1)
    def test_verification_fields(self):
        d=self.entry(); d.update(kind='evidence',status='verified')
        with self.assertRaises(ValueError): self.s.add(d)
        d['source']='https://example.com/run';
        with self.assertRaises(ValueError): self.s.add(d)
        d['sha']='a'*40; self.assertIn('id',self.s.add(d))
    def test_invalid_slug(self):
        with self.assertRaises(ValueError): self.s.add_project({'slug':'../bad','name':'bad'})
    def test_unknown_project(self):
        d=self.entry();d['project']='missing'
        with self.assertRaises(ValueError): self.s.add(d)
    def test_delete_fts(self):
        id=self.s.add(self.entry())['id']; self.assertFalse(self.s.delete('beta',id)); self.assertTrue(self.s.delete('alpha',id)); self.assertEqual(self.s.entries('alpha','ядра'),[])
    def test_context_labels(self):
        self.s.add(self.entry()); t=self.s.context('alpha'); self.assertIn('Historical memory',t); self.assertIn('reported',t)
    def test_context_budget(self):
        d=self.entry(); d['body']='я'*50000
        self.s.add(d); ctx=self.s.context('alpha')
        self.assertLessEqual(len(ctx),CONTEXT_CHARS)
        self.assertIn('[Context limited;',ctx)
    def test_pagination(self):
        for i in range(PAGE_SIZE+2): self.s.add(self.entry())
        first=self.s.entries('alpha'); second=self.s.entries('alpha',offset=PAGE_SIZE)
        self.assertEqual(len(first),PAGE_SIZE); self.assertEqual(len(second),2)
        self.assertFalse({x['id'] for x in first}&{x['id'] for x in second})
    def test_fts_syntax(self):
        self.s.add(self.entry()); self.assertEqual(self.s.entries('alpha','"***'),[])

class HTTPTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup); self.token='x'*40; self.s=make_server('127.0.0.1',0,self.tmp.name,'standalone',self.token); self.t=threading.Thread(target=self.s.serve_forever,daemon=True); self.t.start();self.addCleanup(self.stop)
    def stop(self): self.s.shutdown();self.s.server_close();self.t.join()
    def request(self,path,body=None,token=True,marker=True):
        h={};
        if token:h['Authorization']='Bearer '+self.token
        if body is not None:
            h['Content-Type']='application/json'
            if marker:h['X-DevMemory']='1'
        req=urllib.request.Request('http://127.0.0.1:'+str(self.s.server_port)+path, data=json.dumps(body).encode() if body is not None else None,headers=h)
        try: return urllib.request.urlopen(req,timeout=3).status
        except urllib.error.HTTPError as e: return e.code
    def test_health_mode(self):
        with urllib.request.urlopen('http://127.0.0.1:'+str(self.s.server_port)+'/health',timeout=3) as r:
            data=json.load(r)
        self.assertEqual(data,{'status':'ok','version':'0.2.3','mode':'standalone'})
    def test_backup_api_auth_and_restore(self):
        self.assertEqual(self.request('/api/backup',token=False),403)
        self.assertEqual(self.request('/api/restore',{},token=False),403)
        self.assertEqual(self.request('/api/restore',{},marker=False),400)
        self.assertEqual(self.request('/api/projects',{'slug':'demo','name':'Demo'}),201)
        req=urllib.request.Request('http://127.0.0.1:'+str(self.s.server_port)+'/api/backup',headers={'Authorization':'Bearer '+self.token})
        with urllib.request.urlopen(req,timeout=3) as r: backup=json.load(r)
        self.assertEqual(self.request('/api/restore',backup),409)
        self.assertEqual(self.request('/api/restore',{}),400)
    def test_api_auth(self): self.assertEqual(self.request('/api/projects',token=False),403)
    def test_auth_required_at_start(self):
        with self.assertRaises(ValueError): make_server('127.0.0.1',0,self.tmp.name,'standalone','short')
    def test_api_create(self):
        self.assertEqual(self.request('/api/projects',{'slug':'demo','name':'Demo'}),201);self.assertEqual(self.request('/api/projects'),200)
        self.assertEqual(self.request('/api/entries',{'project':'demo','kind':'note','status':'reported','title':'Hello','body':'World'}),201)
        self.assertEqual(self.request('/api/entries?project=demo&q=World'),200);self.assertEqual(self.request('/api/context?project=demo'),200)
    def test_write_marker(self): self.assertEqual(self.request('/api/projects',{'slug':'demo','name':'Demo'},marker=False),400)
    def test_ingress_deny_direct(self): self.s.mode='ingress'; self.assertEqual(self.request('/'),403)
    def test_static(self): self.assertEqual(self.request('/',token=False),200);self.assertEqual(self.request('/app.js',token=False),200)
    def test_worker_limit(self):
        self.assertEqual(MAX_WORKERS,8)
        # Exhaust the exact same semaphore used by process_request.
        for _ in range(MAX_WORKERS): self.assertTrue(self.s.slots.acquire(blocking=False))
        try: self.assertFalse(self.s.slots.acquire(blocking=False))
        finally:
            for _ in range(MAX_WORKERS): self.s.slots.release()
    def test_large_unicode_record(self):
        self.assertEqual(self.request('/api/projects',{'slug':'demo','name':'Demo'}),201)
        self.assertEqual(self.request('/api/entries',{'project':'demo','kind':'note','status':'reported','title':'Unicode','body':'😀'*50000}),201)
    def test_bad_json_shape(self): self.assertEqual(self.request('/api/projects',[]),400)
if __name__=='__main__': unittest.main()
