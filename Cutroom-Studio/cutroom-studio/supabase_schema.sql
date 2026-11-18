-- ==============================================================================
-- Cutroom Studio Production Supabase Schema
-- Scalable Billion-Dollar SaaS Architecture for High-Volume Video Processing
-- ==============================================================================

-- 1. Users Table
CREATE TABLE IF NOT EXISTS public.users (
  id TEXT PRIMARY KEY,
  email TEXT UNIQUE,
  pw TEXT,
  name TEXT NOT NULL,
  created DOUBLE PRECISION NOT NULL,
  plan TEXT NOT NULL DEFAULT 'Creator',
  preferred TEXT NOT NULL DEFAULT '{}',
  stripe_id TEXT UNIQUE
);

-- 2. Sessions Table
CREATE TABLE IF NOT EXISTS public.sessions (
  token TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  expires DOUBLE PRECISION NOT NULL
);
CREATE INDEX IF NOT EXISTS session_expiry ON public.sessions(expires);

-- 3. Projects Table
CREATE TABLE IF NOT EXISTS public.projects (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  filename TEXT NOT NULL,
  status TEXT NOT NULL,
  bytes BIGINT NOT NULL DEFAULT 0,
  received BIGINT NOT NULL DEFAULT 0,
  source_url TEXT,
  sample TEXT,
  prefs TEXT NOT NULL,
  info TEXT NOT NULL DEFAULT '{}',
  created DOUBLE PRECISION NOT NULL,
  updated DOUBLE PRECISION NOT NULL
);
CREATE INDEX IF NOT EXISTS project_owner ON public.projects(user_id, updated DESC);

-- 4. Clips Table (Multi-Clip Viral Moments)
CREATE TABLE IF NOT EXISTS public.clips (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES public.projects(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  start_at DOUBLE PRECISION NOT NULL,
  end_at DOUBLE PRECISION NOT NULL,
  score INTEGER,
  insights TEXT NOT NULL,
  edit TEXT NOT NULL,
  version INTEGER NOT NULL DEFAULT 1,
  created DOUBLE PRECISION NOT NULL
);
CREATE INDEX IF NOT EXISTS clip_parent ON public.clips(project_id, score DESC);

-- 5. Jobs Queue Table (Asynchronous Processing Pipeline)
CREATE TABLE IF NOT EXISTS public.jobs (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES public.projects(id) ON DELETE CASCADE,
  clip_id TEXT REFERENCES public.clips(id) ON DELETE SET NULL,
  user_id TEXT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  kind TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'queued',
  progress INTEGER NOT NULL DEFAULT 0,
  stage TEXT NOT NULL DEFAULT 'Waiting for a worker',
  payload TEXT NOT NULL DEFAULT '{}',
  output TEXT,
  error TEXT,
  attempts INTEGER NOT NULL DEFAULT 0,
  worker TEXT,
  lease DOUBLE PRECISION,
  created DOUBLE PRECISION NOT NULL,
  updated DOUBLE PRECISION NOT NULL
);
CREATE INDEX IF NOT EXISTS job_queue ON public.jobs(status, created);
CREATE INDEX IF NOT EXISTS job_owner ON public.jobs(user_id, kind, created DESC);

-- 6. Usage Tracking
CREATE TABLE IF NOT EXISTS public.usage (
  project_id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  duration DOUBLE PRECISION NOT NULL,
  created DOUBLE PRECISION NOT NULL
);
CREATE INDEX IF NOT EXISTS usage_window ON public.usage(user_id, created);

-- 7. Media & Font Assets Table
CREATE TABLE IF NOT EXISTS public.assets (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  kind TEXT NOT NULL,
  name TEXT NOT NULL,
  path TEXT NOT NULL,
  details TEXT NOT NULL,
  created DOUBLE PRECISION NOT NULL
);
CREATE INDEX IF NOT EXISTS asset_owner ON public.assets(user_id, created DESC);

-- 8. Brand Kits Table
CREATE TABLE IF NOT EXISTS public.brands (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  data TEXT NOT NULL,
  created DOUBLE PRECISION NOT NULL
);
CREATE INDEX IF NOT EXISTS brand_owner ON public.brands(user_id, created DESC);

-- 9. Throttles & Rate-Limiting Table
CREATE TABLE IF NOT EXISTS public.throttles (
  key TEXT PRIMARY KEY,
  since DOUBLE PRECISION NOT NULL,
  hits INTEGER NOT NULL DEFAULT 0
);

-- 10. Enable Row Level Security (RLS) for SaaS Security
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.clips ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.assets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.brands ENABLE ROW LEVEL SECURITY;

-- Service Role Policy (Bypasses RLS for Cutroom Backend Worker)
CREATE POLICY "Service Role Full Access Users" ON public.users FOR ALL USING (true);
CREATE POLICY "Service Role Full Access Projects" ON public.projects FOR ALL USING (true);
CREATE POLICY "Service Role Full Access Clips" ON public.clips FOR ALL USING (true);
CREATE POLICY "Service Role Full Access Jobs" ON public.jobs FOR ALL USING (true);
CREATE POLICY "Service Role Full Access Assets" ON public.assets FOR ALL USING (true);
CREATE POLICY "Service Role Full Access Brands" ON public.brands FOR ALL USING (true);
