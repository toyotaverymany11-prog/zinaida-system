import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4

spec=importlib.util.spec_from_file_location('grok_subscription',Path(__file__).parents[1]/'megamozg/grok_subscription.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


class SubscriptionTests(unittest.TestCase):
    def test_repeat_and_changed_prompt_never_post_twice(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(m,'credentials',return_value='synthetic'),patch.object(m,'api',return_value={'request_id':str(uuid4())}) as api:
            first=m.submit(tmp,'unused','cube');self.assertEqual(first['state'],'submitted');self.assertEqual(m.submit(tmp,'unused','cube'),first)
            with self.assertRaises(ValueError):m.submit(tmp,'unused','different cube')
            self.assertEqual(api.call_count,1)

    def test_lost_response_is_unknown_and_cannot_repeat(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(m,'credentials',return_value='synthetic'),patch.object(m,'api',side_effect=TimeoutError) as api:
            self.assertEqual(m.submit(tmp,'unused','cube')['state'],'unknown');m.submit(tmp,'unused','cube');self.assertEqual(api.call_count,1)
            with self.assertRaises(ValueError):m.resume(tmp,'unused')

    def test_api_key_only_auth_does_not_qualify(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'auth.json';p.write_text(json.dumps({'api_key':'synthetic-key'}))
            with self.assertRaisesRegex(ValueError,'subscription_reauthentication_required'):m.credentials(p)
