"""ViMax shot-schema bridge with a separate frozen-speech execution contract.

The stock generate_single_video(prompt, reference_image_paths) call does not
carry a waveform. An executor must explicitly qualify this richer sidecar;
native generated voices cannot silently substitute for an approved Fish voice.
No model or cloud operation is submitted by this module.
"""
from .contracts import Invalid, digest, require_text, validate_plan


def export(plan, cast, layout):
    validation = validate_plan(plan, cast)
    width, height, fps = (layout.get(k) for k in ['width', 'height', 'fps'])
    if (any(type(n) is not int for n in [width, height, fps]) or width >= height
            or width % 64 or height % 64 or width * 16 != height * 9 or fps != 24):
        raise Invalid('Explicit vertical 24fps layout on the LTX grid required')
    if width * height > 1048576 or min(width, height) < 256:
        raise Invalid('Layout outside bounded speaking-scene trial')
    scene_layouts = layout.get('scenes', {})
    if set(scene_layouts) != {s['id'] for s in plan['scenes']}:
        raise Invalid('Every scene needs an exact layout binding')
    role_indices = {role: i for i, role in enumerate(sorted(cast))}
    camera_indices = {}; shots = []; execution = []
    for i, scene in enumerate(plan['scenes']):
        config = scene_layouts[scene['id']]
        group = require_text(config.get('camera_group'), 'camera group')
        camera_indices.setdefault(group, len(camera_indices))
        ids = {a['id'] for a in scene['cast']}
        visible = []
        for field in ['first_visible_cast', 'last_visible_cast']:
            value = config.get(field)
            if not isinstance(value, list) or len(value) != len(set(value)) or not set(value) <= ids:
                raise Invalid('Frame visibility must explicitly bind real scene roles')
            visible.append([role_indices[k] for k in value])
        lines = scene.get('dialogue', [])
        if lines and (scene.get('speech_mode') != 'audio_driven' or len(lines) != 1):
            raise Invalid('This bridge qualifies one frozen spoken line per shot only')
        frames = config.get('frames')
        if type(frames) is not int or not 33 <= frames <= 241 or (frames - 1) % 8:
            raise Invalid('Bounded 8n+1 frame count required')
        if abs(frames / fps - scene['duration_seconds']) > 1 / fps:
            raise Invalid('Video timing differs from the directed speech slot')
        if config.get('variation_type') not in {'small', 'medium', 'large'}:
            raise Invalid('Explicit ViMax motion variation required')
        shots.append({'idx': i, 'is_last': i == len(plan['scenes']) - 1,
                      'cam_idx': camera_indices[group], 'visual_desc': scene['action'],
                      'variation_type': config['variation_type'],
                      'variation_reason': scene['camera_reason'],
                      'ff_desc': scene['first_frame'], 'ff_vis_char_idxs': visible[0],
                      'lf_desc': scene['last_frame'], 'lf_vis_char_idxs': visible[1],
                      'motion_desc': scene['performance'] + '\n' + scene['camera_movement'],
                      'audio_desc': '\n'.join(line['speaker'] + ': ' + line['text'] for line in lines)})
        binding = {'shot_idx': i, 'source_scene_id': scene['id'], 'frames': frames,
                   'width': width, 'height': height, 'fps': fps,
                   'cast': scene['cast'], 'dialogue': lines,
                   'speech_mode': 'frozen_waveform' if lines else 'no_dialogue',
                   'waveform_preservation_required': bool(lines)}
        execution.append(binding)
    return {'schema_version': 1, 'status': 'plan_only_not_generated',
            'source_plan_sha256': validation['plan_sha256'], 'cast_sha256': digest(cast),
            'shot_descriptions': shots, 'execution_bindings': execution,
            'role_indices': role_indices, 'artistic_approval': False,
            'publication_authorized': False}


def executor_preflight(bundle, capability):
    blockers = []
    if capability.get('live_qualified') is not True:
        blockers.append('executor_not_live_qualified')
    for binding in bundle['execution_bindings']:
        if [binding['width'], binding['height']] not in capability.get('qualified_sizes', []):
            blockers.append('vertical_size_not_qualified')
        if binding['waveform_preservation_required']:
            if capability.get('accepts_audio_file') is not True:
                blockers.append('executor_has_text_audio_description_only')
            if capability.get('preserves_source_waveform') is not True:
                blockers.append('source_voice_not_preserved')
    return {'status': 'eligible_for_budget_check' if not blockers else 'blocked_before_generation',
            'capability_compatible': not blockers, 'generation_permitted': False,
            'requires_budget_preflight': True, 'blockers': sorted(set(blockers)),
            'bundle_sha256': digest(bundle), 'publication_authorized': False}
