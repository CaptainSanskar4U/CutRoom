import {ico,$,$$,esc,clone,clamp,time,date,size,option,btn,iconBtn,blank,spinner,go,ratios,languages,durationChoices,durationLabel,capNames,layoutChoices,subtitleLanguages,api,sendAsset,chunk,modal,closeModal,toast,formError,action,copy,progress} from './ui.js';
import {openEditor} from './editor.js';

const view=$('#view'),sidebar=$('#sidebar'),top=$('#topbar');
const state={me:null,config:{max_bytes:2147483648,chunk_bytes:5242880,guest:true,import_hosts:[]},use:null,samples:[],projects:[],brands:[],assets:[],presets:{},jobs:[],screen:'home',id:'',project:null,editor:null,upload:null,ready:false,mobile:false,search:'',filter:'all',sort:'recent',layout:'grid',clipSort:'score',counter:0,polling:false,pending:null};
const navs=[['home','home','Clipping studio'],['projects','folder','Projects'],['brand','palette','Brand kits'],['exports','download','Export center'],['settings','settings','Settings']];
const axes={hook:'Opening hook',engagement:'Engagement',completeness:'Completeness',emotion:'Expressiveness',density:'Information',independence:'Independence',confidence:'Speech quality',duration:'Length fit',ending:'Ending'};
const statuses={uploading:['Uploading','amber'],queued:['Queued','violet'],processing:['Processing','violet'],ready:['Ready','green'],failed:['Attention','red'],done:['Ready','green'],running:['Rendering','violet']};
const statusBadge=(s,dot=true)=>{const d=statuses[s]||[s,'violet'];return `<span class="badge ${d[1]}">${dot?'<i></i>':''}${esc(d[0])}</span>`;};
const act=(name,extra='')=>`data-action="${name}" ${extra}`;
const who=()=>state.me?.name||'Guest creator';
const plan=()=>state.me?.plan||'Guest';
const minute=x=>x<60?(x>0?'<1':'0'):String(Math.floor(x/60));
const ratiosOpts=r=>ratios.map(x=>option(x,x,r)).join('');
const langOpts=l=>Object.entries(languages).map(([k,v])=>option(k,v,l)).join('');
const layoutOpts=l=>Object.entries(layoutChoices).map(([k,v])=>option(k,v,l)).join('');
const subLangOpts=l=>Object.entries(subtitleLanguages).map(([k,v])=>option(k,v,l)).join('');
const capOpts=p=>Object.entries(capNames).map(([k,v])=>option(k,v,p)).join('');
let lastUiKey='', editorRouteBack='';

function chrome(){
 const k=state.screen==='project'||state.screen==='edit'?'projects':state.screen;
 const p=state.use||{seconds:0,limit:1800};
 sidebar.innerHTML=`<a class="logo" href="#home" aria-label="Cutroom home"><img src="/assets/mark.svg" alt=""><strong class="logo-word">Cutroom<i>.</i></strong></a>
 <div class="workspace-label"><span>${ico('layers',13)}</span><span>Personal workspace</span></div>
 <nav class="nav"><div class="nav-group"><h2 class="nav-group-title">WORKSPACE</h2>${navs.slice(0,4).map(([id,icon,label])=>`<a href="#${id}" class="nav-item ${k===id?'active':''}" ${k===id?'aria-current="page"':''}>${ico(icon,17)}<span>${label}</span></a>`).join('')}</div><div class="nav-group"><h2 class="nav-group-title">PREFERENCES</h2><a href="#settings" class="nav-item ${k==='settings'?'active':''}" ${k==='settings'?'aria-current="page"':''}>${ico('settings',17)}<span>Settings</span></a><button class="nav-item" ${act('help')}>${ico('help',17)}<span>Help &amp; shortcuts</span></button></div></nav>
 <div class="sidebar-foot"><a class="usage-widget" href="#settings" title="Manage usage"><div class="usage-head">${ico('bolt',14)} Processing allowance</div>${progress(Math.round(p.seconds/p.limit*100))}<div class="spread"><span class="muted">${minute(p.seconds)} / ${Math.round(p.limit/60)} min used</span><span class="purple-link">View usage ${ico('chevron',11)}</span></div></a>
 <button type="button" class="profile" ${act('profile')}><span class="avatar">${esc(who().split(/\s+/).slice(0,2).map(x=>x[0]).join('').toUpperCase())}</span><span class="profile-meta"><span class="profile-name">${esc(who())}</span><span class="profile-sub">${state.me?.email?`${esc(plan())} workspace`:'Local guest workspace'}</span></span>${ico('down',14)}</button></div>`;
 sidebar.classList.toggle('open',state.mobile);
 let label=navs.find(x=>x[0]===k)?.[2]||'Workspace', info=`<span>Workspace</span>${ico('chevron',13)}<b>${label}</b>`;
 if(state.screen==='project')info=`<a href="#projects">Projects</a>${ico('chevron',13)}<b>${esc(state.project?.title||'Project')}</b>`;
 if(state.screen==='edit')info=`<a href="#projects">Projects</a>${ico('chevron',13)}<a href="${editorRouteBack||'#projects'}">${esc(state.project?.title||'Project')}</a>${ico('chevron',13)}<b>Clip editor</b>`;
 top.innerHTML=`<div class="crumb"><button class="icon-btn mobile-menu" ${act('mobile')} aria-label="Open navigation">${ico('menu')}</button>${ico('layers',15)}${info}</div><div class="actions"><button type="button" class="icon-btn top-help" aria-label="Help" title="Help" ${act('help')}>${ico('help',17)}</button>${btn('New project','plus',{kind:'primary',attrs:act('new')})}</div>`;
 document.title=`Cutroom — ${state.screen==='edit'?'Clip editor':label}`;
}
function mobile(open){state.mobile=open;sidebar.classList.toggle('open',open);$('#mobile-shade').hidden=!open;}
function header(eyebrow,title,body,extra=''){return `<div class="page-head"><div><p class="eyebrow section-mark">${esc(eyebrow)}</p><h1>${esc(title)}</h1><p>${esc(body)}</p></div><div class="actions">${extra}</div></div>`;}

function home(){
 view.innerHTML=`<div class="intro spread"><div><p class="eyebrow section-mark">CREATOR WORKSPACE</p><h1>Clipping studio</h1><p>Find the moments worth sharing. Cutroom handles the rough cut.</p></div></div>
 <section class="hero" id="quick-drop" aria-labelledby="hero-title"><div class="hero-main"><span class="hero-label">${ico('sparkle',14)} AI clip generator</span><h2 id="hero-title">Long videos.<br><span>Standout shorts.</span></h2><p>Find highlights, add animated captions, and reframe for any feed — from one video.</p>
 <form id="quick-url" class="quick-url"><label class="url-field">${ico('link',16)}<span class="sr-only">Direct video URL</span><input name="url" placeholder="Paste a direct video link…" autocomplete="off" inputmode="url" maxlength="2400"></label><button class="btn primary" type="submit">${ico('sparkle',16)}<span>Generate clips</span></button></form>
 <div class="under-hero"><span>or</span>${btn('Upload video','upload',{kind:'upload-btn',attrs:act('new')})}<span class="hero-note">MP4, MOV, WebM · up to ${size(state.config.max_bytes)}</span></div></div>
 <div class="hero-art" aria-hidden="true"><svg class="art-rings" viewBox="0 0 400 270" fill="none"><ellipse cx="200" cy="135" rx="185" ry="79" transform="rotate(-25 200 135)" stroke="currentColor" stroke-dasharray="4 5"/><ellipse cx="200" cy="135" rx="190" ry="98" transform="rotate(26 200 135)" stroke="currentColor" stroke-opacity=".65"/><circle cx="339" cy="84" r="3" fill="currentColor"/><circle cx="95" cy="228" r="3.5" fill="currentColor"/></svg>
 <span class="art-rays">${ico('sparkle',28)}</span><span class="art-rays two">${ico('sparkle',18)}</span><span class="art-rays three">${ico('sparkle',14)}</span>
 <span class="art-tag start">${ico('film',12)} SOURCE FOOTAGE</span><div class="art-source"><img src="/assets/studio-portrait.jpg" alt=""><span class="art-play">${ico('play',15)}</span><span class="time-chip">18:42</span></div>
 <div class="art-output"><img src="/assets/studio-portrait.jpg" alt=""><span class="art-ratio">9:16</span><span class="art-caption">THIS CHANGES<br><strong>EVERYTHING.</strong></span></div><div class="art-tag end">${ico('sparkle',12)} AI REFRAME</div></div></section>
 <section class="project-section" aria-labelledby="recent-heading"><div class="section-head"><div><h2 id="recent-heading">Recent projects</h2><p>${state.projects.length?'Continue editing your latest videos.':'Start with a real example, or bring your own video.'}</p></div><div class="actions"><label class="search">${ico('search',16)}<span class="sr-only">Search projects</span><input id="project-search" placeholder="Search projects" value="${esc(state.search)}"></label>${btn('View all','arrow',{tag:'a',attrs:'href="#projects"'})}</div></div><div id="project-cards"></div></section>
 <footer class="home-foot"><span class="row">${ico('book',14)} <button type="button" class="linkish" ${act('help')}>New to Cutroom?</button><span> See how your first cut comes together.</span></span><span>Cutroom Studio · creator tools</span></footer>`;
 const q=$('#quick-url',view);q.onsubmit=e=>{e.preventDefault();newProject({url:q.elements.url.value.trim()});};
 $('#project-search',view).oninput=e=>{state.search=e.target.value;fillCards(true);};
 const hero=$('#quick-drop',view);hero.ondragover=e=>{if(e.dataTransfer.types.includes('Files')){e.preventDefault();hero.classList.add('is-drop');}};hero.ondragleave=()=>hero.classList.remove('is-drop');hero.ondrop=e=>{if(e.dataTransfer.files.length){e.preventDefault();hero.classList.remove('is-drop');newProject({file:e.dataTransfer.files[0]});}};
 fillCards(true);
}

function projectCard(p,sample=false){
 const id=esc(p.id),name=esc(p.title),poster=esc(p.poster||''), dur=sample?p.duration:p.info?.duration;
 const a=act(sample?'sample':'open-project',`data-id="${id}"`);
 return `<article class="card project-card"><button type="button" class="thumb ${poster?'':'blank-thumb'}" ${a} aria-label="Open ${name}">${poster?`<img src="${poster}" alt="" loading="eager">`:`<span class="thumb-symbol">${ico(p.status==='processing'?'sparkle':'film',25)}</span>`}${sample||p.sample?'<span class="sample-tag">Sample</span>':''}${dur?`<span class="time-chip">${time(dur)}</span>`:''}${poster?`<span class="clip-play">${ico('play',17)}</span>`:''}</button>
 <div class="card-body"><div class="card-top"><button class="card-title" type="button" ${a}>${name}</button>${iconBtn(sample?'About this sample':'Project actions',sample?'info':'dots',act(sample?'sample-info':'project-menu',`data-id="${id}"`))}</div><div class="card-meta">${ico('film',12)} ${p.clip_count} ${p.clip_count===1?'clip':'clips'} <span class="divider-dot">·</span> ${sample?esc(p.type):p.sample?'Sample project':date(p.updated)} ${sample?'':`<span class="divider-dot">·</span>${statusBadge(p.status)}`}</div></div></article>`;
}
function projectsPage(){
 view.innerHTML=header('LIBRARY','Projects','Search, organize, and revisit your source videos.',btn('New project','plus',{kind:'primary',attrs:act('new')}))+
 `<div class="filters"><label class="search">${ico('search',16)}<span class="sr-only">Search projects</span><input id="project-search" placeholder="Search projects" value="${esc(state.search)}"></label><select class="filter-select" id="project-filter" aria-label="Project status">${['all','ready','processing','uploading','failed','sample'].map(x=>option(x,{all:'All statuses',ready:'Ready',processing:'Processing',uploading:'Uploading',failed:'Needs attention',sample:'Examples'}[x],state.filter)).join('')}</select><select class="filter-select" id="project-sort" aria-label="Sort projects">${option('recent','Most recent',state.sort)}${option('name','Project name',state.sort)}</select><div class="segmented" aria-label="Project layout">${['grid','list'].map(x=>`<button type="button" class="${state.layout===x?'selected':''}" ${act('layout',`data-id="${x}"`)} aria-label="${x} view" aria-pressed="${state.layout===x}">${ico(x,15)}</button>`).join('')}</div></div><div id="project-cards"></div>`;
 $('#project-search').oninput=e=>{state.search=e.target.value;fillCards(false);};$('#project-filter').onchange=e=>{state.filter=e.target.value;fillCards(false);};$('#project-sort').onchange=e=>{state.sort=e.target.value;fillCards(false);};fillCards(false);
}
function fillCards(recent){
 const container=$('#project-cards',view);if(!container)return;
 const search=state.search.toLowerCase(); const match=x=>x.title.toLowerCase().includes(search);
 let list=state.projects.filter(match);if(!recent&&state.filter!=='all')list=list.filter(x=>state.filter==='sample'?Boolean(x.sample):state.filter==='processing'?['processing','queued'].includes(x.status):x.status===state.filter);
 if(!recent&&state.sort==='name')list.sort((a,b)=>a.title.localeCompare(b.title));
 const samples=state.samples.filter(match).filter(s=>!state.projects.some(p=>p.sample===s.id));
 const showSamples=(recent||['all','sample'].includes(state.filter));
 const all=recent?[...list.map(p=>projectCard(p)),...(showSamples?samples.map(p=>projectCard(p,true)):[])].slice(0,3):list.map(p=>projectCard(p));
 if(!state.ready){container.innerHTML=spinner('Loading workspace…');return;}
 const klass=`cards ${!recent&&state.layout==='list'?'list-view':''}`;
 container.innerHTML=(all.length?`<div class="${klass}">${all.join('')}</div>`:!recent&&showSamples&&samples.length?'':blank(search?'search':'folder',search?'No matches':'No projects here yet',search?'Try another search or change the status filter.':'Upload a source to generate your first set of clips.',search?'':btn('Create a project','plus',{kind:'primary',attrs:act('new')})))+
 (!recent&&showSamples&&samples.length?`<div class="project-section"><div class="section-head"><div><h2>Sample library <span class="badge violet">Try it</span></h2><p>Real video, real transcripts, and editable cuts. No processing minutes used.</p></div></div><div class="${klass}">${samples.map(p=>projectCard(p,true)).join('')}</div></div>`:'');
}

async function loadProjects(){state.projects=state.me?await api('/projects'):[];}
async function loadUsage(){state.use=state.me?await api('/usage'):null;}
async function loadBrand(){state.brands=state.me?await api('/brands'):[];state.assets=state.me?await api('/assets'):[];}
async function loadJobs(){state.jobs=state.me?await api('/jobs'):[];}
async function refreshUser(){const d=await api('/me');state.me=d.user;state.config=d.config;await Promise.all([loadProjects(),loadUsage(),loadBrand(),loadJobs()]);}
async function ensureUser(continuation){
 if(state.me)return true;
 if(!state.config.guest){state.pending=continuation||null;authDialog('register');return false;}
 state.me=await api('/auth/guest','POST');await loadUsage();chrome();return true;
}
function authDialog(mode='register'){
 const register=mode==='register';const d=modal({title:register?'Make this workspace yours':'Sign in to Cutroom',kicker:'YOUR ACCOUNT',body:`<p class="modal-lead">${register?(state.me?.guest?'Keep your current projects and sign back in from another browser.':'Create an account to store your projects, clips, and exports.'):'Get back to your saved projects and exports.'}</p><form class="stack" id="auth-form">${register?'<label class="field">Display name<input name="name" autocomplete="name" placeholder="Your name" maxlength="80"></label>':''}<label class="field">Email<input type="email" name="email" autocomplete="email" required placeholder="you@example.com"></label><label class="field">Password<input type="password" name="password" autocomplete="${register?'new-password':'current-password'}" required ${register?'minlength="10"':''} maxlength="128" placeholder="${register?'At least 10 characters':'Your password'}"></label><p class="form-error" role="alert" hidden></p><button class="btn primary big" type="submit">${ico('user',17)} ${register?'Create account':'Sign in'}</button><p class="inline-note">${register?'Already have an account?':'New to Cutroom?'} ${btn(register?'Sign in':'Create an account',null,{kind:'ghost sm',attrs:act(register?'login':'register')})}</p></form>`});
 const f=$('#auth-form',d);f.onsubmit=e=>{e.preventDefault();formError(f);action($('button[type=submit]',f),async()=>{try{const data=Object.fromEntries(new FormData(f));state.me=await api('/auth/'+(register?'register':'login'),'POST',data);await Promise.all([loadProjects(),loadUsage(),loadBrand(),loadJobs()]);closeModal();toast(register?'Your account is ready.':'Welcome back.');const pending=state.pending;state.pending=null;await route();if(typeof pending==='function')pending();}catch(e){formError(f,e.message);}});};
}
function profile(){
 if(!state.me||state.me.guest){authDialog('register');return;}
 modal({title:who(),kicker:'MY ACCOUNT',body:`<p class="modal-lead">${esc(state.me.email)}</p><div class="actions">${btn('Workspace settings','settings',{attrs:act('settings')})}${btn('Sign out','logout',{attrs:act('logout')})}</div>`});
}
function prefsFields(prefs={}){
 const counts=[1,2,3,4,5,6,7,8,9,10];
 return `<div class="grid2">
   <label class="field">Video Layout<select name="layout">${layoutOpts(prefs.layout||'track')}</select></label>
   <label class="field">Aspect ratio<select name="ratio">${ratiosOpts(prefs.ratio||state.me?.preferred?.ratio||'9:16')}</select></label>
   <label class="field">Subtitle Language<select name="subtitle_language">${subLangOpts(prefs.subtitle_language||'auto')}</select></label>
   <label class="field">Spoken language<select name="language">${langOpts(prefs.language||state.me?.preferred?.language||'auto')}</select></label>
   <label class="field">Subtitle Animation & Style<select name="preset">${capOpts(prefs.preset||'pulse')}</select></label>
   <label class="field">Brand kit<select name="brand">${option('','No brand kit',prefs.brand||'')}${state.brands.map(x=>option(x.id,x.name,prefs.brand)).join('')}</select></label>
   <label class="field">Clip length<select name="length">${durationChoices.map(x=>option(x,durationLabel[x],prefs.length||'auto')).join('')}</select></label>
   <label class="field">Number of clips<select name="count">${counts.map(n=>option(String(n),`${n} ${n===1?'clip':'clips'}${n===6?' (Default)':''}`,String(prefs.count||6))).join('')}</select></label>
 </div>
 <div class="field stack" style="gap:5px;margin-top:4px">
   <label for="focus-input"><strong>What should Cutroom look for?</strong> <small>(AI Custom Instructions)</small></label>
   <input id="focus-input" name="focus" value="${esc(prefs.focus||'')}" maxlength="500" placeholder="E.g. key moments, financial calculations, funny debates, surprising insights...">
   <div class="prompt-pills">
     <button type="button" class="prompt-pill" data-pill="High-energy opening hooks and viral statements">🔥 Viral Hooks</button>
     <button type="button" class="prompt-pill" data-pill="Business metrics, revenue, costs, and profit calculations">💰 Business & Numbers</button>
     <button type="button" class="prompt-pill" data-pill="Surprising counterintuitive facts and deep insights">💡 Key Insights</button>
     <button type="button" class="prompt-pill" data-pill="Action-packed moments and emotional climaxes">⚡ High Energy</button>
   </div>
 </div>`;
}
function readPrefs(f){
 const data=new FormData(f);
 const count=Math.min(10,Math.max(1,parseInt(data.get('count')||6,10)));
 return {
   length:data.get('length')||'auto',
   ratio:data.get('ratio')||'9:16',
   layout:data.get('layout')||'track',
   language:data.get('language')||'auto',
   subtitle_language:data.get('subtitle_language')||'auto',
   preset:data.get('preset')||'pulse',
   brand:data.get('brand')||null,
   focus:String(data.get('focus')||'').trim(),
   count
 };
}
function newProject({url='',file=null,resume=null}={}){
 let selected=file,mode=url?'url':'file'; if(resume)mode='file';
 const d=modal({title:resume?'Resume video upload':'Create a project',kicker:'AI CLIP GENERATOR',wide:true,body:`<p class="modal-lead">${resume?'Select the same local video to continue where you left off.':'Upload a video or import a direct video file. Choose how you want your clips to start.'}</p><form class="stack" id="create-form" autocomplete="off">
 ${resume?'':`<div class="segmented" id="source-type"><button type="button" data-mode="file" class="${mode==='file'?'selected':''}">${ico('upload',15)} Upload file</button><button type="button" data-mode="url" class="${mode==='url'?'selected':''}">${ico('link',15)} Import link</button></div>`}
 <div id="file-mode" ${mode==='file'?'':'hidden'}><input id="source-file" class="sr-only" type="file" accept="video/*,.mkv,.webm,.mxf,.ts,.wmv,.avi" tabindex="-1"><button type="button" class="dropzone" id="dropzone" aria-label="Choose a video file" style="width:100%"><span class="drop-icon">${ico('upload',18)}</span><strong>Click to choose or drop a video here</strong><small>MP4, MOV, WebM, MKV and more · up to ${size(state.config.max_bytes)}</small></button><div class="upload-summary" id="file-summary" hidden></div></div>
 <label class="field" id="url-mode" ${mode==='url'?'':'hidden'}>Direct video URL<input type="url" id="source-url" ${mode==='url'?'':'disabled'} name="url" maxlength="2400" value="${esc(url)}" placeholder="https://example.com/video.mp4"><small>Use a public HTTPS file from an approved host. Platform watch pages are not direct files.</small></label>
 ${resume?'':prefsFields()}<p class="form-error" role="alert" hidden></p><div class="dialog-footer">${btn('Cancel',null,{attrs:act('close')})}<button type="submit" class="btn primary big">${ico(resume?'upload':'sparkle',17)} ${resume?'Resume upload':'Generate clips'}</button></div></form>`});
 const f=$('#create-form',d),fi=$('#source-file',d),drop=$('#dropzone',d),summary=$('#file-summary',d);
 function setFile(v){selected=v;drop.hidden=!!v;summary.hidden=!v;if(v)summary.innerHTML=`<div class="row">${ico('film',18)}<div><b>${esc(v.name)}</b><br><small class="muted">${size(v.size)} · video file</small></div></div>${iconBtn('Remove selected file','x','id="remove-file"')}`;if(v)$('#remove-file',summary).onclick=()=>{fi.value='';setFile(null);};formError(f);}
 setFile(selected);drop.onclick=()=>fi.click();fi.onchange=()=>setFile(fi.files[0]);drop.ondragover=e=>{e.preventDefault();drop.classList.add('drag');};drop.ondragleave=()=>drop.classList.remove('drag');drop.ondrop=e=>{e.preventDefault();drop.classList.remove('drag');if(e.dataTransfer.files.length)setFile(e.dataTransfer.files[0]);};
 $$('[data-mode]',d).forEach(b=>b.onclick=()=>{mode=b.dataset.mode;$$('[data-mode]',d).forEach(el=>el.classList.toggle('selected',el===b));$('#file-mode',d).hidden=mode!=='file';$('#url-mode',d).hidden=mode!=='url';$('#source-url',d).disabled=mode!=='url';formError(f);});
 $$('.prompt-pill',d).forEach(b=>b.onclick=()=>{const inp=$('#focus-input',d);if(inp){const val=inp.value.trim();inp.value=val?`${val}, ${b.dataset.pill}`:b.dataset.pill;inp.focus();}});
 f.onsubmit=e=>{e.preventDefault();formError(f);action($('button[type=submit]',f),async()=>{try{
  const useFile=mode==='file',url=useFile?null:$('#source-url',d).value.trim(),prefs=readPrefs(f);
  if(useFile&&!selected)throw Error('Choose a video file first.');
  if(useFile&&(!selected.size||selected.size>state.config.max_bytes))throw Error(`Choose a video up to ${size(state.config.max_bytes)}.`);
  if(!useFile&&!url)throw Error('Enter a direct HTTPS video link.');
  if(resume&&(selected.size!==resume.bytes||selected.name!==resume.filename))throw Error('Choose the same filename and file size as the original upload.');
  if(useFile&&state.upload?.running)throw Error('Another upload is active. Pause it before starting a different upload.');
  if(!await ensureUser(()=>newProject({url:url||'',file:selected,resume})))return;
  const p=resume?await api(`/projects/${resume.id}`):await api('/projects','POST',{filename:useFile?selected.name:'',bytes:useFile?selected.size:0,url,prefs});
  closeModal();state.search='';await loadProjects();go(`project/${p.id}`);if(state.screen==='project'&&state.id===p.id){state.project=p;showProject();}
  if(useFile)startUpload(p,selected);else toast('Video import queued.');
 }catch(e){formError(f,e.message);}});};
}
async function startUpload(p,file){
 const task={id:p.id,file,done:p.received,loaded:p.received,total:file.size,running:true,aborted:false,xhr:null};state.upload=task;
 function update(){if(state.screen==='project'&&state.id===p.id)refreshUploadMeter(p);}
 update();let conflicts=0;
 try{while(task.done<file.size&&!task.aborted){const end=Math.min(file.size,task.done+state.config.chunk_bytes);try{
  task.done=await chunk(p.id,file,task.done,end,n=>{task.loaded=n;update();},x=>{task.xhr=x;});task.loaded=task.done;update();
 }catch(e){if(e.status===409&&Number.isInteger(e.detail?.offset)&&conflicts++<4){task.done=e.detail.offset;task.loaded=task.done;continue;}throw e;}}
 if(!task.aborted){const ready=await api(`/projects/${p.id}/start`,'POST');task.running=false;task.xhr=null;if(state.id===p.id&&state.screen==='project'){state.project=ready;showProject();}toast('Upload saved. Analysis queued.');}
 }catch(e){if(!task.aborted)toast(e.message,'error');}
 finally{task.running=false;task.xhr=null;loadProjects().catch(()=>{});if(state.screen==='project'&&state.id===p.id) await refreshProject();}
}
function refreshUploadMeter(p){
 const t=state.upload?.id===p.id?state.upload:null;const pct=Math.round((t?.loaded??p.received)/(p.bytes||1)*100);
 const bar=$('#u-meter',view);if(!bar)return;
 bar.innerHTML=`<div class="spread"><span>${t?.running?'Uploading video':'Saved upload progress'}</span><strong class="status-number">${pct}%</strong></div>${progress(pct)}<p class="small muted">${size(t?.loaded??p.received)} of ${size(p.bytes)} transferred.</p>`;
 const actions=$('#u-actions',view);if(actions){if(t?.running){if(!$('[data-action=pause-upload]',actions))actions.innerHTML=btn('Pause upload','pause',{attrs:act('pause-upload')});}else actions.innerHTML=btn(p.received===p.bytes?'Start analysis':'Resume upload',p.received===p.bytes?'sparkle':'upload',{kind:'primary',attrs:act(p.received===p.bytes?'start-project':'resume',`data-id="${p.id}"`)});}
}
function processing(p){
 const job=p.job,upload=p.status==='uploading',failed=p.status==='failed',stage=job?.stage||'Waiting for a worker',n=job?.progress||0;
 view.innerHTML=header('SOURCE PROJECT',p.title,upload?'Upload your source video to begin.':'The full workspace will be available when analysis finishes.',btn('All projects','back',{tag:'a',attrs:'href="#projects"'})+iconBtn('Project actions','dots',act('project-menu',`data-id="${p.id}"`)))+
 `<section class="processing surface"><div class="processing-top"><span class="processing-mark">${ico(failed?'alert':upload?'upload':'sparkle',25)}</span><div><p class="eyebrow">${failed?'ACTION NEEDED':upload?'STEP 1 OF 2':'ANALYSIS RUNNING'}</p><h2>${failed?'Could not finish analysis':upload?'Secure video upload':'Finding your best cuts'}</h2></div></div>
 ${upload?`<div id="u-meter"></div><div class="actions" id="u-actions" style="margin-top:13px"></div>`:`<div class="spread"><span>${esc(stage)}</span><strong class="status-number">${n}%</strong></div>${progress(n)}${failed?`<p class="form-error">${esc(job?.error||'The video could not be processed.')}</p><div class="actions" style="margin-top:12px">${btn('Retry analysis','refresh',{kind:'primary',attrs:act('retry',`data-id="${job?.id||''}"`)})}</div>`:`<p class="small muted">This runs in the background. You can leave this page and come back.</p>`}<div class="stages">${[['film','Prepare video',0,15],['captions','Transcribe',15,40],['cut','Rank clips',40,60],['target','Track subjects',60,80],['sparkle','Enhance & polish',80,100]].map(([icon,label,a,b])=>`<div class="${n>=b?'complete':n>=a&&!failed?'active':''}">${ico(n>=b?'check':icon,15)}<strong>${label}</strong></div>`).join('')}</div>`}</section>`;
 if(upload)refreshUploadMeter(p);
}
function clipCard(p,c){
 const a=`data-id="${c.id}"`,poster=c.poster||p.poster,score=c.score!=null?`<button type="button" class="score-chip" ${act('score',a)} aria-label="View Cut Score ${c.score}">${ico('bolt',12)} ${c.score} Cut Score</button>`:'';
 return `<article class="card clip-card"><div style="position:relative"><button class="thumb ${poster?'':'blank-thumb'}" ${act('preview-clip',a)} aria-label="Preview ${esc(c.title)}">${poster?`<img src="${esc(poster)}" alt="">`:''}<span class="clip-play">${ico('play',18)}</span><span class="time-chip">${time(c.end_at-c.start_at)}</span></button>${score}</div><div class="card-body"><div class="card-top"><button type="button" class="card-title" ${act('edit-clip',a)}>${esc(c.title)}</button>${iconBtn('Clip actions','dots',act('clip-menu',a))}</div><p class="clip-copy">${esc(c.insights.description||c.insights.reason||'Manually selected clip')}</p><div class="card-actions"><span class="small muted">${time(c.start_at)} – ${time(c.end_at)}</span>${btn('Edit clip','edit',{kind:'soft sm',attrs:act('edit-clip',a)})}</div></div></article>`;
}
function projectReady(p){
 const clips=[...(p.clips||[])];if(state.clipSort==='time')clips.sort((a,b)=>a.start_at-b.start_at);if(state.clipSort==='new')clips.sort((a,b)=>b.created-a.created);
 const running=p.job?.kind==='regenerate'&&['queued','running'].includes(p.job.status),failed=p.job?.kind==='regenerate'&&p.job.status==='failed';
 view.innerHTML=header(p.sample?'SAMPLE PROJECT':'SOURCE PROJECT',p.title,`${p.clip_count} ${p.clip_count===1?'clip':'clips'} · ${time(p.info.duration)} source`,btn('Regenerate','refresh',{attrs:act('regenerate',running?'disabled':'')})+btn('Batch export','download',{kind:'primary',attrs:act('batch',clips.length?'':'disabled')})+iconBtn('Project actions','dots',act('project-menu',`data-id="${p.id}"`)))+
 `<div class="project-banner surface">${p.poster?`<img src="${p.poster}" alt="">`:`<span class="export-icon">${ico('film')}</span>`}<div class="row"><div><h3>Source video</h3><div class="card-meta">${p.info.width} × ${p.info.height} <span class="divider-dot">·</span> ${p.info.language?(languages[p.info.language]||p.info.language):'No speech'} <span class="divider-dot">·</span> ${p.info.speakers?p.info.speakers+' estimated speaker'+(p.info.speakers!==1?'s':''):'No speaker labels'}</div></div></div><div class="actions">${btn('Full transcript','captions',{kind:'sm',attrs:act('transcript')})}${btn('Play source','play',{kind:'sm',attrs:act('preview-source')})}</div></div>
 ${running||failed?`<div class="tip" style="margin-bottom:13px">${ico(failed?'alert':'refresh',17)}<div>${failed?esc(p.job.error):`${esc(p.job.stage)} · ${p.job.progress}%`}</div>${failed?btn('Retry',null,{kind:'sm',attrs:act('retry',`data-id="${p.job.id}"`)}):''}</div>`:''}
 <div class="section-head"><div><h2>Your clips</h2><p>Cut Score ranks moments against each other. It does not predict views.</p></div><div class="actions"><select id="clip-sort" class="filter-select" aria-label="Sort clips">${option('score','Cut Score',state.clipSort)}${option('time','Source time',state.clipSort)}${option('new','Newest first',state.clipSort)}</select>${btn('Manual clip','plus',{attrs:act('manual')})}</div></div>
 ${clips.length?`<div class="cards">${clips.map(c=>clipCard(p,c)).join('')}</div>`:blank('cut','No clips yet','Regenerate highlights or select a clip manually.')}`;
 $('#clip-sort').onchange=e=>{state.clipSort=e.target.value;projectReady(p);};
}
function showProject(){if(!state.project)return;state.project.status==='ready'?projectReady(state.project):processing(state.project);}
function keyFor(p){return JSON.stringify([p?.id,p?.status,p?.title,p?.received,p?.job?.status,p?.job?.stage,p?.job?.progress,p?.clip_count,p?.updated]);}
async function refreshProject(force=false){
 if(state.screen!=='project')return;const id=state.id;const p=await api(`/projects/${id}`);if(state.screen!=='project'||state.id!==id)return;
 const old=state.project;state.project=p;const k=keyFor(p);
 if(old?.job?.kind==='regenerate'&&['queued','running'].includes(old.job.status)&&p.job?.status==='done')toast(p.job.output?.clip_ids?.length?`${p.job.output.clip_ids.length} alternative clips added.`:'No different moments were found. Try a new focus or length.');
 if(old?.status==='processing'&&p.status==='ready'){toast('Your clips are ready.');loadUsage().then(chrome).catch(()=>{});}
 if(force||k!==lastUiKey){lastUiKey=k;showProject();if(!old||old.title!==p.title)chrome();}
}
function clipFind(id){return state.project?.clips?.find(x=>x.id===id);}
function projectFind(id){return state.project?.id===id?state.project:state.projects.find(x=>x.id===id);}

function scoreDialog(c){
 const data=c.insights;modal({title:'Why this clip was selected',kicker:'CUT SCORE',body:`<div class="row" style="margin-bottom:12px"><div class="score-num">${c.score??'—'}</div><p class="muted small">Relative editorial ranking<br>Not a forecast of virality</p></div><p class="modal-lead">${esc(data.reason||'Manually selected.')}</p><div class="score-grid">${Object.entries(data.axes||{}).map(([k,v])=>`<div class="score-axis"><span>${axes[k]||esc(k)}</span>${progress(v)}<b>${v}</b></div>`).join('')}</div>${data.hook?`<div class="divider"></div><p class="inline-note">OPENING LINE</p><p class="small">${esc(data.hook)}</p>`:''}`});
}
function previewDialog(p,c=null){
 const from=c?.start_at??0,to=c?.end_at??p.info.duration;
 const d=modal({title:c?.title||p.title,kicker:c?'SOURCE EXCERPT':'SOURCE VIDEO',wide:true,body:`<video class="preview-loading" src="${esc(p.preview)}" poster="${esc(p.poster||'')}" controls playsinline preload="metadata"></video><div class="dialog-footer"><p class="inline-note" style="margin-right:auto">${c?'Original excerpt. Open the editor for reframing and captions.':'Original video before any clip edits.'}</p>${c?btn('Open editor','edit',{kind:'primary',attrs:act('edit-clip',`data-id="${c.id}"`)}):''}</div>`});
 const v=$('video',d);v.addEventListener('loadedmetadata',()=>{v.currentTime=from;},{once:true}); if(c){v.addEventListener('timeupdate',()=>{if(v.currentTime>=to){v.pause();v.currentTime=to-.01;}if(v.currentTime<from-.2)v.currentTime=from;});v.addEventListener('play',()=>{if(v.currentTime>=to-.07)v.currentTime=from;});}
}
function transcriptDialog(p){
 const d=modal({title:'Source transcript',kicker:'TIMESTAMPED SPEECH',wide:true,body:spinner('Loading transcript…')});
 api(`/projects/${p.id}/analysis`).then(a=>{if(!d.open||$('#dialog-title',d)?.textContent!=='Source transcript')return;$('.loading',d).outerHTML=a.words.length?`<div class="transcript-full">${groupTranscript(a.words).map(w=>`<p><b>${time(w[0].s)} ${w[0].speaker?'· Speaker '+w[0].speaker:''}</b> ${esc(w.map(x=>x.t).join(' '))}</p>`).join('')}</div>`:blank('captions','No speech detected','This project can still be reframed and edited.');}).catch(e=>toast(e.message,'error'));
}
function groupTranscript(words){const rows=[];let cur=[];for(const x of words){if(cur.length&&(cur[0].speaker!==x.speaker||cur.length>=22||x.s-cur.at(-1).e>1.2)){rows.push(cur);cur=[];}cur.push(x);}if(cur.length)rows.push(cur);return rows;}
function regenerateDialog(){
 const p=state.project,d=modal({title:'Find alternative moments',kicker:'REGENERATE CLIPS',body:`<p class="modal-lead">Rank the original transcript again. Different lengths or a more specific focus can find new moments without changing existing clips.</p><form id="regen-form" class="stack">${prefsFields(p.prefs)}<p class="form-error" hidden></p><div class="dialog-footer"><button type="submit" class="btn primary">${ico('sparkle')} Find more clips</button></div></form>`});
 const f=$('#regen-form',d);f.onsubmit=e=>{e.preventDefault();action($('button[type=submit]',f),async()=>{try{await api(`/projects/${p.id}/regenerate`,'POST',readPrefs(f));closeModal();toast('Alternative moments queued.');await refreshProject(true);}catch(e){formError(f,e.message);}});};
}
function renderDialog(clips,before=null){
 const list=Array.isArray(clips)?clips:[clips];const batch=list.length>1;
 const d=modal({title:batch?'Export multiple clips':'Export clip',kicker:'SERVER RENDER',body:`<p class="modal-lead">${batch?'Queue up to eight selected clips for rendering.':'Render your saved edits, framing, overlays, and captions into a downloadable MP4.'}</p><form id="render-form" class="stack">${batch?`<div id="batch-checks" class="stack" style="max-height:160px;overflow:auto">${list.map((c,i)=>`<label class="check-label"><input name="clip" type="checkbox" value="${c.id}" ${i<8?'checked':''}> ${esc(c.title)}</label>`).join('')}</div>`:''}
 <div class="grid2"><label class="field">Resolution<select name="resolution">${[480,720,1080,2160].map(n=>option(String(n),n===2160?'2160p · 4K':n+'p', '1080')).join('')}</select></label><label class="field">Quality<select name="quality">${['compact','standard','high'].map(n=>option(n,n[0].toUpperCase()+n.slice(1),'standard')).join('')}</select></label></div><p class="inline-note">H.264 video · AAC audio where present · SRT sidecar · Original aspect ratio selection retained</p><p class="form-error" role="alert" hidden></p><div class="dialog-footer">${btn('Cancel',null,{attrs:act('close')})}<button type="submit" class="btn primary big">${ico('download',17)} ${batch?'Queue renders':'Start render'}</button></div></form>`});
 const f=$('#render-form',d);f.onsubmit=e=>{e.preventDefault();action($('button[type=submit]',f),async()=>{const completed=[];try{
   const data=new FormData(f),ids=batch?data.getAll('clip'):[list[0].id];if(!ids.length||ids.length>8)throw Error('Select one to eight clips.');
   if(before)await before();const opts={resolution:Number(data.get('resolution')),quality:data.get('quality')};
   for(const id of ids)completed.push(await api(`/clips/${id}/render`,'POST',opts));
   closeModal();toast(`${completed.length===1?'Render':completed.length+' renders'} queued in Export Center.`);go('exports');if(state.screen==='exports'){await loadJobs();exportsPage();}
  }catch(e){formError(f,(completed.length?`${completed.length} already queued. `:'')+e.message);}});};
}
function exportRow(j){
 const project=state.projects.find(p=>p.id===j.project_id);const title=j.output?.title||j.title||project?.title||'Clip export';
 const url=`/api/jobs/${j.id}/download`;
 return `<article class="export-row surface"><div class="export-details"><span class="export-icon">${ico(j.status==='done'?'video':'download',18)}</span><div><h3>${esc(title)}</h3><p class="muted">${date(j.created)} · ${j.output?`${j.output.width} × ${j.output.height} · ${size(j.output.bytes)}`:'H.264 MP4'}</p>${j.error?`<p class="small" style="color:#9a3153">${esc(j.error)}</p>`:''}</div></div><div>${statusBadge(j.status)}${j.status==='running'||j.status==='queued'?`${progress(j.progress)}<span class="inline-note">${esc(j.stage)} · ${j.progress}%</span>`:''}</div><div class="actions">${j.status==='done'?`${iconBtn('Preview export','play',act('play-export',`data-id="${j.id}"`))}${btn('MP4','download',{tag:'a',kind:'soft sm',attrs:`href="${url}" download`})}${btn('SRT',null,{tag:'a',kind:'sm',attrs:`href="${url}?format=srt" download`})}`:j.status==='failed'?btn('Retry','refresh',{kind:'sm',attrs:act('retry',`data-id="${j.id}"`)}):''}${j.status!=='running'?iconBtn('Remove export','trash',act('delete-export',`data-id="${j.id}"`)):''}</div></article>`;
}
function exportsPage(){
 view.innerHTML=header('DELIVERY','Export center','Track background renders and download your finished videos.',btn('Browse projects','folder',{tag:'a',attrs:'href="#projects"'}))+`<div id="export-list"></div>`;fillExports();
}
function fillExports(){const el=$('#export-list',view);if(el)el.innerHTML=state.jobs.length?`<div class="export-list">${state.jobs.map(exportRow).join('')}</div>`:blank('download','No exports yet','Open a clip in the editor, then start a render. Your finished MP4 and SRT appear here.',btn('Browse projects','folder',{tag:'a',kind:'primary',attrs:'href="#projects"'}));}

function brandPage(){
 view.innerHTML=header('CREATOR IDENTITY','Brand kits','Reuse caption styles, brand colors, and logos across your videos.',btn('New brand kit','plus',{kind:'primary',attrs:act('brand-create')}))+
 `${state.brands.length?`<div class="cards">${state.brands.map(b=>`<article class="card brand-card"><div class="brand-preview" style="background:${b.background};color:${b.caption.color};font-size:${Math.max(17,b.caption.size*.4)}px">${b.logo?`<img src="/api/assets/${b.logo}" alt="Brand logo">`:''}<span>On-<b style="color:${b.caption.highlight}">brand</b><br> captions.</span></div><div class="card-top"><h3>${esc(b.name)}</h3>${iconBtn('Delete brand kit','trash',act('brand-delete',`data-id="${b.id}"`))}</div><p class="muted small">${esc(capNames[b.caption.preset])} · ${esc(b.caption.font_id?'Custom font':b.caption.font)}</p>${btn('Edit brand kit','edit',{attrs:act('brand-edit',`data-id="${b.id}"`)})}</article>`).join('')}</div>`:blank('palette','Your visual style, saved','Save a brand kit once and apply it on upload or in the editor.',btn('Create a brand kit','plus',{kind:'primary',attrs:act('brand-create')}))}
 <div class="project-section"><div class="section-head"><div><h2>Caption presets</h2><p>Each preset can be customized before you export.</p></div></div><div class="cards">${Object.values(state.presets).map(cap=>`<div class="surface brand-card"><div class="brand-preview" style="background:${cap.background||'#271c3d'};color:${cap.color};font-family:${esc(cap.font)},sans-serif;${cap.uppercase?'text-transform:uppercase':''}">One <span style="color:${cap.highlight}">good line.</span></div><div class="card-top"><h3>${esc(capNames[cap.preset])}</h3>${btn('Use','plus',{kind:'sm',attrs:act('brand-from-preset',`data-id="${cap.preset}"`)})}</div></div>`).join('')}</div></div>`;
}
async function brandForm(b=null,preset='pulse'){
 if(!await ensureUser(()=>brandForm(b,preset)))return;await loadBrand();
 const cap=clone(b?.caption||state.presets[preset]||state.presets.pulse);let image=b?.logo||null,font=cap.font_id||null;
 const d=modal({title:b?'Edit brand kit':'Create a brand kit',kicker:'STYLE LIBRARY',body:`<form class="stack" id="brand-form"><label class="field">Name<input name="name" required maxlength="60" value="${esc(b?.name||'')}" placeholder="E.g. Podcast brand"></label><div class="grid2"><label class="field">Caption preset<select name="preset">${Object.keys(capNames).map(x=>option(x,capNames[x],cap.preset)).join('')}</select></label><label class="field">Base font<select name="font">${['DejaVu Sans','Liberation Sans','Liberation Serif','DejaVu Sans Mono','Noto Sans'].map(x=>option(x,x,cap.font)).join('')}</select></label></div><div class="grid2"><label class="field">Text color<input name="color" type="color" value="${cap.color}"></label><label class="field">Highlight color<input name="highlight" type="color" value="${cap.highlight}"></label><label class="field">Background<input name="background" type="color" value="${b?.background||'#171322'}"></label><label class="field">Font size<input name="size" type="number" min="20" max="110" value="${cap.size}"></label></div><div class="grid2"><label class="field">Logo<select name="logo">${option('','No logo',image||'')}${state.assets.filter(a=>a.kind==='image').map(a=>option(a.id,a.name,image)).join('')}</select></label><label class="field">Custom font<select name="font_id">${option('','Use base font',font||'')}${state.assets.filter(a=>a.kind==='font').map(a=>option(a.id,a.name,font)).join('')}</select></label></div><div class="actions">${btn('Upload logo','upload',{kind:'sm',attrs:'id="brand-logo"'})}${btn('Upload font','upload',{kind:'sm',attrs:'id="brand-font"'})}<input type="file" id="bl-file" accept="image/png,image/jpeg,image/webp" hidden><input type="file" id="bf-file" accept=".ttf,.otf" hidden></div><p class="form-error" role="alert" hidden></p><div class="dialog-footer"><button class="btn primary" type="submit">${ico('check',17)} Save brand kit</button></div></form>`});
 const f=$('#brand-form',d);f.elements.preset.onchange=()=>{const v=state.presets[f.elements.preset.value];for(const k of ['font','color','highlight','size'])f.elements[k].value=v[k];};
 function asset(button,input,kind,field){const btn=$(button,d),inp=$(input,d);btn.onclick=()=>inp.click();inp.onchange=()=>{if(!inp.files[0])return;action(btn,async()=>{const a=await sendAsset(inp.files[0],kind);state.assets.unshift(a);const o=document.createElement('option');o.value=a.id;o.textContent=a.name;f.elements[field].append(o);f.elements[field].value=a.id;toast(`${kind==='image'?'Logo':'Font'} uploaded.`);});};}
 asset('#brand-logo','#bl-file','image','logo');asset('#brand-font','#bf-file','font','font_id');
 f.onsubmit=e=>{e.preventDefault();action($('button[type=submit]',f),async()=>{try{const a=Object.fromEntries(new FormData(f));const caption=clone(a.preset===cap.preset?cap:state.presets[a.preset]);Object.assign(caption,{font:a.font,color:a.color,highlight:a.highlight,size:Number(a.size),font_id:a.font_id||null});const body={name:a.name,caption,background:a.background,logo:a.logo||null};await api(b?`/brands/${b.id}`:'/brands',b?'PUT':'POST',body);await loadBrand();closeModal();if(state.screen==='brand')brandPage();toast('Brand kit saved.');}catch(e){formError(f,e.message);}});};
}
function settingsPage(){
 const p=state.use||{seconds:0,limit:1800,projects:0,exports:0,bytes:0,storage_limit:3*1024**3};
 const account=state.me?.email;
 view.innerHTML=header('PREFERENCES','Workspace settings','Manage your profile, defaults, and monthly processing allowance.')+`<div class="settings-grid"><section class="section-box surface"><form id="settings-form" class="setting-form"><h3>Profile &amp; defaults</h3><p>${account?`Signed in as ${esc(account)}.`:'Save this workspace to an account to sign in from another browser.'}</p><label class="field">Display name<input name="name" maxlength="80" required value="${esc(who())}"></label><div class="grid2"><label class="field">Default aspect ratio<select name="ratio">${ratiosOpts(state.me?.preferred?.ratio||'9:16')}</select></label><label class="field">Default spoken language<select name="language">${langOpts(state.me?.preferred?.language||'auto')}</select></label></div><p class="form-error" hidden></p><div class="actions"><button class="btn primary" type="submit">${ico('check',16)} Save preferences</button>${account?btn('Sign out','logout',{attrs:act('logout')}):btn('Create account','user',{attrs:act('register')} )+btn('Sign in',null,{kind:'ghost',attrs:act('login')})}</div></form></section>
 <section class="section-box surface"><div class="spread"><h3>Plan &amp; usage</h3><span class="badge violet">${esc(plan())}</span></div><p>Processing allowance resets each calendar month (UTC). Examples and re-ranking do not count.</p><div class="meter"><div class="spread"><b>${minute(p.seconds)} of ${p.limit/60} min used</b><span class="small muted">${Math.min(100,Math.round(p.seconds/p.limit*100))}%</span></div>${progress(Math.round(p.seconds/p.limit*100))}</div><div class="stat-grid"><div><strong>${p.projects}</strong><span>Projects</span></div><div><strong>${p.exports}</strong><span>Exports this month</span></div><div><strong>${size(p.bytes)}</strong><span>Source storage</span></div></div>${state.config.stripe&&account?btn(plan()==='Studio'?'Manage subscription':'Upgrade to Studio','bolt',{kind:'soft',attrs:act(plan()==='Studio'?'billing-portal':'billing-checkout')}):`<div class="tip">${ico('info',15)} <span>${!state.config.stripe?'Paid subscriptions are not configured on this instance. Your current allowance is active.':'Create an account to manage a subscription.'}</span></div>`}</section></div>`;
 const f=$('#settings-form',view);f.onsubmit=e=>{e.preventDefault();action($('button[type=submit]',f),async()=>{try{if(!await ensureUser())return;state.me=await api('/settings','PATCH',Object.fromEntries(new FormData(f)));chrome();toast('Preferences saved.');}catch(e){formError(f,e.message);}});};
}
function help(){
 modal({title:'How to use Cutroom',kicker:'STUDIO GUIDE',body:`<p class="modal-lead">From source file to a finished short, in four steps.</p><div class="help-section"><details open><summary>1. Add your source</summary><p>Choose a local video or use a direct HTTPS URL. In this workspace, link imports are allowed from ${esc(state.config.import_hosts.join(', ')||'the hosts configured by your operator')}. Uploads can be resumed from Projects.</p></details><details><summary>2. Review Cut Score</summary><p>Cutroom estimates how well a moment works on its own using speech, sentence boundaries, delivery, and visual signals. The score is an editorial ranking, not a prediction of virality.</p></details><details><summary>3. Make it yours</summary><p>Edit words in the transcript, trim in the timeline, select an aspect ratio, and add layers. Space plays or pauses. Ctrl/⌘+Z undoes, Ctrl/⌘+Shift+Z redoes, Ctrl/⌘+S saves, and arrow keys scrub.</p></details><details><summary>4. Render and download</summary><p>The export worker burns in captions and applies your settings. Your actual H.264 MP4 and an SRT file appear in Export Center.</p></details></div><div class="dialog-footer" style="justify-content:flex-start">${btn('API documentation','external',{tag:'a',attrs:'href="/api/docs" target="_blank" rel="noopener noreferrer"'})}</div>`});
}
function sampleInfo(s){
 if(!s)return;const d=modal({title:s.title,kicker:'SAMPLE LIBRARY',body:`<p class="modal-lead">A real ${esc(s.type.toLowerCase())} with ${s.clip_count} clips picked by the Cutroom pipeline. Open an editable copy to try the workspace.</p><p class="small muted">Media: ${esc(s.credit)}. <a class="purple-link" target="_blank" rel="noopener noreferrer" href="${esc(s.link)}">View source ${ico('external',12)}</a></p><div class="dialog-footer">${btn('Open sample','arrow',{kind:'primary',attrs:act('sample',`data-id="${s.id}"`)})}</div>`});
}
function confirmDialog(title,body,label,fn){
 const d=modal({title,body:`<p class="modal-lead">${esc(body)}</p><div class="dialog-footer">${btn('Cancel',null,{attrs:act('close')})}${btn(label,'trash',{kind:'danger',attrs:'id="confirm-action"'})}</div>`});$('#confirm-action',d).onclick=e=>action(e.currentTarget,fn);
}
function projectMenu(p){
 if(!p)return;
 modal({title:p.title,kicker:'PROJECT ACTIONS',body:`<div class="stack">${btn('Rename project','edit',{attrs:act('rename',`data-id="${p.id}"`)})}${p.status==='ready'?btn('Duplicate project','copy',{attrs:act('duplicate',`data-id="${p.id}"`)}):''}${btn('Delete project','trash',{kind:'danger',attrs:act('delete-project',`data-id="${p.id}"`)})}</div>`});
}
function nameDialog(p){
 const d=modal({title:'Rename project',body:`<form class="stack" id="name-form"><label class="field">Name<input name="title" value="${esc(p.title)}" required maxlength="120"></label><p class="form-error" hidden></p><div class="dialog-footer"><button type="submit" class="btn primary">Save name</button></div></form>`});const f=$('form',d);
 f.onsubmit=e=>{e.preventDefault();action($('button[type=submit]',f),async()=>{try{await api(`/projects/${p.id}`,'PATCH',{title:f.elements.title.value});await loadProjects();closeModal();if(state.screen==='project')await refreshProject(true);else fillCards(state.screen==='home');toast('Project renamed.');}catch(e){formError(f,e.message);}});};
}
function clipMenu(c){
 if(!c)return;const a=`data-id="${c.id}"`;
 modal({title:c.title,kicker:'CLIP ACTIONS',body:`<div class="stack">${btn('Edit clip','edit',{attrs:act('edit-clip',a)})}${c.insights.social?btn('Copy social caption','copy',{attrs:act('social',a)}):''}${btn('Duplicate clip','copy',{attrs:act('duplicate-clip',a)})}${btn('Export clip','download',{attrs:act('export-clip',a)})}${btn('Delete clip','trash',{kind:'danger',attrs:act('delete-clip',a)})}</div>`});
}

async function route(){
 const part=location.hash.slice(1).split('?')[0];let [screen,id]=part.split('/');screen=['home','projects','brand','exports','settings','project','edit'].includes(screen)?screen:'home';
 if((screen==='project'||screen==='edit')&&!/^[a-f0-9]{32}$/.test(id||'')){screen='projects';id='';}
 if(state.editor&&!(screen==='edit'&&id===state.id)){
  if(state.editor.dirty()&&!window.confirm('Leave the editor without saving your changes?')){location.hash=`edit/${state.id}`;return;}
  state.editor.destroy();state.editor=null;
 }
 if(state.editor&&screen==='edit'&&state.id===id)return;
 const token=++state.counter;state.screen=screen;state.id=id||'';if(screen!=='edit')state.project=null;lastUiKey='';mobile(false);view.classList.toggle('edit-mode',screen==='edit');chrome();
 window.scrollTo({top:0,behavior:'instant'});
 if(screen==='home'){home();return;}
 if(screen==='projects'){projectsPage();return;}
 if(screen==='brand'){brandPage();return;}
 if(screen==='exports'){exportsPage();loadJobs().then(()=>{if(state.screen==='exports')fillExports();}).catch(()=>{});return;}
 if(screen==='settings'){settingsPage();loadUsage().then(()=>{if(state.screen==='settings'&&!$('#dialog').open){chrome();const f=$('#settings-form');if(f&&!f.contains(document.activeElement))settingsPage();}}).catch(()=>{});return;}
 view.innerHTML=spinner(screen==='edit'?'Opening clip editor…':'Opening project…');
 try{
  if(!state.me){if(!state.ready)return;throw Error('Sign in to open this project.');}
  if(screen==='project'){await refreshProject(true);return;}
  const clip=await api(`/clips/${id}`), p=await api(`/projects/${clip.project_id}`);const analysis=await api(`/projects/${clip.project_id}/analysis`);
  if(token!==state.counter)return;
  state.project=p;editorRouteBack=`#project/${p.id}`;chrome();
  state.editor=openEditor(view,{clip,project:p,analysis,presets:state.presets,brands:state.brands,assets:state.assets,
   exportClip:(c,save)=>renderDialog(c,save),showScore:()=>scoreDialog(clip),onAsset:a=>state.assets.unshift(a)});
 }catch(e){if(token===state.counter)view.innerHTML=blank('alert','Could not open this workspace',e.message,btn('Back to projects','back',{tag:'a',attrs:'href="#projects"'})+(!state.me?btn('Sign in','user',{kind:'primary',attrs:act('login')}):''));}
}

async function onAction(name,id,el){
 switch(name){
 case 'new':newProject();break; case 'help':help();break;case 'close':closeModal();break;case 'mobile':mobile(!state.mobile);break;case 'profile':profile();break;case 'login':authDialog('login');break;case 'register':authDialog('register');break;
 case 'settings':closeModal();go('settings');break;
 case 'logout':await action(el,async()=>{await api('/auth/logout','POST');state.me=null;state.use=null;state.projects=[];state.brands=[];state.assets=[];state.jobs=[];if(state.upload){state.upload.aborted=true;state.upload.xhr?.abort();}state.upload=null;closeModal();go('home');await route();toast('Signed out.');});break;
 case 'open-project':go(`project/${id}`);break;
 case 'sample-info':sampleInfo(state.samples.find(s=>s.id===id));break;
 case 'sample':await action(el,async()=>{if(!await ensureUser(async()=>{try{const p=await api(`/samples/${id}/open`,'POST');await loadProjects();go(`project/${p.id}`);}catch(e){toast(e.message,'error');}}))return;const p=await api(`/samples/${id}/open`,'POST');closeModal();await loadProjects();go(`project/${p.id}`);});break;
 case 'layout':state.layout=id;projectsPage();break;
 case 'project-menu':projectMenu(projectFind(id));break;
 case 'rename':nameDialog(projectFind(id));break;
 case 'resume':newProject({resume:projectFind(id)});break;
 case 'pause-upload':if(state.upload?.running){state.upload.aborted=true;state.upload.xhr?.abort();toast('Upload paused. Completed chunks were kept.');}break;
 case 'start-project':await action(el,async()=>{await api(`/projects/${id}/start`,'POST');await refreshProject(true);});break;
 case 'retry':await action(el,async()=>{await api(`/jobs/${id}/retry`,'POST');toast('Job returned to the queue.');if(state.screen==='project')await refreshProject(true);else{await loadJobs();fillExports();}});break;
 case 'duplicate':await action(el,async()=>{const p=await api(`/projects/${id}/duplicate`,'POST');closeModal();await loadProjects();toast('Project duplicated.');go(`project/${p.id}`);});break;
 case 'delete-project':confirmDialog('Delete this project?','This also removes its clips, uploaded media, and exports. Processing allowance already used will not be refunded.','Delete project',async()=>{if(state.upload?.id===id){state.upload.aborted=true;state.upload.xhr?.abort();}await api(`/projects/${id}`,'DELETE');await Promise.all([loadProjects(),loadUsage()]);closeModal();toast('Project deleted.');if(state.screen==='project')go('projects');else fillCards(state.screen==='home');});break;
 case 'preview-source':previewDialog(state.project);break;case 'preview-clip':previewDialog(state.project,clipFind(id));break;case 'transcript':transcriptDialog(state.project);break;
 case 'regenerate':regenerateDialog();break;case 'batch':renderDialog(state.project.clips);break;
 case 'score':scoreDialog(clipFind(id));break;case 'edit-clip':closeModal();go(`edit/${id}`);break;case 'clip-menu':clipMenu(clipFind(id));break;
 case 'social':await copy(clipFind(id).insights.social);break;
 case 'export-clip':renderDialog(clipFind(id));break;
 case 'manual':await action(el,async()=>{const c=await api(`/projects/${state.id}/clips`,'POST');go(`edit/${c.id}`);});break;
 case 'duplicate-clip':await action(el,async()=>{await api(`/clips/${id}/duplicate`,'POST');closeModal();toast('Clip duplicated.');await refreshProject(true);});break;
 case 'delete-clip':confirmDialog('Delete this clip?','Finished exports will remain in Export Center.','Delete clip',async()=>{await api(`/clips/${id}`,'DELETE');closeModal();await refreshProject(true);toast('Clip deleted.');});break;
 case 'play-export':{const j=state.jobs.find(x=>x.id===id);modal({title:j?.output?.title||'Finished clip',kicker:'MP4 PREVIEW',wide:true,body:`<video class="preview-loading" src="/api/jobs/${id}/download?inline=true" controls playsinline preload="metadata"></video><div class="dialog-footer">${btn('Download MP4','download',{tag:'a',kind:'primary',attrs:`href="/api/jobs/${id}/download" download`})}</div>`});break;}
 case 'delete-export':confirmDialog('Remove this export?','The rendered file will be removed. Your editable clip and original video will stay saved.','Remove export',async()=>{await api(`/jobs/${id}`,'DELETE');await loadJobs();fillExports();closeModal();toast('Export removed.');});break;
 case 'brand-create':await brandForm();break;case 'brand-from-preset':await brandForm(null,id);break;case 'brand-edit':await brandForm(state.brands.find(x=>x.id===id));break;
 case 'brand-delete':confirmDialog('Delete this brand kit?','Existing clips keep their saved style and assets.','Delete brand kit',async()=>{await api(`/brands/${id}`,'DELETE');await loadBrand();closeModal();brandPage();toast('Brand kit deleted.');});break;
 case 'billing-checkout':case 'billing-portal':await action(el,async()=>{const a=await api('/billing/'+name.split('-')[1],'POST');window.open(a.url,'_blank','noopener,noreferrer')||location.assign(a.url);});break;
 }
}
document.addEventListener('click',e=>{const t=e.target.closest('[data-action]');if(!t||t.disabled)return;e.preventDefault();onAction(t.dataset.action,t.dataset.id,t).catch(e=>toast(e.message||'Could not finish the action.','error'));});
$('#mobile-shade').addEventListener('click',()=>mobile(false));
window.addEventListener('hashchange',()=>route().catch(e=>toast(e.message,'error')));
window.addEventListener('beforeunload',e=>{if(state.editor?.dirty()||state.upload?.running){e.preventDefault();e.returnValue='';}});

async function init(){
 const [info,samples,presets]=await Promise.allSettled([api('/me'),api('/samples'),api('/presets')]);
 if(info.status==='fulfilled'){state.me=info.value.user;state.config=info.value.config;}
 if(samples.status==='fulfilled')state.samples=samples.value;
 if(presets.status==='fulfilled')state.presets=presets.value;
 await Promise.allSettled([loadProjects(),loadUsage(),loadBrand(),loadJobs()]);state.ready=true;
 await route();if(info.status==='rejected')toast(info.reason.message,'error');
 try{
  const q=new URLSearchParams(location.search);
  if(q.get('entry')==='signin'){
   if(!state.me||state.me.guest)authDialog('login');
  }else if(q.get('sample')){
   const sId=q.get('sample');
   if(state.samples.some(x=>x.id===sId)){
    const existing=state.projects.find(p=>p.sample===sId);
    if(existing&&existing.status==='ready'){go(`project/${existing.id}`);}
    else{const p=await api(`/samples/${sId}/open`,'POST');await loadProjects();go(`project/${p.id}`);}
   }
  }
 }catch(_){}
}
route().catch(()=>{});init().catch(e=>toast(e.message,'error'));
setInterval(async()=>{
 if(state.polling||!state.me||document.visibilityState==='hidden')return;const screen=state.screen;state.polling=true;
 try{
  if(screen==='project')await refreshProject();
  if(screen==='exports'){const prev=state.jobs;await loadJobs();if(state.screen==='exports'&&JSON.stringify(prev)!==JSON.stringify(state.jobs)){const finished=state.jobs.find(x=>x.status==='done'&&prev.some(j=>j.id===x.id&&['queued','running'].includes(j.status)));if(finished)toast('Your MP4 is ready to download.');fillExports();}}
  if(['home','projects'].includes(screen)){const key=JSON.stringify(state.projects.map(keyFor));await loadProjects();if(state.screen===screen&&key!==JSON.stringify(state.projects.map(keyFor)))fillCards(screen==='home');}
 }catch(e){if(e.status===401){state.me=null;state.projects=[];state.jobs=[];state.use=null;chrome();}}finally{state.polling=false;}
},2000);
