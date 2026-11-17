import tempfile
import time
import unittest
from datetime import datetime,timezone
from pathlib import Path
from unittest.mock import patch
from production.allocation import allocate_once,bind_lease,validate_intent,watch_allocation
from production.core import ProductionError,write_json


class Allocation(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        now=time.time()
        self.intent={'schema_version':1,'approved':True,'created_at_epoch':now,'terminate_at_epoch':now+120,
          'budget_usd':1,'hourly_total_usd':1,'body':{'name':'zina-video-'+'a'*32,'image':'test/image@sha256:'+'b'*64,
          'cpu':{'id':'cpu3c','vcpuCount':1},'disk':10,'ports':[],'cloud':'SECURE'}}
        write_json(self.root/'allocation.json',self.intent)
        self.pod={'id':'test123','name':self.intent['body']['name'],'createdAt':datetime.fromtimestamp(now+.1,timezone.utc).isoformat(),
          'image':self.intent['body']['image'],'cpu':{'id':'cpu3c'},'cost':.05}
    def test_lost_create_reply_never_repeats_post(self):
        from unittest.mock import Mock
        control=Mock();control.create.side_effect=ProductionError('reply lost')
        with patch('production.allocation.watcher_ready',return_value=True):
            with self.assertRaises(ProductionError):allocate_once(self.root,control)
            self.assertEqual(allocate_once(self.root,control)['status'],'reconciliation_required')
        self.assertEqual(control.create.call_count,1)
    def test_no_live_guard_means_no_create(self):
        from unittest.mock import Mock
        control=Mock()
        with self.assertRaisesRegex(ProductionError,'Pre-armed'):allocate_once(self.root,control)
        control.create.assert_not_called()
    def test_changed_intent_cannot_reuse_submission(self):
        from unittest.mock import Mock
        control=Mock();control.create.return_value=self.pod
        with patch('production.allocation.watcher_ready',return_value=True):allocate_once(self.root,control)
        self.intent['body']['disk']=11;write_json(self.root/'allocation.json',self.intent)
        with self.assertRaisesRegex(ProductionError,'intent changed'):allocate_once(self.root,control)
        self.assertEqual(control.create.call_count,1)
    def test_reconciliation_binds_original_deadline_before_watch(self):
        from unittest.mock import Mock
        control=Mock();control.matching.return_value=[self.pod]
        with patch('production.allocation.watch',return_value={'status':'terminated_confirmed'}) as watch:
            result=watch_allocation(self.root,control)
        self.assertEqual(result['status'],'terminated_confirmed');watch.assert_called_once()
        import json
        lease=json.loads((self.root/'lease.json').read_text())
        self.assertEqual(lease['terminate_at_epoch'],self.intent['terminate_at_epoch'])
    def test_wrong_or_overpriced_resource_is_cleaned_without_readiness(self):
        from unittest.mock import Mock
        control=Mock();control.matching.return_value=[dict(self.pod,cost=99)]
        with patch('production.allocation.watch') as watch,patch('production.allocation.enforce',return_value={'status':'terminated_confirmed'}) as cleanup:
            watch_allocation(self.root,control)
        watch.assert_not_called();cleanup.assert_called_once()
    def test_queue_storage_and_over_budget_rejected(self):
        for field in ('queue','mounts','templateId'):
            self.intent['body'][field]={}
            with self.assertRaises(ProductionError):validate_intent(self.intent)
            del self.intent['body'][field]
        self.intent['budget_usd']=.001
        with self.assertRaises(ProductionError):validate_intent(self.intent)
    def test_old_resource_is_not_adopted(self):
        self.pod['createdAt']=datetime.fromtimestamp(self.intent['created_at_epoch']-30,timezone.utc).isoformat()
        with self.assertRaisesRegex(ProductionError,'predates'):bind_lease(self.intent,self.pod)

    def test_rejected_resource_on_restart_never_becomes_ready(self):
        from unittest.mock import Mock
        write_json(self.root/'lease.json',bind_lease(self.intent,self.pod))
        (self.root/'allocation-cancel').touch()
        with patch('production.allocation.watch') as watch,patch('production.allocation.enforce',return_value={}) as cleanup:
            watch_allocation(self.root,Mock())
        watch.assert_not_called();cleanup.assert_called_once()
