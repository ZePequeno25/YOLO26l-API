# 🚀 Como Executar a API Manualmente (Sem Serviço do Windows)

Este guia documenta o método para configurar e executar a API manualmente em modo console (foreground), o que é ideal para desenvolvimento, testes e resolução de problemas (debug) quando os serviços do Windows apresentam erros.

Ele também descreve como resolver conflitos de versão do Python (como a incompatibilidade do PyTorch com o Python 3.14).

---

## 🔍 Por que usar este método?

* **Logs em Tempo Real**: Veja todas as requisições, erros e saídas do console instantaneamente.
* **Isolamento de Erros**: Evita falhas de permissão ao tentar escrever arquivos do sistema.
* **Hot-Reload**: Permite iniciar a API de forma que ela se reinicie sozinha ao editar arquivos de código.

---

## 🛠️ Resolução de Conflitos: Python 3.14 vs Python 3.12

O PyTorch e o YOLO **não possuem compatibilidade oficial com o Python 3.14** (que é uma versão experimental/pré-lançamento). Se o seu sistema estiver configurado para usar o Python 3.14 por padrão, você enfrentará erros de carregamento de DLL (`torch_python.dll`) e erros de permissão de escrita ao tentar copiar a DLL do `openh264`.

A solução consiste em forçar a criação da `.venv` utilizando o **Python 3.12** (versão estável instalada na máquina).

---

## 📝 Passo a Passo: Configuração e Execução

Execute os passos a seguir utilizando o **PowerShell**:

### 1. Preparar a Pasta e Limpar o Ambiente Antigo
Navegue para a pasta da API e remova o ambiente virtual anterior (`.venv`) que possa ter sido criado com a versão errada do Python:

```powershell
# Acesse o diretório da API
cd "c:\Users\aborr\Projeto TCC\YOLO26l-API\api-tcc"

# Delete a pasta do ambiente virtual antigo se ela existir
Remove-Item -Recurse -Force .venv
```

### 2. Criar a `.venv` com o Python 3.12
Force a criação do ambiente virtual apontando para o executável do Python 3.12:

```powershell
& "C:\Users\aborr\AppData\Local\Programs\Python\Python312\python.exe" -m venv .venv
```

### 3. Instalar Dependências e Ferramentas de Build
Atualize as ferramentas do `pip` e instale as dependências listadas no `requirements.txt`:

```powershell
# Atualizar pip, setuptools e wheel
.\.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel

# Instalar os pacotes necessários
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 4. Executar a API

Você pode iniciar a API de duas formas no terminal:

#### **Método A: Execução Direta (Sem ativação)**
Inicia a API diretamente chamando o interpretador do ambiente virtual recém-criado:

```powershell
.\.venv\Scripts\python.exe main.py
```

#### **Método B: Ativando a `.venv` no PowerShell**
> [!IMPORTANT]
> No PowerShell, você **deve** usar o script `.ps1` para ativar. Executar o arquivo `.bat` não alterará o ambiente do PowerShell ativo.

```powershell
# Ativa o ambiente virtual
.\.venv\Scripts\Activate.ps1

# Inicia a API
python main.py
```

#### **Método C: Execução com Hot-Reload (Desenvolvimento)**
Caso queira modificar o código e testar imediatamente sem precisar reiniciar o terminal a cada salvamento:

```powershell
# Com o ambiente virtual já ativado
uvicorn main:app --host 0.0.0.0 --port 8080 --reload
```

---

## ❓ Diagnóstico de Problemas Comuns

### 1. Erro `Permission denied: 'C:\\Python314\\openh264-1.8.0-win64.dll'`
* **Causa**: O script foi executado usando o interpretador global do sistema fora do ambiente virtual `.venv`, e tentou colar a DLL do `openh264` em uma pasta de sistema protegida pelo Windows.
* **Solução**: Certifique-se de ativar a `.venv` (Método B) ou rodar chamando o executável local (Método A).

### 2. Falha de carregamento do `torch_python.dll` ou dependências
* **Causa**: Incompatibilidade binária causada pela execução sob a versão do Python 3.14.
* **Solução**: Refazer os passos do guia para garantir que a `.venv` utilize o Python 3.12.

---

## 📊 Onde ficam os Logs?

Quando rodamos a API de forma manual, a gravação dos logs muda em relação ao modo Serviço do Windows:

### 1. Logs de Console (Standard Output / Uvicorn)
* **Execução manual normal**: As saídas são exibidas **apenas na tela do terminal** (não salvam em arquivo automaticamente).
* **Como salvar em arquivo automaticamente (Recomendado)**: Criamos um script chamado `run_api.py` que inicia a API e grava os logs automaticamente em UTF-8 (evitando problemas de codificação no Windows). Basta executar:
  ```powershell
  .\.venv\Scripts\python.exe run_api.py
  ```
  *(Os logs do console da API manual ficarão gravados diretamente em UTF-8 em `api-tcc/logs/api_manual.log`)*

### 2. Logs Automáticos da Aplicação (Pastas de logs)
Mesmo rodando manualmente, a API continuará salvando automaticamente os seguintes logs na pasta `api-tcc/logs/`:
* 📁 `logs/errors/`: Relatórios de erros reportados pelo app mobile (ex: `logs/errors/{username}/{YYYY-MM-DD}.log`).
* 📁 `logs/security/`: IPs banidos ou bloqueios por comportamento suspeito.
* 📁 `logs/metrics/`: Dados e estatísticas de uso.

*(Os logs do modo serviço do Windows continuam salvos separadamente em `logs/windows-services/`)*

