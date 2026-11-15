@echo off
title Qanooni AI API (close this window to stop the server)
cd /d "%~dp0"

where python >nul 2>&1
if errorlevel 1 (
    echo Python was not found. Install Python 3.12 from https://www.python.org/downloads/
    echo and tick "Add python.exe to PATH" in the installer, then run this file again.
    pause
    exit /b 1
)

if not exist ".env" (
    echo The .env file is missing. Put the .env file you were sent in this folder:
    echo %~dp0
    echo ^(.env.example shows which values it needs^)
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo First run: setting things up, this takes a few minutes...
    python -m venv .venv
    if errorlevel 1 ( echo Could not create the virtual environment. & pause & exit /b 1 )
)

".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q -r requirements.txt
if errorlevel 1 ( echo Installing packages failed. Check your internet connection. & pause & exit /b 1 )

echo.
echo Starting the server at http://127.0.0.1:8000/docs
echo Keep this window open. Close it to stop the server.
echo.

start "" /b powershell -NoProfile -Command "Start-Sleep -Seconds 5; Start-Process 'http://127.0.0.1:8000/docs'"
".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000

echo.
echo The server stopped. See the messages above for the reason.
pause
