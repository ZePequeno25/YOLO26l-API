# 🗂️ ÍNDICE DE NAVEGAÇÃO RÁPIDA

## 🚀 Comece Aqui

- 📖 **[README.md](README.md)** — Visão geral do projeto
- 📋 **[.PROJECT_TREE.txt](.PROJECT_TREE.txt)** — Árvore completa de diretórios
- 📚 **[docs/API/CONTRATO_API.md](docs/API/CONTRATO_API.md)** — Endpoints da API

---

## 📚 Documentação (docs/)

### Guias & Tutoriais
- [docs/GUIDES/MODELOS.md](docs/GUIDES/MODELOS.md) — Documentação dos modelos
- [docs/GUIDES/ESTRUTURA.md](docs/GUIDES/ESTRUTURA.md) — Arquitetura do projeto
- [docs/GUIDES/COMO_LIGAR_API.md](docs/GUIDES/COMO_LIGAR_API.md) — Iniciar a API
- [docs/GUIDES/AUTH_GOOGLE.md](docs/GUIDES/AUTH_GOOGLE.md) — Firebase/Google Auth
- [docs/GUIDES/ARQUIVOS_ANALISADOS.md](docs/GUIDES/ARQUIVOS_ANALISADOS.md) — Outputs
- [docs/GUIDES/MUDANCAS.md](docs/GUIDES/MUDANCAS.md) — Histórico de mudanças
- [docs/GUIDES/SOLUCAO.md](docs/GUIDES/SOLUCAO.md) — Solução final

### API
- [docs/API/CONTRATO_API.md](docs/API/CONTRATO_API.md) — Endpoints, models, exemplos Kotlin

### Setup & Configuração
- [docs/SETUP/FIRESTORE.md](docs/SETUP/FIRESTORE.md) — Firebase/Firestore setup

### Relatórios Técnicos
- [docs/REPORTS/TECNICO_IMPLEMENTACAO.md](docs/REPORTS/TECNICO_IMPLEMENTACAO.md) — Tudo implementado
- [docs/REPORTS/CLASS_MAPPING.md](docs/REPORTS/CLASS_MAPPING.md) — Mapeamento de classes

---

## 🐍 Scripts (scripts/)

### 🔴 PRINCIPAL — Treino
- **[scripts/train_new_model.py](scripts/train_new_model.py)** — Treina + exporta OpenVINO
- **[scripts/install_arc_deps.ps1](scripts/install_arc_deps.ps1)** — Instala PyTorch XPU (Arc)

### Testes da API
- [scripts/test_api_full.py](scripts/test_api_full.py)
- [scripts/test_api_upload.py](scripts/test_api_upload.py)
- [scripts/test_api_with_downloads.py](scripts/test_api_with_downloads.py)

### Testes de Detecção
- [scripts/test_detection_simple.py](scripts/test_detection_simple.py)
- [scripts/test_detection_detailed.py](scripts/test_detection_detailed.py)
- [scripts/test_detection_debug.py](scripts/test_detection_debug.py)

### Outros
- [scripts/test_auth_google.py](scripts/test_auth_google.py)
- [scripts/exemplos_api_completo.py](scripts/exemplos_api_completo.py)
- [scripts/organize_models.py](scripts/organize_models.py)

---

## 🔧 Ferramentas (tools/)

Utilitários para diagnóstico:
- [tools/check_firestore_api.py](tools/check_firestore_api.py)
- [tools/debug_firestore.py](tools/debug_firestore.py)
- [tools/test_firestore_connection.py](tools/test_firestore_connection.py)
- [tools/verify_firestore_created.py](tools/verify_firestore_created.py)

---

## 🤖 Modelos (models/)

```
models/
├── chair/                       ← Modelo padrão
├── garrafa_de_vidro/            ← Novos modelos aqui
├── yolo26l.pt                   ← Base model (sem treino)
└── ... (outros modelos)
```

Estrutura de cada modelo:
```
{modelo_name}/
├── my_model.pt                  (PyTorch weights)
├── my_model_openvino_model/     (OpenVINO IR)
│   ├── openvino_model.xml
│   ├── openvino_model.bin
│   └── ...
└── config.yaml
```

---

## 📊 Dados (data/)

```
data/
├── content/custom_data/         ← Dataset principal
│   ├── data.yaml
│   ├── train/ { images/, labels/ }
│   ├── valid/ { images/, labels/ }
│   └── test/  { images/, labels/ }
├── runs/                        ← Resultados de inferência
└── training_artifacts/          ← Dados temporários de treino
```

---

## 🚀 API (api-tcc/)

Backend FastAPI. Para rodar:
```bash
cd api-tcc
python main.py
```

Estrutura:
```
api-tcc/
├── main.py                      ← Ponto de entrada
├── app/core/                    ← Firebase, config
├── app/models/                  ← Pydantic schemas
├── app/routes/                  ← Endpoints (auth, detection, errors)
├── app/services/                ← Lógica de detecção
└── config/                      ← Variáveis de ambiente
```

**Swagger:** http://localhost:8000/docs

---

## 📁 Organização Final

| Pasta | Conteúdo | Arquivos |
|-------|----------|----------|
| `docs/` | Documentação centralizada | 12 arquivos .md |
| `scripts/` | Treino, testes, exemplos | 24 scripts Python |
| `tools/` | Utilitários diagnostico | 4 scripts |
| `models/` | Modelos YOLO treinados | 32 arquivos |
| `data/` | Datasets | 21847 arquivos |
| `api-tcc/` | Backend FastAPI | 65 arquivos |
| `downloads/` | Backups ZIP | 2 arquivos |
| `logs/` | Logs runtime (criado automaticamente) | N/A |

---

## ⚡ Comandos Rápidos

### Iniciar API
```bash
cd api-tcc && python main.py
```

### Treinar novo modelo
```bash
python scripts/train_new_model.py --model yolo11s.pt --epochs 100 --batch 8 --name novo_modelo
```

### Com Arc B570
```bash
python scripts/train_new_model.py --model yolo11s.pt --epochs 100 --batch 8 --name novo_modelo --device xpu --half
```

### Testar detecção
```bash
python scripts/test_detection_simple.py
```

### Ver logs de erro
```bash
# Erros do usuário "user@gmail.com" em 29/03/2026
cat logs/errors/user@gmail.com/2026-03-29.log
```

---

## 📌 Checklist de Setup

- [ ] Dependências instaladas: `pip install -r api-tcc/requirements.txt`
- [ ] Firebase credentials: `api-tcc/firebase-service-account.json`
- [ ] Dataset em: `data/content/custom_data/`
- [ ] API em: `http://localhost:8000/docs`
- [ ] Logs criados: `logs/errors/`

---

## 🔗 Links Principais

| Recurso | URL |
|---------|-----|
| API Swagger | http://localhost:8000/docs |
| System Status | http://localhost:8000/system/status |
| Classes | http://localhost:8000/system/classes |

---

**Última atualização:** 2026-04-08  
**Versão:** 1.1
