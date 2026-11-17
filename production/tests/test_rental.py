import copy
import json
from pathlib import Path
import tempfile
import unittest
from production.core import ProductionError,Runtime
from production.rental import enforce,validate_lease


class RentalGuard(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.receipt=Path(self.tmp.name)/'cleanup.json'
        self.pod={'id':'pod_fixture','name':'zina-video-'+'a'*32,'createdAt':'2026-01-01T00:00:00Z'}
        self.lease={'schema_version':1,'provider':'runpod','resource':dict(self.pod),
                    'budget_usd':1,'hourly_total_usd':1,'fixed_cost_usd':.1,
                    'created_at_epoch':1767225600,'terminate_at_epoch':1767225660,
                    'cleanup_allowance_seconds':60,
                    'termination_authorized':True,'shared_resource':False}
        self.calls=[]
        owner=self
        class Fake:
            def get(_,ident,runtime):owner.calls.append('GET');return owner.pod
            def terminate(_,ident,runtime):owner.calls.append('DELETE');owner.pod=None
        self.control=Fake()

    def run_guard(self,**kwargs):
        options=dict(execute_authorized=True,now=1767225670,retry_interval=.01);options.update(kwargs)
        return enforce(self.lease,self.control,self.receipt,Runtime(2),**options)

    def test_zero_budget_and_missing_permission_never_touch_provider(self):
        with self.assertRaises(ProductionError):self.run_guard(execute_authorized=False)
        self.lease['budget_usd']=0
        with self.assertRaises(ProductionError):self.run_guard()
        self.assertEqual(self.calls,[])

    def test_not_due_only_waits_and_due_requires_confirmed_absence(self):
        self.assertEqual(self.run_guard(now=1767225601)['status'],'waiting')
        self.assertEqual(self.calls,[])
        result=self.run_guard()
        self.assertEqual(result['status'],'terminated_confirmed')
        self.assertEqual(self.calls,['GET','DELETE','GET'])
        self.run_guard()
        self.assertEqual(self.calls.count('DELETE'),1)

    def test_lost_delete_response_is_reconciled_without_second_delete(self):
        def lost(ident,runtime):
            self.calls.append('DELETE');self.pod=None;raise ProductionError('response lost')
        self.control.terminate=lost
        self.assertTrue(self.run_guard()['provider_absence_confirmed'])
        self.assertEqual(self.calls.count('DELETE'),1)

    def test_foreign_or_changed_resource_is_never_deleted(self):
        self.pod['name']='a-shared-service'
        with self.assertRaises(ProductionError):self.run_guard()
        self.assertNotIn('DELETE',self.calls)
        self.assertEqual(json.loads(self.receipt.read_text())['status'],'ownership_mismatch')

    def test_provider_failure_stops_after_bounded_attempts_without_false_success(self):
        def unavailable(ident,runtime):self.calls.append('DELETE');raise ProductionError('unavailable')
        self.control.terminate=unavailable
        with self.assertRaises(ProductionError):self.run_guard()
        receipt=json.loads(self.receipt.read_text())
        self.assertEqual(receipt['status'],'cleanup_unconfirmed')
        self.assertFalse(receipt['provider_absence_confirmed'])
        self.assertEqual(self.calls.count('DELETE'),5)

    def test_lifetime_and_ownership_cannot_silently_change(self):
        for key,value in [('budget_usd',.001),('shared_resource',True),('created_at_epoch',1767225650)]:
            bad=copy.deepcopy(self.lease);bad[key]=value
            with self.assertRaises(ProductionError):validate_lease(bad)
        self.run_guard()
        self.lease['terminate_at_epoch']+=1
        with self.assertRaises(ProductionError):self.run_guard()
