import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from production.analysis import analyze_order, OutcomeUnknown
from production.core import ProductionError
from production.demo import make_fixture
from production.intake import Intake
from production.planning import order_evidence, latest_plan
from production.preparation import prepare_order


class VisualAnalysis(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        cls.fixture=Path(cls.tmp.name)/'media'
        make_fixture(cls.fixture)
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        self.intake=Intake(self.root,enqueue=True)
        p=self.fixture/'red.mp4'
        with p.open('rb') as f:a=self.intake.upload('input.mp4',f,p.stat().st_size)
        self.order=self.intake.create({'request_id':str(uuid4()),'mode':'reference',
            'brief':'Описать наблюдаемые кадры','references':[a['id']]})
        prepare_order(self.root,self.order['id'],max_samples=2)
        with self.intake.connect() as db:db.execute("UPDATE preparation_jobs SET status='awaiting_review'")
        self.packet=order_evidence(self.root,self.order['id'])
        self.ident=self.order['id'];self.request=str(uuid4());self.calls=0
        test=self
        class Planner:
            def generate(self,prompt,images,folder,runtime):
                test.calls+=1
                test.assertEqual(len(images),1)
                test.assertTrue(images[0].is_file())
                test.assertNotIn(str(test.root),prompt)
                r=test.packet['references'][0]
                return {'summary':'Красное поле', 'cast':[],
                    'open_questions':['Движение между выборочными кадрами и звук не проверены'],
                    'scenes':[{'source':{'asset_id':r['asset_id'],'start':0,'end':r['duration_seconds']},
                        'observation':'На выборочных кадрах красный фон','action':'Сохранить исходный цвет',
                        'preserve':['Хронометраж'],'change':['Изменения не заданы'],'checks':['Сверить цвет']}]
                    }, {'model':'synthetic-test','usage':{},'tool_calls':0}
        self.planner=Planner()

    def run_analysis(self,**kwargs):
        return analyze_order(self.root,self.ident,self.request,self.planner,**kwargs)

    def test_validated_plan_reuses_same_attempt_without_another_model_call(self):
        first=self.run_analysis()
        self.assertEqual(first,self.run_analysis())
        self.assertEqual(self.calls,1)
        plan=latest_plan(self.root,self.ident,self.packet['packet_sha256'])
        self.assertEqual(plan['revision'],1)
        self.assertFalse(plan['generation_authorized'])
        self.assertEqual(plan['semantic_review'],'pending')
        self.assertFalse(first['reference_audio_analyzed'])

    def test_recovery_commits_validated_output_without_model_repeat(self):
        with patch('production.analysis.save_plan',side_effect=RuntimeError('crash before commit')):
            with self.assertRaises(RuntimeError):self.run_analysis()
        receipt=self.run_analysis(recover_only=True)
        self.assertEqual(receipt['status'],'plan_saved')
        self.assertEqual(self.calls,1)

    def test_interrupted_response_is_not_repeated_automatically(self):
        with patch.object(self.planner,'generate',side_effect=ProductionError('simulated transport failure')) as gen:
            with self.assertRaises(ProductionError):self.run_analysis()
            with self.assertRaises(OutcomeUnknown):self.run_analysis()
            self.assertEqual(gen.call_count,1)
        self.assertIsNone(latest_plan(self.root,self.ident,self.packet['packet_sha256']))

    def test_corrupt_saved_response_cannot_be_recovered(self):
        with patch('production.analysis.save_plan',side_effect=RuntimeError):
            with self.assertRaises(RuntimeError):self.run_analysis()
        path=self.root/'analyses'/self.ident/self.request/'validated.json'
        path.write_text('{}')
        with self.assertRaises(OutcomeUnknown):self.run_analysis(recover_only=True)
        self.assertEqual(self.calls,1)

    def test_analysis_request_is_idempotent_and_blocks_concurrent_repreparation(self):
        self.intake.request_analysis(self.ident,self.request)
        self.intake.request_analysis(self.ident,self.request)
        with self.assertRaises(ProductionError):self.intake.retry_preparation(self.ident,str(uuid4()))
        self.assertEqual(self.intake.cancel_analysis(self.ident)['status'],'cancelled')
        self.intake.request_analysis(self.ident,self.request)
        self.assertEqual(self.intake.orders()[0]['analysis']['status'],'cancelled')

    def test_stale_manual_edit_is_not_overwritten(self):
        from production.planning import save_plan
        original=save_plan
        def conflicting(root,ident,request,**kwargs):
            other=copy.deepcopy(request);other['request_id']=str(uuid4())
            other['plan']['summary']='Изменение владельца'
            original(root,ident,other)
            return original(root,ident,request)
        with patch('production.analysis.save_plan',side_effect=conflicting):
            with self.assertRaisesRegex(ProductionError,'revision changed'):self.run_analysis()
        self.assertEqual(latest_plan(self.root,self.ident,self.packet['packet_sha256'])['plan']['summary'],'Изменение владельца')
