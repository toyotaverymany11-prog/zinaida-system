"""Pilot-only transfer using short-lived per-file URLs, never a Hub account key.

The trusted controller supplies exact paths, byte counts and SHA-256 hashes.
This is a disposable /workspace probe, not a general public download endpoint.
"""
from concurrent.futures import ThreadPoolExecutor
import argparse
import hashlib
import json
import os
from pathlib import Path
import time
import urllib.request
from urllib.parse import urlparse


def transfer_estimate(sample_bytes, elapsed, total_bytes, remaining_seconds):
    if min(sample_bytes, elapsed, total_bytes, remaining_seconds) <= 0:
        raise ValueError('Positive transfer measurements required')
    rate = sample_bytes / elapsed
    # Reserve 25% for verification, small files and transfer variation.
    estimate = total_bytes / rate * 1.25
    return {'bytes_per_second': rate, 'estimated_seconds': estimate,
            'fits': estimate <= remaining_seconds}


def preflight(rows, deadline):
    url = rows[0]['url']
    u = urlparse(url)
    if u.scheme != 'https' or u.hostname != 'us.aws.cdn.hf.co':
        raise ValueError('Unexpected model CDN')
    limit = min(rows[0]['bytes'], 64 * 1024 * 1024)
    started = time.monotonic()
    request = urllib.request.Request(url, headers={'Range':f'bytes=0-{limit-1}'})
    count = 0
    with urllib.request.urlopen(request, timeout=10) as response:
        while count < limit:
            if time.monotonic() - started > 45:
                raise TimeoutError('Transfer sample deadline')
            block = response.read1(min(1024*1024, limit-count))
            if not block:
                raise ValueError('Incomplete transfer sample')
            count += len(block)
    elapsed = time.monotonic() - started
    result = transfer_estimate(count, elapsed, sum(r['bytes'] for r in rows), deadline-time.monotonic())
    result.update(sample_bytes=count, sample_seconds=elapsed)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--timeout', type=int, default=1500)
    args = parser.parse_args()
    if not 60 <= args.timeout <= 2100:
        raise ValueError('Transfer timeout must be 60..2100 seconds')
    config = Path('/workspace/download-locations.private.json')
    root = Path('/workspace/comfy/models')
    rows = json.loads(config.read_text())
    started = time.time()
    deadline = time.monotonic() + args.timeout
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
        sample = preflight(rows, deadline)
        Path('/workspace/transfer-preflight.json').write_text(json.dumps(sample, indent=2))
        print(json.dumps({'transfer_preflight':sample}), flush=True)
        if not sample['fits']:
            raise TimeoutError('Measured transfer cannot fit the original deadline')
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(fetch, rows))
        report = {'started_at': started, 'completed_at': time.time(), 'models': results,
                  'status': 'verified' if all(r['status'] == 'verified' for r in results) else 'failed'}
        Path('/workspace/model-download-report.json').write_text(json.dumps(report, indent=2))
    except Exception as exc:
        # Do not expose signed URL details, including on sample failure.
        Path('/workspace/model-download-report.json').write_text(json.dumps({
            'status':'failed', 'error_type':type(exc).__name__, 'completed_at':time.time()}))
        print(json.dumps({'status':'failed','error_type':type(exc).__name__}), flush=True)
        raise SystemExit(1) from None
    finally:
        config.unlink(missing_ok=True)


if __name__ == '__main__':
    main()
