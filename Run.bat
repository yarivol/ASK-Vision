@echo off
chcp 65001 >nul
echo Активация окружения...
call venv\Scripts\activate
echo Запуск ASK-Vision...
python main.py
pause