import os, json, time, shutil, logging, glob
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [STATE-MGR] %(message)s")
logger = logging.getLogger(__name__)

BACKUP_DIR = "/opt/zinaida/backups"
STATE_FILES = [
    "/opt/zinaida/cache/skill_registry.json",
    "/opt/zinaida/sandbox/logs/sandbox_log.json",
    "/opt/zinaida/sandbox/logs/resolver_state.json"
]
MAX_SNAPSHOTS = 10

def create_snapshot(reason: str = "auto") -> str:
    ts = int(time.time())
    snap_dir = os.path.join(BACKUP_DIR, f"snapshot_{ts}")
    os.makedirs(snap_dir, exist_ok=True)
    
    manifest = {"timestamp": ts, "reason": reason, "files": []}
    for fpath in STATE_FILES:
        if os.path.exists(fpath):
            dest = os.path.join(snap_dir, os.path.basename(fpath))
            shutil.copy2(fpath, dest)
            manifest["files"].append(os.path.basename(fpath))
            
    with open(os.path.join(snap_dir, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
        
    cleanup_old_snapshots()
    logger.info(f"✅ Snapshot created: {snap_dir} ({reason})")
    return snap_dir

def list_snapshots() -> list:
    snaps = sorted(glob.glob(os.path.join(BACKUP_DIR, "snapshot_*")), reverse=True)
    result = []
    for s in snaps:
        mf = os.path.join(s, "manifest.json")
        if os.path.exists(mf):
            with open(mf) as f: result.append(json.load(f))
    return result

def rollback(snapshot_id: str) -> bool:
    snap_dir = os.path.join(BACKUP_DIR, snapshot_id)
    if not os.path.isdir(snap_dir):
        logger.error(f"Snapshot not found: {snapshot_id}")
        return False
        
    mf_path = os.path.join(snap_dir, "manifest.json")
    if not os.path.exists(mf_path): return False
    
    with open(mf_path) as f: manifest = json.load(f)
    
    for fname in manifest.get("files", []):
        src = os.path.join(snap_dir, fname)
        for orig in STATE_FILES:
            if os.path.basename(orig) == fname and os.path.exists(src):
                shutil.copy2(src, orig)
                logger.info(f"Restored: {orig}")
                
    logger.warning(f"🔄 Rollback complete: {snapshot_id}")
    return True

def cleanup_old_snapshots():
    snaps = sorted(glob.glob(os.path.join(BACKUP_DIR, "snapshot_*")))
    while len(snaps) > MAX_SNAPSHOTS:
        old = snaps.pop(0)
        shutil.rmtree(old, ignore_errors=True)
        logger.info(f"🗑️ Cleaned old snapshot: {old}")

if __name__ == "__main__":
    logger.info("State Manager ready.")
