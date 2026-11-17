import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from production.core import Cancelled, ProductionError, Runtime
from production.recipes import ltx25_plan, verify_ltx25_weights


class RecipeContracts(unittest.TestCase):
    def test_real_comfy_v3_flattened_inputs_and_model_inventory(self):
        from production.comfy import inventory_errors
        fields = {
            'model_name':['COMBO',{'options':['model.safetensors']}],
            'values':['COMFY_AUTOGROW_V3',{'template':{'names':['a','b'],'min':1}}],
            'format':['COMFY_DYNAMICCOMBO_V3',{'options':[{'key':'auto','inputs':{
                'required':{'codec':['COMBO',{'options':['auto']}]}}}]}],
        }
        inputs={'model_name':'model.safetensors','values.a':['1',0],
                'format':'auto','format.codec':'auto'}
        self.assertEqual(inventory_errors(inputs,fields,{'1':{}}),[])
        for change in ({'model_name':'missing.safetensors'},{'format.codec':'unknown'}):
            self.assertTrue(inventory_errors(dict(inputs,**change),fields,{'1':{}}))
        missing=dict(inputs);del missing['values.a']
        self.assertTrue(inventory_errors(missing,fields,{'1':{}}))
        fields['model_name'][1]['options']=[]
        self.assertTrue(inventory_errors(inputs,fields,{'1':{}}))

    def test_plan_is_reproducible_and_remains_unqualified(self):
        args = ('A blue cube.', 42, 'ltx-test', 'http://127.0.0.1:8188')
        plan = ltx25_plan(*args)
        self.assertEqual(plan['workflow_sha256'], ltx25_plan(*args)['workflow_sha256'])
        changed = ltx25_plan('A red cube.', *args[1:])
        self.assertNotEqual(plan['workflow_sha256'], changed['workflow_sha256'])
        self.assertFalse(plan['generation_authorized'])
        self.assertFalse(plan['gpu_qualified'])
        self.assertEqual(len(plan['required_models']), 5)
        classes = set(plan['node_classes'])
        self.assertNotIn('TextGenerateLTX2Prompt', classes)
        self.assertNotIn('ComfySwitchNode', classes)
        self.assertEqual(plan['workflow']['405:339']['inputs']['noise_seed'], 42)
        for prompt, seed in (('', 42), ('x', True), ('x', 1.2), ('x', 2**53)):
            with self.assertRaises(ProductionError):
                ltx25_plan(prompt, seed, *args[2:])

    def test_weight_validation_rejects_same_size_corruption_and_can_stop(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root/'model.bin'
            path.write_bytes(b'good')
            spec = {'models':[{'path':'model.bin','bytes':4,
                               'sha256':hashlib.sha256(b'good').hexdigest()}]}
            with patch('production.recipes.read_json',return_value=spec):
                self.assertEqual(verify_ltx25_weights(root, Runtime(5))['status'],'weights_verified')
                path.write_bytes(b'evil')
                self.assertEqual(verify_ltx25_weights(root, Runtime(5))['models'][0]['status'],'sha_mismatch')
                path.unlink()
                self.assertEqual(verify_ltx25_weights(root, Runtime(5))['models'][0]['status'],'missing')
                with self.assertRaises(Cancelled):
                    verify_ltx25_weights(root, Runtime(5, should_cancel=lambda:True))

    def test_changed_pinned_graph_cannot_be_prepared(self):
        from production import recipes
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for name in ('ltx25-t2v.api.json','ltx25-t2v.lock.json'):
                (root/name).write_bytes((recipes.WORKFLOWS/name).read_bytes())
            path=root/'ltx25-t2v.api.json'
            graph=json.loads(path.read_text())
            graph['405:383']={'class_type':'PrimitiveBoolean','inputs':{'value':True}}
            path.write_text(json.dumps(graph))
            with patch('production.recipes.WORKFLOWS',root):
                with self.assertRaises(ProductionError):
                    ltx25_plan('A cube.',42,'ltx-test','http://127.0.0.1:8188')
