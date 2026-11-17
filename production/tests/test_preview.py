import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4

from PIL import Image
from production.core import Cancelled, ProductionError, Runtime, digest
from production.demo import make_fixture
from production.intake import Intake
from production.planning import order_evidence, save_plan, save_plan_review
from production.preparation import prepare_order
from production.preview import (PreviewInterrupted, cancel_preview, preview_file,
    preview_manifest, preview_state, render_preview, request_preview)
from production.media import ffmpeg


class SourcePreview(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture_tmp=tempfile.TemporaryDirectory();cls.fixture=Path(cls.fixture_tmp.name)/'sources'
        make_fixture(cls.fixture)

    @classmethod
    def tearDownClass(cls):cls.fixture_tmp.cleanup()

    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.intake=Intake(self.root,enqueue=True)
        ids=[]
        for name in ('red.mp4','blue.mp4'):
            path=self.fixture/name
            with path.open('rb') as f:ids.append(self.intake.upload(name,f,path.stat().st_size)['id'])
        self.order=self.intake.create({'request_id':str(uuid4()),'mode':'reference','brief':'Preview only','references':ids})
        self.ident=self.order['id'];prepare_order(self.root,self.ident,max_samples=2)
        with self.intake.connect() as db:db.execute("UPDATE preparation_jobs SET status='awaiting_review' WHERE order_id=?",(self.ident,))
        self.packet=order_evidence(self.root,self.ident)
        scenes=[dict(source={'asset_id':asset,'start':0,'end':1},observation='Source color',
                     action='Keep interval',preserve=['color'],change=['Only reorder the existing clips'],checks=['timing']) for asset in reversed(ids)]
        self.plan_request={'request_id':str(uuid4()),'expected_revision':0,'packet_sha256':self.packet['packet_sha256'],
            'plan':{'author':'synthetic-test','summary':'Reorder blue then red','scenes':scenes,'open_questions':[]}}
        self.plan=save_plan(self.root,self.ident,self.plan_request)
        self.review={'request_id':str(uuid4()),'expected_revision':1,'packet_sha256':self.packet['packet_sha256'],
            'decision':'accept_plan','notes':'Synthetic structural test only'}
        save_plan_review(self.root,self.ident,self.review)
        self.request={key:self.review[key] for key in ('expected_revision','packet_sha256')}
        self.request['request_id']=str(uuid4())

    def queued(self):return request_preview(self.root,self.ident,self.request)

    def ready(self):
        with self.intake.connect() as db:db.execute("UPDATE preparation_jobs SET preview_status='ready' WHERE order_id=?",(self.ident,))

    def test_real_cut_order_duration_and_completed_recovery_without_rendering(self):
        self.queued();rid=self.request['request_id']
        result=render_preview(self.root,self.ident,rid,timeout=45);self.ready()
        self.assertFalse(result['generation_authorized']);self.assertFalse(result['finished_video_accepted'])
        self.assertAlmostEqual(float(result['duration']),2,places=1)
        path=preview_file(self.root,self.ident,rid)
        from production.media import release_check
        with self.assertRaisesRegex(ProductionError,'previews cannot be released'):
            release_check(json.loads((path.parent/'manifest.json').read_text()),self.root,path.parent,[])
        for second,channel in ((.4,2),(1.4,0)):
            still=self.root/f'{second}.png'
            Runtime(5).run(ffmpeg('-ss',second,'-i',path,'-frames:v',1,still))
            with Image.open(still) as im:self.assertGreater(im.getpixel((100,100))[channel],220)
        receipt=path.parents[1]/'receipt.json'
        data=json.loads(receipt.read_text());data['state']='rendering';receipt.write_text(json.dumps(data))
        with patch('production.media.render') as renderer:
            resumed=render_preview(self.root,self.ident,rid,recover_only=True)
            renderer.assert_not_called();self.assertEqual(resumed['output_sha256'],digest(path))
        path.write_bytes(b'corrupted')
        with self.assertRaises(ProductionError):preview_file(self.root,self.ident,rid)

    def test_plan_change_or_revoked_decision_blocks_stale_output(self):
        self.queued();rid=self.request['request_id'];render_preview(self.root,self.ident,rid);self.ready()
        revoked=dict(self.review,request_id=str(uuid4()),decision='request_changes')
        save_plan_review(self.root,self.ident,revoked)
        with self.assertRaises(ProductionError):preview_file(self.root,self.ident,rid)
        newer=copy.deepcopy(self.plan_request);newer.update(request_id=str(uuid4()),expected_revision=1)
        save_plan(self.root,self.ident,newer)
        with self.assertRaises(ProductionError):render_preview(self.root,self.ident,rid)

    def test_duplicate_delivery_and_cancel_do_not_requeue(self):
        self.queued();cancel_preview(self.root,self.ident)
        self.queued();self.assertEqual(preview_state(self.root,self.ident)['status'],'cancelled')
        with self.assertRaises(ProductionError):
            request_preview(self.root,self.ident,dict(self.request,expected_revision=2))
        with self.assertRaises(Cancelled):
            render_preview(self.root,self.ident,self.request['request_id'],should_cancel=lambda:True)

    def test_incomplete_attempt_never_restarts_implicitly(self):
        self.queued();rid=self.request['request_id']
        with patch('production.media.render',side_effect=RuntimeError('interrupted')):
            with self.assertRaises(RuntimeError):render_preview(self.root,self.ident,rid)
        with patch('production.media.render') as renderer:
            with self.assertRaises(PreviewInterrupted):render_preview(self.root,self.ident,rid,recover_only=True)
            renderer.assert_not_called()

    def test_unavailable_generated_scene_is_not_replaced_with_reference(self):
        proposal=copy.deepcopy(self.plan);proposal['plan']['scenes'][0]['source']=None
        with self.assertRaisesRegex(ProductionError,'generated scenes are unavailable'):
            preview_manifest(self.packet,proposal)
