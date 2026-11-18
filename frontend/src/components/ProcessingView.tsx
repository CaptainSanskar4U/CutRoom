import React, { useEffect, useState } from 'react';
import { 
  Sparkles, 
  AudioWaveform, 
  FileText, 
  TrendingUp, 
  Eye, 
  CheckCircle, 
  AlertCircle,
  ArrowRight,
  Clock
} from 'lucide-react';
import { api } from '../api';
import { SourceVideo } from '../types';

interface ProcessingViewProps {
  videoId: string;
  onCompleted: (video: SourceVideo) => void;
  onCancel: () => void;
}

export const ProcessingView: React.FC<ProcessingViewProps> = ({
  videoId,
  onCompleted,
  onCancel
}) => {
  const [video, setVideo] = useState<SourceVideo | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let intervalId: any;

    const pollStatus = async () => {
      try {
        const data = await api.getVideo(videoId);
        setVideo(data);

        if (data.status === 'completed') {
          clearInterval(intervalId);
          setTimeout(() => {
            onCompleted(data);
          }, 1000);
        } else if (data.status === 'failed') {
          clearInterval(intervalId);
          setError(data.status_message || 'Video processing encountered an issue.');
        }
      } catch (err: any) {
        console.error('Polling error:', err);
      }
    };

    pollStatus();
    intervalId = setInterval(pollStatus, 2000);

    return () => clearInterval(intervalId);
  }, [videoId, onCompleted]);

  const steps = [
    {
      id: 'extracting_audio',
      label: 'Audio Extraction & Normalization',
      desc: '16kHz mono audio extraction via FFmpeg 9.0',
      icon: AudioWaveform,
      activeIf: ['extracting_audio', 'transcribing', 'analyzing_virality', 'tracking_faces', 'completed']
    },
    {
      id: 'transcribing',
      label: 'AI Speech Transcription',
      desc: 'faster-whisper model extracting millisecond word timestamps',
      icon: FileText,
      activeIf: ['transcribing', 'analyzing_virality', 'tracking_faces', 'completed']
    },
    {
      id: 'analyzing_virality',
      label: 'Virality Scoring & Hook Isolation',
      desc: '0-99 OpusClip algorithm evaluating Hook, Flow, Value & Ending',
      icon: TrendingUp,
      activeIf: ['analyzing_virality', 'tracking_faces', 'completed']
    },
    {
      id: 'tracking_faces',
      label: 'Computer Vision Face Reframing',
      desc: 'OpenCV Haar/DNN tracking active speaker with smooth 9:16 crop',
      icon: Eye,
      activeIf: ['tracking_faces', 'completed']
    }
  ];

  return (
    <div className="max-w-3xl mx-auto py-10 px-4 space-y-8 animate-in fade-in duration-300">
      {/* Title block */}
      <div className="text-center space-y-2">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-brand-500/10 border border-brand-500/20 text-brand-400 text-xs font-semibold">
          <Sparkles className="w-3.5 h-3.5 animate-spin" />
          <span>Autonomous AI Pipeline in Progress</span>
        </div>
        <h1 className="text-2xl font-black text-white tracking-tight">
          Generating Viral Clips for "{video?.title || 'Your Video'}"
        </h1>
        <p className="text-xs text-zinc-400 max-w-lg mx-auto">
          Please wait while our models deconstruct the video, isolate high-retention moments, track speakers, and prepare word-level animated captions.
        </p>
      </div>

      {/* Progress Card */}
      <div className="bg-dark-900 border border-zinc-800 rounded-2xl p-6 shadow-xl space-y-6">
        {/* Progress Bar */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-xs">
            <span className="font-semibold text-zinc-200">
              {video?.status_message || 'Initializing pipeline...'}
            </span>
            <span className="font-mono font-bold text-brand-400">
              {video?.progress || 10}%
            </span>
          </div>

          <div className="w-full h-3 bg-zinc-800 rounded-full overflow-hidden p-0.5">
            <div 
              className="h-full bg-gradient-to-r from-brand-600 via-brand-500 to-emerald-400 rounded-full transition-all duration-500 ease-out shadow-sm shadow-brand-500/50"
              style={{ width: `${Math.max(8, video?.progress || 10)}%` }}
            />
          </div>
        </div>

        {/* Multi-step Visualizer */}
        <div className="space-y-3 pt-2">
          {steps.map((st, idx) => {
            const Icon = st.icon;
            const isCompleted = video?.progress ? video.progress > (idx + 1) * 22 : false;
            const isCurrent = video?.status === st.id;

            return (
              <div 
                key={st.id}
                className={`flex items-start gap-4 p-3.5 rounded-xl border transition-all ${
                  isCurrent 
                    ? 'bg-brand-500/5 border-brand-500/30' 
                    : isCompleted 
                    ? 'bg-zinc-800/30 border-zinc-800' 
                    : 'bg-zinc-900/30 border-zinc-800/40 opacity-50'
                }`}
              >
                <div className={`p-2 rounded-lg ${
                  isCurrent 
                    ? 'bg-brand-500/20 text-brand-400' 
                    : isCompleted 
                    ? 'bg-emerald-500/20 text-emerald-400' 
                    : 'bg-zinc-800 text-zinc-500'
                }`}>
                  {isCompleted ? <CheckCircle className="w-4 h-4" /> : <Icon className="w-4 h-4" />}
                </div>

                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <p className={`text-xs font-bold ${isCurrent ? 'text-brand-300' : 'text-zinc-200'}`}>
                      {st.label}
                    </p>
                    {isCurrent && (
                      <span className="text-[10px] font-semibold text-brand-400 animate-pulse">
                        Processing...
                      </span>
                    )}
                  </div>
                  <p className="text-[11px] text-zinc-400 mt-0.5">{st.desc}</p>
                </div>
              </div>
            );
          })}
        </div>

        {error && (
          <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs flex items-center gap-3">
            <AlertCircle className="w-5 h-5 shrink-0" />
            <div>
              <p className="font-bold">Pipeline Error</p>
              <p className="text-[11px] text-rose-300/80">{error}</p>
            </div>
          </div>
        )}

        {/* Footer controls */}
        <div className="flex items-center justify-between pt-4 border-t border-zinc-800 text-xs">
          <div className="flex items-center gap-2 text-zinc-400">
            <Clock className="w-3.5 h-3.5 text-zinc-400" />
            <span>Average processing time: ~30-60 seconds</span>
          </div>

          <button
            onClick={onCancel}
            className="text-zinc-400 hover:text-white px-3 py-1.5 rounded-lg hover:bg-zinc-800 transition"
          >
            Cancel & Back to Dashboard
          </button>
        </div>
      </div>
    </div>
  );
};
