
import argparse, asyncio, json, math, os, subprocess, tempfile
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.abspath(__file__))
FONT = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
if not os.path.exists(FONT):
    FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'

W, H, FPS = 540, 960, 15
BG = (5, 9, 19)
CYAN = (46, 221, 237)
GOLD = (246, 193, 95)
WHITE = (247, 249, 255)
DIM = (155, 170, 192)

def font(size):
    return ImageFont.truetype(FONT, size)

def centered(d, text, y, size, color=WHITE):
    f = font(size)
    box = d.textbbox((0, 0), text, font=f)
    width = box[2] - box[0]
    if width > W - 70:
        size = max(18, int(size * (W - 70) / width))
        f = font(size)
        box = d.textbbox((0, 0), text, font=f)
        width = box[2] - box[0]
    d.text(((W - width) / 2, y), text, font=f, fill=color)

def draw_frame(slide, t, idx, count, duration):
    im = Image.new('RGB', (W, H), BG)
    d = ImageDraw.Draw(im)

    for x in range(-50, W + 50, 54):
        xx = x + int(t * 7) % 54
        d.line((xx, 0, xx, H), fill=(14, 27, 42), width=1)

    for y in range(0, H, 54):
        d.line((0, y, W, y), fill=(14, 27, 42), width=1)

    d.rounded_rectangle(
        (22, 27, W - 22, H - 28),
        radius=24,
        outline=(38, 81, 103),
        width=2
    )

    d.text((43, 54), 'MONEY / INSIGHTS',
           font=font(20), fill=GOLD)
    d.text((W - 95, 54), f'{idx+1:02d}/{count:02d}',
           font=font(18), fill=DIM)

    pulse = math.sin(t * 2.5) * 7
    fade = min(1, t * 2.3)
    kind = slide.get('kind', 'highlight')

    if kind == 'question':
        d.ellipse(
            (172, 195+pulse, 368, 391+pulse),
            outline=CYAN, width=6
        )
        centered(d, '?', 211+pulse, 126, GOLD)

    elif kind.startswith('prices'):
        vals = [500, 700] if kind == 'prices2' else [500, 700, 750]
        gap = 12
        bw = (W-88-(len(vals)-1)*gap)//len(vals)

        for j, val in enumerate(vals):
            x = 44+j*(bw+gap)
            y = 236+int(math.sin(t*2+j)*5)
            color = GOLD if j == len(vals)-1 else CYAN

            d.rounded_rectangle(
                (x, y, x+bw, y+140),
                radius=18,
                fill=(17, 32, 48),
                outline=color,
                width=3
            )

            f = font(32 if len(vals)==2 else 26)
            s = f'{val}円'
            bb = d.textbbox((0, 0), s, font=f)
            d.text(
                (x+(bw-(bb[2]-bb[0]))/2, y+48),
                s, font=f, fill=color
            )

    elif kind == 'bars':
        for j, ratio in enumerate([0.52, 0.76, 1.0]):
            x = 101+j*118
            height = int(178*ratio*min(1, t*0.8))
            d.rounded_rectangle(
                (x, 407-height, x+68, 407),
                radius=12,
                fill=(19, 63, 82),
                outline=GOLD if j==2 else CYAN,
                width=3
            )

    else:
        d.ellipse(
            (145, 191+pulse, 395, 441+pulse),
            outline=CYAN, width=5
        )
        d.ellipse(
            (163, 209+pulse, 377, 423+pulse),
            outline=GOLD, width=3
        )
        centered(d, '¥', 252+pulse, 100, WHITE)

    centered(
        d, slide.get('headline', ''),
        494+int((1-fade)*18), 37, WHITE
    )
    centered(d, slide.get('body', ''), 575, 25, CYAN)

    d.line(
        (65, 681, W-65, 681),
        fill=(36, 78, 95), width=2
    )

    centered(d, '知って得する お金の雑学', 730, 22, DIM)

    d.rounded_rectangle(
        (46, 845, W-46, 857),
        radius=6, fill=(35, 50, 67)
    )

    progress = (idx+min(1, t/max(duration, 0.1)))/count

    d.rounded_rectangle(
        (46, 845, 46+max(2, int((W-92)*progress)), 857),
        radius=6, fill=GOLD
    )

    return im

async def voice_one(text, path):
    import edge_tts
    await edge_tts.Communicate(
        text,
        'ja-JP-KeitaNeural',
        rate='-8%',
        pitch='-8Hz'
    ).save(path)

def audio_length(path):
    try:
        result = subprocess.check_output(
            [
                'ffprobe', '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                path
            ],
            text=True
        )
        return float(result.strip())
    except Exception:
        return 0.0

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--topic', default='decoy')
    parser.add_argument('--output', default='video.mp4')
    parser.add_argument('--silent', action='store_true')
    parser.add_argument('--demo-seconds', type=int, default=0)
    args = parser.parse_args()

    with open(os.path.join(ROOT, 'topics.json'), encoding='utf-8') as f:
        topics = json.load(f)

    if args.topic not in topics:
        parser.error('Unknown topic: '+args.topic)

    slides = topics[args.topic]['slides']

    with tempfile.TemporaryDirectory() as tmp:
        durations = []
        audio_paths = []

        for i, slide in enumerate(slides):
            path = os.path.join(tmp, f'voice_{i}.mp3')

            if not args.silent:
                try:
                    asyncio.run(
                        voice_one(slide.get('voice', ''), path)
                    )
                    duration = audio_length(path)

                    if duration > 0:
                        audio_paths.append(path)
                        durations.append(duration+0.6)
                        continue

                except Exception as e:
                    print('Voice unavailable:', e)

            audio_paths.append(None)
            durations.append(5.0)

        if args.demo_seconds:
            durations = [
                args.demo_seconds/len(slides)
            ]*len(slides)

        clips = []

        for i, (slide, duration, voice) in enumerate(
            zip(slides, durations, audio_paths)
        ):
            clip = os.path.join(tmp, f'clip_{i}.mp4')

            cmd = [
                'ffmpeg', '-hide_banner', '-loglevel', 'error',
                '-y', '-f', 'rawvideo',
                '-pix_fmt', 'rgb24',
                '-s', f'{W}x{H}',
                '-r', str(FPS),
                '-i', '-'
            ]

            if voice:
                cmd += ['-i', voice]

            cmd += [
                '-t', str(duration),
                '-vf', 'scale=1080:1920:flags=lanczos,fps=30',
                '-c:v', 'libx264',
                '-preset', 'veryfast',
                '-crf', '21',
                '-pix_fmt', 'yuv420p'
            ]

            if voice:
                cmd += [
                    '-map', '0:v', '-map', '1:a',
                    '-af', 'apad',
                    '-c:a', 'aac', '-b:a', '160k'
                ]
            else:
                cmd += [
                    '-f', 'lavfi', '-t', str(duration),
                    '-i', 'anullsrc=channel_layout=stereo:sample_rate=44100',
                    '-map', '0:v', '-map', '1:a',
                    '-c:a', 'aac', '-b:a', '128k'
                ]

            cmd += ['-shortest', clip]

            proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

            try:
                for n in range(max(1, math.ceil(duration*FPS))):
                    frame = draw_frame(
                        slide, n/FPS, i, len(slides), duration
                    )
                    proc.stdin.write(frame.tobytes())
            finally:
                proc.stdin.close()

            if proc.wait() != 0:
                raise RuntimeError('Video encoding failed')

            clips.append(clip)

        manifest = os.path.join(tmp, 'list.txt')

        with open(manifest, 'w') as f:
            for clip in clips:
                f.write("file '"+clip+"'\n")

        subprocess.run(
            [
                'ffmpeg', '-hide_banner', '-loglevel', 'error',
                '-y', '-f', 'concat', '-safe', '0',
                '-i', manifest,
                '-c', 'copy',
                '-movflags', '+faststart',
                args.output
            ],
            check=True
        )

    print('Created:', args.output)

if __name__ == '__main__':
    main()
