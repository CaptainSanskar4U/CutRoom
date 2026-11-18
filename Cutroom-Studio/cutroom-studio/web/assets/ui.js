const icons = {
 home:'<path d="m3 10 9-7 9 7v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><path d="M9 21v-7h6v7"/>', folder:'<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z"/>', palette:'<path d="M12 3a9 9 0 1 0 0 18h1.4a1.9 1.9 0 0 0 1.3-3.2 1.9 1.9 0 0 1 1.3-3.3H18a3 3 0 0 0 3-3c0-4.7-4-8.5-9-8.5Z"/><path d="M7.5 10h.01M11 6.5h.01m4 .5h.01m2.5 3.5h.01" stroke-width="2.8"/>', download:'<path d="M12 3v12m-4-4 4 4 4-4M5 16v4h14v-4"/>', settings:'<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .35 1.9l.06.06-2.8 2.8-.06-.06a1.7 1.7 0 0 0-1.9-.35 1.7 1.7 0 0 0-1 1.55V21h-4v-.1A1.7 1.7 0 0 0 9 19.35a1.7 1.7 0 0 0-1.9.35l-.06.06-2.8-2.8.06-.06a1.7 1.7 0 0 0 .35-1.9 1.7 1.7 0 0 0-1.55-1H3v-4h.1A1.7 1.7 0 0 0 4.65 9a1.7 1.7 0 0 0-.35-1.9l-.06-.06 2.8-2.8.06.06a1.7 1.7 0 0 0 1.9.35 1.7 1.7 0 0 0 1-1.55V3h4v.1A1.7 1.7 0 0 0 15 4.65a1.7 1.7 0 0 0 1.9-.35l.06-.06 2.8 2.8-.06.06a1.7 1.7 0 0 0-.35 1.9 1.7 1.7 0 0 0 1.55 1h.1v4h-.1a1.7 1.7 0 0 0-1.5 1Z"/>', help:'<circle cx="12" cy="12" r="9"/><path d="M9.1 9.1a3 3 0 0 1 5.8 1.05c0 2-2.9 2.3-2.9 4m0 2.9h.01"/>', chevron:'<path d="m9 18 6-6-6-6"/>', down:'<path d="m6 9 6 6 6-6"/>', plus:'<path d="M12 5v14M5 12h14"/>', sparkle:'<path d="M10.5 3.5 12.6 9l5.4 2-5.4 2.1-2.1 5.4-2-5.4L3 11l5.5-2 2-5.5ZM18.5 2l.9 2.6 2.6.9-2.6.9-.9 2.6-.9-2.6-2.6-.9 2.6-.9.9-2.6Z"/>', link:'<path d="M10 13.5a4 4 0 0 0 5.7.3l4-4a4 4 0 0 0-5.7-5.7l-2.2 2.2m.2 4.2a4 4 0 0 0-5.7-.3l-4 4A4 4 0 0 0 8 19.9l2.2-2.2"/>', upload:'<path d="M12 16V4m-4 4 4-4 4 4M5 16v4h14v-4"/>', film:'<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M7 4v16m10-16v16M3 9h4m-4 6h4m10-6h4m-4 6h4"/>', video:'<rect x="3" y="5" width="13" height="14" rx="2"/><path d="m16 10 5-3v10l-5-3"/>', search:'<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 4 4"/>', arrow:'<path d="M4 12h16m-6-6 6 6-6 6"/>', back:'<path d="M20 12H4m6-6-6 6 6 6"/>', play:'<path d="m9 5 11 7-11 7Z" fill="currentColor" stroke-linejoin="round"/>', pause:'<path d="M9 5v14m6-14v14" stroke-width="3"/>', crop:'<path d="M7 3v12a2 2 0 0 0 2 2h12M3 7h12a2 2 0 0 1 2 2v12"/>', captions:'<rect x="3" y="5" width="18" height="14" rx="3"/><path d="M6 11h5m2.5 0H18m-12 3.5h3m2.5 0H18"/>', cut:'<circle cx="6" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><path d="m8.1 8.1 12 12M14 14l-6 2m2.4-5.5L20 3"/>', clock:'<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>', dots:'<circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/>', x:'<path d="m6 6 12 12M6 18 18 6"/>', grid:'<rect x="4" y="4" width="6" height="6" rx="1"/><rect x="14" y="4" width="6" height="6" rx="1"/><rect x="4" y="14" width="6" height="6" rx="1"/><rect x="14" y="14" width="6" height="6" rx="1"/>', list:'<path d="M8 6h12M8 12h12M8 18h12M4 6h.01M4 12h.01M4 18h.01"/>', menu:'<path d="M4 6h16M4 12h16M4 18h16"/>', check:'<path d="m5 12 4 4 10-10"/>', alert:'<circle cx="12" cy="12" r="9"/><path d="M12 7.5v5m0 3.3h.01"/>', refresh:'<path d="M20 7v5h-5M4 17v-5h5M6 8a7 7 0 0 1 11-2l3 3M4 15l3 3a7 7 0 0 0 11-2"/>', edit:'<path d="M12 20H5a1 1 0 0 1-1-1v-7M16 4l4 4m-9 9-4 1 1-4L18 4a2 2 0 0 1 3 3Z"/>', copy:'<rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2"/>', trash:'<path d="M4 7h16m-13 0 1 13h8l1-13M9 7V4h6v3m-5 4v5m4-5v5"/>', box:'<path d="M4 7h16v13H4zM3 4h18v3H3zm6 8h6"/>', bolt:'<path d="m13 2-9 12h7l-1 8 10-12h-7z"/>', user:'<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>', logout:'<path d="M11 4H5v16h6m-1-8h11m-4-4 4 4-4 4"/>', lock:'<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3m-4 5v2"/>', target:'<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="3"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2"/>', layers:'<path d="m12 3 9 5-9 5-9-5 9-5Zm-9 9 9 5 9-5M3 16l9 5 9-5"/>', audio:'<path d="M3 9h4l5-4v14l-5-4H3Zm13-.5a5 5 0 0 1 0 7m3-10a9 9 0 0 1 0 13"/>', mute:'<path d="M3 9h4l5-4v14l-5-4H3Zm13 1 5 5m-5 0 5-5"/>', undo:'<path d="M8 5 3 10l5 5m-5-5h11a5 5 0 0 1 0 10h-3"/>', redo:'<path d="m16 5 5 5-5 5m5-5H10a5 5 0 0 0 0 10h3"/>', skipback:'<path d="M6 5v14m13-13-9 6 9 6Z"/>', skip:'<path d="M18 5v14M5 6l9 6-9 6Z"/>', expand:'<path d="M14 4h6v6m-10 10H4v-6M20 4l-6 6M4 20l6-6"/>', text:'<path d="M4 5h16M12 5v14m-3 0h6"/>', image:'<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="8" cy="9" r="1.5"/><path d="m21 16-5-5-6 6-3-2-4 4"/>', info:'<circle cx="12" cy="12" r="9"/><path d="M12 11v5m0-8h.01"/>', external:'<path d="M13 5h6v6m0-6-8 8m5 0v6H5V8h6"/>', sliders:'<path d="M5 4v16m7-16v16m7-16v16M2 9h6m1 6h6m1-6h6"/>', sort:'<path d="M4 6h16M4 12h11M4 18h6"/>', frame:'<path d="M9 4H4v5m11-5h5v5m0 6v5h-5m-6 0H4v-5"/>', book:'<path d="M12 6a9 9 0 0 0-9-1v13a9 9 0 0 1 9 1 9 9 0 0 1 9-1V5a9 9 0 0 0-9 1Zm0 0v13"/>', rocket:'<path d="M12 16 8 12c2-6 6-9 13-9 0 7-3 11-9 13Zm-4-4H4l-1 4 4 1m5-1v4l-4 1-1-4m9-9h.01"/>', wave:'<path d="M3 12h2l2-6 3 12 3-15 3 18 2-9h3"/>'
};
export const ico=(name,size=18)=>`<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${icons[name]||icons.info}</svg>`;
export const $=(s,root=document)=>root.querySelector(s);
export const $$=(s,root=document)=>Array.from(root.querySelectorAll(s));
export const esc=(v='')=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export const clone=x=>JSON.parse(JSON.stringify(x));
export const clamp=(x,a=0,b=1)=>Math.max(a,Math.min(b,x));
export function time(t,precise=false){let x=Math.max(0,Number(t)||0); return `${Math.floor(x/60)}:${String(Math.floor(x%60)).padStart(2,'0')}${precise?'.'+String(Math.floor(x%1*100)).padStart(2,'0'):''}`;}
export const date=t=>new Intl.DateTimeFormat(undefined,{month:'short',day:'numeric'}).format(new Date(t*1000));
export const size=n=>n>=1024**3?`${(n/1024**3).toFixed(1)} GB`:n>=1024**2?`${(n/1024**2).toFixed(1)} MB`:`${Math.max(0,Math.round((n||0)/1024))} KB`;
export const option=(value,label,selected)=>`<option value="${esc(value)}" ${value===selected?'selected':''}>${esc(label)}</option>`;
export const btn=(label,icon,{kind='plain',attrs='',tag='button'}={})=>`<${tag} ${tag==='button'?'type="button"':''} class="btn ${kind}" ${attrs}>${icon?ico(icon):''}<span>${esc(label)}</span></${tag}>`;
export const iconBtn=(label,icon,attrs='')=>`<button type="button" class="icon-btn" title="${esc(label)}" aria-label="${esc(label)}" ${attrs}>${ico(icon)}</button>`;
export const blank=(icon,title,body,action='')=>`<div class="blank"><span class="blank-icon">${ico(icon,23)}</span><h3>${esc(title)}</h3><p>${esc(body)}</p>${action}</div>`;
export const spinner=(label='Loading…')=>`<div class="loading" role="status"><span class="spinner"></span>${esc(label)}</div>`;
export const go=(url)=>{location.hash=url;};
export const durationChoices=['auto','short','medium','long'];
export const durationLabel={auto:'Smart length',short:'10–30 seconds',medium:'25–60 seconds',long:'45–115 seconds'};
export const ratios=['9:16','16:9','1:1','4:5'];
export const languages={auto:'Auto-detect',en:'English',hi:'Hindi',es:'Spanish',fr:'French',pt:'Portuguese',de:'German',ja:'Japanese',zh:'Chinese',ko:'Korean',ta:'Tamil',mr:'Marathi',ar:'Arabic',it:'Italian',nl:'Dutch',ru:'Russian',id:'Indonesian'};
export const capNames={pulse:'Pulse (Pop & Pill)',hormozi:'Hormozi (Bold Impact)',beast:'Beast (Viral Pop)',cinema:'Cinema (Minimal Glow)',studio:'Studio (Clean)',spotlight:'Spotlight (Boxed)',mono:'Mono (Tech)'};
export const layoutChoices={fit:'Center Fit (Original Aspect Ratio)',track:'Full Screen (Edge-to-Edge)'};
export const subtitleLanguages={auto:'Same as Spoken / Auto',en:'English',hi:'Hindi',es:'Spanish',fr:'French',pt:'Portuguese',de:'German',ja:'Japanese',zh:'Chinese',ko:'Korean',ta:'Tamil',mr:'Marathi',ar:'Arabic',it:'Italian',nl:'Dutch',ru:'Russian',id:'Indonesian'};

export class ApiError extends Error{constructor(message,status,detail){super(message);this.status=status;this.detail=detail;}}
function msg(detail,fallback){return typeof detail==='string'?detail:Array.isArray(detail)?detail.map(e=>`${e.loc?.slice(1).join(' › ')||'Value'}: ${String(e.msg).replace(/^Value error, /,'')}`).join(' · '):detail?.message||fallback;}
export async function api(path,method='GET',payload){
 let options={method,credentials:'include',headers:{Accept:'application/json'}};
 if(payload!==undefined){options.body=JSON.stringify(payload);options.headers['Content-Type']='application/json';}
 let r;
 let attempts=3;
 while(attempts>0){
  try{
   r=await fetch('/api'+path,options);
   if(r&&r.status<500)break;
   attempts--;
   if(attempts<=0)break;
   await new Promise(res=>setTimeout(res,600));
  }catch(err){
   attempts--;
   if(attempts<=0){
    const offline=!navigator.onLine;
    throw new ApiError(offline?'No internet connection. Please check your network.':'CutRoom Studio is momentarily reconnecting. Please try again in a few seconds.',0);
   }
   await new Promise(res=>setTimeout(res,700));
  }
 }
 if(!r)throw new ApiError('Could not reach CutRoom Studio. Ensure the server is running on port 3000.',0);
 if(r.status===204)return null;
 let data=null;try{data=await r.json();}catch{}
 if(!r.ok)throw new ApiError(msg(data?.detail,`Request could not finish (${r.status}).`),r.status,data?.detail);
 return data;
}
export async function sendAsset(file,kind){
 const r=await fetch(`/api/assets?kind=${encodeURIComponent(kind)}&name=${encodeURIComponent(file.name)}`,{method:'POST',headers:{'Content-Type':'application/octet-stream'},body:file,credentials:'same-origin'});
 const x=await r.json();if(!r.ok)throw new ApiError(msg(x.detail,'Could not upload asset.'),r.status,x.detail);return x;
}
export function chunk(id,file,start,end,progress,handoff){
 return new Promise((resolve,reject)=>{
  const r=new XMLHttpRequest();r.open('PATCH',`/api/projects/${id}/upload`);r.setRequestHeader('Content-Type','application/octet-stream');r.setRequestHeader('Upload-Offset',String(start));r.timeout=120000;
  r.upload.onprogress=e=>{if(e.lengthComputable)progress(start+e.loaded);};
  r.onload=()=>{let x;try{x=JSON.parse(r.responseText);}catch{};if(r.status>=200&&r.status<300)resolve(x.offset);else reject(new ApiError(msg(x?.detail,`Upload interrupted (${r.status}).`),r.status,x?.detail));};
  r.onerror=r.ontimeout=()=>reject(new ApiError('Upload connection interrupted. Your completed chunks were kept.',0));
  r.onabort=()=>reject(new ApiError('Upload paused.',0)); handoff(r);r.send(file.slice(start,end));
 });
}

const dialog=$('#dialog');
let onClose=null;
export function closeModal(){ if(dialog.open)dialog.close(); }
dialog.addEventListener('close',()=>{if(dialog.open)return;const f=onClose; onClose=null;f?.();dialog.innerHTML='';});
dialog.addEventListener('click',e=>{if(e.target===dialog)closeModal();});
export function modal({title,kicker='',body,wide=false,closed,closeLabel='Close dialog'}){
 if(dialog.open){const f=onClose; onClose=null; f?.();}
 dialog.classList.toggle('wide',wide);
 dialog.innerHTML=`<div class="dialog-inner"><header class="dialog-heading"><div>${kicker?`<p class="eyebrow">${esc(kicker)}</p>`:''}<h2 id="dialog-title">${esc(title)}</h2></div>${iconBtn(closeLabel,'x','data-close')}</header>${body}</div>`;
 dialog.setAttribute('aria-labelledby','dialog-title');onClose=closed;
 $('[data-close]',dialog).onclick=closeModal; if(!dialog.open)dialog.showModal(); return dialog;
}
export function toast(text,kind='ok'){
 const note=document.createElement('div');note.className=`toast ${kind}`;note.innerHTML=`<span class="toast-icon">${ico(kind==='error'?'alert':'check')}</span><span>${esc(text)}</span>${iconBtn('Dismiss message','x')}`;
 $('#toasts').append(note);$('button',note).onclick=()=>note.remove();setTimeout(()=>note.remove(),kind==='error'?7500:4600);
}
export function formError(form,message=''){const n=$('.form-error',form);if(n){n.textContent=message;n.hidden=!message;}}
export async function action(button,fn){
 if(button?.disabled)return;const previous=button?.innerHTML;if(button){button.disabled=true;button.setAttribute('aria-busy','true');button.innerHTML=`<span class="spinner mini"></span><span>Working…</span>`;}
 try{return await fn();}catch(e){toast(e.message||'Something went wrong.','error');}finally{if(button?.isConnected){button.disabled=false;button.removeAttribute('aria-busy');button.innerHTML=previous;}}
}
export async function copy(text){try{await navigator.clipboard.writeText(text);toast('Copied to clipboard.');}catch{const d=modal({title:'Copy social caption',body:`<textarea rows="6" readonly>${esc(text)}</textarea>`});$('textarea',d).select();}}
export function progress(n){return `<div class="progress" role="progressbar" aria-label="Progress" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${n}"><span style="width:${clamp(n,0,100)}%"></span></div>`;}
