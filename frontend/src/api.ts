import axios from 'axios';
import { User, Project, SourceVideo, Clip, DashboardStats, TemplatePreset } from './types';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const client = axios.create({
  baseURL: API_BASE,
});

client.interceptors.request.use((config) => {
  const token = localStorage.getItem('autoclip_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const api = {
  // Auth
  register: async (data: { email: string; password: string; full_name?: string }) => {
    const res = await client.post<{ access_token: string; user: User }>('/api/auth/register', data);
    localStorage.setItem('autoclip_token', res.data.access_token);
    return res.data;
  },
  login: async (data: { email: string; password: string }) => {
    const res = await client.post<{ access_token: string; user: User }>('/api/auth/login', data);
    localStorage.setItem('autoclip_token', res.data.access_token);
    return res.data;
  },
  getMe: async () => {
    const res = await client.get<User>('/api/auth/me');
    return res.data;
  },
  logout: () => {
    localStorage.removeItem('autoclip_token');
  },

  // Projects
  getProjects: async () => {
    const res = await client.get<Project[]>('/api/projects');
    return res.data;
  },
  createProject: async (title: string) => {
    const res = await client.post<Project>('/api/projects', { title });
    return res.data;
  },
  deleteProject: async (id: string) => {
    await client.delete(`/api/projects/${id}`);
  },

  // Videos
  getVideos: async (projectId?: string) => {
    const res = await client.get<SourceVideo[]>('/api/videos', {
      params: projectId ? { project_id: projectId } : {}
    });
    return res.data;
  },
  getVideo: async (id: string) => {
    const res = await client.get<SourceVideo>(`/api/videos/${id}`);
    return res.data;
  },
  uploadVideo: async (file: File, projectId?: string, title?: string, autoProcess = false) => {
    const formData = new FormData();
    formData.append('file', file);
    if (projectId) formData.append('project_id', projectId);
    if (title) formData.append('title', title);
    formData.append('auto_process', String(autoProcess));

    const res = await client.post<SourceVideo>('/api/videos/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  },
  importUrl: async (url: string, projectId?: string, title?: string, aspectRatio?: string, captionStyle?: string) => {
    const res = await client.post<SourceVideo>('/api/videos/import-url', {
      url: url.trim(),
      project_id: projectId || undefined,
      title: title || undefined,
      aspect_ratio: aspectRatio || '9:16',
      caption_style: captionStyle || 'hormozi'
    });
    return res.data;
  },
  processVideo: async (id: string, options?: { aspect_ratio?: string; min_clip_duration?: number; max_clip_duration?: number; caption_style?: string }) => {
    const res = await client.post(`/api/videos/${id}/process`, options || {});
    return res.data;
  },
  deleteVideo: async (id: string) => {
    await client.delete(`/api/videos/${id}`);
  },

  // Clips
  getClips: async (videoId: string) => {
    const res = await client.get<Clip[]>('/api/clips', { params: { video_id: videoId } });
    return res.data;
  },
  getClip: async (clipId: string) => {
    const res = await client.get<Clip>(`/api/clips/${clipId}`);
    return res.data;
  },
  updateClip: async (clipId: string, data: Partial<Clip>) => {
    const res = await client.put<Clip>(`/api/clips/${clipId}`, data);
    return res.data;
  },
  renderClip: async (clipId: string, options?: { aspect_ratio?: string; caption_style?: string; crop_mode?: string; burn_captions?: boolean }) => {
    const res = await client.post<Clip>(`/api/clips/${clipId}/render`, options || {});
    return res.data;
  },
  deleteClip: async (clipId: string) => {
    await client.delete(`/api/clips/${clipId}`);
  },

  // Templates
  getTemplates: async () => {
    const res = await client.get<TemplatePreset[]>('/api/templates');
    return res.data;
  },

  // Stats
  getStats: async () => {
    const res = await client.get<DashboardStats>('/api/stats/dashboard');
    return res.data;
  },

  resolveUrl: (path?: string) => {
    if (!path) return '';
    if (path.startsWith('http://') || path.startsWith('https://')) return path;
    return `${API_BASE}${path}`;
  }
};
