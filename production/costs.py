from decimal import Decimal, InvalidOperation
import re

from .core import ProductionError


def money(value):
    try:
        value = Decimal(str(value))
    except InvalidOperation as exc:
        raise ProductionError("Invalid cost") from exc
    if not value.is_finite() or value < 0:
        raise ProductionError("Costs and durations must be finite and nonnegative")
    return value


def summarize(attempts, overhead_usd=0):
    total = money(overhead_usd)
    accepted_seconds = Decimal(0)
    accepted_scenes, ids = set(), set()
    rejected = 0
    for a in attempts:
        if not a.get("attempt_id") or a["attempt_id"] in ids:
            raise ProductionError("Duplicate or missing attempt ID")
        ids.add(a["attempt_id"])
        for field in ("compute_usd", "storage_usd", "transfer_usd", "review_usd", "manual_usd", "training_usd"):
            total += money(a.get(field, 0))
        if a.get("accepted") is True:
            scene = a.get("scene_id")
            if not scene or scene in accepted_scenes:
                raise ProductionError("Count only one accepted result per benchmark scene")
            accepted_scenes.add(scene)
            duration = money(a.get("accepted_seconds", 0))
            if not duration:
                raise ProductionError("Accepted result must have positive duration")
            accepted_seconds += duration
        else:
            rejected += 1
    return {"attempts": len(attempts), "accepted_scenes": len(accepted_scenes), "rejected_attempts": rejected,
            "total_usd": str(total), "accepted_seconds": str(accepted_seconds),
            "usd_per_accepted_second": str(total/accepted_seconds) if accepted_seconds else None,
            "note": "Compare only quality-matched accepted material; this is not a forecast."}


def gpu_batch_cost(*, hourly_usd, gpu_count, inference_seconds, startup_seconds,
                   idle_seconds, storage_usd, transfer_usd, review_usd, manual_usd,
                   accepted_seconds):
    """Account for one measured batch, including failed attempts and idle/startup wall time."""
    if type(gpu_count) is not int or gpu_count < 1:
        raise ProductionError("GPU count must be a positive integer")
    billed = money(inference_seconds) + money(startup_seconds) + money(idle_seconds)
    total = money(hourly_usd) * gpu_count * billed / Decimal(3600)
    for extra in (storage_usd, transfer_usd, review_usd, manual_usd):
        total += money(extra)
    accepted = money(accepted_seconds)
    return {'billed_gpu_seconds': str(billed * gpu_count), 'total_usd': str(total),
            'accepted_seconds': str(accepted),
            'usd_per_accepted_second': str(total / accepted) if accepted else None}


def choose_qualified_route(benchmarks, quality_protocol_sha256, scene_ids):
    """Rank supplied measurements on the same complete scene set, not marketing rates.

    This is accounting, not authentication of the caller's evidence or a spending grant.
    """
    if not isinstance(quality_protocol_sha256, str) or not re.fullmatch('[a-f0-9]{64}', quality_protocol_sha256):
        raise ProductionError("A shared quality protocol is required")
    if (not isinstance(scene_ids, list) or not scene_ids
            or any(not isinstance(s, str) or not s for s in scene_ids)
            or len(set(scene_ids)) != len(scene_ids)):
        raise ProductionError("A common nonempty scene set is required")
    qualified = []
    excluded = []
    ids = set()
    for benchmark in benchmarks:
        if not isinstance(benchmark, dict):
            raise ProductionError("Benchmark must be an object")
        ident = benchmark.get('id')
        if not isinstance(ident, str) or not ident or ident in ids:
            raise ProductionError("Duplicate or missing benchmark ID")
        ids.add(ident)
        reason = None
        if benchmark.get('quality_protocol_sha256') != quality_protocol_sha256:
            reason = 'different_quality_protocol'
        elif benchmark.get('quality_accepted') is not True:
            reason = 'quality_not_accepted'
        elif benchmark.get('route') != 'self_hosted_gpu':
            reason = 'external_exception_requires_separate_decision'
        elif not benchmark.get('evidence'):
            reason = 'missing_measured_evidence'
        if reason:
            excluded.append({'id': ident, 'reason': reason})
            continue
        costs = summarize(benchmark.get('attempts', []), benchmark.get('overhead_usd', 0))
        if costs['usd_per_accepted_second'] is None:
            excluded.append({'id': ident, 'reason': 'no_accepted_output'})
            continue
        accepted = {a['scene_id'] for a in benchmark['attempts'] if a.get('accepted') is True}
        if accepted != set(scene_ids):
            excluded.append({'id': ident, 'reason': 'incomplete_or_different_scene_set'})
            continue
        qualified.append({'id': ident, **costs})
    qualified.sort(key=lambda item: (money(item['usd_per_accepted_second']), item['id']))
    return {'status': 'measured_candidates' if qualified else 'needs_measured_pilot',
            'selected': qualified[0]['id'] if qualified else None,
            'qualified': qualified, 'excluded': excluded, 'generation_authorized': False}
