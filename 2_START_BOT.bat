@echo off
chcp 65001 > nul
cd /d "%~dp0"
echo =======================================================
echo  ЗАПУСК KUFAR SNIPER & NEGOTIATOR
echo =======================================================
echo.
python main.py
pause
