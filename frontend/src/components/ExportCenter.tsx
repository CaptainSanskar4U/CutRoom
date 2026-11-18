import React, { useState } from 'react';
import { 
  DownloadCloud, 
  Play, 
  CheckCircle2, 
  AlertCircle, 
  Clock, 
  Film, 
  Share2, 
  ExternalLink,
  Sparkles
} from 'lucide-react';
import { api } from '../api';
import { Clip } from '../types';

interface ExportCenterProps {
  clips: Clip[];
  onRefresh: () => void;
  onOpenEditor: (clip: Clip) => void;
}

export const ExportCenter: React.FC<ExportCenterProps> = ({
  clips,
  onRefresh,
  onOpenEditor
}) => {
  const [activePreviewClip, setActivePreviewClip] = useState<Clip | null>(null);

  const exportedClips = clips.filter((c) => c.render_status === 'completed' || c.render_status === 'rendering');

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Header */}
      <div className="flex items-center justify-between p-6 bg-dark-900 border border-zinc-800 rounded-2xl">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold uppercase tracking-wider text-brand-400">
              Video Rendering Pipeline
            </span>
            <span className="text-zinc-600">•</span>
            <span className="text-xs text-zinc-400">{exportedClips.length} Exports queued or completed</span>
          </div>
          <h1 className="text-xl font-black text-white tracking-tight">Export Center</h1>
          <p className="text-xs text-zinc-400">
            Production MP4 files encoded with FFmpeg H.264, burned-in karaoke captions, and dynamic reframing.
          </p>
        </div>

        <button
          onClick={onRefresh}
          className="text-xs font-semibold text-zinc-300 hover:text-white bg-zinc-800 hover:bg-zinc-700 px-3.5 py-2 rounded-lg border border-zinc-700 transition"
        >
          Refresh Exports
        </button>
      </div>

      {/* Main Grid */}
      {exportedClips.length === 0 ? (
        <div className="p-12 text-center bg-dark-900 border border-zinc-800 rounded-2xl space-y-3">
          <div className="w-12 h-12 rounded-full bg-zinc-800 text-zinc-500 mx-auto flex items-center justify-center">
            <DownloadCloud className="w-6 h-6" />
          </div>
          <h3 className="text-sm font-bold text-white">No Rendered Exports Yet</h3>
          <p className="text-xs text-zinc-400 max-w-sm mx-auto">
            Go to the AI Clips Explorer or Clip Studio to export your clips with burned-in captions and optimal formatting.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {exportedClips.map((clip) => {
            const isCompleted = clip.render_status === 'completed';
            const isRendering = clip.render_status === 'rendering';

            return (
              <div
                key={clip.id}
                className="bg-dark-900 border border-zinc-800 rounded-2xl overflow-hidden shadow-xl flex flex-col justify-between"
              >
                {/* Thumbnail Preview Area */}
                <div className="relative aspect-[9/16] max-h-[380px] bg-zinc-950 overflow-hidden flex items-center justify-center group">
                  {clip.rendered_url && isCompleted ? (
                    <video
                      src={api.resolveUrl(clip.rendered_url)}
                      controls
                      className="w-full h-full object-cover"
                    />
                  ) : clip.thumbnail_url ? (
                    <img
                      src={api.resolveUrl(clip.thumbnail_url)}
                      alt={clip.title}
                      className="w-full h-full object-cover opacity-60"
                    />
                  ) : (
                    <Film className="w-8 h-8 text-zinc-600" />
                  )}

                  {isRendering && (
                    <div className="absolute inset-0 bg-black/70 backdrop-blur-sm flex flex-col items-center justify-center p-6 text-center space-y-3">
                      <div className="w-10 h-10 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
                      <div className="space-y-1">
                        <p className="text-xs font-bold text-white">Rendering MP4</p>
                        <p className="text-[10px] text-brand-400 font-mono">{clip.render_progress}%</p>
                        <p className="text-[10px] text-zinc-400">{clip.render_message || 'Compositing video...'}</p>
                      </div>
                    </div>
                  )}

                  {/* Top badges */}
                  <div className="absolute top-3 left-3 right-3 flex items-center justify-between">
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-black/80 text-white backdrop-blur border border-zinc-700 font-mono">
                      {clip.aspect_ratio}
                    </span>
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-brand-500 text-black shadow-sm font-mono">
                      Score: {clip.virality_score}
                    </span>
                  </div>
                </div>

                {/* Details & CTA */}
                <div className="p-4 space-y-3">
                  <div>
                    <h3 className="text-xs font-bold text-white line-clamp-1">{clip.title}</h3>
                    <p className="text-[11px] text-zinc-400">Duration: {clip.duration}s • Style: {clip.caption_style}</p>
                  </div>

                  <div className="pt-2 border-t border-zinc-800 flex items-center justify-between gap-2">
                    <button
                      onClick={() => onOpenEditor(clip)}
                      className="text-xs font-medium text-zinc-400 hover:text-white px-2.5 py-1.5 rounded-lg hover:bg-zinc-800 transition"
                    >
                      Edit
                    </button>

                    {isCompleted && clip.rendered_url && (
                      <a
                        href={api.resolveUrl(clip.rendered_url)}
                        download={`AutoClip_${clip.title.replace(/[^a-zA-Z0-9]/g, '_')}.mp4`}
                        target="_blank"
                        rel="noreferrer"
                        className="flex items-center gap-1.5 bg-brand-500 hover:bg-brand-400 text-black font-bold text-xs px-3.5 py-1.5 rounded-lg shadow-sm transition"
                      >
                        <DownloadCloud className="w-3.5 h-3.5" />
                        <span>Download MP4</span>
                      </a>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
