$ErrorActionPreference = "Stop"

$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
$isAdmin = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
$scriptPath = $PSCommandPath
$projectDir = Split-Path -Parent $scriptPath

if (-not $isAdmin) {
    $process = Start-Process -FilePath "powershell.exe" -ArgumentList @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", "`"$scriptPath`""
    ) -Verb RunAs -Wait -PassThru
    exit $process.ExitCode
}

Set-Location $projectDir

$binDir = Join-Path $projectDir "bin"
$configDir = Join-Path $projectDir "config\windows-services"
$logDir = Join-Path $projectDir "logs\windows-services"
$hostExe = Join-Path $binDir "ApiTccServiceHost.exe"
$source = Join-Path $projectDir "service_host\WindowsServiceHost.cs"
$python = Join-Path $projectDir ".venv\Scripts\python.exe"
$apiConfig = Join-Path $configDir "ApiTcc.svcconfig"
$ollamaConfig = Join-Path $configDir "ApiTccOllama.svcconfig"

New-Item -ItemType Directory -Force -Path $binDir, $configDir, $logDir | Out-Null

function Wait-ServiceDeleted {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name
    )

    for ($attempt = 1; $attempt -le 30; $attempt++) {
        $service = Get-Service -Name $Name -ErrorAction SilentlyContinue
        if (-not $service) {
            return
        }
        Start-Sleep -Seconds 1
    }

    throw "O servico '$Name' ainda nao foi removido pelo Windows. Tente executar o instalador novamente."
}

if (-not (Test-Path $python)) {
    throw "Python do ambiente virtual nao encontrado em: $python"
}

$csc = Join-Path $env:WINDIR "Microsoft.NET\Framework64\v4.0.30319\csc.exe"
if (-not (Test-Path $csc)) {
    throw "Compilador C# nao encontrado em: $csc"
}

& $csc /nologo /target:exe /out:"$hostExe" /reference:System.ServiceProcess.dll "$source"

$hostValue = "0.0.0.0"
$portValue = "8080"
$envPath = Join-Path $projectDir ".env"
if (Test-Path $envPath) {
    foreach ($line in Get-Content $envPath) {
        if ($line -match "^HOST=(.+)$") { $hostValue = $Matches[1].Trim(" `"'") }
        if ($line -match "^PORT=(.+)$") { $portValue = $Matches[1].Trim(" `"'") }
    }
}

$cpuWorkers = [Math]::Max(2, [Environment]::ProcessorCount / 2)
$apiArgs = "-m uvicorn main:app --host $hostValue --port $portValue --workers $cpuWorkers --log-level info"

@"
Executable=$python
Arguments=$apiArgs
WorkingDirectory=$projectDir
LogDirectory=$logDir
Env.PYTHONUTF8=1
Env.PYTHONPATH=$projectDir
Env.DEBUG=False
Env.OLLAMA_HOST=http://127.0.0.1:11434
"@ | Set-Content -Path $apiConfig -Encoding UTF8

$ollamaExe = (Get-Command "ollama.exe" -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty Source)
if (-not $ollamaExe) {
    $ollamaExe = Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama.exe"
}
if (-not (Test-Path $ollamaExe)) {
    throw "Ollama nao encontrado. Instale o Ollama ou ajuste o caminho no script."
}

$ollamaModels = Join-Path $env:USERPROFILE ".ollama\models"

@"
Executable=$ollamaExe
Arguments=serve
WorkingDirectory=$projectDir
LogDirectory=$logDir
Env.OLLAMA_HOST=0.0.0.0:11434
Env.OLLAMA_MODELS=$ollamaModels
"@ | Set-Content -Path $ollamaConfig -Encoding UTF8

foreach ($serviceName in @("ApiTcc", "ApiTccOllama")) {
    $existing = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
    if ($existing) {
        Stop-Service -Name $serviceName -ErrorAction SilentlyContinue
        $output = & sc.exe delete $serviceName 2>&1
        $output | ForEach-Object { Write-Host $_ }
        if ($LASTEXITCODE -ne 0) {
            throw "sc.exe delete $serviceName falhou com codigo $LASTEXITCODE."
        }
        Wait-ServiceDeleted -Name $serviceName
    }
}

$ollamaBinPath = "`"$hostExe`" `"ApiTccOllama`" `"$ollamaConfig`""
$apiBinPath = "`"$hostExe`" `"ApiTcc`" `"$apiConfig`""

New-Service -Name "ApiTccOllama" -BinaryPathName $ollamaBinPath -StartupType Automatic -DisplayName "API TCC Ollama" | Out-Null
New-Service -Name "ApiTcc" -BinaryPathName $apiBinPath -StartupType Automatic -DisplayName "API TCC" | Out-Null

Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Services\ApiTccOllama" -Name Description -Value "Servidor Ollama local para a API TCC na porta 11434."
Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Services\ApiTcc" -Name Description -Value "API FastAPI do projeto TCC."

Get-Service -Name "ApiTcc","ApiTccOllama" | Out-Null

Start-Service -Name ApiTccOllama
Start-Sleep -Seconds 3
Start-Service -Name ApiTcc
Start-Sleep -Seconds 5

Get-Service -Name "ApiTcc","ApiTccOllama" | Format-Table -AutoSize Name, Status, StartType
