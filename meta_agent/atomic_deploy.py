#!/usr/bin/env python3
import sys, os, shutil, subprocess, time, requests, json
import warnings
warnings.filterwarnings("ignore")

MAPPING = {
    "zinaida_router.py": "zinaida-router.service",
    "grigoriy_router.py": "grigoriy-router.service",
    "provider_monitor.py": "provider-monitor.service",
    "autopilot_loop.py": "zinaida-autopilot.service",
    "agent_runtime.py": "zinaida-runtime.service"
}
BACKUP_DIR = "/opt/zinaida/backups"
META_DIR = "/opt/zinaida/meta_agent"

def deploy(target_name, patch_path):
    if target_name not in MAPPING:
        print(f"Target {target_name} not in mapping")
        return False
    service = MAPPING[target_name]
    target_path = os.path.join(META_DIR, target_name)
    backup_path = os.path.join(BACKUP_DIR, f"{target_name}.bak_{int(time.time())}")
    
    if not os.path.exists(target_path):
        print(f"Target {target_path} missing")
        return False
        
    shutil.copy2(target_path, backup_path)
    shutil.copy2(patch_path, target_path)
    
    res = subprocess.run(["python3", "-m", "py_compile", target_path], capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Compile failed: {res.stderr}")
        shutil.copy2(backup_path, target_path)
        return False
        
    subprocess.run(["systemctl", "restart", service], capture_output=True)
    time.sleep(3)
    
    port = "8002" if "zinaida" in service else "8003"
    try:
        r = requests.get(f"http://127.0.0.1:{port}/health", timeout=5)
        if r.status_code == 200 and "ok" in r.text:
            return True
    except Exception:
        pass
        
    print("Health check failed, rolling back")
    shutil.copy2(backup_path, target_path)
    subprocess.run(["systemctl", "restart", service], capture_output=True)
    return False

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: atomic_deploy.py <target_file> <patch_path>")
        sys.exit(1)
    success = deploy(sys.argv[1], sys.argv[2])
    sys.exit(0 if success else 1)
