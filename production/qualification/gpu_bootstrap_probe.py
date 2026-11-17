"""Qualify a disposable GPU container; never creates cloud resources.

Run only inside the pinned, caller-owned pilot container. The rental guard
remains on the independent control host. This probe never exposes ComfyUI.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--timeout', type=int, default=600)
    args = p.parse_args()
    root = args.root.resolve()
    if root != Path('/workspace') or not 60 <= args.timeout <= 900:
        raise ValueError('Probe accepts only /workspace in the disposable container')
    # Reuse CUDA libraries from the pinned disposable image, while installing
    # Comfy-specific packages into a separate overlay rather than system Python.
    overlay = root / 'gpu-venv'
    if Path(sys.prefix).resolve() != overlay:
        import venv
        venv.EnvBuilder(with_pip=True, system_site_packages=True).create(overlay)
        os.execv(str(overlay / 'bin/python'), [str(overlay / 'bin/python'), *sys.argv])
    import torch
    if not torch.cuda.is_available():
        raise RuntimeError('A real CUDA device is required')
    start = time.monotonic()
    def run(command):
        remaining = args.timeout - (time.monotonic() - start)
        if remaining <= 0:
            raise TimeoutError('Bootstrap deadline reached')
        return subprocess.run(command, cwd=root, check=True, timeout=remaining)
    report = {'torch': torch.__version__, 'cuda': torch.version.cuda,
              'dependency_isolation': 'venv_overlay_on_pinned_disposable_image',
              'gpu': torch.cuda.get_device_name(0),
              'memory_bytes': torch.cuda.get_device_properties(0).total_memory,
              'artistic_qualification': False}
    # A small actual CUDA operation, including synchronization and finite output.
    x = torch.randn(1, 4, 3, 16, 16, device='cuda', dtype=torch.bfloat16)
    w = torch.randn(4, 4, 3, 3, 3, device='cuda', dtype=torch.bfloat16)
    y = torch.nn.functional.conv3d(x, w, padding=1)
    torch.cuda.synchronize()
    report['bf16_conv3d_pass'] = bool(torch.isfinite(y).all().item())
    del x, w, y
    torch.cuda.empty_cache()
    if not report['bf16_conv3d_pass']:
        raise RuntimeError('CUDA arithmetic failed')
    for name in ('comfy', 'worker'):
        run(['tar', '-xzf', str(root / (name + '.tar.gz')), '-C', str(root)])
    constraints = root / 'comfy-constraints.txt'
    import torchvision
    with constraints.open('a') as f:
        f.write('torch==' + torch.__version__ + '\n')
        f.write('torchvision==' + torchvision.__version__ + '\n')
    run([sys.executable, '-m', 'pip', 'install', '--no-cache-dir',
         '-r', str(root / 'comfy/requirements.txt'), '-c', str(constraints)])
    run([sys.executable, '-m', 'pip', 'check'])
    with (root / 'gpu-freeze.txt').open('w') as f:
        subprocess.run([sys.executable, '-m', 'pip', 'freeze'], stdout=f,
                       check=True, timeout=30)
    with (root / 'comfy.log').open('a') as log:
        child = subprocess.Popen([sys.executable, 'main.py', '--listen', '127.0.0.1',
                                  '--port', '8188', '--disable-auto-launch'],
                                 cwd=root / 'comfy', stdout=log, stderr=log,
                                 stdin=subprocess.DEVNULL, start_new_session=True)
    report['comfy_pid'] = child.pid
    try:
        deadline = min(start + args.timeout, time.monotonic() + 90)
        while time.monotonic() < deadline:
            if child.poll() is not None:
                raise RuntimeError('ComfyUI exited during startup')
            try:
                with urllib.request.urlopen('http://127.0.0.1:8188/system_stats', timeout=2) as r:
                    report['system_stats'] = json.load(r)
                report['status'] = 'gpu_runtime_ready_not_model_qualified'
                break
            except (OSError, ValueError):
                time.sleep(1)
        else:
            raise TimeoutError('ComfyUI startup deadline reached')
    except BaseException:
        child.terminate()
        try:
            child.wait(timeout=10)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait(timeout=10)
        raise
    report['elapsed_seconds'] = time.monotonic() - start
    (root / 'gpu-runtime-report.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report))


if __name__ == '__main__':
    main()
