#!/usr/bin/env python3
"""Offline localization tools. --help lists stable agent-callable commands."""
import argparse
import importlib.util
import json
from pathlib import Path
import platform
import re
import shutil
import struct
import sys
from toolkit.common import candidate,file_sha,read_at,require,sha,write_json
from toolkit.suiten_formats import container_index,xmb_parse,xmb_rebuild
from toolkit import delta


def emit(value):print(json.dumps(value,ensure_ascii=False,indent=2))
def load(path):return json.loads(Path(path).read_text(encoding='utf-8'))


def doctor(_):
    emit(dict(python=platform.python_version(),core_ok=sys.version_info>=(3,9),optional={m:bool(importlib.util.find_spec(m)) for m in ['PIL','numpy','fontTools']},external={n:bool(shutil.which(n)) for n in ['ffmpeg','ffprobe','xdelta3']},network_required=False))


def inventory(a):
    root=Path(a.root).resolve();require(root.is_dir(),'root is not a directory')
    rows=[]
    for p in sorted(root.rglob('*')):
        if p.is_symlink():rows.append(dict(path=p.relative_to(root).as_posix(),status='symlink_skipped'));continue
        if p.is_file():rows.append(dict(path=p.relative_to(root).as_posix(),bytes=p.stat().st_size,sha256=file_sha(p),status='hashed_not_parsed'))
    write_json(a.output,dict(format=1,files=rows,runtime_verified=False));emit(dict(files=len(rows),output=str(a.output)))


def container(a):
    src=Path(a.input);index=container_index(src)
    if a.action=='list':emit(index);return
    found=[e for e in index['entries'] if e['name']==a.member];require(len(found)==1,'member not found');e=found[0]
    old=read_at(src,e['offset'],e['size'])
    if a.action=='extract':
        with candidate(a.output,[src]) as temp:temp.write_bytes(old)
        emit(dict(bytes=len(old),sha256=sha(old)));return
    require(sha(old)==a.expect_member_sha256,'member baseline mismatch')
    new=Path(a.replacement).read_bytes();fmt=index['format']
    require(fmt=='suiten-arb' or len(new)==len(old),'FPK/TEX supports fixed-size replacement only')
    with candidate(a.output,[src,a.replacement]) as temp:
        shutil.copyfile(src,temp)
        with temp.open('r+b') as f:
            if len(new)==len(old):f.seek(e['offset']);f.write(new)
            else:
                f.seek(0,2);off=(f.tell()+15)//16*16;f.write(bytes(off-f.tell()));f.write(new)
                f.seek(e['index']);f.write(struct.pack('>II',off-index['base'],len(new)))
        result=container_index(temp);newentry=next(x for x in result['entries'] if x['name']==e['name'])
        require(read_at(temp,newentry['offset'],newentry['size'])==new,'member verification failed')
        require([x for x in result['entries'] if x['name']!=e['name']]==[x for x in index['entries'] if x['name']!=e['name']],'unrelated index changed')
    emit(dict(format=fmt,before=sha(old),after=sha(new),candidate_sha256=file_sha(a.output),runtime_verified=False))


def xmb(a):
    src=Path(a.input);b=src.read_bytes();_,rows=xmb_parse(b)
    require(xmb_rebuild(b,{})==b,'identity roundtrip failed')
    if a.action=='export':
        write_json(a.output,dict(format='suiten-xmb-v1',source_sha256=sha(b),entries=[dict(id=r['id'],source=r['source'],translation=None,protected_tokens=[]) for r in rows]),[src]);emit(dict(entries=len(rows)));return
    table=load(a.table);require(table['format']=='suiten-xmb-v1' and table['source_sha256']==sha(b),'table baseline mismatch')
    entries=table['entries'];require(len(entries)==len(rows) and len({r['id'] for r in entries})==len(rows),'missing or duplicate table IDs')
    original={r['id']:r['source'] for r in rows};require({r['id']:r['source'] for r in entries}==original,'table source/ID mismatch')
    translations={r['id']:r['translation'] for r in entries if r['translation'] is not None}
    issues=text_issues(entries)
    require(not [x for x in issues if x['severity']=='error'],'protected tokens/translation invalid: '+str(issues))
    result=xmb_rebuild(b,translations)
    with candidate(a.output,[src,a.table]) as temp:temp.write_bytes(result)
    emit(dict(entries=len(rows),changed=sum(translations.get(r['id'],r['source'])!=r['source'] for r in rows),before=sha(b),after=sha(result),runtime_verified=False))


def text_issues(entries,glyphs=None):
    issues=[];seen=set();translations={}
    for row in entries:
        key=row['id'];source=row['source'];text=row.get('translation')
        if key in seen:issues.append(dict(id=key,severity='error',reason='duplicate ID'))
        seen.add(key)
        if text is None:issues.append(dict(id=key,severity='warning',reason='untranslated'));continue
        if not isinstance(text,str) or '\0' in text:issues.append(dict(id=key,severity='error',reason='invalid text/NUL'));continue
        tokens=row.get('protected_tokens',[])
        require(isinstance(tokens,list) and all(isinstance(x,str) and x for x in tokens),'tokens must be non-empty strings')
        # Adapter supplies token vocabulary; no universal control-code regex is assumed.
        if tokens:
            pattern='|'.join(re.escape(t) for t in sorted(set(tokens),key=len,reverse=True))
            if re.findall(pattern,source)!=re.findall(pattern,text):issues.append(dict(id=key,severity='error',reason='protected token sequence changed'))
        if source.count('\n')!=text.count('\n'):issues.append(dict(id=key,severity='warning',reason='line count changed; review layout'))
        if glyphs is not None:
            missing=sorted(set(c for c in text if not c.isspace())-glyphs)
            if missing:issues.append(dict(id=key,severity='error',reason='missing glyphs',characters=''.join(missing)))
        translations.setdefault(source,set()).add(text)
    for source,values in translations.items():
        if len(values)>1:issues.append(dict(severity='warning',reason='same source, different translations; context review needed',source=source,translations=sorted(values)))
    return issues


def text_check(a):
    table=load(a.table);glyphs=set(Path(a.glyphs).read_text(encoding='utf-8')) if a.glyphs else None
    issues=text_issues(table['entries'],glyphs);emit(dict(issues=issues,semantic_review_performed=False))
    if any(x['severity']=='error' for x in issues):raise SystemExit(1)


def font_check(font,texts,index):
    from fontTools.ttLib import TTFont
    with TTFont(str(font),fontNumber=index) as f:cmap=f.getBestCmap() or {}
    return sorted({c for text in texts for c in text if not c.isspace() and ord(c) not in cmap})


def font_command(a):
    missing=font_check(a.font,[Path(a.text).read_text(encoding='utf-8')],a.font_index)
    emit(dict(missing=''.join(missing),cmap_only=True,shaping_verified=False))
    if missing:raise SystemExit(1)


def texture(a):
    from toolkit.ui_texture import rebuild_gtf
    labels=load(a.labels);missing=font_check(a.font,[x['text'] for x in labels],a.font_index)
    require(not missing,'font lacks glyphs: '+''.join(missing))
    b=Path(a.input).read_bytes();require(sha(b)==a.expect_sha256,'GTF baseline mismatch')
    rebuilt,_,_,report=rebuild_gtf(b,labels,a.font,a.font_index)
    with candidate(a.output,[a.input,a.labels,a.font]) as temp:temp.write_bytes(rebuilt)
    emit(dict(before=sha(b),after=sha(rebuilt),audit=report,runtime_verified=False))


def preview(a):
    from PIL import Image
    from toolkit.ui_texture import validate_gtf
    b=Path(a.input).read_bytes();w,h=validate_gtf(b)
    if b[24]==0x88:im=Image.frombytes('RGBA',(w,h),b[128:128+w*h],'bcn',(3,'DXT5'))
    else:
        pitch=struct.unpack_from('>I',b,40)[0];im=Image.frombytes('RGBA',(w,h),b[128:128+pitch*h],'raw','ARGB',pitch)
    with candidate(a.output,[a.input]) as temp:im.save(temp,format='PNG')
    emit(dict(width=w,height=h))


def uv(a):
    import math
    x0,y0,x1,y1=a.box;w,h=a.size
    require(all(math.isfinite(v) for v in [x0,y0,x1,y1,w,h]) and w>0 and h>0 and 0<=x0<x1<=w and 0<=y0<y1<=h,'invalid pixel rectangle')
    result=[x0/w,y0/h,x1/w,y1/h] if a.origin=='top' else [x0/w,1-y1/h,x1/w,1-y0/h]
    emit(dict(uv_bounds=result,origin=a.origin,animation_or_mesh_not_modified=True))


def parser():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    s=sub.add_parser('doctor');s.set_defaults(func=doctor)
    s=sub.add_parser('inventory');s.add_argument('root',type=Path);s.add_argument('--output',required=True,type=Path);s.set_defaults(func=inventory)
    s=sub.add_parser('container');ss=s.add_subparsers(dest='action',required=True)
    for action in ('list','extract','replace'):
        c=ss.add_parser(action);c.add_argument('input',type=Path);c.set_defaults(func=container)
        if action!='list':c.add_argument('--member',required=True);c.add_argument('--output',required=True,type=Path)
        if action=='replace':c.add_argument('--replacement',required=True,type=Path);c.add_argument('--expect-member-sha256',required=True)
    s=sub.add_parser('xmb');ss=s.add_subparsers(dest='action',required=True)
    for action in ('export','import'):
        c=ss.add_parser(action);c.add_argument('input',type=Path);c.add_argument('--output',required=True,type=Path);c.set_defaults(func=xmb)
        if action=='import':c.add_argument('--table',required=True,type=Path)
    s=sub.add_parser('text-check');s.add_argument('table',type=Path);s.add_argument('--glyphs',type=Path);s.set_defaults(func=text_check)
    s=sub.add_parser('font-check');s.add_argument('--font',type=Path,required=True);s.add_argument('--text',type=Path,required=True);s.add_argument('--font-index',type=int,default=0);s.set_defaults(func=font_command)
    s=sub.add_parser('gtf-typeset');s.add_argument('input',type=Path);s.add_argument('--labels',type=Path,required=True);s.add_argument('--font',type=Path,required=True);s.add_argument('--font-index',type=int,default=0);s.add_argument('--expect-sha256',required=True);s.add_argument('--output',type=Path,required=True);s.set_defaults(func=texture)
    s=sub.add_parser('gtf-preview');s.add_argument('input',type=Path);s.add_argument('--output',type=Path,required=True);s.set_defaults(func=preview)
    s=sub.add_parser('uv');s.add_argument('--box',nargs=4,type=float,required=True);s.add_argument('--size',nargs=2,type=float,required=True);s.add_argument('--origin',choices=['top','bottom'],required=True);s.set_defaults(func=uv)
    s=sub.add_parser('delta');ss=s.add_subparsers(dest='action',required=True)
    c=ss.add_parser('create');c.add_argument('old',type=Path);c.add_argument('new',type=Path);c.add_argument('--output',type=Path,required=True);c.set_defaults(func=lambda a:emit(delta.create(a.old,a.new,a.output)))
    c=ss.add_parser('apply');c.add_argument('old',type=Path);c.add_argument('patch',type=Path);c.add_argument('--output',type=Path,required=True);c.set_defaults(func=lambda a:emit(delta.apply(a.old,a.patch,a.output)))
    return p


def main():
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
    require(sys.version_info>=(3,9),'Python 3.9+ required');a=parser().parse_args();a.func(a)

if __name__=='__main__':
    try:main()
    except ImportError as e:
        emit(dict(error=str(e),hint='Optional UI tools require: pip install -r requirements-ui.txt'));sys.exit(2)
    except (OSError,ValueError,KeyError,TypeError,struct.error,OverflowError) as e:
        emit(dict(error=str(e)));sys.exit(2)
