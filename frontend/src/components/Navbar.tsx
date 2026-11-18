import React from 'react';
import { Sparkles, UploadCloud, Video, Crown, LogOut, User as UserIcon } from 'lucide-react';
import { User } from '../types';

interface NavbarProps {
  user: User | null;
  onOpenUpload: () => void;
  onLogout: () => void;
  onOpenAuth: () => void;
  activeView: string;
  setActiveView: (view: string) => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  user,
  onOpenUpload,
  onLogout,
  onOpenAuth,
  setActiveView
}) => {
  return (
    <header className="h-16 border-b border-zinc-800 bg-dark-900/80 backdrop-blur sticky top-0 z-40 px-6 flex items-center justify-between">
      {/* Brand Logo */}
      <div 
        className="flex items-center gap-3 cursor-pointer group"
        onClick={() => setActiveView('dashboard')}
      >
        <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-brand-600 via-brand-500 to-emerald-400 p-[1px] shadow-lg shadow-brand-500/20">
          <div className="w-full h-full bg-dark-950 rounded-[11px] flex items-center justify-center">
            <Sparkles className="w-5 h-5 text-brand-400 group-hover:rotate-12 transition-transform duration-300" />
          </div>
        </div>
        <div>
          <div className="flex items-center gap-1.5">
            <span className="font-extrabold text-lg tracking-tight bg-gradient-to-r from-white via-zinc-200 to-zinc-400 bg-clip-text text-transparent">
              AutoClip
            </span>
            <span className="text-[10px] font-semibold tracking-wider uppercase px-1.5 py-0.5 rounded bg-brand-500/10 text-brand-400 border border-brand-500/20">
              AI PRO
            </span>
          </div>
          <p className="text-[11px] text-zinc-500 -mt-0.5">OpusClip Autonomous Engine</p>
        </div>
      </div>

      {/* Actions & User */}
      <div className="flex items-center gap-4">
        {/* Quick Upload CTA */}
        <button
          onClick={onOpenUpload}
          className="flex items-center gap-2 bg-gradient-to-r from-brand-600 to-brand-500 hover:from-brand-500 hover:to-brand-400 text-black font-semibold text-xs px-4 py-2 rounded-lg shadow-md shadow-brand-500/20 transition-all hover:scale-[1.02] active:scale-[0.98]"
        >
          <UploadCloud className="w-4 h-4" />
          <span>Repurpose Video</span>
        </button>

        {/* User Credits & Plan */}
        {user ? (
          <div className="flex items-center gap-3 pl-2 border-l border-zinc-800">
            <div className="hidden sm:flex flex-col items-end">
              <div className="flex items-center gap-1.5 text-xs font-medium text-zinc-200">
                <Crown className="w-3.5 h-3.5 text-amber-400" />
                <span>{user.plan} Plan</span>
              </div>
              <span className="text-[11px] text-zinc-400">
                <strong className="text-brand-400">{user.credits_remaining}m</strong> credits left
              </span>
            </div>

            <div className="flex items-center gap-2 bg-zinc-800/60 p-1.5 rounded-lg border border-zinc-700/50">
              <div className="w-7 h-7 rounded-full bg-zinc-700 flex items-center justify-center text-xs font-bold text-zinc-300">
                {user.full_name ? user.full_name.charAt(0).toUpperCase() : 'U'}
              </div>
              <button
                onClick={onLogout}
                title="Sign out"
                className="text-zinc-400 hover:text-rose-400 p-1 transition-colors"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          </div>
        ) : (
          <button
            onClick={onOpenAuth}
            className="flex items-center gap-1.5 text-xs font-medium text-zinc-300 hover:text-white bg-zinc-800 hover:bg-zinc-700 px-3 py-1.5 rounded-lg border border-zinc-700 transition"
          >
            <UserIcon className="w-3.5 h-3.5" />
            <span>Sign In</span>
          </button>
        )}
      </div>
    </header>
  );
};
