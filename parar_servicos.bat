@echo off
setlocal

cd /d "%~dp0"

net session >nul 2>&1
if not "%ERRORLEVEL%"=="0" (
    echo Solicitando permissao de administrador...
    powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b %ERRORLEVEL%
)

echo Parando os servicos ApiTcc e ApiTccOllama...
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Stop-Service -Name ApiTcc -ErrorAction SilentlyContinue; Stop-Service -Name ApiTccOllama -ErrorAction SilentlyContinue"
set "EXIT_CODE=%ERRORLEVEL%"

if "%EXIT_CODE%"=="0" (
    echo Servicos parados com sucesso.
) else (
    echo Falha ao parar os servicos ou eles ja estao parados.
)

echo.
pause
exit /b %EXIT_CODE%
