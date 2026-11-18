import copy
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from integrations.scene_quality.contracts import Invalid
from integrations.scene_quality.preflight import assess
from integrations.scene_quality.trial_runner import cold_start_check
from integrations.scene_quality.supervisor import (
    apply_review, begin_revision, current, delivery_guard, file_sha, prepare, write,
)


class ColdStartBudget(unittest.TestCase):
    def plan(self):
        return dict(grant_deadline_epoch=10000, remaining_budget_usd=5,
                    hourly_total_ceiling_usd=5, bootstrap_seconds=600,
                    model_bytes_to_transfer=39709872236, disk_available_bytes=140_000_000_000,
                    disk_required_bytes=100_000_000_000, inference_seconds=720,
                    review_seconds=600, cleanup_seconds=150, safety_seconds=120,
                    allocation_seconds=60, transfer_safety_factor=1.25,
                    measurement_ttl_seconds=1800, measured_bytes_per_second=38362253,
                    transfer_measured_at_epoch=8000, independent_cleanup_qualified=True)

    def test_real_cold_start_cannot_fit_original_43_minute_grant(self):
        plan = self.plan(); plan['grant_deadline_epoch'] = 10580
        result = assess(plan, now=8000)
        self.assertFalse(result['allocation_authorized'])
        self.assertIn('cold_start_does_not_fit_original_deadline', result['blockers'])
        self.assertGreater(result['stage_seconds']['transfer'], 1200)

    def test_more_money_does_not_renew_expired_deadline(self):
        plan = self.plan(); plan['remaining_budget_usd'] = 50
        result = assess(plan, now=10001)
        self.assertIn('original_grant_expired', result['blockers'])
        self.assertFalse(result['new_grant_created'])

    def test_cached_weights_still_require_cleanup_and_total_budget(self):
        plan = self.plan(); plan.update(model_bytes_to_transfer=0, remaining_budget_usd=.01)
        result = assess(plan, now=8000)
        self.assertIn('cold_start_exceeds_remaining_aggregate_budget', result['blockers'])

    def test_stale_or_future_bandwidth_measurement_blocks(self):
        for date in [1, 8001]:
            plan = self.plan(); plan['transfer_measured_at_epoch'] = date
            self.assertIn('transfer_measurement_not_current', assess(plan, now=8000)['blockers'])

    def test_adequate_plan_does_not_claim_generation_qualification(self):
        plan = self.plan(); plan.update(grant_deadline_epoch=20000, remaining_budget_usd=10)
        result = assess(plan, now=8000)
        self.assertTrue(result['allocation_authorized'])
        self.assertFalse(result['generation_or_quality_qualified'])

    def test_runner_derives_deadline_from_grant_and_blocks_before_post(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); lock = root / 'source/integrations/scene_quality/workflows'
            lock.mkdir(parents=True)
            (lock / 'ltx25-i2v.lock.json').write_text(json.dumps({'total_model_bytes': 39709872236}))
            plan = self.plan(); plan.update(grant_deadline_epoch=99999999999, remaining_budget_usd=999)
            (root / 'cold-start-plan.json').write_text(json.dumps(plan))
            with self.assertRaisesRegex(RuntimeError, 'original_grant_expired'):
                cold_start_check(root, {'terminate_at_epoch': 7999, 'budget_usd': 5}, now=8000)
            plan['model_bytes_to_transfer'] = 0
            (root / 'cold-start-plan.json').write_text(json.dumps(plan))
            with self.assertRaisesRegex(RuntimeError, 'all pinned model bytes'):
                cold_start_check(root, {'terminate_at_epoch': 20000, 'budget_usd': 5}, now=8000)


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'FFmpeg required')
class QualityJob(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(); cls.base = Path(cls.temp.name)
        for color in ['gray', 'white', 'red']:
            subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i',
                            f'color=c={color}:s=256x144:r=24:d=1', '-c:v', 'libx264',
                            '-pix_fmt', 'yuv420p', str(cls.base / (color + '.mp4'))], check=True)

    @classmethod
    def tearDownClass(cls): cls.temp.cleanup()

    def setUp(self):
        self.work = tempfile.TemporaryDirectory(dir=self.base)
        self.job = Path(self.work.name) / 'job'; self.movie = self.base / 'gray.mp4'
        self.ledger = {'rejections': []}
        self.state = prepare(self.job, self.movie, 'director', self.ledger)
        self.sha = self.state['artifact']['sha256']

    def tearDown(self): self.work.cleanup()

    def evidence(self):
        cap = dict(reviewer_id='independent', model_revision='heldout-fixture',
                   visual_input_qualified=True, temporal_input_qualified=True,
                   audio_perception_qualified=True, calibrated_on_heldout_controls=True)
        execution = dict(cap, artifact_sha256=self.sha, tool_calls=0,
                         input_binding_sha256=file_sha(self.job / 'review-input.json'),
                         coverage_complete=True, coverage=dict(artifact_sha256=self.sha,
                         start=0, end=1, scope='continuous_audiovisual'))
        review = dict(artifact_sha256=self.sha, verdict='pass_candidate', findings=[])
        return review, execution, cap

    def reject(self):
        review, execution, cap = self.evidence()
        review.update(verdict='reject', findings=[dict(start=0, end=.5, stage='camera',
                      severity='major', modality='motion', expected='Physical reveal',
                      observed='Static view', evidence='Continuous fixture video',
                      change='Generate the planned reveal', recheck='Observe parallax and revealed object')])
        return apply_review(self.job, review, execution, cap, self.ledger, 1)

    def test_decode_success_and_idempotent_prepare_do_not_release_movie(self):
        repeat = prepare(self.job, self.movie, 'director', self.ledger)
        self.assertEqual(repeat['revision'], 1)
        self.assertFalse(delivery_guard(self.job, self.movie, self.ledger)['allowed_as_owner_candidate'])
        self.assertEqual(current(self.job)['status'], 'needs_qualified_review')

    def test_owner_rejection_always_wins_over_qualified_model(self):
        self.ledger['rejections'] = [dict(artifact_sha256=self.sha, source='owner feedback', reason='Rejected')]
        r, e, c = self.evidence()
        outcome = apply_review(self.job, r, e, c, self.ledger, 1)
        self.assertFalse(outcome['ready_for_owner'])
        self.assertEqual(outcome['status'], 'needs_rework')

    def test_review_receipt_from_other_bundle_is_rejected(self):
        r, e, c = self.evidence(); e['input_binding_sha256'] = 'b' * 64
        with self.assertRaises(Invalid): apply_review(self.job, r, e, c, self.ledger, 1)

    def test_forged_audio_capability_is_rejected(self):
        r, e, c = self.evidence(); c['audio_perception_qualified'] = False
        with self.assertRaises(Invalid): apply_review(self.job, r, e, c, self.ledger, 1)

    def test_model_green_cannot_override_bound_objective_audio_failure(self):
        path=self.job/'technical.json';technical=json.loads(path.read_text())
        technical.update(hard_failures=['audio_timestamp_discontinuity'],hard_correction_findings=[dict(
            start=.2,end=.3,stage='sound',severity='critical',modality='audio',
            expected='Continuous PCM clock',observed='Overlapping decoded timestamps',
            evidence='Measured synthetic fixture',change='Rebuild from frozen WAV',
            recheck='Continuous timestamps and preserved source offsets')])
        write(path,technical);state=current(self.job);state['technical_report_sha256']=file_sha(path);write(self.job/'state.json',state)
        r,e,c=self.evidence();out=apply_review(self.job,r,e,c,self.ledger,1)
        self.assertFalse(out['ready_for_owner']);self.assertEqual(out['corrections']['tasks'][0]['stage'],'sound')
        self.assertEqual(out['corrections']['tasks'][0]['source_artifact_sha256'],self.sha)
        self.assertFalse(delivery_guard(self.job,self.movie,self.ledger)['allowed_as_owner_candidate'])

    def test_mutating_technical_report_after_review_revokes_delivery(self):
        r,e,c=self.evidence();apply_review(self.job,r,e,c,self.ledger,1)
        self.assertTrue(delivery_guard(self.job,self.movie,self.ledger)['allowed_as_owner_candidate'])
        path=self.job/'technical.json';technical=json.loads(path.read_text());technical['hard_failures']=['audio_timestamp_discontinuity'];write(path,technical)
        self.assertFalse(delivery_guard(self.job,self.movie,self.ledger)['allowed_as_owner_candidate'])

    def test_sparse_coverage_cannot_claim_continuous_perception(self):
        r, e, c = self.evidence(); e['coverage']['scope'] = '2fps_sample'
        with self.assertRaises(Invalid): apply_review(self.job, r, e, c, self.ledger, 1)

    def test_stale_job_revision_rejected_without_overwriting(self):
        self.reject(); r, e, c = self.evidence()
        with self.assertRaises(Invalid): apply_review(self.job, r, e, c, self.ledger, 1)
        self.assertEqual(len(current(self.job)['review_history']), 1)

    def test_corrective_task_has_exact_source_and_recheck(self):
        state = self.reject(); task = state['corrections']['tasks'][0]
        self.assertEqual(task['stage'], 'camera')
        self.assertEqual(task['source_artifact_sha256'], self.sha)
        self.assertTrue(task['recheck'])
        self.assertEqual(state['correction_rounds_used'], 0)

    def test_corrected_version_starts_unreviewed_and_cannot_overwrite_original(self):
        state = self.reject(); child_path = self.job.parent / 'revision'
        child = begin_revision(self.job, child_path, self.base / 'white.mp4', self.ledger, state['revision'])
        self.assertFalse(child['ready_for_owner'])
        self.assertEqual(child['correction_rounds_used'], 1)
        self.assertEqual(current(self.job)['artifact']['sha256'], self.sha)
        with self.assertRaises(Invalid): begin_revision(self.job, child_path, self.movie, self.ledger, state['revision'])

    def test_two_round_limit_and_pending_reviewer_do_not_create_more_work(self):
        state = self.reject(); state['correction_rounds_used'] = 2
        write(self.job / 'state.json', state)
        with self.assertRaises(Invalid): begin_revision(self.job, self.job.parent / 'r3', self.base / 'white.mp4', self.ledger, state['revision'])

    def test_late_owner_denial_revokes_candidate_at_delivery(self):
        r, e, c = self.evidence(); apply_review(self.job, r, e, c, self.ledger, 1)
        self.assertTrue(delivery_guard(self.job, self.movie, self.ledger)['allowed_as_owner_candidate'])
        self.ledger['rejections'] = [dict(artifact_sha256=self.sha, source='owner', reason='new denial')]
        self.assertFalse(delivery_guard(self.job, self.movie, self.ledger)['allowed_as_owner_candidate'])
        self.assertFalse(delivery_guard(self.job, self.base / 'white.mp4', self.ledger)['allowed_as_owner_candidate'])

