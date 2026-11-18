from pathlib import Path
import os
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / '.env')
load_dotenv(ROOT.parent.parent / '.env')

DATA = Path(os.environ.get('CUTROOM_DATA', ROOT / 'data')).resolve()
MODELS = Path(os.environ.get('CUTROOM_MODELS', ROOT / '.cache' / 'cutroom-models')).resolve()
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://postgres:password@localhost:5432/cutroom')
MEDIA = DATA / 'media'
MAX_BYTES = int(os.environ.get('CUTROOM_MAX_BYTES', 100 * 1024**3)) # 100 GB
MAX_SECONDS = int(os.environ.get('CUTROOM_MAX_SECONDS', 86400))     # 24 Hours
CHUNK_BYTES = 5 * 1024**2
THREADS = max(1, int(os.environ.get('CUTROOM_THREADS', 4)))
WHISPER_MODEL = os.environ.get('WHISPER_MODEL', 'base')
WHISPER_DEVICE = os.environ.get('WHISPER_DEVICE', 'cpu')
IMPORT_HOSTS = {x.strip().lower() for x in os.environ.get('CUTROOM_IMPORT_HOSTS', 'youtube.com,youtu.be,tiktok.com,x.com,twitter.com,vimeo.com,instagram.com,facebook.com,reddit.com,upload.wikimedia.org,images-assets.nasa.gov,svs.gsfc.nasa.gov,assets.science.nasa.gov').split(',') if x.strip()}
PUBLIC_ORIGIN = os.environ.get('CUTROOM_PUBLIC_ORIGIN', '').rstrip('/')
COOKIE_MODE = os.environ.get('CUTROOM_SECURE_COOKIE', 'auto')
FFMPEG = os.environ.get('FFMPEG_BIN','ffmpeg')
FFPROBE = os.environ.get('FFPROBE_BIN','ffprobe')
GUEST_ENABLED = os.environ.get('CUTROOM_GUEST', '1') == '1'
STRIPE_SECRET = os.environ.get('STRIPE_SECRET_KEY', '')
STRIPE_PRICE = os.environ.get('STRIPE_PRICE_ID', '')
STRIPE_WEBHOOK = os.environ.get('STRIPE_WEBHOOK_SECRET', '')
LLM_ENDPOINT = os.environ.get('CUTROOM_LLM_ENDPOINT', '')
LLM_KEY = os.environ.get('CUTROOM_LLM_API_KEY', '')
LLM_MODEL = os.environ.get('CUTROOM_LLM_MODEL', 'gpt-4.1-mini')
SUPABASE_URL = os.environ.get('SUPABASE_URL', '')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY', '')
SUPABASE_SECRET = os.environ.get('SUPABASE_SECRET', '')
SUPABASE_BUCKET = os.environ.get('SUPABASE_BUCKET', 'cutroom-media')
PLAN_LIMITS = {'Guest': 86400*365, 'Creator': 86400*365, 'Studio': 86400*365} # Unlimited processing
PLAN_STORAGE = {'Guest': 1000*1024**3, 'Creator': 1000*1024**3, 'Studio': 1000*1024**3} # 1 TB storage
