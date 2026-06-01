@echo off
setlocal

cd /d "%~dp0"

net session >nul 2>&1
if not "%ERRORLEVEL%"=="0" (
    echo Solicitando permissao de administrador...
    powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b %ERRORLEVEL%
)

if not exist "%~dp0logs\windows-services" mkdir "%~dp0logs\windows-services"
set "LOG_FILE=%~dp0logs\windows-services\uninstall-latest.log"

echo Desinstalando os servicos ApiTcc e ApiTccOllama...
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0uninstall_windows_services.ps1" > "%LOG_FILE%" 2>&1
set "EXIT_CODE=%ERRORLEVEL%"

type "%LOG_FILE%"
echo.
if "%EXIT_CODE%"=="0" (
    echo Desinstalacao finalizada.
) else (
    echo A desinstalacao falhou com codigo %EXIT_CODE%.
)

echo.
pause
exit /b %EXIT_CODE%
