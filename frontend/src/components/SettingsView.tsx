import React from 'react';
import { User, Crown, Key, Cpu, ShieldCheck, HardDrive, CheckCircle2 } from 'lucide-react';
import { User as UserType } from '../types';

interface SettingsViewProps {
  user: UserType | null;
}

export const SettingsView: React.FC<SettingsViewProps> = ({ user }) => {
  return (
    <div className="max-w-4xl space-y-6 animate-in fade-in duration-300">
      <div className="p-6 bg-dark-900 border border-zinc-800 rounded-2xl space-y-1">
        <h1 className="text-xl font-black text-white tracking-tight">Account & Engine Settings</h1>
        <p className="text-xs text-zinc-400">
          Manage your subscription plan, AI processing engines, and API configurations.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Subscription / Plan Card */}
        <div className="p-6 bg-dark-900 border border-zinc-800 rounded-2xl space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm font-bold text-white">
              <Crown className="w-4 h-4 text-amber-400" />
              <span>Subscription & Usage</span>
            </div>
            <span className="text-xs font-bold px-2 py-0.5 rounded bg-brand-500/10 text-brand-400 border border-brand-500/20">
              {user?.plan || 'Pro'} Tier
            </span>
          </div>

          <div className="space-y-2">
            <div className="flex justify-between text-xs text-zinc-300">
              <span>Processing Credits Remaining</span>
              <strong className="text-brand-400 font-mono">{user?.credits_remaining || 180} Minutes</strong>
            </div>
            <div className="w-full h-2 bg-zinc-800 rounded-full overflow-hidden">
              <div className="w-3/4 h-full bg-brand-500 rounded-full" />
            </div>
            <p className="text-[10px] text-zinc-400">Auto-renews monthly • Unlimited 1080p rendering</p>
          </div>

          <div className="pt-3 border-t border-zinc-800 flex items-center justify-between">
            <span className="text-xs text-zinc-300">Account: {user?.email}</span>
            <button className="text-xs text-brand-400 hover:underline font-semibold">
              Upgrade to Enterprise
            </button>
          </div>
        </div>

        {/* AI Processing Engine Configuration */}
        <div className="p-6 bg-dark-900 border border-zinc-800 rounded-2xl space-y-4">
          <div className="flex items-center gap-2 text-sm font-bold text-white">
            <Cpu className="w-4 h-4 text-brand-400" />
            <span>AI Models & Hardware</span>
          </div>

          <div className="space-y-3 text-xs">
            <div className="flex items-center justify-between p-2.5 rounded-lg bg-zinc-800/40 border border-zinc-800">
              <div>
                <p className="font-semibold text-zinc-200">Speech-To-Text Model</p>
                <p className="text-[10px] text-zinc-400">faster-whisper (CTranslate2)</p>
              </div>
              <span className="text-emerald-400 font-mono font-bold">tiny (CPU int8)</span>
            </div>

            <div className="flex items-center justify-between p-2.5 rounded-lg bg-zinc-800/40 border border-zinc-800">
              <div>
                <p className="font-semibold text-zinc-200">Computer Vision Reframer</p>
                <p className="text-[10px] text-zinc-400">OpenCV Face Lock & Tracking</p>
              </div>
              <span className="text-emerald-400 font-mono font-bold">Enabled</span>
            </div>

            <div className="flex items-center justify-between p-2.5 rounded-lg bg-zinc-800/40 border border-zinc-800">
              <div>
                <p className="font-semibold text-zinc-200">Subtitle Render Engine</p>
                <p className="text-[10px] text-zinc-400">FFmpeg 9.0 libass Burn-in</p>
              </div>
              <span className="text-emerald-400 font-mono font-bold">Active</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
