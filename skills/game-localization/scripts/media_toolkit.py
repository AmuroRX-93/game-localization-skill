#!/usr/bin/env python3
"""Optional local media tools. Candidates only; no game writes or model downloads."""
import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import wave


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def run(argv, cwd=None):
    p = subprocess.run([str(x) for x in argv], cwd=cwd, capture_output=True, text=True)
    if p.returncode:
        raise ValueError(p.stderr[-4000:] or 'External tool failed')
    return p.stdout


def new_path(path):
    p = Path(path).absolute()
    if os.path.lexists(p):
        raise ValueError('Output already exists: ' + str(p))
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def publish(staged, output):
    # Exclusive create works on filesystems without hardlink support too.
    with open(output, 'xb') as dst:
        try:
            with open(staged, 'rb') as src:
                shutil.copyfileobj(src, dst)
        except BaseException:
            dst.close()
            Path(output).unlink()
            raise


def write_text(path, text):
    output = new_path(path)
    with tempfile.TemporaryDirectory(prefix='media-', dir=output.parent) as tmp:
        staged = Path(tmp) / 'text'
        staged.write_text(text, encoding='utf-8')
        publish(staged, output)


def probe(path, ffprobe='ffprobe'):
    return json.loads(run([ffprobe, '-v', 'error', '-show_format', '-show_streams',
                           '-of', 'json', Path(path).resolve()]))


def finite(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def validate(data, field='text', duration=None, max_cps=15, max_line=24):
    if not isinstance(data, dict):
        raise ValueError('Subtitle document must be an object')
    cues = data.get('cues')
    if not isinstance(cues, list):
        raise ValueError('cues must be an array')
    ids, previous, active_end, issues = set(), -1, -1, []
    for c in cues:
        if not isinstance(c, dict) or not isinstance(c.get('id'), str) or not c['id'] or c['id'] in ids:
            raise ValueError('Missing/duplicate cue id')
        ids.add(c['id'])
        a, b = c.get('start'), c.get('end')
        if not finite(a) or not finite(b) or a < 0 or b <= a:
            raise ValueError('Invalid cue times: ' + c['id'])
        t = c.get(field)
        if not isinstance(t, str) or any(ord(x) < 32 and x not in '\n\t' for x in t):
            raise ValueError('Invalid cue text: ' + c['id'])
        reasons = []
        if a < previous: reasons.append('out_of_order')
        if a < active_end: reasons.append('overlap')
        if duration is not None and b > duration: reasons.append('past_media_end')
        if not t.strip(): reasons.append('empty_text')
        if c.get('reviewed') is not True: reasons.append('unreviewed')
        if len(t.replace('\n', '').replace(' ', '')) / (b-a) > max_cps: reasons.append('reading_speed')
        if any(len(line) > max_line for line in t.split('\n')): reasons.append('long_line')
        if len(t.split('\n')) > 2: reasons.append('more_than_two_lines')
        if reasons: issues.append({'id': c['id'], 'issues': reasons})
        previous, active_end = a, max(active_end, b)
    if not cues: issues.append({'id': None, 'issues': ['no_cues']})
    return issues


def stamp(seconds, ass=False):
    scale = 100 if ass else 1000
    n = round(seconds * scale)
    s, frac = divmod(n, scale)
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    return (f'{h}:{m:02}:{s:02}.{frac:02}' if ass else f'{h:02}:{m:02}:{s:02},{frac:03}')


def export_subs(data, field, kind, font='sans-serif', size=36, width=1280, height=720):
    validate(data, field)
    cues = data['cues']
    if not cues or any(not c[field].strip() for c in cues):
        raise ValueError('Cannot export empty cues/text; select --field source for ASR review')
    if any(c['start'] < cues[i-1]['start'] for i,c in enumerate(cues) if i):
        raise ValueError('Cues must be in chronological order')
    if any(stamp(c['start'], kind == 'ass') == stamp(c['end'], kind == 'ass') for c in cues):
        raise ValueError('Cue duration is below subtitle timestamp precision')
    if kind == 'srt':
        if any(re.search(r'\n[ \t]*\n', c[field]) for c in cues):
            raise ValueError('SRT text cannot contain blank separator lines')
        return '\n'.join(f'{i}\n{stamp(c["start"])} --> {stamp(c["end"])}\n{c[field]}\n' for i,c in enumerate(cues,1))
    if re.search(r'[,\r\n]', font) or size <= 0 or width <= 0 or height <= 0:
        raise ValueError('Invalid ASS style')
    header = f'''[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font},{size},&H00FFFFFF,&H00FFFFFF,&H00202020,&H80000000,0,0,0,0,100,100,0,0,1,1.5,0,2,40,40,32,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
    # Do not interpret translators' literal braces/backslashes as ASS override code.
    if any(any(x in c[field] for x in ('{', '}', '\\')) for c in cues):
        raise ValueError('ASS plain-text export rejects braces/backslashes; review or use SRT')
    return header + '\n'.join('Dialogue: 0,' + stamp(c['start'],True) + ',' + stamp(c['end'],True) +
                              ',Default,,0,0,0,,' + c[field].replace('\n', r'\N') for c in cues) + '\n'


def transcribe(audio, model_dir, language, offset=0, threads=4):
    model_dir = Path(model_dir).resolve()
    required = ['model.bin', 'config.json', 'tokenizer.json', 'preprocessor_config.json']
    if any(not (model_dir / f).is_file() for f in required):
        raise ValueError('Provide a complete local faster-whisper model directory: ' + ', '.join(required))
    if not finite(offset) or offset < 0 or threads < 1:
        raise ValueError('offset must be >= 0; threads must be >= 1')
    with wave.open(str(audio), 'rb') as w:
        if (w.getnchannels(),w.getframerate(),w.getsampwidth()) != (1,16000,2):
            raise ValueError('ASR input must be mono 16 kHz PCM16 WAV; use extract')
    # Prevent fallback tokenizers/models from using the network.
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    try:
        from faster_whisper import WhisperModel
    except ImportError as e:
        raise ValueError('Install optional faster-whisper in a separate environment first') from e
    model = WhisperModel(str(model_dir), device='cpu', compute_type='int8',
                         cpu_threads=threads, local_files_only=True)
    segments, info = model.transcribe(str(audio), language=language, task='transcribe',
                                      beam_size=5, vad_filter=True, word_timestamps=True,
                                      condition_on_previous_text=False)
    cues = []
    for i,s in enumerate(segments,1):
        cues.append({'id': f'asr-{i:06}', 'start': s.start + offset, 'end': s.end + offset,
                     'source': s.text.strip(), 'text': '', 'reviewed': False,
                     'avg_logprob': s.avg_logprob, 'no_speech_prob': s.no_speech_prob,
                     'words': [{'start': w.start+offset, 'end': w.end+offset,
                                'word': w.word, 'probability': w.probability} for w in (s.words or [])]})
    data = {'schema': 'localization-cues-v1', 'source_sha256': sha(audio),
            'model_sha256': {f: sha(model_dir/f) for f in required},
            'language': info.language, 'offset_seconds': offset,
            'engine': 'faster-whisper/cpu/int8', 'status': 'asr_candidate', 'cues': cues}
    validate(data, 'source')
    return data


def ffmpeg_output(ffmpeg, argv, output):
    output = new_path(output)
    with tempfile.TemporaryDirectory(prefix='media-', dir=output.parent) as tmp:
        staged = Path(tmp)/('result'+output.suffix)
        run([ffmpeg, '-hide_banner', '-loglevel', 'error', '-nostdin', '-n'] + argv + [staged])
        publish(staged, output)


def has_filter(ffmpeg, name):
    return bool(re.search(r'^\s*[TSC.]{2,3}\s+' + re.escape(name) + r'\s',
                          run([ffmpeg, '-hide_banner', '-filters']), re.M))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--ffmpeg', default='ffmpeg'); p.add_argument('--ffprobe', default='ffprobe')
    sub = p.add_subparsers(dest='cmd', required=True)
    sub.add_parser('doctor')
    q=sub.add_parser('probe'); q.add_argument('input')
    q=sub.add_parser('extract'); q.add_argument('input'); q.add_argument('output')
    q.add_argument('--audio', type=int, required=True, help='Zero-based audio stream ordinal')
    q.add_argument('--channel', type=int, help='Zero-based channel; otherwise downmix')
    q=sub.add_parser('transcribe'); q.add_argument('input'); q.add_argument('output')
    q.add_argument('--model-dir', required=True); q.add_argument('--language', required=True)
    q.add_argument('--offset', type=float, default=0); q.add_argument('--threads', type=int, default=4)
    for name in ('check','export'):
        q=sub.add_parser(name); q.add_argument('input'); q.add_argument('--field', choices=['text','source'], default='text')
        if name == 'check':
            q.add_argument('--duration',type=float); q.add_argument('--max-cps',type=float,default=15); q.add_argument('--max-line',type=int,default=24)
        else:
            q.add_argument('output'); q.add_argument('--format',choices=['srt','ass'],required=True)
            q.add_argument('--font',default='sans-serif'); q.add_argument('--size',type=int,default=36)
            q.add_argument('--width',type=int,default=1280); q.add_argument('--height',type=int,default=720)
    q=sub.add_parser('burn-preview'); q.add_argument('input'); q.add_argument('subtitles'); q.add_argument('output')
    q=sub.add_parser('delogo-preview'); q.add_argument('input'); q.add_argument('output')
    q.add_argument('--box', type=int,nargs=4,required=True,metavar=('X','Y','W','H'))
    q.add_argument('--start',type=float,required=True); q.add_argument('--end',type=float,required=True)
    a=p.parse_args(argv)
    if a.cmd == 'doctor':
        found=shutil.which(a.ffmpeg)
        print(json.dumps({'ffmpeg': found, 'ffprobe':shutil.which(a.ffprobe),
                          'subtitles_filter':has_filter(a.ffmpeg,'subtitles') if found else False,
                          'delogo_filter':has_filter(a.ffmpeg,'delogo') if found else False,
                          'faster_whisper':importlib.util.find_spec('faster_whisper') is not None,
                          'model_bundled':False},ensure_ascii=False)); return 0
    if a.cmd == 'probe':
        print(json.dumps(probe(a.input,a.ffprobe),ensure_ascii=False,indent=2)); return 0
    if a.cmd == 'extract':
        if Path(a.output).suffix.lower() != '.wav': raise ValueError('extract output must be .wav')
        streams=[s for s in probe(a.input,a.ffprobe)['streams'] if s['codec_type']=='audio']
        if not 0 <= a.audio < len(streams): raise ValueError('Audio stream ordinal out of range')
        opts=[]
        if a.channel is not None:
            if not 0 <= a.channel < streams[a.audio]['channels']: raise ValueError('Channel out of range')
            opts=['-af',f'pan=mono|c0=c{a.channel}']
        ffmpeg_output(a.ffmpeg,['-i',Path(a.input).resolve(),'-map',f'0:a:{a.audio}', '-vn']+opts+
                      ['-ac','1','-ar','16000','-c:a','pcm_s16le'],a.output); return 0
    if a.cmd == 'transcribe':
        new_path(a.output)
        write_text(a.output,json.dumps(transcribe(a.input,a.model_dir,a.language,a.offset,a.threads),ensure_ascii=False,indent=2)+'\n'); return 0
    if a.cmd == 'check':
        if any(not finite(v) or v <= 0 for v in (a.max_cps,a.max_line)) or (a.duration is not None and (not finite(a.duration) or a.duration < 0)):
            raise ValueError('Invalid check thresholds')
        issues=validate(read_json(a.input),a.field,a.duration,a.max_cps,a.max_line)
        print(json.dumps({'issues':issues,'language_verified':False},ensure_ascii=False,indent=2)); return int(bool(issues))
    if a.cmd == 'export':
        if Path(a.output).suffix.lower() != '.'+a.format: raise ValueError('Output suffix must match format')
        write_text(a.output,export_subs(read_json(a.input),a.field,a.format,a.font,a.size,a.width,a.height)); return 0
    if Path(a.output).suffix.lower() != '.mp4': raise ValueError('Preview output must be .mp4')
    if a.cmd == 'burn-preview':
        if not has_filter(a.ffmpeg,'subtitles'): raise ValueError('FFmpeg needs the subtitles filter (libass)')
        suffix=Path(a.subtitles).suffix.lower()
        if suffix not in ('.ass','.srt'): raise ValueError('Use a trusted .ass or .srt subtitle file')
        # Safe temporary basename avoids FFmpeg filter escaping of user paths.
        output=new_path(a.output)
        with tempfile.TemporaryDirectory(prefix='media-',dir=output.parent) as tmp:
            shutil.copyfile(a.subtitles,Path(tmp)/('captions'+suffix))
            staged=Path(tmp)/'preview.mp4'
            run([a.ffmpeg,'-hide_banner','-loglevel','error','-nostdin','-n','-i',Path(a.input).resolve(),
                 '-map','0:v:0','-map','0:a?','-vf','subtitles=filename=captions'+suffix,
                 '-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-c:a','aac','-movflags','+faststart',staged],cwd=tmp)
            publish(staged,output)
        return 0
    if not has_filter(a.ffmpeg,'delogo'): raise ValueError('FFmpeg needs the delogo filter')
    video=next(s for s in probe(a.input,a.ffprobe)['streams'] if s['codec_type']=='video')
    x,y,w,h=a.box
    if x < 1 or y < 1 or w < 2 or h < 2 or x+w >= video['width'] or y+h >= video['height']:
        raise ValueError('delogo rectangle must leave a surrounding pixel border')
    if not finite(a.start) or not finite(a.end) or not 0 <= a.start < a.end: raise ValueError('Invalid time interval')
    filt=f"delogo=x={x}:y={y}:w={w}:h={h}:enable='gte(t,{a.start})*lt(t,{a.end})'"
    ffmpeg_output(a.ffmpeg,['-i',Path(a.input).resolve(),'-map','0:v:0','-map','0:a?',
                  '-vf',filt,'-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-c:a','aac'],a.output)
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, OSError, KeyError, StopIteration, wave.Error) as e:
        print('ERROR: '+str(e),file=sys.stderr); sys.exit(2)
