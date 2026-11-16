import copy
import json
import os
import socket
import sys
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from production.comfy import Executor, prepare
from production.core import Cancelled, ProductionError, Runtime, digest, object_digest, read_json
from production.costs import summarize
from production.demo import make_fixture
from production.manifest import validate
from production.media import ffmpeg, inspect_video, release_check, render


class ProductionIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.base = Path(cls.temp.name)
        cls.root = cls.base/"input with spaces"
        cls.manifest = make_fixture(cls.root)
        cls.output = cls.base/"render"
        cls.report = render(cls.manifest, cls.root, cls.output, Runtime(120))

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_real_render_has_exact_frames_and_is_not_approved(self):
        self.assertEqual(self.report["status"], "needs_review")
        self.assertTrue(all(self.report["technical_checks"].values()))
        self.assertEqual(self.report["probe"]["streams"][0]["nb_frames"], "96")

    def test_cut_content_and_overlay_timing(self):
        from PIL import Image
        rt = Runtime(20)
        colors = []
        for i,t in enumerate([0.25,1.5,2.5,3.5]):
            p=self.base/f"check-{i}.png"
            rt.run(ffmpeg("-ss",t,"-i",self.output/"master.mp4","-frames:v",1,p))
            with Image.open(p) as im:
                colors.append((im.getpixel((250,90)), im.getpixel((5,5))))
        self.assertGreater(colors[0][0][0], 200)
        self.assertGreater(colors[2][0][2], 200)
        self.assertTrue(all(x>200 for x in colors[1][1][:3]))
        self.assertGreater(colors[3][1][2], 200)

    def test_voice_asset_unchanged_and_audio_present(self):
        self.assertEqual(digest(self.root/"tone.wav"),self.manifest["assets"]["tone"]["sha256"])
        log=Runtime(20).run(["ffmpeg","-nostdin","-hide_banner","-i",str(self.output/"master.mp4"),
                            "-vn","-af","volumedetect","-f","null","-"],stderr=True)
        self.assertIn("mean_volume:",log)
        self.assertNotIn("mean_volume: -91",log)

    def test_local_picture_edit_preserves_voice_and_other_scene(self):
        from PIL import Image
        m=copy.deepcopy(self.manifest);m["revision"]="r2"
        m["clips"][1]["asset"]="red"
        target=self.base/"local-edit"
        updated=render(m,self.root,target,Runtime(90))
        self.assertNotEqual(updated["output_sha256"],self.report["output_sha256"])
        rt=Runtime(30)
        audio_hashes=[]
        for folder in (self.output,target):
            audio_hashes.append(rt.run(ffmpeg("-i",folder/"master.mp4","-map","0:a:0",
                                               "-f","hash","-hash","sha256","-")))
        self.assertEqual(audio_hashes[0],audio_hashes[1])
        path=self.base/"unchanged-scene.png"
        rt.run(ffmpeg("-ss",0.25,"-i",target/"master.mp4","-frames:v",1,path))
        with Image.open(path) as im:self.assertGreater(im.getpixel((250,90))[0],200)

    def test_wrong_qr_destination_fails_final_video_validation(self):
        m=copy.deepcopy(self.manifest);m["overlays"][0]["destination"]="https://example.com/wrong"
        with self.assertRaisesRegex(ProductionError,"QR payload"):
            render(m,self.root,self.base/"bad-qr",Runtime(90))

    def test_sparse_or_mismatched_character_review_blocks(self):
        m=copy.deepcopy(self.manifest)
        m["characters"]={"hero":{"version":"v1","reference_assets":["qr"]}}
        m["clips"][0]["characters"]=["hero"]
        # Even inventing a character in a manifest invalidates the prior report.
        with self.assertRaisesRegex(ProductionError,"Stale render"):
            release_check(m,self.root,self.output,[])

    def test_otio_is_editable_and_has_expected_tracks(self):
        import opentimelineio as otio
        t=otio.adapters.read_from_file(str(self.output/"timeline.otio"))
        self.assertEqual(len(t.tracks),4)
        self.assertEqual(len(t.tracks[0]),2)
        self.assertEqual(t.tracks[0][1].source_range.duration.value,48)
        self.assertEqual(t.tracks[2][0].media_reference.target_url,(self.root/"tone.wav").as_uri())

    def test_inspection_records_real_cut_and_last_frame(self):
        a=inspect_video(self.output/"master.mp4",self.base/"inspection",Runtime(60),8)
        self.assertTrue(any(abs(s["start"]-2)<0.1 for s in a["detected_shots"]))
        self.assertGreater(a["frames"][-1]["time_seconds"],3.9)
        self.assertEqual(a["identity_review"],"not_performed")
        self.assertTrue((self.base/"inspection"/"contact_sheet.jpg").exists())

    def test_render_never_overwrites_candidate(self):
        with self.assertRaises(FileExistsError):
            render(self.manifest,self.root,self.output,Runtime(30))

    def test_missing_human_reviews_block_release(self):
        with self.assertRaisesRegex(ProductionError,"Missing reviews"):
            release_check(self.manifest,self.root,self.output,[])

    def test_review_bound_to_exact_manifest(self):
        changed=copy.deepcopy(self.manifest)
        changed["clips"][0]["purpose"]="changed requirement"
        with self.assertRaisesRegex(ProductionError,"Stale render"):
            release_check(changed,self.root,self.output,[])

    def test_altered_output_is_not_approved_by_old_report(self):
        import shutil
        out=self.base/"tampered"
        shutil.copytree(self.output,out)
        with (out/"master.mp4").open("ab") as f:f.write(b"changed")
        with self.assertRaisesRegex(ProductionError,"Stale render"):
            release_check(self.manifest,self.root,out,[])

    def test_changed_asset_hash_blocks(self):
        m=copy.deepcopy(self.manifest)
        m["assets"]["red"]["sha256"]="0"*64
        with self.assertRaisesRegex(ProductionError,"hash mismatch"):
            validate(m,self.root)

    def test_path_escape_and_symlink_escape_block(self):
        m=copy.deepcopy(self.manifest)
        m["assets"]["red"]["path"]="../red.mp4"
        with self.assertRaises(ProductionError):validate(m,self.root)
        target=self.base/"outside.txt";target.write_text("outside")
        (self.root/"outside-link").symlink_to(target)
        m["assets"]["red"]["path"]="outside-link"
        with self.assertRaises(ProductionError):validate(m,self.root)

    def test_recast_requires_original_target_and_identity(self):
        m=copy.deepcopy(self.manifest);m["clips"][0]["route"]="video_recast"
        with self.assertRaisesRegex(ProductionError,"video_recast"):
            validate(m,self.root)

    def test_duration_and_audio_bounds_block(self):
        m=copy.deepcopy(self.manifest);m["audio"][0]["start_frame"]=10
        with self.assertRaises(ProductionError):validate(m,self.root)
        m=copy.deepcopy(self.manifest);m["clips"][0]["duration_frames"]=96
        with self.assertRaisesRegex(ProductionError,"shorter"):
            render(m,self.root,self.base/"too-long",Runtime(30))

    def test_cancellation_stops_process(self):
        cancel=self.base/"cancel"
        timer=threading.Timer(.2,lambda:cancel.touch());timer.start()
        start=time.monotonic()
        try:
            with self.assertRaises(Cancelled):
                Runtime(10,cancel).run([sys.executable,"-c","import time;time.sleep(30)"])
        finally:timer.join()
        self.assertLess(time.monotonic()-start,3)

    def test_global_deadline(self):
        with self.assertRaises(Cancelled):
            Runtime(.1).run([sys.executable,"-c","import time;time.sleep(3)"])


class Costs(unittest.TestCase):
    def test_rejects_are_counted_in_accepted_price(self):
        r=summarize([{"attempt_id":"a","scene_id":"s","compute_usd":"1.50","accepted":False},
                     {"attempt_id":"b","scene_id":"s","compute_usd":"2","accepted":True,"accepted_seconds":2}],"0.50")
        self.assertEqual(r["usd_per_accepted_second"],"2.00")

    def test_zero_accepted_is_not_zero_price(self):
        self.assertIsNone(summarize([{"attempt_id":"a","compute_usd":1}])["usd_per_accepted_second"])

    def test_duplicates_and_nonfinite_block(self):
        with self.assertRaises(ProductionError):summarize([{"attempt_id":"a"},{"attempt_id":"a"}])
        with self.assertRaises(ProductionError):summarize([],"NaN")


class FakeComfyHandler(BaseHTTPRequestHandler):
    def log_message(self,*a):pass
    def send(self,data,code=200):
        raw=json.dumps(data).encode();self.send_response(code)
        self.send_header("Content-Type","application/json");self.send_header("Content-Length",str(len(raw)))
        self.end_headers();self.wfile.write(raw)
    def do_GET(self):
        s=self.server.state
        if self.path=="/system_stats":self.send({"devices":[]})
        elif self.path=="/object_info":self.send({"Loader":{"input":{"required":{"model":[["ok.safetensors"]]}}}})
        elif self.path=="/queue":self.send({"queue_running":s["running"],"queue_pending":s["pending"]})
        elif self.path.startswith("/history"):self.send(s["history"])
        else:self.send({},404)
    def do_POST(self):
        body=json.loads(self.rfile.read(int(self.headers.get("Content-Length",0))) or b"{}")
        s=self.server.state;s["posts"].append((self.path,body))
        if self.path=="/prompt":
            pid=f'p{len(s["posts"])}'
            if s["mode"]=="500":return self.send({},500)
            s["pending"].append([1,pid,body["prompt"],body["extra_data"],[]])
            if s["mode"]=="drop":
                self.connection.shutdown(socket.SHUT_RDWR);self.connection.close();return
            self.send({"prompt_id":pid,"number":1})
        elif self.path=="/queue":
            s["pending"][:]=[x for x in s["pending"] if x[1] not in body.get("delete",[])]
            self.send({})
        else:self.send({},404)


class ComfyIntegration(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.server=ThreadingHTTPServer(("127.0.0.1",0),FakeComfyHandler)
        self.server.state={"posts":[],"pending":[],"running":[],"history":{},"mode":"ok"}
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.host=f"http://127.0.0.1:{self.server.server_port}"
        self.plan=prepare({"1":{"class_type":"Loader","inputs":{"model":"ok.safetensors"}}},"job-1",self.host)
        self.grant={k:self.plan[k] for k in ("job_id","endpoint","workflow_sha256")}
        self.grant.update(approved=True,max_runtime_seconds=60,gpu_hourly_usd=1,budget_usd=1)
        self.e=Executor(self.host,Path(self.temp.name))
    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join();self.temp.cleanup()
    def submit(self):return self.e.submit(self.plan,self.grant,execute_authorized=True)
    def test_no_authorization_no_submission(self):
        with self.assertRaises(ProductionError):self.e.submit(self.plan,self.grant)
        self.assertEqual(self.server.state["posts"],[])
    def test_changed_plan_or_excess_budget_blocks(self):
        self.grant["budget_usd"]=0
        with self.assertRaises(ProductionError):self.submit()
        self.grant["budget_usd"]=1;self.plan["workflow"]["1"]["inputs"]["model"]="different"
        with self.assertRaises(ProductionError):self.submit()
    def test_concurrent_duplicate_submits_only_once(self):
        with ThreadPoolExecutor(2) as pool:results=list(pool.map(lambda _:self.submit(),range(2)))
        self.assertEqual(len(self.server.state["posts"]),1)
        self.assertEqual(results[0]["prompt_id"],results[1]["prompt_id"])
    def test_lost_response_is_reconciled_without_resubmission(self):
        self.server.state["mode"]="drop"
        self.assertEqual(self.submit()["state"],"outcome_unknown")
        self.assertEqual(self.submit()["state"],"outcome_unknown")
        r=self.e.reconcile("job-1")
        self.assertEqual(r["state"],"queued")
        self.assertEqual(len(self.server.state["posts"]),1)
    def test_500_does_not_trigger_blind_retry(self):
        self.server.state["mode"]="500"
        self.assertEqual(self.submit()["state"],"outcome_unknown")
        self.assertEqual(len(self.server.state["posts"]),1)
    def test_cancel_removes_only_own_pending_job(self):
        self.submit();self.server.state["pending"].append([2,"other",{}, {}, []])
        self.assertEqual(self.e.cancel_pending("job-1")["status"],"removed_from_pending")
        self.assertEqual([x[1] for x in self.server.state["pending"]],["other"])
        self.assertFalse(any(x[0]=="/interrupt" for x in self.server.state["posts"]))
    def test_running_job_does_not_interrupt_shared_worker(self):
        self.submit();self.server.state["running"]=self.server.state["pending"][:];self.server.state["pending"]=[]
        self.assertEqual(self.e.cancel_pending("job-1")["status"],"not_cancelled")
        self.assertEqual(len(self.server.state["posts"]),1)
    def test_missing_model_blocks_preflight(self):
        p=prepare({"1":{"class_type":"Loader","inputs":{"model":"missing.safetensors"}}},"x",self.host)
        self.assertEqual(self.e.preflight(p)["status"],"blocked")

    def test_completed_with_error_is_failure_not_success(self):
        r=self.submit();entry=self.server.state["pending"].pop()
        self.server.state["history"][r["prompt_id"]]={"prompt":entry,"status":{"completed":True,"status_str":"error"},"outputs":{}}
        self.assertEqual(self.e.reconcile("job-1")["state"],"failed")

    def test_deadline_does_not_claim_external_work_has_stopped(self):
        r=self.submit();entry=self.server.state["pending"].pop();self.server.state["running"].append(entry)
        from production.core import write_json
        path=Path(self.temp.name)/"job-1.json";r["started_at"]=time.time()-120;write_json(path,r)
        checked=self.e.reconcile("job-1")
        self.assertTrue(checked["requires_controller_stop"])
        self.assertEqual(checked["state"],"running")
    def test_editor_json_is_not_an_api_graph(self):
        with self.assertRaises(ProductionError):prepare({"nodes":[]},"x",self.host)
    def test_paid_cloud_and_insecure_remote_endpoints_block(self):
        for host in ["https://cloud.comfy.org","http://example.com","https://user:pass@example.com"]:
            with self.assertRaises(ProductionError):Executor(host,Path(self.temp.name))


if __name__=="__main__":unittest.main()
