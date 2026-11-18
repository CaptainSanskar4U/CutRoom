import React, { useState, useRef, useEffect } from 'react';
import { 
  Play, 
  Pause, 
  RotateCcw, 
  DownloadCloud, 
  Type, 
  Palette, 
  Crop, 
  Share2, 
  Save, 
  Check, 
  Sparkles,
  Sliders,
  Scissors,
  CheckCircle2,
  AlertCircle,
  Eye,
  RefreshCw,
  Maximize2
} from 'lucide-react';
import { api } from '../api';
import { Clip, WordItem } from '../types';

interface ClipEditorProps {
  clip: Clip;
  onClipUpdated: (updated: Clip) => void;
  onBack: () => void;
  onGoToExport: () => void;
}

export const ClipEditor: React.FC<ClipEditorProps> = ({
  clip,
  onClipUpdated,
  onBack,
  onGoToExport
}) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(clip.start_time);
  const [activeTab, setActiveTab] = useState<'captions' | 'styles' | 'framing' | 'metadata'>('captions');
  
  // Editable state
  const [title, setTitle] = useState(clip.title);
  const [startTime, setStartTime] = useState(clip.start_time);
  const [endTime, setEndTime] = useState(clip.end_time);
  const [aspectRatio, setAspectRatio] = useState(clip.aspect_ratio || '9:16');
  const [cropMode, setCropMode] = useState<string>(clip.crop_mode || 'fit_blur');
  const [cropX, setCropX] = useState<number>(clip.crop_x || 0.5);
  const [cropY, setCropY] = useState<number>(clip.crop_y || 0.35);
  const [captionStyle, setCaptionStyle] = useState(clip.caption_style || 'hormozi');
  const [words, setWords] = useState<WordItem[]>(clip.custom_words || []);
  const [editingWordIdx, setEditingWordIdx] = useState<number | null>(null);

  // Render status
  const [isRendering, setIsRendering] = useState(clip.render_status === 'rendering');
  const [renderProgress, setRenderProgress] = useState(clip.render_progress || 0);
  const [isSaved, setIsSaved] = useState(false);

  const videoRef = useRef<HTMLVideoElement>(null);
  const bgVideoRef = useRef<HTMLVideoElement>(null);

  // Sync video time
  const handleTimeUpdate = () => {
    if (videoRef.current) {
      const t = videoRef.current.currentTime;
      setCurrentTime(t);
      if (bgVideoRef.current && Math.abs(bgVideoRef.current.currentTime - t) > 0.3) {
        bgVideoRef.current.currentTime = t;
      }
      // Loop within clip boundaries
      if (t >= endTime) {
        videoRef.current.currentTime = startTime;
        if (bgVideoRef.current) bgVideoRef.current.currentTime = startTime;
      }
    }
  };

  const togglePlay = () => {
    if (videoRef.current) {
      if (isPlaying) {
        videoRef.current.pause();
        if (bgVideoRef.current) bgVideoRef.current.pause();
        setIsPlaying(false);
      } else {
        if (videoRef.current.currentTime < startTime || videoRef.current.currentTime >= endTime) {
          videoRef.current.currentTime = startTime;
          if (bgVideoRef.current) bgVideoRef.current.currentTime = startTime;
        }
        videoRef.current.play();
        if (bgVideoRef.current) bgVideoRef.current.play();
        setIsPlaying(true);
      }
    }
  };

  const jumpToWord = (wordStart: number) => {
    if (videoRef.current) {
      videoRef.current.currentTime = wordStart;
      if (bgVideoRef.current) bgVideoRef.current.currentTime = wordStart;
      if (!isPlaying) {
        videoRef.current.play();
        if (bgVideoRef.current) bgVideoRef.current.play();
        setIsPlaying(true);
      }
    }
  };

  const handleWordChange = (idx: number, newText: string) => {
    const updated = [...words];
    updated[idx].word = newText;
    setWords(updated);
  };

  const handleSave = async () => {
    try {
      const updated = await api.updateClip(clip.id, {
        title,
        start_time: startTime,
        end_time: endTime,
        aspect_ratio: aspectRatio as any,
        crop_mode: cropMode as any,
        crop_x: cropX,
        crop_y: cropY,
        caption_style: captionStyle as any,
        custom_words: words
      });
      onClipUpdated(updated);
      setIsSaved(true);
      setTimeout(() => setIsSaved(false), 2000);
    } catch (err) {
      console.error(err);
    }
  };

  const handleStartRender = async () => {
    await handleSave();
    setIsRendering(true);
    setRenderProgress(10);
    try {
      await api.renderClip(clip.id, {
        aspect_ratio: aspectRatio,
        crop_mode: cropMode,
        caption_style: captionStyle,
        burn_captions: true
      });

      // Poll rendering status
      const interval = setInterval(async () => {
        try {
          const fresh = await api.getClip(clip.id);
          setRenderProgress(fresh.render_progress);
          if (fresh.render_status === 'completed') {
            clearInterval(interval);
            setIsRendering(false);
            onClipUpdated(fresh);
            onGoToExport();
          } else if (fresh.render_status === 'failed') {
            clearInterval(interval);
            setIsRendering(false);
          }
        } catch (e) {
          clearInterval(interval);
          setIsRendering(false);
        }
      }, 1500);
    } catch (err) {
      console.error(err);
      setIsRendering(false);
    }
  };

  // Find active word for live caption overlay
  const activeWordIdx = words.findIndex((w) => currentTime >= w.start && currentTime <= w.end);
  const startChunk = Math.max(0, activeWordIdx - 2);
  const activePhrase = words.slice(startChunk, startChunk + 4);

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Top action header */}
      <div className="flex items-center justify-between p-4 bg-dark-900 border border-zinc-800 rounded-2xl">
        <div className="flex items-center gap-3">
          <button
            onClick={onBack}
            className="text-xs font-semibold text-zinc-400 hover:text-white px-3 py-1.5 rounded-lg hover:bg-zinc-800 transition"
          >
            ← Back to Clips
          </button>
          <div className="h-4 w-[1px] bg-zinc-800" />
          <h2 className="text-sm font-bold text-white truncate max-w-md">{title}</h2>
          <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-brand-500/10 text-brand-400 border border-brand-500/20 font-mono">
            Score: {clip.virality_score}/99
          </span>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleSave}
            className="flex items-center gap-1.5 bg-zinc-800 hover:bg-zinc-700 text-white font-medium text-xs px-3.5 py-2 rounded-lg border border-zinc-700 transition"
          >
            {isSaved ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Save className="w-3.5 h-3.5" />}
            <span>{isSaved ? 'Saved!' : 'Save Changes'}</span>
          </button>

          <button
            onClick={handleStartRender}
            disabled={isRendering}
            className="flex items-center gap-2 bg-gradient-to-r from-brand-600 to-brand-500 hover:from-brand-500 hover:to-brand-400 text-black font-semibold text-xs px-4 py-2 rounded-lg shadow-md shadow-brand-500/20 transition disabled:opacity-50"
          >
            <DownloadCloud className="w-4 h-4" />
            <span>{isRendering ? `Rendering (${renderProgress}%)...` : 'Export Final MP4'}</span>
          </button>
        </div>
      </div>

      {/* Main Studio Area */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Video Player & Aspect Ratio Canvas */}
        <div className="lg:col-span-7 bg-dark-900 border border-zinc-800 rounded-2xl p-6 shadow-xl space-y-4">
          {/* Aspect Ratio Canvas Frame */}
          <div className="relative mx-auto bg-zinc-950 rounded-xl overflow-hidden border border-zinc-800 shadow-2xl flex items-center justify-center select-none"
               style={{
                 maxWidth: aspectRatio === '9:16' ? '340px' : aspectRatio === '1:1' ? '440px' : aspectRatio === '4:5' ? '380px' : '100%',
                 aspectRatio: aspectRatio === '9:16' ? '9/16' : aspectRatio === '1:1' ? '1/1' : aspectRatio === '4:5' ? '4/5' : '16/9'
               }}
          >
            {clip.rendered_url || clip.video_preview_url ? (
              <>
                {/* Real-time Ambient Blurred Background (fills screen seamlessly when in fit_blur mode) */}
                {cropMode === 'fit_blur' && !clip.rendered_url && (
                  <video
                    ref={bgVideoRef}
                    src={api.resolveUrl(clip.video_preview_url!)}
                    className="absolute inset-0 w-full h-full object-cover filter blur-2xl scale-125 opacity-70 pointer-events-none select-none"
                    muted
                  />
                )}
                {/* Foreground Primary Video */}
                <video
                  ref={videoRef}
                  src={api.resolveUrl(clip.rendered_url || clip.video_preview_url!)}
                  onTimeUpdate={handleTimeUpdate}
                  onClick={togglePlay}
                  className={`relative z-10 w-full h-full cursor-pointer transition-all duration-200 ${
                    cropMode === 'fit_blur' && !clip.rendered_url
                      ? 'object-contain drop-shadow-[0_8px_30px_rgba(0,0,0,0.95)]'
                      : 'object-cover'
                  }`}
                  style={
                    cropMode === 'auto_face' && !clip.rendered_url ? {
                      objectPosition: `${cropX * 100}% ${cropY * 100}%`
                    } : undefined
                  }
                />
              </>
            ) : (
              <div className="text-center p-6 text-zinc-500 text-xs">
                No video preview available
              </div>
            )}

            {/* Live Interactive Karaoke Caption Overlay - positioned in social safe zone (~22% from bottom) */}
            {activePhrase.length > 0 && !clip.rendered_url && (
              <div className="absolute bottom-[22%] left-4 right-4 pointer-events-none text-center select-none z-20">
                <div className={`inline-block px-3 py-1.5 rounded-lg ${
                  captionStyle === 'neon' ? 'bg-black/80 backdrop-blur' : 'drop-shadow-[0_4px_12px_rgba(0,0,0,0.95)]'
                }`}>
                  <p className="text-base sm:text-lg font-black tracking-tight leading-tight uppercase">
                    {activePhrase.map((w, i) => {
                      const isWordActive = currentTime >= w.start && currentTime <= w.end;
                      return (
                        <span
                          key={i}
                          className={`inline-block mx-1 transition-all duration-150 ${
                            isWordActive
                              ? captionStyle === 'hormozi'
                                ? 'text-[#00FF66] scale-110 drop-shadow-[0_0_12px_rgba(0,255,102,0.8)]'
                                : captionStyle === 'neon'
                                ? 'text-cyan-300 scale-110 drop-shadow-[0_0_12px_rgba(34,211,238,0.9)]'
                                : captionStyle === 'beast'
                                ? 'text-amber-400 scale-110 drop-shadow-[0_0_12px_rgba(251,191,36,0.9)]'
                                : 'text-white underline decoration-brand-400 font-extrabold'
                              : 'text-white/80'
                          }`}
                        >
                          {w.word}
                        </span>
                      );
                    })}
                  </p>
                </div>
              </div>
            )}

            {/* Play/Pause center overlay button */}
            {!isPlaying && (
              <div 
                onClick={togglePlay}
                className="absolute inset-0 z-30 bg-black/30 flex items-center justify-center cursor-pointer group"
              >
                <div className="w-14 h-14 rounded-full bg-brand-500 text-black flex items-center justify-center shadow-xl group-hover:scale-110 transition-transform">
                  <Play className="w-6 h-6 fill-current ml-1" />
                </div>
              </div>
            )}
          </div>

          {/* Timeline & Player Controls */}
          <div className="space-y-3 pt-2">
            <div className="flex items-center justify-between text-xs text-zinc-400 font-mono">
              <span>{currentTime.toFixed(1)}s</span>
              <span>Duration: {(endTime - startTime).toFixed(1)}s (Clip: {startTime.toFixed(1)}s - {endTime.toFixed(1)}s)</span>
            </div>

            {/* Timeline track */}
            <div className="relative h-8 bg-zinc-950 rounded-lg border border-zinc-800 p-1 flex items-center">
              {/* Active clip range */}
              <div 
                className="absolute top-1 bottom-1 bg-brand-500/20 border-l-2 border-r-2 border-brand-500 rounded"
                style={{
                  left: '0%',
                  right: '0%'
                }}
              />
              {/* Playhead */}
              <div 
                className="absolute top-0 bottom-0 w-1 bg-white shadow-md z-10"
                style={{
                  left: `${Math.min(100, Math.max(0, ((currentTime - startTime) / Math.max(1, endTime - startTime)) * 100))}%`
                }}
              />
            </div>

            {/* Playback action bar */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <button
                  onClick={togglePlay}
                  className="p-2 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-white transition"
                >
                  {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4 fill-current" />}
                </button>
                <button
                  onClick={() => {
                    if (videoRef.current) {
                      videoRef.current.currentTime = startTime;
                      if (bgVideoRef.current) bgVideoRef.current.currentTime = startTime;
                    }
                  }}
                  className="p-2 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-300 hover:text-white transition"
                  title="Replay from start"
                >
                  <RotateCcw className="w-4 h-4" />
                </button>
              </div>

              {/* Start/End Adjuster Inputs */}
              <div className="flex items-center gap-3 text-xs">
                <div className="flex items-center gap-1.5">
                  <span className="text-zinc-500 font-medium">Start:</span>
                  <input
                    type="number"
                    step="0.5"
                    value={startTime}
                    onChange={(e) => setStartTime(parseFloat(e.target.value) || 0)}
                    className="w-16 bg-zinc-950 border border-zinc-800 rounded px-2 py-1 text-center font-mono text-white text-xs"
                  />
                  <span className="text-zinc-500 font-mono">s</span>
                </div>

                <div className="flex items-center gap-1.5">
                  <span className="text-zinc-500 font-medium">End:</span>
                  <input
                    type="number"
                    step="0.5"
                    value={endTime}
                    onChange={(e) => setEndTime(parseFloat(e.target.value) || 0)}
                    className="w-16 bg-zinc-950 border border-zinc-800 rounded px-2 py-1 text-center font-mono text-white text-xs"
                  />
                  <span className="text-zinc-500 font-mono">s</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Tabbed Inspector */}
        <div className="lg:col-span-5 bg-dark-900 border border-zinc-800 rounded-2xl shadow-xl overflow-hidden">
          {/* Tabs bar */}
          <div className="flex border-b border-zinc-800 bg-zinc-950/60 p-1">
            {[
              { id: 'captions', label: 'Captions', icon: Type },
              { id: 'framing', label: 'Framing', icon: Crop },
              { id: 'styles', label: 'Styles', icon: Palette },
              { id: 'metadata', label: 'Virality', icon: Sparkles }
            ].map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as any)}
                  className={`flex-1 py-2.5 px-3 rounded-xl text-xs font-semibold flex items-center justify-center gap-2 transition ${
                    activeTab === tab.id
                      ? 'bg-zinc-800 text-white shadow-sm border border-zinc-700/60'
                      : 'text-zinc-400 hover:text-white hover:bg-zinc-900'
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </div>

          {/* Tab 1: Interactive Word-Level Caption Editor */}
          {activeTab === 'captions' && (
            <div className="p-5 space-y-4 max-h-[520px] overflow-y-auto">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-xs font-bold text-white">Karaoke Synchronized Words</h3>
                  <p className="text-[11px] text-zinc-400">Click any word to jump playhead; double click to edit text.</p>
                </div>
                <span className="text-[10px] font-mono text-brand-400 bg-brand-500/10 px-2 py-0.5 rounded border border-brand-500/20">
                  {words.length} words
                </span>
              </div>

              {/* Word Pills Cloud */}
              <div className="flex flex-wrap gap-1.5 p-3 bg-zinc-950 rounded-xl border border-zinc-800">
                {words.map((w, idx) => {
                  const isCurrent = currentTime >= w.start && currentTime <= w.end;
                  const isEditing = editingWordIdx === idx;

                  return (
                    <div
                      key={idx}
                      className={`relative group rounded px-1.5 py-0.5 text-xs transition ${
                        isCurrent
                          ? 'bg-brand-500 text-black font-bold shadow-sm'
                          : 'bg-zinc-800/80 text-zinc-200 hover:bg-zinc-700 cursor-pointer'
                      }`}
                    >
                      {isEditing ? (
                        <input
                          type="text"
                          autoFocus
                          value={w.word}
                          onChange={(e) => handleWordChange(idx, e.target.value)}
                          onBlur={() => setEditingWordIdx(null)}
                          onKeyDown={(e) => e.key === 'Enter' && setEditingWordIdx(null)}
                          className="bg-black text-white px-1 py-0.5 rounded outline-none border border-brand-500 text-xs w-20"
                        />
                      ) : (
                        <span 
                          onClick={() => jumpToWord(w.start)}
                          onDoubleClick={() => setEditingWordIdx(idx)}
                        >
                          {w.word}
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>
              <p className="text-[11px] text-zinc-500">
                💡 Double click any word to fix typos or adjust capitalization. Words sync automatically to the video timing!
              </p>
            </div>
          )}

          {/* Tab 2: Framing & Screen Layout */}
          {activeTab === 'framing' && (
            <div className="p-5 space-y-5">
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-bold text-zinc-300">Screen Framing & Precision Alignment</label>
                  <span className="text-[11px] text-brand-400 font-semibold flex items-center gap-1">
                    <Sparkles className="w-3 h-3" />
                    OpusClip Multi-Layout
                  </span>
                </div>

                <div className="grid grid-cols-1 gap-2.5">
                  {/* Option 1: Fit with Ambient Blur (Recommended) */}
                  <button
                    onClick={() => setCropMode('fit_blur')}
                    className={`p-3 rounded-xl border text-left transition flex items-start gap-3 ${
                      cropMode === 'fit_blur'
                        ? 'bg-brand-500/10 border-brand-500 shadow-sm'
                        : 'bg-zinc-800/40 border-zinc-800 hover:border-zinc-700'
                    }`}
                  >
                    <div className="w-4 h-4 rounded-full border-2 border-brand-500 mt-0.5 flex items-center justify-center shrink-0">
                      {cropMode === 'fit_blur' && <div className="w-2 h-2 rounded-full bg-brand-500" />}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold text-white">Fit with Ambient Blur</span>
                        <span className="px-1.5 py-0.5 rounded bg-brand-500/20 text-brand-400 text-[10px] font-bold">Recommended</span>
                      </div>
                      <p className="text-[11px] text-zinc-400 mt-1 leading-relaxed">
                        100% of video content visible centrally across the entire screen. Ambient motion blur fills top/bottom with zero awkward cropping.
                      </p>
                    </div>
                  </button>

                  {/* Option 2: Face Centered Lock */}
                  <button
                    onClick={() => setCropMode('auto_face')}
                    className={`p-3 rounded-xl border text-left transition flex items-start gap-3 ${
                      cropMode === 'auto_face'
                        ? 'bg-brand-500/10 border-brand-500 shadow-sm'
                        : 'bg-zinc-800/40 border-zinc-800 hover:border-zinc-700'
                    }`}
                  >
                    <div className="w-4 h-4 rounded-full border-2 border-brand-500 mt-0.5 flex items-center justify-center shrink-0">
                      {cropMode === 'auto_face' && <div className="w-2 h-2 rounded-full bg-brand-500" />}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold text-white">Face-Centered Smart Lock</span>
                      </div>
                      <p className="text-[11px] text-zinc-400 mt-1 leading-relaxed">
                        Full-bleed portrait crop locked onto active speaker with rule-of-thirds eye-line headroom.
                      </p>
                    </div>
                  </button>

                  {/* Option 3: Split Screen */}
                  <button
                    onClick={() => setCropMode('split_screen')}
                    className={`p-3 rounded-xl border text-left transition flex items-start gap-3 ${
                      cropMode === 'split_screen'
                        ? 'bg-brand-500/10 border-brand-500 shadow-sm'
                        : 'bg-zinc-800/40 border-zinc-800 hover:border-zinc-700'
                    }`}
                  >
                    <div className="w-4 h-4 rounded-full border-2 border-brand-500 mt-0.5 flex items-center justify-center shrink-0">
                      {cropMode === 'split_screen' && <div className="w-2 h-2 rounded-full bg-brand-500" />}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold text-white">Split Screen (Multi-Speaker)</span>
                      </div>
                      <p className="text-[11px] text-zinc-400 mt-1 leading-relaxed">
                        Stacked top/bottom composition for 2-speaker podcasts and interview conversations.
                      </p>
                    </div>
                  </button>
                </div>
              </div>

              {/* Target Platform Aspect Ratio */}
              <div className="space-y-2 pt-2 border-t border-zinc-800">
                <label className="text-xs font-bold text-zinc-300">Target Platform Canvas</label>
                <div className="grid grid-cols-4 gap-2">
                  {[
                    { id: '9:16', label: '9:16', desc: 'Shorts/TikTok' },
                    { id: '1:1', label: '1:1', desc: 'Square' },
                    { id: '4:5', label: '4:5', desc: 'Portrait Feed' },
                    { id: '16:9', label: '16:9', desc: 'Landscape' }
                  ].map((r) => (
                    <button
                      key={r.id}
                      onClick={() => setAspectRatio(r.id as any)}
                      className={`p-2 rounded-lg border text-center transition ${
                        aspectRatio === r.id
                          ? 'bg-brand-500/10 border-brand-500 text-brand-400 font-bold'
                          : 'bg-zinc-850 border-zinc-800 text-zinc-400 hover:text-white'
                      }`}
                    >
                      <div className="text-xs">{r.label}</div>
                      <div className="text-[9px] text-zinc-500">{r.desc}</div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Manual Crop X/Y Sliders (visible when in auto_face mode) */}
              {cropMode === 'auto_face' && (
                <div className="space-y-4 pt-2 border-t border-zinc-800">
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-medium text-zinc-300">Horizontal Center (X-axis)</span>
                      <span className="font-mono text-zinc-400">{(cropX * 100).toFixed(0)}%</span>
                    </div>
                    <input
                      type="range"
                      min="0.1"
                      max="0.9"
                      step="0.02"
                      value={cropX}
                      onChange={(e) => setCropX(parseFloat(e.target.value))}
                      className="w-full accent-brand-500 cursor-pointer"
                    />
                    <div className="flex justify-between text-[10px] text-zinc-500 font-mono">
                      <span>Left (10%)</span>
                      <span>Center (50%)</span>
                      <span>Right (90%)</span>
                    </div>
                  </div>

                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-medium text-zinc-300">Vertical Eye-line Headroom (Y-axis)</span>
                      <span className="font-mono text-zinc-400">{(cropY * 100).toFixed(0)}%</span>
                    </div>
                    <input
                      type="range"
                      min="0.15"
                      max="0.65"
                      step="0.02"
                      value={cropY}
                      onChange={(e) => setCropY(parseFloat(e.target.value))}
                      className="w-full accent-brand-500 cursor-pointer"
                    />
                    <div className="flex justify-between text-[10px] text-zinc-500 font-mono">
                      <span>High Headroom (15%)</span>
                      <span>Cinematic 35%</span>
                      <span>Mid (65%)</span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Tab 3: Style & Animation Customizer */}
          {activeTab === 'styles' && (
            <div className="p-5 space-y-5">
              <div className="space-y-3">
                <label className="text-xs font-bold text-zinc-300">Preset Animation Style</label>
                <div className="grid grid-cols-2 gap-2.5">
                  {[
                    { id: 'hormozi', name: 'Alex Hormozi', color: '#00FF66', desc: 'Neon Yellow/Green pop' },
                    { id: 'neon', name: 'Cyberpunk Neon', color: '#00FFFF', desc: 'Cyan glowing badge' },
                    { id: 'beast', name: 'Beast Retention', color: '#FFAA00', desc: 'Impact Gold caps' },
                    { id: 'minimal', name: 'Minimalist Clean', color: '#FFFFFF', desc: 'Clean modern Helvetica' }
                  ].map((preset) => (
                    <div
                      key={preset.id}
                      onClick={() => setCaptionStyle(preset.id as any)}
                      className={`p-3 rounded-xl border cursor-pointer transition ${
                        captionStyle === preset.id
                          ? 'bg-brand-500/10 border-brand-500 shadow-sm'
                          : 'bg-zinc-800/40 border-zinc-800 hover:border-zinc-700'
                      }`}
                    >
                      <div className="flex items-center gap-2 mb-1">
                        <div 
                          className="w-3 h-3 rounded-full shadow-sm"
                          style={{ backgroundColor: preset.color }}
                        />
                        <span className="text-xs font-bold text-white">{preset.name}</span>
                      </div>
                      <p className="text-[10px] text-zinc-400">{preset.desc}</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Caption Safe Zone Placement Information */}
              <div className="p-3 bg-zinc-950 rounded-xl border border-zinc-800 space-y-1">
                <div className="flex items-center gap-1.5 text-xs font-bold text-zinc-200">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Platform Safe Zone Active</span>
                </div>
                <p className="text-[11px] text-zinc-400 leading-relaxed">
                  Captions are dynamically rendered in the lower third (Y=1440 in 9:16), perfectly avoiding TikTok, Shorts, and Reels UI overlays.
                </p>
              </div>
            </div>
          )}

          {/* Tab 4: Social Hooks & Metadata */}
          {activeTab === 'metadata' && (
            <div className="p-5 space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs font-bold text-zinc-300">AI Clip Title</label>
                <input
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-brand-500"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-bold text-zinc-300">Viral Social Caption & Hashtags</label>
                <textarea
                  rows={4}
                  defaultValue={clip.social_caption || ''}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-brand-500 leading-relaxed"
                />
              </div>

              <div className="p-3 rounded-xl bg-zinc-800/40 border border-zinc-800 space-y-2">
                <div className="flex items-center justify-between text-xs font-bold text-zinc-200">
                  <span>Viral Hook Trigger</span>
                  <span className="text-brand-400 font-mono">Hook Score: {clip.score_breakdown?.hook || 96}%</span>
                </div>
                <p className="text-xs text-zinc-300 italic">
                  "{clip.hook_text || clip.description}"
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
