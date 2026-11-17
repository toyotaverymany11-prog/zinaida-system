import io
import json
import re
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from uuid import uuid4

from production.core import ProductionError
from production.demo import make_fixture
from production.intake import Intake, server


class IntakeIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=tempfile.TemporaryDirectory()
        cls.source=Path(cls.fixture.name)/'source'
        make_fixture(cls.source)

    @classmethod
    def tearDownClass(cls): cls.fixture.cleanup()

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.intake=Intake(self.root)

    def upload(self,name):
        data=(self.source/name).read_bytes()
        return self.intake.upload(name,io.BytesIO(data),len(data))['id']

    def test_reference_and_character_survive_reopen_without_duplicate_order(self):
        data={'request_id':str(uuid4()),'mode':'body_replace','brief':'Медведь берёт чашку',
              'references':[self.upload('red.mp4')],'characters':[self.upload('qr.png')]}
        result=self.intake.create(data)
        reopened=Intake(self.root)
        self.assertEqual(reopened.create(data),result)
        self.assertEqual(len(reopened.orders()),1)
        self.assertFalse(result['generation_authorized'])
        self.assertEqual(result['budget_usd'],0)
        self.assertEqual(result['references'][0]['kind'],'video')
        with self.assertRaisesRegex(ProductionError,'different order'):
            reopened.create(dict(data,brief='Другое задание'))

    def test_missing_source_character_and_budget_override_are_rejected(self):
        data={'request_id':str(uuid4()),'mode':'face_replace','brief':'Заменить лицо'}
        with self.assertRaises(ProductionError): self.intake.create(data)
        data['references']=[self.upload('red.mp4')]
        with self.assertRaises(ProductionError): self.intake.create(data)
        with self.assertRaises(ProductionError):
            self.intake.create(dict(data,mode='new_video',budget_usd=100))
        self.assertEqual(self.intake.orders(),[])

    def test_voice_is_stored_without_claiming_transcription(self):
        result=self.intake.create({'request_id':str(uuid4()),'mode':'new_video','voice':self.upload('tone.wav')})
        self.assertEqual(result['status'],'needs_transcription')
        self.assertEqual(result['brief'],'')

    def test_changed_media_and_incomplete_upload_fail(self):
        ident=self.upload('red.mp4')
        (self.root/'assets'/ident).write_bytes(b'changed')
        with self.assertRaisesRegex(ProductionError,'changed'):
            self.intake.create({'request_id':str(uuid4()),'mode':'reference','brief':'Тест','references':[ident]})
        with self.assertRaisesRegex(ProductionError,'Incomplete'):
            self.intake.upload('partial.mp4',io.BytesIO(b'x'),10)
        with self.assertRaises(ProductionError):
            self.intake.upload('payload.html',io.BytesIO(b'x'),1)

    def test_http_requires_local_origin_and_session_token(self):
        http=server(self.root,0)
        thread=threading.Thread(target=http.serve_forever,daemon=True)
        thread.start()
        self.addCleanup(http.server_close)
        self.addCleanup(http.shutdown)
        url=f'http://127.0.0.1:{http.server_port}'
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
        html=opener.open(url).read().decode()
        token=re.search(r"const token='([^']+)'",html)[1]
        payload=json.dumps({'request_id':str(uuid4()),'mode':'new_video','brief':'Проверка окна'}).encode()
        for headers in ({},{'X-Intake-Token':token,'Origin':'https://other.example'},
                        {'X-Intake-Token':token,'Host':'other.example'}):
            with self.assertRaises(urllib.error.HTTPError) as e:
                opener.open(urllib.request.Request(url+'/api/orders',data=payload,headers=headers))
            self.assertEqual(e.exception.code,403)
        req=urllib.request.Request(url+'/api/orders',data=payload,headers={'X-Intake-Token':token})
        self.assertEqual(json.load(opener.open(req))['brief'],'Проверка окна')


if __name__=='__main__': unittest.main()
