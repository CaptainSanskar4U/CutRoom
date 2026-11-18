import { ico, $, $$, esc, clone, clamp, time, option, btn, iconBtn, ratios, capNames, api, sendAsset, modal, closeModal, toast, formError, action, copy } from './ui.js';

const FONT = ['DejaVu Sans', 'Liberation Sans', 'Liberation Serif', 'DejaVu Sans Mono', 'Noto Sans'];
const FILLERS = new Set(['um', 'uh', 'erm', 'umm', 'uhh', 'ah', 'hmm', 'er']);
const FRAMES = { fit: 'Center Fit', track: 'Full Screen' };
const TABS = [['captions', 'captions', 'Captions'], ['frame', 'crop', 'Framing'], ['layers', 'layers', 'Layers'], ['audio', 'audio', 'Audio']];
function atTrack(track, t) {
  if (!track.length) return [.5, .5, .30, .50, .70, .50]; let low = 0, hi = track.length; while (low < hi) { let m = (low + hi) >> 1; if (track[m].t <= t) low = m + 1; else hi = m; }
  const a = track[Math.max(0, low - 1)], b = track[Math.min(track.length - 1, low)], k = a === b || b.cut ? 0 : clamp((t - a.t) / Math.max(.001, b.t - a.t));
  const vector = q => [q.x, q.y, ...(q.p?.[0] || [.3, q.y]), ...(q.p?.[1] || [.7, q.y])]; const B = vector(b); return vector(a).map((x, i) => x + (B[i] - x) * k);
}
function merged(cuts, start, end) { let cursor = start; const out = []; for (const q of [...cuts].sort((a, b) => a.s - b.s)) { const s = Math.max(start, q.s), e = Math.min(end, q.e); if (e <= s || e <= cursor) continue; if (s > cursor + .02) out.push([cursor, s]); cursor = Math.max(cursor, e); } if (end > cursor + .02) out.push([cursor, end]); return out; }
function groups(words, n) { let out = [], cur = []; for (const w of words) { if (cur.length && (cur.length >= n || w.s - cur.at(-1).e > .42 || w.s - cur[0].s > 2.35 || (cur.length > 1 && /[.!?。！？]["”']?$/.test(cur.at(-1).t)))) { out.push(cur); cur = []; } cur.push(w); } if (cur.length) out.push(cur); return out; }
function formField(label, key, values, kind = 'number', extra = '') {
  const v = key.split('.').reduce((p, k) => p[k], values); return `<label class="field">${esc(label)}<input data-set="${key}" type="${kind}" value="${esc(v)}" ${extra}></label>`;
}
function check(label, key, v) { return `<label class="check-label"><input type="checkbox" data-set="${key}" ${v ? 'checked' : ''}> ${esc(label)}</label>`; }
function selection(label, key, opts, val) { return `<label class="field">${esc(label)}<select data-set="${key}">${opts.map(([k, n]) => option(String(k), n, String(val ?? ''))).join('')}</select></label>`; }
function firstWord(tokens, w) { return tokens.some(q => q.i === w.i); }

export function openEditor(root, { clip, project, analysis, presets, brands, assets, exportClip, showScore, onAsset }) {
  let draft = pick(clip), past = [], future = [], serverVersion = clip.version, committed = JSON.stringify(draft), tab = 'captions', wordFilter = '', savedText = 'All changes saved', seekTo = clip.start_at, t = seekTo, muted = false, raf = 0, ready = false, active = true, saving = null;
  let captionGroups = [], displayWords = [], keep = [], durationOut = 0, capIndex = '', layersIndex = '', lastActive = null, ctx = null, gain = null, frameWidth = 0, frameHeight = 0, drag = null;
  const fontsLoaded = new Set();
  const assetsLocal = [...assets];
  const full = Math.max(.6, Number(project.info.duration));
  const isCenterFitRendered = () => draft.edit.framing === 'fit' && !!clip.video;
  const clock = () => {
    const raw = Number.isFinite(video.currentTime) && ready ? video.currentTime : seekTo;
    return isCenterFitRendered() ? (draft.start_at + raw) : raw;
  };
  function pick(c) { return { title: c.title, start_at: c.start_at, end_at: c.end_at, edit: clone(c.edit) }; }
  const de = (name, extras = '') => `data-ed="${name}" ${extras}`;
  const goBack = `href="#project/${project.id}"`;
  root.innerHTML = `<div class="editor"><div class="edit-header"><div class="edit-title-block"><a class="icon-btn" aria-label="Back to project" ${goBack}>${ico('back')}</a><div><span class="eyebrow">SHORT-FORM EDITOR</span><input id="edit-title" aria-label="Clip title" value="${esc(draft.title)}" maxlength="120"></div></div><div class="actions"><span class="saved-label" id="save-label" role="status">All changes saved</span>${iconBtn('Undo', 'undo', de('undo', 'disabled'))}${iconBtn('Redo', 'redo', de('redo', 'disabled'))}${btn('Save edits', 'check', { attrs: de('save') })}${btn('Export', 'download', { kind: 'primary', attrs: de('export') })}</div></div>
 <div class="edit-grid"><section class="edit-panel"><header class="edit-panel-title"><div class="row">${ico('captions', 16)}<h3>Transcript</h3></div>${clip.score != null ? `<button class="score-flag" ${de('score')}>${ico('bolt', 12)} ${clip.score}</button>` : ''}</header><label class="search transcript-search">${ico('search', 14)}<span class="sr-only">Search transcript</span><input id="word-search" placeholder="Find words in this clip"></label><div class="transcript-area" id="transcript-words"></div></section>
 <section class="player" aria-label="Clip preview"><div class="player-bar"><div class="row">${ico('frame', 14)}<b>PREVIEW</b></div><div class="ratio-row" id="player-ratios"></div></div><div class="player-stage" id="player-stage"><div class="canvas-frame" id="canvas-frame"><div class="pane primary"><video id="clip-player" src="${esc(project.preview)}" preload="auto" playsinline></video></div><div class="pane secondary"><video id="split-player" preload="none" muted playsinline></video></div><div class="layers-preview"></div><div class="captions-preview"></div><div class="preview-fade"></div><button type="button" class="canvas-start" ${de('play')} aria-label="Play clip">${ico('play', 21)}</button></div></div>
 <div class="player-controls">${iconBtn('Jump to clip start', 'skipback', de('jump-start'))}<button class="icon-btn play-round" ${de('play', 'id="play-button"')} aria-label="Play clip">${ico('play', 16)}</button>${iconBtn('Jump to clip end', 'skip', de('jump-end'))}<span class="duration-read" id="player-time">${time(0, true)} / ${time(draft.end_at - draft.start_at)}</span><span class="push"></span><span class="player-label" id="frame-label">Auto track</span>${iconBtn('Toggle preview audio', 'audio', de('mute', 'id="preview-mute"'))}${iconBtn('Expand preview', 'expand', de('expand'))}</div></section>
 <section class="edit-panel edit-settings"><header class="edit-panel-title"><div class="row">${ico('sliders', 15)}<h3>Inspector</h3></div><span class="badge violet" id="format-badge">${draft.edit.ratio}</span></header><div class="panel-tabs" id="panel-tabs"></div><div class="panel-settings" id="panel-settings"></div></section></div>
 <section class="timeline" aria-label="Source timeline"><header class="timeline-head"><h3>${ico('wave', 16)} Timeline</h3><div class="actions"><span class="inline-note" id="timeline-duration"></span>${btn('Set in', 'skipback', { attrs: de('mark-in') })}${btn('Set out', 'skip', { attrs: de('mark-out') })}${btn('Speech cleanup', 'cut', { attrs: de('cleanup') })}</div></header><div class="timeline-inner"><div class="ruler">${Array.from({ length: 9 }, (_, i) => `<span>${time(full * i / 8)}</span>`).join('')}</div><div class="timeline-track" id="timeline-track" aria-label="Seek source"><div class="waveform" aria-hidden="true">${analysis.waveform?.length ? analysis.waveform.map(h => `<span style="height:${Math.round(h * 96) + 3}%"></span>`).join('') : '<span style="height:1px;background:#b9a7c8"></span>'}</div><div class="timeline-selection"></div><div id="cut-areas"></div><button type="button" role="slider" aria-label="Clip start" aria-valuemin="0" aria-valuemax="${full}" class="track-handle first" data-handle="start_at"></button><button type="button" role="slider" aria-label="Clip end" aria-valuemin="0" aria-valuemax="${full}" class="track-handle last" data-handle="end_at"></button><div class="playhead"></div></div></div><div class="tl-footer"><span>Source time <strong id="source-time">${time(t, true)}</strong></span><div class="trim-inline"><label>In <input data-bound="start_at" type="number" min="0" max="${full}" step="0.01" aria-label="Trim start in seconds"></label><label>Out <input data-bound="end_at" type="number" min="0.5" max="${full}" step="0.01" aria-label="Trim end in seconds"></label><span>sec</span></div></div></section></div>`;
  const video = $('#clip-player', root), secondary = $('#split-player', root), stage = $('#player-stage', root), frame = $('#canvas-frame', root), pane = $('.pane.primary', root), pane2 = $('.pane.secondary', root);
  const inspector = $('#panel-settings', root), wordsEl = $('#transcript-words', root), transcriptSearch = $('#word-search', root), titleEl = $('#edit-title', root), timeEl = $('#player-time', root), pHead = $('.playhead', root);
  const rail = $('#timeline-track', root), vplay = $('#play-button', root), playOverlay = $('.canvas-start', root), capPreview = $('.captions-preview', root), layerPreview = $('.layers-preview', root), fadePreview = $('.preview-fade', root);
  const pclip = () => ({ id: clip.id, title: draft.title });
  function btnSaved() {
    $('#save-label', root).textContent = saving ? 'Saving…' : dirty() ? 'Unsaved edits' : savedText;
    const undo = $('[data-ed=undo]', root), redo = $('[data-ed=redo]', root); undo.disabled = !past.length; redo.disabled = !future.length;
  }
  function dirty() { return JSON.stringify(draft) !== committed; }
  function history() { past.push(clone(draft)); if (past.length > 55) past.shift(); future = []; }
  function change(f, areas = true) { const old = JSON.stringify(draft); const before = clone(draft); f(draft); if (JSON.stringify(draft) === old) return; past.push(before); if (past.length > 55) past.shift(); future = []; refresh(areas); }
  function undo(reverse = false) {
    const x = reverse ? future : past, y = reverse ? past : future; if (!x.length) return; y.push(clone(draft)); draft = x.pop(); refresh(true);
  }
  function ratioButtons() { return ratios.map(k => `<button type="button" class="ratio-btn ${k === draft.edit.ratio ? 'selected' : ''}" ${de('ratio', `data-value="${k}"`)} aria-pressed="${k === draft.edit.ratio}">${k}</button>`).join(''); }
  function currentWords() {
    const mods = new Map(draft.edit.word_edits.map(w => [w.i, w]));
    return analysis.words.map(w => ({ ...w, ...(mods.get(w.i) || {}) }));
  }
  function visibleGroups() {
    const cap = draft.edit.caption;
    displayWords = currentWords().filter(w => w.s < draft.end_at && w.e > draft.start_at).sort((a, b) => a.s - b.s || a.i - b.i);
    const visible = (cap.offset === 0 ? displayWords : currentWords()).filter(w => w.t.trim() && w.s + cap.offset < draft.end_at && w.e + cap.offset > draft.start_at).map(w => ({ ...w, s: Math.max(draft.start_at, w.s + cap.offset), e: Math.min(draft.end_at, w.e + cap.offset) })).sort((a, b) => a.s - b.s || a.i - b.i);
    captionGroups = groups(visible, cap.words); keep = merged(draft.edit.cuts, draft.start_at, draft.end_at); durationOut = keep.reduce((sum, [a, b]) => sum + b - a, 0); capIndex = ''; layersIndex = '';
  }
  function fillTranscript() {
    const word = wordFilter.toLowerCase().trim(); let row = [], rows = [];
    for (const w of displayWords) { if (row.length && (row.length >= 12 || w.s - row.at(-1).e > .75 || w.speaker !== row[0].speaker)) { rows.push(row); row = []; } row.push(w); }
    if (row.length) rows.push(row); if (word) rows = rows.filter(g => g.map(w => w.t).join(' ').toLowerCase().includes(word));
    const scroll = wordsEl.scrollTop;
    wordsEl.innerHTML = rows.length ? rows.map(g => `<div class="tr-row"><div class="tr-meta"><button type="button" class="tr-time" ${de('seek', `data-value="${g[0].s}"`)}>${time(g[0].s, true)}</button><span>${g[0].speaker ? `Speaker ${g[0].speaker}` : 'Source words'}</span></div><div class="tr-words">${g.map(w => { const removed = !w.t || draft.edit.cuts.some(c => w.s >= c.s - .025 && w.e <= c.e + .025); return `<button type="button" title="Edit ${esc(w.t || 'removed word')}" class="tr-word ${removed ? 'removed' : ''} ${FILLERS.has(w.t.toLowerCase().replace(/[^a-z]/g, '')) ? 'filler' : ''}" ${de('word', `data-index="${w.i}"`)}>${esc(w.t || '‹removed›')}</button>`; }).join('')}</div></div>`).join('') : `<p class="no-words">${word ? 'No matching words.' : 'No speech in the selected range.'}</p>`;
    wordsEl.scrollTop = scroll; lastActive = null;
  }
  function fontFor(cap) {
    if (!cap.font_id) return `"${cap.font}",Arial,sans-serif`;
    const found = assetsLocal.find(a => a.id === cap.font_id && a.kind === 'font'); if (!found) return `"${cap.font}",Arial,sans-serif`;
    const name = 'cutroom-' + cap.font_id;
    if (!fontsLoaded.has(name)) { fontsLoaded.add(name); const ff = new FontFace(name, `url(${found.url})`, { weight: 'normal' }); ff.load().then(f => { if (active) { document.fonts.add(f); capIndex = ''; draw(); } }).catch(() => { }); }
    return `"${name}",Arial,sans-serif`;
  }
  function addAsset(a) { assetsLocal.unshift(a); onAsset(a); }
  function controls() {
    const e = draft.edit, c = e.caption;
    $('#panel-tabs', root).innerHTML = TABS.map(([id, i, n]) => `<button type="button" class="${tab === id ? 'selected' : ''}" ${de('tab', `data-value="${id}"`)} aria-pressed="${tab === id}">${ico(i, 14)} ${n}</button>`).join('');
    if (tab === 'captions') inspector.innerHTML = `${check('Burn captions into export', 'caption.enabled', c.enabled)}<div class="preset-grid">${Object.entries(capNames).map(([k, label]) => `<button type="button" class="cap-preset ${c.preset === k ? 'selected' : ''}" ${de('preset', `data-value="${k}"`)}>${label}<span>${{ pulse: 'Animated', studio: 'Simple', spotlight: 'Boxed', mono: 'Monospace' }[k]}</span></button>`).join('')}</div>
  ${selection('Font', 'caption.font', FONT.map(k => [k, k]), c.font)}${assetsLocal.some(a => a.kind === 'font') ? selection('Custom font', 'caption.font_id', [['', 'Use base font'], ...assetsLocal.filter(a => a.kind === 'font').map(a => [a.id, a.name])], c.font_id) : ''}${btn('Upload font', 'upload', { attrs: de('upload-font') })}<input type="file" id="edit-font-file" accept=".ttf,.otf" hidden>
  <div class="grid2">${formField('Size', 'caption.size', e, 'number', 'min="20" max="110"')}${formField('Words per group', 'caption.words', e, 'number', 'min="1" max="8"')}${formField('Text', 'caption.color', e, 'color')}${formField('Highlight', 'caption.highlight', e, 'color')}${formField('Outline color', 'caption.outline_color', e, 'color')}${formField('Outline', 'caption.outline', e, 'number', 'min="0" max="12"')}${formField('Shadow', 'caption.shadow', e, 'number', 'min="0" max="12"')}${formField('Offset (sec)', 'caption.offset', e, 'number', 'min="-10" max="10" step=".05"')}</div>
  ${check('Caption background', 'cap-bg', !!c.background)}${c.background ? formField('Background color', 'caption.background', e, 'color') : ''}${formField('Vertical position', 'caption.position', e, 'range', 'min=".08" max=".93" step=".01"')}${selection('Highlight animation', 'caption.motion', [['pop', 'Pop'], ['word', 'Word highlight'], ['none', 'None']], c.motion)}${check('Uppercase', 'caption.uppercase', c.uppercase)}`;
    if (tab === 'frame') inspector.innerHTML = `<h4>Output aspect ratio</h4><div class="ratio-row">${ratioButtons()}</div>${selection('Layout', 'framing', Object.entries(FRAMES), e.framing === 'fit' ? 'fit' : 'track')}
  ${e.framing === 'fit' ? '<p class="control-note">Center Fit: Keeps original video centered with an ambient blurred background. Nothing is cropped.</p>' : '<p class="control-note">Full Screen: Video fills the entire screen edge-to-edge with smart face tracking and safe headroom.</p>'}`;
    if (tab === 'layers') inspector.innerHTML = `<h4>Text and image layers</h4><div class="actions">${btn('Add text', 'text', { attrs: de('new-text') })}${btn('Add image', 'image', { attrs: de('new-image') })}</div>
  ${e.overlays.length ? e.overlays.map((o, i) => `<div class="layer-line"><div class="row" style="min-width:0">${ico(o.type === 'image' ? 'image' : 'text', 12)} <span class="layer-name">${esc(o.type === 'text' ? o.text : assetsLocal.find(a => a.id === o.asset)?.name || 'Image layer')}</span></div><div class="row" style="gap:0">${iconBtn('Edit layer', 'edit', de('layer-edit', `data-index="${i}"`))}${iconBtn('Remove layer', 'trash', de('layer-delete', `data-index="${i}"`))}</div></div>`).join('') : '<p class="control-note">No layers yet. Add a title, logo, or timed image cutaway.</p>'}
  ${clip.insights.broll?.length ? `<h4>B-roll search ideas</h4><div class="broll-tags">${clip.insights.broll.map(t => `<span class="badge violet">${esc(t)}</span>`).join('')}</div><p class="tiny muted">Upload an image you have permission to use and set a layer timing.</p>` : ''}
  ${clip.insights.social ? btn('Copy suggested social caption', 'copy', { attrs: de('social') }) : ''}`;
    if (tab === 'audio') inspector.innerHTML = `<h4>Source audio</h4>${formField('Volume (1 = original)', 'volume', e, 'range', 'min="0" max="2" step=".02"')}<p class="control-note">${project.info.audio ? `Current level: ${Math.round(e.volume * 100)}%. Export audio is AAC.` : 'This source has no audio track.'}</p>${btn(e.volume === 0 ? 'Restore audio' : 'Mute exported audio', e.volume === 0 ? 'audio' : 'mute', { attrs: de('audio-toggle') })}<h4>Speech cleanup</h4>${btn('Review gaps and fillers', 'cut', { attrs: de('cleanup') })}<p class="tiny muted">${e.cuts.length ? `${e.cuts.length} cut${e.cuts.length === 1 ? '' : 's'} applied to audio and video.` : 'No speech cuts applied.'}</p>${e.cuts.length ? btn('Clear speech cuts', 'x', { attrs: de('clear-cuts') }) : ''}`;
    const inp = $('#edit-font-file', root); if (inp) inp.onchange = () => { if (!inp.files[0]) return; action($('[data-ed=upload-font]', root), async () => { const a = await sendAsset(inp.files[0], 'font'); addAsset(a); change(d => d.edit.caption.font_id = a.id); toast('Custom font uploaded.'); }); };
  }
  function renderTimeline() {
    const s = clamp(draft.start_at / full) * 100, e = clamp(draft.end_at / full) * 100;
    const first = $('[data-handle=start_at]', root), last = $('[data-handle=end_at]', root), selection = $('.timeline-selection', root);
    selection.style.left = s + '%'; selection.style.width = (e - s) + '%'; first.style.left = s + '%'; last.style.left = e + '%'; first.setAttribute('aria-valuenow', draft.start_at.toFixed(2)); last.setAttribute('aria-valuenow', draft.end_at.toFixed(2));
    for (const key of ['start_at', 'end_at']) { const el = $(`[data-bound=${key}]`, root); if (document.activeElement !== el) el.value = draft[key].toFixed(2); }
    $('#cut-areas', root).innerHTML = draft.edit.cuts.map(c => `<div class="clean-cut" style="left:${clamp(c.s / full) * 100}%;width:${(clamp(c.e / full) - clamp(c.s / full)) * 100}%"></div>`).join('');
    $('#timeline-duration', root).textContent = `${time(durationOut, true)} output · ${time(full)} source`;
  }
  function refresh(areas = true) {
    visibleGroups(); renderTimeline(); btnSaved();
    if (areas) { fillTranscript(); controls(); $('#player-ratios', root).innerHTML = ratioButtons(); $('#format-badge', root).textContent = draft.edit.ratio; $('#frame-label', root).textContent = FRAMES[draft.edit.framing]; if (document.activeElement !== titleEl) titleEl.value = draft.title; }
    draw();
  }
  function seek(seconds) {
    seekTo = clamp(seconds, 0, Math.max(0, full - .02));
    if (ready) {
      video.currentTime = isCenterFitRendered() ? clamp(seekTo - draft.start_at, 0, durationOut) : seekTo;
    }
    t = seekTo; draw();
  }
  function skipCuts(at) {
    if (!keep.length) return draft.end_at;
    for (const [s, e] of keep) { if (at < s) return s; if (at < e) return at; }
    return draft.end_at;
  }
  function elapsedOut(x) { let elapsed = 0; for (const [s, e] of keep) elapsed += Math.max(0, Math.min(x, e) - s); return elapsed; }
  function constructAudio() {
    if (ctx || !project.info.audio || typeof AudioContext === 'undefined' || draft.edit.volume <= 1) return;
    try { ctx = new AudioContext(); gain = ctx.createGain(); ctx.createMediaElementSource(video).connect(gain).connect(ctx.destination); } catch { gain = null; }
  }
  function play() {
    if (!video.paused) { video.pause(); return; }
    const when = clock(); let next = when < draft.start_at || when >= draft.end_at - .07 ? (keep[0]?.[0] ?? draft.start_at) : skipCuts(when);
    if (next >= draft.end_at - .03) next = keep[0]?.[0] ?? draft.start_at; if (Math.abs(when - next) > .015) seek(next);
    constructAudio(); ctx?.resume().catch(() => { }); video.play().catch(e => { if (e.name !== 'AbortError') toast('Could not play this preview. Try reloading the page.', 'error'); });
  }
  function trim(key, val) {
    if (!Number.isFinite(val)) return;
    if (key === 'start_at') draft.start_at = Math.round(clamp(val, Math.max(0, draft.end_at - 180), draft.end_at - .5) * 1000) / 1000;
    else draft.end_at = Math.round(clamp(val, draft.start_at + .5, Math.min(full, draft.start_at + 180)) * 1000) / 1000;
  }
  function fitVideo(el, w, h, sw, sh, x, y, fit = false) {
    if (w <= 0 || h <= 0 || !sw || !sh) return;
    const scale = fit ? Math.min(w / sw, h / sh) : Math.max(w / sw, h / sh); const a = sw * scale, b = sh * scale;
    el.style.width = a.toFixed(2) + 'px'; el.style.height = b.toFixed(2) + 'px';
    const left = fit ? (w - a) / 2 : -clamp(a * x - w / 2, 0, Math.max(0, a - w)); const top = fit ? (h - b) / 2 : -clamp(b * y - h / 2, 0, Math.max(0, b - h));
    el.style.transform = `translate(${left.toFixed(2)}px,${top.toFixed(2)}px)`;
  }
  function compose() {
    const e = draft.edit, a = atTrack(analysis.track, t);
    const [x, y] = [a[0], a[1]];
    const [w, h] = e.ratio.split(':').map(Number), box = stage.getBoundingClientRect(), r = w / h;
    const boundW = box.width - 23, boundH = box.height - 18;
    frameWidth = Math.max(40, Math.min(boundW, boundH * r)); frameHeight = frameWidth / r;
    frame.style.width = frameWidth + 'px'; frame.style.height = frameHeight + 'px'; frame.style.background = e.background;
    const isCenterFitRendered = e.framing === 'fit' && !!clip.video;
    const targetSrc = isCenterFitRendered ? clip.video : project.preview;
    if (video.getAttribute('data-src') !== targetSrc) {
      video.setAttribute('data-src', targetSrc);
      video.src = targetSrc;
      video.currentTime = isCenterFitRendered ? clamp(t - draft.start_at, 0, durationOut) : t;
    }
    const sw = video.videoWidth || (isCenterFitRendered ? 720 : project.info.width), sh = video.videoHeight || (isCenterFitRendered ? 1280 : project.info.height);
    if (secondary.hasAttribute('src')) { secondary.pause(); secondary.removeAttribute('src'); secondary.load(); }
    pane2.style.display = 'none'; pane.style.width = ''; pane.style.height = ''; pane.style.left = ''; pane.style.top = '';
    if (isCenterFitRendered) {
      pane.style.width = frameWidth + 'px'; pane.style.height = frameHeight + 'px';
      video.style.width = frameWidth + 'px'; video.style.height = frameHeight + 'px';
      video.style.transform = '';
      capPreview.innerHTML = '';
      return null;
    } else {
      fitVideo(video, frameWidth, frameHeight, sw, sh, x, y, e.framing === 'fit');
    }
    const u = Math.min(frameWidth, frameHeight) / 1080, cap = e.caption;
    let active = null; if (cap.enabled) {
      let low = 0, high = captionGroups.length; while (low < high) { const i = (low + high) >> 1; if (captionGroups[i][0].s <= t) low = i + 1; else high = i; }
      const g = captionGroups[low - 1]; if (g && t < Math.max(...g.map(q => q.e))) active = g;
    }
    let current = active ? active.filter(w => w.s <= t).at(-1) : null;
    const hash = `${active?.[0]?.i ?? -1}/${current?.i ?? -1}/${frameWidth.toFixed(1)}/${e.caption.enabled}`;
    if (hash !== capIndex) { capIndex = hash; capPreview.innerHTML = active ? `<div class="caption-block" style="top:${cap.position * 100}%;font-size:${cap.size * u}px;color:${cap.color};${cap.background ? `background:${cap.background};padding:${2 * u}px ${8 * u}px;border-radius:${4 * u}px;` : ''}-webkit-text-stroke:${cap.outline * u * .52}px ${cap.outline_color};paint-order:stroke fill;text-shadow:${cap.shadow * u}px ${cap.shadow * u}px ${cap.shadow * u * .7}px #160d20">${active.map(w => `<span class="${current?.i === w.i && cap.motion !== 'none' ? 'em ' + cap.motion : ''}" ${current?.i === w.i && cap.motion !== 'none' ? `style="color:${cap.highlight}"` : ''}>${esc(cap.uppercase ? w.t.toUpperCase() : w.t)}</span>`).join(' ')}</div>` : ''; const label = $('.caption-block', capPreview); if (label) label.style.fontFamily = fontFor(cap); }
    const showing = e.overlays.map((o, i) => [o, i]).filter(([o]) => t >= (o.start ?? draft.start_at) && t < (o.end ?? draft.end_at));
    const hash2 = showing.map(o => o[1]).join(',') + '/' + frameWidth.toFixed(1) + '/' + e.watermark;
    if (hash2 !== layersIndex) { layersIndex = hash2; layerPreview.innerHTML = showing.map(([o]) => o.type === 'image' ? `<img class="layer-image" alt="" src="/api/assets/${o.asset}" style="left:${o.x * 100}%;top:${o.y * 100}%;width:${o.width * 100}%">` : `<span class="layer-text" style="left:${o.x * 100}%;top:${o.y * 100}%;color:${o.color};font-size:${o.size * u}px">${esc(o.text)}</span>`).join('') + (e.watermark ? '<span class="preview-stamp">CUTROOM</span>' : ''); }
    const elapsed = elapsedOut(t), fade = Math.min(e.fade, durationOut / 2), factor = fade > 0 ? clamp(Math.min(elapsed, durationOut - elapsed) / fade) : 1;
    fadePreview.style.opacity = String(1 - factor);
    if (gain) gain.gain.value = e.volume * factor; if (!gain) video.volume = clamp(e.volume * factor); video.muted = muted;
    return current;
  }
  function draw() {
    if (!active) return; const here = clock();
    if (!video.paused) {
      if (isCenterFitRendered()) {
        if (video.currentTime >= durationOut - 0.04) {
          video.pause(); video.currentTime = 0; seekTo = draft.start_at;
        }
      } else {
        const next = skipCuts(Math.max(draft.start_at, here));
        if (here >= draft.end_at - .025 || next >= draft.end_at - .014) {
          video.pause(); seekTo = Math.max(draft.start_at, draft.end_at - .025); video.currentTime = seekTo;
        } else if (next > here + .03) { video.currentTime = next; }
      }
    }
    t = clock(); timeEl.textContent = `${time(elapsedOut(t), true)} / ${time(durationOut)}`; pHead.style.left = `${clamp(t / full) * 100}%`; $('#source-time', root).textContent = time(t, true);
    const kw = compose(); if (kw?.i !== lastActive) { lastActive = kw?.i ?? -1; const previous = $('.tr-word.hot', wordsEl); if (previous) previous.classList.remove('hot'); const next = $(`.tr-word[data-index="${lastActive}"]`, wordsEl); next?.classList.add('hot'); }
  }
  function loop() { draw(); if (active && !video.paused) raf = requestAnimationFrame(loop); }
  function setPlayIcon() { const on = !video.paused; vplay.innerHTML = ico(on ? 'pause' : 'play', 16); vplay.setAttribute('aria-label', on ? 'Pause clip' : 'Play clip'); playOverlay.hidden = on; }
  video.addEventListener('loadedmetadata', () => { ready = true; seek(seekTo); }); video.addEventListener('error', () => { if (active) toast('The browser could not decode this preview. Try reopening the clip.', 'error'); });
  video.addEventListener('seeked', draw); video.addEventListener('pause', () => { setPlayIcon(); cancelAnimationFrame(raf); draw(); }); video.addEventListener('play', () => { setPlayIcon(); cancelAnimationFrame(raf); loop(); });
  const resize = new ResizeObserver(draw); resize.observe(stage);
  transcriptSearch.addEventListener('input', () => { wordFilter = transcriptSearch.value; fillTranscript(); });
  titleEl.addEventListener('change', () => { const v = titleEl.value.trim(); if (v) change(d => d.title = v); else titleEl.value = draft.title; });
  function tFrom(ev) { const r = rail.getBoundingClientRect(); return clamp((ev.clientX - r.left) / Math.max(1, r.width)) * full; }
  rail.addEventListener('pointerdown', ev => { if (ev.button > 0) return; const h = ev.target.closest('[data-handle]'); const key = h?.dataset.handle || null; ev.preventDefault(); video.pause(); if (key) history(); drag = { key, id: ev.pointerId }; rail.setPointerCapture(ev.pointerId); if (!key) seek(tFrom(ev)); });
  rail.addEventListener('pointermove', ev => { if (drag?.id !== ev.pointerId) return; const seconds = tFrom(ev); if (drag.key) { trim(drag.key, seconds); seek(draft[drag.key]); refresh(false); } else seek(seconds); });
  function endDrag(e) { if (drag?.id !== e.pointerId) return; const was = drag; drag = null; if (was.key) refresh(true); }
  rail.addEventListener('pointerup', endDrag); rail.addEventListener('pointercancel', endDrag);
  rail.addEventListener('keydown', ev => { const key = ev.target.dataset.handle; if (key && ['ArrowLeft', 'ArrowRight'].includes(ev.key)) { ev.preventDefault(); const k = ev.key === 'ArrowRight' ? 1 : -1; change(() => trim(key, draft[key] + k * (ev.shiftKey ? 1 : .1))); seek(draft[key]); } });

  function wordDialog(i) {
    const w = displayWords.find(w => w.i === i); if (!w) return; video.pause(); seek(w.s);
    const d = modal({ title: 'Edit caption word', kicker: w.speaker ? 'SPEAKER ' + w.speaker : 'SOURCE TRANSCRIPT', body: `<form id="word-form" class="stack"><label class="field">Caption text<input name="word" value="${esc(w.t)}" maxlength="140"><small>Leave blank to hide the word in the captions without cutting the audio.</small></label><div class="grid2"><label class="field">Start (source seconds)<input type="number" name="start" required min="0" step=".001" max="${full}" value="${w.s}"></label><label class="field">End (source seconds)<input type="number" name="end" required min="0" step=".001" max="${full}" value="${w.e}"></label></div><p class="form-error" hidden></p><div class="dialog-footer">${btn('Cut word from video', 'cut', { kind: 'danger sm', attrs: 'id="cut-word"' })}<button type="submit" class="btn primary">Save word</button></div></form>` });
    const f = $('form', d); f.onsubmit = ev => {
      ev.preventDefault(); const val = { i: w.i, t: f.elements.word.value.trim(), s: Number(f.elements.start.value), e: Number(f.elements.end.value) }; if (val.e < val.s) { formError(f, 'End must not precede start.'); return; }
      change(x => { x.edit.word_edits = x.edit.word_edits.filter(t => t.i !== w.i); x.edit.word_edits.push(val); }); closeModal();
    };
    $('#cut-word', d).onclick = () => { if (w.e - w.s < .045) { formError(f, 'This word is too short to cut.'); return; } if (draft.edit.cuts.length >= 50) { formError(f, 'The clip can hold up to 50 cuts.'); return; } change(x => x.edit.cuts.push({ s: w.s, e: w.e })); closeModal(); };
  }
  function cleanDialog() {
    const d = modal({ title: 'Review speech cleanup', kicker: 'SPEECH TOOLS', body: `<p class="modal-lead">Review the ranges before removing them from both audio and video. Word gaps use the transcript’s timestamps; listen back for context.</p><form id="clean-form" class="stack"><label class="check-label"><input name="fill" type="checkbox" checked> Find single-word fillers</label><label class="check-label"><input name="gap" type="checkbox" checked> Find pauses between words</label><label class="field">Minimum pause (seconds)<input name="threshold" type="number" value="0.65" min="0.3" max="10" step="0.05"></label><div class="help-section" id="clean-options" style="max-height:160px;overflow:auto"></div><p class="form-error" hidden></p><div class="dialog-footer"><button type="submit" class="btn primary">Apply selected cuts</button></div></form>` });
    const f = $('form', d), list = $('#clean-options', d); let ranges = [];
    function compute() {
      ranges = []; const threshold = Math.max(.3, Number(f.elements.threshold.value) || .65);
      for (let i = 0; i < displayWords.length; i++) {
        const w = displayWords[i], next = displayWords[i + 1]; if (f.elements.fill.checked && FILLERS.has(w.t.toLowerCase().replace(/[^a-z]/g, '')) && w.e - w.s > .085) ranges.push({ s: Math.max(draft.start_at, w.s + .01), e: Math.min(draft.end_at, w.e - .01), label: `Filler: “${w.t}”` });
        if (f.elements.gap.checked && next && next.s - w.e >= threshold) ranges.push({ s: w.e + .13, e: next.s - .13, label: 'Speech gap' });
      }
      ranges = ranges.filter(r => r.e - r.s > .04 && !draft.edit.cuts.some(q => q.s <= r.s + .025 && q.e >= r.e - .025)).slice(0, 50);
      list.innerHTML = ranges.length ? ranges.map((r, i) => `<label class="check-label"><input type="checkbox" name="range" value="${i}" checked> ${esc(r.label)} · ${time(r.s, true)}–${time(r.e, true)}</label>`).join('') : '<span class="muted small">No matching ranges were found.</span>';
    }
    f.addEventListener('change', e => { if (e.target.name !== 'range') compute(); }); compute();
    f.onsubmit = e => { e.preventDefault(); const selected = new FormData(f).getAll('range').map(i => { const { s, e } = ranges[Number(i)]; return { s, e }; }); if (!selected.length) { formError(f, 'Select at least one range.'); return; } if (selected.length + draft.edit.cuts.length > 50) { formError(f, 'Choose fewer ranges. Up to 50 cuts are supported.'); return; } change(x => x.edit.cuts.push(...selected)); closeModal(); toast(`${selected.length} speech cut${selected.length > 1 ? 's' : ''} applied.`); };
  }
  function layerForm(type, index = null) {
    if (index === null && draft.edit.overlays.length >= 10) { toast('This clip already has ten layers.', 'error'); return; }
    const o = index === null ? { type, text: '', asset: null, x: .5, y: type === 'image' ? .35 : .18, width: .32, color: '#ffffff', size: 54, start: null, end: null } : clone(draft.edit.overlays[index]);
    const d = modal({
      title: index === null ? (type === 'image' ? 'Add image layer' : 'Add text overlay') : 'Edit layer', kicker: 'VIDEO LAYERS', body: `<form id="layer-form" class="stack">${type === 'text' ? `<label class="field">Text<input name="text" maxlength="160" required value="${esc(o.text)}" placeholder="An opening headline"></label><div class="grid2"><label class="field">Text size<input name="size" type="number" required min="20" max="110" value="${o.size}"></label><label class="field">Text color<input name="color" type="color" value="${o.color}"></label></div>` : `<label class="field">Image<select name="asset">${option('', 'Select an image…', o.asset || '')}${assetsLocal.filter(a => a.kind === 'image').map(a => option(a.id, a.name, o.asset)).join('')}</select></label><div class="actions">${btn('Upload an image', 'upload', { attrs: 'id="layer-upload"' })}<input id="layer-file" type="file" accept="image/png,image/jpeg,image/webp" hidden></div><label class="field">Width (% of frame)<input name="width" type="number" min="8" max="100" required value="${Math.round(100 * o.width)}"></label>`}
   <div class="grid2"><label class="field">Horizontal center (%)<input name="x" type="number" min="0" max="100" required value="${Math.round(100 * o.x)}"></label><label class="field">Vertical center (%)<input name="y" type="number" min="0" max="100" required value="${Math.round(100 * o.y)}"></label><label class="field">In time (source seconds)<input name="start" type="number" min="0" max="${full}" step=".01" value="${o.start ?? ''}" placeholder="Clip start"></label><label class="field">Out time (source seconds)<input name="end" type="number" min="0" max="${full}" step=".01" value="${o.end ?? ''}" placeholder="Clip end"></label></div><p class="form-error" hidden></p><div class="dialog-footer"><button type="submit" class="btn primary">Save layer</button></div></form>`
    });
    const f = $('form', d); if (type === 'image') { const input = $('#layer-file', d), upload = $('#layer-upload', d); upload.onclick = () => input.click(); input.onchange = () => { if (!input.files[0]) return; action(upload, async () => { const a = await sendAsset(input.files[0], 'image'); addAsset(a); const b = document.createElement('option'); b.value = a.id; b.textContent = a.name; f.elements.asset.append(b); f.elements.asset.value = a.id; toast('Image uploaded.'); }); }; }
    f.onsubmit = ev => {
      ev.preventDefault(); const data = Object.fromEntries(new FormData(f)); const item = { ...o, x: Number(data.x) / 100, y: Number(data.y) / 100, start: data.start === '' ? null : Number(data.start), end: data.end === '' ? null : Number(data.end) };
      if (type === 'text') { item.text = data.text.trim(); if (!item.text) { formError(f, 'Enter some text.'); return; } item.size = Number(data.size); item.color = data.color; }
      else { item.asset = data.asset || null; item.width = Number(data.width) / 100; if (!item.asset) { formError(f, 'Choose or upload an image.'); return; } }
      if ((item.start ?? draft.start_at) >= (item.end ?? draft.end_at)) { formError(f, 'Out time must be later than in time.'); return; }
      change(x => { if (index === null) x.edit.overlays.push(item); else x.edit.overlays[index] = item; }); closeModal();
    };
  }
  function applyBrand(id) {
    const b = brands.find(x => x.id === id); if (!b) return;
    change(x => { x.edit.caption = clone(b.caption); x.edit.background = b.background; if (b.logo && x.edit.overlays.length < 10 && !x.edit.overlays.some(o => o.asset === b.logo)) x.edit.overlays.push({ type: 'image', text: '', asset: b.logo, x: .85, y: .1, width: .18, color: '#ffffff', size: 54, start: null, end: null }); }); toast('Brand kit applied.');
  }
  async function persist(notify = true) {
    if (document.activeElement === titleEl) titleEl.blur(); if (saving) return saving;
    if (!dirty()) { if (notify) toast('All changes are already saved.'); return; }
    const snapshot = JSON.stringify(draft);
    if (durationOut < .5) throw Error('Leave at least half a second in the clip.');
    saving = api(`/clips/${clip.id}`, 'PUT', { ...JSON.parse(snapshot), version: serverVersion }); btnSaved();
    try { const saved = await saving; serverVersion = saved.version; committed = snapshot; savedText = 'All changes saved'; if (notify) toast('Clip edits saved.'); }
    finally { saving = null; btnSaved(); }
  }
  function assign(path, val) {
    change(d => { const route = path.split('.'); let o = d.edit; while (route.length > 1) o = o[route.shift()]; o[route[0]] = val; });
  }
  function changed(ev) {
    const target = ev.target; const key = target.dataset.set;
    if (target.dataset.bound) { const bound = target.dataset.bound; change(() => trim(bound, Number(target.value))); target.value = draft[bound].toFixed(2); seek(draft[bound]); return; }
    if (!key) return;
    if (key === 'brand') { applyBrand(target.value); return; }
    if (key === 'cap-bg') { assign('caption.background', target.checked ? '#20162c' : null); return; }
    if (target.validity && !target.validity.valid) { target.reportValidity(); controls(); return; }
    let value = target.type === 'checkbox' ? target.checked : ['number', 'range'].includes(target.type) || key === 'fade' ? Number(target.value) : target.value;
    if (key === 'caption.font_id') value = value || null; assign(key, value);
    if (key === 'volume' && !video.paused && draft.edit.volume > 1) { constructAudio(); ctx?.resume().catch(() => { }); draw(); }
  }
  root.addEventListener('change', changed);
  function handler(ev) {
    const b = ev.target.closest('[data-ed]'); if (!b || b.disabled) return; ev.preventDefault(); const a = b.dataset.ed, v = b.dataset.value, i = Number(b.dataset.index);
    switch (a) {
      case 'tab': tab = v; controls(); break;
      case 'ratio': assign('ratio', v); break;
      case 'preset': if (presets[v]) change(d => d.edit.caption = clone(presets[v])); break;
      case 'score': showScore(); break; case 'social': copy(clip.insights.social); break;
      case 'undo': undo(); break; case 'redo': undo(true); break;
      case 'save': action(b, () => persist()); break; case 'export': video.pause(); exportClip(pclip(), () => persist(false)); break;
      case 'play': play(); break; case 'jump-start': video.pause(); seek(draft.start_at); break; case 'jump-end': video.pause(); seek(draft.end_at - .026); break; case 'seek': video.pause(); seek(Number(v)); break;
      case 'mute': muted = !muted; $('#preview-mute', root).innerHTML = ico(muted ? 'mute' : 'audio'); $('#preview-mute', root).setAttribute('aria-pressed', String(muted)); draw(); break;
      case 'expand': if (document.fullscreenElement) document.exitFullscreen?.(); else if (stage.requestFullscreen) stage.requestFullscreen().catch(() => toast('Fullscreen is not allowed in this preview.', 'error')); else toast('Fullscreen is not available in this browser.', 'error'); break;
      case 'mark-in': video.pause(); change(() => trim('start_at', clock())); break;
      case 'mark-out': video.pause(); change(() => trim('end_at', clock())); break;
      case 'audio-toggle': assign('volume', draft.edit.volume === 0 ? 1 : 0); break;
      case 'word': wordDialog(i); break;
      case 'cleanup': video.pause(); cleanDialog(); break; case 'clear-cuts': change(d => d.edit.cuts = []); break;
      case 'new-text': video.pause(); layerForm('text'); break; case 'new-image': video.pause(); layerForm('image'); break;
      case 'layer-edit': video.pause(); layerForm(draft.edit.overlays[i].type, i); break; case 'layer-delete': change(d => d.edit.overlays.splice(i, 1)); break;
      case 'upload-font': $('#edit-font-file', root)?.click(); break;
    }
  }
  root.addEventListener('click', handler);
  function hotkey(ev) {
    if ($('#dialog').open) return;
    if (['INPUT', 'TEXTAREA', 'SELECT'].includes(ev.target.tagName)) return;
    const k = ev.key.toLowerCase(); if ((ev.metaKey || ev.ctrlKey) && ['z', 's', 'y'].includes(k)) { ev.preventDefault(); if (k === 's') persist().catch(e => toast(e.message, 'error')); else undo(ev.shiftKey || k === 'y'); }
    else if (k === ' ' && !['BUTTON', 'A'].includes(ev.target.tagName)) { ev.preventDefault(); play(); }
    else if (k === 'arrowleft' || k === 'arrowright') { if (ev.target.dataset.handle) return; ev.preventDefault(); video.pause(); seek(clock() + (k === 'arrowright' ? .5 : -.5)); }
  }
  window.addEventListener('keydown', hotkey);
  refresh(true);
  return { dirty, destroy() { active = false; resize.disconnect(); cancelAnimationFrame(raf); video.pause(); secondary.pause(); ctx?.close().catch(() => { }); window.removeEventListener('keydown', hotkey); root.removeEventListener('change', changed); root.removeEventListener('click', handler); } };
}
