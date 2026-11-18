import React from 'react';
import { 
  Sparkles, 
  UploadCloud, 
  Film, 
  Scissors, 
  Clock, 
  CheckCircle2, 
  Play, 
  ArrowRight,
  TrendingUp,
  DownloadCloud,
  Layers
} from 'lucide-react';
import { api } from '../api';
import { SourceVideo, DashboardStats, Clip } from '../types';

interface DashboardViewProps {
  stats: DashboardStats | null;
  videos: SourceVideo[];
  onOpenUpload: () => void;
  onSelectVideo: (video: SourceVideo) => void;
  onRefresh: () => void;
}

export const DashboardView: React.FC<DashboardViewProps> = ({
  stats,
  videos,
  onOpenUpload,
  onSelectVideo,
  onRefresh
}) => {
  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      {/* Hero Welcome Banner */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-zinc-900 via-dark-900 to-zinc-900 border border-zinc-800 p-8 shadow-2xl">
        <div className="relative z-10 max-w-2xl space-y-3">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-brand-500/10 border border-brand-500/20 text-brand-400 text-xs font-semibold">
            <Sparkles className="w-3.5 h-3.5 text-brand-400" />
            <span>AI Virality Engine • OpusClip Alternative</span>
          </div>

          <h1 className="text-3xl font-black text-white tracking-tight leading-tight">
            Turn Any Long Video into <span className="bg-gradient-to-r from-brand-400 to-emerald-400 bg-clip-text text-transparent">Viral Shorts</span> in 1-Click
          </h1>

          <p className="text-xs text-zinc-400 leading-relaxed max-w-xl">
            Upload podcasts, interviews, webinars, or YouTube URLs. Our system transcribes audio with word-level accuracy, tracks active speakers with OpenCV, and scores viral moments on a 0-99 scale.
          </p>

          <div className="pt-2 flex items-center gap-3">
            <button
              onClick={onOpenUpload}
              className="flex items-center gap-2 bg-brand-500 hover:bg-brand-400 text-black font-bold text-xs px-5 py-2.5 rounded-xl shadow-lg shadow-brand-500/25 transition-all hover:scale-[1.02] active:scale-[0.98]"
            >
              <UploadCloud className="w-4 h-4" />
              <span>Repurpose a Video Now</span>
            </button>
          </div>
        </div>

        {/* Decorative background glow */}
        <div className="absolute right-0 top-0 bottom-0 w-1/3 bg-gradient-to-l from-brand-500/10 to-transparent pointer-events-none" />
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-5 bg-dark-900 border border-zinc-800 rounded-2xl space-y-1">
          <div className="flex items-center justify-between text-zinc-400 text-xs">
            <span>Viral Clips Created</span>
            <Scissors className="w-4 h-4 text-brand-400" />
          </div>
          <p className="text-2xl font-black text-white font-mono">{stats?.total_clips_generated || 0}</p>
          <span className="text-[10px] text-zinc-500">Across all projects</span>
        </div>

        <div className="p-5 bg-dark-900 border border-zinc-800 rounded-2xl space-y-1">
          <div className="flex items-center justify-between text-zinc-400 text-xs">
            <span>Exported MP4s</span>
            <DownloadCloud className="w-4 h-4 text-emerald-400" />
          </div>
          <p className="text-2xl font-black text-white font-mono">{stats?.exported_clips || 0}</p>
          <span className="text-[10px] text-zinc-500">Rendered with captions</span>
        </div>

        <div className="p-5 bg-dark-900 border border-zinc-800 rounded-2xl space-y-1">
          <div className="flex items-center justify-between text-zinc-400 text-xs">
            <span>Video Repurposed</span>
            <Clock className="w-4 h-4 text-amber-400" />
          </div>
          <p className="text-2xl font-black text-white font-mono">{stats?.minutes_processed || 0}m</p>
          <span className="text-[10px] text-zinc-500">Total duration analyzed</span>
        </div>

        <div className="p-5 bg-dark-900 border border-zinc-800 rounded-2xl space-y-1">
          <div className="flex items-center justify-between text-zinc-400 text-xs">
            <span>Credits Remaining</span>
            <Sparkles className="w-4 h-4 text-brand-400" />
          </div>
          <p className="text-2xl font-black text-brand-400 font-mono">{stats?.credits_remaining || 180}m</p>
          <span className="text-[10px] text-zinc-500">{stats?.plan || 'Pro'} Tier plan</span>
        </div>
      </div>

      {/* Recent Videos Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-bold text-white tracking-tight">Recent Source Videos</h2>
          <button
            onClick={onOpenUpload}
            className="text-xs text-brand-400 hover:text-brand-300 font-semibold"
          >
            + Upload New
          </button>
        </div>

        {videos.length === 0 ? (
          <div className="p-10 border border-dashed border-zinc-800 rounded-2xl text-center space-y-3 bg-zinc-950/40">
            <div className="w-12 h-12 rounded-full bg-zinc-800/80 text-zinc-500 mx-auto flex items-center justify-center">
              <Film className="w-6 h-6" />
            </div>
            <h3 className="text-sm font-bold text-white">No Videos Uploaded Yet</h3>
            <p className="text-xs text-zinc-400 max-w-sm mx-auto">
              Upload a long-form video or paste a YouTube URL to let our AI pipeline generate viral short clips.
            </p>
            <button
              onClick={onOpenUpload}
              className="bg-zinc-800 hover:bg-zinc-700 text-white font-semibold text-xs px-4 py-2 rounded-lg border border-zinc-700 transition"
            >
              Upload Video
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {videos.map((vid) => (
              <div
                key={vid.id}
                onClick={() => onSelectVideo(vid)}
                className="bg-dark-900 border border-zinc-800 hover:border-zinc-700 rounded-2xl overflow-hidden shadow-lg cursor-pointer transition-all flex flex-col justify-between group"
              >
                {/* Thumbnail banner */}
                <div className="relative aspect-video bg-zinc-950 overflow-hidden flex items-center justify-center">
                  {vid.thumbnail_path ? (
                    <img
                      src={api.resolveUrl(vid.thumbnail_path)}
                      alt={vid.title}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                    />
                  ) : (
                    <Film className="w-8 h-8 text-zinc-600" />
                  )}

                  <div className="absolute bottom-2 right-2 px-2 py-0.5 rounded bg-black/80 text-white text-[10px] font-mono backdrop-blur">
                    {Math.floor(vid.duration / 60)}:{Math.floor(vid.duration % 60).toString().padStart(2, '0')}
                  </div>

                  {vid.status !== 'completed' && (
                    <div className="absolute inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4 text-center">
                      <div className="space-y-1">
                        <span className="text-xs font-bold text-brand-400 animate-pulse">
                          {vid.status_message || 'Processing...'}
                        </span>
                        <div className="w-24 h-1.5 bg-zinc-700 rounded-full overflow-hidden mx-auto">
                          <div className="h-full bg-brand-500 rounded-full" style={{ width: `${vid.progress}%` }} />
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                {/* Details */}
                <div className="p-4 space-y-3">
                  <div>
                    <h3 className="text-xs font-bold text-white line-clamp-1 group-hover:text-brand-300 transition">
                      {vid.title}
                    </h3>
                    <p className="text-[11px] text-zinc-500 mt-0.5">
                      {new Date(vid.created_at).toLocaleDateString()} • {vid.width}x{vid.height}
                    </p>
                  </div>

                  <div className="pt-2 border-t border-zinc-800 flex items-center justify-between text-xs">
                    <span className="font-semibold text-brand-400 flex items-center gap-1">
                      <Scissors className="w-3.5 h-3.5" />
                      {vid.clip_count} Viral Clips
                    </span>
                    <span className="text-zinc-400 group-hover:text-white flex items-center gap-1 font-medium">
                      <span>Explore</span>
                      <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
