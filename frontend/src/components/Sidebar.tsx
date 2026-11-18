import React from 'react';
import { 
  LayoutDashboard, 
  FolderKanban, 
  Scissors, 
  Film, 
  Palette, 
  DownloadCloud, 
  Settings,
  HelpCircle,
  TrendingUp
} from 'lucide-react';

interface SidebarProps {
  activeView: string;
  setActiveView: (view: string) => void;
  selectedClipId: string | null;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeView,
  setActiveView,
  selectedClipId
}) => {
  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'projects', label: 'Projects', icon: FolderKanban },
    { id: 'clips', label: 'AI Clips Explorer', icon: Scissors, badge: 'Viral' },
    { id: 'editor', label: 'Clip Studio & Editor', icon: Film, disabled: !selectedClipId },
    { id: 'templates', label: 'Caption Styles', icon: Palette },
    { id: 'exports', label: 'Export Center', icon: DownloadCloud },
    { id: 'settings', label: 'Settings & Usage', icon: Settings },
  ];

  return (
    <aside className="w-64 border-r border-zinc-800 bg-dark-900/40 p-4 flex flex-col justify-between hidden md:flex shrink-0">
      <div className="space-y-6">
        <div className="space-y-1">
          <p className="px-3 text-[10px] font-bold uppercase tracking-wider text-zinc-500 mb-2">
            Studio Navigation
          </p>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeView === item.id;
            return (
              <button
                key={item.id}
                onClick={() => !item.disabled && setActiveView(item.id)}
                disabled={item.disabled}
                className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-xs font-medium transition-all ${
                  isActive
                    ? 'bg-brand-500/10 text-brand-400 border border-brand-500/20 shadow-sm'
                    : item.disabled
                    ? 'text-zinc-600 cursor-not-allowed'
                    : 'text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800/50'
                }`}
              >
                <div className="flex items-center gap-3">
                  <Icon className={`w-4 h-4 ${isActive ? 'text-brand-400' : 'text-zinc-400'}`} />
                  <span>{item.label}</span>
                </div>
                {item.badge && (
                  <span className="text-[9px] font-bold px-1.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {/* Feature highlight widget */}
        <div className="p-3.5 rounded-xl bg-gradient-to-b from-zinc-800/40 to-zinc-900/80 border border-zinc-800/80 space-y-2.5">
          <div className="flex items-center gap-2 text-xs font-semibold text-zinc-200">
            <TrendingUp className="w-4 h-4 text-brand-400" />
            <span>AI Virality Algorithm</span>
          </div>
          <p className="text-[11px] text-zinc-400 leading-relaxed">
            Multi-factor scoring analyzes opening hooks, narrative flow, and emotional density to guarantee maximum watch-time.
          </p>
          <div className="flex items-center justify-between pt-1 border-t border-zinc-800 text-[10px] text-zinc-400">
            <span>Score threshold:</span>
            <span className="font-semibold text-brand-400">0 - 99 Scale</span>
          </div>
        </div>
      </div>

      <div className="pt-4 border-t border-zinc-800/80 space-y-2">
        <div className="flex items-center justify-between px-3 text-[11px] text-zinc-400">
          <span>Engine Status</span>
          <span className="flex items-center gap-1.5 text-emerald-400 font-medium">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            Active
          </span>
        </div>
        <p className="px-3 text-[10px] text-zinc-400">
          FFmpeg 9.0 • Whisper AI • OpenCV Tracking
        </p>
      </div>
    </aside>
  );
};
