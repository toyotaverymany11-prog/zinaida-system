"""Held-out critic evaluation. A model-written confidence flag is never a certificate."""
import math
from .contracts import Invalid, digest, require_text, sha, seconds

SCOPES = ('casting', 'story', 'camera', 'editing', 'speech', 'sound', 'anatomy', 'brand')
POLICY = {'version': 1, 'min_positive_groups': 2, 'min_negative_groups': 2,
          'max_false_accepts': 0, 'max_false_reject_rate': .25,
          'max_abstention_rate': .25, 'max_age_seconds': 86400}


def validate_dataset(dataset):
    cases = dataset.get('cases')
    if not isinstance(cases, list) or not 1 <= len(cases) <= 2000:
        raise Invalid('Bounded explicit control cases required')
    ids, groups, assets = set(), {}, {}
    for case in cases:
        ident = require_text(case.get('id'), 'control id')
        if ident in ids: raise Invalid('Duplicate control id')
        ids.add(ident)
        group = require_text(case.get('source_group'), 'original source group')
        split = case.get('split')
        if split not in {'development', 'holdout'}: raise Invalid('Explicit control split required')
        if groups.setdefault(group, split) != split: raise Invalid('Source variants leak across control splits')
        asset = sha(case.get('artifact_sha256'))
        if assets.setdefault(asset, (group, split)) != (group, split):
            raise Invalid('Identical asset relabelled into another control group')
        labels = case.get('labels')
        if not isinstance(labels, dict) or not labels: raise Invalid('Control labels required')
        for scope, label in labels.items():
            if scope not in SCOPES or label not in {'pass', 'reject'}: raise Invalid('Invalid control label')
        require_text(case.get('label_basis'), 'label evidence')
    return cases


def public_cases(dataset):
    """Only these fields may reach a critic. Gold decisions remain in the runner."""
    return [{'id': c['id'], 'artifact_sha256': c['artifact_sha256']}
            for c in validate_dataset(dataset) if c['split'] == 'holdout']


def wilson_upper(errors, total):
    if not total: return None
    z = 1.959963984540054
    p = errors / total
    return (p + z*z/(2*total) + z*math.sqrt(p*(1-p)/total+z*z/(4*total*total))) / (1+z*z/total)


def evaluate(dataset, predictions, identity, *, measured_at, policy=None):
    """Predictions and receipts come from a trusted runner, never from the browser."""
    policy = dict(POLICY if policy is None else policy)
    if set(policy) != set(POLICY): raise Invalid('Unknown calibration policy fields')
    for k in ['reviewer_id', 'model_revision', 'route']:
        require_text(identity.get(k), k)
    seconds(measured_at)
    cases = {c['id']: c for c in validate_dataset(dataset) if c['split'] == 'holdout'}
    if not isinstance(predictions, list): raise Invalid('Explicit prediction records required')
    found = {}
    for p in predictions:
        c = cases.get(p.get('case_id'))
        if c is None: raise Invalid('Prediction for an unknown or development case')
        if p.get('artifact_sha256') != c['artifact_sha256']:
            raise Invalid('Critic received another control file')
        sha(p.get('runner_receipt_sha256'))
        if p.get('identity') != identity: raise Invalid('Mixed reviewer identities in calibration')
        for scope, decision in p.get('decisions', {}).items():
            if scope not in c['labels'] or decision not in {'pass', 'reject', 'abstain'}:
                raise Invalid('Unexpected control prediction')
            key = (c['id'], scope)
            if key in found: raise Invalid('Duplicate control prediction')
            found[key] = decision
    metrics, qualified = {}, []
    for scope in SCOPES:
        selected = [c for c in cases.values() if scope in c['labels']]
        pos = [c for c in selected if c['labels'][scope] == 'pass']
        neg = [c for c in selected if c['labels'][scope] == 'reject']
        false_accepts = sum(found.get((c['id'], scope)) == 'pass' for c in neg)
        false_rejects = sum(found.get((c['id'], scope)) == 'reject' for c in pos)
        abstains = sum(found.get((c['id'], scope), 'abstain') == 'abstain' for c in selected)
        enough = (len({c['source_group'] for c in pos}) >= policy['min_positive_groups']
                  and len({c['source_group'] for c in neg}) >= policy['min_negative_groups'])
        ok = (enough and false_accepts <= policy['max_false_accepts']
              and false_rejects / len(pos) <= policy['max_false_reject_rate']
              and abstains / len(selected) <= policy['max_abstention_rate'])
        metrics[scope] = {'positive_cases': len(pos), 'negative_cases': len(neg),
            'positive_groups': len({c['source_group'] for c in pos}),
            'negative_groups': len({c['source_group'] for c in neg}),
            'false_accepts': false_accepts, 'false_rejects': false_rejects, 'abstentions': abstains,
            'false_accept_rate': false_accepts / len(neg) if neg else None,
            'false_accept_wilson_upper_95': wilson_upper(false_accepts, len(neg)),
            'false_reject_rate': false_rejects / len(pos) if pos else None,
            'qualified_on_this_control_set': bool(ok)}
        if ok: qualified.append(scope)
    return {'schema_version': 1, 'identity': identity, 'measured_at': measured_at,
            'dataset_sha256': digest(dataset), 'predictions_sha256': digest(predictions),
            'policy': policy, 'policy_sha256': digest(policy), 'metrics': metrics,
            'qualified_scopes': qualified,
            'limits': 'Initial held-out evaluation only. Small denominators and95%upper bounds are explicit; no universal quality guarantee.'}


def validate_bundle(bundle, *, now, required_scopes=SCOPES):
    """Recompute denominators and decisions instead of trusting a green summary."""
    report = evaluate(bundle['dataset'], bundle['predictions'], bundle['identity'],
                      measured_at=bundle['measured_at'])
    if report != bundle.get('report'): raise Invalid('Calibration summary or policy changed')
    if not 0 <= now - report['measured_at'] <= POLICY['max_age_seconds']:
        raise Invalid('Calibration expired or measured in the future')
    if not set(required_scopes).issubset(report['qualified_scopes']):
        raise Invalid('Reviewer has unqualified required scopes')
    return report
