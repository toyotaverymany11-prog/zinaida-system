"""Fail-closed release gate for exact video, project, references and critic evidence."""
import argparse
import json
from pathlib import Path
import shutil
import time
from .contracts import Invalid, digest, sha, validate_plan
from .qualification import SCOPES, validate_bundle
from .supervisor import current, delivery_guard, file_sha, locked, write


def read(path):
    path = Path(path)
    if path.is_symlink() or any(p.is_symlink() for p in path.parents):
        raise Invalid('Quality evidence cannot be a symlink')
    if path.stat().st_size > 8*1024*1024: raise Invalid('Quality evidence is oversized')
    return json.loads(path.read_text())


def policy(root):
    value = read(Path(root)/'policy.json')
    if (value.get('schema_version') != 1 or value.get('required_scopes') != list(SCOPES)
            or value.get('publication_authorized') is not False):
        raise Invalid('Current explicit quality policy required')
    fields = ['brand_reference_sha256', 'cast_manifest_sha256', 'direction_rules_sha256']
    if set(value.get('reference_files', {})) != set(fields):
        raise Invalid('Current reference files required')
    for k in fields:
        sha(value.get(k))
        name = value['reference_files'][k]
        if not isinstance(name, str) or Path(name).name != name:
            raise Invalid('Invalid reference address')
        path = Path(root)/name
        if path.is_symlink() or not path.is_file() or file_sha(path) != value[k]:
            raise Invalid('Current reference changed')
    return value


def bind(root, job, movie, project, context):
    """Called after snapshot preparation; the creator cannot make this a release."""
    root, job = Path(root), Path(job)
    rules = policy(root)
    cast = read(root/rules['reference_files']['cast_manifest_sha256'])
    validate_plan(context, cast)
    if job.parent.resolve() != root.resolve(): raise Invalid('Job outside configured quality root')
    with locked(job):
        state = current(job)
        if state['artifact']['sha256'] != file_sha(movie): raise Invalid('Quality snapshot differs from movie')
        if job.name != state['artifact']['sha256']: raise Invalid('Quality job name must bind exact artifact')
        value = {'schema_version': 1, 'artifact_sha256': state['artifact']['sha256'],
                 'project_sha256': file_sha(project), 'policy_sha256': digest(rules),
                 'creative_context_sha256': digest(context),
                 'required_scopes': list(SCOPES), 'purpose': 'candidate_for_owner_only',
                 'publication_authorized': False}
        target = job/'release-input.json'
        if target.exists() and read(target) != value:
            raise Invalid('Existing release binding requires a new review job')
        instructions = read(job/'review-input.json')
        if state.get('review_history') and instructions.get('release_binding') != value:
            raise Invalid('References were not bound before independent review')
        if instructions.get('release_binding') not in (None, value):
            raise Invalid('Existing reviewer input has another release binding')
        copies = job/'references';copies.mkdir(exist_ok=True)
        for key, name in rules['reference_files'].items():
            target_reference=copies/name
            if target_reference.exists():
                if file_sha(target_reference)!=rules[key]:raise Invalid('Frozen review reference changed')
            else:
                shutil.copyfile(root/name,target_reference)
                if file_sha(target_reference)!=rules[key]:raise Invalid('Reference changed during snapshot')
                target_reference.chmod(0o400)
        instructions.update(release_binding=value,
            reference_files={k:'references/'+v for k,v in rules['reference_files'].items()},
            comparison_context='creative-context.json')
        write(job/'creative-context.json',context)
        write(job/'review-input.json', instructions)
        write(target, value)
        return value


def guard(root, movie, project, ledger, *, now=None):
    """Check every read, including after bytes are loaded. Never renders or dispatches."""
    root = Path(root)
    result = {'allowed_as_owner_candidate': False, 'publication_authorized': False,
              'owner_artistic_approval': False, 'reason': 'quality_not_qualified'}
    try:
        rules = policy(root)
        artifact = file_sha(movie); job = root/artifact
        value = read(job/'release-input.json')
        if (value.get('artifact_sha256') != artifact or value.get('project_sha256') != file_sha(project)
                or value.get('policy_sha256') != digest(rules)
                or value.get('required_scopes') != list(SCOPES)
                or value.get('purpose') != 'candidate_for_owner_only'
                or value.get('publication_authorized') is not False):
            raise Invalid('Release binding changed')
        context=read(job/'creative-context.json')
        if digest(context)!=value.get('creative_context_sha256'):raise Invalid('Creative context changed')
        for key,name in rules['reference_files'].items():
            if file_sha(job/'references'/name)!=rules[key]:raise Invalid('Frozen review reference changed')
        validate_plan(context,read(job/'references'/rules['reference_files']['cast_manifest_sha256']))
        if not delivery_guard(job, movie, ledger)['allowed_as_owner_candidate']:
            raise Invalid('Independent exact-version review not passed')
        state = current(job)
        if not state.get('review_history'): raise Invalid('Independent review record missing')
        last = state['review_history'][-1]
        if not isinstance(last.get('file'), str) or Path(last['file']).name != last['file']:
            raise Invalid('Invalid review record address')
        review = read(job/last['file'])
        if digest(review) != last.get('sha256'): raise Invalid('Review record changed')
        capability = read(job/'reviewer-capability.json')
        if digest(capability) != review.get('capability_sha256'):
            raise Invalid('Reviewer capability does not match its execution')
        execution = review['execution']
        bundle = read(job/'calibration.json')
        calibration = validate_bundle(bundle, now=time.time() if now is None else now)
        ident = calibration['identity']
        if (ident['reviewer_id'] != execution['reviewer_id'] or ident['model_revision'] != execution['model_revision']
                or ident['route'] != execution.get('route')
                or capability.get('calibration_sha256') != digest(bundle)):
            raise Invalid('Another reviewer calibration supplied')
        # Do not trust state.json alone: revalidate the immutable review and input.
        from .contracts import validate_review
        if execution.get('input_binding_sha256') != file_sha(job/'review-input.json'):
            raise Invalid('Reviewer input changed')
        if (read(job/'review-input.json').get('release_binding') != value
                or execution.get('reference_policy_sha256') != digest(rules)):
            raise Invalid('Reviewer did not receive current references')
        coverage = execution.get('coverage', {})
        if (coverage.get('artifact_sha256') != artifact or coverage.get('start') != 0
                or coverage.get('end') != state['artifact']['duration_seconds']
                or coverage.get('scope') != 'continuous_audiovisual'):
            raise Invalid('Complete audiovisual coverage is missing')
        decision = validate_review(review['review'], state['artifact'], execution)
        if not decision['ready_for_owner']: raise Invalid('Reviewer result cannot grant delivery')
        if (review['outcome'].get('artifact_sha256') != artifact
                or not all(capability.get(k) is True for k in ['visual_input_qualified',
                    'temporal_input_qualified', 'audio_perception_qualified', 'calibrated_on_heldout_controls'])):
            raise Invalid('Required reviewer perception not qualified')
        result.update(allowed_as_owner_candidate=True, reason='exact_version_independently_qualified',
                      artifact_sha256=artifact, project_sha256=value['project_sha256'],
                      policy_sha256=value['policy_sha256'])
    except (Invalid, OSError, ValueError, KeyError, TypeError):
        pass
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['bind','guard'])
    for field in ['root','video','project']: parser.add_argument('--'+field, required=True)
    parser.add_argument('--ledger', required=True)
    parser.add_argument('--context')
    args = parser.parse_args(); ledger = read(args.ledger)
    if args.action == 'bind':
        if not args.context:parser.error('--context is required before independent review')
        value = bind(args.root, Path(args.root)/file_sha(args.video), args.video, args.project,read(args.context))
    else: value = guard(args.root, args.video, args.project, ledger)
    print(json.dumps(value, ensure_ascii=False, indent=2))
    if args.action == 'guard' and not value['allowed_as_owner_candidate']: raise SystemExit(3)


if __name__ == '__main__': main()
