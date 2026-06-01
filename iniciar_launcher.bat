@echo off
setlocal

cd /d "%~dp0"

where py >nul 2>&1
if "%ERRORLEVEL%"=="0" (
    py -3 launcher.py
    exit /b %ERRORLEVEL%
)

where python >nul 2>&1
if "%ERRORLEVEL%"=="0" (
    python launcher.py
    exit /b %ERRORLEVEL%
)

echo Python 3 nao encontrado. Instale o Python 3 e execute novamente.
pause
exit /b 1
