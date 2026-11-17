"""Bind reviewed orders to bounded GPU attempts and explicit shot quality decisions.

HTTP preparation never spends money. Only the trusted owner CLI can execute,
using an existing exclusive Pod, an exact grant and a live independent guard.
"""
import argparse
import fcntl
import json
from pathlib import Path
import time
from uuid import UUID

from .core import ProductionError, Runtime, digest, local_asset, number, object_digest, read_json, write_json
from .intake import Intake
from .preview import approved_packet
from .recipes import ltx25_plan, ltx25_image_plan

CHECKS = ('prompt_match', 'geometry', 'temporal', 'cinematography', 'audio')


def shot_controls(ident, proposal, token, image_asset_id=None):
    from html import escape
    config = json.dumps({'order':str(UUID(ident)), 'token':token,
        'revision':proposal['revision'], 'packet':proposal['packet_sha256'],
        'scenes':len(proposal['plan']['scenes']), 'image_asset_id':image_asset_id}).replace('<', '\\u003c')
    return (Path(__file__).with_name('shots.html').read_text()
            .replace('__SHOT_CONFIG__', config).replace('__SHOT_NONCE__', escape(token, quote=True)))


def tables(db):
    db.execute('''CREATE TABLE IF NOT EXISTS shot_requests (
        request_id TEXT PRIMARY KEY, order_id TEXT NOT NULL,
        fingerprint TEXT NOT NULL, data TEXT NOT NULL)''')
    db.execute('''CREATE TABLE IF NOT EXISTS shot_reviews (
        request_id TEXT PRIMARY KEY, shot_id TEXT NOT NULL,
        fingerprint TEXT NOT NULL, data TEXT NOT NULL)''')


def folder(root, ident, request_id):
    return Path(root).resolve() / 'shots' / str(UUID(ident)) / str(UUID(request_id))


def load_request(root, ident, request_id):
    ident, request_id = str(UUID(ident)), str(UUID(request_id))
    with Intake(Path(root)).connect() as db:
        tables(db)
        row = db.execute('SELECT order_id,data FROM shot_requests WHERE request_id=?', (request_id,)).fetchone()
    if not row or row[0] != ident:
        raise ProductionError('Unknown shot request')
    return json.loads(row[1])


def check_current(root, ident, request, runtime):
    packet, proposal = approved_packet(root, ident, request, runtime)
    if object_digest(proposal['plan']) != request['plan_sha256']:
        raise ProductionError('Scene plan changed')
    if request.get('recipe') == 'ltx25-i2v':
        image_file(root, ident, request, runtime)
    return packet, proposal


def image_file(root, ident, request, runtime):
    image = request['input_image']
    if image['filename'] != image['sha256'] + '.png':
        raise ProductionError('Input image filename does not match its SHA')
    path = local_asset(folder(root, ident, request['request_id']), 'input/' + image['filename'])
    if digest(path, runtime) != image['sha256']:
        raise ProductionError('Prepared input image changed')
    return path


def recipe_plan(request, endpoint):
    args = (request['prompt'], request['seed'], 'shot-' + request['request_id'], endpoint)
    if request['recipe'] == 'ltx25-t2v':
        return ltx25_plan(*args)
    if request['recipe'] == 'ltx25-i2v':
        image = request['input_image']
        return ltx25_image_plan(*args, image['filename'], image['sha256'], image.get('frame_size'))
    raise ProductionError('Unknown shot recipe')


def prepare_shot(root, ident, request):
    ident = str(UUID(ident))
    fields = {'request_id', 'expected_revision', 'packet_sha256', 'scene_index', 'seed'}
    if not isinstance(request, dict) or set(request) not in (fields, fields | {'image_asset_id'}, fields | {'image_asset_id','framing'}):
        raise ProductionError('Invalid shot preparation request')
    request = dict(request, request_id=str(UUID(request['request_id'])))
    if type(request['scene_index']) is not int or type(request['seed']) is not int:
        raise ProductionError('Scene and seed must be integers')
    packet, proposal = approved_packet(root, ident, request, Runtime(30))
    order = packet['order']
    image_mode = 'image_asset_id' in request
    character_mode = (image_mode and len(order['characters']) == 1
                      and order['characters'][0]['id'] == request['image_asset_id'])
    if order['mode'] != 'new_video' or (order['characters'] and not character_mode) or (order['references'] and not image_mode):
        raise ProductionError('This T2V pilot cannot silently ignore references or character identity')
    if image_mode and (len(order['references']) != 1 or order['references'][0]['kind'] != 'image'
                       or order['references'][0]['id'] != request['image_asset_id']):
        raise ProductionError('I2V requires exactly one matching static reference')
    if character_mode:
        cast = proposal['plan'].get('cast', {})
        if len(cast) != 1 or list(cast.values()) != [[request['image_asset_id']]]:
            raise ProductionError('Single-image character trial needs one explicit cast assignment')
    scenes = proposal['plan']['scenes']
    if proposal['plan']['open_questions'] or not 0 <= request['scene_index'] < len(scenes):
        raise ProductionError('Resolve open questions and choose an existing scene')
    scene = scenes[request['scene_index']]
    if scene['source'] is not None:
        raise ProductionError('Source editing requires a qualified reference recipe')
    prompt = '\n'.join([scene['action'], 'Preserve: ' + '; '.join(scene['preserve']),
                       'Requested changes: ' + '; '.join(scene['change']),
                       'Check: ' + '; '.join(scene['checks'])])
    # Validate the fixed recipe without contacting any endpoint.
    image_data = None
    image = None
    if image_mode:
        import hashlib
        import io
        from PIL import Image, ImageOps
        source = local_asset(root, 'assets/' + request['image_asset_id'])
        if digest(source) != request['image_asset_id']:
            raise ProductionError('Reference image changed')
        with Image.open(source) as original:
            im = ImageOps.exif_transpose(original).convert('RGB')
            source_size={'width':im.width,'height':im.height}
            framing=request.get('framing')
            if framing is not None:
                if not isinstance(framing,dict) or set(framing)!={'width','height','fit'} or framing['fit']!='contain':
                    raise ProductionError('Explicit contain framing required')
                width,height=framing['width'],framing['height']
                if (any(type(v) is not int or not 256<=v<=1536 or v%64 for v in (width,height))
                        or width*height>1048576):
                    raise ProductionError('Invalid bounded framing dimensions')
                contained=ImageOps.contain(im,(width,height),method=Image.Resampling.LANCZOS)
                canvas=Image.new('RGB',(width,height),'black')
                canvas.paste(contained,((width-contained.width)//2,(height-contained.height)//2));im=canvas
            elif im.width * 704 != im.height * 1280:
                raise ProductionError('This first-frame recipe requires the 1280:704 aspect ratio; no implicit crop')
            stream = io.BytesIO(); im.save(stream, format='PNG')
        image_data = stream.getvalue()
        sha = hashlib.sha256(image_data).hexdigest()
        image = {'asset_id':request['image_asset_id'], 'sha256':sha, 'filename':sha+'.png',
                 'width':im.width, 'height':im.height, 'transform':'exif_transpose_rgb_png_no_crop'}
        if framing is not None:
            image.update(frame_size={'width':im.width,'height':im.height},source_size=source_size,
                         transform='exif_transpose_rgb_contain_black_padding_no_crop')
        plan = ltx25_image_plan(prompt, request['seed'], 'shot-'+request['request_id'],
                                'http://127.0.0.1:8188', image['filename'], sha, image.get('frame_size'))
    else:
        plan = ltx25_plan(prompt, request['seed'], 'shot-' + request['request_id'], 'http://127.0.0.1:8188')
    fingerprint = object_digest(request)
    result = dict(request, order_id=ident, request_sha256=fingerprint,
                  plan_sha256=object_digest(proposal['plan']), prompt=prompt,
                  recipe='ltx25-i2v' if image_mode else 'ltx25-t2v', workflow_sha256=plan['workflow_sha256'],
                  duration_scope='five_second_technical_shot', generation_authorized=False,
                  finished_video_accepted=False, status='prepared')
    if image_mode:
        result.update(input_image=image, required_checks=[*CHECKS, 'first_frame_match'])
        if framing is not None:result['required_checks'].append('framing_match')
        if character_mode:
            result['required_checks'].append('identity')
            result['identity_scope']='single_image_animation_trial_not_cross_scene_qualification'
    with Intake(Path(root)).connect() as db:
        tables(db)
        db.execute('BEGIN IMMEDIATE')
        previous = db.execute('SELECT order_id,fingerprint,data FROM shot_requests WHERE request_id=?',
                              (request['request_id'],)).fetchone()
        if previous:
            if previous[:2] != (ident, fingerprint):
                raise ProductionError('Shot request ID reused for different content')
            existing = json.loads(previous[2])
            if image_mode:
                image_file(root, ident, existing, Runtime(30))
            return existing
        if image_mode:
            target = folder(root, ident, request['request_id'])/'input'/image['filename']
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                if digest(target) != image['sha256']:
                    raise ProductionError('Existing input image changed')
            else:
                with target.open('xb') as stream:
                    stream.write(image_data)
        db.execute('INSERT INTO shot_requests VALUES (?,?,?,?)',
                   (request['request_id'], ident, fingerprint, json.dumps(result, ensure_ascii=False)))
    return result


def shot_state(root, ident, request_id=None):
    ident = str(UUID(ident))
    with Intake(Path(root)).connect() as db:
        tables(db)
        if request_id is None:
            row = db.execute('SELECT request_id FROM shot_requests WHERE order_id=? ORDER BY rowid DESC LIMIT 1',
                             (ident,)).fetchone()
            if not row:
                return {'status': 'not_requested', 'finished_video_accepted': False}
            request_id = row[0]
    request = load_request(root, ident, request_id)
    result = {key: request[key] for key in ('request_id', 'expected_revision', 'packet_sha256', 'scene_index')}
    result.update(status='prepared', finished_video_accepted=False, generation_authorized=False)
    result['required_checks'] = request.get('required_checks', list(CHECKS))
    path = folder(root, ident, request_id) / 'result.json'
    if path.exists():
        receipt = read_json(path)
        if receipt.get('request_sha256') != request['request_sha256']:
            raise ProductionError('Shot receipt belongs to another request')
        result.update(receipt)
    with Intake(Path(root)).connect() as db:
        review = db.execute('SELECT data FROM shot_reviews WHERE shot_id=? ORDER BY rowid DESC LIMIT 1',
                            (request_id,)).fetchone()
    if review:
        result['quality_review'] = json.loads(review[0])
    result['project_available'] = False
    if (folder(root,ident,request_id)/'edit/project-package.json').exists():
        from .shot_edit import project_file
        try:
            project_file(root,ident,request_id)
            result['project_available'] = True
        except (ProductionError, OSError, KeyError, ValueError):
            pass
    try:
        check_current(root, ident, request, Runtime(30))
    except ProductionError:
        result.update(status='stale_plan', finished_video_accepted=False)
    return result


def shot_file(root, ident, request_id):
    request = load_request(root, ident, request_id)
    runtime = Runtime(30)
    check_current(root, ident, request, runtime)
    receipt = read_json(folder(root, ident, request_id) / 'result.json')
    if receipt.get('status') != 'needs_quality_review' or receipt.get('request_sha256') != request['request_sha256']:
        raise ProductionError('No verified generated shot is available')
    base = folder(root, ident, request_id)
    path = local_asset(base, receipt['output_file'])
    if digest(path, runtime) != receipt['output_sha256']:
        raise ProductionError('Generated media changed')
    return path


def review_shot(root, ident, request_id, review):
    if not isinstance(review, dict) or set(review) != {'request_id','output_sha256','decision','checks','notes'}:
        raise ProductionError('Invalid shot review')
    rid = str(UUID(review['request_id']))
    if review['decision'] not in {'accept_shot','reject_shot'}:
        raise ProductionError('Unknown shot decision')
    request = load_request(root, ident, request_id)
    if (not isinstance(review['checks'], dict) or set(review['checks']) != set(request.get('required_checks', CHECKS))
            or any(type(v) is not bool for v in review['checks'].values())):
        raise ProductionError('Every quality criterion needs an explicit decision')
    from .planning import require_text
    require_text(review['notes'], 'quality notes')
    if review['decision'] == 'accept_shot' and not all(review['checks'].values()):
        raise ProductionError('A failed quality criterion cannot be accepted')
    path = shot_file(root, ident, request_id)
    if digest(path) != review['output_sha256']:
        raise ProductionError('Quality decision refers to another output')
    fingerprint = object_digest(review)
    result = dict(review, shot_id=str(UUID(request_id)), scope='local_shot_quality_only',
                  identity_authenticated=False, finished_video_accepted=False)
    with Intake(Path(root)).connect() as db:
        tables(db)
        db.execute('BEGIN IMMEDIATE')
        old = db.execute('SELECT shot_id,fingerprint,data FROM shot_reviews WHERE request_id=?',(rid,)).fetchone()
        if old:
            if old[:2] != (request_id, fingerprint):
                raise ProductionError('Quality request ID reused for different content')
            return json.loads(old[2])
        db.execute('INSERT INTO shot_reviews VALUES (?,?,?,?)',(rid,request_id,fingerprint,json.dumps(result,ensure_ascii=False)))
    return result


def execute_shot(root, ident, request_id, grant, lease_path, guard_root, credential_file,
                 *, execute_authorized=False):
    from .comfy import Executor
    from .rental import RunpodControl, enforce, validate_lease
    from .rental_guard import guard_status, private_token
    request = load_request(root, ident, request_id)
    lease = read_json(lease_path)
    validate_lease(lease)
    if (not execute_authorized or grant.get('approved') is not True
            or grant.get('request_sha256') != request['request_sha256']
            or grant.get('lease_sha256') != object_digest(lease)):
        raise ProductionError('Owner grant does not match this shot and rental')
    seconds = number(grant.get('max_runtime_seconds'), 'shot runtime', 1, 1800)
    budget = number(grant.get('budget_usd'), 'shot budget', 0.0001, lease['budget_usd'])
    if seconds * lease['hourly_total_usd'] / 3600 > budget:
        raise ProductionError('Runtime exceeds the granted shot budget')
    plan = recipe_plan(request, grant['endpoint'])
    if plan['workflow_sha256'] != request['workflow_sha256']:
        raise ProductionError('Prepared recipe changed')
    base = folder(root, ident, request_id)
    base.mkdir(parents=True, exist_ok=True)
    with (base / 'attempt.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ProductionError('This shot attempt is already active') from None
        check_current(root, ident, request, Runtime(30))
        result_path = base / 'result.json'
        if result_path.exists() and read_json(result_path).get('status') == 'needs_quality_review':
            shot_file(root, ident, request_id)
            return read_json(result_path)
        binding = {'request_sha256': request['request_sha256'], 'grant_sha256': object_digest(grant),
                   'lease_sha256': object_digest(lease), 'workflow_sha256': plan['workflow_sha256']}
        intent = base / 'intent.json'
        if intent.exists() and read_json(intent) != binding:
            raise ProductionError('Existing attempt cannot change grant, workflow or rental')
        if not guard_status(guard_root, lease)['ready'] or lease['terminate_at_epoch'] - time.time() < seconds + 15:
            raise ProductionError('Live guard and sufficient original lease lifetime are required')
        control = RunpodControl(private_token(credential_file))
        write_json(intent, binding)
        result = dict(binding, request_id=request_id, status='running', finished_video_accepted=False)
        write_json(result_path, result)
        runtime = Runtime(seconds)
        try:
            executor = Executor(plan['endpoint'], base / 'executor')
            authorization = {k: plan[k] for k in ('job_id','endpoint','workflow_sha256')}
            authorization.update(approved=True, max_runtime_seconds=seconds,
                                 gpu_hourly_usd=lease['hourly_total_usd'], budget_usd=budget)
            executor.submit(plan, authorization, execute_authorized=True)
            while True:
                runtime.check()
                check_current(root, ident, request, runtime)
                if not guard_status(guard_root, lease)['ready']:
                    raise ProductionError('Rental guard is no longer live')
                state = executor.reconcile(plan['job_id'])
                if state['state'] in {'generated_unverified', 'downloaded_unverified'}:
                    break
                if state['state'] not in {'running','queued','submitted'} or state.get('requires_controller_stop'):
                    raise ProductionError('GPU outcome failed or is unknown; no automatic new attempt')
                time.sleep(.5)
            output = base / 'download'
            # An interrupted download is not silently overwritten or regenerated.
            if (output / 'downloads.json').exists():
                download = read_json(output / 'downloads.json')
            else:
                download = executor.download(plan['job_id'], output)
            files = download['files']
            if len(files) != 1 or not files[0]['file'].endswith('.mp4'):
                raise ProductionError('Expected exactly one video from the pinned recipe')
            video = local_asset(output, files[0]['file'])
            if digest(video, runtime) != files[0]['sha256']:
                raise ProductionError('Downloaded media integrity mismatch')
            from .media import ffmpeg
            from .core import probe
            runtime.run(ffmpeg('-i', video, '-f', 'null', '-'))
            metadata = probe(video, runtime)
            check_current(root, ident, request, runtime)
            result.update(status='needs_quality_review', output_file=str(video.relative_to(base)),
                          output_sha256=files[0]['sha256'], probe=metadata,
                          finished_video_accepted=False)
            write_json(result_path, result)
            return result
        except BaseException as exc:
            result.update(status='interrupted_or_failed', error_type=type(exc).__name__)
            write_json(result_path, result)
            raise
        finally:
            # Every trusted execution owns this disposable rental; also cover
            # cancellation, revoked plans, failed inference and failed download.
            enforce(lease, control, base / 'rental-cleanup.json', Runtime(lease['cleanup_allowance_seconds']),
                    execute_authorized=True, force_due=True)


def main():
    p = argparse.ArgumentParser(description='Execute one prepared shot on an owner-granted guarded Pod')
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--order-id', required=True)
    p.add_argument('--request-id', required=True)
    p.add_argument('--grant', type=Path, required=True)
    p.add_argument('--lease', type=Path, required=True)
    p.add_argument('--guard-root', type=Path, required=True)
    p.add_argument('--credential-file', type=Path, required=True)
    p.add_argument('--execute-authorized', action='store_true')
    a = p.parse_args()
    from .model_install import cancel_on_signal
    with cancel_on_signal():
        result = execute_shot(a.root, a.order_id, a.request_id, read_json(a.grant), a.lease,
                              a.guard_root, a.credential_file, execute_authorized=a.execute_authorized)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
