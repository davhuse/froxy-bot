@echo off
echo 🚀 Git deposu kuruluyor...
git init
git config user.email "habil@example.com"
git config user.name "Habil"
git remote remove origin 2>nul
git remote add origin https://github.com/davhuse/froxy-bot.git
git branch -M main
git add .
git commit -m "Update with StringSession and absolute template paths"
echo 🚀 GitHub'a yukleniyor...
git push -u origin main --force
echo ✅ Yukleme tamamlandi!
