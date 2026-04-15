# 📁 Estrutura do Projeto TCC — Detecção de Cadeiras

## 🆕 Atualização Recente (2026-04-12)

- **Rota de feedback** (`POST /feedback`) com cooldown de 5 dias e limite de 1000 caracteres
- **Codec H.264** (`avc1`) nos vídeos gerados — compatível com Android (antes: `mp4v` causava falha de reprodução)
- **`openh264-1.8.0-win64.dll`** instalado em `api-tcc/` para suporte ao encoding H.264 pelo OpenCV
- **Mime-type correto** no download: `mimetypes.guess_type()` substitui `application/octet-stream` hardcoded
- **Múltiplos workers Uvicorn** em produção: `max(2, cpu_count // 2)` — processamento paralelo de usuários
- **Hot reload** agora é mutuamente exclusivo com workers (fix para crash no Windows com `reload=True + workers>1`)
- **Limite de duração de vídeo**: 30 segundos via `MAX_VIDEO_DURATION_SECONDS`
- **Stride de inferência**: `VIDEO_INFERENCE_STRIDE=2` para reduzir timeouts HTTP 524 do Cloudflare
- **Firebase**: mensagens internas não são mais expostas ao cliente em erros de token
- **Erros de validação** (`ValueError`) retornam HTTP 422 com mensagem amigável gerada pelo Ollama
- **2.344 arquivos de treino** coletados em `training_artifacts/`

### Histórico de Atualizações Anteriores

**2026-04-10 (Segurança Completa + Otimizações):**
- JWT dupla-camada: Firebase ID token → API JWT Bearer (via `POST /auth/token`)
- Rate limiting em `/auth`: 5 req/60s; bloqueio 300s
- 404 Guard Middleware: detecta scanning de rotas, bloqueia após 10×404 em 60s
- YOLO `stream=True` para vídeos longos sem acúmulo de RAM
- Prompt Ollama restritivo + 20 filtros regex

**2026-04-08 (LLM local + segurança):**
- Mensagem personalizada com Ollama (`qwen2.5-coder:7b`)
- Hardening de autenticação e validação de `model_name`
- Testes: `pytest` (10 passed), `pip-audit` (sem CVEs), `bandit` (sem findings)

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
├── main.py                          # Ponto de entrada (workers/reload)
├── requirements.txt                 # Dependências
├── openh264-1.8.0-win64.dll         # DLL H.264 para OpenCV (Windows)
│
├── app/
│   ├── __init__.py
│   │
│   ├── core/                        # Configuração & Integrações
│   │   ├── firebase.py              # ✓ Auth Firebase + JWT dupla-camada
│   │   ├── rate_limiter.py          # ✓ Sliding window rate limiter
│   │   ├── not_found_guard.py       # ✓ 404 scan detection middleware
│   │   └── config.py
│   │
│   ├── models/                      # Pydantic models (schemas)
│   │   ├── auth.py
│   │   ├── detection.py
│   │   ├── error_report.py          # ✓ Erros mobile
│   │   └── feedback_report.py       # ✓ Novo: feedback mobile
│   │
│   ├── routes/                      # Endpoints
│   │   ├── auth_routes.py           # /auth/google, /auth/token
│   │   ├── detection_routes.py      # ✓ mime-type, 422, Ollama errors
│   │   ├── error_routes.py          # POST /errors/report
│   │   ├── feedback_routes.py       # ✓ Novo: POST /feedback
│   │   └── system_routes.py
│   │
│   └── services/
│       ├── detection_service.py     # ✓ H.264, vid_stride, duração 30s
│       └── ollama_message_service.py # ✓ generate_error_message()
│
└── config/
    └── settings.py                  # ✓ MAX_VIDEO_DURATION_SECONDS, VIDEO_INFERENCE_STRIDE
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
├── errors/
│   └── {username}/
│       ├── 2026-03-29.log
│       └── ...
└── feedback/
    └── {username}/
        ├── 2026-04-11.log
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
| `/auth/google` | POST | ✗ | Login/cadastro no Firestore |
| `/auth/token` | POST | ✗ | Troca Firebase token por API JWT |
| `/detection/analyze` | POST | ✓ | Detecção de imagem/vídeo |
| `/detection/download/{filename}` | GET | ✓ | Download de arquivo analisado |
| `/errors/report` | POST | ✗ | Receber erro do app mobile |
| `/feedback` | POST | ✗ | Receber feedback (cooldown 5 dias) |

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
| [docs/API/FEEDBACK_ROUTE.md](docs/API/FEEDBACK_ROUTE.md) | **Rota de feedback** — contrato completo |
| [docs/REPORTS/TECNICO_IMPLEMENTACAO.md](docs/REPORTS/TECNICO_IMPLEMENTACAO.md) | **Relatório técnico** — tudo que foi implementado |
| [docs/GUIDES/ESTRUTURA.md](docs/GUIDES/ESTRUTURA.md) | Visão geral da arquitetura |
| [docs/GUIDES/COMO_LIGAR_API.md](docs/GUIDES/COMO_LIGAR_API.md) | Passo a passo para rodar a API |
| [docs/SETUP/FIRESTORE.md](docs/SETUP/FIRESTORE.md) | Setup do Firebase/Firestore |

---

## 📌 Checklist Rápido

- ✅ API em `https://kelvin-tech-api.online` (porta 8080, Cloudflare)
- ✅ Múltiplos workers ativos (`DEBUG=False` → `max(2, cpu_count//2)`)
- ✅ Vídeos retornados em H.264 (compatível com Android)
- ✅ Rota `/feedback` com cooldown de 5 dias
- ✅ JWT dupla-camada (Firebase → API Bearer token)
- ✅ Rate limiting e 404 Guard ativos
- ✅ Modelos em `models/`
- ✅ 2.344 arquivos de treino em `training_artifacts/`
- ✅ Logs de erro em `logs/errors/` e feedback em `logs/feedback/`
- ✅ Documentação centralizada em `docs/`

---

## 🔗 Links Importantes

- **API Swagger:** https://kelvin-tech-api.online/docs
- **System Status:** https://kelvin-tech-api.online/system/status
- **Logs Locais:** `api-tcc/logs/`

---

**Última atualização:** 2026-04-12  
**Versão:** 1.3  
**Status:** ✅ Produção
