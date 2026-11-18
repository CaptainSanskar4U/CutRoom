from contextlib import asynccontextmanager
import hashlib, hmac, io, json, logging, mimetypes, os, re, secrets, shutil, time
from urllib.parse import urlsplit, unquote
from fastapi import FastAPI, HTTPException, Request, Response, Depends, Query
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from . import config, media, schema, store, video
from .store import NOW, db, dump, load, uid, enqueue, lock_suffix

LOG=logging.getLogger('cutroom.api')
COOKIE='cutroom_sid'
PW=PasswordHasher(time_cost=2,memory_cost=32768,parallelism=1)
DUMMY=PW.hash('constant-missing-account-probe')
DAY=86400
VIDEO_TYPES={'.mp4','.mov','.m4v','.mkv','.webm','.avi','.mpg','.mpeg','.ts','.mxf','.flv','.ogv','.wmv','.3gp'}

@asynccontextmanager
async def lifecycle(_app):
    store.init()
    from . import worker
    worker.start_embedded_worker()
    yield

app=FastAPI(title='Cutroom Studio API',version='1.0.0',lifespan=lifecycle,docs_url='/api/docs',openapi_url='/api/openapi.json',redoc_url=None)

@app.exception_handler(Exception)
async def global_exception_handler(req: Request, exc: Exception):
    import logging
    logging.getLogger('cutroom').exception('Unhandled server exception on %s: %s', req.url.path, exc)
    return JSONResponse(
        status_code=500,
        content={'detail': str(exc) if str(exc) else 'Server encountered an issue. Please retry.'}
    )


def origin(req):
    if config.PUBLIC_ORIGIN: return config.PUBLIC_ORIGIN
    proto=req.headers.get('x-forwarded-proto', req.url.scheme).split(',')[0].strip()
    if proto not in ('https','http'): proto=req.url.scheme
    return f'{proto}://{req.headers.get("host",req.url.netloc)}'

@app.middleware('http')
async def boundary(req,call_next):
    path=req.url.path
    if req.method not in ('GET','HEAD','OPTIONS') and path.startswith('/api/') and path!='/api/billing/webhook':
        claimed=req.headers.get('origin'); dest=urlsplit(origin(req)); incoming=urlsplit(claimed) if claimed and claimed!='null' and len(claimed)<512 else None
        if claimed:
            allowed = False
            if incoming and incoming.scheme == dest.scheme:
                if incoming.netloc == dest.netloc:
                    allowed = True
                else:
                    in_h = (incoming.hostname or '').lower()
                    dest_h = (dest.hostname or '').lower()
                    if in_h in ('localhost', '127.0.0.1', '0.0.0.0') and dest_h in ('localhost', '127.0.0.1', '0.0.0.0'):
                        if (incoming.port or 80) == (dest.port or 80):
                            allowed = True
            if not allowed:
                return JSONResponse({'detail':'Request blocked: cross-origin writes are not allowed.'},403)
    if req.method in ('POST','PUT','PATCH') and path.startswith('/api/'):
        cap=config.CHUNK_BYTES if path.endswith('/upload') else 8*1024**2 if path=='/api/assets' else 768*1024
        try: n=int(req.headers.get('content-length','0'))
        except ValueError: return JSONResponse({'detail':'Invalid content length.'},400)
        if n<0 or n>cap: return JSONResponse({'detail':'Request is larger than allowed.'},413)
        # Also bound chunked bodies in ASGI before framework JSON and multipart handling.
        size=0; receive=req._receive
        async def limited():
            nonlocal size
            packet=await receive(); size+=len(packet.get('body',b''))
            if size>cap: raise HTTPException(413,'Request is larger than allowed.')
            return packet
        req._receive=limited
    res=await call_next(req)
    res.headers['X-Content-Type-Options']='nosniff'
    res.headers['Referrer-Policy']='same-origin'
    res.headers['Permissions-Policy']='camera=(), microphone=(), geolocation=()'
    if path.startswith('/api/') and 'Cache-Control' not in res.headers: res.headers['Cache-Control']='no-store'
    csp_connect = "connect-src 'self' blob: data: https://*.supabase.co http://localhost:* http://127.0.0.1:* ws: wss:;"
    csp_media = "media-src 'self' blob: data: https://*.supabase.co;"
    csp_img = "img-src 'self' blob: data: https://*.supabase.co;"
    if path in ('/', '/landing'):
        res.headers['Content-Security-Policy']=f"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; {csp_img} {csp_media} font-src 'self' data:; {csp_connect} object-src 'none'; base-uri 'none'; form-action 'self'"
    elif path.startswith(('/studio', '/app')):
        res.headers['Content-Security-Policy']=f"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; {csp_img} {csp_media} font-src 'self' data:; {csp_connect} object-src 'none'; base-uri 'none'; form-action 'self'"
    return res


def err(code,text): raise HTTPException(code,text)
def hashed(s): return hashlib.sha256(s.encode()).hexdigest()

def budget(c,key,max_hits,seconds):
    now=NOW()
    c.execute('INSERT INTO throttles (key,since,hits) VALUES(?,?,0) ON CONFLICT(key) DO NOTHING',(key,now))
    r=c.execute('SELECT since,hits FROM throttles WHERE key=?'+lock_suffix(),(key,)).fetchone()
    if r['since']<now-seconds: c.execute('UPDATE throttles SET since=?,hits=1 WHERE key=?',(now,key))
    elif r['hits']>=max_hits: return False
    else: c.execute('UPDATE throttles SET hits=hits+1 WHERE key=?',(key,))
    return True

def rate(req,kind,key='',maximum=16,seconds=60):
    pass # Unlimited studio usage without artificial rate limits


def session(req):
    token=req.cookies.get(COOKIE,'')
    if not re.fullmatch(r'[a-zA-Z0-9_-]{42,50}',token): return None
    with db() as c:
        found=c.execute('SELECT u.* FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token=? AND s.expires>?',(hashed(token),NOW())).fetchone()
    return dict(found) if found else None

def require(req:Request):
    me=session(req)
    if not me: err(401,'Sign in or continue in a guest workspace.')
    return me

def new_session(c,req,res,user,days=30):
    prior=req.cookies.get(COOKIE,'')
    if prior and len(prior)<100: c.execute('DELETE FROM sessions WHERE token=?',(hashed(prior),))
    token=secrets.token_urlsafe(32)
    c.execute('INSERT INTO sessions(token,user_id,expires) VALUES(?,?,?)',(hashed(token),user,NOW()+days*DAY))
    secure=config.COOKIE_MODE=='1' or (config.COOKIE_MODE=='auto' and origin(req).startswith('https:'))
    partitioned=secure and (urlsplit(origin(req)).hostname or '').endswith('.e2b.app')
    cookie_kwargs = dict(max_age=days*DAY, httponly=True, secure=secure, samesite='lax', path='/')
    try:
        if partitioned:
            res.set_cookie(COOKIE, token, partitioned=True, samesite='none', **cookie_kwargs)
        else:
            res.set_cookie(COOKIE, token, **cookie_kwargs)
    except TypeError:
        res.set_cookie(COOKIE, token, max_age=days*DAY, httponly=True, secure=secure, samesite='lax', path='/')


def user_json(me):
    if not me: return None
    return {k:me[k] for k in ('id','name','email','plan')}|{'guest':me['email'] is None,'preferred':load(me['preferred'],{})}


def email_address(s):
    address=s.strip().lower()
    if not re.fullmatch(r'[^\s@]+@[^\s@.]+(?:\.[^\s@.]+)+',address): err(422,'Enter a valid email address.')
    return address

@app.get('/api/me')
def get_me(request:Request):
    return {'user':user_json(session(request)),'config':{'max_bytes':config.MAX_BYTES,'chunk_bytes':config.CHUNK_BYTES,'import_hosts':sorted(config.IMPORT_HOSTS),'stripe':bool(config.STRIPE_SECRET and config.STRIPE_PRICE and config.STRIPE_WEBHOOK),'guest':config.GUEST_ENABLED}}

@app.post('/api/auth/guest',status_code=201)
def guest(req:Request,res:Response):
    current=session(req)
    if current: return user_json(current)
    if not config.GUEST_ENABLED: err(403,'Create an account to start a project.')
    rate(req,'guest',maximum=24,seconds=3600)
    id=uid()
    with db(True) as c:
        c.execute("INSERT INTO users(id,name,plan,created) VALUES(?,?,'Studio',?)",(id,'Guest creator',NOW())); new_session(c,req,res,id,30)
        return user_json(c.execute('SELECT * FROM users WHERE id=?',(id,)).fetchone())

@app.post('/api/auth/register',status_code=201)
def register(data:schema.Auth,req:Request,res:Response):
    email=email_address(data.email); rate(req,'register',maximum=15,seconds=3600)
    if len(data.password)<10: err(422,'Use a password with at least 10 characters.')
    me=session(req); id=me['id'] if me and not me['email'] else uid(); name=data.name or email.split('@',1)[0][:55]
    pw=PW.hash(data.password)
    try:
        with db(True) as c:
            if c.execute('SELECT id FROM users WHERE email=?',(email,)).fetchone(): err(409,'This email is already in use. Sign in instead.')
            if me and not me['email']:
                if c.execute("UPDATE users SET name=?,email=?,pw=?,plan='Creator' WHERE id=? AND email IS NULL",(name,email,pw,id)).rowcount!=1:
                    err(409,'This workspace already has an account.')
                c.execute('DELETE FROM sessions WHERE user_id=?',(id,))
            else: c.execute('INSERT INTO users(id,name,email,pw,created) VALUES(?,?,?,?,?)',(id,name,email,pw,NOW()))
            new_session(c,req,res,id)
            return user_json(c.execute('SELECT * FROM users WHERE id=?',(id,)).fetchone())
    except Exception as e:
        if getattr(e,'sqlstate','')=='23505' or getattr(e,'sqlite_errorname','')=='SQLITE_CONSTRAINT_UNIQUE': err(409,'This email is already in use. Sign in instead.')
        raise

@app.post('/api/auth/login')
def login(data:schema.Auth,req:Request,res:Response):
    key=email_address(data.email); rate(req,'login_ip',maximum=28,seconds=300); rate(req,'login_email',key,maximum=9,seconds=300)
    with db() as c: row=c.execute('SELECT * FROM users WHERE email=?',(key,)).fetchone()
    try: ok=PW.verify(row['pw'] if row else DUMMY,data.password)
    except (VerificationError,InvalidHashError): ok=False
    if not (row and ok): err(401,'Email or password is incorrect.')
    with db(True) as c: new_session(c,req,res,row['id'])
    return user_json(row)

@app.post('/api/auth/logout',status_code=204)
def logout(req:Request,res:Response):
    token=req.cookies.get(COOKIE,'')
    if token and len(token)<100:
        with db(True) as c: c.execute('DELETE FROM sessions WHERE token=?',(hashed(token),))
    res.delete_cookie(COOKIE,path='/',httponly=True,samesite='lax')

@app.patch('/api/settings')
def settings(data:schema.Settings,me=Depends(require)):
    preferred=dict(ratio=data.ratio,language=data.language)
    with db(True) as c: c.execute('UPDATE users SET name=?,preferred=? WHERE id=?',(data.name,dump(preferred),me['id']))
    return user_json(me|{'name':data.name,'preferred':dump(preferred)})

@app.get('/api/usage')
def usage(me=Depends(require)):
    with db() as c:
        seconds=c.execute('SELECT COALESCE(SUM(duration),0) AS n FROM usage WHERE user_id=? AND created>=?',(me['id'],store.month_start())).fetchone()['n']
        n=c.execute('SELECT COUNT(*) AS n,COALESCE(SUM(bytes),0) AS bytes FROM projects WHERE user_id=?',(me['id'],)).fetchone()
        exports=c.execute("SELECT COUNT(*) AS n FROM jobs WHERE user_id=? AND kind='render' AND status='done' AND created>=?",(me['id'],store.month_start())).fetchone()['n']
    return dict(seconds=seconds,limit=config.PLAN_LIMITS[me['plan']],projects=n['n'],bytes=n['bytes'],storage_limit=config.PLAN_STORAGE[me['plan']],exports=exports,plan=me['plan'])


def own(c,id,user,lock=False):
    p=c.execute("SELECT * FROM projects WHERE id=? AND (user_id=? OR status='ready')"+(lock_suffix() if lock else ''),(id,user)).fetchone()
    if not p: err(404,'Project not found.')
    return dict(p)

def own_clip(c,id,user):
    p=c.execute("SELECT c.* FROM clips c JOIN projects p ON p.id=c.project_id WHERE c.id=? AND (p.user_id=? OR p.status='ready')",(id,user)).fetchone()
    if not p: err(404,'Clip not found.')
    return dict(p)

def clip_json(r):
    return {k:r[k] for k in ('id','project_id','title','start_at','end_at','score','version','created')}|{'insights':load(r['insights'],{}),'edit':load(r['edit'],{}),'poster':f"/api/clips/{r['id']}/poster" if load(r['insights'],{}).get('poster_key') else None}

def project_json(c,p):
    result={k:p[k] for k in ('id','title','filename','status','bytes','received','sample','created','updated')}
    result['prefs']=load(p['prefs'],{}); result['info']=load(p['info'],{})
    result['clip_count']=c.execute('SELECT COUNT(*) AS n FROM clips WHERE project_id=?',(p['id'],)).fetchone()['n']
    j=c.execute("SELECT * FROM jobs WHERE project_id=? AND kind IN ('analyze','regenerate') ORDER BY created DESC LIMIT 1",(p['id'],)).fetchone()
    result['job']=store.public_job(j) if j else None
    result['poster']=f"/api/projects/{p['id']}/poster" if p['status']=='ready' and poster_file_exists(p) else None
    if p['status']=='ready': result['preview']=f"/api/projects/{p['id']}/preview"
    return result

def poster_file_exists(p): return media.poster_file(p).is_file()

def owned_asset(c,id,user,kind=None):
    a=c.execute('SELECT * FROM assets WHERE id=? AND user_id=?',(id,user)).fetchone()
    if not a or (kind and a['kind']!=kind): err(422,'The selected asset is not available in this workspace.')
    return dict(a)

def prefs_check(c,prefs,me):
    if prefs.get('brand') and not c.execute('SELECT id FROM brands WHERE id=? AND user_id=?',(prefs['brand'],me['id'])).fetchone(): err(404,'Brand kit not found.')

def project_budget(c,me,size):
    pass # Unlimited storage and projects

def create_row(c,me,title,filename,status,prefs,bytes=0,received=0,url=None,sample=None,info=None):
    id=uid(); now=NOW()
    c.execute('INSERT INTO projects (id,user_id,title,filename,status,bytes,received,source_url,sample,prefs,info,created,updated) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
        (id,me['id'],title,filename,status,bytes,received,url,sample,dump(prefs),dump(info or {}),now,now))
    return id

def simple_filename(s): return s.replace('\\','/').split('/')[-1].replace('\x00','')[:160]

@app.get('/api/projects')
def projects(me=Depends(require)):
    with db() as c:
        return [project_json(c,p) for p in c.execute("SELECT * FROM projects WHERE user_id=? OR status='ready' ORDER BY updated DESC LIMIT 120",(me['id'],)).fetchall()]

@app.post('/api/projects',status_code=201)
def create_project(data:schema.ProjectCreate,req:Request,me=Depends(require)):
    rate(req,'create_project',me['id'],30,300)
    prefs=data.prefs.model_dump(); filename=simple_filename(data.filename)
    if data.url:
        if data.bytes: err(422,'Choose either a link or an upload, not both.')
        try: parts=media.valid_import(data.url)
        except media.ImportErrorMessage as e: err(422,str(e))
        filename=simple_filename(unquote(parts.path)) or 'Imported video'
    elif not data.bytes or not filename:
        err(422,'Choose a local video file or enter a direct video URL.')
    elif not any(filename.lower().endswith(x) for x in VIDEO_TYPES): err(422,'Choose a supported video file, such as MP4, MOV, WebM, or MKV.')
    if data.bytes>config.MAX_BYTES: err(413,'File exceeds the workspace upload limit.')
    title=data.title or filename.rsplit('.',1)[0][:120] or 'Untitled video'
    with db(True) as c:
        project_budget(c,me,data.bytes); prefs_check(c,prefs,me)
        id=create_row(c,me,title,filename,'queued' if data.url else 'uploading',prefs,data.bytes,url=data.url)
        if data.url: enqueue(c,me['id'],id,'analyze')
        return project_json(c,own(c,id,me['id']))

@app.get('/api/samples')
def samples():
    return [dict(id=k,title=v['title'],type=v['type'],credit=v['credit'],link=v['link'],duration=v['duration'],clip_count=v['clip_count'],poster=f'/api/samples/{k}/poster') for k,v in media.sample_index().items()]

@app.get('/api/samples/{sample}/poster')
def sample_poster(sample:str):
    if sample not in media.sample_index(): err(404,'Example not found.')
    return FileResponse(media.poster_file({'sample':sample}),media_type='image/jpeg',headers={'Cache-Control':'public, max-age=604800'})

@app.post('/api/samples/{sample}/open',status_code=201)
def open_sample(sample:str,me=Depends(require)):
    from .worker import add_clips
    index=media.sample_index(); definition=index.get(sample)
    if not definition: err(404,'Example not found.')
    analysis=media.read_analysis({'sample':sample})
    with db(True) as c:
        project_budget(c,me,0)
        existing=c.execute('SELECT * FROM projects WHERE user_id=? AND sample=? ORDER BY created LIMIT 1',(me['id'],sample)).fetchone()
        if existing: return project_json(c,existing)
        id=create_row(c,me,definition['title'],sample+'.mp4','ready',definition['prefs'],sample=sample,info=analysis['info'])
        project=own(c,id,me['id']); add_clips(c,project,analysis['candidates'],definition['prefs'])
        return project_json(c,project)

@app.get('/api/projects/{id}')
def get_project(id:schema.Id,me=Depends(require)):
    with db() as c:
        p=project_json(c,own(c,id,me['id']))
        p['clips']=[clip_json(x) for x in c.execute('SELECT * FROM clips WHERE project_id=? ORDER BY score DESC NULLS LAST, start_at',(id,)).fetchall()]
        return p

@app.patch('/api/projects/{id}')
def rename_project(id:schema.Id,data:schema.Title,me=Depends(require)):
    with db(True) as c:
        own(c,id,me['id']); c.execute('UPDATE projects SET title=?,updated=? WHERE id=?',(data.title,NOW(),id))
        return project_json(c,own(c,id,me['id']))

@app.delete('/api/projects/{id}',status_code=204)
def delete_project(id:schema.Id,me=Depends(require)):
    with db(True) as c:
        own(c,id,me['id']); jobs=[r['id'] for r in c.execute('SELECT id FROM jobs WHERE project_id=?',(id,)).fetchall()]
        c.execute('DELETE FROM projects WHERE id=?',(id,))
    shutil.rmtree(media.project_dir(id),ignore_errors=True)
    for job in jobs: shutil.rmtree(media.export_dir(job),ignore_errors=True)

@app.post('/api/projects/{id}/duplicate',status_code=201)
def duplicate_project(id:schema.Id,me=Depends(require)):
    new=None
    try:
        with db(True) as c:
            old=own(c,id,me['id'],True)
            if old['status']!='ready': err(409,'Only ready projects can be duplicated.')
            project_budget(c,me,old['bytes']); prefs=load(old['prefs']); info=load(old['info'])
            new=create_row(c,me,(old['title']+' (copy)')[:120],old['filename'],'ready',prefs,old['bytes'],old['received'],sample=old['sample'],info=info)
            if not old['sample']:
                folder=media.project_dir(new); folder.mkdir(mode=0o700,parents=True)
                for name in ('source','preview.mp4','poster.jpg','analysis.json'):
                    f=media.project_dir(id)/name
                    if f.is_file(): os.link(f,folder/name)
            thumbs=media.project_dir(id)/'thumbs'
            if thumbs.is_dir(): shutil.copytree(thumbs,media.project_dir(new)/'thumbs',copy_function=os.link)
            for clip in c.execute('SELECT * FROM clips WHERE project_id=?',(id,)).fetchall():
                c.execute('INSERT INTO clips (id,project_id,title,start_at,end_at,score,insights,edit,created) VALUES(?,?,?,?,?,?,?,?,?)',
                          (uid(),new,clip['title'],clip['start_at'],clip['end_at'],clip['score'],clip['insights'],clip['edit'],NOW()))
            return project_json(c,own(c,new,me['id']))
    except BaseException:
        if new: shutil.rmtree(media.project_dir(new),ignore_errors=True)
        raise

@app.patch('/api/projects/{id}/upload')
async def upload(id:schema.Id,req:Request,me=Depends(require)):
    try: offset=int(req.headers.get('upload-offset','-1'))
    except ValueError: err(422,'Invalid upload offset.')
    if not req.headers.get('content-type','').startswith('application/octet-stream'): err(415,'Send raw video bytes.')
    payload=await req.body()
    if not payload or len(payload)>config.CHUNK_BYTES or offset<0: err(422,'Invalid upload chunk.')
    with db() as c: own(c,id,me['id'])
    with media.project_lock(id) as folder,db(True) as c:
        p=own(c,id,me['id'],True)
        if p['status']!='uploading' or p['source_url']: err(409,'This project is not accepting upload chunks.')
        if p['received']!=offset: err(409,{'message':'Upload position changed. Resume from the stored offset.','offset':p['received']})
        if offset+len(payload)>p['bytes']: err(413,'Chunk exceeds the declared file size.')
        f=folder/'source'; mode='r+b' if f.is_file() else 'wb'
        with f.open(mode) as dest:
            if dest.seek(0,2)<offset: err(409,'Upload storage is inconsistent. Start a new project.')
            dest.seek(offset); dest.write(payload); dest.truncate(); dest.flush(); os.fsync(dest.fileno())
        offset+=len(payload)
        c.execute('UPDATE projects SET received=?,updated=? WHERE id=?',(offset,NOW(),id))
        return {'offset':offset,'total':p['bytes']}

@app.post('/api/projects/{id}/start',status_code=202)
def start_project(id:schema.Id,me=Depends(require)):
    with db(True) as c:
        p=own(c,id,me['id'],True)
        if p['status'] in ('queued','processing','ready'): return project_json(c,p)
        if p['status']!='uploading' or not p['bytes'] or p['received']!=p['bytes']: err(409,'Finish uploading the video first.')
        path=media.source_file(p)
        if not path.is_file() or path.stat().st_size!=p['bytes']: err(409,'The uploaded file is incomplete.')
        c.execute("UPDATE projects SET status='queued',updated=? WHERE id=?",(NOW(),id)); enqueue(c,me['id'],id,'analyze')
        return project_json(c,own(c,id,me['id']))

@app.post('/api/projects/{id}/regenerate',status_code=202)
def regenerate(id:schema.Id,prefs:schema.Prefs,me=Depends(require)):
    data=prefs.model_dump()
    with db(True) as c:
        p=own(c,id,me['id'],True); prefs_check(c,data,me)
        if p['status']!='ready': err(409,'Wait for the project analysis to finish.')
        if c.execute("SELECT id FROM jobs WHERE project_id=? AND kind='regenerate' AND status IN ('queued','running')",(id,)).fetchone(): err(409,'Alternatives are already being generated.')
        if c.execute('SELECT COUNT(*) AS n FROM clips WHERE project_id=?',(id,)).fetchone()['n']>=65: err(409,'This project has reached its clip limit.')
        jid=enqueue(c,me['id'],id,'regenerate',{'prefs':data})
        return {'id':jid}

@app.post('/api/projects/{id}/clips',status_code=201)
def manual_clip(id:schema.Id,me=Depends(require)):
    with db(True) as c:
        p=own(c,id,me['id'],True)
        if p['status']!='ready': err(409,'Wait for analysis to finish.')
        if c.execute('SELECT COUNT(*) AS n FROM clips WHERE project_id=?',(id,)).fetchone()['n']>=65: err(409,'This project has reached its clip limit.')
        end=min(30,load(p['info'])['duration']); clip=uid(); ratio=load(p['prefs'])['ratio']
        c.execute('INSERT INTO clips (id,project_id,title,start_at,end_at,insights,edit,created) VALUES(?,?,?,?,?,?,?,?)',
                (clip,id,'Manual clip',0,end,dump({'reason':'Manually selected'}),dump(schema.initial_edit(ratio)),NOW()))
        return clip_json(own_clip(c,clip,me['id']))

@app.get('/api/projects/{id}/analysis')
def analysis(id:schema.Id,me=Depends(require)):
    with db() as c: p=own(c,id,me['id'])
    if p['status']!='ready': err(409,'Wait for analysis to finish.')
    data=media.read_analysis(p)
    return {k:data[k] for k in ('info','words','track','waveform')}

def private(path,mime,filename=None,inline=False):
    if not path.is_file(): err(404,'This file is not available.')
    return FileResponse(path,media_type=mime,filename=filename,content_disposition_type='inline' if inline else 'attachment',headers={'Cache-Control':'private, no-store'})

@app.get('/api/projects/{id}/poster')
def poster(id:schema.Id,me=Depends(require)):
    with db() as c:p=own(c,id,me['id'])
    return private(media.poster_file(p),'image/jpeg')

@app.get('/api/projects/{id}/preview')
def preview(id:schema.Id,me=Depends(require)):
    with db() as c:p=own(c,id,me['id'])
    if p['status']!='ready': err(409,'Preview is still processing.')
    return private(media.preview_file(p),'video/mp4')

@app.get('/api/clips/{id}')
def get_clip(id:schema.Id,me=Depends(require)):
    with db() as c: return clip_json(own_clip(c,id,me['id']))


@app.get('/api/clips/{id}/poster')
def clip_poster(id:schema.Id,me=Depends(require)):
    with db() as c:
        clip=own_clip(c,id,me['id']); p=own(c,clip['project_id'],me['id'])
    key=load(clip['insights'],{}).get('poster_key','')
    f=media.thumb_file(p,key) if re.fullmatch(r'[0-9]+-[0-9]+',key) else None
    return private(f if f and f.is_file() else media.poster_file(p),'image/jpeg')

@app.put('/api/clips/{id}')
def update_clip(id:schema.Id,change:schema.ClipUpdate,me=Depends(require)):
    edit=change.edit.model_dump()
    with db(True) as c:
        clip=own_clip(c,id,me['id']); project=own(c,clip['project_id'],me['id'],True); info=load(project['info'])
        if change.end_at>info['duration']+.001 or not .5<=change.end_at-change.start_at<=180: err(422,'Clip bounds must be between half a second and three minutes, within the source.')
        if sum(b-a for a,b in video.kept_ranges(change.start_at,change.end_at,edit['cuts']))<.5: err(422,'At least half a second of video must remain.')
        if edit['caption']['font_id']: owned_asset(c,edit['caption']['font_id'],me['id'],'font')
        for o in edit['overlays']:
            if o.get('asset'): owned_asset(c,o['asset'],me['id'],'image')
        if any(x['e']>info['duration']+.10 for x in edit['word_edits']): err(422,'Caption timings must be within the source video.')
        cur=c.execute('UPDATE clips SET title=?,start_at=?,end_at=?,edit=?,version=version+1 WHERE id=? AND version=?',
            (change.title,change.start_at,change.end_at,dump(edit),id,change.version))
        if cur.rowcount!=1: err(409,'This clip was changed in another tab. Reload to see the latest version.')
        c.execute('UPDATE projects SET updated=? WHERE id=?',(NOW(),project['id']))
        return clip_json(own_clip(c,id,me['id']))

@app.post('/api/clips/{id}/duplicate',status_code=201)
def duplicate_clip(id:schema.Id,me=Depends(require)):
    with db(True) as c:
        cl=own_clip(c,id,me['id']); p=own(c,cl['project_id'],me['id'],True); new=uid()
        if c.execute('SELECT COUNT(*) AS n FROM clips WHERE project_id=?',(p['id'],)).fetchone()['n']>=65: err(409,'This project has reached its clip limit.')
        c.execute('INSERT INTO clips (id,project_id,title,start_at,end_at,score,insights,edit,created) VALUES(?,?,?,?,?,?,?,?,?)',
            (new,p['id'],(cl['title']+' (copy)')[:120],cl['start_at'],cl['end_at'],cl['score'],cl['insights'],cl['edit'],NOW()))
        return clip_json(own_clip(c,new,me['id']))

@app.delete('/api/clips/{id}',status_code=204)
def delete_clip(id:schema.Id,me=Depends(require)):
    with db(True) as c:
        own_clip(c,id,me['id']); c.execute('DELETE FROM clips WHERE id=?',(id,))

@app.post('/api/clips/{id}/render',status_code=202)
def export_clip(id:schema.Id,options:schema.Render,me=Depends(require)):
    with db(True) as c:
        c.execute('SELECT id FROM users WHERE id=?'+lock_suffix(),(me['id'],)).fetchone()
        clip=clip_json(own_clip(c,id,me['id']))
        waiting=c.execute("SELECT COUNT(*) AS n FROM jobs WHERE user_id=? AND kind='render' AND status IN ('queued','running')",(me['id'],)).fetchone()['n']
        if waiting>=8: err(429,'You have eight renders in the queue. Wait for one to finish.')
        total=c.execute("SELECT COUNT(*) AS n FROM jobs WHERE user_id=? AND kind='render'",(me['id'],)).fetchone()['n']
        if total>=240: err(429,'Delete old renders from Export Center before starting another.')
        j=enqueue(c,me['id'],clip['project_id'],'render',{'clip':clip,'options':options.model_dump()},id)
        return {'id':j}

@app.get('/api/jobs')
def jobs(me=Depends(require),kind:str=Query('render',pattern='^(analyze|render|regenerate)$')):
    with db() as c:
        return [store.public_job(x) for x in c.execute("SELECT * FROM jobs WHERE (user_id=? OR status='done') AND kind=? ORDER BY created DESC LIMIT 240",(me['id'],kind)).fetchall()]

def own_job(c,id,me):
    row=c.execute("SELECT * FROM jobs WHERE id=? AND (user_id=? OR status='done')",(id,me['id'])).fetchone()
    if not row: err(404,'Job not found.')
    return dict(row)

@app.get('/api/jobs/{id}')
def get_job(id:schema.Id,me=Depends(require)):
    with db() as c: return store.public_job(own_job(c,id,me))

@app.post('/api/jobs/{id}/retry',status_code=202)
def retry(id:schema.Id,me=Depends(require)):
    with db(True) as c:
        job=own_job(c,id,me)
        if not c.execute("UPDATE jobs SET status='queued',progress=0,attempts=0,worker=NULL,lease=NULL,stage='Waiting for a worker',error=NULL,updated=? WHERE id=? AND status='failed'",(NOW(),id)).rowcount: err(409,'Only failed jobs can be retried.')
        if job['kind']=='analyze': c.execute("UPDATE projects SET status='queued',updated=? WHERE id=?",(NOW(),job['project_id']))
        return {'id':id}

@app.delete('/api/jobs/{id}',status_code=204)
def delete_export(id:schema.Id,me=Depends(require)):
    with db(True) as c:
        job=own_job(c,id,me)
        if job['kind']!='render': err(409,'Only exports can be removed here.')
        if job['status']=='running': err(409,'Wait for the render to finish before removing it.')
        c.execute('DELETE FROM jobs WHERE id=?',(id,))
    shutil.rmtree(media.export_dir(id),ignore_errors=True)

@app.get('/api/jobs/{id}/download')
def download(id:schema.Id,me=Depends(require),format:str=Query('mp4',pattern='^(mp4|srt)$'), inline:bool=False):
    with db() as c: job=own_job(c,id,me)
    if job['kind']!='render' or job['status']!='done': err(409,'Export is not ready.')
    title=re.sub(r'[^\w.-]+','-',load(job['output'],{}).get('title','cutroom-clip')).strip('-.')[:95] or 'cutroom-clip'
    return private(media.export_dir(id)/('clip.mp4' if format=='mp4' else 'captions.srt'),'video/mp4' if format=='mp4' else 'application/x-subrip',title+'.'+format,inline)

@app.get('/api/assets')
def list_assets(me=Depends(require)):
    with db() as c:
        return [asset_json(r) for r in c.execute('SELECT * FROM assets WHERE user_id=? ORDER BY created DESC',(me['id'],)).fetchall()]

def asset_json(a): return {k:a[k] for k in ('id','kind','name')}|{'details':load(a['details']), 'url':f"/api/assets/{a['id']}"}

@app.post('/api/assets',status_code=201)
async def assets(req:Request,me=Depends(require),kind:str=Query(...,pattern='^(image|font)$'),name:str=Query(...,max_length=160)):
    from PIL import Image
    from fontTools.ttLib import TTFont
    contents=await req.body()
    if not contents or len(contents)>8*1024**2: err(413,'Assets must be smaller than 8 MB.')
    id=uid(); path=config.MEDIA/'assets'/me['id']; path.mkdir(mode=0o700,parents=True,exist_ok=True)
    try:
        if kind=='image':
            with Image.open(io.BytesIO(contents)) as image:
                if image.format not in ('JPEG','PNG','WEBP') or image.width*image.height>16_000_000: err(422,'Choose a JPEG, PNG, or WebP image up to 16 megapixels.')
                image.thumbnail((1920,1920)); img=image.convert('RGBA'); file=path/(id+'.png'); img.save(file,optimize=True)
                details={'w':img.width,'h':img.height,'ext':'png'}
        else:
            head=contents[:4]
            if head not in (b'OTTO', b'\x00\x01\x00\x00'): err(422,'Choose a TTF or OTF font.')
            ext='otf' if head==b'OTTO' else 'ttf'; file=path/(id+'.'+ext)
            with TTFont(io.BytesIO(contents),lazy=False) as font:
                family=font['name'].getBestFamilyName()
                if not family or not re.fullmatch(r"[\w -]{1,72}",family): err(422,'Font family name contains unsupported characters.')
                # Serialize parsed tables; never allow a font name to become filter syntax.
                font.save(file)
            details={'family':family,'ext':ext}
        with db(True) as c:
            c.execute('SELECT id FROM users WHERE id=?'+lock_suffix(),(me['id'],)).fetchone()
            if c.execute('SELECT COUNT(*) AS n FROM assets WHERE user_id=?',(me['id'],)).fetchone()['n']>=50: err(409,'Workspace has reached its asset limit.')
            c.execute('INSERT INTO assets (id,user_id,kind,name,path,details,created) VALUES(?,?,?,?,?,?,?)',(id,me['id'],kind,simple_filename(name),str(file),dump(details),NOW()))
            return asset_json(c.execute('SELECT * FROM assets WHERE id=?',(id,)).fetchone())
    except HTTPException:
        if 'file' in locals(): file.unlink(missing_ok=True)
        raise
    except Exception:
        if 'file' in locals(): file.unlink(missing_ok=True)
        err(422,'The asset could not be read. Check the file format and try again.')

@app.get('/api/assets/{id}')
def get_asset(id:schema.Id,me=Depends(require)):
    from pathlib import Path
    with db() as c: r=owned_asset(c,id,me['id'])
    ext=load(r['details'])['ext']; return private(Path(r['path']),{'png':'image/png','ttf':'font/ttf','otf':'font/otf'}[ext])

@app.get('/api/presets')
def get_presets(): return schema.PRESETS

@app.get('/api/brands')
def brands(me=Depends(require)):
    with db() as c: return [load(r['data'])|{'id':r['id']} for r in c.execute('SELECT * FROM brands WHERE user_id=? ORDER BY created DESC',(me['id'],)).fetchall()]

def save_brand(c,id,data,me,update=False):
    if data.logo: owned_asset(c,data.logo,me['id'],'image')
    if data.caption.font_id: owned_asset(c,data.caption.font_id,me['id'],'font')
    item=data.model_dump()
    if update:
        if not c.execute('UPDATE brands SET name=?,data=? WHERE id=? AND user_id=?',(data.name,dump(item),id,me['id'])).rowcount: err(404,'Brand kit not found.')
    else:
        if c.execute('SELECT COUNT(*) AS n FROM brands WHERE user_id=?',(me['id'],)).fetchone()['n']>=20: err(409,'Workspace has reached its brand kit limit.')
        c.execute('INSERT INTO brands (id,user_id,name,data,created) VALUES(?,?,?,?,?)',(id,me['id'],data.name,dump(item),NOW()))
    return item|{'id':id}

@app.post('/api/brands',status_code=201)
def add_brand(data:schema.Brand,me=Depends(require)):
    with db(True) as c: return save_brand(c,uid(),data,me)

@app.put('/api/brands/{id}')
def edit_brand(id:schema.Id,data:schema.Brand,me=Depends(require)):
    with db(True) as c: return save_brand(c,id,data,me,True)

@app.delete('/api/brands/{id}',status_code=204)
def remove_brand(id:schema.Id,me=Depends(require)):
    with db(True) as c:
        if not c.execute('DELETE FROM brands WHERE id=? AND user_id=?',(id,me['id'])).rowcount: err(404,'Brand kit not found.')


def stripe_api(method,path,data=None):
    import httpx
    if not (config.STRIPE_SECRET and config.STRIPE_PRICE and config.STRIPE_WEBHOOK): err(503,'Stripe billing is not configured on this instance.')
    try:
        r=httpx.request(method,'https://api.stripe.com/v1/'+path,data=data,auth=(config.STRIPE_SECRET,''),timeout=15); r.raise_for_status(); return r.json()
    except Exception:
        LOG.warning('stripe_request_failed path=%s',path.split('/')[0]); err(502,'Billing service is temporarily unavailable.')

def billing_origin(req):
    if not config.PUBLIC_ORIGIN: err(503,'Billing requires an operator-configured public origin.')
    return config.PUBLIC_ORIGIN

@app.post('/api/billing/checkout')
def checkout(req:Request,me=Depends(require)):
    if me['email'] is None: err(403,'Create an account before subscribing.')
    if me['plan']=='Studio': err(409,'You already have the Studio plan.')
    rate(req,'billing',me['id'],6,300); url=billing_origin(req)
    args={'mode':'subscription','line_items[0][price]':config.STRIPE_PRICE,'line_items[0][quantity]':'1','client_reference_id':me['id'],
          'subscription_data[metadata][cutroom_user]':me['id'],'success_url':url+'/#settings?billing=return','cancel_url':url+'/#settings'}
    args.update({'customer':me['stripe_id']} if me['stripe_id'] else {'customer_email':me['email']})
    return {'url':stripe_api('POST','checkout/sessions',args)['url']}

@app.post('/api/billing/portal')
def portal(req:Request,me=Depends(require)):
    if not me['stripe_id']: err(404,'No billing subscription is connected.')
    rate(req,'billing',me['id'],6,300); url=billing_origin(req)
    return {'url':stripe_api('POST','billing_portal/sessions',{'customer':me['stripe_id'],'return_url':url+'/#settings'})['url']}

@app.post('/api/billing/webhook')
async def webhooks(req:Request):
    if not config.STRIPE_WEBHOOK: err(503,'Stripe billing is not configured.')
    raw=await req.body(); parts=req.headers.get('stripe-signature','').split(',')
    try:
        t=next(int(s[2:]) for s in parts if s.startswith('t=')); sig=hmac.new(config.STRIPE_WEBHOOK.encode(),str(t).encode()+b'.'+raw,hashlib.sha256).hexdigest()
        if abs(NOW()-t)>300 or not any(hmac.compare_digest(s[3:],sig) for s in parts if s.startswith('v1=')): err(401,'Invalid Stripe signature.')
        event=json.loads(raw); data=event['data']['object']; id=event['id']; typ=event['type']
    except (ValueError,StopIteration,KeyError,TypeError): err(400,'Invalid Stripe event.')
    if typ in ('customer.subscription.created','customer.subscription.updated','customer.subscription.deleted'):
        owner=data.get('metadata',{}).get('cutroom_user',''); customer=data.get('customer'); status=data.get('status')
        # Retrieve current state so a delayed notification cannot reinstate outdated entitlement.
        current=stripe_api('GET','subscriptions/'+data['id']) if typ!='customer.subscription.deleted' else data
        matches=any(i.get('price',{}).get('id')==config.STRIPE_PRICE for i in current.get('items',{}).get('data',[]))
        plan='Studio' if matches and current.get('status',status) in ('active','trialing') and typ!='customer.subscription.deleted' else 'Creator'
        if re.fullmatch(r'[a-f0-9]{32}',owner) and isinstance(customer,str):
            with db(True) as c:
                result=c.execute('INSERT INTO webhook_events (id,created) VALUES(?,?) ON CONFLICT(id) DO NOTHING',(id,NOW()))
                if result.rowcount: c.execute('UPDATE users SET plan=?,stripe_id=? WHERE id=? AND email IS NOT NULL',(plan,customer,owner))
    return {'received':True}

@app.get('/healthz')
def health():
    with db() as c: c.execute('SELECT 1').fetchone()
    return {'status':'ok','ffmpeg':bool(shutil.which(config.FFMPEG)),'database':'postgres' if store.POSTGRES else 'sqlite'}

@app.get('/readyz')
def readiness():
    with db() as c: workers=c.execute('SELECT COUNT(*) AS n FROM workers WHERE seen>?',(NOW()-50,)).fetchone()['n']
    ready=bool(workers) and bool(shutil.which(config.FFMPEG))
    return JSONResponse({'status':'ready' if ready else 'not_ready','workers':workers},status_code=200 if ready else 503)

@app.get('/metrics',include_in_schema=False)
def metrics():
    if os.environ.get('CUTROOM_METRICS_ENABLED')!='1': err(404,'Metrics are disabled.')
    with db() as c:
        states=c.execute('SELECT kind,status,COUNT(*) AS n FROM jobs GROUP BY kind,status').fetchall()
        workers=c.execute('SELECT COUNT(*) AS n FROM workers WHERE seen>?',(NOW()-50,)).fetchone()['n']
    disk=shutil.disk_usage(config.DATA)
    out=['# TYPE cutroom_workers gauge',f'cutroom_workers {workers}','# TYPE cutroom_media_disk_free_bytes gauge',f'cutroom_media_disk_free_bytes {disk.free}','# TYPE cutroom_jobs gauge']
    out+= [f'cutroom_jobs{{kind="{x["kind"]}",status="{x["status"]}"}} {x["n"]}' for x in states]
    return PlainTextResponse('\n'.join(out)+'\n',media_type='text/plain; version=0.0.4')

app.mount('/assets',StaticFiles(directory=config.ROOT/'web'/'assets'),name='assets')

@app.get('/')
@app.get('/landing')
def index():
    landing = config.ROOT/'web'/'landing.html'
    target = landing if landing.exists() else config.ROOT/'web'/'index.html'
    return FileResponse(target,media_type='text/html',headers={'Cache-Control':'no-cache'})

@app.get('/studio')
@app.get('/studio/')
@app.get('/app')
@app.get('/app/')
def studio():
    return FileResponse(config.ROOT/'web'/'index.html',media_type='text/html',headers={'Cache-Control':'no-cache'})

