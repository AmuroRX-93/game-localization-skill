"""Synthetic regression cases; optional FFmpeg integration, no downloaded models."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
import wave

SOURCE=Path(__file__).resolve().parents[1]/'skills/game-localization/scripts/media_toolkit.py'
spec=importlib.util.spec_from_file_location('media_toolkit',SOURCE)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


class MediaTests(unittest.TestCase):
    def setUp(self):
        self.doc={'cues':[{'id':'a','start':0.25,'end':2.0,'source':'Source.',
                           'text':'示例字幕。','reviewed':True}]}

    def test_srt_ass_timestamps(self):
        self.assertIn('00:00:00,250 --> 00:00:02,000',m.export_subs(self.doc,'text','srt'))
        self.assertIn('Dialogue: 0,0:00:00.25,0:00:02.00',m.export_subs(self.doc,'text','ass'))
        self.assertEqual(m.stamp(59.9999),'00:01:00,000')

    def test_duplicate_ids_rejected(self):
        self.doc['cues']*=2
        with self.assertRaises(ValueError):m.validate(self.doc)

    def test_invalid_times(self):
        for a,b in [(0,0),(-1,2),(float('nan'),2),(0,float('inf')),(True,2)]:
            self.doc['cues'][0].update(start=a,end=b)
            with self.assertRaises(ValueError):m.validate(self.doc)

    def test_nested_overlap_detected(self):
        self.doc['cues'][0]['end']=20
        self.doc['cues'] += [dict(self.doc['cues'][0],id='b',start=2,end=3),dict(self.doc['cues'][0],id='c',start=4,end=5)]
        self.assertEqual([x['id'] for x in m.validate(self.doc) if 'overlap' in x['issues']],['b','c'])

    def test_empty_translation_not_silently_source(self):
        self.doc['cues'][0]['text']=''
        with self.assertRaises(ValueError):m.export_subs(self.doc,'text','srt')
        self.assertIn('Source.',m.export_subs(self.doc,'source','srt'))

    def test_ass_controls_rejected(self):
        self.doc['cues'][0]['text']=r'{\p1}drawing'
        with self.assertRaises(ValueError):m.export_subs(self.doc,'text','ass')

    def test_srt_blank_paragraph_rejected(self):
        self.doc['cues'][0]['text']='a\n\nb'
        with self.assertRaises(ValueError):m.export_subs(self.doc,'text','srt')

    def test_sub_centisecond_ass_rejected(self):
        self.doc['cues'][0].update(start=1.001,end=1.002)
        with self.assertRaises(ValueError):m.export_subs(self.doc,'text','ass')

    def test_qa_flags(self):
        self.doc['cues'][0].update(text='中'*30,reviewed=False,end=0.5)
        flags=m.validate(self.doc,duration=0.4)[0]['issues']
        self.assertTrue({'reading_speed','long_line','unreviewed','past_media_end'} <= set(flags))

    def test_existing_output_and_symlink_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'已有 中文.txt';p.write_text('keep')
            with self.assertRaises(ValueError):m.write_text(p,'replace')
            self.assertEqual(p.read_text(),'keep')
            link=Path(d)/'link';link.symlink_to(p)
            with self.assertRaises(ValueError):m.write_text(link,'replace')

    def test_missing_local_model_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError,'complete local'):m.transcribe('none.wav',d,'ja')

    def test_asr_adapter_contract_not_model_inference(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);wav=root/'speech.wav'
            with wave.open(str(wav),'wb') as w:
                w.setparams((1,2,16000,0,'NONE',''));w.writeframes(b'\0\0'*16000)
            for f in ('model.bin','config.json','tokenizer.json','preprocessor_config.json'):(root/f).write_text('{}')
            captured={}
            class FakeModel:
                def __init__(self,*args,**kwargs):captured['init']=kwargs
                def transcribe(self,*args,**kwargs):
                    captured['transcribe']=kwargs
                    seg=types.SimpleNamespace(start=0.1,end=0.8,text=' 原文 ',avg_logprob=-0.2,no_speech_prob=0.1,words=[])
                    return iter([seg]),types.SimpleNamespace(language='ja')
            with patch.dict(sys.modules,{'faster_whisper':types.SimpleNamespace(WhisperModel=FakeModel)}),patch.dict(os.environ,{}):
                doc=m.transcribe(wav,root,'ja',offset=10)
                self.assertEqual(os.environ['HF_HUB_OFFLINE'],'1')
            self.assertTrue(captured['init']['local_files_only'])
            self.assertEqual(captured['transcribe']['task'],'transcribe')
            self.assertEqual(doc['cues'][0]['start'],10.1)
            self.assertEqual(doc['cues'][0]['source'],'原文')
            self.assertEqual(doc['cues'][0]['text'],'')
            self.assertFalse(doc['cues'][0]['reviewed'])


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'),'FFmpeg unavailable')
class FFmpegTests(unittest.TestCase):
    def test_audio_selection_and_candidate_video(self):
        with tempfile.TemporaryDirectory(prefix='媒体 测试 ') as d:
            r=Path(d);src=r/'original.mkv';audio=r/'voice.wav'
            m.run(['ffmpeg','-v','error','-f','lavfi','-i','color=c=blue:s=160x120:r=10:d=1',
                   '-f','lavfi','-i','sine=frequency=440:duration=1','-f','lavfi','-i','sine=frequency=880:duration=1',
                   '-map','0:v','-map','1:a','-map','2:a','-vf','drawbox=x=30:y=65:w=50:h=10:color=white:t=fill',
                   '-c:v','libx264','-c:a','pcm_s16le',src])
            before=m.sha(src)
            self.assertEqual(m.main(['extract',str(src),str(audio),'--audio','1','--channel','0']),0)
            with wave.open(str(audio),'rb') as w:self.assertEqual((w.getnchannels(),w.getframerate(),w.getsampwidth()),(1,16000,2))
            with self.assertRaises(ValueError):m.main(['extract',str(src),str(r/'bad.wav'),'--audio','2'])
            self.assertFalse((r/'bad.wav').exists())
            if m.has_filter('ffmpeg','delogo'):
                out=r/'delogo.mp4'
                m.main(['delogo-preview',str(src),str(out),'--box','20','60','80','20','--start','0.2','--end','0.7'])
                p=m.probe(out);self.assertEqual(len([s for s in p['streams'] if s['codec_type']=='audio']),2)
                self.assertGreater(out.stat().st_size,0)
                frames=subprocess.run(['ffmpeg','-v','error','-i',str(out),'-an','-f','rawvideo','-pix_fmt','rgb24','-'],capture_output=True,check=True).stdout
                stride=160*120*3;pixel=(70*160+40)*3
                # White patch remains outside the interval, disappears on blue inside it.
                self.assertGreater(frames[pixel],200)
                self.assertLess(frames[4*stride+pixel],50)
                self.assertGreater(frames[8*stride+pixel],200)
            self.assertEqual(m.sha(src),before)

    def test_failed_encode_does_not_publish(self):
        with tempfile.TemporaryDirectory() as d:
            output=Path(d)/'broken.mp4'
            with self.assertRaises(ValueError):m.ffmpeg_output('ffmpeg',['-i',str(Path(d)/'missing.mp4')],output)
            self.assertFalse(output.exists())
            self.assertEqual(list(Path(d).iterdir()),[])

    def test_subtitle_filter_diagnostic(self):
        # Check advertised FFmpeg availability agrees with the tool's doctor predicate.
        raw=m.run(['ffmpeg','-hide_banner','-filters'])
        self.assertEqual(m.has_filter('ffmpeg','subtitles'),any(' subtitles ' in line for line in raw.splitlines()))

    def test_burn_if_libass_available(self):
        if not m.has_filter('ffmpeg','subtitles'):self.skipTest('FFmpeg lacks libass/subtitles')
        with tempfile.TemporaryDirectory(prefix="字幕 空格 ' ") as d:
            r=Path(d);src=r/'src.mp4';srt=r/"中文 '字幕.srt";out=r/'out.mp4'
            m.run(['ffmpeg','-v','error','-f','lavfi','-i','color=c=black:s=320x180:r=10:d=1','-c:v','libx264',src])
            srt.write_text('1\n00:00:00,100 --> 00:00:00,900\nSubtitle test\n',encoding='utf-8')
            m.main(['burn-preview',str(src),str(srt),str(out)])
            self.assertGreater(out.stat().st_size,0)


if __name__=='__main__':unittest.main()
