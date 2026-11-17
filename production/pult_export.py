"""One-shot metadata publication. The pult reads this cache, never Intake SQLite.

No scheduler, model, provider call, queue or schema migration is installed here.
The operator supplies the source root and the reviewed binding out of band.
"""
import argparse
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import time

from production.pult_link import SCHEMA, binding, collect, decode, fingerprint, view

MAX_CACHE_BYTES = 4096


def name_for(link):
    return 'order-' + fingerprint(binding(link)) + '.json'


@contextmanager
def directory_fd(directory, trusted_uid):
    path = Path(directory).absolute()
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('unsafe_cache_directory')
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        info = os.fstat(fd)
        if info.st_uid != trusted_uid or info.st_mode & 0o022:
            raise ValueError('unsafe_cache_directory')
        yield fd
    finally:
        os.close(fd)


def normalized(raw, link, now):
    """Publish only the already validated whitelist, including on collection failure."""
    result = view(raw, link, now=now)
    if result['state'] not in {'observed', 'unavailable', 'binding_mismatch'}:
        raise ValueError('invalid_export')
    if result['observed_at'] is None:
        raise ValueError('invalid_export')
    return dict(schema=SCHEMA, binding=link,
                **{key: result[key] for key in ('state', 'observed_at', 'preparation',
                   'analysis', 'preview', 'plan_revision', 'plan_review', 'read_only',
                   'finished_video_accepted')})


def read_snapshot(directory, link, *, trusted_uid=None):
    """Bounded local-file read for the pult; no database or source-root dependency."""
    link = binding(link)
    trusted_uid = os.geteuid() if trusted_uid is None else trusted_uid
    try:
        with directory_fd(directory, trusted_uid) as parent:
            fd = os.open(name_for(link), os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                         dir_fd=parent)
            try:
                info = os.fstat(fd)
                if (not stat.S_ISREG(info.st_mode) or info.st_uid != trusted_uid
                        or info.st_mode & 0o022 or info.st_nlink != 1
                        or not 0 < info.st_size <= MAX_CACHE_BYTES):
                    return None
                data = os.read(fd, MAX_CACHE_BYTES + 1)
                if len(data) != info.st_size or len(data) > MAX_CACHE_BYTES:
                    return None
                raw = decode(data)
                # Keep the original stamp. Rendering applies expiry; a read never refreshes it.
                return normalized(raw, link, raw.get('observed_at'))
            finally:
                os.close(fd)
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        return None


def run_worker(command, raw_binding, timeout):
    """subprocess.run kills and reaps its direct child on timeout; no detached work."""
    return subprocess.run(command, input=raw_binding, stdout=subprocess.PIPE,
                          stderr=subprocess.DEVNULL, timeout=timeout, check=True).stdout


def export_once(source_root, directory, link, *, timeout=3.0):
    link = binding(link)
    if not 0 < timeout <= 10:
        raise ValueError('invalid_timeout')
    # Directory must already exist and have one trusted writer. Never alter source rights.
    with directory_fd(directory, os.geteuid()) as parent:
        lock = os.open('.export.lock', os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK,
                       0o600, dir_fd=parent)
        try:
            lock_info = os.fstat(lock)
            if (not stat.S_ISREG(lock_info.st_mode) or lock_info.st_uid != os.geteuid()
                    or lock_info.st_nlink != 1 or lock_info.st_mode & 0o022):
                raise ValueError('unsafe_lock')
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise RuntimeError('export_busy') from None
            now = time.time()
            try:
                # Use this exact installed package, independent of the caller's cwd,
                # PYTHONPATH and Python startup customizations.
                bootstrap = 'import sys;sys.path.insert(0,sys.argv.pop(1));from production.pult_export import main;main()'
                raw = run_worker([sys.executable, '-I', '-c', bootstrap,
                                  str(Path(__file__).resolve().parent.parent), '_collect',
                                  '--source-root', str(Path(source_root).absolute())],
                                 json.dumps(link).encode(), timeout)
                snapshot = normalized(decode(raw), link, time.time())
            except (OSError, subprocess.SubprocessError, ValueError, TypeError, KeyError):
                # A failed refresh invalidates a previously successful observation.
                snapshot = {'schema': SCHEMA, 'binding': link, 'observed_at': now,
                            'state': 'unavailable', 'preparation': 'unavailable',
                            'analysis': 'unavailable', 'preview': 'unavailable',
                            'plan_revision': None, 'plan_review': 'not_observed',
                            'read_only': True, 'finished_video_accepted': False}
            payload = json.dumps(snapshot, ensure_ascii=False, allow_nan=False,
                                 separators=(',', ':')).encode()
            if len(payload) > MAX_CACHE_BYTES:
                raise ValueError('oversize_export')
            # Work relative to the validated directory FD, so a renamed parent cannot
            # redirect either the temporary file or the atomic replacement.
            temp_name = '.tmp-' + os.urandom(16).hex()
            temp_fd = os.open(temp_name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                              0o640, dir_fd=parent)
            try:
                with os.fdopen(temp_fd, 'wb') as handle:
                    # The deployment's setgid cache directory chooses its reader
                    # group. A restrictive producer umask must not remove that read.
                    os.fchmod(handle.fileno(), 0o640)
                    handle.write(payload); handle.flush(); os.fsync(handle.fileno())
                os.replace(temp_name, name_for(link), src_dir_fd=parent, dst_dir_fd=parent)
                os.fsync(parent)
            finally:
                try:
                    os.unlink(temp_name, dir_fd=parent)
                except FileNotFoundError:
                    pass
            return {'state': snapshot['state'], 'observed_at': snapshot['observed_at'],
                    'cache_name': name_for(link), 'bytes': len(payload)}
        finally:
            os.close(lock)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['export', '_collect'])
    parser.add_argument('--source-root', required=True)
    parser.add_argument('--cache-directory')
    parser.add_argument('--timeout', type=float, default=3)
    args = parser.parse_args()
    link = binding(decode(sys.stdin.buffer.read(MAX_CACHE_BYTES + 1)))
    if args.action == '_collect':
        result = collect(args.source_root, link)
    else:
        if not args.cache_directory:
            parser.error('--cache-directory is required for export')
        result = export_once(args.source_root, args.cache_directory, link, timeout=args.timeout)
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))


if __name__ == '__main__':
    main()
