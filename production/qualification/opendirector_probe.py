"""Bounded, offline-provider qualification through the real installed CLI.

Uses only caller-provided technical media. Creates isolated local projects,
never configures providers or invokes generation. Stops its own server group.
"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time
import urllib.request
from uuid import uuid4
import zipfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--application", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--port", type=int, default=18081)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    cli_path = args.application / ".venv/bin/opendirector"
    url = f"http://127.0.0.1:{args.port}"
    env = {k: os.environ[k] for k in ("PATH", "HOME", "USER", "LANG", "TMPDIR") if k in os.environ}
    env["OPENDIRECTOR_ROOT"] = str(args.output / "data")
    env["NO_PROXY"] = "127.0.0.1,localhost"
    events = []
    process = None
    log = (args.output / "server.log").open("w")
    deadline = time.monotonic() + 300

    def run(*command, pid=None, operation=None, success=True):
        if time.monotonic() >= deadline:
            raise TimeoutError("Qualification deadline exceeded")
        argv = [str(cli_path), "--url", url]
        if pid: argv += ["--project", str(pid)]
        if operation: argv += ["--operation-id", str(operation)]
        completed = subprocess.run(argv + list(map(str, command)), cwd=args.application,
            env=env, capture_output=True, text=True, timeout=40)
        try: result = json.loads(completed.stdout)
        except ValueError: result = {"raw": completed.stdout, "stderr": completed.stderr}
        events.append({"command": list(map(str, command)), "exit_code": completed.returncode, "result": result})
        if success and completed.returncode:
            raise RuntimeError(f"CLI failed: {command}: {result}")
        if not success and not completed.returncode:
            raise AssertionError("Unsupported transition unexpectedly accepted")
        return result

    def start():
        nonlocal process
        process = subprocess.Popen([str(cli_path), "serve", "--port", str(args.port)],
            cwd=args.application, env=env, stdout=log, stderr=log, start_new_session=True)
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        for _ in range(180):
            if process.poll() is not None: raise RuntimeError("Server exited before readiness")
            try:
                with opener.open(urllib.request.Request(url+"/api/health",
                        headers={"X-OpenDirector-Request":"1"}), timeout=1) as r:
                    if json.load(r) == {"status":"ok"}: break
            except (OSError, ValueError): time.sleep(0.2)
        else: raise TimeoutError("Server readiness timed out")
        with opener.open(url, timeout=5) as r:
            html = r.read().decode()
            assert r.status == 200 and '<script' in html and '/@vite/client' not in html

    def stop():
        nonlocal process
        if process is not None and process.poll() is None:
            os.killpg(process.pid, signal.SIGINT)
            try: process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGTERM)
                process.wait(timeout=5)
        process = None

    def command_file(name, payload, versions=()):
        p = args.output / name
        p.write_text(json.dumps({"payload":payload, "expectedVersions":list(versions)}, ensure_ascii=False))
        return p

    try:
        start()
        pid, target, editor = uuid4(), uuid4(), uuid4()
        run("project", "create", "--name", "Техническая проба переноса", pid=pid)
        for name, kind in (("red.mp4","video"),("blue.mp4","video"),("tone.wav","audio")):
            run("asset", "import", args.source/name, "--kind", kind, pid=pid)
        font = run("timeline", "default-font")
        run("asset", "import", font["path"], "--kind", "file", pid=pid)
        snapshot = run("project", "show", pid=pid)
        assets = {a["name"]:a for a in snapshot["assets"]}
        def ref(a): return {"assetId":a["id"],"revision":a["revision"],"kind":a["kind"],"fingerprint":a["fingerprint"]}
        def clip(name, ident, duration, start=None):
            a=assets[name]
            c={"id":ident,"resource":{"asset":ref(a),"title":name,"durationSeconds":a["metadata"]["durationSeconds"]},
                "inPoint":0,"outPoint":duration,"speed":1,"muted":name.endswith('.mp4')}
            if start is not None: c["start"]=start
            return c
        font_asset = next(a for a in assets.values() if a["kind"] == "file")
        doc={"id":str(editor),"projectId":str(pid),"kind":"timeline","data":{
            "fps":24,"width":320,"height":180,"tracks":[
                {"id":"picture","kind":"visual","title":"Изображение","clips":[clip("red.mp4","one",2),clip("blue.mp4","two",2)]},
                {"id":"sound","kind":"audio","title":"Защищённый звук","clips":[clip("tone.wav","sound-1",4,0)]}],
            "fonts":[{"id":"font","title":"Noto Sans","asset":ref(font_asset)}],
            "overlays":[{"id":"title","start":0,"end":4,"text":"Техническая проба","x":0.05,"y":0.1,"maxWidth":0.9,
                "fontId":"font","style":{"fontSize":20,"color":"#ffffff","align":"center","lineHeight":1.2}}]}}
        unsupported=copy.deepcopy(doc)
        unsupported['data']['tracks'][0]['clips'][0]['transition_after']={"type":"dissolve","duration_frames":24}
        run("editor","create","--file",command_file("unsupported.json",{"document":unsupported}),pid=pid,success=False)
        assert not run("project","show",pid=pid)["editorDocuments"]
        created=run("editor","create","--file",command_file("create.json",{"document":doc}),pid=pid)
        assert created["status"] == "applied"
        run("timeline","export","--editor-id",editor,"--revision",1,"--output",args.output/"v1.timeline.zip",pid=pid)
        saved=run("project","show",pid=pid)["editorDocuments"][0]
        revised=copy.deepcopy(saved)
        revised['data']['tracks'][0]['clips'][1]['resource']=doc['data']['tracks'][0]['clips'][0]['resource']
        run("editor","save","--file",command_file("edit.json",{"document":revised},
            [{"objectType":"editor_document","id":str(editor),"revision":1}]),pid=pid)
        run("timeline","export","--editor-id",editor,"--revision",2,"--output",args.output/"v2.timeline.zip",pid=pid)
        run("project","create","--name","Проверка повторного открытия",pid=target)
        operation=uuid4()
        imported=run("timeline","import",args.output/"v2.timeline.zip","--operation-id",operation,pid=target)
        assert imported['status']=='applied',imported
        replay=run("timeline","import",args.output/"v2.timeline.zip","--operation-id",operation,pid=target)
        assert replay==imported
        before=run("project","show",pid=target)
        stop();start()
        after=run("project","show",pid=target)
        assert before==after
        assert after['editorDocuments'][0]['data']['overlays'][0]['text']=='Техническая проба'
        assert len(after['editorDocuments'])==1
        verified={}
        for version in ('v1','v2'):
            with zipfile.ZipFile(args.output/f'{version}.timeline.zip') as z:
                manifest=json.loads(z.read('manifest.json'))
                timeline=json.loads(z.read('timeline.json'))
                for a in manifest['resources']:
                    assert hashlib.sha256(z.read(a['path'])).hexdigest()==a['fingerprint'][7:]
                verified[version]=timeline
        assert verified['v1']['tracks'][0]['clips'][0] == verified['v2']['tracks'][0]['clips'][0]
        assert verified['v1']['tracks'][1] == verified['v2']['tracks'][1]
        assert verified['v1']['tracks'][0]['clips'][1] != verified['v2']['tracks'][0]['clips'][1]
        report={"status":"partial_qualification","installed_http":True,"exact_revision_packages":True,
            "cyrillic_retained":True,"package_fingerprints":True,"local_edit_preserves_other_data":True,
            "restart_preserves_project":True,"replay_without_duplicate":True,"transition_supported":False,
            "server_mp4":False,"artistic_pilot":False,"provider_calls":0,"events":events}
        (args.output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
        print(json.dumps({k:v for k,v in report.items() if k!='events'},ensure_ascii=False))
    except BaseException as exc:
        (args.output/'failure.json').write_text(json.dumps({"error":str(exc),"events":events},ensure_ascii=False,indent=2))
        raise
    finally:
        stop();log.close()


if __name__ == '__main__': main()
