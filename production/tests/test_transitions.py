import copy
import tempfile
import unittest
from pathlib import Path

from PIL import Image
import opentimelineio as otio

from production.core import ProductionError, Runtime
from production.demo import make_fixture
from production.manifest import validate
from production.media import ffmpeg, render


class TransitionIntegration(unittest.TestCase):
    def test_mixed_cut_and_dissolve_have_exact_duration(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)/"sources"
            original = make_fixture(root)
            original["overlays"] = []
            original["clips"].append(dict(original["clips"][0], id="third"))
            for index in (0, 1):
                m=copy.deepcopy(original)
                m["clips"][index]["transition_after"]={"type":"dissolve","duration_frames":24}
                out=Path(tmp)/f"mixed-{index}"
                report=render(m,root,out,Runtime(120))
                self.assertEqual(report["probe"]["streams"][0]["nb_frames"],"120")
                timeline=otio.adapters.read_from_file(str(out/"timeline.otio"))
                self.assertEqual(timeline.duration().to_frames(),120)

    def test_dissolve_actual_pixels_duration_audio_and_editable_timing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)/"sources"
            m = make_fixture(root)
            m["overlays"] = []
            m["clips"][0]["transition_after"] = {"type":"dissolve", "duration_frames":24}
            m["audio"][0]["duration_frames"] = 72
            out = Path(tmp)/"dissolve"
            report = render(m, root, out, Runtime(120))
            self.assertEqual(report["probe"]["streams"][0]["nb_frames"], "72")
            self.assertEqual(report["status"], "needs_review")
            colors = []
            for i, t in enumerate((0.5,1.5,2.5)):
                p = Path(tmp)/f"frame-{i}.png"
                Runtime(20).run(ffmpeg("-ss",t,"-i",out/"master.mp4","-frames:v",1,p))
                with Image.open(p) as im: colors.append(im.getpixel((250,90)))
            self.assertGreater(colors[0][0], 220)
            self.assertTrue(80 < colors[1][0] < 180 and 80 < colors[1][2] < 180, colors)
            self.assertGreater(colors[2][2], 220)
            timeline = otio.adapters.read_from_file(str(out/"timeline.otio"))
            self.assertEqual(timeline.duration().to_frames(), 72)
            self.assertIsInstance(timeline.tracks[0][1], otio.schema.Transition)
            changed = copy.deepcopy(m)
            changed["revision"] = "r2"
            changed["clips"][1]["asset"] = "red"
            edited = Path(tmp)/"edited"
            render(changed, root, edited, Runtime(120))
            pcm = lambda folder: Runtime(20).run(ffmpeg("-i",folder/"master.mp4","-map","0:a:0",
                "-f","hash","-hash","sha256","-"))
            self.assertEqual(pcm(out), pcm(edited))

    def test_invalid_and_triple_overlaps_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)/"sources"
            original = make_fixture(root)
            for count in (0, True, 48, -1):
                m = copy.deepcopy(original)
                m["clips"][0]["transition_after"] = {"type":"dissolve", "duration_frames":count}
                with self.assertRaises(ProductionError): validate(m, root)
            m = copy.deepcopy(original)
            m["clips"].append(dict(m["clips"][0], id="third"))
            for c in m["clips"][:2]: c["transition_after"] = {"type":"dissolve", "duration_frames":30}
            with self.assertRaisesRegex(ProductionError, "triple-overlap"): validate(m, root)


if __name__ == "__main__": unittest.main()
