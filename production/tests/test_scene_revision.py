import unittest
from unittest.mock import patch
from production.core import ProductionError, digest, read_json
from production.shot_edit import build
from production.scene_revision import revise
from production.shots import folder
from production.tests import test_shots as fixtures


class SceneRevision(unittest.TestCase):
    @classmethod
    def setUpClass(cls):fixtures.BoundShot.setUpClass()
    @classmethod
    def tearDownClass(cls):fixtures.BoundShot.tearDownClass()
    def setUp(self):
        self.case=fixtures.BoundShot();self.case.setUp();self.addCleanup(self.case.doCleanups)
        result=self.case.execute()
        self.base=folder(self.case.root,self.case.ident,self.case.request['request_id'])
        build(self.case.root,self.case.ident,self.case.request['request_id'],self.base/'edit')
        self.edit={'source_sha256':result['output_sha256'],'start_frame':12,'duration_frames':24,'source_audio':'mute'}
    def run_edit(self):return revise(self.case.root,self.case.ident,self.case.request['request_id'],self.edit)
    def test_frame_exact_edit_portable_project_and_repeat_without_render(self):
        from pathlib import Path
        import opentimelineio as otio
        original=digest(self.base/'edit/render/master.mp4')
        result=self.run_edit();out=Path(result['output'])
        report=read_json(out/'render/render.json')
        video=next(s for s in report['probe']['streams'] if s['codec_type']=='video')
        self.assertEqual(int(video['nb_frames']),24)
        timeline=otio.adapters.read_from_file(str(out/'render/timeline.otio'))
        self.assertEqual(timeline.tracks[0][0].source_range.start_time.value,12)
        self.assertEqual(digest(self.base/'edit/render/master.mp4'),original)
        self.assertFalse(result['finished_video_accepted'])
        with patch('production.scene_revision.render',side_effect=AssertionError('repeated render')):
            self.assertEqual(self.run_edit(),result)
    def test_wrong_source_and_out_of_range_do_not_render(self):
        valid=dict(self.edit)
        for change in ({'source_sha256':'0'*64},{'start_frame':40},{'duration_frames':True}):
            self.edit=dict(valid,**change)
            with patch('production.scene_revision.render') as render:
                with self.assertRaises(ProductionError):self.run_edit()
                render.assert_not_called()
    def test_interrupted_correction_retries_without_overwriting(self):
        with patch('production.scene_revision.render',side_effect=ProductionError('interrupted')):
            with self.assertRaises(ProductionError):self.run_edit()
        result=self.run_edit()
        self.assertTrue(all(result['technical_checks'].values()))
        self.assertEqual(len(list((self.base/'revisions').glob('*.interrupted-*'))),1)
    def test_mutated_archive_cannot_be_reused(self):
        from pathlib import Path
        result=self.run_edit();(Path(result['output'])/'preview-project.zip').write_bytes(b'bad')
        with self.assertRaisesRegex(ProductionError,'Saved correction changed'):self.run_edit()

    def test_delivery_is_bound_and_plan_revocation_blocks_it(self):
        from production.scene_revision import revision_file,revisions
        from production.planning import save_plan_review
        import uuid
        result=self.run_edit();rid=result['revision_id']
        path=revision_file(self.case.root,self.case.ident,self.case.request['request_id'],rid,'video')
        self.assertEqual(digest(path),result['output_sha256'])
        self.assertEqual(len(revisions(self.case.root,self.case.ident,self.case.request['request_id'])),1)
        save_plan_review(self.case.root,self.case.ident,dict(self.case.accept,request_id=str(uuid.uuid4()),
            decision='request_changes',notes='Revoke for delivery test'))
        with self.assertRaises(ProductionError):
            revision_file(self.case.root,self.case.ident,self.case.request['request_id'],rid,'video')
