import hashlib
import importlib.util
from pathlib import Path
import unittest
from uuid import uuid4

spec=importlib.util.spec_from_file_location('video_media',Path(__file__).parents[1]/'megamozg/video_media.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


class MediaTests(unittest.TestCase):
    def test_range_full_partial_suffix_and_invalid(self):
        for value,expected in [(None,(0,9,False)),('bytes=2-5',(2,5,True)),('bytes=7-',(7,9,True)),('bytes=-3',(7,9,True)),('bytes=0-999',(0,9,True))]:self.assertEqual(m.interval(value,10),expected)
        for value in ['bytes=10-','bytes=4-2','bytes=-0','bytes=-','bytes=0-1,5-6']:
            with self.assertRaises(ValueError):m.interval(value,10)

    def test_exact_bytes_binding_and_current_required(self):
        link={'task_id':str(uuid4())};data=b'video';p=dict(binding=link,revision='a'*64,kind='video',sha256=hashlib.sha256(data).hexdigest(),data=data,current=True)
        self.assertEqual(m.validate(p,link,'a'*64,'video'),data)
        for key,value in [('data',b'changed'),('current',False),('revision','b'*64),('kind','project'),('binding',{})]:
            with self.assertRaises(ValueError):m.validate(dict(p,**{key:value}),link,'a'*64,'video')
