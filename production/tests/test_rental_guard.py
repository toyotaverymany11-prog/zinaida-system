import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from production.core import ProductionError, Runtime, read_json, write_json
from production.rental_guard import SimulationControl, guard_status, private_token


class GuardProcessTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.lease_path=self.root/'lease.json'
        now=time.time()
        self.pod={'id':'fixture_pod','name':'zina-video-'+'b'*32,
                  'createdAt':datetime.fromtimestamp(now,timezone.utc).isoformat()}
        self.lease={'schema_version':1,'provider':'runpod','resource':dict(self.pod),
            'budget_usd':1,'hourly_total_usd':1,'fixed_cost_usd':0,
            'created_at_epoch':now,'terminate_at_epoch':now+4,
            'cleanup_allowance_seconds':10,'termination_authorized':True,'shared_resource':False}
        write_json(self.lease_path,self.lease)
        self.calls=[];self.drop_delete=False;self.fail_delete=False;self.trickle=False
        owner=self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_GET(self):
                owner.calls.append(('GET',self.path))
                self.send_response(200 if owner.pod else 404);self.end_headers()
                if owner.trickle:
                    for _ in range(80):
                        try:self.wfile.write(b' ');self.wfile.flush()
                        except OSError:break
                        time.sleep(.05)
                elif owner.pod:self.wfile.write(json.dumps(owner.pod).encode())
            def do_DELETE(self):
                owner.calls.append(('DELETE',self.path))
                if not owner.fail_delete:owner.pod=None
                if owner.drop_delete:self.close_connection=True;return
                self.send_response(500 if owner.fail_delete else 204);self.end_headers()
        self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        self.server.daemon_threads=True
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.addCleanup(self.server.server_close);self.addCleanup(self.server.shutdown)
        self.url=f'http://127.0.0.1:{self.server.server_port}/v2'
        self.children=[];self.addCleanup(self.stop_children)

    def stop_children(self):
        for p in self.children:
            if p.poll() is None:p.kill()
            p.wait(timeout=3)

    def start(self,command='watch',extra=()):
        p=subprocess.Popen([sys.executable,'-m','production.rental_guard',command,
            '--lease',str(self.lease_path),'--root',str(self.root/'guard'),
            '--simulation-control-url',self.url,*extra],cwd=Path(__file__).resolve().parents[2],
            stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        self.children.append(p);return p

    def wait_phase(self,phase='watching',timeout=4):
        until=time.monotonic()+timeout
        path=self.root/'guard/fixture_pod/guard.json'
        while time.monotonic()<until:
            if path.exists():
                r=read_json(path)
                if r['phase']==phase:return r
            time.sleep(.02)
        self.fail(f'Guard did not reach {phase}')

    def cleanup_receipt(self):return read_json(self.root/'guard/fixture_pod/cleanup.json')

    def test_detached_guard_survives_launcher_exit_and_simulation_never_ready(self):
        launcher=self.start('launch');out,err=launcher.communicate(timeout=3)
        self.assertEqual(launcher.returncode,0,(out,err))
        r=self.wait_phase();self.assertNotEqual(r['pid'],launcher.pid)
        self.assertFalse(guard_status(self.root/'guard',self.lease)['ready'])
        self.wait_phase('finished',8)
        self.assertTrue(self.cleanup_receipt()['provider_absence_confirmed'])
        self.assertEqual(sum(x[0]=='DELETE' for x in self.calls),1)

    def test_signal_terminates_own_resource_and_checks_absence(self):
        p=self.start();self.wait_phase();p.send_signal(signal.SIGTERM);p.communicate(timeout=4)
        self.assertEqual(p.returncode,0);self.assertIsNone(self.pod)
        self.assertEqual(self.wait_phase('finished')['stop_reason'],'signal')

    def test_cancel_file_reconciles_lost_delete_reply(self):
        self.drop_delete=True;cancel=self.root/'cancel'
        p=self.start(extra=['--cancel-file',str(cancel)]);self.wait_phase();cancel.touch()
        p.communicate(timeout=4)
        self.assertTrue(self.cleanup_receipt()['provider_absence_confirmed'])
        self.assertEqual(sum(x[0]=='DELETE' for x in self.calls),1)

    def test_missing_lease_still_cleans_original_resource(self):
        p=self.start();self.wait_phase();self.lease_path.unlink();p.communicate(timeout=4)
        self.assertEqual(p.returncode,2)
        self.assertTrue(self.cleanup_receipt()['provider_absence_confirmed'])

    def test_changed_lease_does_not_extend_deadline_or_target(self):
        p=self.start();self.wait_phase();changed=dict(self.lease,terminate_at_epoch=time.time()+200)
        write_json(self.lease_path,changed);p.communicate(timeout=4)
        self.assertIsNone(self.pod);self.assertTrue(self.cleanup_receipt()['provider_absence_confirmed'])

    def test_sigkill_restart_keeps_original_deadline(self):
        p=self.start();self.wait_phase();p.kill();p.communicate(timeout=2)
        self.assertFalse(guard_status(self.root/'guard',self.lease)['ready'])
        second=self.start();second.communicate(timeout=8)
        self.assertEqual(second.returncode,0)
        self.assertEqual(self.wait_phase('finished')['terminate_at_epoch'],self.lease['terminate_at_epoch'])
        self.assertTrue(self.cleanup_receipt()['provider_absence_confirmed'])

    def test_second_guard_refuses_same_lease(self):
        first=self.start();self.wait_phase();second=self.start();second.communicate(timeout=2)
        self.assertEqual(second.returncode,2);self.assertIsNotNone(self.pod)
        first.send_signal(signal.SIGTERM);first.communicate(timeout=4)

    def test_foreign_resource_and_zero_budget_never_delete(self):
        self.pod['name']='shared';p=self.start();p.communicate(timeout=3)
        self.assertEqual(p.returncode,2);self.assertFalse(any(x[0]=='DELETE' for x in self.calls))
        self.calls.clear();self.lease['budget_usd']=0;write_json(self.lease_path,self.lease)
        p=self.start();p.communicate(timeout=3);self.assertEqual(self.calls,[])

    def test_trickling_http_body_is_bounded(self):
        self.trickle=True;begin=time.monotonic()
        with self.assertRaises(ProductionError):SimulationControl(self.url).get('fixture_pod',Runtime(.2))
        self.assertLess(time.monotonic()-begin,1)

    def test_credential_file_must_be_private_and_fixture_cannot_leave_loopback(self):
        p=self.root/'credential';p.write_text('fake-test-value');p.chmod(0o644)
        with self.assertRaises(ProductionError):private_token(p)
        p.chmod(0o600);self.assertEqual(private_token(p),'fake-test-value')
        symlink=self.root/'symlink';symlink.symlink_to(p)
        with self.assertRaises(ProductionError):private_token(symlink)
        for url in ['https://api.runpod.io/v2','http://localhost:8000','http://127.0.0.1:8000@evil.test']:
            with self.assertRaises(ProductionError):SimulationControl(url)

    def test_failed_cleanup_never_reports_success(self):
        self.fail_delete=True;p=self.start();self.wait_phase();p.send_signal(signal.SIGTERM)
        p.communicate(timeout=8)
        r=self.cleanup_receipt();self.assertEqual(r['status'],'cleanup_unconfirmed')
        self.assertFalse(r['provider_absence_confirmed'])
        self.assertEqual(sum(x[0]=='DELETE' for x in self.calls),5)
