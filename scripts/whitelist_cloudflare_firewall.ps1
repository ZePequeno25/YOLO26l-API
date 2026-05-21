$ErrorActionPreference = "Stop"

Write-Host "Baixando lista de IPs do Cloudflare (IPv4 e IPv6)..." -ForegroundColor Cyan

$ipv4 = Invoke-RestMethod -Uri "https://www.cloudflare.com/ips-v4"
$ipv6 = Invoke-RestMethod -Uri "https://www.cloudflare.com/ips-v6"

$allIps = ($ipv4 -split "`n" | Where-Object { $_ -match "\S" }) + ($ipv6 -split "`n" | Where-Object { $_ -match "\S" })
$ipList = $allIps -join ","

$ruleName = "Allow Cloudflare (HTTP/HTTPS)"

Write-Host "Removendo regra antiga do firewall (se existir)..." -ForegroundColor Yellow
$existingRule = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
if ($existingRule) {
    Remove-NetFirewallRule -DisplayName $ruleName
}

Write-Host "Adicionando IPs do Cloudflare ao Firewall do Windows (Portas 80 e 443)..." -ForegroundColor Green
New-NetFirewallRule -DisplayName $ruleName `
    -Direction Inbound `
    -Action Allow `
    -Protocol TCP `
    -LocalPort 80, 443 `
    -RemoteAddress $allIps `
    -Description "Permite tráfego das portas 80 e 443 apenas para a rede do Cloudflare"

Write-Host "Concluído com sucesso! Tráfego da Cloudflare liberado." -ForegroundColor Green
