"""End-to-end smoke test against a running API AND worker. Uses actual bundled video."""
import argparse, json, subprocess, tempfile, time, uuid
from pathlib import Path
import httpx

ROOT=Path(__file__).resolve().parents[1]

def ok(r):
    assert r.is_success,(r.request.method,str(r.request.url),r.status_code,r.text[:700]); return r.json()

def until(client,path,test,timeout=230):
    deadline=time.monotonic()+timeout; progress=None
    while time.monotonic()<deadline:
        x=ok(client.get(path)); status= x.get('job') or x
        if (status.get('stage'),status.get('progress'))!=progress:
            progress=(status.get('stage'),status.get('progress')); print('  ',status.get('status'),*progress,flush=True)
        if status.get('status')=='failed': raise AssertionError(status.get('error'))
        if test(x): return x
        time.sleep(1.2)
    raise AssertionError(f'Timed out waiting for {path}')

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--base-url',default='http://127.0.0.1:3000'); ap.add_argument('--output-dir'); args=ap.parse_args()
    with httpx.Client(base_url=args.base_url,timeout=40) as a,httpx.Client(base_url=args.base_url,timeout=40) as b,tempfile.TemporaryDirectory() as td:
        root=Path(args.output_dir or td); root.mkdir(parents=True,exist_ok=True)
        account={'name':'Workflow QA','email':f'qa-{uuid.uuid4().hex[:10]}@example.test','password':'real-workflow-QA-8722'}
        user=ok(a.post('/api/auth/register',json=account)); assert user['email']==account['email'] and not user['guest']
        filename=ROOT/'samples'/'path.mp4'; video=filename.read_bytes()
        p=ok(a.post('/api/projects',json={'title':'QA full source','filename':filename.name,'bytes':len(video),'prefs':{'length':'short','ratio':'9:16','count':5}})); pth='/api/projects/'+p['id']
        assert p['status']=='uploading'; chunk=1024**2; part=video[:chunk]
        assert a.patch(pth+'/upload',content=part,headers={'Content-Type':'application/octet-stream','Upload-Offset':'40'}).status_code==409
        assert ok(a.patch(pth+'/upload',content=part,headers={'Content-Type':'application/octet-stream','Upload-Offset':'0'}))['offset']==len(part)
        # Simulate upload disconnect/reconnect: a new HTTP client resumes using the saved session and offset.
        assert b.get(pth).status_code==401
        assert a.post('/api/auth/logout').status_code==204
        assert a.get(pth).status_code==401
        ok(a.post('/api/auth/login',json=account)); p=ok(a.get(pth)); assert p['received']==len(part)
        for index in range(len(part),len(video),chunk):
            size=min(len(video),index+chunk)
            assert ok(a.patch(pth+'/upload',content=video[index:size],headers={'Content-Type':'application/octet-stream','Upload-Offset':str(index)}))['offset']==size
        assert a.get(pth+'/preview').status_code==409
        ok(a.post(pth+'/start')); print('Uploaded',len(video),'bytes. Waiting for real models…',flush=True)
        p=until(a,pth,lambda x:x['status']=='ready'); assert len(p['clips'])>=3 and p['info']['duration']>180, p['info']
        assert p['info']['face_frames']>10 and p['info']['speakers']>=1
        analysis=ok(a.get(pth+'/analysis')); words=analysis['words']; assert len(words)>280 and len(analysis['track'])>100
        assert all(x['s']<x['e'] and x['t'] for x in words)
        rr=a.get(pth+'/preview',headers={'Range':'bytes=100-899'}); assert rr.status_code==206 and len(rr.content)==800
        other=ok(b.post('/api/auth/guest')); assert other['id']!=user['id']; assert b.get(pth+'/preview').status_code==404
        clip=p['clips'][0]; clip_uri='/api/clips/'+clip['id']; assert b.get(clip_uri).status_code==404
        assert clip['score'] and len(clip['insights']['axes'])==9
        assert len({(x['start_at'],x['end_at']) for x in p['clips']})==len(p['clips'])
        editable={k:clip[k] for k in ('title','start_at','end_at','edit','version')}
        editable.update(title='QA — changed caption and overlays',start_at=clip['start_at']+.35,end_at=min(clip['end_at'],clip['start_at']+13.8))
        edited=editable['edit']; edited['ratio']='4:5'; edited['framing']='track'; edited['fade']=.25
        w=next(x for x in words if editable['start_at']+.4<x['s']<editable['end_at']-.5)
        edited['word_edits']=[{k:w[k] for k in ('i','s','e')}|{'t':'VERIFIED'}]
        edited['overlays']=[{'type':'text','text':'Real export verified','x':.5,'y':.17,'color':'#eee088','size':74}]
        # Reuse the real project photo as an uploaded logo layer; import as checked PNG on the server.
        picture=(ROOT/'samples'/'galaxies.jpg').read_bytes()
        asset=ok(a.post('/api/assets',params={'kind':'image','name':'logo.jpg'},content=picture,headers={'Content-Type':'application/octet-stream'}));
        assert b.get(asset['url']).status_code==422
        edited['overlays'].append({'type':'image','asset':asset['id'],'x':.82,'y':.90,'width':.16,'start':round(editable['start_at']+1,3)})
        edited['cuts']=[{'s':round(editable['start_at']+4.1,3),'e':round(editable['start_at']+4.6,3)}]
        saved=ok(a.put(clip_uri,json=editable)); assert saved['version']==editable['version']+1
        assert a.put(clip_uri,json=editable).status_code==409
        first=ok(a.post(clip_uri+'/render',json={'resolution':720,'quality':'standard'})); job_uri='/api/jobs/'+first['id']; print('Rendering server-side…',flush=True)
        j=until(a,job_uri,lambda p:p['status']=='done',timeout=150)
        assert j['output']['width']==720 and j['output']['height']==900
        mp4=a.get(job_uri+'/download'); assert mp4.is_success and mp4.headers['content-type']=='video/mp4'
        result=root/'verified-clip.mp4';result.write_bytes(mp4.content)
        srt=a.get(job_uri+'/download?format=srt'); assert srt.is_success and 'VERIFIED' in srt.text
        (root/'captions.srt').write_text(srt.text)
        parsed=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',result])); count={x['codec_type']:x for x in parsed['streams']}
        assert count['video']['codec_name']=='h264' and count['audio']['codec_name']=='aac'
        assert abs(float(parsed['format']['duration'])-j['output']['duration'])<.13
        assert abs(float(count['video']['duration'])-float(count['audio']['duration']))<.1
        assert a.post('/api/auth/logout').status_code==204 and a.get(job_uri+'/download').status_code==401
        ok(a.post('/api/auth/login',json=account)); assert ok(a.get(clip_uri))['title']==saved['title']; assert a.get(job_uri+'/download',headers={'Range':'bytes=0-127'}).status_code==206
        assert ok(a.get('/api/usage'))['seconds']>180
        evidence={k:p['info'][k] for k in ('duration','face_frames','speakers','scene_changes','language')}
        evidence.update(clip_count=len(p['clips']),word_count=len(words),output=j['output'],codec=count['video']['codec_name'],audio=count['audio']['codec_name'],ffprobe_duration=float(parsed['format']['duration']))
        (root/'e2e-result.json').write_text(json.dumps(evidence,indent=2));print(json.dumps(evidence,indent=2),flush=True)
        assert a.delete(pth).status_code==204

if __name__=='__main__': main()
