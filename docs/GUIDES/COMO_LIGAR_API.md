# Como iniciar a API como servico do Windows

Este guia mostra como instalar, iniciar, parar e verificar a API TCC rodando como servico do Windows.

## Pasta correta

Abra o PowerShell e entre na pasta da API:

```powershell
cd "C:\Users\aborr\Projeto TCC\YOLO26l-API\api-tcc"
```

## Instalar os servicos

Opcao mais simples: entre na pasta `api-tcc` e execute:

```powershell
.\instalar_servicos.bat
```

Ou clique duas vezes no arquivo:

```text
C:\Users\aborr\Projeto TCC\YOLO26l-API\api-tcc\instalar_servicos.bat
```

Se preferir executar direto pelo PowerShell, use o script de instalacao:

Execute o script de instalacao:

```powershell
.\install_windows_services.ps1
```

O script pede permissao de administrador automaticamente e cria dois servicos:

- `ApiTcc`: servico da API FastAPI.
- `ApiTccOllama`: servico do Ollama usado pela API.

Ao final, ele tambem tenta iniciar os dois servicos.

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
http://192.168.76.103:8080/docs
```

Ou teste a rota de saude:

```text
http://192.168.76.103:8080/healthz
```

Pelo PowerShell:

```powershell
Invoke-WebRequest -Uri "http://192.168.76.103:8080/healthz"
```

## Remover os servicos

Se precisar desinstalar, execute:

```powershell
.\desinstalar_servicos.bat
```

Ou clique duas vezes no arquivo:

```text
C:\Users\aborr\Projeto TCC\YOLO26l-API\api-tcc\desinstalar_servicos.bat
```

Se preferir executar direto pelo PowerShell:

```powershell
.\uninstall_windows_services.ps1
```

## Logs

Os logs dos servicos ficam em:

```text
C:\Users\aborr\Projeto TCC\YOLO26l-API\api-tcc\logs\windows-services
```

## Resumo rapido

```powershell
cd "C:\Users\aborr\Projeto TCC\YOLO26l-API\api-tcc"
.\install_windows_services.ps1
Get-Service -Name "ApiTcc","ApiTccOllama"
```

Se ja estiver instalado:

```powershell
Start-Service -Name ApiTccOllama
Start-Service -Name ApiTcc
Get-Service -Name "ApiTcc","ApiTccOllama"
```
