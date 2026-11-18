import unittest
from integrations.scene_quality.media_probe import audio_continuity


class ContinuousAudioClock(unittest.TestCase):
    def frames(self):
        return [{'pts_time':str(i*1024/48000),'nb_samples':1024} for i in range(4)]

    def test_continuous_pcm_with_rounded_timestamps_is_allowed(self):
        f=self.frames()
        for x in f:x['pts_time']=f"{float(x['pts_time']):.6f}"
        self.assertTrue(audio_continuity(f,48000)['continuous'])

    def test_overlapping_aac_join_is_detected(self):
        f=self.frames();f[2]['pts_time']=f[1]['pts_time'];r=audio_continuity(f,48000)
        self.assertFalse(r['continuous']);self.assertLess(r['discontinuities'][0]['delta_seconds'],0)

    def test_missing_audio_time_is_detected_even_if_all_packets_decode(self):
        f=self.frames();f[2]['pts_time']=str(float(f[2]['pts_time'])+.07)
        self.assertFalse(audio_continuity(f,48000)['continuous'])
