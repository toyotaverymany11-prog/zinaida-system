"""Synthetic policy/accounting contracts; these are not model quality benchmarks."""
import copy
import unittest

from production.core import ProductionError
from production.costs import choose_qualified_route, gpu_batch_cost
from production.generation import requirements, readiness, validate_character_assignment
from production.manifest import required_reviews


class GenerationPolicy(unittest.TestCase):
    def test_replacement_does_not_silently_route_to_generic_animation(self):
        order = {'mode': 'body_replace', 'characters': [{'id': 'hero-image'}]}
        route = readiness(order)
        self.assertEqual(route['primary_route'], 'self_hosted_gpu')
        self.assertFalse(route['external_api_auto_fallback'])
        self.assertFalse(route['generation_authorized'])
        self.assertEqual([c['id'] for c in route['candidates']], ['wan-animate-replacement'])
        self.assertTrue(all(not c['execution_ready'] for c in route['candidates']))
        criteria = requirements(order)['criteria']
        self.assertTrue({'identity', 'source_preservation', 'contact_and_occlusion', 'temporal'} <= set(criteria))
        self.assertEqual(readiness(dict(order, mode='face_replace'))['candidates'], [])

    def test_character_binding_cannot_mix_or_drop_reference_images(self):
        packet = {'order': {'characters': [{'id': 'a'}, {'id': 'b'}, {'id': 'c'}]}}
        validate_character_assignment({'cast': {'hero': ['a', 'b'], 'friend': ['c']}}, packet)
        for cast in ({'hero': ['a']}, {'hero': ['a', 'b'], 'friend': ['b', 'c']},
                     {'hero': ['a', 'b', 'unknown']}, {'hero': ['a', 'a', 'b', 'c']}):
            with self.assertRaises(ProductionError):
                validate_character_assignment({'cast': cast}, packet)

    def test_stylization_never_waives_temporal_identity_or_source_reviews(self):
        manifest = {'quality_profile': 'stylized', 'clips': [{'route': 'video_recast', 'characters': ['hero']}]}
        self.assertTrue({'temporal', 'identity', 'source_preservation', 'contact_and_occlusion'} <= set(required_reviews(manifest)))
        self.assertNotIn('photorealism', required_reviews(manifest))
        manifest['quality_profile'] = 'photorealistic'
        self.assertIn('photorealism', required_reviews(manifest))


class MeasuredEconomics(unittest.TestCase):
    def test_batch_includes_all_gpus_startup_idle_and_non_compute_costs(self):
        args = dict(hourly_usd='2', gpu_count=2, inference_seconds=900, startup_seconds=600,
                    idle_seconds=300, storage_usd='.1', transfer_usd='.2', review_usd='.3',
                    manual_usd='.4', accepted_seconds=10)
        result = gpu_batch_cost(**args)
        self.assertEqual(result['billed_gpu_seconds'], '3600')
        self.assertEqual(result['total_usd'], '3.0')
        self.assertEqual(result['usd_per_accepted_second'], '0.3')
        self.assertIsNone(gpu_batch_cost(**dict(args, accepted_seconds=0))['usd_per_accepted_second'])
        for change in ({'gpu_count': True}, {'idle_seconds': -1}, {'hourly_usd': 'NaN'}):
            with self.assertRaises(ProductionError):
                gpu_batch_cost(**dict(args, **change))

    def test_cheapest_quality_matched_complete_batch_wins_with_rejects_included(self):
        protocol = 'a' * 64
        def bench(ident, compute, **changes):
            data = dict(id=ident, route='self_hosted_gpu', quality_accepted=True,
                quality_protocol_sha256=protocol, evidence=['synthetic-test-receipt'],
                attempts=[dict(attempt_id=ident+'1', scene_id='scene', accepted=True,
                               accepted_seconds=10, compute_usd=compute)])
            return dict(data, **changes)
        expensive_retries = bench('cheap-hour-with-retries', '.10')
        expensive_retries['attempts'].append(dict(attempt_id='retry', accepted=False, compute_usd='2'))
        complete = bench('fast-gpu', '.80')
        cases = [expensive_retries, complete, bench('poor-quality', '.01', quality_accepted=False),
                 bench('api', '.001', route='paid_api'), bench('marketing-only', '.001', evidence=[]),
                 bench('different-test', '.001', quality_protocol_sha256='b'*64)]
        missing = bench('different-scene', '.001')
        missing['attempts'][0]['scene_id'] = 'other'
        cases.append(missing)
        result = choose_qualified_route(cases, protocol, ['scene'])
        self.assertEqual(result['selected'], 'fast-gpu')
        self.assertEqual(len(result['excluded']), 5)
        self.assertFalse(result['generation_authorized'])
        self.assertEqual(result['qualified'][1]['rejected_attempts'], 1)
        self.assertIsNone(choose_qualified_route([], protocol, ['scene'])['selected'])
        with self.assertRaises(ProductionError):
            choose_qualified_route([complete, copy.deepcopy(complete)], protocol, ['scene'])

