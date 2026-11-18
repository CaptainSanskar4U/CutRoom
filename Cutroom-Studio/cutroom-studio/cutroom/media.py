from pathlib import Path
from contextlib import contextmanager
import http.client, ipaddress, json, socket, ssl, time, os, shutil, re
from urllib.parse import urlsplit, urljoin
from .config import MEDIA, ROOT, IMPORT_HOSTS, MAX_BYTES

try:
    import fcntl
    def _flock_ex(f): fcntl.flock(f, fcntl.LOCK_EX)
    def _flock_un(f): fcntl.flock(f, fcntl.LOCK_UN)
except ImportError:
    try:
        import msvcrt
        def _flock_ex(f):
            try: msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError: pass
        def _flock_un(f):
            try: msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
            except OSError: pass
    except ImportError:
        def _flock_ex(f): pass
        def _flock_un(f): pass

SAMPLES = ROOT/'samples'

def sample_index():
    try: return json.loads((SAMPLES/'index.json').read_text())
    except FileNotFoundError: return {}

def project_dir(id): return MEDIA/'projects'/id

def export_dir(id): return MEDIA/'exports'/id

def source_file(project):
    return SAMPLES/f"{project['sample']}.mp4" if project['sample'] else project_dir(project['id'])/'source'

def analysis_file(project):
    return SAMPLES/f"{project['sample']}.json" if project['sample'] else project_dir(project['id'])/'analysis.json'

def preview_file(project):
    return source_file(project) if project['sample'] else project_dir(project['id'])/'preview.mp4'

def poster_file(project):
    return SAMPLES/f"{project['sample']}.jpg" if project['sample'] else project_dir(project['id'])/'poster.jpg'


def thumb_key(start,end): return f"{round(start*1000)}-{round(end*1000)}"

def thumb_file(project,key):
    if project['sample']:
        bundled=SAMPLES/'thumbs'/f"{project['sample']}-{key}.jpg"
        if bundled.is_file() or not project.get('id'): return bundled
    return project_dir(project['id'])/'thumbs'/f'{key}.jpg'

def read_analysis(project): return json.loads(analysis_file(project).read_text())

def store_analysis(path,data):
    temp=path.with_suffix('.partial'); temp.write_text(json.dumps(data,ensure_ascii=False,separators=(',',':'),allow_nan=False)); temp.replace(path)

def get_supabase_client():
    from . import config
    if getattr(config, 'SUPABASE_URL', None) and getattr(config, 'SUPABASE_SECRET', None):
        try:
            from supabase import create_client
            return create_client(config.SUPABASE_URL, config.SUPABASE_SECRET)
        except Exception:
            return None
    return None

def sync_to_supabase_storage(local_path, remote_path):
    client = get_supabase_client()
    if not client or not Path(local_path).is_file(): return None
    from . import config
    try:
        bucket = getattr(config, 'SUPABASE_BUCKET', 'cutroom-media')
        with open(local_path, 'rb') as f:
            file_bytes = f.read()
        client.storage.from_(bucket).upload(remote_path, file_bytes, file_options={"upsert": "true"})
        return client.storage.from_(bucket).get_public_url(remote_path)
    except Exception as e:
        import logging
        logging.getLogger('cutroom').warning('supabase_sync_failed err=%s', e)
        return None

@contextmanager
def project_lock(id):
    folder=project_dir(id); folder.mkdir(mode=0o700,parents=True,exist_ok=True)
    with (folder/'.lock').open('ab') as f:
        _flock_ex(f)
        try: yield folder
        finally: _flock_un(f)

class ImportErrorMessage(Exception): pass

def is_platform_url(url: str) -> bool:
    clean = url.lower().strip()
    return any(domain in clean for domain in [
        'youtube.com', 'youtu.be', 'tiktok.com', 'x.com', 'twitter.com',
        'vimeo.com', 'instagram.com', 'facebook.com', 'reddit.com'
    ])

def valid_import(url):
    clean = url.strip()
    if is_platform_url(clean):
        return urlsplit(clean)
    try: p=urlsplit(clean)
    except ValueError as e: raise ImportErrorMessage('Enter a valid video link.') from e
    try:
        good = p.scheme in ('https', 'http') and (
            p.hostname in IMPORT_HOSTS or 
            (p.path and p.path.lower().endswith(('.mp4','.mov','.mkv','.webm','.m4v')))
        )
    except ValueError: good=False
    if not good and not is_platform_url(clean):
        raise ImportErrorMessage('Enter a valid YouTube or direct video link.')
    if '\r' in url or '\n' in url or '\t' in url: raise ImportErrorMessage('Invalid video URL.')
    return p

class PinnedHTTPS(http.client.HTTPSConnection):
    def __init__(self,host,addresses):
        super().__init__(host,timeout=16,context=ssl.create_default_context()); self.addresses=addresses
    def connect(self):
        last=None
        for addr in self.addresses:
            s=None
            try:
                s=socket.create_connection((addr,443),self.timeout)
                self.sock=self._context.wrap_socket(s,server_hostname=self.host)
                return
            except OSError as e:
                last=e
                if s: s.close()
        if last: raise last
        raise ImportErrorMessage('The video host is unavailable.')


def parse_subtitles_to_words(raw_bytes, ext):
    """Parses JSON3 or VTT subtitle data into word-level records with distributed timestamps."""
    words = []
    if ext == 'json3':
        try:
            data = json.loads(raw_bytes.decode('utf-8', errors='ignore'))
            events = data.get('events', [])
            for ev in events:
                start_ms = ev.get('tStartMs', 0)
                dur_ms = ev.get('dDurationMs', 0)
                segs = ev.get('segs', [])
                if not segs: continue
                for seg in segs:
                    txt = seg.get('utf8', '').strip()
                    if not txt or txt == '\n': continue
                    offset = seg.get('tOffsetMs', 0)
                    ws = (start_ms + offset) / 1000.0
                    tokens = [p.strip() for p in txt.split() if p.strip()]
                    if tokens:
                        seg_dur = max(0.2, (dur_ms - offset) / 1000.0)
                        word_span = seg_dur / len(tokens)
                        for w_i, tok in enumerate(tokens):
                            w_start = ws + w_i * word_span
                            w_end = min(ws + seg_dur, w_start + word_span)
                            words.append(dict(
                                i=len(words),
                                s=round(w_start, 3),
                                e=round(max(w_start + 0.05, w_end), 3),
                                t=tok,
                                p=0.95,
                                speaker=None
                            ))
        except Exception: pass
    elif ext == 'vtt':
        try:
            content = raw_bytes.decode('utf-8', errors='ignore')
            lines = content.splitlines()
            current_s = 0.0
            current_e = 0.0
            for line in lines:
                line = line.strip()
                if '-->' in line:
                    parts = line.split('-->')
                    def parse_vtt_ts(tstr):
                        tstr = tstr.strip().split()[0]
                        p = tstr.split(':')
                        if len(p) == 3: return float(p[0])*3600 + float(p[1])*60 + float(p[2])
                        elif len(p) == 2: return float(p[0])*60 + float(p[1])
                        return 0.0
                    current_s = parse_vtt_ts(parts[0])
                    current_e = parse_vtt_ts(parts[1])
                elif line and not line.startswith(('WEBVTT', 'NOTE', 'STYLE')) and current_e > current_s:
                    txt = re.sub(r'<[^>]+>', '', line).strip()
                    tokens = [p.strip() for p in txt.split() if p.strip()]
                    if tokens:
                        dur_per_word = max(0.18, (current_e - current_s) / len(tokens))
                        for idx, tok in enumerate(tokens):
                            ws = current_s + idx * dur_per_word
                            we = ws + dur_per_word
                            words.append(dict(
                                i=len(words),
                                s=round(ws, 3),
                                e=round(min(current_e, we), 3),
                                t=tok,
                                p=0.92,
                                speaker=None
                            ))
        except Exception: pass
    return words

def extract_platform_telemetry(url):
    """Bulletproof Native Subtitle & Telemetry Snatcher: bypasses YouTube 429 translation blocks."""
    import yt_dlp, urllib.request
    opts = {'quiet': True, 'skip_download': True, 'no_warnings': True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
        heatmap = info.get('heatmap') or []
        duration = float(info.get('duration') or 0)
        title = info.get('title') or 'Imported Video'
        thumbnail = info.get('thumbnail')
        
        subs = {}
        if info.get('automatic_captions'): subs.update(info['automatic_captions'])
        if info.get('subtitles'): subs.update(info['subtitles'])
        subs.pop('live_chat', None)
        # Prioritize original spoken tracks first (-orig), then language-specific, then any
        orig_keys = [k for k in subs.keys() if k.endswith('-orig')]
        priority_keys = orig_keys + ['hi-orig', 'en-orig', 'es-orig', 'hi', 'en', 'es', 'pt', 'id'] + list(subs.keys())
        
        words = []
        for lk in priority_keys:
            if lk in subs and subs[lk]:
                fmt = next((s for s in subs[lk] if s.get('ext') == 'json3'), None) or \
                      next((s for s in subs[lk] if s.get('ext') == 'vtt'), None) or \
                      subs[lk][0]
                if fmt and fmt.get('url'):
                    try:
                        headers = {
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                            'Referer': 'https://www.youtube.com/'
                        }
                        req = urllib.request.Request(fmt['url'], headers=headers)
                        with urllib.request.urlopen(req, timeout=6) as resp:
                            raw = resp.read()
                            words = parse_subtitles_to_words(raw, fmt.get('ext', 'json3'))
                            if words:
                                break
                    except Exception:
                        continue
                    
        return {
            'duration': duration,
            'title': title,
            'thumbnail': thumbnail,
            'heatmap': heatmap,
            'words': words,
            'has_native_subs': bool(words),
            'info': info
        }

def download_fast_proxy(url, dest, limit, cb):
    """Downloads an ultra-fast, lightweight 480p proxy stream for instant face tracking and timeline preview."""
    import yt_dlp
    dest.parent.mkdir(parents=True, exist_ok=True)
    outtmpl = str(dest) + ".%(ext)s"
    def hook(d):
        if d.get('status') == 'downloading':
            curr = d.get('downloaded_bytes', 0)
            tot = d.get('total_bytes') or d.get('total_bytes_estimate') or limit
            cb(curr, tot)
    opts = {
        'format': 'bestvideo[height<=480]+bestaudio/best[height<=480]/best[height<=720]/best',
        'outtmpl': outtmpl,
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        'progress_hooks': [hook],
        'max_filesize': limit,
        'concurrent_fragment_downloads': 8
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        fname = ydl.prepare_filename(info)
        if os.path.exists(fname):
            if Path(fname).resolve() != dest.resolve():
                if dest.exists(): dest.unlink()
                shutil.move(fname, str(dest))
            return dest.stat().st_size
    raise ImportErrorMessage("Failed to download video proxy from link.")

def download_audio_stream(url, dest, limit, cb):
    """Downloads only the lightweight audio stream (m4a/aac/opus) in seconds for fast chunked Whisper."""
    import yt_dlp
    dest.parent.mkdir(parents=True, exist_ok=True)
    outtmpl = str(dest) + ".%(ext)s"
    def hook(d):
        if d.get('status') == 'downloading':
            curr = d.get('downloaded_bytes', 0)
            tot = d.get('total_bytes') or d.get('total_bytes_estimate') or limit
            cb(curr, tot)
    opts = {
        'format': 'bestaudio[ext=m4a]/bestaudio/best',
        'outtmpl': outtmpl,
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        'progress_hooks': [hook],
        'max_filesize': limit,
        'concurrent_fragment_downloads': 8
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        fname = ydl.prepare_filename(info)
        if os.path.exists(fname):
            if Path(fname).resolve() != dest.resolve():
                if dest.exists(): dest.unlink()
                shutil.move(fname, str(dest))
            return dest.stat().st_size
    raise ImportErrorMessage("Failed to download audio stream from link.")

def import_video(url,dest,limit,cb):
    """Downloads video files either via yt-dlp (for YouTube/social links) or direct HTTPS."""
    if is_platform_url(url):
        import yt_dlp
        dest.parent.mkdir(parents=True, exist_ok=True)
        outtmpl = str(dest) + ".%(ext)s"
        def hook(d):
            if d.get('status') == 'downloading':
                curr = d.get('downloaded_bytes', 0)
                tot = d.get('total_bytes') or d.get('total_bytes_estimate') or limit
                cb(curr, tot)
        opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': outtmpl,
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'progress_hooks': [hook],
            'max_filesize': limit,
            'concurrent_fragment_downloads': 8
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            fname = ydl.prepare_filename(info)
            if os.path.exists(fname):
                if Path(fname).resolve() != dest.resolve():
                    if dest.exists(): dest.unlink()
                    shutil.move(fname, str(dest))
                return dest.stat().st_size
        raise ImportErrorMessage("Failed to download video from link.")

    for _ in range(5):
        p=valid_import(url)
        try:
            addresses=sorted({e[4][0] for e in socket.getaddrinfo(p.hostname,443,type=socket.SOCK_STREAM)},key=lambda s:':' in s)
            if not addresses or not all(ipaddress.ip_address(ip).is_global for ip in addresses):
                raise ImportErrorMessage('The import URL does not resolve to a public address.')
            connection=PinnedHTTPS(p.hostname,addresses[:5]); response=None
            try:
                connection.request('GET',(p.path or '/')+('?'+p.query if p.query else ''),headers={'User-Agent':'Cutroom-Studio/1.0','Accept':'video/*,application/octet-stream'})
                response=connection.getresponse()
                if response.status in (301,302,303,307,308):
                    url=urljoin(url,response.getheader('Location','')); continue
                if response.status!=200: raise ImportErrorMessage(f'The video host returned HTTP {response.status}. Check access or upload the file directly.')
                mime=response.getheader('Content-Type','').lower()
                if mime.startswith(('text/','application/json','application/xml')): raise ImportErrorMessage('The link points to a page, not a direct video file.')
                size=int(response.getheader('Content-Length','0') or '0'); used=0
                if size>limit: raise ImportErrorMessage('The linked video exceeds the file or storage limit.')
                deadline=time.monotonic()+1200
                with dest.open('wb') as f:
                    while data:=response.read(256*1024):
                        used+=len(data)
                        if used>limit: raise ImportErrorMessage('The linked video exceeds the file or storage limit.')
                        if time.monotonic()>deadline: raise ImportErrorMessage('The remote download took too long.')
                        f.write(data); cb(used,size)
                if not used or (size and used!=size): raise ImportErrorMessage('The linked file did not download completely.')
                return used
            finally:
                if response: response.close()
                connection.close()
        except (OSError,http.client.HTTPException,ValueError) as e:
            raise ImportErrorMessage('Could not download the video. Check the link or upload a local copy.') from e
    raise ImportErrorMessage('Too many redirects while importing the video.')
