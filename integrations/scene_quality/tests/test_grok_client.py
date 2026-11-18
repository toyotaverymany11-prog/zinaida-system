import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from integrations.scene_quality.grok_client import generate


class Stream:
    headers={'x-request-id':'offline-fixture'}
    def __init__(self,complete=True):self.complete=complete
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def __iter__(self):
        yield ('data: '+json.dumps({'model':'fixture-build','choices':[{'delta':{'reasoning_content':'fixture'},'finish_reason':None}]})).encode()+b'\n'
        if self.complete:
            yield ('data: '+json.dumps({'model':'fixture-build','system_fingerprint':'fixture-fp','choices':[{'delta':{'content':'{"ok":true}'},'finish_reason':'stop'}]})).encode()+b'\n'
            yield b'data: [DONE]\n'


class ExplicitReasoningBudget(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)/'request';self.bodies=[]
        owner=self
        class Opener:
            def open(self,request,timeout):owner.bodies.append(json.loads(request.data));return Stream(owner.complete)
        self.complete=True
        self.addCleanup(patch.stopall)
        patch('integrations.scene_quality.grok_client.subscription_headers',return_value={'Content-Type':'application/json'}).start()
        patch('integrations.scene_quality.grok_client.urllib.request.build_opener',return_value=Opener()).start()

    def test_default_effort_is_explicit_and_model_revision_is_recorded(self):
        self.assertEqual(generate(self.root,'Unit fixture'),{'ok':True})
        self.assertEqual(self.bodies[0]['reasoning_effort'],'low')
        r=json.loads((self.root/'receipt.json').read_text());self.assertEqual(r['observed_models'],['fixture-build'])
        self.assertEqual(r['reasoning_chars'],7);self.assertIsNotNone(r['time_to_first_content_seconds'])

    def test_changing_effort_cannot_reuse_previous_request_identity(self):
        generate(self.root,'Unit fixture')
        with self.assertRaisesRegex(RuntimeError,'input changed'):generate(self.root,'Unit fixture',reasoning_effort='high')
        self.assertEqual(len(self.bodies),1)

    def test_incomplete_response_is_not_retried_automatically(self):
        self.complete=False
        with self.assertRaises(RuntimeError):generate(self.root,'Unit fixture')
        with self.assertRaisesRegex(RuntimeError,'Reconcile'):generate(self.root,'Unit fixture')
        self.assertEqual(len(self.bodies),1)

    def test_mutated_cached_result_is_never_a_success(self):
        generate(self.root,'Unit fixture');(self.root/'response.json').write_text('{"forged":true}')
        with self.assertRaisesRegex(RuntimeError,'changed'):generate(self.root,'Unit fixture')
        self.assertEqual(len(self.bodies),1)
