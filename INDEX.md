# 🗂️ ÍNDICE DE NAVEGAÇÃO RÁPIDA

## 🚀 Comece Aqui

- 📖 **[README.md](README.md)** — Visão geral do projeto e guia mestre
- 📘 **[docs/MANUAL_DE_USO_E_SCRIPTS.md](docs/MANUAL_DE_USO_E_SCRIPTS.md)** — Manual de uso da API e execução dos scripts estatísticos
- 📐 **[docs/REVISAO_TCC_METRICAS_E_MODELO_MATEMATICO.md](docs/REVISAO_TCC_METRICAS_E_MODELO_MATEMATICO.md)** — Modelo matemático completo ($\text{IoU}$, $\text{P}$, $\text{R}$, $\text{mAP}$, Limiares Dinâmicos $\tau = 1,4\mu - 1,5\sigma$) e tabelas para o TCC
- 📚 **[docs/TCC_completo.md](docs/TCC_completo.md)** — Texto integral do TCC
- 🏗️ **[docs/ARQUITETURA_MICROSSERVICOS.md](docs/ARQUITETURA_MICROSSERVICOS.md)** — Arquitetura SOA, Warm-Up de modelos e Classificação em Sobcamada

---

## 📚 Documentação (docs/)

### Guias & Tutoriais
- [docs/MANUAL_DE_USO_E_SCRIPTS.md](docs/MANUAL_DE_USO_E_SCRIPTS.md) — Manual de uso e execução de scripts estatísticos
- [docs/ARQUITETURA_MICROSSERVICOS.md](docs/ARQUITETURA_MICROSSERVICOS.md) — Arquitetura de microsserviços, Warm-Up e Sobcamada
- [docs/DETALHAMENTO_CODIGO.md](docs/DETALHAMENTO_CODIGO.md) — Detalhamento de classes, métodos, rotas e serviços
- [docs/FLUXO_SISTEMA.md](docs/FLUXO_SISTEMA.md) — Diagrama de sequência e fluxo síncrono da API
- [docs/REVISAO_TCC_METRICAS_E_MODELO_MATEMATICO.md](docs/REVISAO_TCC_METRICAS_E_MODELO_MATEMATICO.md) — Fórmulas matemáticas e tabelas de validação

---

## 🐍 Scripts Estatísticos e de Monitoramento (scripts/)

### 📊 Avaliação e Estatísticas de Produção
- **[scripts/visualizar_metricas.py](scripts/visualizar_metricas.py)** — Histórico completo de acertos e requisições no SQLite
- **[scripts/calculate_box_confidence_averages.py](scripts/calculate_box_confidence_averages.py)** — Cálculo de $\mu, \sigma$ e limiares dinâmicos sugeridos por classe
- **[scripts/average_model_precision.py](scripts/average_model_precision.py)** — Resumo de Precisão, Recall e mAP por modelo

### 🚀 Treino & Ferramentas
- [scripts/train_new_model.py](scripts/train_new_model.py) — Treino YOLO e conversão OpenVINO
- [scripts/organize_models.py](scripts/organize_models.py) — Organização de diretórios de modelos
- [scripts/test_api_full.py](scripts/test_api_full.py) — Teste completo dos endpoints

---

## 🚀 API Backend (api-tcc/)

Para iniciar a API:
```bash
python api-tcc/main.py
```

Swagger Interativo: http://localhost:8080/docs
