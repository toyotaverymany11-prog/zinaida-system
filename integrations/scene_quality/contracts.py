"""Version-bound creative production contracts. Structural checks never certify taste."""
import hashlib
import json
import math
import re


class Invalid(ValueError):
    pass


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':')).encode()).hexdigest()


def require_text(value, name):
    if not isinstance(value, str) or not value.strip() or len(value) > 8000:
        raise Invalid(name + ' must be nonempty bounded text')
    return value


def sha(value):
    if not isinstance(value, str) or not re.fullmatch('[a-f0-9]{64}', value):
        raise Invalid('Exact artifact SHA256 required')
    return value


def seconds(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise Invalid('Finite nonnegative timestamp required')
    return value


def validate_plan(plan, cast):
    """Validate explicit directing decisions and provenance, without heuristic quality scores."""
    for key in ['audience', 'viewer_promise', 'emotional_change', 'visible_turn', 'ending_action']:
        require_text(plan.get(key), key)
    scenes = plan.get('scenes')
    if not isinstance(scenes, list) or not 1 <= len(scenes) <= 30:
        raise Invalid('Between1and30 scenes required')
    ids = set()
    for scene in scenes:
        sid = require_text(scene.get('id'), 'scene id')
        if sid in ids:
            raise Invalid('Duplicate scene id')
        ids.add(sid)
        for key in ['action', 'new_information', 'performance', 'location_id', 'light_direction',
                    'first_frame', 'last_frame', 'camera_position', 'camera_movement', 'camera_reason']:
            require_text(scene.get(key), key)
        if not 0 < seconds(scene.get('duration_seconds')) <= 30:
            raise Invalid('Scene duration outside bounded range')
        actors = scene.get('cast')
        if not isinstance(actors, list) or not actors:
            raise Invalid('Explicit cast bindings required')
        for actor in actors:
            character = cast.get(actor.get('id'))
            if not character or character.get('approval') != 'approved':
                raise Invalid('Unknown, rejected or unapproved character')
            if actor.get('reference_sha256') != character.get('reference_sha256'):
                raise Invalid('Character reference changed')
            sha(actor['reference_sha256'])
        dialogue = scene.get('dialogue', [])
        if not isinstance(dialogue, list):
            raise Invalid('Dialogue must be a list')
        for line in dialogue:
            character = cast.get(line.get('speaker'))
            if not character or line['speaker'] not in {a['id'] for a in actors}:
                raise Invalid('Speaking role not bound to scene')
            require_text(line.get('text'), 'spoken text')
            require_text(line.get('intention'), 'performance intention')
            if line.get('voice_id') != character.get('voice_id'):
                raise Invalid('Voice substitution')
            if scene.get('speech_mode') not in {'audio_driven', 'joint_audio_video_qualified_voice'}:
                raise Invalid('Visible speech must use audio-driven or qualified joint generation')
            if scene['speech_mode'] == 'audio_driven':
                sha(line.get('audio_sha256'))
        if not isinstance(scene.get('continuity'), dict) or not scene['continuity']:
            raise Invalid('Continuity state required')
    return {'status': 'structurally_valid_creative_proposal', 'plan_sha256': digest(plan),
            'scene_count': len(scenes), 'artistic_approval': False}


STAGES = {'producer', 'script', 'casting', 'directing', 'camera', 'scene_generation',
          'continuity', 'speech', 'sound', 'editing', 'delivery'}


def validate_review(review, artifact, execution):
    """Execution evidence is stamped by the runner, never accepted from a model answer."""
    if review.get('artifact_sha256') != artifact['sha256']:
        raise Invalid('Review belongs to a different version')
    if execution.get('artifact_sha256') != artifact['sha256']:
        raise Invalid('Reviewer input differs from delivered bytes')
    if execution.get('reviewer_id') == artifact.get('creator_id'):
        raise Invalid('Creator cannot independently approve own output')
    if execution.get('tool_calls', 0) != 0:
        raise Invalid('Reviewer attempted actions instead of isolated assessment')
    verdict = review.get('verdict')
    if verdict not in {'reject', 'abstain', 'pass_candidate'}:
        raise Invalid('Unknown creative verdict')
    findings = review.get('findings')
    if not isinstance(findings, list):
        raise Invalid('Explicit findings required')
    for finding in findings:
        start, end = seconds(finding.get('start')), seconds(finding.get('end'))
        if not start <= end <= artifact['duration_seconds']:
            raise Invalid('Finding time outside actual file')
        if finding.get('stage') not in STAGES:
            raise Invalid('Unknown correction stage')
        if finding.get('severity') not in {'critical', 'major', 'minor'}:
            raise Invalid('Unknown severity')
        for key in ['expected', 'observed', 'evidence', 'change', 'recheck']:
            require_text(finding.get(key), key)
        if finding.get('modality') == 'audio' and not execution.get('audio_perception_qualified'):
            raise Invalid('Audio opinion without qualified audio input')
        if finding.get('modality') == 'motion' and not execution.get('temporal_input_qualified'):
            raise Invalid('Motion opinion based only on stills')
    if verdict == 'reject' and not findings:
        raise Invalid('Rejection requires actionable evidence')
    severe = any(f['severity'] in {'critical', 'major'} for f in findings)
    complete = (execution.get('visual_input_qualified') and execution.get('temporal_input_qualified')
                and execution.get('audio_perception_qualified') and execution.get('coverage_complete'))
    ready = (verdict == 'pass_candidate' and not severe and complete
             and execution.get('calibrated_on_heldout_controls') is True)
    return {'status': 'candidate_for_owner' if ready else 'needs_rework' if severe or verdict == 'reject'
            else 'needs_qualified_review', 'ready_for_owner': bool(ready),
            'artistic_owner_approval': False, 'publication_authorized': False,
            'review_sha256': digest(review), 'artifact_sha256': artifact['sha256']}


def correction_tasks(review, rounds_used, max_rounds=2):
    if not isinstance(rounds_used, int) or not 0 <= rounds_used <= max_rounds:
        raise Invalid('Invalid correction count')
    if rounds_used == max_rounds:
        return {'status': 'iteration_limit_reached', 'tasks': [], 'show_failed_movie_as_ready': False}
    return {'status': 'corrections_required', 'round': rounds_used + 1,
            'tasks': [{'stage': f['stage'], 'start': f['start'], 'end': f['end'],
                       'change': f['change'], 'recheck': f['recheck']}
                      for f in review['findings'] if f['severity'] in {'critical', 'major'}],
            'show_failed_movie_as_ready': False}
