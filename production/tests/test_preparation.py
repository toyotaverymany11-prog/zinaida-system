import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4

from production.core import ProductionError
from production.demo import make_fixture
from production.intake import Intake
from production.preparation import prepare_order
from production.media import inspect_video


class OrderPreparation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        cls.fixture=Path(cls.temp.name)/'fixture'
        make_fixture(cls.fixture)

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def setUp(self):
        self.work=tempfile.TemporaryDirectory()
        self.addCleanup(self.work.cleanup)
        self.root=Path(self.work.name)
        self.intake=Intake(self.root)

    def order(self,voice=False):
        def upload(name):
            path=self.fixture/name
            with path.open('rb') as f:return self.intake.upload(name,f,path.stat().st_size)['id']
        data={'request_id':str(uuid4()),'mode':'reference','brief':'Техническая проба',
              'references':[upload('red.mp4')]}
        if voice:data['voice']=upload('tone.wav')
        return self.intake.create(data)

    def test_repeat_reuses_verified_evidence_and_repairs_changed_evidence(self):
        order=self.order()
        with patch('production.preparation.inspect_video',wraps=inspect_video) as inspected:
            first=prepare_order(self.root,order['id'],max_samples=4)
            second=prepare_order(self.root,order['id'],max_samples=4)
            self.assertEqual(inspected.call_count,1)
            self.assertEqual(first['reference_evidence'],second['reference_evidence'])
            item=second['reference_evidence'][0]
            (self.root/item['files'][0]['path']).write_bytes(b'damaged')
            third=prepare_order(self.root,order['id'],max_samples=4)
            self.assertEqual(inspected.call_count,2)
            self.assertNotEqual(item['analysis_path'],third['reference_evidence'][0]['analysis_path'])
        self.assertEqual(third['status'],'prepared_for_review')
        self.assertEqual(third['semantic_review'],'not_performed')
        self.assertFalse(third['generation_authorized'])
        self.assertEqual(third['provider_calls'],0)

    def test_unconfigured_voice_preserves_independent_reference_work(self):
        order=self.order(voice=True)
        receipt=prepare_order(self.root,order['id'],max_samples=4)
        self.assertEqual(receipt['status'],'blocked')
        self.assertTrue(receipt['reference_evidence'])
        self.assertFalse(receipt['generation_authorized'])

    def test_cancel_is_recorded_without_starting_inspection(self):
        order=self.order()
        cancel=self.root/'cancel';cancel.touch()
        with patch('production.preparation.inspect_video') as inspected:
            with self.assertRaises(ProductionError):
                prepare_order(self.root,order['id'],cancel_file=cancel)
            inspected.assert_not_called()
        receipt=json.loads((self.root/'preparations'/order['id']/'receipt.json').read_text())
        self.assertEqual(receipt['status'],'failed_or_cancelled')

    def test_altered_source_cannot_reuse_evidence(self):
        order=self.order()
        prepare_order(self.root,order['id'],max_samples=4)
        (self.root/'assets'/order['references'][0]['id']).write_bytes(b'changed')
        with self.assertRaisesRegex(ProductionError,'changed'):
            prepare_order(self.root,order['id'],max_samples=4)


if __name__=='__main__':unittest.main()
