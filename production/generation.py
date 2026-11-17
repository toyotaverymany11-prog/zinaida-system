"""Self-hosted generation policy and quality requirements for saved video orders.

Planning is CPU-only. Model metadata is not an installed or qualified executor.
"""
import json
from pathlib import Path

from .core import ProductionError, object_digest

POLICY = {
    'schema_version': 1,
    'primary_route': 'self_hosted_gpu',
    'objective': 'lowest_total_cost_per_accepted_second_at_required_quality',
    'external_api_auto_fallback': False,
    'budget_usd': 0,
    'voice_policy': 'preserve_four_approved_fish_voices',
    'quality_precedes_cost': True,
}

# Pin public upstream revisions. Downloading weights and qualifying hardware are separate steps.
MODELS = [
    {'id': 'ltx-2.5', 'repo': 'Lightricks/LTX-2.5',
     'revision': '49b093a39c19169a8a81721dcc541e07e945232f',
     'tasks': ['cinematic_generation', 'reference_generation', 'character_generation'],
     'runtime': 'comfyui', 'weights_variant': 'comfy_int8',
     'state': 't2v_execution_verified_artistic_unqualified',
     'technical_evidence': 'production/qualification/automatic-live-20261117.json',
     'limitations': ['Automatic guarded 5-second T2V and editable package verified; initial teapot geometry failed, later cube samples remained stable',
                     'Reference editing, face fidelity and accepted cost remain unqualified',
                     'Comfy int8 files cannot be loaded by the PyTorch pipeline']},
    {'id': 'wan-animate-2', 'repo': 'Wan-AI/Wan2.2-Animate-2-14B',
     'revision': '6e8f1973bf0abc2aafd517992e8b6d88c3c46e69',
     'tasks': ['motion_transfer', 'character_generation'],
     'runtime': 'upstream_python', 'state': 'upstream_metadata_verified',
     'limitations': ['Official tested setup uses multiple A800 GPUs',
                     'Source background preservation is not established by animation capability']},
    {'id': 'wan-animate-replacement', 'repo': 'Wan-AI/Wan2.2-Animate-14B',
     'revision': 'cb93a225fbaf1ca100f54e79da8f994995b689b3',
     'tasks': ['body_replacement'],
     'runtime': 'upstream_python', 'state': 'upstream_metadata_verified',
     'limitations': ['Requires replacement preprocessing and relighting',
                     'Animal replacement and exact source preservation need separate acceptance']},
]

QUALITY_CRITERIA = {
    'cinematography': 'Свет, композиция, движение камеры и ракурс соответствуют замыслу.',
    'photorealism': 'Для фотореализма проверены кожа, глаза, волосы, руки и детали без пластикового вида.',
    'temporal': 'Детали и геометрия сохраняются в движении, на поворотах и между планами.',
    'identity': 'Герой сверяется с закреплёнными изображениями, включая профиль, речь и перекрытия лица.',
    'source_preservation': 'Вне заданной области сохраняются камера, тайминг, действие, фон и исходный звук.',
    'contact_and_occlusion': 'Контакты, тени и перекрытия согласованы с заменённым телом или животным.',
}


def requirements(order):
    mode = order['mode']
    if mode not in {'new_video', 'reference', 'face_replace', 'body_replace'}:
        raise ProductionError('Unknown production mode')
    checks = ['cinematography', 'photorealism', 'temporal']
    if order.get('characters') or mode in {'face_replace', 'body_replace'}:
        checks.append('identity')
    if mode in {'face_replace', 'body_replace'}:
        checks.append('source_preservation')
    if mode == 'body_replace':
        checks.append('contact_and_occlusion')
    return {
        'policy_sha256': object_digest(POLICY),
        'quality_profile': 'cinematic_or_source_matched',
        'criteria': {key: QUALITY_CRITERIA[key] for key in checks},
        'character_references': [asset['id'] for asset in order.get('characters', [])],
        'character_assignment': 'requires_explicit_identity_mapping',
        'audio_policy': POLICY['voice_policy'],
        'quality_acceptance': 'pending',
        'cost_basis': POLICY['objective'],
        'external_api_auto_fallback': False,
    }


def readiness(order):
    task = {'new_video': 'cinematic_generation', 'reference': 'reference_generation',
            'face_replace': 'face_only_replacement', 'body_replace': 'body_replacement'}[order['mode']]
    candidates = [dict(model, execution_ready=False) for model in MODELS if task in model['tasks']]
    blockers = ['Конкретному запуску нужны ограниченный бюджет и действующее разрешение.',
                'До аренды нужен независимо запущенный и проверенный контроль её завершения.',
                'Нужны измерения качества, времени и стоимости принятого результата.']
    if not candidates:
        blockers.append('Точный маршрут замены только лица ещё требует выбора и испытания.')
    return {'primary_route': POLICY['primary_route'], 'task': task,
            'candidates': candidates, 'blockers': blockers, 'generation_authorized': False,
            'external_api_auto_fallback': False, 'catalog_checked_on': '2026-11-17'}


def validate_character_assignment(plan, packet):
    """Optional named cast preserves existing plans while enabling explicit identity binding."""
    cast = plan.get('cast')
    if cast is None:
        return
    if not isinstance(cast, dict) or not cast or len(cast) > 12:
        raise ProductionError('Cast must map 1..12 character IDs to reference images')
    allowed = {a['id'] for a in packet['order']['characters']}
    assigned = set()
    for name, refs in cast.items():
        if not isinstance(name, str) or not name.strip() or len(name) > 80:
            raise ProductionError('Invalid character name')
        if (not isinstance(refs, list) or not refs
                or any(not isinstance(ref, str) or ref not in allowed for ref in refs)):
            raise ProductionError('Character must use this order reference images')
        if len(set(refs)) != len(refs) or assigned.intersection(refs):
            raise ProductionError('An image cannot silently represent multiple characters')
        assigned.update(refs)
    if assigned != allowed:
        raise ProductionError('Assign every character reference explicitly')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Inspect self-hosted policy; never executes generation')
    parser.add_argument('--order', type=Path, required=True)
    args = parser.parse_args()
    order = json.loads(args.order.read_text())
    print(json.dumps({'requirements': requirements(order), 'readiness': readiness(order)},
                     ensure_ascii=False, indent=2))
