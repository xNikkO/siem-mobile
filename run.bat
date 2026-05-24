@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" run.py %*
) else (
    python run.py %*
)
if errorlevel 1 py -3 run.py %*
exit /b %ERRORLEVEL%
