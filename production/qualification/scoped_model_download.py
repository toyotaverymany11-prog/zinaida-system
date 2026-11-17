"""Pilot-only transfer using short-lived per-file URLs, never a Hub account key.

The trusted controller supplies exact paths, byte counts and SHA-256 hashes.
This is a disposable /workspace probe, not a general public download endpoint.
"""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import time
import urllib.request
from urllib.parse import urlparse


def main():
    config = Path('/workspace/download-locations.private.json')
    root = Path('/workspace/comfy/models')
    rows = json.loads(config.read_text())
    started = time.time()
    deadline = time.monotonic() + 850
    def fetch(row):
        result = {'path': row['path'], 'expected_bytes': row['bytes']}
        try:
            target = root / row['path']
            if not target.resolve().is_relative_to(root.resolve()) or target.is_symlink():
                raise ValueError('Path outside models')
            u = urlparse(row['url'])
            if u.scheme != 'https' or u.hostname != 'us.aws.cdn.hf.co':
                raise ValueError('Unexpected model CDN')
            target.parent.mkdir(parents=True, exist_ok=True)
            # Only a smaller partial file from this pilot's interrupted SSH copy
            # may be removed. Never overwrite a complete or oversized model.
            if target.exists():
                if target.stat().st_size >= row['bytes']:
                    raise ValueError('Existing model requires independent verification')
                target.unlink()
            part = target.with_suffix(target.suffix + '.pilot-part')
            h = hashlib.sha256()
            count = 0
            with urllib.request.urlopen(row['url'], timeout=25) as response, part.open('xb') as out:
                while True:
                    if time.monotonic() >= deadline:
                        raise TimeoutError('Download deadline')
                    chunk = response.read(8 * 1024 * 1024)
                    if not chunk:
                        break
                    count += len(chunk)
                    if count > row['bytes']:
                        raise ValueError('Oversized model')
                    h.update(chunk)
                    out.write(chunk)
                out.flush()
                os.fsync(out.fileno())
            if count != row['bytes'] or h.hexdigest() != row['sha256']:
                raise ValueError('Model integrity mismatch')
            os.link(part, target)
            part.unlink()
            result.update(status='verified', bytes=count, sha256=h.hexdigest())
        except Exception as exc:
            # Exception messages can contain signed URLs. Do not log them.
            result.update(status='failed', error_type=type(exc).__name__)
        print(json.dumps(result), flush=True)
        return result
    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(fetch, rows))
        report = {'started_at': started, 'completed_at': time.time(), 'models': results,
                  'status': 'verified' if all(r['status'] == 'verified' for r in results) else 'failed'}
        Path('/workspace/model-download-report.json').write_text(json.dumps(report, indent=2))
    finally:
        config.unlink(missing_ok=True)


if __name__ == '__main__':
    main()
