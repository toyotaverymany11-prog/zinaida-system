"""Verified evidence and revisioned scene proposals. Proposals grant no execution rights."""
import argparse
from html import escape
from pathlib import Path
from uuid import UUID
import json

from .core import ProductionError, Runtime, digest, local_asset, number, object_digest, read_json
from .intake import Intake


def order_evidence(root, order_id):
    intake = Intake(Path(root))
    ident = str(UUID(order_id))
    runtime = Runtime(30)
    with intake.connect() as db:
        row = db.execute('SELECT data FROM orders WHERE id=?', (ident,)).fetchone()
    if row is None:
        raise ProductionError('Unknown order')
    order = json.loads(row[0])
    receipt = read_json(intake.root / 'preparations' / ident / 'receipt.json')
    if receipt.get('order_sha256') != object_digest(order):
        raise ProductionError('Preparation belongs to a different order')
    if receipt.get('status') != 'prepared_for_review':
        raise ProductionError('Order preparation is incomplete')
    for asset in [*order['references'], *order['characters'], *([order['voice']] if order.get('voice') else [])]:
        if digest(local_asset(intake.root, 'assets/' + asset['id']), runtime) != asset['id']:
            raise ProductionError('Source integrity check failed')
    media = []
    references = []
    for item in receipt['reference_evidence']:
        checked = {}
        for entry in item['files']:
            path = local_asset(intake.root, entry['path'])
            if digest(path, runtime) != entry['sha256']:
                raise ProductionError('Prepared evidence changed; repeat preparation')
            checked[entry['path']] = entry['sha256']
        if item['analysis_path'] not in checked:
            raise ProductionError('Analysis is missing from verified evidence')
        analysis = read_json(local_asset(intake.root, item['analysis_path']))
        asset_id = item['asset_id']
        if analysis['source_sha256'] != asset_id or asset_id not in {a['id'] for a in order['references']}:
            raise ProductionError('Analysis source mismatch')
        folder = Path(item['analysis_path']).parent
        frames = []
        for frame in analysis['frames']:
            path = (folder / frame['path']).as_posix()
            if checked.get(path) != frame['sha256']:
                raise ProductionError('Frame is missing from verified evidence')
            frames.append({'time_seconds': frame['time_seconds'], 'media_index': len(media)})
            media.append({'path': path, 'sha256': checked[path], 'kind': 'image'})
        audio_index = None
        if analysis.get('audio_for_analysis'):
            path = (folder / analysis['audio_for_analysis']).as_posix()
            if path not in checked:
                raise ProductionError('Audio is missing from verified evidence')
            audio_index = len(media)
            media.append({'path': path, 'sha256': checked[path], 'kind': 'audio'})
        references.append({'asset_id': asset_id,
            'duration_seconds': float(analysis['probe']['format']['duration']),
            'detected_shots': analysis['detected_shots'], 'frames': frames,
            'audio_index': audio_index, 'coverage': analysis['coverage']})
    if {r['asset_id'] for r in references} != {a['id'] for a in order['references'] if a['kind'] == 'video'}:
        raise ProductionError('Preparation is missing reference evidence')
    transcript = None
    if order.get('voice'):
        item = receipt['transcript']
        path = local_asset(intake.root, item['path'])
        if digest(path, runtime) != item['sha256']:
            raise ProductionError('Transcript changed; repeat preparation')
        transcript = read_json(path)
    packet = {'schema_version': 1, 'order': order, 'references': references,
              'transcript': transcript, 'media': media,
              'semantic_review': 'pending', 'artistic_review': 'pending'}
    packet['packet_sha256'] = object_digest(packet)
    return packet


def media_file(root, order_id, index):
    root = Path(root).resolve()
    ident = str(UUID(order_id))
    receipt = read_json(root / 'preparations' / ident / 'receipt.json')
    entries = []
    for item in receipt['reference_evidence']:
        checked = {f['path']: f['sha256'] for f in item['files']}
        analysis_path = local_asset(root, item['analysis_path'])
        if digest(analysis_path) != checked.get(item['analysis_path']):
            raise ProductionError('Analysis integrity check failed')
        analysis = read_json(analysis_path)
        folder = Path(item['analysis_path']).parent
        for frame in analysis['frames']:
            entries.append(((folder / frame['path']).as_posix(), frame['sha256'], 'image', checked))
        if analysis.get('audio_for_analysis'):
            path = (folder / analysis['audio_for_analysis']).as_posix()
            entries.append((path, checked.get(path), 'audio', checked))
    if not 0 <= index < len(entries):
        raise ProductionError('Unknown evidence media')
    relative, sha, kind, checked = entries[index]
    path = local_asset(root, relative)
    if sha != checked.get(relative) or digest(path) != sha:
        raise ProductionError('Media integrity check failed')
    return path, kind


def source_file(root, order_id, asset_id):
    intake = Intake(Path(root))
    with intake.connect() as db:
        row = db.execute('SELECT data FROM orders WHERE id=?', (str(UUID(order_id)),)).fetchone()
    if row is None:
        raise ProductionError('Unknown order')
    order = json.loads(row[0])
    assets = [*order['references'], *order['characters'], *([order['voice']] if order.get('voice') else [])]
    for asset in assets:
        if asset['id'] == asset_id:
            path = local_asset(intake.root, 'assets/' + asset_id)
            if digest(path, Runtime(30)) != asset_id:
                raise ProductionError('Source integrity check failed')
            import mimetypes
            return path, mimetypes.guess_type(asset['name'])[0] or 'application/octet-stream'
    raise ProductionError('Source does not belong to this order')


def review_page(root, order_id):
    packet = order_evidence(root, order_id)
    order = packet['order']
    proposal = latest_plan(root, order['id'], packet['packet_sha256'])
    parts = ['<!doctype html><html lang="ru"><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width,initial-scale=1">',
        '<title>Материалы и план</title><style>',
        'body{font:17px system-ui;margin:auto;padding:24px;max-width:1100px;background:#111923;color:#e8edf3}',
        'a{color:#8dc9ff}section{margin:24px 0}p{white-space:pre-wrap}',
        '.frames{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}',
        'figure{margin:0}img{width:100%}audio{max-width:100%}li{margin:8px 0}',
        '</style><a href="/">К заказам</a><h1>Материалы и план</h1>']
    for key, title in [('brief', 'Задача'), ('changes', 'Изменить'), ('preserve', 'Сохранить')]:
        if order[key]:
            parts.append('<h2>' + title + '</h2><p>' + escape(order[key]) + '</p>')
    if packet['transcript']:
        parts.append('<h2>Черновая расшифровка</h2><p>' + escape(packet['transcript']['text']) + '</p>')
    for asset in order['characters']:
        url = f"/api/orders/{order['id']}/source/{asset['id']}"
        parts.append(f'<h2>Персонаж</h2><img style="max-width:320px" src="{url}" alt="Изображение персонажа">')
    if order.get('voice'):
        url = f"/api/orders/{order['id']}/source/{order['voice']['id']}"
        parts.append(f'<h2>Голосовой оригинал</h2><audio controls src="{url}"></audio>')
    for ref in packet['references']:
        url = f"/api/orders/{order['id']}/source/{ref['asset_id']}"
        parts.append(f'<video style="width:100%;max-height:520px" controls preload="metadata" src="{url}"></video>')
        parts.append('<section><h2>Референс</h2><p>Выборочные кадры. Движение проверяется по исходному видео.</p><div class="frames">')
        for frame in ref['frames']:
            url = f"/api/orders/{order['id']}/media/{frame['media_index']}"
            parts.append(f'<figure><img loading="lazy" src="{url}" alt="Кадр референса">'
                         f"<figcaption>{frame['time_seconds']:.3f} с</figcaption></figure>")
        parts.append('</div>')
        if ref['audio_index'] is not None:
            url = f"/api/orders/{order['id']}/media/{ref['audio_index']}"
            parts.append(f'<h3>Звук референса</h3><audio controls src="{url}"></audio>')
        parts.append('</section>')
    parts.append('<h2>План сцен</h2>')
    if proposal is None:
        parts.append('<p>Ожидается разбор задачи и предложение плана сцен.</p>')
    else:
        label = ('Материалы изменились. План требует повторной проверки.' if proposal['status'] == 'stale_evidence'
                 else 'Ожидается независимая смысловая и художественная проверка.')
        parts.append(f"<p>Версия {proposal['revision']}. {label}</p><p>{escape(proposal['plan']['summary'])}</p>")
        for i, scene in enumerate(proposal['plan']['scenes'], 1):
            parts.append(f'<section><h3>Сцена {i}</h3>')
            if scene['source']:
                parts.append(f"<p>{scene['source']['start']:.3f} - {scene['source']['end']:.3f} с</p>")
            for key, label in [('observation','Наблюдение'),('action','Действие')]:
                parts.append(f'<h4>{label}</h4><p>{escape(scene[key])}</p>')
            for key, label in [('preserve','Сохранить'),('change','Изменить'),('checks','Проверить')]:
                parts.append(f'<h4>{label}</h4><ul>' + ''.join('<li>' + escape(v) + '</li>' for v in scene[key]) + '</ul>')
            parts.append('</section>')
        if proposal['plan']['open_questions']:
            parts.append('<h3>Открытые вопросы</h3><ul>' + ''.join(
                '<li>' + escape(v) + '</li>' for v in proposal['plan']['open_questions']) + '</ul>')
    parts.append('</html>')
    return ''.join(parts)


def require_text(value, name):
    if not isinstance(value, str) or not value.strip() or len(value) > 12000:
        raise ProductionError(f'{name} must contain text (1..12000 characters)')
    return value


def text_list(value, name):
    if not isinstance(value, list) or not 1 <= len(value) <= 30:
        raise ProductionError(f'{name} must contain 1..30 items')
    for item in value:
        require_text(item, name)


def validate_plan(plan, packet):
    if not isinstance(plan, dict) or set(plan) != {'author', 'summary', 'scenes', 'open_questions'}:
        raise ProductionError('Plan fields must be author, summary, scenes, open_questions')
    require_text(plan['author'], 'author')
    require_text(plan['summary'], 'summary')
    if not isinstance(plan['open_questions'], list) or len(plan['open_questions']) > 30:
        raise ProductionError('Invalid open_questions')
    for question in plan['open_questions']:
        require_text(question, 'question')
    scenes = plan['scenes']
    if not isinstance(scenes, list) or not 1 <= len(scenes) <= 200:
        raise ProductionError('A plan needs 1..200 scenes')
    sources = {r['asset_id']: r for r in packet['references']}
    intervals = {key: [] for key in sources}
    for scene in scenes:
        if not isinstance(scene, dict) or set(scene) != {
                'source', 'observation', 'action', 'preserve', 'change', 'checks'}:
            raise ProductionError('Invalid scene fields')
        for key in ('observation', 'action'):
            require_text(scene[key], key)
        for key in ('preserve', 'change', 'checks'):
            text_list(scene[key], key)
        source = scene['source']
        if source is None and packet['order']['mode'] == 'new_video':
            continue
        if not isinstance(source, dict) or set(source) != {'asset_id', 'start', 'end'}:
            raise ProductionError('Reference scenes need a source interval')
        if source['asset_id'] not in sources:
            raise ProductionError('Unknown reference in scene')
        duration = sources[source['asset_id']]['duration_seconds']
        start = number(source['start'], 'scene start', 0, duration)
        end = number(source['end'], 'scene end', 0, duration)
        if end <= start:
            raise ProductionError('Scene interval must have positive duration')
        intervals[source['asset_id']].append((start, end))
    if packet['order']['mode'] in {'face_replace', 'body_replace'}:
        for asset_id, spans in intervals.items():
            cursor = 0
            for start, end in spans:
                if abs(start - cursor) > 0.001:
                    raise ProductionError('Replacement must cover reference in original order without gaps')
                cursor = end
            if abs(cursor - sources[asset_id]['duration_seconds']) > 0.001:
                raise ProductionError('Replacement must cover the full reference duration')


def connect_plans(db):
    db.execute("""CREATE TABLE IF NOT EXISTS scene_plans (
        order_id TEXT NOT NULL, revision INTEGER NOT NULL, request_id TEXT UNIQUE NOT NULL,
        request_sha256 TEXT NOT NULL, data TEXT NOT NULL,
        PRIMARY KEY (order_id, revision))""")


def save_plan(root, order_id, request):
    if not isinstance(request, dict) or set(request) != {
            'request_id', 'expected_revision', 'packet_sha256', 'plan'}:
        raise ProductionError('Invalid plan request')
    request_id = str(UUID(request['request_id']))
    revision = request['expected_revision']
    if type(revision) is not int or revision < 0:
        raise ProductionError('Invalid expected_revision')
    packet = order_evidence(root, order_id)
    if request['packet_sha256'] != packet['packet_sha256']:
        raise ProductionError('Evidence changed; reload it before planning')
    validate_plan(request['plan'], packet)
    intake = Intake(Path(root))
    fingerprint = object_digest(request)
    ident = packet['order']['id']
    with intake.connect() as db:
        connect_plans(db)
        db.execute('BEGIN IMMEDIATE')
        previous = db.execute('SELECT order_id,request_sha256,data FROM scene_plans WHERE request_id=?',
                              (request_id,)).fetchone()
        if previous:
            if previous[:2] != (ident, fingerprint):
                raise ProductionError('Plan request ID belongs to different content')
            return json.loads(previous[2])
        current = db.execute('SELECT COALESCE(MAX(revision),0) FROM scene_plans WHERE order_id=?',
                             (ident,)).fetchone()[0]
        if current != revision:
            raise ProductionError('Plan revision changed; reload before saving')
        result = {'order_id': ident, 'revision': current + 1,
                  'packet_sha256': packet['packet_sha256'], 'plan': request['plan'],
                  'status': 'needs_independent_review', 'generation_authorized': False,
                  'semantic_review': 'pending', 'artistic_review': 'pending', 'provider_calls': 0}
        db.execute('INSERT INTO scene_plans VALUES (?,?,?,?,?)',
                   (ident, current + 1, request_id, fingerprint, json.dumps(result, ensure_ascii=False)))
    return result


def latest_plan(root, order_id, packet_sha256):
    intake = Intake(Path(root))
    with intake.connect() as db:
        connect_plans(db)
        row = db.execute('SELECT data FROM scene_plans WHERE order_id=? ORDER BY revision DESC LIMIT 1',
                         (order_id,)).fetchone()
    if not row:
        return None
    plan = json.loads(row[0])
    if plan['packet_sha256'] != packet_sha256:
        plan['status'] = 'stale_evidence'
    return plan


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Export verified evidence or submit a scene proposal')
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--order-id', required=True)
    parser.add_argument('--submit', type=Path)
    args = parser.parse_args()
    result = (save_plan(args.root, args.order_id, read_json(args.submit)) if args.submit
              else order_evidence(args.root, args.order_id))
    print(json.dumps(result, ensure_ascii=False, indent=2))
