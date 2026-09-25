"""Streaming/mmap copy-add difference files, including shifted unchanged ranges."""
import contextlib
import json
import mmap
from pathlib import Path
from .common import candidate,file_sha,require,write_json


@contextlib.contextmanager
def mapped(path):
    with Path(path).open('rb') as f:
        if Path(path).stat().st_size:
            with mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as m:yield m
        else:yield b''


def create(old,new,output):
    output=Path(output);require(not output.exists(),'delta output must be a new directory');output.mkdir()
    try:
        with mapped(old) as a,mapped(new) as b,(output/'payload.bin').open('xb') as payload:
            shifts={0};segments=[];pos=0
            for at in (len(a)//4,len(a)//2,3*len(a)//4):
                if at+128<=len(a):
                    match=b.find(a[at:at+128])
                    if match>=0:shifts.add(match-at)
            for q in range(0,len(b),65536):
                chunk=b[q:q+65536]
                off=next((q-s for s in sorted(shifts) if q-s>=0 and a[q-s:q-s+len(chunk)]==chunk),None)
                if off is None:kind='add';off=pos;payload.write(chunk);pos+=len(chunk)
                else:kind='copy'
                if segments and segments[-1][0]==kind and segments[-1][1]+segments[-1][2]==off:segments[-1][2]+=len(chunk)
                else:segments.append([kind,off,len(chunk)])
        m=dict(format=1,before=file_sha(old),after=file_sha(new),old_size=Path(old).stat().st_size,new_size=Path(new).stat().st_size,blob='payload.bin',blob_sha256=file_sha(output/'payload.bin'),segments=segments)
        write_json(output/'delta.json',m)
        # Rebuild in the temporary patch folder and compare before publishing success.
        apply(old,output,output/'roundtrip.bin');(output/'roundtrip.bin').unlink()
        return m
    except BaseException:
        import shutil
        shutil.rmtree(output);raise


def apply(old,patch,output):
    patch=Path(patch);m=json.loads((patch/'delta.json').read_text(encoding='utf-8'))
    require(m['format']==1 and m['blob']=='payload.bin','unsupported delta manifest')
    blob=patch/'payload.bin'
    require(Path(old).stat().st_size==m['old_size'] and file_sha(old)==m['before'],'baseline mismatch')
    require(file_sha(blob)==m['blob_sha256'],'payload corrupted')
    with candidate(output,[old,blob,patch/'delta.json']) as temp,Path(old).open('rb') as a,blob.open('rb') as b:
        total=0
        with temp.open('wb') as f:
            for kind,offset,size in m['segments']:
                require(kind in ('copy','add') and offset>=0 and size>=0,'bad segment')
                source=a if kind=='copy' else b;limit=m['old_size'] if kind=='copy' else blob.stat().st_size
                require(offset+size<=limit and total+size<=m['new_size'],'delta range overflow')
                source.seek(offset);left=size
                while left:
                    chunk=source.read(min(left,1024*1024));require(chunk,'truncated segment');f.write(chunk);left-=len(chunk)
                total+=size
        require(total==m['new_size'] and file_sha(temp)==m['after'],'rebuilt hash mismatch')
    return dict(sha256=m['after'],bytes=m['new_size'],runtime_verified=False)
