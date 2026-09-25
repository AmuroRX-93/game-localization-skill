"""Behavioral tests with generated data only; no game/third-party assets."""
import importlib.util
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest

SCRIPTS=Path(__file__).resolve().parents[1]/'skills/game-localization/scripts'
sys.path.insert(0,str(SCRIPTS))
import localization_toolkit as cli
from toolkit import delta
from toolkit.common import candidate,file_sha
from toolkit.suiten_formats import xmb_parse,xmb_rebuild,container_index
from make_toolkit_demo import make_xmb,make_arb


class ToolkitTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory(prefix='中文 toolkit ');self.addCleanup(t.cleanup);self.d=Path(t.name)
    def write(self,name,b):p=self.d/name;p.write_bytes(b);return p
    def test_xmb_roundtrip_and_growth(self):
        b=make_xmb(['日本語','Hello [$name]']);self.assertEqual(xmb_rebuild(b,{}),b)
        n=xmb_rebuild(b,{'00000001':'更长的简体中文句子'});self.assertEqual(xmb_parse(n)[1][0]['source'],'更长的简体中文句子')
    def test_xmb_reject_duplicate_id(self):
        b=bytearray(make_xmb(['a','b']));struct.pack_into('>I',b,48+32+12,1)
        with self.assertRaises(ValueError):xmb_parse(b)
    def test_xmb_reject_nonzero_padding(self):
        b=make_xmb(['text'])+b'\0a'
        with self.assertRaises(ValueError):xmb_parse(b)
    def test_xmb_reject_unknown_and_nul(self):
        b=make_xmb(['x'])
        for t in [{'bad':'x'},{'00000001':'\0'}]:
            with self.assertRaises(ValueError):xmb_rebuild(b,t)
    def test_xmb_bad_pool(self):
        b=bytearray(make_xmb(['x']));struct.pack_into('>I',b,48+28,0xffffffff)
        with self.assertRaises(ValueError):xmb_parse(b)
    def test_arb_growth_preserves_source_and_other_member(self):
        b=make_arb({'a':b'abc','b':b'untouched'});src=self.write('a.arb',b);rep=self.write('rep',b'longer translated text')
        a=cli.parser().parse_args(['container','replace',str(src),'--member','a','--replacement',str(rep),'--expect-member-sha256',cli.sha(b'abc'),'--output',str(self.d/'new')]);cli.container(a)
        index=container_index(self.d/'new');self.assertEqual(src.read_bytes(),b)
        old=container_index(src)['entries'][1];self.assertEqual(index['entries'][1],old)
        self.assertEqual(cli.read_at(self.d/'new',old['offset'],old['size']),b'untouched')
    def test_arb_duplicate_overlap_bad_bounds(self):
        raw=make_arb({'a':b'abc','b':b'def'})
        for pos,value in [(16,0xffffffff),(16+18,0)]:
            b=bytearray(raw);struct.pack_into('>I',b,pos,value);src=self.write('bad',b)
            with self.assertRaises(ValueError):container_index(src)
    def test_fpk_tex_fixed_replacement(self):
        fpk=bytearray(96);fpk[:4]=b'FPK\0';struct.pack_into('>III',fpk,4,1,16,96);fpk[16:18]=b'a\0';struct.pack_into('>II',fpk,80,0,3);fpk.extend(b'abc')
        tex=bytearray(32);tex[:4]=b'TEX ';struct.pack_into('>I',tex,8,1);struct.pack_into('>II',tex,16,32,3);tex[24:26]=b'a\0';tex.extend(b'abc')
        for name,b in [('a.fpk',fpk),('a.tsb',tex)]:
            src=self.write(name,b);rep=self.write('rep',b'new');out=self.d/(name+'.new')
            args=['container','replace',str(src),'--member','a','--replacement',str(rep),'--expect-member-sha256',cli.sha(b'abc'),'--output',str(out)]
            cli.container(cli.parser().parse_args(args));self.assertEqual(out.read_bytes()[:-3],b[:-3]);self.assertEqual(out.read_bytes()[-3:],b'new')
            rep.write_bytes(b'long');args[-1]=str(self.d/(name+'.invalid'))
            with self.assertRaises(ValueError):cli.container(cli.parser().parse_args(args))
    def test_unknown_magic(self):
        with self.assertRaises(ValueError):container_index(self.write('weird.xmb',b'NOPE'))
    def test_output_no_overwrite(self):
        p=self.write('input',b'keep')
        with self.assertRaises(ValueError):
            with candidate(p,[p]):pass
        with self.assertRaises(ValueError):
            with candidate(p):pass
        self.assertEqual(p.read_bytes(),b'keep')
    def test_candidate_failure_leaves_no_output(self):
        p=self.d/'out'
        with self.assertRaises(RuntimeError):
            with candidate(p) as tmp:tmp.write_bytes(b'temp');raise RuntimeError('failed')
        self.assertFalse(p.exists());self.assertFalse(list(self.d.glob('.localization-*')))
    def test_delta_shift_and_wrong_input(self):
        b=bytes(range(256))*1024;a=self.write('old',b);n=self.write('new',b'shift'+b+b'end');folder=self.d/'delta'
        m=delta.create(a,n,folder);self.assertLess((folder/'payload.bin').stat().st_size,len(b));delta.apply(a,folder,self.d/'result');self.assertEqual((self.d/'result').read_bytes(),n.read_bytes())
        a.write_bytes(b'wrong')
        with self.assertRaises(ValueError):delta.apply(a,folder,self.d/'fail')
        self.assertFalse((self.d/'fail').exists())
    def test_delta_empty(self):
        for i,(a,b) in enumerate([(b'',b''),(b'',b'new'),(b'old',b'')]):
            old=self.write('old',a);new=self.write('new',b);folder=self.d/str(i);delta.create(old,new,folder);delta.apply(old,folder,self.d/(str(i)+'out'));self.assertEqual((self.d/(str(i)+'out')).read_bytes(),b)
    def test_delta_corrupt_payload(self):
        a=self.write('old',b'old');b=self.write('new',b'new');folder=self.d/'p';delta.create(a,b,folder);(folder/'payload.bin').write_bytes(b'bad')
        with self.assertRaises(ValueError):delta.apply(a,folder,self.d/'out')
        self.assertFalse((self.d/'out').exists())
    def test_delta_reject_segment_overflow(self):
        a=self.write('old',b'old');b=self.write('new',b'new');folder=self.d/'p';delta.create(a,b,folder);m=json.loads((folder/'delta.json').read_text());m['segments']=[['copy',99,3]];(folder/'delta.json').write_text(json.dumps(m))
        with self.assertRaises(ValueError):delta.apply(a,folder,self.d/'out')
    def test_tokens_duplicates_glyphs(self):
        rows=[dict(id='1',source='Hello [$name]',translation='你好',protected_tokens=['[$name]']),dict(id='1',source='Other',translation='字')]
        problems=cli.text_issues(rows,set('你好'));self.assertTrue(any('token' in x['reason'] for x in problems));self.assertTrue(any('duplicate' in x['reason'] for x in problems));self.assertTrue(any('glyph' in x['reason'] for x in problems))
    def test_consistency_is_warning_not_fake_semantic_proof(self):
        rows=[dict(id='1',source='Open',translation='打开'),dict(id='2',source='Open',translation='开放')]
        problems=cli.text_issues(rows);self.assertEqual(len(problems),1);self.assertEqual(problems[0]['severity'],'warning')
    def test_uv_bottom(self):
        from unittest.mock import patch
        a=cli.parser().parse_args(['uv','--box','0','0','32','16','--size','64','64','--origin','bottom'])
        with patch.object(cli,'emit') as emit:cli.uv(a)
        self.assertEqual(emit.call_args.args[0]['uv_bounds'],[0,.75,.5,1])


@unittest.skipUnless(all(importlib.util.find_spec(m) for m in ['PIL','numpy','fontTools']),'optional UI dependencies absent')
class TextureTests(unittest.TestCase):
    def gtf(self,fmt):
        from PIL import Image
        from toolkit.ui_texture import encode_bc3
        import numpy as np
        im=Image.new('RGBA',(16,16),(255,255,255,255));header=bytearray(128);header[:4]=bytes.fromhex('01030000');struct.pack_into('>I',header,8,1);struct.pack_into('>I',header,16,128);header[24]=fmt;header[25]=1;header[26]=2;struct.pack_into('>HHH',header,32,16,16,1)
        if fmt==0x88:data=encode_bc3(im)
        else:struct.pack_into('>I',header,40,64);data=np.array(im)[:,:,[3,0,1,2]].tobytes()
        return bytes(header)+data
    def test_gtf_identity_both_formats(self):
        from toolkit.ui_texture import rebuild_gtf
        for fmt in [0x88,0xa5]:
            b=self.gtf(fmt);self.assertEqual(rebuild_gtf(b,[],'unused.ttf')[0],b)
    def test_gtf_bad_variant_rejected(self):
        from toolkit.ui_texture import validate_gtf
        for offset,value in [(24,0),(26,3),(27,1)]:
            b=bytearray(self.gtf(0x88));b[offset]=value
            with self.assertRaises(ValueError):validate_gtf(b)
    def test_gtf_typeset_synthetic_font_preserves_blocks(self):
        from fontTools.fontBuilder import FontBuilder
        from fontTools.pens.ttGlyphPen import TTGlyphPen
        from toolkit.ui_texture import rebuild_gtf
        with tempfile.TemporaryDirectory() as td:
            font=Path(td)/'synthetic.ttf';fb=FontBuilder(1000,isTTF=True);fb.setupGlyphOrder(['.notdef','A']);fb.setupCharacterMap({65:'A'})
            pen=TTGlyphPen(None);pen.moveTo((0,0));pen.lineTo((400,0));pen.lineTo((200,700));pen.closePath();glyph=pen.glyph()
            fb.setupGlyf({'.notdef':glyph,'A':glyph});fb.setupHorizontalMetrics({'.notdef':(500,0),'A':(500,0)});fb.setupHorizontalHeader(ascent=800,descent=-200);fb.setupNameTable({'familyName':'Synthetic','styleName':'Regular'});fb.setupOS2(sTypoAscender=800,sTypoDescender=-200,usWinAscent=800,usWinDescent=200);fb.setupPost();fb.setupMaxp();fb.save(font)
            for fmt in [0x88,0xa5]:
                b=self.gtf(fmt);new,_,_,_=rebuild_gtf(b,[dict(text='A',box=[0,0,8,12],align='center',ink_height=8)],font)
                self.assertEqual(new[:128],b[:128]);self.assertEqual(len(new),len(b));self.assertNotEqual(new,b)
                if fmt==0x88:self.assertEqual(new[128+3*16:128+4*16],b[128+3*16:128+4*16])

if __name__=='__main__':unittest.main()
