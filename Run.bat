@echo off
rem Starts the cheat panel without a console window.
where pythonw >nul 2>nul
if errorlevel 1 (
  echo Python 3.10 or newer is required: https://www.python.org/downloads/
  echo Tick "Add python.exe to PATH" during installation, then run this again.
  pause
  exit /b 1
)
start "" pythonw "%~dp0app.py"
