#!/usr/bin/env python3
"""Create synthetic adapter fixtures, with no game assets or external downloads."""
import argparse
import json
from pathlib import Path
import struct


def make_xmb(strings):
    count=len(strings);keys=48+count*32;pool=keys+20;b=bytearray(pool)
    b[:4]=b'XMB\0';struct.pack_into('>8I',b,8,40,count*4+1,keys,5,0,0,pool,count)
    for i,text in enumerate(strings):
        at=48+i*32;b[at:at+8]=bytes.fromhex('0001000100000003');b[at+8:at+12]=bytes.fromhex('00020003');b[at+16:at+20]=bytes.fromhex('00030004');b[at+24:at+28]=bytes.fromhex('00040002')
        struct.pack_into('>I',b,at+12,i+1);struct.pack_into('>I',b,at+28,len(b)-pool);b.extend(text.encode()+b'\0')
    return bytes(b)


def make_arb(members):
    h=bytearray(2048);h[:6]=b'BfPk\xfe\xff';struct.pack_into('>HH',h,6,1,len(members));at=16;data=bytearray()
    for name,b in members.items():
        name=name.encode();rec=17+len(name);struct.pack_into('>IIIHH',h,at,len(data),len(b),0,rec,len(name));h[at+17:at+17+len(name)]=name;at+=rec;data.extend(b);data.extend(bytes(-len(data)%16))
    if at>2048:raise ValueError('demo index too large')
    return bytes(h+data)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True,type=Path);a=p.parse_args();a.output.mkdir()
    xmb=make_xmb(['弾薬を補給する。','Hello, [$name]!'])
    (a.output/'sample.xmb').write_bytes(xmb)
    (a.output/'sample.arb').write_bytes(make_arb({'game/language/demo.xmb':xmb,'game/untouched.bin':b'SYNTHETIC_UNCHANGED_MEMBER'}))
    (a.output/'glyphs.txt').write_text('补给弹药。你好，[$name]！',encoding='utf-8')
    print(json.dumps(dict(output=str(a.output),synthetic=True,runtime_verified=False)))

if __name__=='__main__':main()
