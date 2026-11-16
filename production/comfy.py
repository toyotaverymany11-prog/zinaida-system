"""A guarded adapter around the repository's existing ComfyRunner.

No pod creation, paid API substitution, global interrupt, or blind submission retry.
Receipts belong to individual caller-owned attempts, not to a second project queue.
"""
from __future__ import annotations

import fcntl
import importlib
import os
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlparse

from .core import ProductionError, digest, number, object_digest, read_json, write_json


def existing_runner():
    scripts = Path(__file__).resolve().parents[1]/"skills/creative/comfyui/scripts"
    if not scripts.is_dir():
        raise ProductionError("Existing ComfyUI scripts are missing from this checkout")
    # These are the existing executor's modules, not copied implementations.
    sys.path.insert(0, str(scripts))
    return importlib.import_module("run_workflow"), importlib.import_module("_common")


def endpoint_url(value):
    u = urlparse(value)
    if u.username or u.password or u.query or u.fragment or not u.hostname:
        raise ProductionError("Endpoint must not contain credentials, query or fragment")
    if u.scheme != "https" and not (u.scheme == "http" and u.hostname in {"localhost", "127.0.0.1", "::1"}):
        raise ProductionError("Use TLS or a local SSH tunnel for a self-hosted endpoint")
    if u.hostname == "cloud.comfy.org" or u.hostname.endswith(".cloud.comfy.org"):
        raise ProductionError("This adapter is for our self-hosted models, not Comfy Cloud")
    return value.rstrip("/")


def prepare(workflow, job_id, endpoint):
    from .manifest import ID
    if not ID.fullmatch(job_id):
        raise ProductionError("Invalid caller job ID")
    if not isinstance(workflow, dict) or not workflow or "nodes" in workflow:
        raise ProductionError("Expected exported ComfyUI API graph, not editor JSON")
    classes = set()
    for node in workflow.values():
        if not isinstance(node, dict) or not isinstance(node.get("class_type"), str) or not isinstance(node.get("inputs"), dict):
            raise ProductionError("Invalid API graph node")
        classes.add(node["class_type"])
    return {"schema_version": 1, "job_id": job_id, "endpoint": endpoint_url(endpoint),
            "workflow_sha256": object_digest(workflow), "node_classes": sorted(classes),
            "workflow": workflow, "status": "prepared_not_submitted"}


class Executor:
    def __init__(self, endpoint, receipt_dir: Path, api_key=None):
        self.endpoint = endpoint_url(endpoint)
        module, self.transport = existing_runner()
        self.runner = module.ComfyRunner(self.endpoint, api_key=api_key)
        self.receipt_dir = receipt_dir
        receipt_dir.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def lock(self, job_id):
        from .manifest import ID
        if not ID.fullmatch(job_id):
            raise ProductionError("Invalid job ID")
        with (self.receipt_dir/f"{job_id}.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            yield self.receipt_dir/f"{job_id}.json"

    def get(self, path):
        response = self.transport.http_get(self.runner._url(path), headers=self.runner.headers,
                                           retries=2, timeout=15, follow_redirects=False)
        if response.status != 200:
            raise ProductionError(f"ComfyUI read failed: HTTP {response.status}")
        return response.json()

    def preflight(self, plan):
        self._check_plan(plan)
        self.get("/system_stats")
        info = self.get("/object_info")
        errors = []
        for key, node in plan["workflow"].items():
            spec = info.get(node["class_type"])
            if not spec:
                errors.append(f"{key}: missing node {node['class_type']}")
                continue
            for name, field in spec.get("input", {}).get("required", {}).items():
                value = node["inputs"].get(name)
                if name not in node["inputs"]:
                    errors.append(f"{key}: required input {name} missing")
                elif isinstance(field, list) and field and isinstance(field[0], list):
                    # ComfyUI links are [node id, output index]; don't treat them as literals.
                    link = isinstance(value, list) and len(value) == 2 and str(value[0]) in plan["workflow"]
                    if not link and value not in field[0]:
                        errors.append(f"{key}: {name} not available (model/option missing)")
        return {"status": "blocked" if errors else "preflight_pass", "errors": errors,
                "workflow_sha256": plan["workflow_sha256"],
                "note": "Node/input inventory only. Does not prove VRAM fit, quality or commercial eligibility."}

    def _check_plan(self, plan):
        fresh = prepare(plan["workflow"], plan["job_id"], plan["endpoint"])
        if fresh["workflow_sha256"] != plan["workflow_sha256"] or self.endpoint != fresh["endpoint"]:
            raise ProductionError("Plan was altered or endpoint does not match")

    def submit(self, plan, grant, *, execute_authorized=False):
        self._check_plan(plan)
        if not execute_authorized or grant.get("approved") is not True:
            raise ProductionError("No authorized execution requested")
        for key in ("job_id", "endpoint", "workflow_sha256"):
            if grant.get(key) != plan[key]:
                raise ProductionError(f"Authorization does not match {key}")
        runtime = number(grant.get("max_runtime_seconds"), "max_runtime_seconds", 1, 86400)
        hourly = number(grant.get("gpu_hourly_usd"), "gpu_hourly_usd", 0)
        budget = number(grant.get("budget_usd"), "budget_usd", 0)
        if runtime*hourly/3600 > budget:
            raise ProductionError("Declared runtime cost exceeds authorized budget")
        # Pricing and grants must come from the trusted controller. This is not
        # a provider-side spending cap or authority to keep a pod running.
        with self.lock(plan["job_id"]) as path:
            if path.exists():
                old = read_json(path)
                if old["workflow_sha256"] != plan["workflow_sha256"] or old["endpoint"] != self.endpoint:
                    raise ProductionError("Job ID reused for different work")
                return old  # Never submit twice, including after an unknown outcome.
            result = self.preflight(plan)
            if result["status"] != "preflight_pass":
                return result
            receipt = {"schema_version": 1, "job_id": plan["job_id"], "endpoint": self.endpoint,
                       "workflow_sha256": plan["workflow_sha256"], "state": "submitting",
                       "started_at": time.time(), "max_runtime_seconds": runtime,
                       "budget_usd": budget, "gpu_hourly_usd": hourly}
            write_json(path, receipt)  # Crash after this point is an unknown outcome.
            payload = {"prompt": plan["workflow"], "client_id": f"production-{plan['job_id']}",
                       "extra_data": {"production_job_id": plan["job_id"],
                                      "workflow_sha256": plan["workflow_sha256"]}}
            try:
                # In this repository's transport, retries=1 means ONE attempt.
                response = self.transport.http_post(self.runner._url("/prompt"), headers=self.runner.headers,
                    json_body=payload, retries=1, timeout=min(30, runtime), follow_redirects=False)
                body = response.json()
                if response.status == 200 and body.get("prompt_id"):
                    receipt.update(state="submitted", prompt_id=body["prompt_id"])
                elif response.status in {400, 401, 403, 404, 422}:
                    receipt.update(state="rejected", http_status=response.status)
                else:
                    receipt.update(state="outcome_unknown", http_status=response.status)
            except Exception as exc:
                receipt.update(state="outcome_unknown", error_type=type(exc).__name__)
            write_json(path, receipt)
            return receipt

    def reconcile(self, job_id):
        with self.lock(job_id) as path:
            r = read_json(path)
            if r["endpoint"] != self.endpoint:
                raise ProductionError("Receipt endpoint mismatch")
            if r["state"] == "rejected":
                return r
            queue = self.get("/queue")
            history = self.get("/history?max_items=200")
            candidates = []
            for state, entries in (("running", queue.get("queue_running", [])),
                                   ("queued", queue.get("queue_pending", []))):
                candidates += [(state, entry, None) for entry in entries]
            for pid, entry in history.items():
                status = entry.get("status", {})
                state = "failed" if status.get("status_str") == "error" else (
                    "generated_unverified" if status.get("completed") else "unknown")
                candidates.append((state, entry.get("prompt", []), entry))
            found = []
            for state, entry, detail in candidates:
                if not isinstance(entry, list) or len(entry) < 4:
                    continue
                extra = entry[3] if isinstance(entry[3], dict) else {}
                if (extra.get("production_job_id") == job_id and
                        extra.get("workflow_sha256") == r["workflow_sha256"]):
                    found.append((state, entry[1], detail))
            ids = {x[1] for x in found}
            if len(ids) > 1:
                r["state"] = "duplicate_detected"
            elif found:
                state, pid, detail = found[-1]
                r.update(state=state, prompt_id=pid)
                if detail is not None:
                    r["outputs"] = detail.get("outputs", {})
            elif r["state"] not in {"generated_unverified", "failed", "downloaded_unverified"}:
                r["state"] = "outcome_unknown"
            r["deadline_exceeded"] = time.time() > r["started_at"]+r["max_runtime_seconds"]
            r["requires_controller_stop"] = r["deadline_exceeded"] and r["state"] in {"running", "queued", "outcome_unknown"}
            write_json(path, r)
            return r

    def cancel_pending(self, job_id):
        r = self.reconcile(job_id)
        if r["state"] != "queued":
            return {"status": "not_cancelled", "state": r["state"],
                    "reason": "Running jobs require the controller's exclusive-worker stop route."}
        response = self.transport.http_post(self.runner._url("/queue"), headers=self.runner.headers,
            json_body={"delete": [r["prompt_id"]]}, retries=1, timeout=15, follow_redirects=False)
        if response.status != 200:
            return {"status": "cancellation_unknown"}
        # Recheck: the job could have started between observing and deleting it.
        queue = self.get("/queue")
        if any(x[1] == r["prompt_id"] for x in queue.get("queue_running", [])):
            return {"status": "not_cancelled", "state": "running"}
        if any(x[1] == r["prompt_id"] for x in queue.get("queue_pending", [])):
            return {"status": "cancellation_unknown"}
        with self.lock(job_id) as path:
            latest = read_json(path)
            latest["state"] = "removed_from_pending"
            write_json(path, latest)
        return {"status": "removed_from_pending", "note": "Not a global interrupt and not proof of pod shutdown."}

    def download(self, job_id, output: Path):
        r = self.reconcile(job_id)
        if r["state"] != "generated_unverified":
            raise ProductionError("Outputs are not confirmed generated")
        output.mkdir(parents=True, exist_ok=False)
        files = []
        for node, data in r.get("outputs", {}).items():
            if not isinstance(data, dict):
                continue
            for key in ("videos", "video", "gifs", "images", "audio"):
                entries = data.get(key, [])
                entries = entries if isinstance(entries, list) else [entries]
                for entry in entries:
                    if not isinstance(entry, dict) or not entry.get("filename"):
                        continue
                    name, sub = entry["filename"], entry.get("subfolder", "")
                    for part in (name, sub):
                        if not isinstance(part, str) or Path(part).is_absolute() or ".." in Path(part).parts or "\\" in part:
                            raise ProductionError("Unsafe output path")
                    if entry.get("type", "output") != "output":
                        raise ProductionError("Refusing to download non-output files")
                    # Do not swallow failures or report a partial set as complete.
                    path = self.runner.download_output(filename=name, subfolder=sub, file_type="output",
                                                       output_dir=output, overwrite=False)
                    if not path.is_file() or not path.stat().st_size:
                        raise ProductionError("Empty output")
                    files.append({"node": node, "file": str(path.relative_to(output)),
                                  "sha256": digest(path), "bytes": path.stat().st_size})
        if not files:
            raise ProductionError("Completed job has no downloadable media")
        result = {"status": "downloaded_unverified", "job_id": job_id, "files": files,
                  "note": "Media decode, identity, artistic and delivery checks remain required."}
        write_json(output/"downloads.json", result)
        with self.lock(job_id) as path:
            latest = read_json(path)
            latest.update(state="downloaded_unverified", downloads=files)
            write_json(path, latest)
        return result
