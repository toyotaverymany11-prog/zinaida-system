import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4
from production.core import object_digest,write_json,ProductionError
from integrations.scene_quality.intake_app import CurrentReceiptIntake


class CurrentOrderReceipt(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.intake=CurrentReceiptIntake(self.root,enqueue=True)
        self.order=self.intake.create({'request_id':str(uuid4()),'mode':'new_video','brief':'Explicit unit fixture'})
        self.ident=self.order['id'];self.receipt=self.root/'preparations'/self.ident/'receipt.json'
        write_json(self.receipt,{'order_sha256':object_digest(self.order),'status':'prepared_for_review',
                                'reference_evidence':[{'source':'synthetic-reference'}],'blocker':None})

    def test_derived_analysis_status_does_not_hide_preparation(self):
        result=self.intake.orders()[0]
        self.assertIn('analysis',result);self.assertEqual(result['preparation']['reference_count'],1)
        self.assertEqual(result['preparation']['status'],'queued')

    def test_changing_original_brief_revokes_old_receipt(self):
        with self.intake.connect() as db:
            raw=json.loads(db.execute('SELECT data FROM orders WHERE id=?',(self.ident,)).fetchone()[0])
            raw['brief']='Changed original';db.execute('UPDATE orders SET data=? WHERE id=?',(json.dumps(raw),self.ident))
        result=self.intake.orders()[0];self.assertNotIn('reference_count',result['preparation'])

    def test_reading_display_metadata_does_not_rewrite_order(self):
        with self.intake.connect() as db:before=db.execute('SELECT data FROM orders WHERE id=?',(self.ident,)).fetchone()[0]
        self.intake.orders()
        with self.intake.connect() as db:after=db.execute('SELECT data FROM orders WHERE id=?',(self.ident,)).fetchone()[0]
        self.assertEqual(before,after)

    def test_changed_backend_requires_requalification(self):
        with patch('integrations.scene_quality.intake_app.ORDERS_IMPLEMENTATION','0'*64):
            with self.assertRaises(ProductionError):self.intake.orders()
