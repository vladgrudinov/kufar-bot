@echo off
chcp 65001 > nul
cd /d "%~dp0"
echo =======================================================
echo  ВХОД В АККАУНТ KUFAR.BY ДЛЯ АВТОМАТИЗАЦИИ СООБЩЕНИЙ
echo =======================================================
echo.
python interactive_login.py
pause
