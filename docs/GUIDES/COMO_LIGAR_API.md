# Como iniciar a API como servico do Windows

Este guia mostra como instalar, iniciar, parar e verificar a API TCC rodando como servico do Windows.

## Pre-requisitos da maquina

- Windows com PowerShell.
- Python 3 instalado e disponivel como `py` ou `python`.
- Ollama instalado, se quiser usar mensagens personalizadas.
- Permissao de administrador para criar servicos e liberar a porta `8080` no Firewall.

O instalador cria a `.venv` automaticamente se ela ainda nao existir.

## Pasta correta

Abra o PowerShell na pasta onde o projeto foi copiado e entre na pasta da API:

```powershell
cd .\api-tcc
```

Se voce abriu o PowerShell direto na pasta `api-tcc`, nao precisa executar o `cd`.

## Instalar os servicos

Opcao mais simples: entre na pasta `api-tcc` e execute:

```powershell
.\instalar_servicos.bat
```

Ou clique duas vezes no arquivo:

```text
api-tcc\instalar_servicos.bat
```

Se preferir executar direto pelo PowerShell, use o script de instalacao:

Execute o script de instalacao:

```powershell
.\install_windows_services.ps1
```

O script pede permissao de administrador automaticamente e cria dois servicos:

- `ApiTcc`: servico da API FastAPI.
- `ApiTccOllama`: servico do Ollama usado pela API.

Ao final, ele tambem tenta iniciar os dois servicos e liberar a porta `8080` no Firewall do Windows.

## Verificar se os servicos estao rodando

```powershell
Get-Service -Name "ApiTcc","ApiTccOllama"
```

O esperado e aparecer `Running` na coluna `Status`.

## Iniciar os servicos manualmente

Se os servicos ja estiverem instalados, inicie com:

```powershell
Start-Service -Name ApiTccOllama
Start-Service -Name ApiTcc
```

Inicie o `ApiTccOllama` primeiro, porque a API pode depender dele para gerar mensagens personalizadas.

## Parar os servicos

```powershell
Stop-Service -Name ApiTcc
Stop-Service -Name ApiTccOllama
```

## Reiniciar os servicos

```powershell
Restart-Service -Name ApiTccOllama
Restart-Service -Name ApiTcc
```

## Testar a API

Depois que o servico `ApiTcc` estiver `Running`, teste no navegador:

```text
http://localhost:8080/docs
```

Ou teste a rota de saude:

```text
http://localhost:8080/healthz
```

Pelo PowerShell:

```powershell
Invoke-WebRequest -Uri "http://localhost:8080/healthz"
```

Para acessar de outro aparelho na mesma rede, descubra o IP da maquina que esta rodando a API:

```powershell
Get-NetIPAddress -AddressFamily IPv4 |
  Where-Object { $_.IPAddress -notlike "127.*" -and $_.PrefixOrigin -ne "WellKnown" } |
  Select-Object IPAddress
```

Depois use:

```text
http://IP_DA_MAQUINA:8080/docs
```

Exemplo:

```text
http://192.168.1.50:8080/docs
```

## Remover os servicos

Se precisar desinstalar, execute:

```powershell
.\desinstalar_servicos.bat
```

Ou clique duas vezes no arquivo:

```text
api-tcc\desinstalar_servicos.bat
```

Se preferir executar direto pelo PowerShell:

```powershell
.\uninstall_windows_services.ps1
```

## Logs

Os logs dos servicos ficam em:

```text
api-tcc\logs\windows-services
```

## Resumo rapido

```powershell
cd .\api-tcc
.\install_windows_services.ps1
Get-Service -Name "ApiTcc","ApiTccOllama"
```

Se ja estiver instalado:

```powershell
Start-Service -Name ApiTccOllama
Start-Service -Name ApiTcc
Get-Service -Name "ApiTcc","ApiTccOllama"
```
