import React, { useState } from 'react';
import { 
  Sparkles, 
  Flame, 
  Play, 
  Sliders, 
  DownloadCloud, 
  Copy, 
  Check, 
  Layers,
  Repeat,
  Zap,
  TrendingUp,
  ShieldCheck
} from 'lucide-react';
import { api } from '../api';
import { Clip, SourceVideo } from '../types';

interface ClipsExplorerProps {
  video: SourceVideo;
  clips: Clip[];
  onSelectClip: (clip: Clip) => void;
  onRefreshClips: () => void;
}

export const ClipsExplorer: React.FC<ClipsExplorerProps> = ({
  video,
  clips,
  onSelectClip,
  onRefreshClips
}) => {
  const [playingClipId, setPlayingClipId] = useState<string | null>(null);
  const [copiedClipId, setCopiedClipId] = useState<string | null>(null);
  const [renderingClipIds, setRenderingClipIds] = useState<Set<string>>(new Set());

  const handleCopyCaption = (clip: Clip) => {
    if (clip.social_caption) {
      navigator.clipboard.writeText(clip.social_caption);
      setCopiedClipId(clip.id);
      setTimeout(() => setCopiedClipId(null), 2000);
    }
  };

  const handleQuickRender = async (clip: Clip) => {
    setRenderingClipIds((prev) => new Set(prev).add(clip.id));
    try {
      await api.renderClip(clip.id, {
        aspect_ratio: clip.aspect_ratio,
        caption_style: clip.caption_style,
        crop_mode: clip.crop_mode || 'fit_blur',
        burn_captions: true
      });
      onRefreshClips();
    } catch (err) {
      console.error(err);
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 90) return 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10';
    if (score >= 80) return 'text-amber-400 border-amber-500/30 bg-amber-500/10';
    return 'text-blue-400 border-blue-500/30 bg-blue-500/10';
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Header bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-6 bg-dark-900 border border-zinc-800 rounded-2xl">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold uppercase tracking-wider text-brand-400 flex items-center gap-1">
              <Zap className="w-3.5 h-3.5" />
              YouTube Algorithm Viral Intelligence
            </span>
            <span className="text-zinc-600">•</span>
            <span className="text-xs text-zinc-400">{clips.length} Viral Shorts Extracted</span>
          </div>
          <h1 className="text-xl font-black text-white tracking-tight">{video.title}</h1>
          <p className="text-xs text-zinc-400">
            Engineered for YouTube Shorts algorithm: Swipe-Away Prevention + Infinite Loop Stitching for &gt;100% Retention.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-zinc-800/60 border border-zinc-700/60 text-xs">
            <Flame className="w-4 h-4 text-amber-400" />
            <span className="text-zinc-300">Top Viral Score:</span>
            <strong className="text-brand-400 font-mono text-sm">{clips[0]?.virality_score || 95}/99</strong>
          </div>
        </div>
      </div>

      {/* Clips Grid / List */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {clips.map((clip, index) => {
          const isPlaying = playingClipId === clip.id;
          const isCopied = copiedClipId === clip.id;
          const isRendering = renderingClipIds.has(clip.id) || clip.render_status === 'rendering';
          const isCompleted = clip.render_status === 'completed' && clip.rendered_url;
          const scoreClass = getScoreColor(clip.virality_score);
          const breakdown = clip.score_breakdown;

          return (
            <div
              key={clip.id}
              className="bg-dark-900 border border-zinc-800 hover:border-zinc-700 rounded-2xl p-5 shadow-lg transition-all flex flex-col justify-between group space-y-4"
            >
              {/* Top Meta Header */}
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-2.5">
                  <div className={`px-2.5 py-1 rounded-xl border text-sm font-black font-mono flex items-center gap-1.5 shadow-sm ${scoreClass}`}>
                    <Flame className="w-3.5 h-3.5" />
                    <span>{clip.virality_score}</span>
                    <span className="text-[10px] font-normal text-zinc-400">/99</span>
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider">
                        Short #{index + 1} • {clip.duration}s
                      </span>
                      {clip.virality_score >= 88 && (
                        <span className="flex items-center gap-1 text-[9px] font-bold px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                          <Repeat className="w-2.5 h-2.5" /> Infinite Loop Glitch
                        </span>
                      )}
                    </div>
                    <h3 className="text-sm font-bold text-white line-clamp-1 group-hover:text-brand-300 transition">
                      {clip.title}
                    </h3>
                  </div>
                </div>

                <div className="flex items-center gap-1">
                  <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-zinc-800 text-zinc-300 border border-zinc-700 font-mono">
                    {clip.aspect_ratio}
                  </span>
                  <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-brand-500/10 text-brand-400 border border-brand-500/20 capitalize">
                    {clip.caption_style}
                  </span>
                </div>
              </div>

              {/* Video Preview Box & Algorithmic Analysis */}
              <div className="grid grid-cols-1 sm:grid-cols-12 gap-4 items-center">
                {/* 9:16 Video Preview Box */}
                <div className="sm:col-span-5 relative aspect-[9/16] rounded-xl overflow-hidden bg-zinc-950 border border-zinc-800 shadow-inner group/preview flex items-center justify-center">
                  {isPlaying && (clip.rendered_url || clip.video_preview_url) ? (
                    <>
                      {/* Ambient blur background layer if playing unrendered preview */}
                      {!clip.rendered_url && (
                        <video
                          src={api.resolveUrl(clip.video_preview_url!)}
                          className="absolute inset-0 w-full h-full object-cover filter blur-xl scale-125 opacity-60 pointer-events-none"
                          muted
                        />
                      )}
                      <video
                        src={api.resolveUrl(clip.rendered_url || clip.video_preview_url)}
                        controls
                        autoPlay
                        className={`relative z-10 w-full h-full ${
                          clip.rendered_url ? 'object-cover' : 'object-contain'
                        }`}
                        onEnded={() => setPlayingClipId(null)}
                      />
                    </>
                  ) : (
                    <div 
                      className="w-full h-full relative cursor-pointer flex items-center justify-center overflow-hidden"
                      onClick={() => setPlayingClipId(clip.id)}
                    >
                      {clip.thumbnail_url ? (
                        <>
                          <img 
                            src={api.resolveUrl(clip.thumbnail_url)} 
                            alt=""
                            className="absolute inset-0 w-full h-full object-cover filter blur-xl scale-125 opacity-60 pointer-events-none"
                          />
                          <img 
                            src={api.resolveUrl(clip.thumbnail_url)} 
                            alt={clip.title}
                            className="relative z-10 w-full h-full object-contain group-hover/preview:scale-105 transition-transform duration-300 drop-shadow-md"
                          />
                        </>
                      ) : (
                        <div className="w-full h-full flex items-center justify-center bg-zinc-900 text-zinc-600">
                          <Layers className="w-8 h-8" />
                        </div>
                      )}
                      <div className="absolute inset-0 z-20 bg-black/30 flex items-center justify-center">
                        <div className="w-10 h-10 rounded-full bg-white/90 text-black flex items-center justify-center shadow-lg group-hover/preview:scale-110 transition-transform">
                          <Play className="w-4 h-4 fill-current ml-0.5" />
                        </div>
                      </div>
                      <div className="absolute bottom-2 left-2 right-2 z-20 px-2 py-1 bg-black/75 backdrop-blur rounded text-[10px] text-zinc-300 text-center font-mono">
                        {clip.start_time}s - {clip.end_time}s ({clip.duration}s)
                      </div>
                    </div>
                  )}
                </div>

                {/* Algorithmic Intelligence Breakdown */}
                <div className="sm:col-span-7 space-y-3">
                  {/* YouTube Algorithm Exploit Card */}
                  <div className="p-3 rounded-xl bg-zinc-800/40 border border-zinc-800 space-y-1.5">
                    <div className="flex items-center gap-1.5 text-[11px] font-bold text-zinc-200">
                      <Zap className="w-3.5 h-3.5 text-amber-400" />
                      <span>YouTube Algorithm Optimization</span>
                    </div>
                    <p className="text-[11px] text-zinc-400 leading-relaxed italic">
                      "{clip.virality_reason || 'High retention short clip with unclosed loop hook.'}"
                    </p>
                  </div>

                  {/* Viral metrics breakdown */}
                  {breakdown && (
                    <div className="grid grid-cols-3 gap-2 text-center">
                      <div className="p-2 rounded-lg bg-zinc-900 border border-zinc-800">
                        <span className="text-[9px] text-zinc-400 uppercase font-semibold">Swipe Shield</span>
                        <p className="text-xs font-bold text-brand-400 font-mono">{breakdown.hook}%</p>
                      </div>
                      <div className="p-2 rounded-lg bg-zinc-900 border border-zinc-800">
                        <span className="text-[9px] text-zinc-400 uppercase font-semibold">Loop Glitch</span>
                        <p className="text-xs font-bold text-emerald-400 font-mono">{breakdown.ending || 95}%</p>
                      </div>
                      <div className="p-2 rounded-lg bg-zinc-900 border border-zinc-800">
                        <span className="text-[9px] text-zinc-400 uppercase font-semibold">Dopamine WPM</span>
                        <p className="text-xs font-bold text-amber-400 font-mono">{breakdown.value}%</p>
                      </div>
                    </div>
                  )}

                  {/* Opening Hook Line */}
                  <div className="space-y-1">
                    <span className="text-[10px] uppercase font-bold text-zinc-400 tracking-wider">
                      Opening Hook Line (0-2s):
                    </span>
                    <p className="text-xs text-zinc-200 line-clamp-2 bg-zinc-950/60 p-2 rounded-lg border border-zinc-800/60 font-medium">
                      "{clip.hook_text || clip.description}"
                    </p>
                  </div>
                </div>
              </div>

              {/* Bottom Actions Bar */}
              <div className="pt-3 border-t border-zinc-800 flex items-center justify-between gap-2">
                <button
                  onClick={() => handleCopyCaption(clip)}
                  className="flex items-center gap-1.5 text-xs text-zinc-400 hover:text-white px-2.5 py-1.5 rounded-lg hover:bg-zinc-800 transition"
                  title="Copy YouTube Shorts title, hook & hashtags"
                >
                  {isCopied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{isCopied ? 'Copied' : 'Copy Social Hook'}</span>
                </button>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => onSelectClip(clip)}
                    className="flex items-center gap-1.5 bg-zinc-800 hover:bg-zinc-700 text-white font-medium text-xs px-3 py-1.5 rounded-lg border border-zinc-700 transition"
                  >
                    <Sliders className="w-3.5 h-3.5" />
                    <span>Fine-Tune & Edit</span>
                  </button>

                  {isCompleted ? (
                    <a
                      href={api.resolveUrl(clip.rendered_url)}
                      download={`ViralShort_${clip.title.replace(/[^a-zA-Z0-9]/g, '_')}.mp4`}
                      target="_blank"
                      rel="noreferrer"
                      className="flex items-center gap-1.5 bg-brand-500 hover:bg-brand-400 text-black font-bold text-xs px-3.5 py-1.5 rounded-lg shadow-sm transition"
                    >
                      <DownloadCloud className="w-3.5 h-3.5" />
                      <span>Download MP4</span>
                    </a>
                  ) : (
                    <button
                      onClick={() => handleQuickRender(clip)}
                      disabled={isRendering}
                      className="flex items-center gap-1.5 bg-brand-500 hover:bg-brand-400 text-black font-semibold text-xs px-3.5 py-1.5 rounded-lg shadow-sm transition disabled:opacity-50"
                    >
                      <DownloadCloud className="w-3.5 h-3.5" />
                      <span>{isRendering ? 'Rendering...' : 'Export MP4'}</span>
                    </button>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
