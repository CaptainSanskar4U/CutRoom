import React, { useState } from 'react';
import { Palette, Sparkles, Check, Type, Sliders, Layers } from 'lucide-react';
import { TemplatePreset } from '../types';

interface BrandTemplatesViewProps {
  templates: TemplatePreset[];
}

export const BrandTemplatesView: React.FC<BrandTemplatesViewProps> = ({ templates }) => {
  const [selectedPreset, setSelectedPreset] = useState<string>('hormozi');

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      <div className="p-6 bg-dark-900 border border-zinc-800 rounded-2xl space-y-1">
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold uppercase tracking-wider text-brand-400">
            Brand Identity & Design System
          </span>
        </div>
        <h1 className="text-xl font-black text-white tracking-tight">Caption Styles & Brand Templates</h1>
        <p className="text-xs text-zinc-400">
          Professional animated caption presets inspired by the top creators (Alex Hormozi, MrBeast, Vox). Custom font styles, animated highlights, and brand colors.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {templates.map((tpl) => {
          const isSelected = selectedPreset === tpl.id;
          return (
            <div
              key={tpl.id}
              onClick={() => setSelectedPreset(tpl.id)}
              className={`p-6 rounded-2xl border cursor-pointer transition-all flex flex-col justify-between space-y-6 ${
                isSelected
                  ? 'bg-brand-500/5 border-brand-500 shadow-xl'
                  : 'bg-dark-900 border-zinc-800 hover:border-zinc-700'
              }`}
            >
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    <div 
                      className="w-4 h-4 rounded-full shadow-md"
                      style={{ backgroundColor: tpl.highlight_color }}
                    />
                    <h3 className="text-base font-bold text-white">{tpl.name}</h3>
                  </div>
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-zinc-800 text-zinc-300 border border-zinc-700">
                    {tpl.tag}
                  </span>
                </div>
                <p className="text-xs text-zinc-400 leading-relaxed">{tpl.description}</p>
              </div>

              {/* Animated Live Preview Box */}
              <div className="p-6 rounded-xl bg-zinc-950 border border-zinc-800 text-center select-none shadow-inner">
                <p className="text-lg font-black tracking-tight uppercase">
                  <span>THIS IS </span>
                  <span 
                    className="underline decoration-2"
                    style={{ color: tpl.highlight_color }}
                  >
                    HOW YOU HOOK
                  </span>
                  <span> VIEWERS</span>
                </p>
                <span className="text-[10px] font-mono text-zinc-500 block mt-2">
                  Font: {tpl.font_family} • Highlight: {tpl.highlight_color}
                </span>
              </div>

              <div className="flex items-center justify-between pt-2 border-t border-zinc-800 text-xs">
                <span className="text-zinc-500">Preset Active</span>
                {isSelected ? (
                  <span className="flex items-center gap-1 text-brand-400 font-bold">
                    <Check className="w-4 h-4" /> Selected
                  </span>
                ) : (
                  <span className="text-zinc-400 hover:text-white">Click to Select</span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
