"""Reproduce the scoped REA evidence passes. Uses no target bundles, accounts or private APIs."""
import argparse, json, os, pathlib, subprocess, urllib.request

PUBLIC={
 'opus-home':'https://www.opus.pro/',
 'opus-results':'https://help.opus.pro/docs/article/get-clips-faq-1',
 'opus-score':'https://help.opus.pro/docs/article/virality-score',
 'opus-reframe':'https://help.opus.pro/docs/article/subject-tracking',
 'opus-editor':'https://help.opus.pro/docs/article/captions-and-emojis',
}

def scenario(url,chromium,actions):
    return {'browser':{'mode':'launch','executable_path':chromium},'start_url':{'url':url},'command_timeout_ms':16000,
            'actions':actions,'capture':{'at_end':['accessibility','url']}}

def click(id,selector):
    return {'step_id':id,'action':'click','locator':{'kind':'css','selector':selector},'timeout_ms':9000}

def capture(rea,out,name,value):
    p=out/(name+'.scenario.json');p.write_text(json.dumps(value,indent=2))
    subprocess.run([rea,'validate-browser-scenario',str(p),'--format','json'],check=True)
    raw=subprocess.check_output([rea,'capture-browser-scenario',str(p),'--format','json'],timeout=47)
    (out/(name+'.evidence.json')).write_bytes(raw)
    d=json.loads(raw); steps=[(s['step_id'],s['status']) for s in d['normalized_result']['steps']]
    print(d['evidence_id'],name,steps,flush=True)
    if any(s!='completed' for _,s in steps): raise RuntimeError(f'{name}: REA found a failed browser step')

def main():
    p=argparse.ArgumentParser();p.add_argument('--rea',default='rea');p.add_argument('--browser',required=True);p.add_argument('--base',default='http://127.0.0.1:3000');p.add_argument('--out',type=pathlib.Path,default=pathlib.Path('.cache/rea-audit'));p.add_argument('--public',action='store_true');p.add_argument('--public-only',action='store_true'); a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    if a.public or a.public_only:
        for name,url in PUBLIC.items(): capture(a.rea,a.out,name,scenario(url,a.browser,[{'step_id':'observe-public-ui','action':'wait_for_timeout','duration_ms':500}]))
    if a.public_only: return
    url=a.base.rstrip('/')
    op=a.out/'cutroom-openapi.json';op.write_bytes(urllib.request.urlopen(url+'/api/openapi.json',timeout=10).read())
    dest=a.out/'cutroom-api.evidence.json';dest.unlink(missing_ok=True)
    subprocess.run([a.rea,'inspect-api-contract',str(op),'--detail','summary','--evidence_output',str(dest),'--format','json'],check=True,stdout=subprocess.DEVNULL,timeout=30)
    steps=[click('open-sample','button.thumb[data-action="sample"][data-id="lunar"]'),click('open-editor','.clip-card:first-child .btn[data-action="edit-clip"]'),click('layout','#player-ratios button[data-value="1:1"]'),click('save','[data-ed="save"]'),{'step_id':'saved','action':'wait_for','locator':{'kind':'css','selector':'.toast:has-text("Clip edits saved")'},'state':'visible','timeout_ms':8000}]
    capture(a.rea,a.out,'cutroom-edit-and-save',scenario(url+'/',a.browser,steps))

if __name__=='__main__': main()
