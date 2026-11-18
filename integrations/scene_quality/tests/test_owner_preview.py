"""Synthetic protocol tests, using the installed real session recheck function."""
import contextlib
import hashlib
import importlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
from uuid import uuid4

from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer
_adapter = str(Path(__file__).resolve().parents[2]/'megamozg')
if _adapter not in sys.path: sys.path.insert(0, _adapter)
try:
    import team as installed_team
except ImportError:
    installed_team = None
import video_owner_preview as preview
import video_scene_producer as candidate

COOKIE = 'unit_owner_session'
def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()

class Store:
    def __init__(self, path):
        self.path = path
    @contextlib.contextmanager
    def db(self):
        db = sqlite3.connect(self.path); db.row_factory = sqlite3.Row
        try:
            yield db
        finally:
            db.close()

@unittest.skipIf(installed_team is None, 'Installed pult session auth required for this integration test')
class OwnerHTTP(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(str(Path(self.temp.name)/'sessions.sqlite'))
        self.owner = str(uuid4()); self.other = str(uuid4()); self.employee = str(uuid4())
        self.link = {'task_id':str(uuid4()),'task_revision':1,'owner_id':self.owner,
                     'order_id':str(uuid4()),'order_fingerprint':'a'*64}
        self.revision='b'*64; self.data=b'synthetic-protocol-draft-no-private-content'
        self.sha=hashlib.sha256(self.data).hexdigest(); self.calls=0; self.after_read=None
        with self.store.db() as db:
            db.executescript("""
                CREATE TABLE users(id TEXT PRIMARY KEY,name TEXT,role TEXT,active INTEGER);
                CREATE TABLE sessions(token_hash TEXT,user_id TEXT,csrf TEXT,expires REAL);
                CREATE TABLE team_tasks(id TEXT,revision INTEGER,created_by TEXT);
            """)
            for uid, role, token in [(self.owner,'owner','owner'),(self.other,'owner','other'),
                                     (self.employee,'employee','employee')]:
                db.execute('INSERT INTO users VALUES(?,?,?,1)',(uid,'Synthetic User',role))
                db.execute('INSERT INTO sessions VALUES(?,?,?,?)',(digest(token),uid,'csrf',9e12))
            db.execute('INSERT INTO team_tasks VALUES(?,?,?)',(self.link['task_id'],1,self.owner));db.commit()
        # team.active_request is the actual installed function; only app constants
        # are supplied by this isolated harness, not a real server or session.
        import team
        self.assertIn('active_request',dir(team))
        fake_app=types.ModuleType('app');fake_app.COOKIE=COOKIE;fake_app.digest=digest
        self.app_patch=patch.dict(sys.modules,{'app':fake_app});self.app_patch.start()
        self.addCleanup(self.app_patch.stop)
        @web.middleware
        async def identity(request, handler):
            token=request.cookies.get(COOKIE,'')
            with self.store.db() as db:
                row=db.execute('SELECT users.id,users.role FROM users JOIN sessions ON sessions.user_id=users.id WHERE token_hash=?',
                               (digest(token),)).fetchone()
            if row is None:
                raise web.HTTPUnauthorized()
            request['user']=dict(row)
            if request.headers.get('X-Synthetic-Agent')=='yes':
                request['agent_authenticated']=True
            return await handler(request)
        app=web.Application(middlewares=[identity])
        install=preview.install_imported if getattr(self,'imported_mode',False) else preview.install
        install(app,self.store,{self.link['task_id']:self.link},self.producer)
        self.client=TestClient(TestServer(app));await self.client.start_server()
        self.addAsyncCleanup(self.client.close)

    def producer(self, link, revision, kind):
        self.calls+=1
        if self.after_read:self.after_read()
        if getattr(self,'imported_mode',False):
            if kind=='owner_imported_draft_catalog':
                return {'binding':self.link,'current':True,'drafts':[{'artifact_id':self.revision,'sha256':self.sha,'bytes':len(self.data),'title':'Synthetic imported film','source_kind':'imported_film','project_id':'unit-project','duration_seconds':1}],**preview.FLAGS}
            return {'binding':self.link,'current':True,'artifact_id':revision,'kind':kind,'sha256':self.sha,'data':self.data,**preview.FLAGS}
        if kind=='owner_draft_catalog':
            return {'binding':self.link,'current':True,
                    'drafts':[{'revision':self.revision,'sha256':self.sha,'bytes':len(self.data)}],
                    **preview.FLAGS}
        return {'binding':self.link,'current':True,'revision':revision,'kind':kind,
                'sha256':self.sha,'data':self.data,**preview.FLAGS}

    async def get(self, token='owner', tail='', headers=None):
        prefix='imported-drafts' if getattr(self,'imported_mode',False) else 'drafts'
        return await self.client.get('/api/workboard/tasks/'+self.link['task_id']+'/video/'+prefix+tail,
                                     cookies={COOKIE:token},headers=headers)

    async def test_owner_catalog_and_bytes_are_explicit_draft(self):
        response=await self.get()
        self.assertEqual(response.status,200);value=await response.json()
        self.assertEqual(value['label'],preview.LABEL);self.assertFalse(value['ready_for_owner'])
        self.assertFalse(value['finished_video_accepted']);self.assertFalse(value['publication_authorized'])
        response=await self.get(tail='/'+self.revision+'/video')
        self.assertEqual(response.status,200);self.assertEqual(await response.read(),self.data)
        self.assertEqual(response.headers['X-Video-Status'],'draft')
        self.assertEqual(response.headers['X-Video-Accepted'],'false')
        self.assertEqual(response.headers['Cache-Control'],'no-store, private')

    async def test_other_owner_employee_agent_and_missing_session_denied_before_producer(self):
        for token in ['other','employee','missing']:
            response=await self.get(token)
            self.assertIn(response.status,[401,403])
        response=await self.get(headers={'X-Synthetic-Agent':'yes'})
        self.assertEqual(response.status,403);self.assertEqual(self.calls,0)

    async def test_session_revocation_during_read_denies_returned_bytes(self):
        def revoke():
            with self.store.db() as db:
                db.execute('DELETE FROM sessions WHERE token_hash=?',(digest('owner'),));db.commit()
        self.after_read=revoke
        response=await self.get(tail='/'+self.revision+'/video')
        self.assertEqual(response.status,401);self.assertNotEqual(await response.read(),self.data)

    async def test_task_binding_change_after_read_is_denied(self):
        def change():
            with self.store.db() as db:db.execute('UPDATE team_tasks SET revision=2');db.commit()
        self.after_read=change
        response=await self.get()
        self.assertEqual(response.status,409)

    async def test_range_preserves_draft_flags_and_exact_sha(self):
        response=await self.get(tail='/'+self.revision+'/video',headers={'Range':'bytes=0-8'})
        self.assertEqual(response.status,206);self.assertEqual(await response.read(),self.data[:9])
        self.assertEqual(response.headers['ETag'],'"'+self.sha+'"')
        self.assertEqual(response.headers['X-Video-Accepted'],'false')


class ProducerBoundary(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.movie=self.root/'movie.mp4';self.movie.write_bytes(b'synthetic-media-v1')
        self.project=self.root/'project.zip';self.project.write_bytes(b'synthetic-project')
        self.sha=hashlib.sha256(self.movie.read_bytes()).hexdigest();self.revision='b'*64
        self.link={'task_id':str(uuid4()),'task_revision':1,'owner_id':str(uuid4()),
                   'order_id':str(uuid4()),'order_fingerprint':'a'*64}
        fake=types.ModuleType('production.scene_revision')
        fake.revision_file=lambda root,order,request,revision,kind:self.movie if kind=='video' else self.project
        self.addCleanup(patch.stopall)
        patch.dict(sys.modules,{'production.scene_revision':fake}).start()
        patch.object(preview,'collect',return_value={'state':'observed'}).start()

    def producer(self):
        return preview.owner_draft_producer(self.root,self.link,'synthetic-request',{self.revision:self.sha})

    def test_exact_draft_is_never_ready_and_does_not_open_candidate_endpoint(self):
        p=self.producer();r=p(self.link,self.revision,'owner_draft_video')
        self.assertEqual(r['sha256'],self.sha);self.assertFalse(r['ready_for_owner'])
        self.assertFalse(r['finished_video_accepted'])
        quality=self.root/'quality';quality.mkdir();(quality/'owner-rejections.json').write_text('{"rejections":[]}')
        with patch.object(candidate,'collect',return_value={'state':'observed'}),patch(
                'integrations.scene_quality.release.guard',return_value={'allowed_as_owner_candidate':False}):
            old=candidate.scene_producer(self.root,self.link,'synthetic-request',[self.revision],quality_root=quality)
            self.assertEqual(old(self.link,None,'catalog')['versions'],[])
            for kind in ['video','project']:
                with self.assertRaises(ValueError):old(self.link,self.revision,kind)

    def test_unknown_revision_changed_hash_and_wrong_kind_denied(self):
        p=self.producer()
        for revision, kind in [('c'*64,'owner_draft_video'),(self.revision,'video'),
                               (self.revision,'project')]:
            with self.assertRaises(ValueError):p(self.link,revision,kind)
        self.movie.write_bytes(b'other-synthetic-media')
        with self.assertRaises(ValueError):p(self.link,self.revision,'owner_draft_video')

    def test_source_or_file_mutation_during_read_revokes_draft(self):
        p=self.producer();original=preview.os.read;done=False
        def mutate(fd,size):
            nonlocal done
            data=original(fd,size)
            if not done:self.movie.write_bytes(b'changed-during-read');done=True
            return data
        with patch.object(preview.os,'read',side_effect=mutate):
            with self.assertRaises(ValueError):p(self.link,self.revision,'owner_draft_video')

    def test_current_source_change_during_read_revokes_draft(self):
        p=self.producer()
        with patch.object(preview,'collect',side_effect=[{'state':'observed'},{'state':'binding_mismatch'}]):
            with self.assertRaises(ValueError):p(self.link,self.revision,'owner_draft_video')

    def test_producer_cannot_forge_ready_or_acceptance_flags(self):
        for name in ['ready_for_owner','finished_video_accepted','publication_authorized']:
            packet=dict(preview.FLAGS);packet[name]=True
            with self.assertRaises(ValueError):preview._flags(packet)

    def test_default_rpc_has_no_draft_capability(self):
        from video_producer_service import worker
        config={'orders':{self.link['task_id']:{'binding':self.link,'root':str(self.root),
                       'request_id':'synthetic-request','revisions':[self.revision]}}}
        with self.assertRaises(ValueError):
            worker(config,{'task':self.link['task_id'],'revision':self.revision,'kind':'owner_draft_video'})

    def test_opt_in_rpc_returns_exact_tagged_draft_without_changing_candidate(self):
        from video_producer_service import worker
        config={'orders':{self.link['task_id']:{'binding':self.link,'root':str(self.root),
                       'request_id':'synthetic-request','revisions':[self.revision],
                       'owner_draft_previews':{self.revision:self.sha}}}}
        r=worker(config,{'task':self.link['task_id'],'revision':self.revision,'kind':'owner_draft_video'})
        self.assertFalse(r['ready_for_owner']);self.assertEqual(r['kind'],'owner_draft_video')
        self.assertIn('data_base64',r)


if __name__=='__main__':
    unittest.main()
