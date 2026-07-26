@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================================
echo  KeyVadi Reklam Hesabi - Yeni Oturum Anahtari
echo ============================================================
echo.
set /p PHONE="Telefon numarasi (Enter = +13869914668): "
if "%PHONE%"=="" set PHONE=+13869914668
echo.
python keyvadi_oturum_yenile.py %PHONE%
echo.
echo ============================================================
echo  Yukaridaki anahtari kopyalayin:
echo    Render ^> froxy-bot ^> Environment
echo    AD_STRING_SESSION_KEYVADI = (anahtar)
echo    Save changes
echo ============================================================
echo.
pause
