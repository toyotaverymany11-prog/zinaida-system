import sys, os, logging, uuid
sys.path.insert(0, os.path.dirname(__file__))
from skill_validator import validate_skill
from skill_registry import SkillRegistry

logging.basicConfig(level=logging.INFO, format="%(asctime)s [SKILL-PIPELINE] %(message)s")
logger = logging.getLogger(__name__)

registry = SkillRegistry()

def process_raw_skill(raw: dict) -> dict:
    skill_id = raw.get("id", str(uuid.uuid4())[:8])
    code = raw.get("code", "")
    test_input = raw.get("test_input", {})
    expected = raw.get("expected_output", "")
    source = raw.get("source", "extracted")

    if not code:
        return {"status": "rejected", "reason": "empty_code"}

    registry.add(skill_id, source, code, test_input, expected)
    result = validate_skill(code, test_input, expected)
    registry.update_result(skill_id, result["score"], result["elapsed"], result["output"])

    current = registry._load()["skills"].get(skill_id, {})
    return {
        "skill_id": skill_id,
        "score": result["score"],
        "status": current.get("status"),
        "promoted": current.get("status") == "trusted",
        "elapsed": result["elapsed"]
    }

if __name__ == "__main__":
    logger.info("Pipeline ready. Import process_raw_skill to use.")
