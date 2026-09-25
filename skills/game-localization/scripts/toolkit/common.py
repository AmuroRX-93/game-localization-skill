"""Shared offline candidate I/O. No live installation or process control."""
import contextlib
import hashlib
import json
import os
from pathlib import Path
import tempfile


def sha(data):return hashlib.sha256(data).hexdigest()

def file_sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def require(ok,message):
    if not ok:raise ValueError(message)


def read_at(path,offset,size):
    require(offset>=0 and size>=0,'negative range')
    with Path(path).open('rb') as f:f.seek(offset);b=f.read(size)
    require(len(b)==size,'truncated input');return b


@contextlib.contextmanager
def candidate(path,inputs=()):
    path=Path(path).resolve()
    require(path not in [Path(p).resolve() for p in inputs],'output must differ from every input')
    require(not path.exists(),'output already exists; choose a new candidate path')
    require(path.parent.is_dir(),'output parent must exist')
    fd,temp=tempfile.mkstemp(prefix='.localization-',dir=path.parent);os.close(fd);temp=Path(temp)
    try:
        yield temp
        # Exclusive final creation: never replace an existing user file, including a raced one.
        with temp.open('rb') as source,path.open('xb') as target:
            try:
                import shutil
                shutil.copyfileobj(source,target,1024*1024);target.flush();os.fsync(target.fileno())
            except BaseException:
                target.close();path.unlink();raise
    finally:
        temp.unlink(missing_ok=True)


def write_json(path,value,inputs=()):
    with candidate(path,inputs) as temp:
        temp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
