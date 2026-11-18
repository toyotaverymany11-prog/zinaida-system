"""Business failures at the pult boundary. Passing models here are explicit test doubles."""
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
from uuid import uuid4

from integrations.scene_quality.contracts import Invalid, digest
from integrations.scene_quality.qualification import SCOPES
from integrations.scene_quality.release import bind, guard
from integrations.scene_quality.supervisor import prepare, apply_review, file_sha, write
from integrations.scene_quality.tests.test_qualification import bundle


class ReleaseFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.shared=tempfile.TemporaryDirectory();cls.movie=Path(cls.shared.name)/'one-second.mp4'
        subprocess.run(['ffmpeg','-v','error','-y','-f','lavfi','-i','color=gray:s=256x144:r=24:d=1','-c:v','libx264','-pix_fmt','yuv420p',str(cls.movie)],check=True)

    @classmethod
    def tearDownClass(cls):cls.shared.cleanup()

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.quality=self.root/'quality';self.quality.mkdir()
        self.movie=self.root/'master.mp4';shutil.copyfile(type(self).movie,self.movie)
        self.project=self.root/'project.zip';self.project.write_bytes(b'unit-test-project')
        self.ledger={'rejections':[]};self.ledger_path=self.quality/'owner-rejections.json';write(self.ledger_path,self.ledger)
        self.rules={'schema_version':1,'required_scopes':list(SCOPES),'publication_authorized':False,'reference_files':{}}
        for key,name in [('brand_reference_sha256','brand.mp4'),('cast_manifest_sha256','cast.json'),('direction_rules_sha256','rules.md')]:
            f=self.quality/name;f.write_text('trusted-unit-control-'+key);self.rules[key]=file_sha(f);self.rules['reference_files'][key]=name
        write(self.quality/'cast.json',{'fixture':{'approval':'approved','reference_sha256':'c'*64,'voice_id':'fixture-voice'}})
        self.rules['cast_manifest_sha256']=file_sha(self.quality/'cast.json')
        write(self.quality/'policy.json',self.rules)
        self.sha=file_sha(self.movie);self.job=self.quality/self.sha
        self.state=prepare(self.job,self.movie,'fixture-director',self.ledger)
        scene={k:'Explicit unit-test staging' for k in ['action','new_information','performance','location_id',
             'light_direction','first_frame','last_frame','camera_position','camera_movement','camera_reason']}
        scene.update(id='fixture-scene',duration_seconds=1,cast=[{'id':'fixture','reference_sha256':'c'*64}],
                     dialogue=[],continuity={'prop':'gray test plate'})
        self.context={k:'Synthetic unit-test proposal, no artistic claim' for k in ['audience','viewer_promise','emotional_change','visible_turn','ending_action']}
        self.context['scenes']=[scene]
        bind(self.quality,self.job,self.movie,self.project,self.context)

    def approve_fixture(self):
        b=bundle();ident=b['identity'];cap=dict(ident,visual_input_qualified=True,temporal_input_qualified=True,
            audio_perception_qualified=True,calibrated_on_heldout_controls=True,calibration_sha256=digest(b))
        e=dict(cap,artifact_sha256=self.sha,tool_calls=0,input_binding_sha256=file_sha(self.job/'review-input.json'),
               reference_policy_sha256=digest(self.rules),coverage_complete=True,
               coverage={'artifact_sha256':self.sha,'start':0,'end':self.state['artifact']['duration_seconds'],'scope':'continuous_audiovisual'})
        review={'artifact_sha256':self.sha,'verdict':'pass_candidate','findings':[]}
        apply_review(self.job,review,e,cap,self.ledger,1)
        write(self.job/'reviewer-capability.json',cap);write(self.job/'calibration.json',b)

    def check(self):return guard(self.quality,self.movie,self.project,self.ledger,now=1001)

    def test_unreviewed_decode_success_does_not_open_delivery(self):
        self.assertFalse(self.check()['allowed_as_owner_candidate'])

    def test_exact_calibrated_test_double_can_open_candidate_but_never_publication(self):
        self.approve_fixture();r=self.check();self.assertTrue(r['allowed_as_owner_candidate']);self.assertFalse(r['publication_authorized']);self.assertFalse(r['owner_artistic_approval'])

    def test_forged_ready_flag_without_qualified_execution_is_denied(self):
        s=json.loads((self.job/'state.json').read_text());s.update(status='candidate_for_owner',ready_for_owner=True);write(self.job/'state.json',s)
        self.assertFalse(self.check()['allowed_as_owner_candidate'])

    def test_owner_denial_wins_even_after_pass(self):
        self.approve_fixture();self.ledger['rejections'].append({'artifact_sha256':self.sha,'source':'owner','reason':'wrong wrist'})
        self.assertFalse(self.check()['allowed_as_owner_candidate'])

    def test_changed_project_and_references_revoke_ready_movie(self):
        self.approve_fixture();self.project.write_bytes(b'other-project');self.assertFalse(self.check()['allowed_as_owner_candidate'])
        self.project.write_bytes(b'unit-test-project');(self.quality/'brand.mp4').write_text('new reference')
        self.assertFalse(self.check()['allowed_as_owner_candidate'])

    def test_even_updated_policy_needs_new_review_after_reference_change(self):
        self.approve_fixture();f=self.quality/'rules.md';f.write_text('new camera rule');self.rules['direction_rules_sha256']=file_sha(f);write(self.quality/'policy.json',self.rules)
        self.assertFalse(self.check()['allowed_as_owner_candidate'])

    def test_wrong_model_or_mutated_calibration_cannot_inherit_approval(self):
        self.approve_fixture();b=json.loads((self.job/'calibration.json').read_text());b['identity']['model_revision']='another';write(self.job/'calibration.json',b)
        self.assertFalse(self.check()['allowed_as_owner_candidate'])

    def test_changed_movie_does_not_inherit_old_release(self):
        self.approve_fixture();self.movie.write_bytes(b'different movie');self.assertFalse(self.check()['allowed_as_owner_candidate'])

    def test_changed_script_and_frozen_cast_revoke_release(self):
        self.approve_fixture();f=self.job/'creative-context.json';x=json.loads(f.read_text());x['ending_action']='different ending';write(f,x)
        self.assertFalse(self.check()['allowed_as_owner_candidate'])

    def test_wrong_cast_cannot_be_bound_before_review(self):
        x=copy.deepcopy(self.context);x['scenes'][0]['cast'][0]['reference_sha256']='d'*64
        with self.assertRaises(Invalid):bind(self.quality,self.job,self.movie,self.project,x)

    def test_symlinked_calibration_is_not_a_trusted_record(self):
        self.approve_fixture();p=self.job/'calibration.json';target=self.root/'outside.json';p.rename(target);p.symlink_to(target)
        self.assertFalse(self.check()['allowed_as_owner_candidate'])

    def test_cli_denial_has_nonzero_exit_status(self):
        r=subprocess.run([sys.executable,'-m','integrations.scene_quality.release','guard','--root',str(self.quality),
            '--video',str(self.movie),'--project',str(self.project),'--ledger',str(self.ledger_path)],capture_output=True,text=True)
        self.assertEqual(r.returncode,3);self.assertFalse(json.loads(r.stdout)['allowed_as_owner_candidate'])

    def test_read_only_release_import_does_not_start_scientific_runtime(self):
        script="import sys;from integrations.scene_quality.release import guard;assert not {'numpy','torch','cv2'}.intersection(sys.modules)"
        r=subprocess.run([sys.executable,'-c',script],capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stderr)

    def producer(self):
        adapter=Path(__file__).resolve().parents[2]/'megamozg';sys.path.insert(0,str(adapter));self.addCleanup(lambda:sys.path.remove(str(adapter)))
        import video_scene_producer
        self.link={'task_id':str(uuid4()),'task_revision':1,'owner_id':str(uuid4()),'order_id':str(uuid4()),'order_fingerprint':'a'*64}
        fake=types.ModuleType('production.scene_revision');fake.revision_file=lambda root,order,request,revision,kind:self.movie if kind=='video' else self.project
        self.addCleanup(patch.stopall)
        patch.dict(sys.modules,{'production.scene_revision':fake}).start()
        patch.object(video_scene_producer,'collect',return_value={'state':'observed'}).start()
        # The adapter uses the real gate with a deterministic calibration clock.
        patch('integrations.scene_quality.release.time.time',return_value=1001).start()
        return video_scene_producer.scene_producer(self.root,self.link,'request',['b'*64],quality_root=self.quality,quality_ledger=self.ledger_path)

    def test_pult_hides_unreviewed_revision_and_blocks_video_and_zip(self):
        p=self.producer();self.assertEqual(p(self.link,None,'catalog')['versions'],[])
        for kind in ['video','project']:
            with self.assertRaises(ValueError):p(self.link,'b'*64,kind)

    def test_pult_delivers_only_exact_passed_bytes(self):
        self.approve_fixture();p=self.producer();self.assertEqual(len(p(self.link,None,'catalog')['versions']),1)
        self.assertEqual(p(self.link,'b'*64,'video')['data'],self.movie.read_bytes())
        self.assertEqual(p(self.link,'b'*64,'project')['data'],self.project.read_bytes())

    def test_owner_rejection_during_read_revokes_download(self):
        self.approve_fixture();p=self.producer();original=os.read
        def read_and_revoke(fd,size):
            data=original(fd,size)
            write(self.ledger_path,{'rejections':[{'artifact_sha256':self.sha,'source':'owner','reason':'late refusal'}]})
            return data
        with patch('video_scene_producer.os.read',side_effect=read_and_revoke):
            with self.assertRaises(ValueError):p(self.link,'b'*64,'video')
