import time
import unittest
from unittest.mock import patch
from production.core import ProductionError,write_json
from production.guarded_job import execute
from production.tests import test_shots as fixtures


class GuardedJob(unittest.TestCase):
    @classmethod
    def setUpClass(cls):fixtures.BoundShot.setUpClass()
    @classmethod
    def tearDownClass(cls):fixtures.BoundShot.tearDownClass()
    def setUp(self):
        self.case=fixtures.BoundShot();self.case.setUp();self.addCleanup(self.case.doCleanups)
        self.root=self.case.root/'job';self.root.mkdir();self.bundle=self.root/'bundle';self.bundle.mkdir()
        self.request=self.root/'request.json';write_json(self.request,self.case.prepared)
        now=time.time();self.intent={'schema_version':1,'approved':True,'created_at_epoch':now,'terminate_at_epoch':now+600,
            'budget_usd':1,'hourly_total_usd':1,'request_sha256':self.case.prepared['request_sha256'],
            'body':{'name':'zina-video-'+'a'*32,'image':'image@sha256:'+'b'*64,'disk':5,'cpu':{'id':'cpu3c','vcpuCount':2}}}
        write_json(self.root/'allocation.json',self.intent)
    def run_job(self):return execute(self.root,self.bundle,self.case.root,self.request,self.root/'key',self.root/'ssh')
    def test_completed_shot_builds_project_without_any_cloud_call(self):
        self.case.execute()
        with patch('production.guarded_job.AllocationControl',side_effect=AssertionError('cloud accessed')):
            result=self.run_job();again=self.run_job()
        self.assertTrue(result['editable_project_ready']);self.assertEqual(result,again)
        self.assertFalse(result['finished_video_accepted'])
    def test_missing_preparation_blocks_allocation(self):
        with patch('production.guarded_job.allocate_once') as allocate:
            with self.assertRaisesRegex(ProductionError,'bundle is incomplete'):self.run_job()
        allocate.assert_not_called();self.assertFalse((self.root/'allocation-cancel').exists())
    def test_other_shot_cannot_borrow_budget(self):
        self.intent['request_sha256']='0'*64;write_json(self.root/'allocation.json',self.intent)
        with patch('production.guarded_job.allocate_once') as allocate:
            with self.assertRaisesRegex(ProductionError,'exact prepared shot'):self.run_job()
        allocate.assert_not_called()
    def test_unknown_create_outcome_requests_independent_cleanup(self):
        for n in ('comfy.tar.gz','worker.tar.gz','comfy-constraints.txt','gpu_bootstrap_probe.py'):(self.bundle/n).touch()
        for n in ('download-locations.private.json','scoped_model_download.py','ssh'):(self.root/n).touch()
        with patch('production.guarded_job.private_token',return_value='fixture'),patch('production.guarded_job.AllocationControl'),\
            patch('production.guarded_job.launch_allocation',return_value={'unit':'fixture'}),\
            patch('production.guarded_job.watcher_ready',return_value=True),\
            patch('production.guarded_job.allocate_once',side_effect=ProductionError('reply lost')):
            with self.assertRaisesRegex(ProductionError,'reply lost'):self.run_job()
        self.assertTrue((self.root/'allocation-cancel').exists())
