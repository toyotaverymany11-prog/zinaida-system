import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from production.pult_export import export_once, name_for, read_snapshot, run_worker
from production.pult_link import view
from production.tests import test_pult_link


class ExportTests(unittest.TestCase):
    def setUp(self):
        # Use the same real Intake/order contract as the projection tests.
        self.fixture = test_pult_link.ObservationTests('test_real_intake_contract_and_repeated_reads_do_not_write')
        self.fixture.setUp()
        self.root = self.fixture.root
        self.link = self.fixture.link
        self.tmp = tempfile.TemporaryDirectory()
        self.cache = Path(self.tmp.name)

    def tearDown(self):
        self.fixture.tearDown()
        self.fixture.doCleanups()
        self.tmp.cleanup()

    def test_real_export_read_is_independent_of_source_and_expires(self):
        db = self.root / 'intake.sqlite3'
        before = hashlib.sha256(db.read_bytes()).hexdigest()
        receipt = export_once(self.root, self.cache, self.link)
        self.assertEqual(receipt['state'], 'observed')
        self.assertEqual(before, hashlib.sha256(db.read_bytes()).hexdigest())
        snapshot = read_snapshot(self.cache, self.link)
        self.assertEqual(view(snapshot, self.link)['state'], 'observed')
        db.rename(db.with_suffix('.hidden'))
        self.assertEqual(read_snapshot(self.cache, self.link), snapshot)
        self.assertEqual(view(snapshot, self.link, now=snapshot['observed_at']+181)['state'], 'stale')
        text = (self.cache/name_for(self.link)).read_text()
        self.assertNotIn(str(self.root), text)
        self.assertNotIn('brief', text)
        self.assertEqual(set(snapshot), {'schema','binding','state','observed_at','preparation','analysis','preview','plan_revision','plan_review','read_only','finished_video_accepted'})

    def test_failed_refresh_invalidates_good_cache(self):
        export_once(self.root, self.cache, self.link)
        with patch('production.pult_export.run_worker', side_effect=subprocess.TimeoutExpired('worker', 3)):
            receipt = export_once(self.root, self.cache, self.link)
        self.assertEqual(receipt['state'], 'unavailable')
        self.assertEqual(view(read_snapshot(self.cache,self.link),self.link)['state'], 'unavailable')

    def test_real_child_timeout_leaves_no_detached_child(self):
        marker = self.cache/'child.pid'
        script = 'import os,time,pathlib;pathlib.Path('+repr(str(marker))+').write_text(str(os.getpid()));time.sleep(20)'
        started = time.monotonic()
        with self.assertRaises(subprocess.TimeoutExpired):
            run_worker([sys.executable,'-c',script],b'',0.5)
        self.assertLess(time.monotonic()-started, 3)
        self.assertTrue(marker.exists())
        with self.assertRaises(ProcessLookupError):
            os.kill(int(marker.read_text()),0)

    def test_concurrent_export_does_not_start_another_worker(self):
        with (self.cache/'.export.lock').open('w') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            with patch('production.pult_export.run_worker') as worker:
                with self.assertRaisesRegex(RuntimeError,'export_busy'):
                    export_once(self.root,self.cache,self.link)
                worker.assert_not_called()

    def test_links_fifo_permissions_and_oversize_fail_closed(self):
        target=self.cache/name_for(self.link)
        target.symlink_to('/etc/passwd')
        self.assertIsNone(read_snapshot(self.cache,self.link));target.unlink()
        os.mkfifo(target)
        self.assertIsNone(read_snapshot(self.cache,self.link));target.unlink()
        export_once(self.root,self.cache,self.link)
        target.chmod(0o666)
        self.assertIsNone(read_snapshot(self.cache,self.link));target.chmod(0o600)
        target.write_bytes(b' '*4097)
        self.assertIsNone(read_snapshot(self.cache,self.link))

    def test_malformed_snapshot_and_wrong_owner_fail_closed(self):
        export_once(self.root,self.cache,self.link)
        self.assertIsNone(read_snapshot(self.cache,self.link,trusted_uid=os.geteuid()+1))
        target=self.cache/name_for(self.link);raw=json.loads(target.read_text())
        raw['state']=['observed'];target.write_text(json.dumps(raw))
        self.assertIsNone(read_snapshot(self.cache,self.link))
        target.write_text('{"schema":1,"schema":2}')
        self.assertIsNone(read_snapshot(self.cache,self.link))

    def test_other_binding_cannot_read_cached_order(self):
        export_once(self.root,self.cache,self.link)
        changed=dict(self.link,task_revision=self.link['task_revision']+1)
        self.assertIsNone(read_snapshot(self.cache,changed))

    def test_restrictive_umask_preserves_intended_reader_group(self):
        previous=os.umask(0o077)
        try:
            export_once(self.root,self.cache,self.link)
        finally:
            os.umask(previous)
        self.assertEqual((self.cache/name_for(self.link)).stat().st_mode & 0o777,0o640)

    def test_failed_atomic_replace_preserves_complete_previous_snapshot(self):
        export_once(self.root,self.cache,self.link)
        target=self.cache/name_for(self.link);before=target.read_bytes()
        with patch('production.pult_export.os.replace',side_effect=OSError('test failure')):
            with self.assertRaises(OSError):
                export_once(self.root,self.cache,self.link)
        self.assertEqual(target.read_bytes(),before)
        self.assertEqual(list(self.cache.glob('.tmp-*')),[])


if __name__ == '__main__':
    unittest.main()
