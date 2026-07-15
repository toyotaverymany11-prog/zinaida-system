import json, os, time, fcntl, logging
from pathlib import Path
from state_manager import create_snapshot

logging.basicConfig(level=logging.INFO, format="%(asctime)s [SKILL-REGISTRY] %(message)s")
logger = logging.getLogger(__name__)

REGISTRY_PATH = "/opt/zinaida/cache/skill_registry.json"

class SkillRegistry:
    def __init__(self):
        self.path = REGISTRY_PATH
        if not os.path.exists(self.path):
            self._save({"skills": {}, "meta": {"updated": time.time()}})

    def _load(self):
        with open(self.path, "r") as f:
            fcntl.flock(f, fcntl.LOCK_SH)
            data = json.load(f)
            fcntl.flock(f, fcntl.LOCK_UN)
        return data

    def _save(self, data):
        tmp = self.path + ".tmp"
        with open(tmp, "w") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            json.dump(data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
            fcntl.flock(f, fcntl.LOCK_UN)
        os.replace(tmp, self.path)

    def add(self, skill_id, source, code, test_input, expected_output):
        data = self._load()
        data["skills"][skill_id] = {
            "status": "pending",
            "source": source,
            "code": code,
            "test_input": test_input,
            "expected_output": expected_output,
            "score": 0.0,
            "runs": 0,
            "successes": 0,
            "created": time.time(),
            "updated": time.time()
        }
        self._save(data)
        logger.info(f"Skill {skill_id} added as pending")

    def update_result(self, skill_id, score, elapsed, output):
        data = self._load()
        if skill_id not in data["skills"]: return
        s = data["skills"][skill_id]
        s["runs"] += 1
        s["score"] = score
        s["last_output"] = output
        s["updated"] = time.time()
        if score >= 0.8:
            s["successes"] += 1
        if s["successes"] >= 3 and s["status"] == "tested":
            s["status"] = "trusted"
            logger.info(f"Skill {skill_id} promoted to trusted")
            create_snapshot(reason=f"skill_{skill_id}_trusted")
        elif s["status"] == "pending":
            s["status"] = "tested"
        self._save(data)

    def get_trusted(self):
        data = self._load()
        return {k: v for k, v in data["skills"].items() if v["status"] == "trusted"}

    def deprecate(self, skill_id, reason="manual"):
        data = self._load()
        if skill_id in data["skills"]:
            data["skills"][skill_id]["status"] = "deprecated"
            data["skills"][skill_id]["deprecation_reason"] = reason
            data["skills"][skill_id]["updated"] = time.time()
            self._save(data)
            logger.info(f"Skill {skill_id} deprecated: {reason}")
