"""Adapters for inspected BLJS10050 layouts, not generic XMB/FPK support.
Derived from the project's xmb_text and ARB/FPK/TEX resource workflows.
"""
import struct
from .common import require,read_at


def xmb_parse(b):
    require(len(b)>=48 and b[:4]==b'XMB\0','not supported XMB')
    start,nodes,keys,nkeys,_,_,pool,count=struct.unpack_from('>8I',b,8)
    require(start==40 and nkeys==5 and nodes==count*4+1,'unsupported XMB tree')
    require(keys==48+count*32 and pool==keys+nkeys*4 and pool<=len(b),'XMB table bounds')
    rows=[];last_end=0
    for i in range(count):
        p=48+i*32
        require(b[p:p+8]==bytes.fromhex('0001000100000003') and
                b[p+8:p+12]==bytes.fromhex('00020003') and
                b[p+16:p+20]==bytes.fromhex('00030004') and
                b[p+24:p+28]==bytes.fromhex('00040002'),'unsupported XMB node')
        key=struct.unpack_from('>I',b,p+12)[0];off=struct.unpack_from('>I',b,p+28)[0]
        require(off==0 if i==0 else off>=last_end,'XMB pool overlap or nonzero prefix')
        require(pool+off<len(b),'XMB string bounds')
        end=b.index(0,pool+off);last_end=end-pool+1
        rows.append(dict(id=f'{key:08x}',offset=off,source=b[pool+off:end].decode('utf-8')))
    require(len({r['id'] for r in rows})==count,'duplicate XMB IDs')
    for i,r in enumerate(rows):
        end=rows[i+1]['offset'] if i+1<len(rows) else len(b)-pool
        suffix=b[pool+r['offset']+len(r['source'].encode()):pool+end]
        require(suffix and not any(suffix),'unsupported nonzero XMB string padding')
    return pool,rows


def xmb_rebuild(b,translations):
    pool,rows=xmb_parse(b);ids={r['id'] for r in rows}
    require(not set(translations)-ids,'unknown translation IDs')
    out=bytearray(b[:pool]);data=bytearray()
    for i,r in enumerate(rows):
        end=rows[i+1]['offset'] if i+1<len(rows) else len(b)-pool
        suffix=b[pool+r['offset']+len(r['source'].encode()):pool+end]
        text=translations.get(r['id'],r['source'])
        require(isinstance(text,str) and '\0' not in text,'invalid translation/NUL')
        struct.pack_into('>I',out,48+i*32+28,len(data));data.extend(text.encode());data.extend(suffix)
    result=bytes(out+data);new=xmb_parse(result)[1]
    require({r['id']:r['source'] for r in new}=={r['id']:translations.get(r['id'],r['source']) for r in rows},'XMB roundtrip failed')
    return result


def container_index(path):
    length=path.stat().st_size;magic=read_at(path,0,4);entries=[]
    if magic==b'BfPk':
        h=read_at(path,0,16);require(h[:6]==b'BfPk\xfe\xff','unsupported ARB endian')
        base=struct.unpack_from('>H',h,6)[0]*2048;count=struct.unpack_from('>H',h,8)[0]
        require(16<=base<=min(length,16*1024*1024),'ARB index bound');h=read_at(path,0,base);at=16
        for _ in range(count):
            require(at+17<=base,'truncated ARB entry')
            off,size,_,rec,nm=struct.unpack_from('>IIIHH',h,at)
            require(rec>=17+nm and at+rec<=base,'bad ARB record')
            name=h[at+17:at+17+nm].decode('utf-8')
            entries.append(dict(name=name,offset=base+off,size=size,index=at));at+=rec
        fmt='suiten-arb'
    elif magic==b'FPK\0':
        h=read_at(path,0,16);count,start,base=struct.unpack_from('>III',h,4)
        require(16<=start and start+count*80<=base<=min(length,16*1024*1024),'FPK table bounds')
        h=read_at(path,0,base)
        for i in range(count):
            at=start+i*80;raw=h[at:at+64];require(b'\0' in raw,'FPK unterminated name')
            name=raw.split(b'\0')[0].decode();off,size=struct.unpack_from('>II',h,at+64)
            entries.append(dict(name=name,offset=base+off,size=size,index=at+64))
        fmt='suiten-fpk'
    elif magic==b'TEX ':
        h=read_at(path,0,16);count=struct.unpack_from('>I',h,8)[0]
        require(0<count<=100000 and 16+8*count<=length,'TEX table bounds')
        h=read_at(path,0,16+8*count);offs=struct.unpack_from('>'+str(count)+'I',h,16);sizes=struct.unpack_from('>'+str(count)+'I',h,16+4*count)
        base=min(offs);require(16+8*count<=base<=min(length,16*1024*1024),'TEX names bounds')
        raw=read_at(path,16+8*count,base-16-8*count);names=raw.split(b'\0')
        require(len(names)>count,'TEX names truncated')
        for i in range(count):entries.append(dict(name=names[i].decode(),offset=offs[i],size=sizes[i],index=16+4*i))
        fmt='suiten-tex'
    else:raise ValueError('unknown container magic; no guessed adapter')
    require(len({e['name'] for e in entries})==len(entries),'duplicate member names')
    ordered=sorted(entries,key=lambda e:e['offset'])
    for i,e in enumerate(ordered):
        end=ordered[i+1]['offset'] if i+1<len(ordered) else length
        require(e['name'] and base<=e['offset'] and e['offset']+e['size']<=end,'overlap or out-of-bounds member')
    return dict(format=fmt,base=base,entries=entries)
