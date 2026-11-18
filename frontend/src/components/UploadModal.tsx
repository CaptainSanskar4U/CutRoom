import React, { useState, useRef } from 'react';
import { X, Upload, Link2, Sparkles, Film, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';
import { api } from '../api';
import { Project, SourceVideo } from '../types';

interface UploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  projects: Project[];
  onUploadSuccess: (video: SourceVideo) => void;
}

export const UploadModal: React.FC<UploadModalProps> = ({
  isOpen,
  onClose,
  projects,
  onUploadSuccess
}) => {
  const [activeTab, setActiveTab] = useState<'url' | 'file'>('url');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [importUrl, setImportUrl] = useState('');
  const [title, setTitle] = useState('');
  const [aspectRatio, setAspectRatio] = useState('9:16');
  const [captionStyle, setCaptionStyle] = useState('hormozi');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const handleFileDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      setSelectedFile(file);
      if (!title) setTitle(file.name.replace(/\.[^/.]+$/, ''));
      setErrorMsg(null);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setSelectedFile(file);
      if (!title) setTitle(file.name.replace(/\.[^/.]+$/, ''));
      setErrorMsg(null);
    }
  };

  const handleSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setErrorMsg(null);

    if (activeTab === 'url') {
      const cleanUrl = importUrl.trim();
      if (!cleanUrl) {
        setErrorMsg('Please paste a video link (YouTube, TikTok, Twitter/X, or direct MP4).');
        return;
      }

      setIsSubmitting(true);
      try {
        const video = await api.importUrl(
          cleanUrl,
          projects[0]?.id,
          title.trim() || undefined,
          aspectRatio,
          captionStyle
        );
        setIsSubmitting(false);
        onUploadSuccess(video);
        onClose();
      } catch (err: any) {
        console.error(err);
        setIsSubmitting(false);
        setErrorMsg(err.response?.data?.detail || err.message || 'Failed to import video link. Please verify the URL.');
      }
    } else {
      if (!selectedFile) {
        setErrorMsg('Please choose or drag & drop a video file to upload.');
        return;
      }

      setIsSubmitting(true);
      try {
        const video = await api.uploadVideo(
          selectedFile,
          projects[0]?.id,
          title.trim() || undefined,
          true
        );
        setIsSubmitting(false);
        onUploadSuccess(video);
        onClose();
      } catch (err: any) {
        console.error(err);
        setIsSubmitting(false);
        setErrorMsg(err.response?.data?.detail || err.message || 'File upload failed. Please try again.');
      }
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="w-full max-w-xl bg-dark-900 border border-zinc-800 rounded-2xl shadow-2xl overflow-hidden flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-zinc-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-brand-500/10 text-brand-400">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-white">Repurpose Video into Viral Shorts</h2>
              <p className="text-[11px] text-zinc-400">Paste any link • Auto-extract best hooks & viral clips to post directly</p>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="p-1.5 rounded-lg text-zinc-400 hover:text-white hover:bg-zinc-800 transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Tab switcher */}
        <div className="px-6 pt-4 flex gap-2">
          <button
            type="button"
            onClick={() => { setActiveTab('url'); setErrorMsg(null); }}
            className={`flex-1 flex items-center justify-center gap-2 py-2.5 text-xs font-semibold rounded-lg border transition ${
              activeTab === 'url'
                ? 'bg-zinc-800 text-white border-zinc-700 shadow-sm'
                : 'bg-transparent text-zinc-400 border-transparent hover:text-zinc-200'
            }`}
          >
            <Link2 className="w-4 h-4" />
            <span>Paste Video Link (YouTube / URL)</span>
          </button>
          <button
            type="button"
            onClick={() => { setActiveTab('file'); setErrorMsg(null); }}
            className={`flex-1 flex items-center justify-center gap-2 py-2.5 text-xs font-semibold rounded-lg border transition ${
              activeTab === 'file'
                ? 'bg-zinc-800 text-white border-zinc-700 shadow-sm'
                : 'bg-transparent text-zinc-400 border-transparent hover:text-zinc-200'
            }`}
          >
            <Upload className="w-4 h-4" />
            <span>Upload File (MP4, MOV)</span>
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 space-y-4">
          {errorMsg && (
            <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          {activeTab === 'url' ? (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-xs font-bold text-zinc-200">Video URL Link</label>
                <button
                  type="button"
                  onClick={() => setImportUrl('https://www.youtube.com/watch?v=aqz-KE-bpKQ')}
                  className="text-[10px] text-brand-400 hover:underline"
                >
                  Use sample test link
                </button>
              </div>

              <div className="relative">
                <Link2 className="absolute left-3 top-3 w-4 h-4 text-zinc-400" />
                <input
                  type="text"
                  placeholder="Paste YouTube, Vimeo, Twitter/X, or direct MP4 URL..."
                  value={importUrl}
                  onChange={(e) => {
                    setImportUrl(e.target.value);
                    if (errorMsg) setErrorMsg(null);
                  }}
                  onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
                  className="w-full bg-zinc-800/80 border border-zinc-700 rounded-lg pl-9 pr-3 py-2.5 text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-brand-500"
                  autoFocus
                />
              </div>
              <p className="text-[10px] text-zinc-400">
                Our engine automatically downloads, analyzes, reframes to 9:16, and burns in animated subtitles.
              </p>
            </div>
          ) : (
            <div
              onDragOver={(e) => e.preventDefault()}
              onDrop={handleFileDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition ${
                selectedFile
                  ? 'border-brand-500/50 bg-brand-500/5'
                  : 'border-zinc-700 hover:border-zinc-500 bg-zinc-800/20 hover:bg-zinc-800/40'
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept="video/*"
                onChange={handleFileSelect}
                className="hidden"
              />
              <div className="mx-auto w-12 h-12 rounded-full bg-zinc-800 flex items-center justify-center mb-3 text-zinc-400">
                {selectedFile ? <Film className="w-6 h-6 text-brand-400" /> : <Upload className="w-6 h-6" />}
              </div>
              {selectedFile ? (
                <div>
                  <p className="text-xs font-bold text-white mb-0.5">{selectedFile.name}</p>
                  <p className="text-[11px] text-zinc-400">{(selectedFile.size / (1024 * 1024)).toFixed(1)} MB • Click to change file</p>
                </div>
              ) : (
                <div>
                  <p className="text-xs font-bold text-white mb-0.5">Drag & drop your video here, or browse</p>
                  <p className="text-[11px] text-zinc-400">Supports MP4, MOV, WEBM, MKV (podcasts, interviews, talks)</p>
                </div>
              )}
            </div>
          )}

          {/* Optional Title */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-zinc-300">Custom Title (Optional)</label>
            <input
              type="text"
              placeholder="e.g. AI Podcast Highlights"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full bg-zinc-800/60 border border-zinc-700 rounded-lg px-3 py-2 text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-brand-500"
            />
          </div>

          {/* AI Settings Matrix */}
          <div className="grid grid-cols-2 gap-3 pt-2">
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-zinc-300">Target Aspect Ratio</label>
              <select
                value={aspectRatio}
                onChange={(e) => setAspectRatio(e.target.value)}
                className="w-full bg-zinc-800/60 border border-zinc-700 rounded-lg px-2.5 py-2 text-xs text-white focus:outline-none focus:border-brand-500"
              >
                <option value="9:16">9:16 (TikTok, Shorts, Reels)</option>
                <option value="1:1">1:1 (Square Feed)</option>
                <option value="4:5">4:5 (Instagram Portrait)</option>
                <option value="16:9">16:9 (Landscape Standard)</option>
              </select>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-zinc-300">Caption Style Preset</label>
              <select
                value={captionStyle}
                onChange={(e) => setCaptionStyle(e.target.value)}
                className="w-full bg-zinc-800/60 border border-zinc-700 rounded-lg px-2.5 py-2 text-xs text-white focus:outline-none focus:border-brand-500"
              >
                <option value="hormozi">Alex Hormozi (Yellow/Green)</option>
                <option value="neon">Cyberpunk Neon (Cyan Glow)</option>
                <option value="beast">Beast Retention (Impact Gold)</option>
                <option value="minimal">Minimalist Clean (White)</option>
              </select>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 bg-zinc-950/50 border-t border-zinc-800 flex items-center justify-between">
          <div className="flex items-center gap-1.5 text-[11px] text-zinc-400">
            <CheckCircle2 className="w-3.5 h-3.5 text-brand-400" />
            <span>AI automatically isolates best viral hooks</span>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-3.5 py-2 rounded-lg text-xs font-medium text-zinc-400 hover:text-white hover:bg-zinc-800 transition"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={() => handleSubmit()}
              disabled={isSubmitting}
              className="flex items-center gap-2 bg-brand-500 hover:bg-brand-400 text-black font-bold text-xs px-5 py-2.5 rounded-lg shadow-md shadow-brand-500/25 transition-all hover:scale-[1.02] active:scale-[0.98] disabled:opacity-60 cursor-pointer"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Queuing Pipeline...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  <span>Generate AI Clips</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
