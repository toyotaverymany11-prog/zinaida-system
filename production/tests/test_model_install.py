import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import signal
import tempfile
import unittest
from unittest.mock import patch

from production.core import Cancelled, ProductionError, Runtime, object_digest
from production.model_install import inspect_install, install, installation_lock, validate_lock


class ModelInstallation(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base/'models'
        self.payload = b'verified model fixture'
        self.spec = {'repo_id':'fixture/model', 'revision':'a'*40,
                     'models':[{'path':'vae/model.safetensors', 'bytes':len(self.payload),
                                'sha256':hashlib.sha256(self.payload).hexdigest()}],
                     'total_model_bytes':len(self.payload)}

    def run_install(self, **kwargs):
        options = dict(download_authorized=True, max_download_bytes=len(self.payload), reserve_bytes=0)
        options.update(kwargs)
        runtime = options.pop('runtime', Runtime(5))
        return install(self.spec, self.root, Path(sys.executable), runtime, **options)

    def fetch(self, lock, model, stage, python, runtime):
        path=stage/model['path'];path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(self.payload)

    def test_plan_does_not_create_files_and_cli_blocks_unauthorized_download(self):
        report=inspect_install(self.spec,self.root,Runtime(5),0)
        self.assertEqual(report['status'],'download_required')
        self.assertFalse(self.root.exists())
        with patch('production.model_install._hub_call') as remote:
            with self.assertRaises(ProductionError):self.run_install(download_authorized=False)
            self.assertFalse(self.root.exists())
            with self.assertRaises(ProductionError):self.run_install(max_download_bytes=1)
            remote.assert_not_called()
        run=subprocess.run([sys.executable,'-m','production','models-install','--root',str(self.root),
                            '--hf-python',sys.executable],capture_output=True,text=True,timeout=10)
        self.assertEqual(run.returncode,2)
        self.assertIn('authorization',json.loads(run.stdout)['error'])

    def test_verified_install_is_reused_without_network_and_corruption_preserved(self):
        with patch('production.model_install._hub_call',side_effect=self.fetch) as fetch:
            result=self.run_install()
            self.assertEqual(result['status'],'installed_verified')
            self.assertFalse(result['generation_authorized'])
            self.assertFalse(result['gpu_qualified'])
            target=self.root/'vae/model.safetensors'
            self.assertEqual(target.read_bytes(),self.payload)
            result=self.run_install(max_download_bytes=0)
            self.assertEqual(result['models'][0]['action'],'reused_verified')
            self.assertEqual(fetch.call_count,1)
            target.write_bytes(b'X'*len(self.payload))
            with self.assertRaises(ProductionError):self.run_install()
            self.assertEqual(target.read_bytes(),b'X'*len(self.payload))
            self.assertEqual(fetch.call_count,1)

    def test_download_corruption_never_becomes_installed(self):
        def corrupt(lock,model,stage,python,runtime):
            self.fetch(lock,model,stage,python,runtime)
            (stage/model['path']).write_bytes(b'X'*len(self.payload))
        with patch('production.model_install._hub_call',side_effect=corrupt):
            with self.assertRaises(ProductionError):self.run_install()
        self.assertFalse((self.root/'vae/model.safetensors').exists())
        receipt=json.loads(next(self.root.rglob('receipt.json')).read_text())
        self.assertEqual(receipt['status'],'failed')
        with patch('production.model_install._hub_call') as fetch:
            with self.assertRaises(ProductionError):self.run_install()
            fetch.assert_not_called()

    def test_completed_stage_after_crash_is_verified_then_promoted_without_network(self):
        stage=self.root/'.production-install'/object_digest(self.spec)/'staging'
        self.fetch(self.spec,self.spec['models'][0],stage,None,Runtime(5))
        with patch('production.model_install._hub_call') as fetch:
            self.assertEqual(self.run_install()['status'],'installed_verified')
            fetch.assert_not_called()
        self.assertEqual((self.root/'vae/model.safetensors').read_bytes(),self.payload)

    def test_interrupted_process_stops_and_partial_state_survives_explicit_retry(self):
        pidfile=self.base/'pid'
        def slow(lock,model,stage,python,runtime):
            stage.mkdir(parents=True,exist_ok=True)
            script="import os,time,pathlib;pathlib.Path('partial').write_bytes(b'p');pathlib.Path(%r).write_text(str(os.getpid()));time.sleep(30)" % str(pidfile)
            runtime.run([sys.executable,'-c',script],cwd=stage)
        with patch('production.model_install._hub_call',side_effect=slow):
            with self.assertRaises(Cancelled):self.run_install(runtime=Runtime(5, should_cancel=pidfile.exists))
        with self.assertRaises(ProcessLookupError):os.kill(int(pidfile.read_text()),0)
        receipt=json.loads(next(self.root.rglob('receipt.json')).read_text())
        self.assertEqual(receipt['status'],'interrupted')
        def resume(lock,model,stage,python,runtime):
            self.assertEqual((stage/'partial').read_bytes(),b'p')
            self.fetch(lock,model,stage,python,runtime)
        with patch('production.model_install._hub_call',side_effect=resume):
            self.assertEqual(self.run_install()['status'],'installed_verified')

    def test_disk_reserve_blocks_transfer(self):
        from collections import namedtuple
        disk=namedtuple('disk','total used free')(100,99,1)
        with patch('production.model_install.shutil.disk_usage',return_value=disk),patch('production.model_install._hub_call') as fetch:
            with self.assertRaises(ProductionError):self.run_install()
            fetch.assert_not_called()

    def test_sigterm_stops_owned_download_child(self):
        pidfile=self.base/'child.pid'
        code="""from production.model_install import cancel_on_signal
from production.core import Runtime,Cancelled
import sys
try:
 with cancel_on_signal():
  Runtime(10).run([sys.executable,'-c',%r])
except Cancelled:
 sys.exit(2)
""" % ("import os,time,pathlib;pathlib.Path(%r).write_text(str(os.getpid()));time.sleep(20)" % str(pidfile))
        parent=subprocess.Popen([sys.executable,'-c',code],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            deadline=time.monotonic()+5
            while not pidfile.exists() and time.monotonic()<deadline:time.sleep(.02)
            self.assertTrue(pidfile.exists())
            parent.send_signal(signal.SIGTERM)
            self.assertEqual(parent.wait(timeout=5),2)
            with self.assertRaises(ProcessLookupError):os.kill(int(pidfile.read_text()),0)
        finally:
            if parent.poll() is None:parent.kill();parent.wait()
            if pidfile.exists():
                try:os.kill(int(pidfile.read_text()),signal.SIGKILL)
                except ProcessLookupError:pass

    def test_lock_wait_is_bounded_and_cannot_start_second_transfer(self):
        with installation_lock(self.root,Runtime(5)),patch('production.model_install._hub_call') as fetch:
            with self.assertRaises(Cancelled):self.run_install(runtime=Runtime(.1))
            fetch.assert_not_called()

    def test_invalid_pins_paths_and_sizes_rejected(self):
        bad_specs=[]
        for key,value in [('revision','main'),('repo_id','https://evil.invalid/model'),('total_model_bytes',1)]:
            bad=copy.deepcopy(self.spec);bad[key]=value;bad_specs.append(bad)
        for key,value in [('path','../escape'),('path','/absolute'),('path','.production-install/file'),
                          ('path','vae//file'),('sha256','unknown'),('bytes',True)]:
            bad=copy.deepcopy(self.spec);bad['models'][0][key]=value;bad_specs.append(bad)
        bad=copy.deepcopy(self.spec);bad['models']*=2;bad_specs.append(bad)
        for bad in bad_specs:
            with self.subTest(bad=bad),self.assertRaises(ProductionError):validate_lock(bad)

    def test_model_and_state_symlinks_cannot_escape_private_root(self):
        self.root.mkdir()
        outside=self.base/'outside';outside.mkdir()
        (self.root/'vae').symlink_to(outside,target_is_directory=True)
        with self.assertRaises(ProductionError):self.run_install()
        (self.root/'vae').unlink()
        import shutil
        shutil.rmtree(self.root/'.production-install')
        (self.root/'.production-install').symlink_to(outside,target_is_directory=True)
        with self.assertRaises(ProductionError):self.run_install()
        self.assertEqual(list(outside.iterdir()),[])

    def test_hub_worker_errors_do_not_expose_secret_text(self):
        from production.model_install import _hub_call
        runtime=Runtime(5)
        with patch.object(runtime,'run',side_effect=ProductionError('Bearer hf_PRIVATE signed-url-secret')):
            with self.assertRaises(ProductionError) as raised:
                _hub_call(self.spec,self.spec['models'][0],self.root/'staging',sys.executable,runtime)
        self.assertNotIn('PRIVATE',str(raised.exception))
        self.assertNotIn('signed-url',str(raised.exception))

    def test_multiple_files_recover_after_second_transfer_fails(self):
        other=dict(self.spec['models'][0],path='text_encoders/model.safetensors')
        self.spec['models'].append(other);self.spec['total_model_bytes']*=2
        def fail_second(lock,model,stage,python,runtime):
            if model['path'].startswith('text_'):raise ProductionError('connection lost')
            self.fetch(lock,model,stage,python,runtime)
        with patch('production.model_install._hub_call',side_effect=fail_second):
            with self.assertRaises(ProductionError):self.run_install(max_download_bytes=len(self.payload)*2)
        with patch('production.model_install._hub_call',side_effect=self.fetch) as fetch:
            result=self.run_install()
            self.assertEqual(result['status'],'installed_verified')
            self.assertEqual(result['models'][0]['action'],'reused_verified')
            self.assertEqual(fetch.call_count,1)
