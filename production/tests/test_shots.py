import copy
from datetime import datetime, timezone
from pathlib import Path
import shutil
import tempfile
import time
import unittest
from unittest.mock import patch
from uuid import uuid4

from production.core import ProductionError, digest, object_digest, write_json
from production.demo import make_fixture
from production.intake import Intake
from production.planning import order_evidence, save_plan, save_plan_review, review_page
from production.preparation import prepare_order
from production.shots import CHECKS, prepare_shot, execute_shot, shot_file, shot_state, review_shot


class BoundShot(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.media_tmp=tempfile.TemporaryDirectory()
        cls.media=Path(cls.media_tmp.name)/'media'
        make_fixture(cls.media)

    @classmethod
    def tearDownClass(cls):
        cls.media_tmp.cleanup()

    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.intake=Intake(self.root,enqueue=True)
        self.order=self.intake.create({'request_id':str(uuid4()),'mode':'new_video','brief':'Synthetic shot test'})
        self.ident=self.order['id'];prepare_order(self.root,self.ident,max_samples=2)
        with self.intake.connect() as db:
            db.execute("UPDATE preparation_jobs SET status='awaiting_review' WHERE order_id=?",(self.ident,))
        self.packet=order_evidence(self.root,self.ident)
        self.plan_request={'request_id':str(uuid4()),'expected_revision':0,'packet_sha256':self.packet['packet_sha256'],
            'plan':{'author':'synthetic-test','summary':'Synthetic test, not real inference','open_questions':[],
                    'scenes':[dict(source=None,observation='No reference',action='A red object',preserve=['red'],change=['camera motion'],checks=['geometry'])]}}
        save_plan(self.root,self.ident,self.plan_request)
        self.accept={'request_id':str(uuid4()),'expected_revision':1,'packet_sha256':self.packet['packet_sha256'],
            'decision':'accept_plan','notes':'Synthetic structural test only'}
        save_plan_review(self.root,self.ident,self.accept)
        self.request={k:self.accept[k] for k in ('expected_revision','packet_sha256')}
        self.request.update(request_id=str(uuid4()),scene_index=0,seed=137)
        self.prepared=prepare_shot(self.root,self.ident,self.request)
        now=time.time()
        self.lease={'schema_version':1,'provider':'runpod','resource':{'id':'synthetic_pod','name':'zina-video-'+'a'*32,
            'createdAt':datetime.fromtimestamp(now,timezone.utc).isoformat()},'created_at_epoch':now,
            'terminate_at_epoch':now+600,'budget_usd':1,'hourly_total_usd':1,'fixed_cost_usd':0,
            'cleanup_allowance_seconds':30,'termination_authorized':True,'shared_resource':False}
        self.lease_path=self.root/'lease.json';write_json(self.lease_path,self.lease)
        self.grant={'approved':True,'request_sha256':self.prepared['request_sha256'],'lease_sha256':object_digest(self.lease),
            'max_runtime_seconds':30,'budget_usd':.1,'endpoint':'http://127.0.0.1:8188'}
        self.calls=[];owner=self
        class FakeExecutor:
            def __init__(self,*a):owner.calls.append('construct')
            def submit(self,*a,**kw):owner.calls.append('submit')
            def reconcile(self,*a):return {'state':'generated_unverified'}
            def download(self,job,output):
                owner.calls.append('download');output.mkdir()
                shutil.copyfile(owner.media/'red.mp4',output/'clip.mp4')
                result={'files':[{'file':'clip.mp4','sha256':digest(output/'clip.mp4')}]}
                write_json(output/'downloads.json',result);return result
        self.executor=FakeExecutor
        for target,kw in [('production.comfy.Executor',{'side_effect':FakeExecutor}),
                          ('production.rental.RunpodControl',{}),
                          ('production.rental_guard.private_token',{'return_value':'synthetic'}),
                          ('production.rental_guard.guard_status',{'return_value':{'ready':True}}),
                          ('production.rental.enforce',{'return_value':{'status':'terminated_confirmed'}})]:
            p=patch(target,**kw);mock=p.start();self.addCleanup(p.stop)
            if target.endswith('.enforce'):self.cleanup=mock

    def execute(self,grant=None):
        return execute_shot(self.root,self.ident,self.request['request_id'],grant or self.grant,
            self.lease_path,self.root/'guard',self.root/'secret',execute_authorized=True)

    def prepare_image_order(self, size=(640,352), character=False):
        from PIL import Image
        path=self.root/'first-frame.png';Image.new('RGB',size,'red').save(path)
        with path.open('rb') as stream:asset=self.intake.upload('first-frame.png',stream,path.stat().st_size)
        self.order=self.intake.create({'request_id':str(uuid4()),'mode':'new_video',
            'brief':'Animate exact first frame','references':[asset['id']],
            'characters':[asset['id']] if character else []})
        self.ident=self.order['id'];prepare_order(self.root,self.ident)
        self.packet=order_evidence(self.root,self.ident)
        plan=copy.deepcopy(self.plan_request)
        plan.update(request_id=str(uuid4()),packet_sha256=self.packet['packet_sha256'])
        if character:plan['plan']['cast']={'test_actor':[asset['id']]}
        save_plan(self.root,self.ident,plan)
        self.accept.update(request_id=str(uuid4()),packet_sha256=self.packet['packet_sha256'])
        save_plan_review(self.root,self.ident,self.accept)
        self.request.update(request_id=str(uuid4()),packet_sha256=self.packet['packet_sha256'],image_asset_id=asset['id'])
        return asset

    def test_image_request_binds_reference_derivative_and_explicit_quality(self):
        from production.shots import image_file, recipe_plan
        from production.core import Runtime
        self.prepare_image_order()
        self.prepared=prepare_shot(self.root,self.ident,self.request)
        self.assertEqual(self.prepared,prepare_shot(self.root,self.ident,self.request))
        self.assertEqual(self.prepared['recipe'],'ltx25-i2v')
        plan=recipe_plan(self.prepared,'http://127.0.0.1:8188')
        self.assertEqual(plan['workflow_sha256'],self.prepared['workflow_sha256'])
        self.grant['request_sha256']=self.prepared['request_sha256']
        result=self.execute()
        review={'request_id':str(uuid4()),'output_sha256':result['output_sha256'],
                'decision':'accept_shot','checks':dict.fromkeys(CHECKS,True),'notes':'Synthetic structural test'}
        with self.assertRaisesRegex(ProductionError,'Every quality'):
            review_shot(self.root,self.ident,self.request['request_id'],review)
        review['checks']['first_frame_match']=True
        self.assertEqual(review_shot(self.root,self.ident,self.request['request_id'],review)['decision'],'accept_shot')
        path=image_file(self.root,self.ident,self.prepared,Runtime(30));path.write_bytes(b'changed')
        with self.assertRaises(ProductionError):prepare_shot(self.root,self.ident,self.request)
        with self.assertRaises(ProductionError):shot_file(self.root,self.ident,self.request['request_id'])

    def test_image_preparation_rejects_unrelated_asset_and_implicit_crop(self):
        self.prepare_image_order(size=(320,180))
        with self.assertRaisesRegex(ProductionError,'aspect ratio'):
            prepare_shot(self.root,self.ident,self.request)
        with self.assertRaisesRegex(ProductionError,'matching static'):
            prepare_shot(self.root,self.ident,dict(self.request,image_asset_id='0'*64))
        self.assertEqual(self.calls,[])

    def test_explicit_portrait_framing_preserves_full_reference_and_binds_workflow(self):
        from PIL import Image
        from production.shots import image_file, recipe_plan
        from production.core import Runtime
        self.prepare_image_order(size=(320,180))
        self.request['framing']={'width':768,'height':1344,'fit':'contain'}
        prepared=prepare_shot(self.root,self.ident,self.request)
        self.assertIn('framing_match',prepared['required_checks'])
        with Image.open(image_file(self.root,self.ident,prepared,Runtime(30))) as im:
            self.assertEqual(im.size,(768,1344))
            self.assertEqual(im.getpixel((384,0)),(0,0,0))
            self.assertEqual(im.getpixel((384,672)),(255,0,0))
        self.assertEqual(recipe_plan(prepared,'http://127.0.0.1:8188')['workflow_sha256'],prepared['workflow_sha256'])
        with self.assertRaises(ProductionError):
            prepare_shot(self.root,self.ident,dict(self.request,framing={'width':1024,'height':1024,'fit':'contain'}))
        with self.assertRaisesRegex(ProductionError,'Invalid bounded'):
            prepare_shot(self.root,self.ident,dict(self.request,request_id=str(uuid4()),framing={'width':1536,'height':1536,'fit':'contain'}))

    def test_single_character_trial_requires_cast_and_identity_review(self):
        self.prepare_image_order(character=True)
        prepared=prepare_shot(self.root,self.ident,self.request)
        self.assertIn('identity',prepared['required_checks'])
        self.assertIn('not_cross_scene',prepared['identity_scope'])
        from production.scene_revision import revision_checks
        self.assertIn('identity',revision_checks(self.root,self.ident,self.request['request_id']))
        from production.preview import approved_packet
        from production.core import Runtime
        packet,proposal=approved_packet(self.root,self.ident,self.request,Runtime(30))
        proposal=copy.deepcopy(proposal);proposal['plan'].pop('cast')
        with patch('production.shots.approved_packet',return_value=(packet,proposal)):
            with self.assertRaisesRegex(ProductionError,'explicit cast'):
                prepare_shot(self.root,self.ident,dict(self.request,request_id=str(uuid4())))

    def test_preparation_is_idempotent_and_never_spends(self):
        self.assertEqual(self.prepared,prepare_shot(self.root,self.ident,self.request))
        self.assertFalse(self.prepared['generation_authorized']);self.assertEqual(self.calls,[])
        with self.assertRaises(ProductionError):
            prepare_shot(self.root,self.ident,dict(self.request,seed=138))
        self.assertIn('shot-prepare',review_page(self.root,self.ident,'local-token'))

    def test_verified_download_repeat_does_not_submit_again_and_review_cannot_release_film(self):
        result=self.execute();self.assertEqual(result['status'],'needs_quality_review')
        self.assertEqual(self.execute(),result);self.assertEqual(self.calls.count('submit'),1)
        self.cleanup.assert_called_once()
        path=shot_file(self.root,self.ident,self.request['request_id'])
        review={'request_id':str(uuid4()),'output_sha256':digest(path),'decision':'accept_shot',
                'checks':dict.fromkeys(CHECKS,True),'notes':'Synthetic fixture review, not model quality'}
        saved=review_shot(self.root,self.ident,self.request['request_id'],review)
        self.assertFalse(saved['finished_video_accepted'])
        self.assertEqual(saved,review_shot(self.root,self.ident,self.request['request_id'],review))
        self.assertEqual(shot_state(self.root,self.ident)['quality_review'],saved)
        path.write_bytes(b'corrupt')
        with self.assertRaises(ProductionError):shot_file(self.root,self.ident,self.request['request_id'])

    def test_failed_criterion_and_wrong_output_cannot_be_accepted(self):
        result=self.execute()
        review={'request_id':str(uuid4()),'output_sha256':result['output_sha256'],'decision':'accept_shot',
                'checks':dict.fromkeys(CHECKS,False),'notes':'Geometry failed'}
        with self.assertRaises(ProductionError):review_shot(self.root,self.ident,self.request['request_id'],review)
        review.update(decision='reject_shot')
        self.assertEqual(review_shot(self.root,self.ident,self.request['request_id'],review)['decision'],'reject_shot')
        review.update(request_id=str(uuid4()),output_sha256='0'*64)
        with self.assertRaises(ProductionError):review_shot(self.root,self.ident,self.request['request_id'],review)

    def test_wrong_grant_or_revoked_plan_never_submits(self):
        with self.assertRaises(ProductionError):self.execute(dict(self.grant,request_sha256='0'*64))
        save_plan_review(self.root,self.ident,dict(self.accept,request_id=str(uuid4()),decision='request_changes'))
        with self.assertRaises(ProductionError):self.execute()
        self.assertEqual(self.calls,[])
        self.assertEqual(shot_state(self.root,self.ident)['status'],'stale_plan')

    def test_constructor_failure_and_unknown_gpu_outcome_both_cleanup(self):
        with patch('production.comfy.Executor',side_effect=ProductionError('initialization failed')):
            with self.assertRaises(ProductionError):self.execute()
        self.cleanup.assert_called_once();self.cleanup.reset_mock()
        with patch.object(self.executor,'reconcile',return_value={'state':'outcome_unknown'}):
            with self.assertRaisesRegex(ProductionError,'unknown'):self.execute()
        self.cleanup.assert_called_once()
        self.assertEqual(shot_state(self.root,self.ident)['status'],'interrupted_or_failed')

    def test_revocation_during_poll_stops_and_cleans(self):
        def revoke(*a):
            save_plan_review(self.root,self.ident,dict(self.accept,request_id=str(uuid4()),decision='request_changes'))
            return {'state':'running'}
        with patch.object(self.executor,'reconcile',side_effect=revoke):
            with self.assertRaises(ProductionError):self.execute()
        self.cleanup.assert_called_once();self.assertNotIn('download',self.calls)
