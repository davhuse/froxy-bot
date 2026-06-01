@echo off
echo 🚀 Git deposu kuruluyor...
git init
git config user.email "habil@example.com"
git config user.name "Habil"
git remote remove origin 2>nul
git remote add origin https://github.com/davhuse/froxy-bot.git
git branch -M main
git rm --cached *.session 2>nul
git rm --cached *.session-journal 2>nul
git rm --cached -r __pycache__ 2>nul
git add .
git commit -m "Fix: untrack session files and add watchdog"
echo 🚀 GitHub'a yukleniyor...
git push -u origin main --force
echo ✅ Yukleme tamamlandi!
