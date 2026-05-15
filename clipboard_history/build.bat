@echo off
chcp 65001 >nul
pyinstaller --onefile --windowed --name "剪贴板历史悬浮窗" main.py
echo 打包完成，输出在 dist 目录。
pause
