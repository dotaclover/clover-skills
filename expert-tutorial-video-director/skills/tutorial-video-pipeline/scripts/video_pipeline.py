#!/usr/bin/env python3
"""配置驱动、保留源文件的视频二次加工（1.0.0 开发稿）。"""
import argparse
import asyncio
import json
import math
import os
import re
import shutil
import subprocess
import sys
from fractions import Fraction
from pathlib import Path


def binary(value, name):
    found = shutil.which(value or name)
    if not found and value and Path(value).is_file():
        found = str(Path(value).resolve())
    if not found:
        raise ValueError(f'找不到 {name}；指定 --{name}')
    return found


def execute(args):
    restricted = []
    for arg in args:
        if arg == '-i':
            restricted.extend(['-protocol_whitelist', 'file,pipe'])
        restricted.append(arg)
    subprocess.run(restricted, check=True, stdin=subprocess.DEVNULL, shell=False)


def probe(path, fp):
    return json.loads(subprocess.check_output([
        fp, '-v', 'error', '-protocol_whitelist', 'file,pipe',
        '-show_format', '-show_streams', '-of', 'json', str(path)
    ], stdin=subprocess.DEVNULL, shell=False))


def finite(value, name, minimum=0):
    value = float(value)
    if not math.isfinite(value) or value < minimum:
        raise ValueError(f'{name} 无效: {value}')
    return value


def local(value, base):
    p = Path(value).expanduser()
    return (p if p.is_absolute() else base / p).resolve(strict=True)


def video_info(path, fp):
    info = probe(path, fp)
    videos = [s for s in info['streams'] if s['codec_type'] == 'video']
    if not videos:
        raise ValueError('源文件没有视频轨')
    v = videos[0]
    rotations = [v.get('tags', {}).get('rotate', 0)] + [s.get('rotation', 0) for s in v.get('side_data_list', [])]
    if any(float(x) % 360 for x in rotations):
        raise ValueError('旋转源被拒绝：先另存方向规范化副本，再配置源坐标遮挡')
    sar = Fraction(v.get('sample_aspect_ratio', '1:1').replace(':', '/') if v.get('sample_aspect_ratio') not in (None, 'N/A', '0:1') else '1')
    rate = v.get('avg_frame_rate', '0/0')
    if rate == '0/0':
        rate = v.get('r_frame_rate', '30/1')
    fps = float(Fraction(rate))
    if not 1 <= fps <= 120:
        raise ValueError('源帧率不在1..120；先规范化素材')
    return {'path': path, 'width': int(v['width']), 'height': int(v['height']),
            'sar': float(sar), 'fps': fps, 'rate': rate,
            'duration': finite(info['format']['duration'], '源时长', 0.001),
            'audio': any(s['codec_type'] == 'audio' for s in info['streams'])}


def stamp(seconds, ass=False):
    unit = 100 if ass else 1000
    n = round(seconds * unit)
    return (f'{n // (3600 * unit):02}:{n // (60 * unit) % 60:02}:{n // unit % 60:02}'
            + (f'.{n % unit:02}' if ass else f',{n % unit:03}'))


def ass_file(path, rows, width, height, font, size):
    text = f'''[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 0
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font},{size},&H00FFFFFF,&H00FFFFFF,&H00151515,&H80000000,0,0,0,0,100,100,0,0,1,2,1,2,16,16,16,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
    for a, b, t in rows:
        t = str(t).replace('\\', '/').replace('{', '(').replace('}', ')').replace('\n', ' ')
        text += f'Dialogue: 0,{stamp(a, True)},{stamp(b, True)},Default,,0,0,0,,{t}\n'
    path.write_text(text, encoding='utf-8-sig')


def tempo(speed):
    filters = []
    while speed > 2:
        filters.append('atempo=2'); speed /= 2
    while speed < 0.5:
        filters.append('atempo=0.5'); speed *= 2
    return ','.join(filters + [f'atempo={speed:.9f}'])


async def tts(text, voice, rate, path):
    import edge_tts
    await edge_tts.Communicate(text, voice, rate=rate).save(str(path))


def prepare(config, base, fp, allow_tts):
    allowed = {'source', 'encoding_mode', 'crf', 'target_mb', 'width', 'height', 'fps', 'resize_mode', 'audio_mode', 'original_volume', 'voice_volume', 'subtitle_mode', 'font', 'font_size', 'voice', 'rate', 'segments'}
    if set(config) - allowed:
        raise ValueError(f'未知全局字段: {sorted(set(config)-allowed)}')
    finite(config.get('font_size', 16), 'font_size', 1)
    encoding = config.get('encoding_mode', 'quality')
    if encoding not in ('quality', 'size'):
        raise ValueError('encoding_mode 必须为 quality/size')
    if encoding == 'quality' and 'target_mb' in config:
        raise ValueError('target_mb 只能在显式 size 模式设置，避免静默忽略')
    if encoding == 'size':
        finite(config['target_mb'], 'target_mb', 0.01)
    crf = finite(config.get('crf', 20), 'crf')
    if crf > 51:
        raise ValueError('crf 必须在0..51')
    mode = config.get('audio_mode', 'original')
    if mode not in ('original', 'replace', 'mix', 'mute'):
        raise ValueError('audio_mode 必须为 original/replace/mix/mute')
    subtitle_mode = config.get('subtitle_mode', 'none')
    if subtitle_mode not in ('none', 'sidecar', 'burn'):
        raise ValueError('subtitle_mode 必须为 none/sidecar/burn')
    font = config.get('font', 'Microsoft YaHei')
    if not re.fullmatch(r'[\w .\-\u4e00-\u9fff]+', font):
        raise ValueError('字体名含不支持字符')
    for key in ('original_volume', 'voice_volume'):
        finite(config.get(key, 1), key)
    items = config.get('segments')
    if items is None:
        items = [{}]
    if not isinstance(items, list) or not items:
        raise ValueError('segments 须为非空数组；省略代表完整 source')
    prepared = []
    cache = {}
    for item in items:
        allowed_segment = {'source', 'start', 'end', 'speed', 'duration', 'voice_file', 'narration', 'subtitles', 'subtitle_text', 'masks'}
        if set(item) - allowed_segment:
            raise ValueError(f'未知片段字段: {sorted(set(item)-allowed_segment)}')
        source_value = item.get('source', config.get('source'))
        if not isinstance(source_value, str) or not source_value:
            raise ValueError('每段必须有 source 或继承全局 source')
        p = local(source_value, base)
        if p not in cache:
            cache[p] = video_info(p, fp)
        src = cache[p]
        a = finite(item.get('start', 0), 'start')
        b = finite(item.get('end', src['duration']), 'end')
        if not a < b <= src['duration'] + 0.001:
            raise ValueError('片段范围越界')
        if 'duration' in item and 'speed' in item:
            raise ValueError('duration 与 speed 不能同时设置')
        duration = finite(item['duration'], 'duration', 0.05) if 'duration' in item else (b-a)/finite(item.get('speed', 1), 'speed', 0.05)
        if item.get('voice_file') and item.get('narration'):
            raise ValueError('voice_file/narration 互斥')
        has_voice = bool(item.get('voice_file') or item.get('narration'))
        if has_voice and mode not in ('replace', 'mix'):
            raise ValueError('配音只能在 replace/mix 模式启用')
        if mode in ('replace', 'mix') and not has_voice:
            raise ValueError('replace/mix 每段须提供 voice_file 或 narration')
        if item.get('narration') and not allow_tts:
            raise ValueError('TTS需要显式 --allow-tts-network 授权，旁白将发送到在线服务')
        voice = local(item['voice_file'], base) if item.get('voice_file') else None
        if voice and not any(s['codec_type'] == 'audio' for s in probe(voice, fp)['streams']):
            raise ValueError('voice_file 没有音轨')
        masks = []
        for mask in item.get('masks', []):
            unit = mask.get('unit', 'pixels')
            if unit not in ('pixels', 'normalized'):
                raise ValueError('mask unit 必须为 pixels/normalized')
            vals = [finite(mask[k], k, 0.000001 if k in ('w', 'h') else 0) for k in ('x', 'y', 'w', 'h')]
            x, y, w, h = vals
            if x+w > (1 if unit == 'normalized' else src['width']) or y+h > (1 if unit == 'normalized' else src['height']):
                raise ValueError('遮挡矩形越界')
            if unit == 'normalized':
                x, y, w, h = x*src['width'], y*src['height'], w*src['width'], h*src['height']
            masks.append((int(x), int(y), max(1, math.ceil(w)), max(1, math.ceil(h))))
        rows = []
        timing = 'none'
        if subtitle_mode != 'none':
            if item.get('subtitles'):
                timing = 'explicit'
                for sub in item['subtitles']:
                    sa = finite(sub['start'], '字幕 start'); sb = finite(sub['end'], '字幕 end')
                    if not sa < sb <= duration:
                        raise ValueError('字幕范围超过输出片段')
                    rows.append((sa, sb, str(sub['text'])))
            elif item.get('subtitle_text'):
                timing = 'approximate'
                parts = [s.strip() for s in re.split('[，。！？；\n]', item['subtitle_text']) if s.strip()]
                weight = sum(map(len, parts)); cursor = 0
                for part in parts:
                    span = duration*len(part)/weight
                    rows.append((cursor, cursor+span, part)); cursor += span
        prepared.append({'item': item, 'src': src, 'a': a, 'b': b, 'duration': duration,
                         'voice': voice, 'masks': masks, 'rows': rows, 'timing': timing})
    if any(s['item'].get('narration') for s in prepared):
        import edge_tts
    src = prepared[0]['src']
    if ('width' in config) != ('height' in config):
        raise ValueError('显式画布须同时指定 width/height')
    width = int(config.get('width', src['width']))
    height = int(config.get('height', src['height']))
    if any(n < 2 or n > 7680 or n % 2 for n in (width, height)):
        raise ValueError('画布须为2..7680偶数；奇数源请明确配置偶数画布')
    fps = finite(config.get('fps', src['fps']), 'fps', 1)
    if fps > 120:
        raise ValueError('fps 不能超过120')
    if config.get('resize_mode', 'contain') not in ('contain', 'crop'):
        raise ValueError('resize_mode 必须为 contain/crop')
    return prepared, width, height, fps


def render(args, ff, fp):
    config_path = Path(args.config).resolve(strict=True)
    config = json.loads(config_path.read_text(encoding='utf-8-sig'))
    output = Path(args.output).resolve()
    if output.exists():
        raise ValueError('输出目录已存在，no overwrite：指定全新目录')
    segments, width, height, fps = prepare(config, config_path.parent, fp, args.allow_tts_network)
    output.mkdir(parents=True, exist_ok=False)
    work = output/'work'; work.mkdir()
    mode = config.get('audio_mode', 'original')
    submode = config.get('subtitle_mode', 'none')
    size = finite(config.get('font_size', max(16, width*0.025)), 'font_size', 1)
    rows = []; timeline = []; cursor = 0
    for i, s in enumerate(segments):
        src = s['src']; d = s['duration']; item = s['item']
        voice = s['voice']
        if item.get('narration'):
            voice = work/f'voice_{i:03}.mp3'
            asyncio.run(tts(item['narration'], config.get('voice', 'zh-TW-HsiaoChenNeural'), config.get('rate', '+0%'), voice))
        vf = f"setpts={d/(s['b']-s['a']):.9f}*(PTS-STARTPTS)"
        for x, y, w, h in s['masks']:
            vf += f',drawbox=x={x}:y={y}:w={w}:h={h}:color=0xCCCCCC:t=fill'
        # 先应用源显示宽高比，再统一方形像素；contain 不放大实际画面。
        dw = src['width']*src['sar']; dh = src['height']
        scale = min(width/dw, height/dh, 1) if config.get('resize_mode', 'contain') == 'contain' else max(width/dw, height/dh)
        rw = max(2, math.floor(dw*scale/2)*2); rh = max(2, math.floor(dh*scale/2)*2)
        if config.get('resize_mode', 'contain') == 'crop':
            rw = max(width, math.ceil(dw*scale/2)*2); rh = max(height, math.ceil(dh*scale/2)*2)
        vf += f',scale={rw}:{rh},setsar=1'
        vf += f',pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black' if config.get('resize_mode', 'contain') == 'contain' else f',crop={width}:{height}'
        vf += f',fps={fps:.9f},format=yuv420p'
        if submode == 'burn' and s['rows']:
            ass = work/f'caption_{i:03}.ass'
            ass_file(ass, s['rows'], width, height, config.get('font', 'Microsoft YaHei'), size)
            # 固定生成的安全相对文件名，避免 Windows 盘符及配置路径的滤镜转义。
            vf += f",ass=filename=caption_{i:03}.ass"
        cmd = [ff, '-v', 'warning', '-nostdin', '-n', '-ss', str(s['a']), '-t', str(s['b']-s['a']), '-i', str(src['path'])]
        if voice:
            cmd += ['-i', str(voice)]
        graph = [f'[0:v]{vf}[v]']
        if mode != 'mute':
            orig = src['audio'] and mode in ('original', 'mix')
            if orig:
                graph.append(f"[0:a:0]{tempo((s['b']-s['a'])/d)},volume={float(config.get('original_volume', 1))},aresample=48000,aformat=channel_layouts=stereo,apad,atrim=duration={d},asetpts=PTS-STARTPTS[o]")
            if voice:
                graph.append(f"[1:a:0]volume={float(config.get('voice_volume', 1))},aresample=48000,aformat=channel_layouts=stereo,apad,atrim=duration={d},asetpts=PTS-STARTPTS[n]")
            if orig and voice:
                graph.append('[o][n]amix=inputs=2:duration=longest:normalize=0,alimiter=limit=0.95:latency=1[a]')
            elif orig or voice:
                graph.append(f"[{'o' if orig else 'n'}]anull[a]")
            else:
                graph.append(f'anullsrc=r=48000:cl=stereo,atrim=duration={d}[a]')
        cmd += ['-filter_complex', ';'.join(graph), '-map', '[v]']
        if mode != 'mute':
            cmd += ['-map', '[a]', '-c:a', 'aac', '-b:a', '128k', '-ar', '48000', '-ac', '2']
        cmd += ['-t', str(d), '-c:v', 'libx264', '-preset', 'fast', '-crf', str(config.get('crf', 20)), str(work/f'clip_{i:03}.mp4')]
        # libass 相对文件名仅在此工作目录解析，不改变主进程当前目录。
        restricted = []
        for arg in cmd:
            if arg == '-i':
                restricted += ['-protocol_whitelist', 'file,pipe']
            restricted.append(arg)
        subprocess.run(restricted, check=True, cwd=work, stdin=subprocess.DEVNULL, shell=False)
        clip_info = probe(work/f'clip_{i:03}.mp4', fp)
        actual = float(next(track['duration'] for track in clip_info['streams'] if track['codec_type'] == 'video'))
        rows += [(cursor+a, cursor+b, t) for a, b, t in s['rows']]
        timeline.append({'source': str(src['path']), 'source_start': s['a'], 'source_end': s['b'], 'output_start': cursor, 'duration': actual, 'subtitle_timing': s['timing']})
        cursor += actual
    listing = work/'concat.txt'
    listing.write_text(''.join(f"file 'clip_{i:03}.mp4'\n" for i in range(len(segments))), encoding='utf-8')
    master = work/'master.mp4'
    execute([ff, '-v', 'warning', '-nostdin', '-n', '-f', 'concat', '-safe', '1', '-i', str(listing), '-c', 'copy', '-movflags', '+faststart', str(master)])
    final = output/'final.mp4'
    encoding = config.get('encoding_mode', 'quality')
    target = None
    if encoding == 'quality':
        shutil.copyfile(master, final)
    else:
        target = float(config['target_mb'])*1_000_000
        duration = float(probe(master, fp)['format']['duration'])
        bitrate = int(target*0.95*8/duration - (128000 if mode != 'mute' else 0) - 16000)
        achieved = False
        for attempt in range(3):
            if bitrate < 50000:
                raise ValueError('目标体积太小；增大 target_mb 或缩短视频')
            candidate = work/f'encoded_{attempt}.mp4'
            base = [ff, '-v', 'warning', '-nostdin', '-n', '-i', str(master), '-map', '0:v:0', '-c:v', 'libx264', '-preset', 'slow', '-b:v', str(bitrate), '-passlogfile', str(work/f'pass_{attempt}')]
            execute(base + ['-pass', '1', '-an', '-f', 'null', os.devnull])
            audio = ['-map', '0:a:0', '-c:a', 'copy'] if mode != 'mute' else ['-an']
            execute(base + ['-pass', '2'] + audio + ['-movflags', '+faststart', str(candidate)])
            if candidate.stat().st_size <= target:
                achieved = True; break
            bitrate = int(bitrate*0.85)
        if not achieved:
            raise ValueError('三次双遍仍未达上限；不报告成功，保留缓存')
        shutil.copyfile(candidate, final)
    if submode != 'none':
        (output/'subtitles.srt').write_text('\n'.join(f'{i+1}\n{stamp(a)} --> {stamp(b)}\n{t}\n' for i, (a,b,t) in enumerate(rows)), encoding='utf-8-sig')
    execute([ff, '-v', 'error', '-nostdin', '-i', str(final), '-f', 'null', os.devnull])
    info = probe(final, fp)
    v = next(s for s in info['streams'] if s['codec_type'] == 'video')
    report = {'encoding_mode': encoding, 'target_enabled': encoding == 'size', 'target_mb': config.get('target_mb'),
              'target_met': final.stat().st_size <= target if target else None,
              'bytes': final.stat().st_size, 'duration': float(info['format']['duration']),
              'output': {'width': v['width'], 'height': v['height'], 'fps': v['avg_frame_rate'], 'sar': v.get('sample_aspect_ratio'), 'video_codec': v['codec_name'], 'audio_mode': mode, 'audio_codec': next((s['codec_name'] for s in info['streams'] if s['codec_type'] == 'audio'), None)},
              'resize_mode': config.get('resize_mode', 'contain'), 'subtitle_mode': submode,
              'subtitle_segments': len(rows), 'subtitle_timing': sorted(set(s['timing'] for s in segments)),
              'decode_validation': 'passed', 'source_modified': False,
              'source_modified_note': '仅说明脚本未写入源路径；不是前后哈希或完整性验证',
              'audio_note': '原音可能变速/重采样/AAC重编码；mix为固定音量amix加限幅，无自动ducking；配音尾部裁切或补静音',
              'encoding_note': '质量模式片段编码后无损拼接；size额外双遍编码；多段时间存在帧量化及AAC边界偏差'}
    (output/'timeline.json').write_text(json.dumps(timeline, ensure_ascii=False, indent=2), encoding='utf-8')
    (output/'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--ffmpeg'); p.add_argument('--ffprobe')
    sub = p.add_subparsers(dest='command', required=True)
    a = sub.add_parser('probe'); a.add_argument('source')
    a = sub.add_parser('frames'); a.add_argument('source'); a.add_argument('--output', required=True); a.add_argument('--interval', type=float, default=2)
    a = sub.add_parser('render'); a.add_argument('--config', required=True); a.add_argument('--output', required=True); a.add_argument('--allow-tts-network', action='store_true')
    args = p.parse_args()
    ff, fp = binary(args.ffmpeg, 'ffmpeg'), binary(args.ffprobe, 'ffprobe')
    if args.command == 'probe':
        print(json.dumps(probe(Path(args.source).resolve(strict=True), fp), ensure_ascii=False, indent=2))
    elif args.command == 'frames':
        source = Path(args.source).resolve(strict=True)
        info = video_info(source, fp)
        interval = finite(args.interval, 'interval', 0.1)
        if info['duration']/interval > 500:
            raise ValueError('超过500帧，请增大interval')
        output = Path(args.output).resolve(); output.mkdir(parents=True, exist_ok=False)
        execute([ff, '-v', 'warning', '-nostdin', '-n', '-i', str(source), '-vf', f'fps=1/{interval}', '-q:v', '3', str(output/'frame_%05d.jpg')])
        (output/'index.json').write_text(json.dumps({'interval_seconds': interval, 'note': '近似采样中心，非精确seek/视觉识别', 'source': str(source)}, ensure_ascii=False, indent=2), encoding='utf-8')
    else:
        render(args, ff, fp)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, TypeError, OSError, subprocess.CalledProcessError, ImportError, KeyError, ZeroDivisionError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        sys.exit(1)
