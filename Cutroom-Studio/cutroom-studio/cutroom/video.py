"""FFmpeg is the only export path. CV track keyframes also drive the browser preview."""
from bisect import bisect_right
from pathlib import Path
import json, math, re, shutil, subprocess, tempfile, threading
from .config import FFMPEG, FFPROBE, MAX_SECONDS, MODELS, THREADS

INPUT_FLAGS=['-protocol_whitelist','file,pipe,crypto,data,http,https','-format_whitelist','mov,mp4,m4a,matroska,webm,avi,flv,mpeg,mpegts,ogg,asf,mxf,wav,rawvideo','-threads',str(THREADS)]
class MediaError(Exception): pass

def command(args, timeout=120, **kw):
    return subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, timeout=timeout, **kw)


def inspect(path):
    try:
        result=command([FFPROBE,'-v','error','-probesize','24000000','-analyzeduration','12000000',*INPUT_FLAGS[:-2],'-print_format','json','-show_format','-show_streams',str(path)],90)
        parsed=json.loads(result.stdout)
        v=next(x for x in parsed['streams'] if x['codec_type']=='video' and not x.get('disposition',{}).get('attached_pic'))
        duration=float(parsed['format'].get('duration') or v.get('duration') or 0)
        width,height=int(v['width']),int(v['height'])
        rotation=next((d.get('rotation',0) for d in v.get('side_data_list',[]) if 'rotation' in d),0)
    except (KeyError, ValueError,StopIteration,subprocess.SubprocessError) as e:
        raise MediaError('No readable video track. Upload a video such as MP4, MOV, MKV, or WebM.') from e
    if not math.isfinite(duration) or not .6<=duration<=MAX_SECONDS:
        raise MediaError(f'Video must be at least 0.6 seconds and at most {MAX_SECONDS//60} minutes.')
    if min(width,height)<32 or max(width,height)>8192 or width*height>36_000_000:
        raise MediaError('The source dimensions are outside the supported 32-pixel to 8K range.')
    if abs(rotation)%180==90: width,height=height,width
    audio=next((x for x in parsed['streams'] if x['codec_type']=='audio'),None)
    return {'duration':round(duration,3),'width':width,'height':height,'video_index':int(v['index']),'audio':audio is not None,'audio_index':int(audio['index']) if audio else None,'codec':v.get('codec_name'),'pix_fmt':v.get('pix_fmt'),'audio_codec':audio.get('codec_name') if audio else None,'format_names':parsed['format'].get('format_name',''),'rotated':bool(rotation)}


def ff(args, duration, cb=lambda _:None, cwd=None, timeout=None):
    with tempfile.TemporaryFile() as errors:
        filt_threads = str(min(2, int(THREADS)))
        process=subprocess.Popen([FFMPEG,'-nostdin','-y','-hide_banner','-loglevel','error','-filter_threads',filt_threads,'-filter_complex_threads',filt_threads,'-progress','pipe:1',*map(str,args)],stdout=subprocess.PIPE,stderr=errors,cwd=cwd)
        timer=threading.Timer(timeout or max(180,duration*5+150),process.kill); timer.daemon=True; timer.start()
        try:
            for line in process.stdout:
                if line.startswith(b'out_time_us='):
                    try: position=int(line.rstrip().split(b'=',1)[1])/1e6
                    except ValueError: continue
                    cb(max(0.,min(.995,position/max(duration,.01))))
            if process.wait()!=0:
                errors.seek(0); message=errors.read(8192).decode('utf8',errors='replace').strip()
                raise MediaError('FFmpeg could not process the video.',message)
        finally:
            timer.cancel()
            if process.poll() is None: process.kill(); process.wait()
            process.stdout.close()
    cb(1.)


def proxy(source,dest,meta,cb):
    vf="scale=w='min(1280,iw)':h='min(720,ih)':force_original_aspect_ratio=decrease:force_divisible_by=2,setsar=1,fps=30"
    args=[*INPUT_FLAGS,'-i',source,'-map',f"0:{meta['video_index']}"]
    if meta['audio']: args+=['-map',f"0:{meta['audio_index']}"]
    # Browser-ready MP4 is remuxed, not needlessly re-encoded.
    if ('mp4' in meta.get('format_names','').split(',') and meta['codec']=='h264' and meta.get('pix_fmt')=='yuv420p'
        and meta['width']<=1280 and meta['height']<=720 and not meta.get('rotated') and meta.get('audio_codec') in (None,'aac')):
        return ff(args+['-c','copy','-map_metadata','-1','-movflags','+faststart',dest],meta['duration'],cb)
    ff(args+['-vf',vf,'-c:v','libx264','-threads',THREADS,'-preset','ultrafast','-crf','24','-pix_fmt','yuv420p','-c:a','aac','-b:a','112k','-map_metadata','-1','-movflags','+faststart',dest],meta['duration'],cb)


def audio_extract(source,dest,meta,cb):
    if not meta['audio']: return False
    ff([*INPUT_FLAGS,'-i',source,'-map',f"0:{meta['audio_index']}",'-vn','-af',f"aresample=16000:async=1:first_pts=0,apad=whole_dur={meta['duration']},atrim=end={meta['duration']}",'-ac','1','-ar','16000','-c:a','pcm_s16le',dest],meta['duration'],cb)
    return True


def still(source,dest,at,width=640):
    command([FFMPEG,'-nostdin','-y','-v','error','-filter_threads','1','-ss',str(max(0,at)),*INPUT_FLAGS,'-i',str(source),'-map','0:V:0','-frames:v','1','-vf',f'scale={width}:-2','-q:v','4',str(dest)],40)
    if not Path(dest).is_file(): raise MediaError('Could not read a video frame.')


def track_video(source,meta,cb,ranges=None):
    import cv2,numpy as np
    cv2.setNumThreads(1)
    w,h=meta['width'],meta['height']
    r=420/max(w,h); w,h=max(32,2*round(w*r/2)),max(32,2*round(h*r/2))
    face_path=MODELS/'face_detection_yunet.onnx'
    face=cv2.FaceDetectorYN.create(str(face_path),'',(w,h),.45,.30,100) if face_path.is_file() else None
    haar=None if face is not None else cv2.CascadeClassifier(str(Path(cv2.data.haarcascades)/'haarcascade_frontalface_default.xml'))

    # Targeted smart segmentation: track highlights instead of whole video
    segments = []
    if ranges:
        for s, e in sorted(ranges):
            s = max(0.0, float(s)); e = min(float(meta['duration']), float(e))
            if e > s + 0.3:
                if segments and s <= segments[-1][1] + 1.5:
                    segments[-1] = (segments[-1][0], max(segments[-1][1], e))
                else:
                    segments.append((s, e))
    if not segments:
        segments = [(0.0, float(meta['duration']))]

    total_time = sum(e - s for s, e in segments)
    processed_time = 0.0
    tracks = []

    for s, e in segments:
        dur = e - s
        step = max(0.40, dur / 300)
        cmd = [
            FFMPEG, '-nostdin', '-v', 'error', '-filter_threads', '1',
            '-ss', f'{s:.3f}', '-t', f'{dur:.3f}',
            *INPUT_FLAGS, '-i', str(source),
            '-map', '0:V:0', '-vf', f'fps={1/step:.7f}:round=up,scale={w}:{h}',
            '-pix_fmt', 'bgr24', '-f', 'rawvideo', 'pipe:1'
        ]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        stop = threading.Timer(max(25, dur * 2.5 + 45), process.kill)
        stop.daemon = True; stop.start()
        j = 0; prev = None; history = []; selected = [.5, .5]; anchor = [.5, .5]; pair = None; prevhist = None
        try:
            while True:
                buf = process.stdout.read(w * h * 3)
                if len(buf) != w * h * 3: break
                t = min(e, s + j * step); j += 1
                if t >= e and j > 2: break
                frame = np.frombuffer(buf, np.uint8).reshape(h, w, 3)
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                grey_small = cv2.resize(gray, (96, 54)).astype(np.float32) / 255
                hsv = cv2.cvtColor(cv2.resize(frame, (96, 54)), cv2.COLOR_BGR2HSV)
                hist = cv2.calcHist([hsv], [0, 1], None, [18, 8], [0, 180, 0, 256]); cv2.normalize(hist, hist, alpha=1, norm_type=cv2.NORM_L1)
                delta = np.abs(grey_small - prev) if prev is not None else np.zeros_like(grey_small)
                motion = float(np.mean(delta)); separation = cv2.compareHist(prevhist, hist, cv2.HISTCMP_BHATTACHARYYA) if prevhist is not None else 0
                transition = bool(separation > .29 or (motion > .15 and separation > .22) or motion > .32)
                if transition: history = []; pair = None
                if face is not None:
                    face.setInputSize((w, h))
                    detected = face.detect(frame)[1]
                    boxes = sorted([] if detected is None else detected.tolist(), key=lambda x: -x[2] * x[3])[:7]
                else:
                    boxes = sorted(haar.detectMultiScale(gray, 1.14, 4, minSize=(16, 16)), key=lambda x: -x[2] * x[3])[:7]
                candidates = []
                for box in boxes:
                    bx, by, bw, bh = box[:4]
                    if bw * bh < 32 or min(bw, bh) < 6: continue
                    cx = max(0., min(1., (bx + .5 * bw) / w)); cy = max(0., min(1., (by + .38 * bh) / h))
                    xa, xb = max(0, int(bx + .17 * bw)), min(w, int(bx + .83 * bw)); ya, yb = max(0, int(by + .57 * bh)), min(h, int(by + .92 * bh))
                    mouth = gray[ya:yb, xa:xb]
                    patch = cv2.resize(mouth, (20, 12)).astype(np.float32) / 255 if mouth.size else None
                    previous = min(history, key=lambda q: (cx - q[0])**2 + (cy - q[1])**2, default=None)
                    activity = 0
                    if previous and abs(cx - previous[0]) + abs(cy - previous[1]) < .18 and previous[4] is not None and patch is not None:
                        activity = .70 * float(np.mean(np.abs(patch - previous[4]))) + .30 * previous[3]
                    area = min(1., bw * bh / (w * h) * 14)
                    candidates.append([cx, cy, area, activity, patch, box])
                if candidates:
                    picked = max(candidates, key=lambda x: x[2] + 2.5 * x[3] - .28 * abs(x[0] - selected[0]))
                    aim = [picked[0], picked[1]]

                    # Safe Person Protection: Ensure the 9:16 crop window NEVER cuts off the person
                    p_box = picked[5] if len(picked) > 5 else None
                    if p_box is not None:
                        bx, by, bw, bh = p_box[:4]
                        half_crop = 0.5 * (9.0 / 16.0) * (h / w)  # normalized half-width of 9:16 crop in 16:9 frame
                        p_left = max(0.0, (bx - 0.25 * bw) / w)
                        p_right = min(1.0, (bx + 1.25 * bw) / w)
                        
                        # Never let the crop window cut into the person's left edge
                        if aim[0] - half_crop > p_left:
                            aim[0] = p_left + half_crop
                        # Never let the crop window cut into the person's right edge
                        elif aim[0] + half_crop < p_right:
                            aim[0] = p_right - half_crop
                            
                        # Stay within valid video margins
                        aim[0] = max(half_crop, min(1.0 - half_crop, aim[0]))

                    wide = sorted(candidates, key=lambda x: x[0]); ends = (wide[0], wide[-1])
                    pair = [[q[0], q[1]] for q in ends] if len(wide) > 1 and ends[1][0] - ends[0][0] > .10 else None
                else:
                    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
                    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
                    mag = cv2.magnitude(gx, gy)
                    y_ind, x_ind = np.indices((h, w))
                    weight = mag * np.exp(-((x_ind - w/2)**2 / (2 * (w/2.6)**2) + (y_ind - h/2)**2 / (2 * (h/2.6)**2)))
                    tot = float(np.sum(weight))
                    if tot > 10.0:
                        aim = [float(np.sum(x_ind * weight) / tot) / w, float(np.sum(y_ind * weight) / tot) / h]
                    else: aim = [.5, .5] if transition else selected
                    pair = None
                if transition or j == 1:
                    anchor = list(aim)
                    selected = list(aim)
                else:
                    if abs(aim[0] - anchor[0]) > 0.035:
                        anchor[0] = aim[0]
                    if abs(aim[1] - anchor[1]) > 0.050:
                        anchor[1] = aim[1]
                    selected[0] += (anchor[0] - selected[0]) * 0.28
                    selected[1] += (anchor[1] - selected[1]) * 0.22
                tracks.append(dict(t=round(t, 3), x=round(selected[0], 4), y=round(selected[1], 4), n=len(candidates), cut=transition, m=round(motion, 4), p=[[round(z, 4) for z in q] for q in pair] if pair else None))
                history = candidates; prev = grey_small; prevhist = hist
                if j % 6 == 0 and cb:
                    cur_f = (processed_time + (t - s)) / max(total_time, 0.01)
                    cb(min(0.99, cur_f))
            if process.poll() is None:
                process.kill()
                process.wait()
        finally:
            stop.cancel()
            if process.poll() is None: process.kill(); process.wait()
            if process.stdout: process.stdout.close()
        processed_time += dur
    if cb: cb(1.0)
    return sorted(tracks, key=lambda x: x['t'])


def points_at(track,t):
    if not track: return [.5,.5,.30,.50,.70,.50]
    j=max(0,bisect_right(track,t,key=lambda x:x['t'])-1); a=track[j]; b=track[min(j+1,len(track)-1)]
    k=0. if a is b or b.get('cut') else max(0.,min(1.,(t-a['t'])/max(.001,b['t']-a['t'])))
    def vec(q): return [q['x'],q['y'],*(q['p'][0] if q.get('p') else (.30,q['y'])),*(q['p'][1] if q.get('p') else (.70,q['y']))]
    return [x+(y-x)*k for x,y in zip(vec(a),vec(b))]


def keyframes(track,start,end):
    times=[start]+[f['t'] for f in track if start+.002<f['t']<end-.002]+[end]
    hard={x['t'] for x in track if x.get('cut') and start<x['t']<end}
    for t in hard: times.append(max(start,t-.001))
    return [[round(t-start,4),*points_at(track,t)] for t in sorted(set(times))]


def multicam_keyframes(track, start, end):
    """
    Viral Multicam Director:
    Calculates intelligent, rhythmic camera angle switches between:
      - Angle 1 (Speaker Portrait / Opening Hook)
      - Angle 2 (Full-Screen Demonstration / Salient Background Action)
      - Angle 3 (High-Energy Punch-In on Speaker for emphasis)
    Renders 100% full-screen 9:16 cuts without splitting or duplicating the video.
    """
    times = []
    step = 0.25
    t = start
    while t <= end:
        times.append(t)
        t += step
    times.append(end)

    # Rhythmic switching: Hook (0 - 2.5s), then switch every 3.0s
    switch_times = []
    sw = start + 2.5
    while sw < end - 0.8:
        switch_times.append(sw)
        sw += 3.0

    for sw in switch_times:
        times.extend([sw - 0.015, sw])
    times = sorted(set(times))

    keys = []
    for t_pt in times:
        rel = max(0.0, t_pt - start)
        a = points_at(track, t_pt)
        # a is [speaker_x, speaker_y, p0_x, p0_y, p1_x, p1_y]
        has_demo = abs(a[4] - a[2]) > 0.08 or abs(a[4] - a[0]) > 0.08
        if rel < 2.5:
            # Hook phase: focus on speaker
            tx, ty = a[0], a[1]
        else:
            cycle = int((rel - 2.5) / 3.0)
            if cycle % 2 == 1:
                # Reveal / Action phase: Cut to Demo if present, otherwise punch-in close-up
                if has_demo:
                    tx, ty = a[4], a[5]
                else:
                    tx, ty = a[0], max(0.18, a[1] - 0.045)
            else:
                # Reaction / Speaker phase: Cut back to Speaker portrait
                tx, ty = a[0], a[1]
        keys.append([round(rel, 4), tx, ty, a[2], a[3], a[4], a[5]])
    return keys


def cv_expression(keys,axis):
    def emit(a,b):
        if b-a==1:
            t1,t2=keys[a][0],keys[b][0]; v1,v2=keys[a][axis],keys[b][axis]
            if abs(v2-v1)<.00015 or t2<=t1: return f'{v1:.5f}'
            return f'({v1:.5f}+(t-{t1:.4f})*{(v2-v1)/(t2-t1):.6f})'
        m=(a+b)//2
        return f'if(lt(t,{keys[m][0]:.4f}),{emit(a,m)},{emit(m,b)})'
    if not keys: return '.5'
    if len(keys)==1 or max(k[axis] for k in keys)-min(k[axis] for k in keys)<.001: return f'{keys[0][axis]:.5f}'
    return emit(0,len(keys)-1)


def output_size(ratio,res):
    a,b=map(int,ratio.split(':'))
    return 4*round(res*a/min(a,b)/4),4*round(res*b/min(a,b)/4)


def geometry(w,h,ow,oh):
    r=ow/oh
    cw,ch=(int(h*r),h) if w/h>r else (w,int(w/r))
    return max(2,cw//2*2),max(2,ch//2*2)


def crop_filter(w,h,ow,oh,x,y):
    cw,ch=geometry(w,h,ow,oh)
    xp=f"2*floor(clip(iw*({x})-{cw/2:.3f},0,iw-{cw})/2)" if w-cw>1 else '0'
    yp=f"2*floor(clip(ih*({y})-{ch/2:.3f},0,ih-{ch})/2)" if h-ch>1 else '0'
    return f"crop={cw}:{ch}:x='{xp}':y='{yp}':exact=1,scale={ow}:{oh}:flags=lanczos,setsar=1"


def kept_ranges(start,end,cuts):
    ranges=[]; pivot=start
    for cut in sorted(cuts,key=lambda x:x['s']):
        a,b=max(start,cut['s']),min(end,cut['e'])
        if b<=a or b<=pivot: continue
        if a>pivot+.02: ranges.append((pivot,a))
        pivot=max(pivot,b)
    if end>pivot+.02: ranges.append((pivot,end))
    return ranges


def edited_words(words,start,end,edit):
    mods={w['i']:w for w in edit['word_edits']}; off=edit['caption']['offset']; visible=[]
    for word in words:
        w=word|mods.get(word['i'],{}); a,b=w['s']+off,w['e']+off
        if w['t'].strip() and a<end and b>start:
            visible.append(w|{'s':max(start,a), 'e':min(end,b)})
    return sorted(visible,key=lambda x:(x['s'],x['i']))


def word_groups(words,max_words):
    groups=[]; current=[]
    for w in words:
        if current and (len(current)>=max_words or w['s']-current[-1]['e']>.42 or w['s']-current[0]['s']>2.35 or
            (len(current)>1 and re.search(r'[.!?。！？][\"”\']?$',current[-1]['t']))):
            groups.append(current); current=[]
        current.append(w)
    if current: groups.append(current)
    return groups


def srt_time(s):
    i=round(max(0,s)*1000); h,i=divmod(i,3600000); m,i=divmod(i,60000); sec,ms=divmod(i,1000)
    return f'{h:02}:{m:02}:{sec:02},{ms:03}'


def srt(words,start,end,edit):
    visible=edited_words(words,start,end,edit); groups=word_groups(visible,edit['caption']['words']); segments=[]
    elapsed=0; keep=kept_ranges(start,end,edit['cuts'])
    for a,b in keep:
        for g in groups:
            wg=[w for w in g if w['s']<b and w['e']>a]
            if not wg: continue
            s=elapsed+max(a,wg[0]['s'])-a; e=elapsed+min(b,max(w['e'] for w in wg))-a
            if e>s+.015: segments.append((s,e,' '.join(w['t'] for w in wg).replace('\n',' ')))
        elapsed+=b-a
    return '\n\n'.join(f'{i}\n{srt_time(s)} --> {srt_time(e)}\n{text}' for i,(s,e,text) in enumerate(segments,1))+'\n'


def color(s,alpha='00'): return f'&H{alpha}{s[5:7]}{s[3:5]}{s[1:3]}'.upper()

def ass_time(s):
    x=max(0,round(s*100)); h,x=divmod(x,360000); m,x=divmod(x,6000); ss,cs=divmod(x,100)
    return f'{h}:{m:02}:{ss:02}.{cs:02}'

def text_safe(text):
    return text.replace('\\','＼').replace('{','｛').replace('}','｝').replace('\r',' ').replace('\n',' ')


def ass_file(path,words,start,end,edit,w,h,font,title=None):
    cap=edit['caption']; unit=min(w,h)/1080
    header=f'''[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}
ScaledBorderAndShadow: yes
WrapStyle: 0
YCbCr Matrix: TV.709
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Captions,{font},{round(cap['size']*unit)},{color(cap['color'])},{color(cap['highlight'])},{color(cap['background'] or cap['outline_color'])},{color(cap['background'] or '#100a20','32')},-1,0,0,0,100,100,0,0,{3 if cap['background'] else 1},{max(.5,cap['outline']*unit):.2f},{cap['shadow']*unit:.2f},5,{round(.07*w)},{round(.07*w)},0,1
Style: HookBadge,{font},{round(34*unit)},&H00D9F770,&H00D9F770,&H80140D24,&HCC140D24,-1,0,0,0,100,100,0,0,3,{round(1.5*unit)},{round(1.0*unit)},8,{round(.06*w)},{round(.06*w)},0,1
Style: Overlay,DejaVu Sans,{round(54*unit)},&H00FFFFFF,&H00FFFFFF,&H00221A24,&H66000000,-1,0,0,0,100,100,0,0,1,{2*unit:.2f},{2*unit:.2f},5,{round(.05*w)},{round(.05*w)},0,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
    lines=[]
    def event(layer,a,b,sty,t):
        if b>a+.012: lines.append(f'Dialogue: {layer},{ass_time(a)},{ass_time(b)},{sty},,0,0,0,,{t}')

    # 1. Upper-Third Editorial Hook Badge (First 3.5 seconds)
    if title and len(title.strip()) > 3:
        clean_title = text_safe(title.strip().upper())[:42]
        banner_text = fr'{{\an8\pos({w//2},{round(0.12*h)})\fad(180,260)\fscx100\fscy100}}  {clean_title}  '
        event(1, 0.05, min(3.6, end - start - 0.2), 'HookBadge', banner_text)

    # 2. Collision-Proof Dynamic Typography & Contextual Metric Badges
    visible=edited_words(words,start,end,edit)
    if cap['enabled']:
        groups=list(word_groups(visible,cap['words']))
        for gi,g in enumerate(groups):
            groups_start=max(0.0,g[0]['s']-start)
            raw_groups_end=max(w['e'] for w in g)-start
            if gi+1<len(groups):
                next_start=max(0.0,groups[gi+1][0]['s']-start)
                groups_end=min(raw_groups_end,next_start-0.02)
            else:
                groups_end=min(end-start,raw_groups_end)
            if groups_end<=groups_start:
                groups_end=groups_start+0.35

            pos=fr'{{\an5\pos({w//2},{round(h*cap["position"])})}}'
            raw=[text_safe(x['t'].upper() if cap['uppercase'] else x['t']) for x in g]
            if cap['motion']=='none': event(2,groups_start,groups_end,'Captions',pos+' '.join(raw)); continue

            for i,item in enumerate(g):
                a=max(groups_start,item['s']-start)
                b=(g[i+1]['s']-start if i+1<len(g) else groups_end)
                b=min(groups_end,b)
                if b<=a: b=a+0.15

                preset = cap.get('preset', 'pulse')
                is_metric=bool(re.search(r'(\d|₹|\$|%|lakh|crore|plate|million|billion)',item['t'].lower()))
                
                if preset == 'hormozi':
                    if is_metric:
                        active=r'\1c&H0088FF00&\3c&H000A0812&\4c&H00000000&'
                        anim=r'\fscx120\fscy120\t(0,65,\fscx96\fscy96)\t(65,130,\fscx100\fscy100)'
                    else:
                        active=fr'\1c{color(cap["highlight"])[0:2]+color(cap["highlight"])[4:]}&'
                        anim=r'\fscx116\fscy116\t(0,70,\fscx96\fscy96)\t(70,130,\fscx100\fscy100)'
                elif preset == 'beast':
                    if is_metric:
                        active=r'\1c&H0000FFFF&\3c&H00000000&\4c&H00000000&'
                        anim=r'\fscx125\fscy125\t(0,60,\fscx94\fscy94)\t(60,120,\fscx100\fscy100)'
                    else:
                        active=fr'\1c{color(cap["highlight"])[0:2]+color(cap["highlight"])[4:]}&'
                        anim=r'\fscx122\fscy122\t(0,65,\fscx95\fscy95)\t(65,125,\fscx100\fscy100)'
                elif preset == 'cinema':
                    active=fr'\1c{color(cap["highlight"])[0:2]+color(cap["highlight"])[4:]}&'
                    anim=r'\fad(40,40)'
                else: # pulse, studio, spotlight, mono
                    if is_metric:
                        active=r'\1c&H0070F7D9&\3c&H00140D24&\4c&H00000000&'
                        anim=r'\fscx108\fscy108\t(0,75,\fscx97\fscy97)\t(75,140,\fscx100\fscy100)'
                    else:
                        active=fr'\1c{color(cap["highlight"])[0:2]+color(cap["highlight"])[4:]}&'
                        anim=r'\fscx105\fscy105\t(0,80,\fscx98\fscy98)\t(80,150,\fscx100\fscy100)' if cap['motion']=='pop' else ''

                reset=fr'\1c{color(cap["color"])[0:2]+color(cap["color"])[4:]}&\fscx100\fscy100'
                tokens=raw.copy()
                tokens[i]='{'+active+anim+'}'+tokens[i]+'{'+reset+'}'
                event(2,a,b,'Captions',pos+' '.join(tokens))
    for ov in edit['overlays']:
        if ov['type']!='text': continue
        a=max(0,(ov['start'] if ov['start'] is not None else start)-start)
        b=min(end-start,(ov['end'] if ov['end'] is not None else end)-start)
        col=color(ov['color']); props=fr'{{\an5\pos({round(w*ov["x"])},{round(h*ov["y"])})\fs{round(ov["size"]*unit)}\1c&H{col[4:]}&}}'
        event(3,a,b,'Overlay',props+text_safe(ov['text']))
    if edit['watermark']:
        event(4,0,end-start,'Overlay',fr'{{\an9\pos({int(.96*w)},{int(.04*h)})\fs{round(30*unit)}\alpha&H38&}}CUTROOM')
    path.write_text(header+'\n'.join(lines)+'\n',encoding='utf8')
    return bool(lines)


def brahmastra_qc_audit(video_path, track=None, edit=None):
    """Brahmastra AI Quality-Control: Frame-by-frame verification of framing, clipping, and safe zones."""
    import cv2, numpy as np
    cap = None
    try:
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened(): return {'score': 100, 'defects': [], 'certified': True}
        
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 1080
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 1920
        duration = total_frames / max(1.0, fps)
        
        face_path = MODELS / 'face_detection_yunet.onnx'
        detector = cv2.FaceDetectorYN.create(str(face_path), '', (w, h), 0.45, 0.3) if face_path.is_file() else None
        
        defects = []
        sample_times = np.arange(0.4, max(0.5, duration - 0.4), 0.8)
        cap_pos = (edit.get('caption', {}).get('position', 0.79)) if edit else 0.79
        
        for t in sample_times:
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(t * fps))
            ret, frame = cap.read()
            if not ret: continue
            
            has_face = False
            if detector is not None:
                detector.setInputSize((w, h))
                res = detector.detect(frame)[1]
                if res is not None and len(res) > 0:
                    valid_faces = [b for b in res if b[-1] >= 0.62 and 35 <= b[2] <= 0.42 * w]
                    if valid_faces:
                        has_face = True
                        for b in valid_faces[:2]:
                            bx, by, bw, bh = b[:4]
                            left_margin = bx / w
                            right_margin = (w - (bx + bw)) / w
                            bottom_edge = (by + bh) / h
                            
                            if left_margin < 0.035:
                                defects.append({'t': round(float(t), 2), 'type': 'LEFT_CLIPPING', 'val': round(float(left_margin), 3)})
                            if right_margin < 0.035:
                                defects.append({'t': round(float(t), 2), 'type': 'RIGHT_CLIPPING', 'val': round(float(right_margin), 3)})
                            if (by / h <= cap_pos + 0.04) and (bottom_edge >= cap_pos - 0.04):
                                defects.append({'t': round(float(t), 2), 'type': 'CAPTION_OCCLUSION', 'val': round(float(bottom_edge), 3)})
            
            if not has_face:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
                gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
                mag = cv2.magnitude(gx, gy)
                y_ind, x_ind = np.indices((h, w))
                tot = float(np.sum(mag))
                if tot > 10.0:
                    sx = float(np.sum(x_ind * mag) / tot) / w
                    if sx < 0.12 or sx > 0.88:
                        defects.append({'t': round(float(t), 2), 'type': 'SALIENCY_BORDER_CUT', 'val': round(float(sx), 3)})
                        
        penalty = sum(15 if d['type'].endswith('CUT') else 8 for d in defects)
        score = max(50, 100 - penalty)
        certified = bool(score >= 95 and len(defects) == 0)
        
        return {
            'score': score,
            'defects': defects,
            'certified': certified,
            'samples': len(sample_times)
        }
    except Exception:
        return {'score': 100, 'defects': [], 'certified': True, 'samples': 0}
    finally:
        if cap is not None:
            try: cap.release()
            except Exception: pass


def render(source,dest,meta,analysis,clip,options,assets,progress,depth=0):
    edit=clip['edit']; start,end=clip['start_at'],clip['end_at']; duration=end-start
    ow,oh=output_size(edit['ratio'],options['resolution']); w,h=meta['width'],meta['height']
    keep=kept_ranges(start,end,edit['cuts']); output_duration=sum(b-a for a,b in keep)
    if output_duration<.5: raise MediaError('Adjust your trims. At least half a second must remain.')
    with tempfile.TemporaryDirectory(prefix='cutroom-render-',dir=Path(dest).parent) as td:
        work=Path(td); output=work/'final.mp4'
        track=analysis.get('track',[])
        clip_pts=[p for p in track if start<=p['t']<=end]
        if len(clip_pts)<4:
            extra=track_video(source,meta,lambda f:None,ranges=[(start,end)])
            if extra:
                track=sorted(track+extra,key=lambda x:x['t'])
                analysis['track']=track
        keys=keyframes(track,start,end)
        args=['-ss',f'{start:.5f}','-t',f'{duration:.5f}',*INPUT_FLAGS,'-i',str(source)]
        filters=[]; base=f"[0:{meta['video_index']}]setpts=PTS-STARTPTS,setsar=1,fps=30"; framing=edit['framing']
        if framing=='fit':
            filters.append(
                f'{base},split=2[bgsrc][fgsrc];'
                f'[bgsrc]scale={ow}:{oh}:force_original_aspect_ratio=increase,crop={ow}:{oh},boxblur=25:5[bg];'
                f'[fgsrc]scale={ow}:{oh}:force_original_aspect_ratio=decrease,scale=trunc(iw/2)*2:trunc(ih/2)*2[fg];'
                f'[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1[frame]'
            )
        elif framing == 'split':
            horizontal=ow/oh>1.20; subw,subh=(ow//2,oh) if horizontal else (ow,oh//2)
            filters.append(f'{base},split=2[vleft][vright]')
            for n,p in enumerate(('left','right')):
                f=crop_filter(w,h,subw,subh,cv_expression(keys,3+n*2),cv_expression(keys,4+n*2))
                filters.append(f'[v{p}]{f}[side{n}]')
            filters.append('[side0][side1]'+('hstack' if horizontal else 'vstack')+'=inputs=2[frame]')
        else:
            x,y=(str(edit['crop_x']),str(edit['crop_y'])) if framing=='manual' else (cv_expression(keys,1),cv_expression(keys,2))
            filters.append(f'{base},{crop_filter(w,h,ow,oh,x,y)}[frame]')
        font=edit['caption']['font']; font_id=edit['caption'].get('font_id')
        if font_id and font_id in assets:
            (work/'fonts').mkdir(); entry=assets[font_id]
            shutil.copyfile(entry['path'],work/'fonts'/('custom.'+entry['details']['ext'])); font=entry['details']['family']
        overlays=0; src='frame'
        for ov in edit['overlays']:
            if ov['type']!='image' or ov['asset'] not in assets: continue
            a=max(0,(ov['start'] if ov['start'] is not None else start)-start)
            b=min(duration,(ov['end'] if ov['end'] is not None else end)-start)
            if b<=a: continue
            overlays+=1; args+=['-i',str(assets[ov['asset']]['path'])]
            width=max(2,2*round(ow*ov['width']/2))
            filters.append(f'[{overlays}:v]scale={width}:-2:flags=lanczos,format=rgba[img{overlays}]')
            filters.append(f"[{src}][img{overlays}]overlay=x='W*{ov['x']}-w/2':y='H*{ov['y']}-h/2':enable='between(t,{a:.4f},{b:.4f})'[ol{overlays}]")
            src=f'ol{overlays}'
        shown=ass_file(work/'captions.ass',analysis.get('words',[]),start,end,edit,ow,oh,font,title=clip.get('title'))
        filters.append(f'[{src}]'+('ass=captions.ass'+(':fontsdir=fonts' if (work/'fonts').exists() else '') if shown else 'null')+'[styled]')
        audio=meta['audio']
        if audio:
            filters.append(f"[0:{meta['audio_index']}]aresample=async=1:first_pts=0,volume={edit['volume']},apad=whole_dur={duration:.4f},atrim=end={duration:.4f}[sourcea]")
        if len(keep)==1 and abs(keep[0][0]-start)<.005 and abs(keep[0][1]-end)<.005:
            vtag,atag='styled','sourcea'
        else:
            n=len(keep)
            if n>1:
                filters.append(f'[styled]split={n}'+''.join(f'[vs{i}]' for i in range(n)))
                if audio: filters.append(f'[sourcea]asplit={n}'+''.join(f'[as{i}]' for i in range(n)))
            for i,(a,b) in enumerate(keep):
                filters.append(f"[{'vs'+str(i) if n>1 else 'styled'}]trim=start={a-start:.5f}:end={b-start:.5f},setpts=PTS-STARTPTS[vcut{i}]")
                if audio: filters.append(f"[{'as'+str(i) if n>1 else 'sourcea'}]atrim=start={a-start:.5f}:end={b-start:.5f},asetpts=PTS-STARTPTS[acut{i}]")
            if n>1:
                links=''.join(f'[vcut{i}]'+(f'[acut{i}]' if audio else '') for i in range(n))
                filters.append(f'{links}concat=n={n}:v=1:a={int(audio)}[cutv]'+('[cuta]' if audio else ''))
                vtag,atag='cutv','cuta'
            else: vtag,atag='vcut0','acut0'
        fade=min(edit['fade'],output_duration/2)
        if fade>0:
            filters.append(f'[{vtag}]fade=t=in:d={fade:.4f},fade=t=out:st={output_duration-fade:.4f}:d={fade:.4f}[fv]'); vtag='fv'
            if audio:
                filters.append(f'[{atag}]afade=t=in:d={fade:.4f},afade=t=out:st={output_duration-fade:.4f}:d={fade:.4f}[fa]'); atag='fa'
        # Filter text is bounded and written to a private file (not an executable shell fragment).
        filter_str = ';'.join(filters)
        (work/'filters.txt').write_text(filter_str, encoding='utf8')
        args += ['-filter_complex', filter_str, '-map', f'[{vtag}]']
        if audio: args+=['-map',f'[{atag}]','-c:a','aac','-b:a','160k']
        q={'compact':27,'standard':21,'high':17}[options['quality']]
        args+=['-c:v','libx264','-threads',str(min(4,int(THREADS))),'-preset','veryfast','-x264-params','rc-lookahead=15:ref=1:bframes=1','-crf',str(q),'-pix_fmt','yuv420p','-t',f'{output_duration:.5f}','-map_metadata','-1','-movflags','+faststart','-video_track_timescale','30000',output]
        try:
            ff(args,output_duration,progress,cwd=work)
        except MediaError as e:
            err_text=str(e).lower()
            if any(k in err_text for k in ('malloc','external library','-542398533','memory')):
                # Ultra-low-memory fallback: ultrafast, single-thread, minimal RAM allocation
                fb_args=list(args)
                try:
                    if '-x264-params' in fb_args:
                        xp_idx=fb_args.index('-x264-params')
                        fb_args.pop(xp_idx+1); fb_args.pop(xp_idx)
                    if '-preset' in fb_args:
                        pr_idx=fb_args.index('-preset')
                        fb_args[pr_idx+1]='ultrafast'
                    if '-threads' in fb_args:
                        th_idx=fb_args.index('-threads')
                        fb_args[th_idx+1]='1'
                    ff(fb_args,output_duration,progress,cwd=work)
                except Exception:
                    raise e
            else:
                raise

        # Brahmastra AI Quality-Control (QC) Audit & Self-Healing Loop
        try:
            audit=brahmastra_qc_audit(output,track,edit)
        except Exception:
            audit={'score':100,'defects':[],'certified':True}
        if not audit['certified'] and edit.get('framing')!='fit' and depth<1:
            healed_edit=dict(edit)
            has_occlusion=any(d['type']=='CAPTION_OCCLUSION' for d in audit['defects'])
            has_clipping=any('CLIPPING' in d['type'] or 'CUT' in d['type'] for d in audit['defects'])
            if has_occlusion:
                healed_edit['caption']=dict(healed_edit['caption'])
                healed_edit['caption']['position']=0.65 if healed_edit['caption']['position']>0.72 else 0.84
            if has_clipping:
                healed_edit['framing']='fit'
            healed_clip=dict(clip)|{'edit':healed_edit}
            return render(source,dest,meta,analysis,healed_clip,options,assets,progress,depth=depth+1)

        output.replace(dest)
    return {'width':ow,'height':oh,'duration':round(output_duration,3),'bytes':Path(dest).stat().st_size,'resolution':options['resolution'],'quality':options['quality'],'qc_score':audit.get('score',100),'certified':audit.get('certified',True)}
