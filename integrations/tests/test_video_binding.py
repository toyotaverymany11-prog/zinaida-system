from contextlib import closing
import hashlib
import importlib.util
from pathlib import Path
import sqlite3
import tempfile
import unittest
from uuid import uuid4

spec=importlib.util.spec_from_file_location('video_binding',Path(__file__).parents[1]/'megamozg/video_binding.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class BindingTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.db=Path(self.tmp.name)/'pult.sqlite3';self.task=str(uuid4())
        with closing(sqlite3.connect(self.db)) as db:
            db.executescript('CREATE TABLE users(id,role,active);CREATE TABLE team_tasks(id,revision,created_by,assignee_user_id,assignee_kind);')
            db.execute('INSERT INTO users VALUES(?,?,?)',('owner','owner',1));db.execute('INSERT INTO team_tasks VALUES(?,?,?,?,?)',(self.task,1,'owner','owner','human'));db.commit()
        self.args=dict(task_id=self.task,task_revision=1,owner_id='owner',order_id=str(uuid4()),order_fingerprint='a'*64)

    def test_explicit_binding_does_not_write_database(self):
        before=self.db.read_bytes();self.assertEqual(module.prepare(self.db,**self.args),self.args);self.assertEqual(self.db.read_bytes(),before)

    def test_wrong_revision_or_order_format_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'task_binding_mismatch'):module.prepare(self.db,**dict(self.args,task_revision=2))
        with self.assertRaises(ValueError):module.prepare(self.db,**dict(self.args,order_fingerprint='bad'))

    def test_revoked_owner_and_delegated_task_rejected(self):
        with closing(sqlite3.connect(self.db)) as db:db.execute('UPDATE users SET active=0');db.commit()
        with self.assertRaisesRegex(ValueError,'active_owner_required'):module.prepare(self.db,**self.args)
        with closing(sqlite3.connect(self.db)) as db:db.execute('UPDATE users SET active=1');db.execute("UPDATE team_tasks SET assignee_kind='agent'");db.commit()
        with self.assertRaisesRegex(ValueError,'owner_human_task_required'):module.prepare(self.db,**self.args)

    def test_missing_source_is_not_created_and_symlink_rejected(self):
        path=self.db.parent/'missing';
        with self.assertRaises(ValueError):module.prepare(path,**self.args)
        self.assertFalse(path.exists());path.symlink_to(self.db)
        with self.assertRaises(ValueError):module.prepare(path,**self.args)

    def test_active_employee_assignment_is_explicit(self):
        with closing(sqlite3.connect(self.db)) as db:
            db.execute("INSERT INTO users VALUES('staff','employee',1)");db.execute("UPDATE team_tasks SET assignee_user_id='staff'");db.commit()
        self.assertEqual(module.prepare(self.db,**self.args),self.args)
