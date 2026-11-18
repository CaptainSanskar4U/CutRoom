from contextlib import contextmanager
from datetime import datetime, timezone
import json, sqlite3, time, uuid
from .config import DATA, MEDIA, DATABASE_URL

POSTGRES = DATABASE_URL.startswith(('postgresql://','postgres://'))
NOW = time.time

def uid():
    return uuid.uuid4().hex

def dump(value):
    return json.dumps(value, separators=(',', ':'), ensure_ascii=False, allow_nan=False)

def load(value, default=None):
    return json.loads(value) if value else default

def month_start():
    return datetime.now(timezone.utc).replace(day=1,hour=0,minute=0,second=0,microsecond=0).timestamp()

class Connection:
    def __init__(self, c): self.c = c
    def execute(self, sql, args=()):
        return self.c.execute(sql.replace('?', '%s') if POSTGRES else sql, args)

_POOL = None

def get_pool():
    global _POOL
    if _POOL is None and POSTGRES:
        try:
            from psycopg_pool import ConnectionPool
            from psycopg.rows import dict_row
            _POOL = ConnectionPool(
                conninfo=DATABASE_URL,
                min_size=2,
                max_size=10,
                kwargs={"row_factory": dict_row, "connect_timeout": 8, "prepare_threshold": None},
                open=True,
                timeout=10.0,
            )
        except Exception:
            _POOL = False
    return _POOL if _POOL else None

@contextmanager
def db(write=False):
    pool = get_pool()
    if pool:
        try:
            with pool.connection(timeout=6.0) as c:
                yield Connection(c)
                c.commit()
                return
        except Exception:
            pass

    if POSTGRES:
        import psycopg
        from psycopg.rows import dict_row
        c = psycopg.connect(DATABASE_URL, row_factory=dict_row, connect_timeout=8, prepare_threshold=None)
    else:
        c = sqlite3.connect(DATA / 'cutroom.sqlite3', timeout=15, isolation_level=None)
        c.row_factory = sqlite3.Row
        c.execute('PRAGMA foreign_keys=ON')
        c.execute('PRAGMA busy_timeout=15000')
    try:
        if write and not POSTGRES: c.execute('BEGIN IMMEDIATE')
        yield Connection(c)
        c.commit()
    except BaseException:
        c.rollback()
        raise
    finally: c.close()

SCHEMA = '''
CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY, email TEXT UNIQUE, pw TEXT, name TEXT NOT NULL, created DOUBLE PRECISION NOT NULL,
  plan TEXT NOT NULL DEFAULT 'Creator', preferred TEXT NOT NULL DEFAULT '{}', stripe_id TEXT UNIQUE
);
CREATE TABLE IF NOT EXISTS sessions (
  token TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE, expires DOUBLE PRECISION NOT NULL
);
CREATE INDEX IF NOT EXISTS session_expiry ON sessions(expires);
CREATE TABLE IF NOT EXISTS projects (
  id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  title TEXT NOT NULL, filename TEXT NOT NULL, status TEXT NOT NULL, bytes BIGINT NOT NULL DEFAULT 0,
  received BIGINT NOT NULL DEFAULT 0, source_url TEXT, sample TEXT, prefs TEXT NOT NULL,
  info TEXT NOT NULL DEFAULT '{}', created DOUBLE PRECISION NOT NULL, updated DOUBLE PRECISION NOT NULL
);
CREATE INDEX IF NOT EXISTS project_owner ON projects(user_id,updated DESC);
CREATE TABLE IF NOT EXISTS clips (
  id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  title TEXT NOT NULL, start_at DOUBLE PRECISION NOT NULL, end_at DOUBLE PRECISION NOT NULL,
  score INTEGER, insights TEXT NOT NULL, edit TEXT NOT NULL, version INTEGER NOT NULL DEFAULT 1,
  created DOUBLE PRECISION NOT NULL
);
CREATE INDEX IF NOT EXISTS clip_parent ON clips(project_id,score DESC);
CREATE TABLE IF NOT EXISTS jobs (
  id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  clip_id TEXT REFERENCES clips(id) ON DELETE SET NULL, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  kind TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'queued', progress INTEGER NOT NULL DEFAULT 0,
  stage TEXT NOT NULL DEFAULT 'Waiting for a worker', payload TEXT NOT NULL DEFAULT '{}', output TEXT,
  error TEXT, attempts INTEGER NOT NULL DEFAULT 0, worker TEXT, lease DOUBLE PRECISION,
  created DOUBLE PRECISION NOT NULL, updated DOUBLE PRECISION NOT NULL
);
CREATE INDEX IF NOT EXISTS job_queue ON jobs(status,created);
CREATE INDEX IF NOT EXISTS job_owner ON jobs(user_id,kind,created DESC);
CREATE TABLE IF NOT EXISTS usage (
  project_id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  seconds DOUBLE PRECISION NOT NULL, created DOUBLE PRECISION NOT NULL
);
CREATE INDEX IF NOT EXISTS usage_user ON usage(user_id,created);
CREATE TABLE IF NOT EXISTS assets (
  id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  kind TEXT NOT NULL, name TEXT NOT NULL, path TEXT NOT NULL, details TEXT NOT NULL, created DOUBLE PRECISION NOT NULL
);
CREATE TABLE IF NOT EXISTS brands (
  id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name TEXT NOT NULL, data TEXT NOT NULL, created DOUBLE PRECISION NOT NULL
);
CREATE TABLE IF NOT EXISTS workers (id TEXT PRIMARY KEY, seen DOUBLE PRECISION NOT NULL);
CREATE TABLE IF NOT EXISTS webhook_events (id TEXT PRIMARY KEY, created DOUBLE PRECISION NOT NULL);
CREATE TABLE IF NOT EXISTS throttles (key TEXT PRIMARY KEY, since DOUBLE PRECISION NOT NULL, hits INTEGER NOT NULL);
'''

def init():
    DATA.mkdir(mode=0o700, parents=True, exist_ok=True)
    MEDIA.mkdir(mode=0o700, parents=True, exist_ok=True)
    with db(True) as c:
        if POSTGRES: c.execute('SELECT pg_advisory_xact_lock(47395408)')
        for statement in SCHEMA.strip().split(';'):
            if statement.strip(): c.execute(statement)
    if not POSTGRES:
        with db() as c: c.execute('PRAGMA journal_mode=WAL')


def enqueue(c, user, project, kind, payload=None, clip=None):
    id = uid(); now = NOW()
    c.execute('INSERT INTO jobs (id,project_id,user_id,clip_id,kind,payload,created,updated) VALUES(?,?,?,?,?,?,?,?)',
              (id,project,user,clip,kind,dump(payload or {}),now,now))
    return id


def lock_suffix(skip=False):
    return (' FOR UPDATE SKIP LOCKED' if skip else ' FOR UPDATE') if POSTGRES else ''


def claim(worker):
    now = NOW()
    with db(True) as c:
        expired = c.execute("SELECT id,project_id,kind FROM jobs WHERE status='running' AND lease<? AND attempts>=3" + lock_suffix(True),(now,)).fetchall()
        for job in expired:
            c.execute("UPDATE jobs SET status='failed',stage='Worker interrupted',error='The worker stopped repeatedly. Retry this job when services are available.',updated=? WHERE id=? AND status='running'",(now,job['id']))
            if job['kind']=='analyze': c.execute("UPDATE projects SET status='failed',updated=? WHERE id=?",(now,job['project_id']))
        row = c.execute("SELECT * FROM jobs WHERE status='queued' OR (status='running' AND lease<? AND attempts<3) ORDER BY created LIMIT 1" + lock_suffix(True), (now,)).fetchone()
        if not row: return None
        c.execute("UPDATE jobs SET status='running',progress=0,stage='Preparing job',worker=?,lease=?,attempts=attempts+1,error=NULL,updated=? WHERE id=?",
                  (worker,now+90,now,row['id']))
        if row['kind']=='analyze': c.execute("UPDATE projects SET status='processing',updated=? WHERE id=?", (now,row['project_id']))
        return {**dict(row),'worker':worker,'attempts':row['attempts']+1}


def public_job(row):
    return {k:row[k] for k in ('id','project_id','clip_id','kind','status','progress','stage','error','attempts','created','updated')} | {'output':load(row['output']), 'title':(load(row['payload'],{}).get('clip') or {}).get('title') if row['kind']=='render' else None}
