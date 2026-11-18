import copy
import unittest
from integrations.scene_quality.contracts import Invalid, validate_review, correction_tasks
from integrations.scene_quality.workflow import build, check_runtime_nodes


class QualityContracts(unittest.TestCase):
    def setUp(self):
        self.artifact={'sha256':'a'*64,'duration_seconds':5,'creator_id':'director'}
        self.execution={'artifact_sha256':'a'*64,'reviewer_id':'independent','tool_calls':0,
            'visual_input_qualified':True,'temporal_input_qualified':True,
            'audio_perception_qualified':True,'coverage_complete':True,
            'calibrated_on_heldout_controls':True}
        self.review={'artifact_sha256':'a'*64,'verdict':'pass_candidate','findings':[]}

    def test_technical_success_cannot_replace_audiovisual_review(self):
        self.execution['audio_perception_qualified']=False
        self.assertFalse(validate_review(self.review,self.artifact,self.execution)['ready_for_owner'])

    def test_uncalibrated_model_cannot_pass_new_films(self):
        self.execution['calibrated_on_heldout_controls']=False
        self.assertFalse(validate_review(self.review,self.artifact,self.execution)['ready_for_owner'])

    def test_review_of_old_version_is_invalid(self):
        self.review['artifact_sha256']='b'*64
        with self.assertRaises(Invalid):validate_review(self.review,self.artifact,self.execution)

    def test_creator_cannot_approve_self(self):
        self.execution['reviewer_id']='director'
        with self.assertRaises(Invalid):validate_review(self.review,self.artifact,self.execution)

    def test_critical_finding_blocks_even_when_model_says_pass(self):
        self.review['findings']=[dict(start=1,end=2,stage='speech',severity='critical',
            expected='Exact approved line',observed='Different line',evidence='Word missing at1s',
            change='Recreate exact speech-driven take',recheck='Compare voice and mouth timing',modality='audio')]
        result=validate_review(self.review,self.artifact,self.execution)
        self.assertEqual(result['status'],'needs_rework')
        tasks=correction_tasks(self.review,0)
        self.assertEqual(tasks['tasks'][0]['stage'],'speech')
        self.assertEqual(correction_tasks(self.review,2)['status'],'iteration_limit_reached')

    def test_stills_cannot_justify_motion_claim(self):
        self.execution['temporal_input_qualified']=False
        self.review['findings']=[dict(start=0,end=1,stage='camera',severity='major',expected='Parallax',
            observed='No parallax',evidence='One still',change='Reshoot',recheck='Temporal proof',modality='motion')]
        with self.assertRaises(Invalid):validate_review(self.review,self.artifact,self.execution)

    def test_finding_outside_actual_file_rejected(self):
        self.review['findings']=[dict(start=4,end=8,stage='camera',severity='major',expected='x',observed='x',evidence='x',change='x',recheck='x')]
        with self.assertRaises(Invalid):validate_review(self.review,self.artifact,self.execution)

    def test_passing_candidate_does_not_authorize_publication(self):
        result=validate_review(self.review,self.artifact,self.execution)
        self.assertTrue(result['ready_for_owner'])
        self.assertFalse(result['publication_authorized'])
        self.assertFalse(result['artistic_owner_approval'])


class AudioDrivenWorkflow(unittest.TestCase):
    def make(self,**kw):return build('Specific natural performance','actor.png','a'*64,'speech.wav','b'*64,**kw)

    def test_original_audio_frozen_in_both_stages_and_preserved_at_output(self):
        g,b=self.make()
        for node in ['398:377','398:340']:
            self.assertEqual(g[node]['inputs']['audio_latent'],['sq_frozen_audio',0])
        self.assertEqual(g['sq_zero_noise']['inputs']['value'],0)
        self.assertEqual(g['398:370']['inputs']['audio'],['sq_trim_audio',0])
        self.assertNotIn('LTXVAudioVAEDecode',{n['class_type'] for n in g.values()})
        self.assertEqual(b['status'],'prepared_gpu_unqualified')

    def test_wrong_dimension_or_timing_rejected_before_gpu(self):
        for kw in [dict(width=777),dict(frames=120),dict(width=1536,height=1536),dict(fps=30)]:
            with self.assertRaises(Invalid):self.make(**kw)

    def test_media_traversal_rejected(self):
        with self.assertRaises(Invalid):build('x','../x.png','a'*64,'speech.wav','b'*64)

    def test_missing_runtime_node_blocks_submission(self):
        g,_=self.make()
        with self.assertRaises(Invalid):check_runtime_nodes(g,{})


if __name__=='__main__':unittest.main()
