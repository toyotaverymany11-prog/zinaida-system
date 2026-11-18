"""Imported film attachment tests; actual ffprobe, session auth and binding read."""
import base64
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4

import video_imported_draft as imported
import video_owner_preview as preview
import test_owner_preview as owner_test


class ImportedOwnerHTTP(owner_test.OwnerHTTP):
    imported_mode = True


class ImportedArtifact(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.shared=tempfile.TemporaryDirectory()
        cls.movie=Path(cls.shared.name)/'synthetic.mp4'
        subprocess.run(['ffmpeg','-v','error','-y','-f','lavfi','-i','color=blue:s=256x144:r=24:d=1',
                        '-f','lavfi','-i','anullsrc=r=48000:cl=stereo',
                        '-t','1','-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac',
                        '-movflags','+faststart',str(cls.movie)],check=True,timeout=20)
        cls.sha=hashlib.sha256(cls.movie.read_bytes()).hexdigest()
    @classmethod
    def tearDownClass(cls):
        cls.shared.cleanup()

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.db=self.root/'pult.sqlite'
        self.link={'task_id':str(uuid4()),'task_revision':1,'owner_id':str(uuid4()),
                   'order_id':str(uuid4()),'order_fingerprint':'a'*64}
        db=sqlite3.connect(self.db)
        db.executescript("""
            CREATE TABLE users(id TEXT PRIMARY KEY,role TEXT,active INTEGER);
            CREATE TABLE team_tasks(id TEXT,revision INTEGER,created_by TEXT,
                                    assignee_user_id TEXT,assignee_kind TEXT);
        """)
        db.execute('INSERT INTO users VALUES(?,?,1)',(self.link['owner_id'],'owner'))
        db.execute('INSERT INTO team_tasks VALUES(?,?,?,?,?)',
                   (self.link['task_id'],1,self.link['owner_id'],self.link['owner_id'],'human'))
        db.commit();db.close()
        self.config=self.root/'producer.json'
        self.config.write_text(json.dumps({'pult_database':str(self.db),'orders':{
            self.link['task_id']:{'binding':self.link,'root':str(self.root),'request_id':'old-pilot',
                                 'revisions':['b'*64]}}}))
        self.addCleanup(patch.stopall)
        patch.object(imported,'collect',return_value={'state':'observed'}).start()

    def attach(self, expected=None):
        return imported.attach(self.config,self.link['task_id'],type(self).movie,
            self.root/'private-imports',expected_sha256=expected or self.sha,expected_duration=1,
            title='Synthetic imported film',project_id='unit-project',
            provenance={'kind':'synthetic_local_fixture'})

    def producer(self, row):
        return imported.imported_draft_producer(self.root,self.link,
            {row['artifact_id']:row['manifest']})

    def test_attach_actual_av_as_new_import_and_repeat_idempotently(self):
        row=self.attach();self.assertEqual(row['status'],'imported_not_enabled')
        again=self.attach();self.assertEqual(again['artifact_id'],row['artifact_id'])
        self.assertEqual(again['status'],'existing_exact_import')
        result=self.producer(row)(self.link,row['artifact_id'],'owner_imported_draft_video')
        self.assertEqual(result['data'],type(self).movie.read_bytes())
        self.assertNotIn('revision',result);self.assertEqual(result['artifact_id'],row['artifact_id'])
        self.assertFalse(result['ready_for_owner'])
        catalog=self.producer(row)(self.link,None,'owner_imported_draft_catalog')
        entry=catalog['drafts'][0]
        self.assertEqual(entry['source_kind'],'imported_film')
        self.assertEqual(entry['title'],'Synthetic imported film')
        self.assertFalse(catalog['finished_video_accepted'])
        self.assertEqual(list((self.root/'private-imports').iterdir()),
                         [Path(row['manifest']).parent])

    def test_wrong_hash_or_inactive_owner_cannot_register(self):
        with self.assertRaises(ValueError):self.attach(expected='f'*64)
        self.assertFalse((self.root/'private-imports').exists())
        db=sqlite3.connect(self.db);db.execute('UPDATE users SET active=0');db.commit();db.close()
        with self.assertRaises(ValueError):self.attach()
        self.assertFalse((self.root/'private-imports').exists())

    def test_unknown_artifact_and_old_shot_kind_do_not_deliver(self):
        row=self.attach();p=self.producer(row)
        with self.assertRaises(ValueError):p(self.link,'c'*64,'owner_imported_draft_video')
        for kind in ['video','project','owner_draft_video']:
            with self.assertRaises(ValueError):p(self.link,row['artifact_id'],kind)

    def test_media_or_manifest_mutation_revokes_import(self):
        row=self.attach();p=self.producer(row);asset=Path(row['manifest']).parent/'asset.mp4'
        asset.chmod(0o600);asset.write_bytes(b'changed')
        with self.assertRaises(ValueError):p(self.link,row['artifact_id'],'owner_imported_draft_video')
        asset.write_bytes(type(self).movie.read_bytes());asset.chmod(0o400)
        manifest=Path(row['manifest']);manifest.chmod(0o600)
        value=json.loads(manifest.read_text());value['title']='changed-title';manifest.write_text(json.dumps(value))
        with self.assertRaises(ValueError):p(self.link,row['artifact_id'],'owner_imported_draft_video')

    def test_current_task_change_during_read_revokes_import(self):
        row=self.attach();p=self.producer(row)
        with patch.object(imported,'collect',side_effect=[{'state':'observed'},{'state':'binding_mismatch'}]):
            with self.assertRaises(ValueError):p(self.link,row['artifact_id'],'owner_imported_draft_video')

    def test_default_rpc_denies_import_and_explicit_mapping_returns_same_bytes(self):
        from video_producer_service import worker
        row=self.attach();config=json.loads(self.config.read_text())
        request={'task':self.link['task_id'],'revision':row['artifact_id'],'kind':'owner_imported_draft_video'}
        with self.assertRaises(ValueError):worker(config,request)
        config['orders'][self.link['task_id']]['owner_imported_drafts']={row['artifact_id']:row['manifest']}
        result=worker(config,request)
        self.assertEqual(base64.b64decode(result['data_base64']),type(self).movie.read_bytes())
        self.assertEqual(result['artifact_id'],row['artifact_id'])
        self.assertFalse(result['publication_authorized'])


if __name__=='__main__':
    unittest.main()
