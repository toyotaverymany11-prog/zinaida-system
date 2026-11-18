import copy
import json
from pathlib import Path
import unittest

from integrations.scene_quality.contracts import Invalid
from integrations.scene_quality.vimax_bridge import export, executor_preflight


class ViMaxBoundary(unittest.TestCase):
    def setUp(self):
        # A real previously returned proposal; not a production-quality fixture.
        fixture = Path(__file__).parent / 'fixtures/producer-proposal.json'
        self.plan = json.loads(fixture.read_text())
        role = self.plan['scenes'][0]['cast'][0]
        line = self.plan['scenes'][0]['dialogue'][0]
        self.cast = {role['id']: dict(approval='approved', reference_sha256=role['reference_sha256'], voice_id=line['voice_id'])}
        self.layout = {'width': 576, 'height': 1024, 'fps': 24, 'scenes': {
            self.plan['scenes'][0]['id']: dict(camera_group='zinaida-room-camera-1',
                first_visible_cast=['zinaida'], last_visible_cast=['zinaida'], frames=137, variation_type='small')}}

    def test_stock_text_audio_interface_cannot_execute_frozen_voice_order(self):
        bundle = export(self.plan, self.cast, self.layout)
        result = executor_preflight(bundle, {'live_qualified': True, 'qualified_sizes': [[576,1024]]})
        self.assertFalse(result['generation_permitted'])
        self.assertIn('executor_has_text_audio_description_only', result['blockers'])
        self.assertFalse(bundle['artistic_approval'])

    def test_wide_default_does_not_override_vertical_order(self):
        self.layout.update(width=1600, height=900)
        with self.assertRaises(Invalid): export(self.plan, self.cast, self.layout)

    def test_approximately_vertical_is_not_the_ordered_9_by_16(self):
        self.layout.update(width=768, height=1344)
        with self.assertRaises(Invalid): export(self.plan, self.cast, self.layout)

    def test_unseen_or_wrong_role_is_not_inserted_into_keyframe(self):
        self.layout['scenes'][self.plan['scenes'][0]['id']]['last_visible_cast'] = ['unknown']
        with self.assertRaises(Invalid): export(self.plan, self.cast, self.layout)

    def test_fixed_voice_binding_survives_schema_export(self):
        result = export(self.plan, self.cast, self.layout)
        self.assertEqual(result['execution_bindings'][0]['dialogue'], self.plan['scenes'][0]['dialogue'])
        self.assertEqual(result['shot_descriptions'][0]['ff_vis_char_idxs'], [0])

    def test_cutting_speech_slot_and_claiming_qualification_are_blocked(self):
        self.layout['scenes'][self.plan['scenes'][0]['id']]['frames'] = 33
        with self.assertRaises(Invalid): export(self.plan, self.cast, self.layout)

