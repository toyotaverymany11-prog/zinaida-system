"""Conservative cold-start feasibility, evaluated BEFORE a billable allocation.

This module never allocates resources or extends an existing grant. Measurements
are observations, not guarantees of future throughput or inference quality.
"""
import argparse
import json
import math
import time
from pathlib import Path

from .contracts import Invalid, digest


def number(value, field, positive=False):
    if (isinstance(value, bool) or not isinstance(value, (int, float))
            or not math.isfinite(value) or value < 0 or (positive and value == 0)):
        raise Invalid('Invalid finite measurement: ' + field)
    return value


def assess(plan, now=None):
    now = time.time() if now is None else number(now, 'now')
    required = ['grant_deadline_epoch', 'remaining_budget_usd', 'hourly_total_ceiling_usd',
                'bootstrap_seconds', 'model_bytes_to_transfer', 'disk_available_bytes',
                'disk_required_bytes', 'inference_seconds', 'review_seconds',
                'cleanup_seconds', 'safety_seconds', 'allocation_seconds',
                'transfer_safety_factor', 'measurement_ttl_seconds']
    for field in required:
        number(plan.get(field), field)
    if plan['transfer_safety_factor'] < 1 or plan['cleanup_seconds'] < 120:
        raise Invalid('Transfer margin and independent cleanup reserve required')
    if plan['hourly_total_ceiling_usd'] == 0 or plan['measurement_ttl_seconds'] == 0:
        raise Invalid('Positive total price and measurement TTL required')
    blockers = []
    transfer = 0
    if plan['model_bytes_to_transfer']:
        rate = number(plan.get('measured_bytes_per_second'), 'measured_bytes_per_second', True)
        measured_at = number(plan.get('transfer_measured_at_epoch'), 'transfer_measured_at_epoch')
        if not 0 <= now - measured_at <= plan['measurement_ttl_seconds']:
            blockers.append('transfer_measurement_not_current')
        transfer = math.ceil(plan['model_bytes_to_transfer'] / rate * plan['transfer_safety_factor'])
    stages = {k: math.ceil(plan[k + '_seconds']) for k in
              ['allocation', 'bootstrap', 'inference', 'review', 'cleanup', 'safety']}
    stages['transfer'] = transfer
    total = sum(stages.values())
    cost = total / 3600 * plan['hourly_total_ceiling_usd']
    available = max(0, plan['grant_deadline_epoch'] - now)
    if plan['grant_deadline_epoch'] <= now:
        blockers.append('original_grant_expired')
    if total > available:
        blockers.append('cold_start_does_not_fit_original_deadline')
    if cost > plan['remaining_budget_usd']:
        blockers.append('cold_start_exceeds_remaining_aggregate_budget')
    if plan['disk_required_bytes'] > plan['disk_available_bytes']:
        blockers.append('insufficient_disk')
    if plan.get('independent_cleanup_qualified') is not True:
        blockers.append('independent_cleanup_not_qualified')
    return {'status': 'eligible_for_allocation_check' if not blockers else 'blocked_before_allocation',
            'allocation_authorized': not blockers, 'blockers': blockers,
            'input_sha256': digest(plan), 'evaluated_at_epoch': now,
            'stage_seconds': stages, 'estimated_total_seconds': total,
            'available_seconds': available, 'conservative_cost_usd': cost,
            'new_grant_created': False, 'generation_or_quality_qualified': False}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--plan', required=True); p.add_argument('--output', required=True)
    a = p.parse_args(); result = assess(json.loads(Path(a.plan).read_text()))
    Path(a.output).write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps(result, ensure_ascii=False))
