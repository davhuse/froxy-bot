@echo off
title LISANSARENA MINI APP SUNUCUSU (v6.0)
chcp 65001 > nul
cls
echo ============================================================
echo   LISANSARENA TELEGRAM MINI APP BASLATILIYOR...
echo ============================================================
cd /d "%~dp0\miniapp_lisansarena"
python server.py
pause
