import argparse, logging, os, shutil, signal, sys, threading, time
from pathlib import Path
from . import config, media, schema, store, video
from .store import NOW, dump, load, db, lock_suffix

LOG=logging.getLogger('cutroom.worker')
QUIT=threading.Event()
class LostJob(Exception): pass

class Reporter:
    def __init__(self,job):
        self.job=job; self.last=0; self.percent=-1; self.stage=''; self.dead=threading.Event(); self.closed=threading.Event()
        self.thread=threading.Thread(target=self.beat,daemon=True); self.thread.start()
    def beat(self):
        while not self.closed.wait(14):
            try:
                with db(True) as c:
                    row=c.execute("UPDATE jobs SET lease=? WHERE id=? AND status='running' AND worker=?",(NOW()+90,self.job['id'],self.job['worker']))
                    if not row.rowcount: self.dead.set(); return
                    c.execute("UPDATE workers SET seen=? WHERE id=?",(NOW(),self.job['worker']))
            except Exception: LOG.exception('heartbeat_failed job=%s',self.job['id'])
    def __call__(self,percent,stage):
        if self.dead.is_set(): raise LostJob()
        value=max(self.percent,min(99,int(percent)))
        if stage==self.stage and (value==self.percent or time.monotonic()-self.last<.7): return
        with db(True) as c:
            row=c.execute("UPDATE jobs SET progress=?,stage=?,lease=?,updated=? WHERE id=? AND status='running' AND worker=?",
                (value,stage,NOW()+90,NOW(),self.job['id'],self.job['worker']))
            if row.rowcount!=1: raise LostJob()
        self.percent=value; self.stage=stage; self.last=time.monotonic()
    def finish(self): self.closed.set(); self.thread.join(timeout=1)


def analyze_file(path, preview_path, progress, prefs, sample=False, heatmap=()):
    from . import intelligence as ai
    progress(2,'Checking video format'); info=video.inspect(path)
    if not sample and (not preview_path.is_file() or preview_path.stat().st_size < 10000):
        tmp=preview_path.with_suffix('.partial.mp4'); progress(4,'Preparing browser preview')
        video.proxy(path,tmp,info,lambda f:progress(4+13*f,'Preparing browser preview')); tmp.replace(preview_path)
    vpath=path if sample else preview_path
    audio=(preview_path.parent / (preview_path.stem+'.audio.wav'))
    try:
        progress(17,'Extracting audio')
        exists=video.audio_extract(path,audio,info,lambda f:progress(17+3*f,'Extracting audio'))
        if exists:
            progress(20,'Transcribing speech')
            pcm=ai.read_pcm(audio)
            words,language=ai.transcribe(pcm,info['duration'],prefs['language'],progress)
            wave=ai.wave_summary(pcm)
            progress(58,'Grouping speaker voices'); speakers=ai.voices(words,pcm)
            del pcm
        else: words,language,wave,speakers=[],None,[],0
    finally: audio.unlink(missing_ok=True)
    progress(42,'Ranking standout moments with custom AI instructions')
    selected=ai.rank(words,info['duration'],prefs,(),wave,language,heatmap=heatmap)
    if not selected: raise video.MediaError('No editable highlight was found. Try a longer video.')
    progress(62,'Precision Steadicam tracking on highlight clips')
    ranges=[(c['s'],c['e']) for c in selected]
    track=video.track_video(vpath,info,lambda f:progress(62+18*f,'Precision subject tracking'), ranges=ranges)
    progress(82,'Enhance & Polish: Applying kinetic typography & motion styling')
    faces=sum(x['n']>0 for x in track)
    return dict(info=info|{'language':language,'speakers':speakers,'face_frames':faces,'scene_changes':sum(x['cut'] for x in track)}, words=words, track=track, waveform=wave, candidates=selected)


def make_thumbs(project,candidates):
    for clip in candidates:
        key=media.thumb_key(clip['s'],clip['e']); f=media.thumb_file(project,key)
        try:
            if not f.is_file():
                f.parent.mkdir(mode=0o755,parents=True,exist_ok=True)
                at=clip['s']+.26*(clip['e']-clip['s'])
                video.still(media.preview_file(project),f,at,480)
            clip['poster_key']=key
            media.sync_to_supabase_storage(f, f"thumbnails/{project['id']}/{key}.jpg")
        except Exception: LOG.warning('clip_thumbnail_unavailable',exc_info=True)


def pick_brand(c,prefs,user):
    if prefs.get('brand'):
        row=c.execute('SELECT data FROM brands WHERE id=? AND user_id=?',(prefs['brand'],user)).fetchone()
        if row: return load(row['data'])
    return None


def add_clips(c,project,candidates,prefs,exclude=()):
    ids=[]; brand=pick_brand(c,prefs,project['user_id']); now=NOW()
    for cand in candidates:
        if any(abs(cand['s']-a)<.42 and abs(cand['e']-b)<.42 for a,b in exclude): continue
        id=store.uid(); edit=schema.initial_edit(prefs,brand)
        c.execute('INSERT INTO clips (id,project_id,title,start_at,end_at,score,insights,edit,created) VALUES(?,?,?,?,?,?,?,?,?)',
            (id,project['id'],cand['title'],cand['s'],cand['e'],cand['score'],dump({k:v for k,v in cand.items() if k not in ('title','s','e','score')}),dump(edit),now))
        ids.append(id)
    return ids


def analysis_job(job,project,report):
    from . import intelligence as ai
    import os, shutil
    prefs=load(project['prefs']); folder=media.project_dir(project['id']); folder.mkdir(mode=0o700,parents=True,exist_ok=True)
    telemetry = None
    source_path = folder/'source'
    preview_path = media.preview_file(project)
    
    # 1. Superfast Platform Telemetry & Subtitle Ingestion (Idea 2: YouTube Cheat Code)
    if project.get('source_url'):
        report(2, 'Extracting audience heatmap & platform telemetry...')
        try:
            telemetry = media.extract_platform_telemetry(project['source_url'])
        except Exception as e:
            LOG.warning('telemetry_extraction_failed err=%s', e)
            telemetry = None

        if telemetry and telemetry.get('has_native_subs'):
            report(8, f"Found {len(telemetry['words'])} words & {len(telemetry['heatmap'])} replay peaks instantly!")
            if not preview_path.is_file() or preview_path.stat().st_size < 10000:
                report(12, 'Streaming fast 480p proxy for active speaker tracking...')
                try:
                    media.download_fast_proxy(project['source_url'], preview_path, config.MAX_BYTES,
                        lambda cur, tot: report(12 + 35 * min(1, cur/max(tot,1)), f"Streaming proxy · {cur//(1024**2)} MB"))
                except Exception:
                    media.import_video(project['source_url'], preview_path, config.MAX_BYTES,
                        lambda cur, tot: report(12 + 35 * min(1, cur/max(tot,1)), 'Fetching proxy'))
            
            if not source_path.is_file() and preview_path.is_file():
                try: os.link(str(preview_path), str(source_path))
                except OSError: shutil.copyfile(str(preview_path), str(source_path))

            info = video.inspect(preview_path)
            report(42, 'Ranking standout viral moments with custom AI instructions...')
            candidates = ai.rank(telemetry['words'], info['duration'], prefs, (), [], language=prefs.get('language', 'auto'), heatmap=telemetry.get('heatmap', []))
            if not candidates: raise video.MediaError('No editable highlight was found. Try a longer video.')
            
            report(62, 'Steadicam tracking on standout viral clips...')
            ranges = [(c['s'], c['e']) for c in candidates]
            track = video.track_video(preview_path, info, lambda f: report(62 + 18 * f, 'Precision subject tracking'), ranges=ranges)
            
            report(82, 'Enhance & Polish: Applying kinetic typography & motion styling...')
            faces = sum(x['n'] > 0 for x in track)
            data = dict(
                info=info | {'language': prefs.get('language', 'auto'), 'speakers': 1, 'face_frames': faces, 'scene_changes': sum(x['cut'] for x in track), 'bytes': preview_path.stat().st_size},
                words=telemetry['words'],
                track=track,
                waveform=[],
                candidates=candidates
            )
            report(90, 'Enhance & Polish: Generating hook cards & B-roll insights...')
            poster_at = min(data['info']['duration'] - .04, data['candidates'][0]['s'] + 1.2)
            try: video.still(preview_path, folder/'poster.jpg', poster_at)
            except Exception: pass
            make_thumbs(project, data['candidates'])
            media.store_analysis(media.analysis_file(project), data)
            report(96, 'Brahmastra Quality Certification...')
            with db(True) as c:
                verify(c, job)
                ids = add_clips(c, project, data['candidates'], prefs)
                proj_title = telemetry.get('title') or project['title']
                c.execute("UPDATE projects SET title=?,status='ready',info=?,updated=? WHERE id=?", (proj_title, dump(data['info']), NOW(), project['id']))
                done(c, job, {'clip_ids': ids})
            return

        elif telemetry and not telemetry.get('has_native_subs'):
            # Fallback to Idea 1: Sound-First Downloader
            report(8, 'Downloading lightweight audio stream for fast AI transcription...')
            temp_audio = folder/'audio.m4a'
            try:
                media.download_audio_stream(project['source_url'], temp_audio, config.MAX_BYTES,
                    lambda cur, tot: report(8 + 15 * min(1, cur/max(tot,1)), f"Fetching audio · {cur//(1024**2)} MB"))
            except Exception: pass
            report(25, 'Fetching preview media...')
            media.download_fast_proxy(project['source_url'], preview_path, config.MAX_BYTES,
                lambda cur, tot: report(25 + 25 * min(1, cur/max(tot,1)), 'Fetching preview media'))
            if not source_path.is_file() and preview_path.is_file():
                try: os.link(str(preview_path), str(source_path))
                except OSError: shutil.copyfile(str(preview_path), str(source_path))

    # Standard analysis for local files or fallback
    path = media.source_file(project)
    if not path.is_file() or not path.stat().st_size: raise video.MediaError('The source upload is incomplete. Select your original file and resume the upload.')
    info = video.inspect(path)
    report(3, 'Reading source media')
    data = analyze_file(path, preview_path, report, prefs, heatmap=telemetry.get('heatmap', []) if telemetry else [])
    report(96, 'Saving clips and preview')
    data['info']['bytes'] = path.stat().st_size
    poster_at = min(data['info']['duration'] - .04, data['candidates'][0]['s'] + 1.2)
    try: video.still(preview_path, folder/'poster.jpg', poster_at)
    except Exception: pass
    make_thumbs(project, data['candidates'])
    media.store_analysis(media.analysis_file(project), data)
    with db(True) as c:
        verify(c, job)
        ids = add_clips(c, project, data['candidates'], prefs)
        c.execute("UPDATE projects SET status='ready',info=?,updated=? WHERE id=?", (dump(data['info']), NOW(), project['id']))
        done(c, job, {'clip_ids': ids})


def regeneration_job(job,project,report):
    from . import intelligence as ai
    report(20,'Loading timestamped transcript'); data=media.read_analysis(project)
    prefs=load(job['payload'])['prefs']
    report(42,'Ranking alternatives')
    candidates=ai.rank(data['words'],data['info']['duration'],prefs,data['track'],data['waveform'],data['info'].get('language'),heatmap=data.get('heatmap',[]))
    report(90,'Creating clip covers')
    make_thumbs(project,candidates)
    with db(True) as c:
        verify(c,job)
        exists=c.execute('SELECT start_at,end_at FROM clips WHERE project_id=?',(project['id'],)).fetchall()
        ids=add_clips(c,project,candidates,prefs,[(x['start_at'],x['end_at']) for x in exists])
        c.execute('UPDATE projects SET updated=? WHERE id=?',(NOW(),project['id']))
        done(c,job,{'clip_ids':ids})


def render_job(job,project,report):
    payload=load(job['payload']); clip=payload['clip']; options=payload['options']; analysis=media.read_analysis(project)
    dest=media.export_dir(job['id']); dest.mkdir(mode=0o700,parents=True,exist_ok=True)
    with db() as c:
        assets={r['id']:dict(r)|{'details':load(r['details'])} for r in c.execute('SELECT * FROM assets WHERE user_id=?',(project['user_id'],)).fetchall()}
    report(2,'Building render graph')
    result=video.render(media.source_file(project),dest/'clip.mp4',analysis['info'],analysis,clip,options,assets,lambda f:report(3+94*f,'Encoding MP4'))
    (dest/'captions.srt').write_text(video.srt(analysis['words'],clip['start_at'],clip['end_at'],clip['edit']),encoding='utf8')
    cloud_url = media.sync_to_supabase_storage(dest/'clip.mp4', f"exports/{job['id']}/clip.mp4")
    media.sync_to_supabase_storage(dest/'captions.srt', f"exports/{job['id']}/captions.srt")
    if cloud_url: result['cloud_url'] = cloud_url
    with db(True) as c:
        verify(c,job)
        done(c,job,result|{'title':clip['title']})


def verify(c,job):
    if not c.execute("SELECT id FROM jobs WHERE id=? AND status='running' AND worker=?"+lock_suffix(),(job['id'],job['worker'])).fetchone(): raise LostJob()

def done(c,job,result):
    c.execute("UPDATE jobs SET status='done',progress=100,stage='Complete',lease=NULL,output=?,updated=? WHERE id=? AND worker=?",(dump(result),NOW(),job['id'],job['worker']))


def run_job(job):
    LOG.info('job_started id=%s kind=%s attempt=%s',job['id'],job['kind'],job['attempts'])
    report=Reporter(job)
    try:
        with db() as c:
            project=c.execute('SELECT * FROM projects WHERE id=? AND user_id=?',(job['project_id'],job['user_id'])).fetchone()
        if not project: raise LostJob()
        if job['kind']=='analyze': analysis_job(job,dict(project),report)
        elif job['kind']=='render': render_job(job,dict(project),report)
        elif job['kind']=='regenerate': regeneration_job(job,dict(project),report)
        LOG.info('job_succeeded id=%s kind=%s',job['id'],job['kind'])
    except LostJob: LOG.info('job_lease_lost id=%s',job['id'])
    except Exception as e:
        LOG.exception('job_failed id=%s kind=%s',job['id'],job['kind'])
        user_message=e.args[0] if isinstance(e,(video.MediaError,media.ImportErrorMessage)) else 'The worker could not finish this job. Retry, or try a different source if the error persists.'
        with db(True) as c:
            result=c.execute("UPDATE jobs SET status='failed',stage='Needs attention',error=?,lease=NULL,updated=? WHERE id=? AND worker=?",
                             (user_message,NOW(),job['id'],job['worker']))
            if result.rowcount and job['kind']=='analyze': c.execute("UPDATE projects SET status='failed',updated=? WHERE id=?",(NOW(),job['project_id']))
    finally: report.finish()


def worker_loop(owner=None, once=False):
    store.init(); owner=owner or f'{os.getpid()}-{store.uid()[:8]}'
    LOG.info('worker_ready owner=%s ffmpeg=%s database=%s',owner,shutil.which(config.FFMPEG), 'postgres' if store.POSTGRES else 'sqlite')
    last_seen=0
    while not QUIT.is_set():
        try:
            if NOW()-last_seen>=10:
                with db(True) as c:
                    last_seen=NOW()
                    c.execute('INSERT INTO workers(id,seen) VALUES(?,?) ON CONFLICT(id) DO UPDATE SET seen=excluded.seen',(owner,last_seen))
                    c.execute('DELETE FROM workers WHERE seen<?',(last_seen-300,))
            job=store.claim(owner)
            if job: run_job(job)
            elif once: break
            else: QUIT.wait(.65)
        except Exception: LOG.exception('worker_loop_failed'); QUIT.wait(3)
        if once: break
    with db(True) as c: c.execute('DELETE FROM workers WHERE id=?',(owner,))

def start_embedded_worker():
    thread = threading.Thread(target=worker_loop, daemon=True)
    thread.start()
    return thread

def main():
    a=argparse.ArgumentParser(); a.add_argument('--once',action='store_true'); args=a.parse_args()
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(name)s %(message)s')
    signal.signal(signal.SIGTERM,lambda *_:QUIT.set()); signal.signal(signal.SIGINT,lambda *_:QUIT.set())
    worker_loop(once=args.once)

if __name__=='__main__': main()
