import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4

from production.core import ProductionError, digest
from production.demo import make_fixture
from production.intake import Intake
from production.local_transcription import transcribe
from production.planning import latest_plan, order_evidence, review_page, save_plan
from production.preparation import prepare_order


class ScenePlanning(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture_dir = tempfile.TemporaryDirectory()
        cls.fixture = Path(cls.fixture_dir.name) / 'media'
        make_fixture(cls.fixture)

    @classmethod
    def tearDownClass(cls):
        cls.fixture_dir.cleanup()

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        self.intake = Intake(self.root)
        path = self.fixture / 'red.mp4'
        with path.open('rb') as stream:
            self.asset = self.intake.upload(path.name, stream, path.stat().st_size)
        self.order = self.intake.create({'request_id': str(uuid4()), 'mode': 'reference',
            'brief': '<script>must remain text</script>', 'references': [self.asset['id']]})
        prepare_order(self.root, self.order['id'], max_samples=2)
        self.packet = order_evidence(self.root, self.order['id'])
        self.request = {'request_id': str(uuid4()), 'expected_revision': 0,
            'packet_sha256': self.packet['packet_sha256'],
            'plan': {'author': 'technical-test', 'summary': 'Красный технический фрагмент',
                'open_questions': ['Художественный референс отсутствует'],
                'scenes': [{'source': {'asset_id': self.asset['id'], 'start': 0,
                    'end': self.packet['references'][0]['duration_seconds']},
                    'observation': 'Красный технический кадр',
                    'action': 'Сохранить исходный фрагмент',
                    'preserve': ['Длительность'], 'change': ['Изменения не заданы'],
                    'checks': ['Сверить длительность с исходником']}]}}

    def test_plan_is_revisioned_idempotent_and_grants_no_execution(self):
        result = save_plan(self.root, self.order['id'], self.request)
        self.assertEqual(save_plan(self.root, self.order['id'], self.request), result)
        self.assertFalse(result['generation_authorized'])
        self.assertEqual(result['semantic_review'], 'pending')
        self.assertEqual(result['generation_readiness']['primary_route'], 'self_hosted_gpu')
        self.assertFalse(result['production_requirements']['external_api_auto_fallback'])
        self.assertIn('photorealism', result['production_requirements']['criteria'])
        conflict = dict(self.request, request_id=str(uuid4()))
        with self.assertRaisesRegex(ProductionError, 'revision changed'):
            save_plan(self.root, self.order['id'], conflict)
        newer = dict(conflict, expected_revision=1)
        self.assertEqual(save_plan(self.root, self.order['id'], newer)['revision'], 2)
        page = review_page(self.root, self.order['id'])
        self.assertIn('Версия 2', page)
        self.assertNotIn('<script>', page)
        self.assertIn('&lt;script&gt;', page)

    def test_changed_evidence_rejects_plan_and_media(self):
        file = self.root / self.packet['media'][0]['path']
        file.write_bytes(b'corrupt')
        with self.assertRaisesRegex(ProductionError, 'changed'):
            save_plan(self.root, self.order['id'], self.request)
        prepare_order(self.root, self.order['id'], max_samples=2)
        with self.assertRaisesRegex(ProductionError, 'Evidence changed'):
            save_plan(self.root, self.order['id'], self.request)

    def test_unknown_source_and_time_and_authorization_are_rejected(self):
        for mutate in (
            lambda r: r['plan']['scenes'][0]['source'].update(end=100000),
            lambda r: r['plan']['scenes'][0]['source'].update(asset_id='missing'),
            lambda r: r['plan'].update(generation_authorized=True),
        ):
            request = copy.deepcopy(self.request)
            mutate(request)
            with self.assertRaises(ProductionError):
                save_plan(self.root, self.order['id'], request)

    def test_replacement_requires_full_original_timing(self):
        from production.planning import validate_plan
        packet = copy.deepcopy(self.packet)
        packet['order']['mode'] = 'body_replace'
        validate_plan(self.request['plan'], packet)
        shortened = copy.deepcopy(self.request['plan'])
        shortened['scenes'][0]['source']['end'] /= 2
        with self.assertRaisesRegex(ProductionError, 'full reference'):
            validate_plan(shortened, packet)

    def test_tampered_transcript_is_recomputed_and_old_bytes_retained(self):
        path = self.fixture / 'tone.wav'
        with path.open('rb') as stream:
            voice = self.intake.upload(path.name, stream, path.stat().st_size)
        order = self.intake.create({'request_id': str(uuid4()), 'mode': 'new_video', 'voice': voice['id']})
        folder = self.root / 'transcripts'
        folder.mkdir()
        target = folder / (order['id'] + '.json')
        original = {'order_id': order['id'], 'source_sha256': voice['id'], 'model': 'tiny', 'text': 'original'}
        target.write_text(json.dumps(original))
        expected = digest(target)
        target.write_text(json.dumps(dict(original, text='tampered')))
        model = self.root / 'tiny.pt'
        model.write_bytes(b'test-model')
        with patch.dict('production.local_transcription.MODEL_SHA', {'tiny': digest(model)}):
            with patch('production.local_transcription.Runtime.run', return_value='{"text":"restored"}'):
                with patch('production.local_transcription.probe', return_value={'format':{'duration':1}}):
                    report = transcribe(self.root, order['id'], Path('/unused'), model, model='tiny',
                                        expected_sha256=expected)
        self.assertEqual(report['text'], 'restored')
        self.assertIn('tampered', next((folder/'history').glob('*.json')).read_text())
        self.assertEqual(target.with_suffix('.sha256').read_text().strip(), digest(target))
