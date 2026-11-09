"""Money Reels Studio — free, animated Japanese finance shorts."""
import argparse
import asyncio
import json
import math
import os
import random
import subprocess
import tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
W, H, FPS = 540, 960, 15  # Render efficiently; upscale at encode time.
NAVY = (5, 10, 23)
CYAN = (67, 225, 239)
GOLD = (255, 197, 88)
WHITE = (249, 251, 255)
MUTED = (152, 172, 197)
FONT_PATHS = [
    '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc',
    '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
    '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
]
FONT_PATH = next((p for p in FONT_PATHS if os.path.exists(p)), FONT_PATHS[-1])
FONTS = {}

def ft(size):
    size = int(size)
    if size not in FONTS:
        FONTS[size] = ImageFont.truetype(FONT_PATH, size)
    return FONTS[size]

def clamp(x, lo=0, hi=1):
    return max(lo, min(hi, x))

def ease(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3

def measure(draw, s, size):
    bb = draw.textbbox((0, 0), str(s), font=ft(size))
    return bb[2] - bb[0]

def text_center(draw, s, y, size, color=WHITE, alpha=1):
    s = str(s)
    while size > 18 and measure(draw, s, size) > W - 72:
        size -= 1
    if alpha < 1:
        color = tuple(int(NAVY[i] * (1-alpha) + color[i] * alpha) for i in range(3))
    draw.text(((W - measure(draw, s, size)) / 2, int(y)), s, font=ft(size), fill=color)

def panel(draw, box, fill=(16, 31, 50), outline=(42, 85, 109), radius=22):
    draw.rounded_rectangle(tuple(map(int, box)), radius=radius, fill=fill, outline=outline, width=2)

def base_frame(t, idx, count, topic):
    im = Image.new('RGB', (W, H), NAVY)
    d = ImageDraw.Draw(im)
    for y in range(0, H, 5):
        shade = int(5 + 9 * y / H)
        d.line((0, y, W, y), fill=(shade, shade + 5, shade + 17), width=5)
    offset = int(t * 13) % 55
    for x in range(-55, W + 55, 55):
        d.line((x + offset, 0, x + offset, H), fill=(20, 38, 58), width=1)
    for y in range(55, H, 55):
        d.line((0, y, W, y), fill=(20, 38, 58), width=1)
    d.rounded_rectangle((20, 25, W - 20, H - 25), radius=27, outline=(34, 82, 109), width=2)
    d.rounded_rectangle((37, 43, 222, 84), radius=13, fill=(17, 42, 62))
    d.text((50, 51), 'MONEY / LAB', font=ft(19), fill=GOLD)
    d.text((W - 99, 53), f'{idx + 1:02d}/{count:02d}', font=ft(18), fill=MUTED)
    d.line((43, 101, W - 43, 101), fill=(39, 75, 94), width=2)
    return im, d

def visual(d, slide, t):
    kind = slide.get('kind', 'reveal')
    enter = ease(t / .65)
    bob = math.sin(t * 2.6) * 6
    if kind == 'question':
        radius = 100 + 5 * math.sin(t * 2.5)
        d.ellipse((W/2-radius, 220-radius/3+bob, W/2+radius, 220+radius*1.67+bob), outline=CYAN, width=6)
        d.ellipse((W/2-radius+16, 220-radius/3+16+bob, W/2+radius-16, 220+radius*1.67-16+bob), outline=(35, 100, 128), width=2)
        text_center(d, '?', 248 + bob, 124, GOLD)
    elif kind == 'prices':
        values = slide.get('values', [500, 700, 750])
        count = len(values)
        gap = 12
        bw = (W - 86 - (count - 1) * gap) / count
        for j, val in enumerate(values):
            x = 43 + j * (bw + gap)
            delay = .14 * j
            p = ease((t - delay) / .48)
            y = 275 + (1-p) * 115 + math.sin(t*2+j)*3
            highlight = j == int(slide.get('highlight', count-1))
            color = GOLD if highlight else CYAN
            panel(d, (x, y, x + bw, y + 147), (24, 39, 59), color if p > .2 else (32, 58, 75))
            s = f'{val:,}円'
            size = 29 if count <= 2 else 24
            d.text((x + (bw - measure(d, s, size))/2, y+48), s, font=ft(size), fill=color)
            if highlight:
                d.rounded_rectangle((x+10, y+113, x+bw-10, y+124), radius=5, fill=GOLD)
    elif kind == 'bars':
        values = slide.get('values', [100, 134, 181])
        labels = slide.get('labels', ['現在', '10年', '20年'])
        maximum = max(values) or 1
        for j, val in enumerate(values):
            x = 92 + j * 125
            p = ease((t - .2*j)/1.15)
            height = int(200 * val / maximum * p)
            y = 443-height
            color = GOLD if j == len(values)-1 else CYAN
            if height > 12:
                panel(d, (x, y, x+74, 443), (20, 61, 79), color, 10)
            text_center_x(d, f'{round(val*p):,}', x+37, max(183, y-44), 24, color)
            text_center_x(d, labels[j] if j < len(labels) else '', x+37, 465, 18, MUTED)
    elif kind == 'split':
        left = slide.get('left', '思い込み')
        right = slide.get('right', '現実')
        panel(d, (40, 240, 259, 424), (25, 38, 59), (79, 114, 142))
        panel(d, (281, 240, 500, 424), (33, 44, 50), GOLD)
        text_center_x(d, left, 150, 311, 27, WHITE)
        text_center_x(d, right, 390, 311, 27, GOLD)
        d.line((264, 278, 276, 390), fill=CYAN, width=3)
    elif kind == 'count':
        value = float(slide.get('number', 100))
        suffix = slide.get('suffix', '%')
        displayed = round(value * ease(t / 1.45))
        text_center(d, f'{displayed:,}{suffix}', 270 + bob, 85, GOLD)
        d.arc((112, 203, 428, 520), start=205, end=205+int(305*ease(t/1.5)), fill=CYAN, width=10)
    else:
        r = 110 + 4*math.sin(t*2.7)
        d.ellipse((W/2-r, 215+bob, W/2+r, 215+2*r+bob), outline=CYAN, width=6)
        d.ellipse((W/2-r+18, 233+bob, W/2+r-18, 197+2*r+bob), outline=GOLD, width=3)
        text_center(d, slide.get('symbol', '¥'), 268+bob, 91, WHITE)

def text_center_x(d, s, x, y, size, color):
    s = str(s)
    while size > 15 and measure(d, s, size) > 198:
        size -= 1
    d.text((x-measure(d, s, size)/2, int(y)), s, font=ft(size), fill=color)

def frame(slide, t, idx, count, duration, title):
    im, d = base_frame(t, idx, count, title)
    visual(d, slide, t)
    appear = ease((t-.15)/.45)
    headline = slide.get('headline', '')
    text_center(d, headline, 549 + (1-appear)*28, 39, WHITE, appear)
    text_center(d, slide.get('body', ''), 633, 26, CYAN, ease((t-.5)/.45))
    d.line((64, 727, W-64, 727), fill=(40, 83, 105), width=2)
    text_center(d, '知らないと損する お金のしくみ', 763, 21, MUTED)
    d.rounded_rectangle((46, 865, W-46, 876), radius=5, fill=(34, 54, 73))
    progress = (idx + clamp(t / max(duration, .1))) / count
    d.rounded_rectangle((46, 865, 46+max(3, int((W-92)*progress)), 876), radius=5, fill=GOLD)
    return im

async def speak(text, path):
    import edge_tts
    await edge_tts.Communicate(text, 'ja-JP-KeitaNeural', rate='+0%', pitch='-6Hz').save(str(path))

def duration_of(path):
    try:
        result = subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', str(path)], text=True)
        return float(result.strip())
    except Exception:
        return 0

def make_clip(slide, i, count, seconds, audio, dest, title):
    cmd = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', 'pipe:0']
    if audio:
        cmd += ['-i', str(audio)]
    else:
        cmd += ['-f', 'lavfi', '-i', 'anullsrc=channel_layout=stereo:sample_rate=44100']
    cmd += ['-map', '0:v:0', '-map', '1:a:0', '-t', str(seconds), '-vf', 'scale=1080:1920:flags=lanczos,fps=30', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '21', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '160k', '-af', 'apad', '-movflags', '+faststart', str(dest)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    try:
        for n in range(math.ceil(seconds*FPS)):
            proc.stdin.write(frame(slide, n/FPS, i, count, seconds, title).tobytes())
    except BrokenPipeError:
        raise RuntimeError('ffmpeg closed unexpectedly; check its error output')
    finally:
        proc.stdin.close()
    if proc.wait():
        raise RuntimeError('ffmpeg failed on slide ' + str(i))

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--topic', default='decoy')
    p.add_argument('--output', default='video.mp4')
    p.add_argument('--silent', action='store_true')
    p.add_argument('--demo-seconds', type=int, default=0)
    args = p.parse_args()
    topics = json.loads((ROOT/'topics.json').read_text(encoding='utf-8'))
    if args.topic == 'auto':
        keys = list(topics)
        args.topic = keys[(int(os.environ.get('GITHUB_RUN_NUMBER', '1'))-1) % len(keys)]
    if args.topic not in topics:
        p.error('Unknown topic: '+args.topic)
    topic = topics[args.topic]
    slides = topic['slides']
    if not slides:
        p.error('No slides found')
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        audio_files, durations = [], []
        for i, slide in enumerate(slides):
            audio = tmp/f'voice_{i:02d}.mp3'
            if not args.silent:
                try:
                    asyncio.run(speak(slide.get('voice', ''), audio))
                    length = duration_of(audio)
                    if length > 0:
                        audio_files.append(audio)
                        durations.append(length+.38)
                        continue
                except Exception as exc:
                    print('Voice unavailable:', exc, flush=True)
            audio_files.append(None)
            durations.append(4.0)
        if args.demo_seconds:
            durations = [args.demo_seconds/len(slides)]*len(slides)
        clips = []
        for i, (slide, seconds, audio) in enumerate(zip(slides, durations, audio_files)):
            dest = tmp/f'clip_{i:02d}.mp4'
            print(f'Creating scene {i+1}/{len(slides)}', flush=True)
            make_clip(slide, i, len(slides), seconds, audio, dest, topic.get('title', ''))
            clips.append(dest)
        listing = tmp/'concat.txt'
        listing.write_text(''.join(f"file '{x.as_posix()}'\n" for x in clips), encoding='utf-8')
        subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', str(listing), '-c', 'copy', '-movflags', '+faststart', args.output], check=True)
    print('Created:', args.output, flush=True)

if __name__ == '__main__':
    main()
