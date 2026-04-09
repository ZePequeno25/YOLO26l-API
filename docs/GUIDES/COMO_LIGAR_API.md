# Como ligar a API

## Onde executar

Entre primeiro na pasta `api-tcc`.

Isso e importante porque a API carrega o arquivo `firebase-service-account.json` por caminho relativo.

```powershell
cd "C:\Users\aborr\Projeto TCC\api-tcc"
```

## Instalar dependencias

Se ainda nao instalou as bibliotecas:

```powershell
python -m pip install -r requirements.txt
```

## Subir a API

Comando mais simples:

```powershell
python main.py
```

Se estiver tudo certo, a API sobe em:

- `http://localhost:8000`
- `http://localhost:8000/docs`

## Teste rapido

Abra no navegador:

```text
http://localhost:8000/system/status
```

Ou rode no PowerShell:

```powershell
Invoke-WebRequest -Uri "http://localhost:8000/system/status"
```

## Parar a API

No terminal onde a API estiver rodando:

```text
Ctrl + C
```

## Resumo rapido

```powershell
cd "C:\Users\aborr\Projeto TCC\api-tcc"
python -m pip install -r requirements.txt
python main.py
```

## Observacao importante

Se voce tentar rodar `api-tcc/main.py` a partir da pasta raiz do projeto, a inicializacao pode falhar por causa do arquivo do Firebase. O caminho seguro e sempre abrir o terminal dentro de `api-tcc` e executar dali.
