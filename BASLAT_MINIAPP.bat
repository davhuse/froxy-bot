@echo off
chcp 65001 > nul
title KeyVadi Telegram Mini App Sunucusu
cd /d "%~dp0\miniapp"
echo ============================================================
echo   ⚡ KEYVADI TELEGRAM MINI APP SUNUCUSU BASLATILIYOR...
echo ============================================================
echo.
python server.py
pause
