# 📁 Estrutura do Projeto TCC — Detecção de Cadeiras

## 🆕 Atualizacao Recente (2026-04-08)

- Mensagem personalizada no retorno da analise com LLM local (Ollama + qwen2.5-coder:7b)
- Novos campos na resposta da deteccao: `personalized_message`, `analysis_model_used`, `llm_model_used`
- Hardening de seguranca em autenticacao e validacao de `model_name`
- `.gitignore` bloqueando arquivos de imagem/video globalmente
- `requirements.txt` revisado e script cross-platform de setup: `api-tcc/setup_env.py`
- Testes executados: `pytest` (10 passed), `pip-audit` (sem CVEs conhecidas), `bandit` (sem findings pendentes)

## 🎯 Visão Geral

Projeto de **Detecção de Objetos (Cadeiras) com YOLO11 + OpenVINO** em FastAPI, com suporte a **Intel Arc B570**.

```
Projeto TCC/
├── 📚 DOCUMENTAÇÃO (docs/)
├── 🔧 FERRAMENTAS (tools/)
├── 📊 DADOS (data/)
├── 🤖 MODELOS (models/)
├── 🐍 SCRIPTS (scripts/)
├── 🚀 API (api-tcc/)
└── 📦 DOWNLOADS (downloads/)
```

---

## 📂 Estrutura Completa

### 📚 `docs/` — Documentação

```
docs/
├── GUIDES/                          # Guias e tutoriais
│   ├── MODELOS.md                   # Documentação de modelos disponíveis
│   ├── ESTRUTURA.md                 # Estrutura geral do projeto
│   ├── COMO_LIGAR_API.md            # Tutorial para rodar a API
│   ├── AUTH_GOOGLE.md               # Autenticação Google/Firebase
│   ├── ARQUIVOS_ANALISADOS.md       # Arquivos processados
│   ├── MUDANCAS.md                  # Histórico de mudanças
│   └── SOLUCAO.md                   # Solução final
│
├── API/                             # Documentação de API
│   └── CONTRATO_API.md              # Contrato geral: endpoints, models, exemplos
│
├── SETUP/                           # Guias de configuração
│   └── FIRESTORE.md                 # Setup do Firebase/Firestore
│
└── REPORTS/                         # Relatórios técnicos
    ├── TECNICO_IMPLEMENTACAO.md     # Relatório de implementação
    └── CLASS_MAPPING.md             # Mapeamento de classes
```

### 🔧 `tools/` — Utilitários & Scripts de Diagnóstico

```
tools/
├── check_firestore_api.py           # Verifica conexão Firestore
├── debug_firestore.py               # Debug de Firestore
├── test_firestore_connection.py     # Testa conexão
└── verify_firestore_created.py      # Verifica se DB foi criado
```

### 📊 `data/` — Datasets

```
data/
├── content/
│   └── custom_data/                 # Dataset principal (Roboflow)
│       ├── data.yaml                # Config do dataset
│       ├── train/
│       │   ├── images/
│       │   └── labels/
│       ├── valid/
│       │   ├── images/
│       │   └── labels/
│       └── test/
│           ├── images/
│           └── labels/
│
├── runs/                            # Resultados de inferência
│   └── detect/
│
└── training_artifacts/              # Dados de treino
    ├── uploads/ { images/, videos/ }
    └── video_frames/
```

### 🤖 `models/` — Modelos Treinados

```
models/
├── chair/                           # Modelo padrão (cadeiras)
│   ├── my_model.pt                  # Weights PyTorch
│   ├── my_model_openvino_model/     # IR (Intermediate Representation)
│   │   ├── openvino_model.xml
│   │   ├── openvino_model.bin
│   │   └── ...
│   └── config.yaml
│
├── garrafa_de_vidro/                # Novo modelo (exemplo)
│   ├── my_model.pt
│   ├── my_model_openvino_model/
│   └── config.yaml
│
├── 0_kursi_chair_door.../           # Modelo anterior (arquivo)
│   ├── my_model.pt
│   └── classes.txt
│
└── yolo26l.pt                       # Base model (não treinado)
```

### 🐍 `scripts/` — Scripts de Treinamento & Testes

```
scripts/
├── train_new_model.py               # ⭐ PRINCIPAL: treina + exporta OpenVINO
├── install_arc_deps.ps1             # Instala PyTorch + IPEX para Arc B570
│
├── test_api_*.py                    # Testes da API
│   ├── test_api_full.py
│   ├── test_api_upload.py
│   ├── test_api_with_downloads.py
│   └── ...
│
├── test_detection_*.py              # Testes de detecção
│   ├── test_detection_simple.py
│   ├── test_detection_detailed.py
│   ├── test_detection_debug.py
│   └── ...
│
├── test_auth_google.py              # Testes de autenticação
├── exemplos_api_completo.py         # Exemplos de uso
├── organize_models.py               # Utilitário para organizar modelos
└── main.py                          # (depreciado)
```

### 🚀 `api-tcc/` — Backend FastAPI

```
api-tcc/
├── main.py                          # Ponto de entrada
├── requirements.txt                 # Dependências
│
├── app/
│   ├── __init__.py
│   │
│   ├── core/                        # Configuração & Integrações
│   │   ├── firebase.py              # ✓ Auth Firebase + Exceções token
│   │   └── config.py
│   │
│   ├── models/                      # Pydantic models (schemas)
│   │   ├── auth.py
│   │   ├── detection.py
│   │   └── error_report.py          # ✓ Novo: erro mobile
│   │
│   ├── routes/                      # Endpoints
│   │   ├── auth_routes.py
│   │   ├── detection_routes.py      # ✓ Tratamento 401/500
│   │   ├── error_routes.py          # ✓ Novo: POST /errors/report
│   │   └── system_routes.py
│   │
│   └── services/
│       └── detection_service.py     # Lógica de detecção
│
└── config/
    └── settings.py                  # Variáveis de ambiente
```

### 📦 `downloads/` — Arquivos Zip

```
downloads/
├── data.zip                         # Dataset backup
└── my_model.zip                     # Modelo backup
```

### 📋 `runs/experiments/` — Logs de Experimentos

```
runs/experiments/
└── (future train logs aqui)
```

### 📝 `logs/` — Logs de Runtime (criada automaticamente)

```
logs/
└── errors/
    └── {username}/
        ├── 2026-03-29.log
        ├── 2026-03-30.log
        └── ...
```

---

## 🚀 Como Usar

### 1️⃣ **Iniciar a API**

```bash
cd api-tcc
python main.py
```

API em: `http://192.168.76.200:8000`  
Swagger: `http://192.168.76.200:8000/docs`

### 2️⃣ **Treinar Novo Modelo**

```bash
# Com Arc B570 (recomendado)
python scripts/train_new_model.py --model yolo11s.pt --epochs 100 --batch 8 --name novo_modelo --device xpu --half

# Ou apenas CPU
python scripts/train_new_model.py --model yolo11s.pt --epochs 100 --batch 8 --name novo_modelo
```

Modelo será salvo em: `models/novo_modelo/`

### 3️⃣ **Testar Detecção**

```bash
python scripts/test_detection_simple.py
```

### 4️⃣ **Verificar Logs de Erros**

```bash
# Ver erros do usuário joao@gmail.com em 29/03
cat logs/errors/joao@gmail.com/2026-03-29.log
```

---

## 📊 Endpoints Principais

| Endpoint | Método | Auth | Descrição |
|----------|--------|------|-----------|
| `/auth/google` | POST | ✗ | Login/cadastro |
| `/detection/analyze` | POST | ✓ | Detecção com token |
| `/detection/analyze-test` | POST | ✗ | Teste local |
| `/errors/report` | POST | ✗ | Receber erro mobile |

Detalhes completos em: [docs/API/CONTRATO_API.md](docs/API/CONTRATO_API.md)

---

## 🔧 Instalação de Dependências

### Setup Básico
```bash
pip install -r api-tcc/requirements.txt
```

### Setup Recomendado (Windows/Linux/macOS)
```bash
cd api-tcc
python setup_env.py
```

Opcoes uteis:
```bash
python setup_env.py --venv .venv
python setup_env.py --skip-venv
python setup_env.py --requirements requirements.txt
```

### Com Intel Arc B570 (XPU)
```powershell
# Executar como admin
.\scripts\install_arc_deps.ps1
```

---

## 📚 Documentação Rápida

| Documento | Resumo |
|-----------|--------|
| [docs/API/CONTRATO_API.md](docs/API/CONTRATO_API.md) | **Contrato da API** — endpoints, modelos, exemplos |
| [docs/REPORTS/TECNICO_IMPLEMENTACAO.md](docs/REPORTS/TECNICO_IMPLEMENTACAO.md) | **Relatório técnico** — tudo que foi implementado |
| [docs/GUIDES/ESTRUTURA.md](docs/GUIDES/ESTRUTURA.md) | Visão geral da arquitetura |
| [docs/GUIDES/COMO_LIGAR_API.md](docs/GUIDES/COMO_LIGAR_API.md) | Passo a passo para rodar a API |
| [docs/SETUP/FIRESTORE.md](docs/SETUP/FIRESTORE.md) | Setup do Firebase/Firestore |

---

## 📌 Checklist Rápido

- ✅ API rodando em `192.168.76.200:8000`
- ✅ Modelos em `models/`
- ✅ Dataset em `data/content/custom_data/`
- ✅ Logs de erro em `logs/errors/`
- ✅ Scripts de treino organizados
- ✅ Documentação centralizada em `docs/`

---

## 🔗 Links Importantes

- **API Swagger:** http://192.168.76.200:8000/docs
- **System Status:** http://192.168.76.200:8000/system/status
- **Logs Locais:** `./logs/errors/`

---

**Última atualização:** 2026-03-29  
**Versão:** 1.0  
**Status:** ✅ Produção
