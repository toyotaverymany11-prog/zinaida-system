import copy
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from coordination.work_registry import change,update


class RegistryTests(unittest.TestCase):
    def request(self,id='integration',scope='repo:/integrations',revision=0):
        return {'expected_revision':revision,'record':{'id':id,'owner':id,'status':'working','scopes':[scope],'branch':'branch','checkpoint':'checkpoint','next_step':'step','evidence':[],'lease_until':110}}

    def test_parent_scope_conflict_survives_expiry(self):
        state=change({'revision':0,'records':{}},self.request(),100)
        with self.assertRaisesRegex(ValueError,'scope_conflict'):
            change(state,self.request('other','repo:/integrations/media',1),200)

    def test_sibling_and_explicit_release(self):
        s=change({'revision':0,'records':{}},self.request(),100)
        r=self.request(revision=1);r['record']['status']='released';s=change(s,r,100)
        self.assertEqual(change(s,self.request('other','repo:/integrations/media',2),100)['revision'],3)

    def test_stale_writer_cannot_replace_record(self):
        with tempfile.TemporaryDirectory() as root:
            def attempt(i):
                try:return update(root,self.request(str(i),'repo:/branch'+str(i)))['revision']
                except ValueError:return 'conflict'
            with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(attempt,[1,2]))
            self.assertEqual(sorted(map(str,results)),['1','conflict'])

    def test_owner_cannot_change_and_path_must_be_canonical(self):
        s=change({'revision':0,'records':{}},self.request(),100)
        r=self.request(revision=1);r['record']['owner']='someone'
        with self.assertRaisesRegex(ValueError,'owner_mismatch'):change(s,r,100)
        r=self.request(scope='repo:/integrations/../production')
        with self.assertRaisesRegex(ValueError,'invalid_scope'):change({'revision':0,'records':{}},r,100)
