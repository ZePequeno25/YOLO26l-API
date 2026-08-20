# 🏗️ API TCC — Visão Computacional, Inspeção de Conformidade e Classificação em Sobcamada

Sistema de visão computacional e inteligência artificial voltado para a **Inspeção de Conformidade em Canteiros de Obras de Engenharia Civil, Segurança do Trabalho (NR 6 / NR 18) e Infraestrutura Governamental**.

O sistema combina modelos **YOLO** acelerados por **Intel OpenVINO**, um motor de **Classificação em Sobcamada (Sub-layer Inspection)**, **Warm-Up de Modelos no startup da API**, calibração estatística de limiares dinâmicos e laudos em linguagem natural gerados por **LLM local (Ollama)**.

---

## 🚀 Principais Funcionalidades Recentes

1. **🔬 Classificação em Sobcamada (Hierarchical Sub-layer Inspection):**
   - Inspeciona em cascata sub-características de objetos primários sem bloquear o tempo real.
   - **Extintores:** Trava/lacre de segurança, manômetro de carga (faixa operacional verde), mangueira de descarga e placa de sinalização de emergência.
   - **Pessoas / Colaboradores:** Capacete de segurança com jugular, colete reflexivo de alta visibilidade e óculos de proteção facial (NR 6).
   - **Maquinário Pesado / Obras:** Alarme sonoro de ré, cabine ROPS/FOPS em escavadeiras, travas em betoneiras e demarcação de vagas.

2. **⚡ Warm-Up de Modelos no Startup (`preload_all_models`):**
   - Todos os modelos ativos são pré-carregados na memória RAM/GPU no boot do servidor FastAPI, eliminando a latência inicial na ativação do modo tempo real.

3. **📐 Limiares Dinâmicos de Confiança ($\tau_{\text{sugerido}}$):**
   - Calibração estatística baseada na média ($\mu$) e desvio padrão ($\sigma$) por classe ($\tau_{\text{sugerido}} = 1,4\mu - 1,5\sigma$), aplicada via `CLASS_CONFIDENCE_THRESHOLDS`.

4. **🚫 Escopo de Construção / Governamental (`DISABLED_MODELS`):**
   - Desativação seletiva de modelos não focados em engenharia/governo (como alimentos e garrafas de vidro).

---

## 📚 Índice de Documentações (`docs/`)

- [📄 TCC Completo (Dissertação em Markdown)](docs/TCC_completo.md)
- [📐 Revisão do TCC — Fórmulas Matemáticas e Tabelas Estatísticas](docs/REVISAO_TCC_METRICAS_E_MODELO_MATEMATICO.md)
- [🏗️ Arquitetura de Microsserviços e Fluxo de Dados](docs/ARQUITETURA_MICROSSERVICOS.md)
- [🔍 Detalhamento de Classes, Métodos e Rotas do Código](docs/DETALHAMENTO_CODIGO.md)
- [📘 Manual de Uso da API e Guia dos Scripts Estatísticos](docs/MANUAL_DE_USO_E_SCRIPTS.md)
- [🔀 Fluxo Detalhado do Sistema](docs/FLUXO_SISTEMA.md)

---

## 🛠️ Como Executar

### 1. Iniciar o Servidor FastAPI
```bash
python api-tcc/main.py
```

### 2. Executar os Scripts Estatísticos e de Monitoramento
```bash
# Visualizar estatísticas de produção do SQLite:
python scripts/visualizar_metricas.py

# Recalcular limiares dinâmicos por classe:
python scripts/calculate_box_confidence_averages.py

# Gerar resumo de mAP e Precisão de treino:
python scripts/average_model_precision.py
```

---

## 🔒 Segurança e Robustez
- **Autenticação em Duas Camadas:** Firebase ID Token -> JWT Bearer local da API (24h).
- **Proteção Anti-DDoS e Rate Limiting:** Limitação de requisições por IP e bloqueio automático contra rotas 404.
- **Processamento de Vídeo:** Amostragem por `stride=2` e inferência em geradores iterativos (`stream=True`) para baixo consumo de memória RAM.
