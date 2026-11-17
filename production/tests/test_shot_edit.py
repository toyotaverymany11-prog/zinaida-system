import json
import unittest
from production.core import ProductionError, read_json
from production.media import release_check
from production.shot_edit import build, package_preview
from production.tests import test_shots as fixtures


class ShotEdit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):fixtures.BoundShot.setUpClass()

    @classmethod
    def tearDownClass(cls):fixtures.BoundShot.tearDownClass()

    def setUp(self):
        self.case=fixtures.BoundShot();self.case.setUp();self.addCleanup(self.case.doCleanups)
        self.case.execute();self.output=self.case.root/'edit'

    def build(self):
        return build(self.case.root,self.case.ident,self.case.request['request_id'],self.output)

    def test_actual_render_editable_timeline_idempotence_and_no_release(self):
        result=self.build()
        self.assertTrue(all(result['technical_checks'].values()))
        self.assertEqual(result,self.build())
        import opentimelineio as otio
        timeline=otio.adapters.read_from_file(str(self.output/'render/timeline.otio'))
        self.assertEqual(timeline.tracks[0][0].source_range.duration.value,48)
        manifest=read_json(self.output/'manifest.json')
        with self.assertRaisesRegex(ProductionError,'previews cannot be released'):
            release_check(manifest,self.output,self.output/'render',[])

    def test_changed_edit_manifest_is_not_reused(self):
        self.build();p=self.output/'manifest.json';m=read_json(p);m['clips'][0]['purpose']='changed'
        p.write_text(json.dumps(m))
        with self.assertRaisesRegex(ProductionError,'manifest changed'):self.build()

    def test_portable_archive_has_resolvable_relative_media_and_original_bytes(self):
        import zipfile
        import opentimelineio as otio
        from production.core import digest
        self.build();path=package_preview(self.output)
        unpack=self.case.root/'unpacked'
        with zipfile.ZipFile(path) as z:z.extractall(unpack)
        timeline=otio.adapters.read_from_file(str(unpack/'timeline.otio'))
        refs=[c.media_reference.target_url for c in timeline.find_clips()]
        self.assertEqual(refs,['assets/shot.mp4'])
        self.assertEqual(digest(unpack/refs[0]),digest(self.output/'assets/shot.mp4'))
        self.assertFalse(read_json(unpack/'checks.json')['finished_video_accepted'])

    def test_changed_render_cannot_be_packaged(self):
        self.build();(self.output/'render/master.mp4').write_bytes(b'bad')
        with self.assertRaisesRegex(ProductionError,'changed before packaging'):package_preview(self.output)
