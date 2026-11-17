import argparse
import json
import os
import sys
from pathlib import Path

from .core import ProductionError, Runtime, read_json


def main(argv=None):
    p = argparse.ArgumentParser(description="Bounded production workers; no project queue or automatic publication")
    sub = p.add_subparsers(dest="command", required=True)
    for name in ("validate", "render", "release-check"):
        s = sub.add_parser(name)
        s.add_argument("manifest", type=Path)
        s.add_argument("--root", type=Path, required=True)
        if name != "validate":
            s.add_argument("--output", type=Path, required=True)
        if name == "render":
            s.add_argument("--timeout", type=float, default=1800)
            s.add_argument("--cancel-file", type=Path)
        if name == "release-check":
            s.add_argument("--decisions", type=Path, required=True)
    s = sub.add_parser("inspect")
    s.add_argument("source", type=Path)
    s.add_argument("--output", type=Path, required=True)
    s.add_argument("--timeout", type=float, default=600)
    s.add_argument("--cancel-file", type=Path)
    s.add_argument("--max-samples", type=int, default=24)
    s = sub.add_parser("costs")
    s.add_argument("ledger", type=Path)
    s = sub.add_parser("prepare-speech")
    s.add_argument("specification", type=Path)
    s = sub.add_parser("prepare-gpu")
    s.add_argument("workflow", type=Path)
    s.add_argument("--job-id", required=True)
    s.add_argument("--endpoint", required=True)
    for name in ("models-plan", "models-check-remote", "models-install"):
        s = sub.add_parser(name, help="Pinned LTX-2.5 files only; no GPU or generation")
        s.add_argument("--root", type=Path, required=True)
        s.add_argument("--timeout", type=float, default=300)
        s.add_argument("--cancel-file", type=Path)
        s.add_argument("--reserve-bytes", type=int, default=1024**3)
        if name != "models-plan":
            s.add_argument("--hf-python", type=Path, required=True)
        if name == "models-install":
            s.add_argument("--download-authorized", action="store_true")
            s.add_argument("--max-download-bytes", type=int, default=0)
    for name in ("preflight-gpu", "submit-gpu", "status-gpu", "cancel-pending-gpu", "download-gpu"):
        s = sub.add_parser(name)
        s.add_argument("plan", type=Path)
        s.add_argument("--receipts", type=Path, required=True)
        if name == "submit-gpu":
            s.add_argument("--grant", type=Path, required=True)
            s.add_argument("--execute-authorized", action="store_true")
        if name == "download-gpu":
            s.add_argument("--output", type=Path, required=True)
    args = p.parse_args(argv)
    try:
        if args.command == "inspect":
            from .media import inspect_video
            result = inspect_video(args.source, args.output, Runtime(args.timeout, args.cancel_file), args.max_samples)
        elif args.command in {"validate", "render", "release-check"}:
            from .manifest import validate
            from .media import render, release_check
            manifest = read_json(args.manifest)
            if args.command == "validate":
                result = validate(manifest, args.root)
                result["paths"] = {k: str(v) for k,v in result["paths"].items()}
            elif args.command == "render":
                result = render(manifest, args.root, args.output, Runtime(args.timeout, args.cancel_file))
            else:
                result = release_check(manifest, args.root, args.output, read_json(args.decisions))
        elif args.command == "prepare-speech":
            from .speech import prepare_batch
            result = prepare_batch(read_json(args.specification))
        elif args.command == "costs":
            from .costs import summarize
            ledger = read_json(args.ledger)
            result = summarize(ledger["attempts"], ledger.get("overhead_usd", 0))
        elif args.command.startswith("models-"):
            from .model_install import cancel_on_signal, check_remote, inspect_install, install
            from .recipes import WORKFLOWS
            lock = read_json(WORKFLOWS / "ltx25-t2v.lock.json")
            runtime = Runtime(args.timeout, args.cancel_file)
            with cancel_on_signal():
                if args.command == "models-plan":
                    result = inspect_install(lock, args.root, runtime, args.reserve_bytes)
                elif args.command == "models-check-remote":
                    result = check_remote(lock, args.root, args.hf_python.resolve(), runtime)
                else:
                    result = install(lock, args.root, args.hf_python.resolve(), runtime,
                                     download_authorized=args.download_authorized,
                                     max_download_bytes=args.max_download_bytes,
                                     reserve_bytes=args.reserve_bytes)
        else:
            from .comfy import Executor, prepare
            if args.command == "prepare-gpu":
                result = prepare(read_json(args.workflow), args.job_id, args.endpoint)
            else:
                plan = read_json(args.plan)
                executor = Executor(plan["endpoint"], args.receipts, os.environ.get("PRODUCTION_COMFY_API_KEY"))
                if args.command == "preflight-gpu":
                    result = executor.preflight(plan)
                elif args.command == "submit-gpu":
                    result = executor.submit(plan, read_json(args.grant), execute_authorized=args.execute_authorized)
                elif args.command == "status-gpu":
                    result = executor.reconcile(plan["job_id"])
                elif args.command == "download-gpu":
                    result = executor.download(plan["job_id"], args.output)
                else:
                    result = executor.cancel_pending(plan["job_id"])
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return 0
    except (ProductionError, OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "blocked_or_failed", "error": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    sys.exit(main())
