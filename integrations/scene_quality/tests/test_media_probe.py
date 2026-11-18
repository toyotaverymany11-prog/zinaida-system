import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from integrations.scene_quality.media_probe import inspect


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'),'FFmpeg required')
class ExactFrameProbe(unittest.TestCase):
    def test_two_frame_flash_is_found_between_sparse_samples(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'flash.mp4'
            subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=c=white:s=256x144:r=24:d=2',
                '-vf',"drawbox=x=0:y=0:w=iw:h=ih:color=black:t=fill:enable='between(n,11,12)'",
                '-c:v','libx264','-pix_fmt','yuv420p',str(path)],check=True)
            r=inspect(path)
            self.assertEqual(r['decoded_frames'],48)
            self.assertEqual(len(r['candidate_findings']),1)
            self.assertEqual(r['candidate_findings'][0]['start_frame'],11)
            self.assertEqual(r['candidate_findings'][0]['end_frame_inclusive'],12)
            self.assertFalse(r['artistic_approval'])

    def test_static_image_is_observation_not_automatic_failure(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'still.mp4'
            subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=c=gray:s=256x144:r=24:d=1',
                '-c:v','libx264','-pix_fmt','yuv420p',str(path)],check=True)
            r=inspect(path)
            self.assertEqual(r['candidate_findings'],[])
            self.assertTrue(r['observations']['low_change_ranges'])
            self.assertFalse(r['artistic_approval'])
