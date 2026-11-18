export interface User {
  id: string;
  email: string;
  full_name: string;
  plan: string;
  credits_remaining: number;
  created_at: string;
}

export interface Project {
  id: string;
  user_id: string;
  title: string;
  status: string;
  video_count: number;
  created_at: string;
  updated_at: string;
}

export interface WordItem {
  word: string;
  start: number;
  end: number;
  probability?: number;
  speaker?: string;
}

export interface TranscriptSegment {
  id: number;
  start: number;
  end: number;
  text: string;
  speaker: string;
  words: WordItem[];
}

export interface TranscriptData {
  language: string;
  language_probability: number;
  duration: number;
  full_text: string;
  segments: TranscriptSegment[];
  words: WordItem[];
}

export interface SourceVideo {
  id: string;
  project_id: string;
  title: string;
  filename: string;
  filepath: string;
  source_url?: string;
  duration: number;
  width: number;
  height: number;
  fps: number;
  status: 'uploaded' | 'extracting_audio' | 'transcribing' | 'analyzing_virality' | 'tracking_faces' | 'completed' | 'failed';
  progress: number;
  status_message?: string;
  thumbnail_path?: string;
  has_transcript: boolean;
  clip_count: number;
  transcript?: TranscriptData;
  created_at: string;
  updated_at: string;
}

export interface ScoreBreakdown {
  hook: number;
  flow: number;
  value: number;
  emotional_intensity: number;
  context_independence: number;
  ending: number;
}

export interface Clip {
  id: string;
  video_id: string;
  start_time: number;
  end_time: number;
  duration: number;
  title: string;
  description?: string;
  virality_score: number;
  score_breakdown?: ScoreBreakdown;
  virality_reason?: string;
  hook_text?: string;
  social_caption?: string;
  aspect_ratio: '9:16' | '1:1' | '16:9' | '4:5';
  crop_mode: 'fit_blur' | 'auto_face' | 'split_screen' | 'center' | 'manual';
  crop_x: number;
  crop_y: number;
  caption_style: 'hormozi' | 'neon' | 'minimal' | 'beast';
  caption_settings?: any;
  custom_words?: WordItem[];
  thumbnail_url?: string;
  video_preview_url?: string;
  rendered_url?: string;
  render_status: 'idle' | 'rendering' | 'completed' | 'failed';
  render_progress: number;
  render_message?: string;
  created_at: string;
  updated_at: string;
}

export interface DashboardStats {
  total_projects: number;
  total_videos: number;
  total_clips_generated: number;
  exported_clips: number;
  minutes_processed: number;
  credits_remaining: number;
  plan: string;
}

export interface TemplatePreset {
  id: string;
  name: string;
  description: string;
  preview_text: string;
  highlight_color: string;
  font_family: string;
  tag: string;
}
