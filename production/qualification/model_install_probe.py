"""Tiny real Hub transfer through the installer; never download model weights."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

from production.core import ProductionError, Runtime, write_json
from production import model_install
from production.recipes import WORKFLOWS


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    from huggingface_hub import get_hf_file_metadata, hf_hub_url, hf_hub_download
    lock=json.loads((WORKFLOWS/'ltx25-t2v.lock.json').read_text())
    url=hf_hub_url(lock['repo_id'],'README.md',revision=lock['revision'])
    meta=get_hf_file_metadata(url,token=True,timeout=10)
    assert meta.size is not None and 0<meta.size<=128*1024
    assert meta.commit_hash==lock['revision'] and len(meta.etag)==40
    source=Path(hf_hub_download(lock['repo_id'],'README.md',revision=lock['revision'],
                               local_dir=args.output/'truth',token=True,etag_timeout=10))
    data=source.read_bytes()
    assert len(data)==meta.size
    assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\x00'+data).hexdigest()==meta.etag
    spec={'repo_id':lock['repo_id'],'revision':lock['revision'],
          'models':[{'path':'README.md','bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),
                     'etag':meta.etag}], 'total_model_bytes':len(data)}
    root=args.output/'installed'
    first=model_install.install(spec,root,Path(sys.executable),Runtime(45),
                                download_authorized=True,max_download_bytes=128*1024)
    original=model_install._hub_call
    def no_network(*_args,**_kwargs):raise AssertionError('Unexpected second Hub request')
    model_install._hub_call=no_network
    try:
        second=model_install.install(spec,root,Path(sys.executable),Runtime(10),
                                     download_authorized=True,max_download_bytes=0)
        assert second['models'][0]['action']=='reused_verified'
        (root/'README.md').write_bytes(b'X'*len(data))
        try:
            model_install.install(spec,root,Path(sys.executable),Runtime(10),
                                  download_authorized=True,max_download_bytes=128*1024)
        except ProductionError:
            corruption_blocked=True
        else:
            raise AssertionError('Corruption was accepted')
    finally:
        model_install._hub_call=original
    report={'real_hub_download_verified':first['status']=='installed_verified',
            'test_file_bytes':len(data),'cached_retry_hub_calls':0,
            'same_size_corruption_blocked':corruption_blocked,
            'model_weights_downloaded':False,'generation_authorized':False,
            'repo_id':lock['repo_id'],'revision':lock['revision']}
    write_json(args.output/'report.json',report)
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
