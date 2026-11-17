"""Bounded, resumable installation using Hugging Face's existing downloader.

No rentals, generation or package installation. The caller owns a private model
directory. Completed weights are promoted only after full size/SHA verification.
"""
import fcntl
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import signal
import threading
import time
from contextlib import contextmanager

from .core import Cancelled, ProductionError, digest, number, object_digest, write_json


@contextmanager
def cancel_on_signal():
    """CLI termination reaches Runtime cleanup, which owns the download process group."""
    if threading.current_thread() is not threading.main_thread():
        raise ProductionError('Signal supervision must run on the main thread')
    def cancel(*_):
        raise Cancelled('Model installation stopped by signal')
    previous = {s: signal.getsignal(s) for s in (signal.SIGTERM, signal.SIGINT)}
    try:
        for s in previous:
            signal.signal(s, cancel)
        yield
    finally:
        for s, handler in previous.items():
            signal.signal(s, handler)


def validate_lock(lock):
    if not isinstance(lock, dict) or not re.fullmatch(r'[\w.-]+/[\w.-]+', lock.get('repo_id', '')):
        raise ProductionError('Invalid model repository')
    if not re.fullmatch(r'[a-f0-9]{40}', lock.get('revision', '')):
        raise ProductionError('A full pinned model commit is required')
    models = lock.get('models')
    if not isinstance(models, list) or not 1 <= len(models) <= 64:
        raise ProductionError('Expected 1..64 exact model files')
    names = set()
    for model in models:
        name = model.get('path', '')
        if (not isinstance(name, str) or not name or len(name) > 300
                or name != str(PurePosixPath(name)) or PurePosixPath(name).is_absolute()
                or any(p in {'..', '.'} or p.startswith('.') for p in PurePosixPath(name).parts)
                or any(c in name for c in ('\\', ':', '\n', '\r', '\x00')) or name in names):
            raise ProductionError('Invalid or duplicate model path')
        names.add(name)
        if not isinstance(model.get('bytes'), int):
            raise ProductionError('Model size must be an integer')
        number(model['bytes'], 'model bytes', 1, 2**50)
        if not re.fullmatch(r'[a-f0-9]{64}', model.get('sha256', '')):
            raise ProductionError('Exact SHA-256 is required')
        etag = model.get('etag', model['sha256'])
        if not re.fullmatch(r'(?:[a-f0-9]{40}|[a-f0-9]{64})', etag):
            raise ProductionError('Invalid source ETag')
    if sum(m['bytes'] for m in models) != lock.get('total_model_bytes'):
        raise ProductionError('Model byte total mismatch')


def safe_path(root, relative):
    """Disallow links even inside root: installation must not mutate another cache."""
    path = root
    for part in Path(relative).parts:
        path = path / part
        if path.is_symlink():
            raise ProductionError('Model installation paths cannot be symlinks')
    if not path.resolve().is_relative_to(root):
        raise ProductionError('Model path leaves the installation directory')
    return path


def inspect_install(lock, root, runtime, reserve_bytes=1024**3):
    validate_lock(lock)
    number(reserve_bytes, 'disk reserve', 0)
    root = Path(root).resolve()
    rows = []
    for model in lock['models']:
        runtime.check()
        path = safe_path(root, model['path'])
        status = 'missing'
        if path.exists():
            status = ('verified' if path.is_file() and path.stat().st_size == model['bytes']
                      and digest(path, runtime) == model['sha256'] else 'conflict')
        rows.append({'path': model['path'], 'bytes': model['bytes'], 'status': status})
    remaining = sum(m['bytes'] for m in rows if m['status'] == 'missing')
    parent = root
    while not parent.exists():
        parent = parent.parent
    free = shutil.disk_usage(parent).free
    return {'schema_version': 1, 'recipe_lock_sha256': object_digest(lock),
            'repo_id': lock['repo_id'], 'revision': lock['revision'], 'models': rows,
            'status': 'conflict' if any(m['status'] == 'conflict' for m in rows)
                      else 'installed_verified' if not remaining else 'download_required',
            'total_model_bytes': lock['total_model_bytes'], 'remaining_model_bytes': remaining,
            'required_free_bytes': remaining + reserve_bytes if remaining else 0,
            'free_bytes': free, 'disk_sufficient': not remaining or free >= remaining + reserve_bytes,
            'download_authorized': False, 'generation_authorized': False, 'gpu_qualified': False,
            'note': 'Conservative disk estimate; partial downloads are retained but not deducted.'}


@contextmanager
def installation_lock(root, runtime):
    root.mkdir(parents=True, exist_ok=True)
    state = safe_path(root, '.production-install')
    state.mkdir(mode=0o700, exist_ok=True)
    path = safe_path(root, '.production-install/install.lock')
    with path.open('a') as handle:
        while True:
            runtime.check()
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                time.sleep(.05)
        try:
            yield state
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def _hub_call(lock, model, stage, python, runtime, metadata_only=False):
    stage.mkdir(parents=True, exist_ok=True)
    request = stage.parent / 'request.json'
    write_json(request, {'repo_id': lock['repo_id'], 'revision': lock['revision'],
                         'model': model, 'directory': str(stage), 'metadata_only': metadata_only})
    env = {k: v for k, v in os.environ.items()
           if k in {'PATH', 'HOME', 'LANG', 'HF_HOME', 'HF_TOKEN_PATH', 'HF_TOKEN'}}
    env.update(HF_ENDPOINT='https://huggingface.co', HF_HUB_DISABLE_TELEMETRY='1',
               HF_HUB_DISABLE_PROGRESS_BARS='1', HF_HUB_DISABLE_XET='1',
               HF_HUB_ETAG_TIMEOUT='10', HF_HUB_DOWNLOAD_TIMEOUT='15')
    try:
        result = runtime.run([str(python), '-I', str(Path(__file__).with_name('hf_download_child.py')),
                              str(request)], cwd=stage, env=env)
        response = json.loads(result)
    except Cancelled:
        raise
    except (ProductionError, ValueError, OSError):
        # Provider errors can contain credentials or signed URLs. Never persist them.
        raise ProductionError('Hugging Face transfer failed; inspect access and connectivity') from None
    if response.get('status') != ('metadata_verified' if metadata_only else 'downloaded'):
        raise ProductionError('Unexpected Hugging Face worker result')
    return response


def check_remote(lock, root, python, runtime):
    """HEAD metadata only, including every file's pinned revision, size and ETag."""
    validate_lock(lock)
    root = Path(root).resolve()
    with installation_lock(root, runtime) as state:
        stage = safe_path(root, '.production-install/' + object_digest(lock) + '/staging')
        results = [_hub_call(lock, m, stage, python, runtime, metadata_only=True)
                   for m in lock['models']]
        result = {'status': 'remote_metadata_verified', 'recipe_lock_sha256': object_digest(lock),
                  'models': results, 'model_bytes_downloaded': 0, 'generation_authorized': False}
        write_json(state / 'remote-check.json', result)
        return result


def install(lock, root, python, runtime, *, download_authorized=False,
            max_download_bytes=0, reserve_bytes=1024**3):
    validate_lock(lock)
    number(max_download_bytes, 'download byte limit', 0)
    number(reserve_bytes, 'disk reserve', 0)
    if download_authorized is not True:
        raise ProductionError('Explicit model download authorization is required')
    root = Path(root).resolve()
    with installation_lock(root, runtime) as state:
        report = inspect_install(lock, root, runtime, reserve_bytes)
        if report['status'] == 'conflict':
            raise ProductionError('Existing model differs from lock; it was not replaced')
        if report['remaining_model_bytes'] > max_download_bytes:
            raise ProductionError('Missing model sizes exceed the download byte limit')
        if not report['disk_sufficient']:
            raise ProductionError('Insufficient disk space including reserve')
        receipt_path = safe_path(root, '.production-install/' + object_digest(lock) + '/receipt.json')
        stage = safe_path(root, '.production-install/' + object_digest(lock) + '/staging')
        receipt = {'schema_version': 1, 'recipe_lock_sha256': object_digest(lock),
                   'status': 'installing', 'started_at': time.time(), 'models': [],
                   'generation_authorized': False, 'gpu_qualified': False}
        write_json(receipt_path, receipt)
        try:
            for model, row in zip(lock['models'], report['models']):
                runtime.check()
                target = safe_path(root, model['path'])
                if row['status'] == 'verified':
                    receipt['models'].append(dict(row, action='reused_verified'))
                else:
                    candidate = safe_path(stage, model['path'])
                    # Crash after download/before promotion reuses only verified bytes.
                    ready = (candidate.is_file() and candidate.stat().st_size == model['bytes']
                             and digest(candidate, runtime) == model['sha256'])
                    if candidate.exists() and not ready:
                        raise ProductionError('Staged file failed verification; original retained')
                    if not ready:
                        if shutil.disk_usage(root).free < model['bytes'] + reserve_bytes:
                            raise ProductionError('Disk reserve would be exhausted')
                        _hub_call(lock, model, stage, python, runtime)
                    candidate = safe_path(stage, model['path'])
                    if (not candidate.is_file() or candidate.stat().st_size != model['bytes']
                            or digest(candidate, runtime) != model['sha256']):
                        raise ProductionError('Downloaded model size or SHA-256 mismatch')
                    runtime.check()
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target = safe_path(root, model['path'])
                    with candidate.open('rb') as handle:
                        os.fsync(handle.fileno())
                    # Atomic no-replace promotion on the same filesystem; no second 40 GB copy.
                    os.link(candidate, target)
                    candidate.unlink()
                    directory = os.open(target.parent, os.O_RDONLY | os.O_DIRECTORY)
                    try:
                        os.fsync(directory)
                    finally:
                        os.close(directory)
                    receipt['models'].append(dict(row, status='verified', action='installed_verified'))
                write_json(receipt_path, receipt)
            receipt.update(status='installed_verified', completed_at=time.time())
            write_json(receipt_path, receipt)
            return receipt
        except BaseException as exc:
            receipt.update(status='interrupted' if isinstance(exc, (Cancelled, KeyboardInterrupt)) else 'failed',
                           error_type=type(exc).__name__)
            write_json(receipt_path, receipt)
            raise
