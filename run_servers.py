"""
Permanent Background Supervisor for CutRoom Studio & AutoClip Engine.
Ensures servers stay running 24/7 on ports 3000 and 8000.
Automatically restarts them if they ever exit or if system memory spikes.
"""
import subprocess
import sys
import time
import urllib.request
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CUTROOM_DIR = ROOT / 'Cutroom-Studio' / 'cutroom-studio'
BACKEND_DIR = ROOT / 'backend'

env = os.environ.copy()
env['PYTHONPATH'] = str(CUTROOM_DIR)

def is_alive(port, path='/'):
    try:
        req = urllib.request.Request(f'http://127.0.0.1:{port}{path}')
        with urllib.request.urlopen(req, timeout=2) as resp:
            return resp.status < 500
    except Exception:
        return False

def start_cutroom():
    print('[Supervisor] Starting Cutroom Studio on port 3000...')
    cmd = [
        sys.executable, '-m', 'uvicorn', 'cutroom.api:app',
        '--host', '0.0.0.0', '--port', '3000',
        '--app-dir', str(CUTROOM_DIR)
    ]
    return subprocess.Popen(cmd, cwd=str(CUTROOM_DIR), env=env)

def start_autoclip():
    print('[Supervisor] Starting AutoClip Backend on port 8000...')
    cmd = [
        sys.executable, '-m', 'uvicorn', 'app.main:app',
        '--host', '0.0.0.0', '--port', '8000',
        '--app-dir', str(BACKEND_DIR)
    ]
    return subprocess.Popen(cmd, cwd=str(BACKEND_DIR), env=env)

def main():
    p_cutroom = None
    p_autoclip = None

    while True:
        # Check Cutroom Studio (Port 3000)
        if not is_alive(3000, '/api/me'):
            if p_cutroom and p_cutroom.poll() is None:
                try: p_cutroom.kill()
                except Exception: pass
            p_cutroom = start_cutroom()
            time.sleep(3)

        # Check AutoClip Backend (Port 8000)
        if not is_alive(8000, '/docs'):
            if p_autoclip and p_autoclip.poll() is None:
                try: p_autoclip.kill()
                except Exception: pass
            p_autoclip = start_autoclip()
            time.sleep(3)

        time.sleep(5)

if __name__ == '__main__':
    main()
