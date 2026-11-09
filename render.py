import argparse, asyncio, json, math, os, subprocess, tempfile
from PIL import Image, ImageDraw, ImageFont

ROOT=os.path.dirname(__file__)
FONT='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
if not os.path.exists(FONT):
    FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
W,H,FPS=540,960,15
BG=(5,10,23); CYAN=(49,225,244); PINK=(255,82,155); WHITE=(245,249,255); DIM=(143,163,189)

def font(n):return ImageFont.truetype(FONT,n)
def center(draw,text,y,sz,color=WHITE):
    f=font(sz); b=draw.textbbox((0,0),text,font=f); draw.text(((W-(b[2]-b[0]))/2,y),text,font=f,fill=color,stroke_width=0)
def rounded(draw,rect,fill,outline=None,width=2):draw.rounded_rectangle(rect,radius=22,fill=fill,outline=outline,width=width)
def frame(slide,t,idx,total):
    im=Image.new('RGB',(W,H),BG);d=ImageDraw.Draw(im)
    # grid / neon frame
    for x in range(0,W,54):d.line((x,0,x,H),fill=(11,23,42),width=1)
    for y in range(0,H,54):d.line((0,y,W,y),fill=(11,23,42),width=1)
    d.rounded_rectangle((22,28,W-22,H-28),radius=25,outline=(28,82,109),width=2)
    d.text((46,55),'MONEY  /  FACTS',font=font(20),fill=CYAN)
    d.text((W-95,55),f'{idx+1:02d}/{total:02d}',font=font(19),fill=DIM)
    pulse=math.sin(t*3)*7
    kind=slide['kind']
    if kind=='question':
        d.ellipse((184,208+pulse,356,380+pulse),outline=CYAN,width=7)
        center(d,'?',212+pulse,115,CYAN)
    elif kind.startswith('prices'):
        vals=[500,700] if kind=='prices2' else [500,700,750]
        gap=16;bw=(W-96-(len(vals)-1)*gap)//len(vals)
        for j,v in enumerate(vals):
            x=48+j*(bw+gap); y=235+int(8*math.sin(t*2+j))
            color=PINK if j==len(vals)-1 else CYAN
            rounded(d,(x,y,x+bw,y+146),(13,28,48),color,3)
            s=f'{v}円';f=font(33 if len(vals)==2 else 28)
            bb=d.textbbox((0,0),s,font=f);d.text((x+(bw-(bb[2]-bb[0]))/2,y+47),s,font=f,fill=color)
    elif kind=='bars':
        vals=[.52,.76,1.0]
        for j,v in enumerate(vals):
            x=100+j*120; height=int(175*v*min(1,t*1.4))
            rounded(d,(x,400-height,x+72,400),(17,53,73),CYAN if j<2 else PINK,3)
    else:
        d.ellipse((145,192+pulse,395,442+pulse),outline=CYAN,width=6)
        d.ellipse((165,212+pulse,375,422+pulse),outline=PINK,width=3)
        center(d,'¥',255+pulse,90,WHITE)
    # text areas
    headline=slide['headline']; size=38 if len(headline)<14 else 32
    center(d,headline,495,size,WHITE)
    center(d,slide['body'],575,25,CYAN)
    d.line((70,672,W-70,672),fill=(32,76,99),width=2)
    center(d,'知って得する お金の雑学',720,22,DIM)
    d.rounded_rectangle((47,846,W-47,859),radius=6,fill=(33,51,70))
    progress=(idx+min(t/4,1))/total
    d.rounded_rectangle((47,846,47+int((W-94)*progress),859),radius=6,fill=CYAN)
    return im

async def synthesize(slides,path):
    import edge_tts
    text=' '.join(s['voice'] for s in slides)
    await edge_tts.Communicate(text,'ja-JP-NanamiNeural',rate='+8%').save(path)

def duration_audio(path):
    try:
        v=subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=noprint_wrappers=1:nokey=1',path],text=True)
        return float(v.strip())
    except Exception:return 0

def main():
    p=argparse.ArgumentParser();p.add_argument('--topic',choices=['decoy','compound','nisa'],default='decoy');p.add_argument('--output',default='video.mp4');p.add_argument('--silent',action='store_true');p.add_argument('--demo-seconds',type=int,default=0);a=p.parse_args()
    topics=json.load(open(os.path.join(ROOT,'topics.json'),encoding='utf8'));slides=topics[a.topic]['slides']
    with tempfile.TemporaryDirectory() as tmp:
        audio=os.path.join(tmp,'voice.mp3');has_audio=False
        if not a.silent:
            try:
                asyncio.run(synthesize(slides,audio));has_audio=True
            except Exception as e:print('Voice service unavailable; rendering without voice:',e)
        dur=duration_audio(audio) if has_audio else 0
        total_seconds=a.demo_seconds or max(20,math.ceil(dur+2))
        slide_sec=total_seconds/len(slides)
        cmd=['ffmpeg','-hide_banner','-loglevel','error','-y','-f','rawvideo','-vcodec','rawvideo','-s',f'{W}x{H}','-pix_fmt','rgb24','-r',str(FPS),'-i','-']
        if has_audio:cmd+=['-i',audio,'-map','0:v','-map','1:a','-af','apad','-shortest']
        cmd+=['-c:v','libx264','-preset','ultrafast','-crf','27','-pix_fmt','yuv420p','-movflags','+faststart']
        if has_audio:cmd+=['-c:a','aac','-b:a','128k']
        cmd+=[a.output]
        proc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
        try:
            for n in range(int(total_seconds*FPS)):
                sec=n/FPS;idx=min(len(slides)-1,int(sec/slide_sec));local=sec-idx*slide_sec
                im=frame(slides[idx],local,idx,len(slides))
                proc.stdin.write(im.tobytes())
        finally:proc.stdin.close()
        code=proc.wait()
        if code:raise RuntimeError('ffmpeg failed')
    print('Created:',a.output)
if __name__=='__main__':main()
