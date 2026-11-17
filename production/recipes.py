"""Pinned, CPU-preparable recipes. No model download, rental or execution here."""
from pathlib import Path

from .comfy import prepare
from .core import ProductionError, digest, number, object_digest, read_json


WORKFLOWS = Path(__file__).with_name("workflows")


def ltx25_plan(prompt, seed, job_id, endpoint):
    """Fixed five-second upstream T2V recipe; not identity/artistic qualification."""
    if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 12000:
        raise ProductionError("A nonempty prompt up to 12000 characters is required")
    number(seed, "seed", 0, 2**53-1)
    if not isinstance(seed, int):
        raise ProductionError("Seed must be an integer")
    lock = read_json(WORKFLOWS / "ltx25-t2v.lock.json")
    graph = read_json(WORKFLOWS / "ltx25-t2v.api.json")
    if object_digest(graph) != lock["workflow_sha256"]:
        raise ProductionError("Pinned workflow hash mismatch")
    graph["405:376"]["inputs"]["value"] = prompt.strip()
    for key in ("405:338", "405:339"):
        graph[key]["inputs"]["noise_seed"] = seed
    plan = prepare(graph, job_id, endpoint)
    plan.update(recipe=lock["recipe"], recipe_lock_sha256=object_digest(lock),
                required_models=lock["models"], total_model_bytes=lock["total_model_bytes"],
                generation_authorized=False, gpu_qualified=False)
    return plan


def verify_ltx25_weights(models_root: Path, runtime):
    """Streaming SHA checks with caller's deadline/cancellation, never download."""
    root = models_root.resolve()
    lock = read_json(WORKFLOWS / "ltx25-t2v.lock.json")
    results = []
    for model in lock["models"]:
        runtime.check()
        path = (root / model["path"]).resolve()
        if not path.is_relative_to(root):
            raise ProductionError("Model path leaves the private models directory")
        state = "missing"
        if path.is_file():
            if path.stat().st_size != model["bytes"]:
                state = "size_mismatch"
            else:
                state = "verified" if digest(path, runtime) == model["sha256"] else "sha_mismatch"
        results.append({"path": model["path"], "status": state})
    return {"status": "weights_verified" if all(x["status"] == "verified" for x in results)
            else "blocked", "models": results, "generation_authorized": False}
