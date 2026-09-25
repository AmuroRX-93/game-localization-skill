"""Port of fixed-slot UI typesetting; explicit font and candidate output only.
Supports the inspected single-texture 128-byte GTF header variant, BC3 and linear ARGB.
"""
import struct
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from .common import require

def validate_gtf(b):
    require(len(b)>=128 and b[:4]==bytes.fromhex('01030000'),'unsupported GTF header')
    require(struct.unpack_from('>I',b,8)[0]==1,'only single-texture GTF supported')
    require(struct.unpack_from('>I',b,16)[0]==128,'only data offset 128 supported')
    w,h=struct.unpack_from('>HH',b,32)
    require(0<w<=8192 and 0<h<=8192 and (w&(w-1))==0 and (h&(h-1))==0,'power-of-two dimensions required')
    require(b[24] in (0x88,0xa5) and 1<=b[25]<=max(w,h).bit_length(),'unsupported GTF format/mips')
    require(b[26]==2 and b[27]==0 and struct.unpack_from('>H',b,36)[0]==1,'only 2D non-cube textures supported')
    return w,h

def encode_bc3(im):
    a = np.asarray(im, dtype=np.uint8)
    (h, w) = a.shape[:2]
    a = np.pad(a, ((0, max(4, h) - h), (0, max(4, w) - w), (0, 0)), mode='edge')
    (h, w) = a.shape[:2]
    block = a.reshape(h // 4, 4, w // 4, 4, 4).transpose(0, 2, 1, 3, 4).reshape(-1, 16, 4)
    alpha = block[:, :, 3].astype(np.int32)
    hi = alpha.max(1)
    lo = alpha.min(1)
    hi = np.maximum(hi, 1)
    lo = np.minimum(lo, hi - 1)
    pal = np.stack([hi, lo] + [((7 - i) * hi + i * lo) // 7 for i in range(1, 7)], axis=1)
    idx = np.abs(alpha[:, :, None] - pal[:, None, :]).argmin(2).astype(np.uint64)
    bits = np.sum(idx << np.arange(0, 48, 3, dtype=np.uint64), axis=1, dtype=np.uint64)
    out = np.zeros((len(block), 16), dtype=np.uint8)
    out[:, 0] = hi
    out[:, 1] = lo
    for i in range(6):
        out[:, 2 + i] = bits >> 8 * i & 255
    rgb = block[:, :, :3].astype(np.int32)
    cmax = rgb.max(1)
    cmin = rgb.min(1)

    def pack(c):
        return (c[:, 0] * 31 + 127) // 255 << 11 | (c[:, 1] * 63 + 127) // 255 << 5 | (c[:, 2] * 31 + 127) // 255
    p0 = pack(cmax)
    p1 = pack(cmin)

    def unpack(v):
        return np.stack([(v >> 11 & 31) * 255 // 31, (v >> 5 & 63) * 255 // 63, (v & 31) * 255 // 31], axis=1)
    c0 = unpack(p0)
    c1 = unpack(p1)
    cp = np.stack([c0, c1, (2 * c0 + c1) // 3, (c0 + 2 * c1) // 3], axis=1)
    ci = ((rgb[:, :, None, :] - cp[:, None, :, :]) ** 2).sum(3).argmin(2).astype(np.uint64)
    cb = np.sum(ci << np.arange(0, 32, 2, dtype=np.uint64), axis=1, dtype=np.uint64)
    out[:, 8] = p0 & 255
    out[:, 9] = p0 >> 8
    out[:, 10] = p1 & 255
    out[:, 11] = p1 >> 8
    for i in range(4):
        out[:, 12 + i] = cb >> 8 * i & 255
    return out.tobytes()

def typeset(original, labels, font_path, font_index=0):
    im = original.copy()
    dirty = Image.new('L', im.size)
    audit = []
    for label in labels:
        (x0, y0, x1, y1) = label['box']
        require(0 <= x0 < x1 <= im.width and 0 <= y0 < y1 <= im.height, (im.size, label))
        old = np.array(original.crop((x0, y0, x1, y1)))
        alpha = old[:, :, 3]
        (ys, xs) = np.where(alpha > 80)
        require(len(xs), label)
        target_height = min(y1 - y0 - 2, label.get('ink_height', max(12, int(ys.max() - ys.min() + 1))))
        size = target_height + 4
        while size > 4:
            font = ImageFont.truetype(str(font_path), size, index=font_index)
            bbox = font.getbbox(label['text'])
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            if tw <= x1 - x0 - 4 and th <= target_height:
                break
            size -= 1
        require(tw <= x1 - x0 - 4 and th <= y1 - y0 - 2, label)
        yy = int((ys.min() + ys.max() + 1 - th) / 2)
        xx = label.get('ink_left', 2) if label['align'] == 'left' else (x1 - x0 - tw) // 2
        require(0 <= xx and xx + tw <= x1 - x0 and 0 <= yy and yy + th <= y1 - y0, 'glyph would be clipped: '+str(label))
        glyph = Image.new('L', (x1 - x0, y1 - y0))
        ImageDraw.Draw(glyph).text((xx - bbox[0], yy - bbox[1]), label['text'], font=font, fill=255)
        core = old[alpha > 200, :3]
        color = tuple(label['color']) if 'color' in label else tuple(np.median(core, axis=0).astype(np.uint8)) if len(core) else (255, 255, 255)
        tile = Image.new('RGBA', glyph.size, color + (0,))
        tile.putalpha(glyph)
        if label.get('background') == 'interpolate':
            blend = np.linspace(0, 1, x1 - x0)[None, :, None]
            bg = np.rint(old[:, :1, :] * (1 - blend) + old[:, -1:, :] * blend).astype(np.uint8)
            tile = Image.alpha_composite(Image.fromarray(bg), tile)
        im.paste(tile, (x0, y0))
        ImageDraw.Draw(dirty).rectangle((x0, y0, x1 - 1, y1 - 1), fill=255)
        audit.append({**label, 'font_size': size, 'ink_size': [tw, th], 'color': list(map(int, color))})
    return (im, dirty, audit)

def rebuild_gtf(gtf, labels, font_path, font_index=0):
    validate_gtf(gtf)
    if gtf[24] == 165:
        (w, h) = struct.unpack_from('>HH', gtf, 32)
        levels = gtf[25]
        pitch = struct.unpack_from('>I', gtf, 40)[0]
        original = Image.frombytes('RGBA', (w, h), gtf[128:128 + pitch * h], 'raw', 'ARGB', pitch)
        (im, dirty, audit) = typeset(original, labels, font_path, font_index)
        out = bytearray(gtf)
        offset = 128
        changed = 0
        unchanged = 0
        for level in range(levels):
            ww = max(1, w >> level)
            hh = max(1, h >> level)
            length = pitch * hh
            require(pitch >= ww * 4 and offset + length <= len(out), 'unsupported texture constraint')
            mip = im if level == 0 else im.resize((ww, hh), Image.Resampling.LANCZOS)
            dm = dirty if level == 0 else dirty.resize((ww, hh), Image.Resampling.BOX)
            pixels = np.array(mip)[:, :, [3, 0, 1, 2]]
            mask = np.array(dm) > 0
            for y in range(hh):
                a = np.frombuffer(out, dtype=np.uint8, count=ww * 4, offset=offset + y * pitch).reshape(ww, 4)
                a[mask[y]] = pixels[y, mask[y]]
            changed += int(mask.sum())
            unchanged += ww * hh - int(mask.sum())
            offset += length
        require(out[:128] == gtf[:128] and out[offset:] == gtf[offset:] and (len(out) == len(gtf)), 'unsupported texture constraint')
        decoded = Image.frombytes('RGBA', (w, h), bytes(out[128:128 + pitch * h]), 'raw', 'ARGB', pitch)
        require(decoded.tobytes() == im.tobytes(), 'unsupported texture constraint')
        return (bytes(out), original, decoded, dict(labels=audit, mip_levels=levels, changed_pixels=changed, unchanged_pixels=unchanged, max_alpha_error=0))
    require(gtf[24] == 136, 'Expected DXT5 UI texture')
    (w, h) = struct.unpack_from('>HH', gtf, 32)
    levels = gtf[25]
    original = Image.frombytes('RGBA', (w, h), gtf[128:128 + w * h], 'bcn', (3, 'DXT5'))
    (im, dirty, audit) = typeset(original, labels, font_path, font_index)
    out = bytearray(gtf)
    offset = 128
    unchanged = 0
    changed = 0
    for level in range(levels):
        ww = max(1, w >> level)
        hh = max(1, h >> level)
        length = max(4, ww) * max(4, hh)
        require(offset + length <= len(gtf), 'unsupported texture constraint')
        mip = im if level == 0 else im.resize((ww, hh), Image.Resampling.LANCZOS)
        dm = dirty if level == 0 else dirty.resize((ww, hh), Image.Resampling.BOX)
        d = np.array(dm)
        d = np.pad(d, ((0, max(4, hh) - hh), (0, max(4, ww) - ww)))
        use = d.reshape(max(4, hh) // 4, 4, max(4, ww) // 4, 4).any(axis=(1, 3)).reshape(-1)
        packed = encode_bc3(mip)
        require(len(packed) == length, 'unsupported texture constraint')
        for (i, yes) in enumerate(use):
            at = offset + i * 16
            if yes:
                out[at:at + 16] = packed[i * 16:i * 16 + 16]
                changed += 1
            else:
                require(out[at:at + 16] == gtf[at:at + 16], 'unsupported texture constraint')
                unchanged += 1
        offset += length
    require(out[:128] == gtf[:128] and len(out) == len(gtf) and (out[offset:] == gtf[offset:]), 'unsupported texture constraint')
    decoded = Image.frombytes('RGBA', (w, h), bytes(out[128:128 + w * h]), 'bcn', (3, 'DXT5'))
    error = np.abs(np.array(decoded.getchannel('A')).astype(int) - np.array(im.getchannel('A')).astype(int))
    require(error.max() <= 37, int(error.max()))
    return (bytes(out), original, decoded, dict(labels=audit, mip_levels=levels, changed_blocks=changed, unchanged_blocks=unchanged, max_alpha_error=int(error.max())))
