import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from uuid import uuid4

from production.intake import Intake
from production.pult_link import collect, view


class ObservationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.order = Intake(self.root, enqueue=True).create({'request_id': str(uuid4()),
            'mode': 'new_video', 'brief': 'PRIVATE BRIEF', 'changes': '', 'preserve': ''})
        with sqlite3.connect(self.root/'intake.sqlite3') as db:
            sha = db.execute('SELECT fingerprint FROM orders').fetchone()[0]
        self.link = {'task_id': str(uuid4()), 'task_revision': 1, 'owner_id': 'owner-test',
                     'order_id': self.order['id'], 'order_fingerprint': sha}

    def test_real_intake_contract_and_repeated_reads_do_not_write(self):
        before = (self.root/'intake.sqlite3').read_bytes()
        for _ in range(3):
            data = view(collect(self.root, self.link, now=1000), self.link, now=1001)
            self.assertEqual(data['state'], 'observed')
            self.assertEqual(data['preparation'], 'queued')
            self.assertFalse(data['finished_video_accepted'])
            self.assertFalse(data['can_execute'])
        self.assertEqual(before, (self.root/'intake.sqlite3').read_bytes())
        self.assertNotIn('PRIVATE', json.dumps(data))
        self.assertNotIn('order_id', data)

    def test_missing_does_not_create_database(self):
        missing = self.root/'absent'
        self.assertEqual(collect(missing, self.link)['state'], 'unavailable')
        self.assertFalse(missing.exists())

    def test_wrong_order_is_not_empty_success(self):
        link = dict(self.link, order_id=str(uuid4()))
        self.assertEqual(collect(self.root, link)['state'], 'binding_mismatch')

    def test_changed_fingerprint_blocks(self):
        self.assertEqual(collect(self.root, dict(self.link, order_fingerprint='0'*64))['state'], 'binding_mismatch')

    def test_tampered_order_blocks(self):
        with sqlite3.connect(self.root/'intake.sqlite3') as db:
            data = json.loads(db.execute('SELECT data FROM orders').fetchone()[0])
            data['brief'] = 'changed'
            db.execute('UPDATE orders SET data=?', (json.dumps(data),))
        self.assertEqual(collect(self.root, self.link)['state'], 'binding_mismatch')

    def test_symlink_rejected(self):
        alias = self.root/'alias'; alias.symlink_to(self.root, target_is_directory=True)
        self.assertEqual(collect(alias, self.link)['state'], 'unavailable')

    def test_malformed_db_is_unknown(self):
        (self.root/'intake.sqlite3').write_bytes(b'broken')
        self.assertEqual(collect(self.root, self.link)['state'], 'unavailable')

    def test_snapshot_expiry_and_future_time(self):
        data = collect(self.root, self.link, now=1000)
        self.assertEqual(view(data, self.link, now=1200)['state'], 'stale')
        self.assertEqual(view(data, self.link, now=900)['state'], 'unavailable')

    def test_snapshot_cannot_cross_binding(self):
        data = collect(self.root, self.link, now=1000)
        for key, value in [('task_id', str(uuid4())), ('owner_id', 'another'), ('task_revision', 2)]:
            self.assertEqual(view(data, dict(self.link, **{key: value}), now=1000)['state'], 'unavailable')

    def test_source_never_escalates_acceptance(self):
        data = collect(self.root, self.link)
        data['finished_video_accepted'] = True
        self.assertEqual(view(data, self.link)['state'], 'unavailable')

    def test_unknown_status_is_never_ready(self):
        with sqlite3.connect(self.root/'intake.sqlite3') as db:
            db.execute("UPDATE preparation_jobs SET status='secret_path_ready'")
        self.assertEqual(collect(self.root, self.link)['preparation'], 'unavailable')

    def test_plan_review_is_limited_and_new_revision_invalidates(self):
        from production.planning import connect_plans
        with sqlite3.connect(self.root/'intake.sqlite3') as db:
            connect_plans(db)
            plan = {'order_id': self.order['id'], 'revision': 1, 'packet_sha256': 'a'*64}
            review = dict(plan, decision='accept_plan')
            db.execute('INSERT INTO scene_plans VALUES(?,?,?,?,?)', (self.order['id'], 1, str(uuid4()), 'b'*64, json.dumps(plan)))
            db.execute('INSERT INTO plan_reviews VALUES(?,?,?,?,?)', (str(uuid4()), self.order['id'], 1, 'c'*64, json.dumps(review)))
        evidence = self.root/'preparations'/self.order['id']
        evidence.mkdir(parents=True)
        (evidence/'receipt.json').write_text('{"changed_evidence":true}')
        data = view(collect(self.root, self.link), self.link)
        self.assertEqual(data['plan_review'], 'recorded_acceptance_unverified')
        self.assertFalse(data['evidence_current'])
        with sqlite3.connect(self.root/'intake.sqlite3') as db:
            db.execute('INSERT INTO scene_plans VALUES(?,?,?,?,?)', (self.order['id'], 2, str(uuid4()), 'b'*64, json.dumps(dict(plan, revision=2))))
        self.assertEqual(collect(self.root, self.link)['plan_review'], 'pending')


if __name__ == '__main__':
    unittest.main()
