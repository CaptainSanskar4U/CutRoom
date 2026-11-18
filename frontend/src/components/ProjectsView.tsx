import React, { useState } from 'react';
import { FolderKanban, Plus, Film, Trash2, Calendar, Sparkles } from 'lucide-react';
import { api } from '../api';
import { Project } from '../types';

interface ProjectsViewProps {
  projects: Project[];
  onSelectProject: (proj: Project) => void;
  onRefresh: () => void;
}

export const ProjectsView: React.FC<ProjectsViewProps> = ({
  projects,
  onSelectProject,
  onRefresh
}) => {
  const [newTitle, setNewTitle] = useState('');
  const [isCreating, setIsCreating] = useState(false);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim()) return;
    try {
      await api.createProject(newTitle.trim());
      setNewTitle('');
      setIsCreating(false);
      onRefresh();
    } catch (err) {
      console.error(err);
    }
  };

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (confirm('Delete this project and its videos?')) {
      try {
        await api.deleteProject(id);
        onRefresh();
      } catch (err) {
        console.error(err);
      }
    }
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      <div className="flex items-center justify-between p-6 bg-dark-900 border border-zinc-800 rounded-2xl">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold uppercase tracking-wider text-brand-400">
              Workspace & Libraries
            </span>
          </div>
          <h1 className="text-xl font-black text-white tracking-tight">Project Management</h1>
          <p className="text-xs text-zinc-400">
            Organize podcasts, webinars, talks, and long-form video archives into persistent projects.
          </p>
        </div>

        <button
          onClick={() => setIsCreating(!isCreating)}
          className="flex items-center gap-2 bg-brand-500 hover:bg-brand-400 text-black font-semibold text-xs px-4 py-2 rounded-lg shadow-sm transition"
        >
          <Plus className="w-4 h-4" />
          <span>New Project</span>
        </button>
      </div>

      {isCreating && (
        <form onSubmit={handleCreate} className="p-4 bg-zinc-900 border border-brand-500/30 rounded-xl flex items-center gap-3">
          <input
            type="text"
            placeholder="Project name (e.g. YouTube Weekly Show)"
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
            className="flex-1 bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-brand-500"
            autoFocus
          />
          <button
            type="submit"
            className="bg-brand-500 hover:bg-brand-400 text-black font-semibold text-xs px-4 py-2 rounded-lg transition"
          >
            Create
          </button>
          <button
            type="button"
            onClick={() => setIsCreating(false)}
            className="text-zinc-400 hover:text-white text-xs px-3 py-2"
          >
            Cancel
          </button>
        </form>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {projects.map((p) => (
          <div
            key={p.id}
            onClick={() => onSelectProject(p)}
            className="p-5 bg-dark-900 border border-zinc-800 hover:border-zinc-700 rounded-2xl shadow-lg cursor-pointer transition-all flex flex-col justify-between space-y-4 group"
          >
            <div className="space-y-2">
              <div className="flex items-start justify-between">
                <div className="p-2.5 rounded-xl bg-zinc-800/80 text-brand-400 border border-zinc-700/60 group-hover:bg-brand-500/10 transition">
                  <FolderKanban className="w-5 h-5" />
                </div>
                <button
                  onClick={(e) => handleDelete(p.id, e)}
                  className="text-zinc-500 hover:text-rose-400 p-1.5 transition"
                  title="Delete project"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>

              <div>
                <h3 className="text-sm font-bold text-white group-hover:text-brand-300 transition">
                  {p.title}
                </h3>
                <p className="text-[11px] text-zinc-400 flex items-center gap-1.5 mt-1">
                  <Film className="w-3.5 h-3.5 text-zinc-400" />
                  <span>{p.video_count} source videos</span>
                </p>
              </div>
            </div>

            <div className="pt-3 border-t border-zinc-800 flex items-center justify-between text-[11px] text-zinc-400">
              <div className="flex items-center gap-1">
                <Calendar className="w-3 h-3 text-zinc-400" />
                <span>Created {new Date(p.created_at).toLocaleDateString()}</span>
              </div>
              <span className="text-brand-400 font-semibold group-hover:translate-x-1 transition-transform">
                Open →
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
