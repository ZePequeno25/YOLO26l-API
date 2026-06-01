$ErrorActionPreference = "Stop"

$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
$isAdmin = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
$scriptPath = $PSCommandPath

if (-not $isAdmin) {
    Start-Process -FilePath "powershell.exe" -ArgumentList @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", "`"$scriptPath`""
    ) -Verb RunAs -Wait
    exit $LASTEXITCODE
}

foreach ($serviceName in @("ApiTcc", "ApiTccOllama")) {
    $existing = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
    if ($existing) {
        Stop-Service -Name $serviceName -ErrorAction SilentlyContinue
        sc.exe delete $serviceName | Out-Null
    }
}

Write-Host "Servicos removidos."
