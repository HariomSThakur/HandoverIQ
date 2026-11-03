@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  py -3 -m venv .venv
  if errorlevel 1 goto :failed
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 goto :failed
)

".venv\Scripts\python.exe" run.py
goto :eof

:failed
echo HandoverIQ could not start. Check Python installation and network access for the first dependency install.
pause
