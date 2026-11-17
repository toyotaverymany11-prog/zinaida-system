"""Private Hugging Face download subprocess. No inference or executable repo code."""
import json
import os
from pathlib import Path
import sys


def main():
    from huggingface_hub import get_hf_file_metadata, hf_hub_download, hf_hub_url
    request = json.loads(Path(sys.argv[1]).read_text())
    model = request['model']
    url = hf_hub_url(request['repo_id'], model['path'], revision=request['revision'],
                    endpoint='https://huggingface.co')
    metadata = get_hf_file_metadata(url, token=True, timeout=10)
    if (metadata.commit_hash != request['revision'] or metadata.size != model['bytes']
            or metadata.etag != model.get('etag', model['sha256'])):
        raise ValueError('Pinned metadata mismatch')
    if not request['metadata_only']:
        hf_hub_download(request['repo_id'], model['path'], revision=request['revision'],
                        local_dir=request['directory'], token=True, etag_timeout=10,
                        endpoint='https://huggingface.co')
    print(json.dumps({'status': 'metadata_verified' if request['metadata_only'] else 'downloaded',
                      'path': model['path'], 'bytes': metadata.size,
                      'revision': metadata.commit_hash, 'etag': metadata.etag}))


if __name__ == '__main__':
    os.umask(0o077)
    try:
        main()
    except Exception as exc:
        # Exception text may carry an authorization header or signed redirect URL.
        print(json.dumps({'status': 'failed', 'error_type': type(exc).__name__}))
        sys.exit(2)
