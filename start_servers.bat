@echo off
title CutRoom Studio Servers
cd /d "%~dp0"
echo Starting CutRoom Studio and AutoClip servers...
python run_servers.py
pause
