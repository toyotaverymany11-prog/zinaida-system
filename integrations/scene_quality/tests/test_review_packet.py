"""Protocol fixtures are synthetic, never evidence of a live critic."""
import json
from pathlib import Path
import tempfile
import unittest

from integrations.scene_quality.contracts import Invalid,digest
from integrations.scene_quality.supervisor import file_sha,write,current
from integrations.scene_quality.review_packet import prepare_blind,record_blind,prepare_comparison,call_preflight


class BlindReviewBoundary(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.job=Path(self.temp.name)/'job';self.job.mkdir()
        # Format qualification belongs to supervisor.prepare, not this fixture.
        (self.job/'media.mp4').write_bytes(b'synthetic-protocol-fixture')
        self.sha=file_sha(self.job/'media.mp4')
        write(self.job/'state.json',{'artifact':{'sha256':self.sha,'creator_id':'writer','duration_seconds':1},'revision':1,'review_history':[]})
        write(self.job/'creative-context.json',{'hidden_intent':'SECRET_ACTION_NOT_OBSERVED'})
        write(self.job/'technical.json',{'hints':'DO_NOT_LEAK_TO_BLIND_REVIEW'})

    def fake_result(self):
        packet=prepare_blind(self.job)
        response={'visible_events':[{'start':0,'end':1,'text':'Synthetic fixture observation'}],
                  'audible_speech':[],'uncertain':['Offline fixture, no real perception qualified']}
        path=self.job/'synthetic-response.json';write(path,response)
        execution={'status':'done','phase':'blind_observation','reviewer_id':'other-fixture',
                   'model_revision':'offline-fixture','route':'offline-fixture','provider_request_id':'offline-fixture',
                   'input_sha256':packet['input_sha256'],'artifact_sha256':self.sha,
                   'response_sha256':file_sha(path),'perception':{'transport':'native_video','raw_audio_included':True,'sampled_fps':1}}
        receipt=self.job/'synthetic-execution.json';write(receipt,execution)
        return record_blind(self.job,receipt,path)

    def comparison_context(self):
        ref=self.job/'references/ref.txt';ref.parent.mkdir();ref.write_text('Synthetic reference')
        context=json.loads((self.job/'creative-context.json').read_text())
        write(self.job/'release-input.json',{'artifact_sha256':self.sha,'creative_context_sha256':digest(context)})
        write(self.job/'review-input.json',{'reference_files':{'test':'references/ref.txt'}})

    def test_blind_packet_does_not_leak_script_technical_hints_or_local_paths(self):
        result=prepare_blind(self.job);folder=Path(result['folder'])
        self.assertEqual({p.name for p in folder.iterdir()},{'asset.mp4','request.json'})
        text=(folder/'request.json').read_text()
        for secret in ['SECRET_ACTION','DO_NOT_LEAK',str(self.job),'writer']:self.assertNotIn(secret,text)
        self.assertFalse(result['ready_for_owner']);self.assertEqual(file_sha(folder/'asset.mp4'),self.sha)

    def test_added_context_or_changed_media_invalidates_blind_packet(self):
        prepare_blind(self.job);folder=self.job/'blind-input';write(folder/'brief.json',{'leak':'secret'})
        with self.assertRaises(Invalid):prepare_blind(self.job)
        (folder/'brief.json').unlink();(folder/'asset.mp4').chmod(0o600);(folder/'asset.mp4').write_bytes(b'changed')
        with self.assertRaises(Invalid):prepare_blind(self.job)

    def test_comparison_requires_a_separate_bound_blind_result(self):
        prepare_blind(self.job);self.comparison_context()
        with self.assertRaises(OSError):prepare_comparison(self.job)
        self.fake_result();result=prepare_comparison(self.job)
        text=(self.job/'comparison-input/request.json').read_text()
        self.assertIn('SECRET_ACTION_NOT_OBSERVED',text)
        self.assertFalse(result['ready_for_owner']);self.assertFalse(result['perception_qualified'])
        self.assertIn('two_stage_review',json.loads((self.job/'review-input.json').read_text()))

    def test_blind_response_mutation_cannot_be_used_for_comparison(self):
        self.fake_result();self.comparison_context()
        record=json.loads((self.job/'blind-record.json').read_text());record['observations']['visible_events'][0]['text']='Changed'
        write(self.job/'blind-record.json',record)
        with self.assertRaises(Invalid):prepare_comparison(self.job)

    def test_no_retroactive_blind_stage_after_model_review(self):
        state=current(self.job);state['review_history']=[{'file':'synthetic'}];write(self.job/'state.json',state)
        with self.assertRaises(Invalid):prepare_blind(self.job)

    def test_missing_access_and_zero_or_expired_budget_block_before_any_call(self):
        packet=prepare_blind(self.job)
        result=call_preflight(packet,None,{'deadline_epoch':2,'remaining_usd':0,'maximum_request_usd':.1,'remaining_calls':1},now=3)
        self.assertFalse(result['ready_to_attempt']);self.assertIn('verified_reviewer_route_missing',result['blockers'])
        self.assertIn('grant_expired',result['blockers']);self.assertIn('request_not_within_current_budget',result['blockers'])
        self.assertFalse(result['model_called'])

    def test_nan_deadline_cannot_create_a_permanent_grant(self):
        packet=prepare_blind(self.job);route={'verified_access':True,'native_video':True,'raw_audio':True,'privacy_approved':True}
        result=call_preflight(packet,route,{'deadline_epoch':float('nan'),'remaining_usd':1,'maximum_request_usd':.1,'remaining_calls':1},now=3)
        self.assertFalse(result['ready_to_attempt']);self.assertFalse(result['model_called'])


if __name__=='__main__':unittest.main()
