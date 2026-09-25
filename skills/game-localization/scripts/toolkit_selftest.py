#!/usr/bin/env python3
"""Asset-free CLI acceptance test; works from an arbitrary current directory."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parent

def run(*args,expected=0):
    p=subprocess.run([sys.executable,str(ROOT/'localization_toolkit.py'),*map(str,args)],capture_output=True,text=True,encoding='utf-8')
    if p.returncode!=expected:raise RuntimeError(p.stdout+p.stderr)
    return json.loads(p.stdout)

def main():
    with tempfile.TemporaryDirectory(prefix='localization agent 中文 ') as d:
        d=Path(d);demo=d/'demo'
        subprocess.run([sys.executable,str(ROOT/'make_toolkit_demo.py'),'--output',str(demo)],check=True,stdout=subprocess.DEVNULL)
        source=demo/'sample.xmb';before=source.read_bytes();table=demo/'table.json'
        run('xmb','export',source,'--output',table)
        t=json.loads(table.read_text(encoding='utf-8'));t['entries'][0]['translation']='补给弹药。';t['entries'][1].update(translation='你好，[$name]！',protected_tokens=['[$name]']);table.write_text(json.dumps(t,ensure_ascii=False),encoding='utf-8')
        run('text-check',table,'--glyphs',demo/'glyphs.txt')
        result=run('xmb','import',source,'--table',table,'--output',demo/'translated.xmb')
        run('xmb','export',demo/'translated.xmb','--output',demo/'reread.json')
        reread=json.loads((demo/'reread.json').read_text(encoding='utf-8'))
        if [r['source'] for r in reread['entries']]!=[r['translation'] for r in t['entries']]:raise ValueError('text roundtrip')
        run('delta','create',source,demo/'translated.xmb','--output',demo/'patch')
        run('delta','apply',source,demo/'patch','--output',demo/'restored.xmb')
        if (demo/'restored.xmb').read_bytes()!=(demo/'translated.xmb').read_bytes():raise ValueError('delta roundtrip')
        run('container','replace',demo/'sample.arb','--member','game/language/demo.xmb','--replacement',demo/'translated.xmb','--expect-member-sha256',hashlib.sha256(before).hexdigest(),'--output',demo/'candidate.arb')
        run('container','extract',demo/'candidate.arb','--member','game/language/demo.xmb','--output',demo/'member.xmb')
        if (demo/'member.xmb').read_bytes()!=(demo/'translated.xmb').read_bytes():raise ValueError('container roundtrip')
        run('container','extract',demo/'candidate.arb','--member','game/untouched.bin','--output',demo/'untouched.bin')
        if (demo/'untouched.bin').read_bytes()!=b'SYNTHETIC_UNCHANGED_MEMBER':raise ValueError('unrelated member changed')
        (demo/'wrong.bin').write_bytes(b'wrong');run('delta','apply',demo/'wrong.bin',demo/'patch','--output',demo/'must-not-exist.bin',expected=2)
        run('xmb','import',source,'--table',table,'--output',source,expected=2)
        if source.read_bytes()!=before or (demo/'must-not-exist.bin').exists():raise ValueError('input protection failed')
        print(json.dumps(dict(passed=True,synthetic_only=True,checks=['text_export_import','protected_tokens','glyph_table','delta_roundtrip','container_roundtrip','unchanged_member','wrong_baseline_rejected','overwrite_rejected','unicode_paths'],runtime_verified=False)))

if __name__=='__main__':main()
