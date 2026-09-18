# Manual de Uso e Guia dos Scripts do Sistema

Este documento descreve detalhadamente a utilização da API RESTful de Detecção e Inspeção de Conformidade, a inicialização do ambiente e a execução dos scripts de avaliação estatística e monitoramento.

---

## 1. Inicialização da API Backend

### 🚀 1.1 Iniciar o Servidor FastAPI
Para iniciar o servidor backend com suporte a aceleração gráfico OpenVINO e pré-carregamento dos modelos (*Warm-Up*):

```bash
# Executar a partir da raiz da API (api-tcc):
cd api-tcc
python main.py
```

Ou a partir da raiz do repositório:
```bash
python api-tcc/main.py
```

### ⚡ 1.2 O que acontece na inicialização (Lifespan Hook)
1. **Métricas de Banco:** Cria/valida as tabelas no SQLite local (`api-tcc/data/prediction_metrics.db`).
2. **Checagem do Ollama:** Valida se o serviço LLM local (`ollama serve`) está ativo.
3. **Model Warm-Up:** Invoca `preload_all_models()`, carregando todos os modelos ativos de visão computacional na memória RAM/GPU para latência zero no aplicativo cliente.

---

## 2. Execução dos Scripts de Avaliação e Monitoramento

Todos os scripts estatísticos estão organizados no diretório `scripts/` e utilizam resolução dinâmica de caminhos (`pathlib.Path`).

### 📊 2.1 Visualizar Métricas Operacionais de Produção
Para verificar o histórico de requisições enviadas ao backend, taxa de acerto por modelo e porcentagem de conformidade:

```bash
python scripts/visualizar_metricas.py
```

* **Saída Esperada:** Tabela formatada contendo total de chamadas, acertos confirmados (`requested_class_found`), porcentagem de acertos e confiança média acumulada no SQLite (`api-tcc/data/prediction_metrics.db`).

---

### 📐 2.2 Calibrar e Sincronizar Limiares Dinâmicos por Classe ($\tau_{\text{sugerido}}$)
Para consultar a distribuição de confiança das caixas delimitadoras ($\mu, \text{min}, \text{max}, \sigma$), recalcular os limiares dinâmicos por classe e **sincronizar automaticamente** com o serviço de detecção do backend:

```bash
python scripts/calculate_box_confidence_averages.py
```

* **Fórmula Estatística Aplicada:**
  $$\tau_{\text{sugerido}} = \max\left(0,40, \; \min\left(0,95, \; 1,4\mu - 1,5\sigma\right)\right)$$
* **Mapeamento Automático:** Os valores resultantes alimentam diretamente a constante `CLASS_CONFIDENCE_THRESHOLDS` em [`api-tcc/app/services/detection_service.py`](file:///c:/Users/aborr/Projeto%20TCC/YOLO26l-API/api-tcc/app/services/detection_service.py).

---

### 🔄 2.3 Pipeline MLOps de Atualização Automática de Limiares
Para executar o pipeline automatizado MLOps que recalcula os limiares de confiança do SQLite, aplica a calibração no backend e exporta o relatório técnico em JSON:

```bash
python scripts/update_class_thresholds.py
```

* **Saída Gerada:**
  - Atualização direta em [`api-tcc/app/services/detection_service.py`](file:///c:/Users/aborr/Projeto%20TCC/YOLO26l-API/api-tcc/app/services/detection_service.py).
  - Relatório JSON completo salvo em `api-tcc/logs/metrics/class_thresholds_summary.json`.

---

### 📈 2.4 Resumo de Métricas de Treino/Benchmark
Para agregar as métricas de treino e teste ($\text{Precisão}$, $\text{Recall}$, $\text{mAP50}$, $\text{mAP50-95}$) a partir da base de predições tabulares:

```bash
python scripts/average_model_precision.py
```

* **Saída Gerada:** Arquivo `api-tcc/logs/metrics/model_precision_summary.csv` contendo a consolidação por modelo.


---

## 3. Guia de Endpoints e Requisições HTTP (API REST)

### 3.1 Endpoint Principal de Análise (`POST /detection/analyze`)
Requer autenticação via Token JWT Bearer no cabeçalho.

#### **Requisição cURL:**
```bash
curl -X POST "http://localhost:8080/detection/analyze" \
  -H "Authorization: Bearer <SEU_TOKEN_JWT>" \
  -F "file=@/caminho/para/imagem_obra.jpg" \
  -F "model_name=extintor e sua sinalização"
```

#### **Exemplo de Resposta JSON com Classificação em Sobcamada:**
```json
{
  "requested_model": "extintor e sua sinalização",
  "class_counts": {
    "Extintor de Incêndio": 1,
    "Placa de Sinalização": 1
  },
  "compliance_status": "CONFORME",
  "compliance_alerts": [],
  "compliance_report": "A análise da cena identificou: 1 Extintor de Incêndio e 1 Placa de Sinalização. Status: Conforme.",
  "sub_layer_analysis": [
    {
      "object_class": "Extintor de Incêndio",
      "category": "Prevenção contra Incêndio",
      "is_conforming": true,
      "passed_items": [
        "Trava / Lacre de Segurança",
        "Manômetro de Carga (Pressão)",
        "Mangueira / Difusor de Incêndio",
        "Placa de Sinalização de Emergência"
      ],
      "failed_items": [],
      "alerts": []
    }
  ]
}
```

---

### 3.2 Endpoint de Teste Rápido sem Autenticação (`POST /detection/analyze-test`)
Permite testes rápidos em ambiente de desenvolvimento.

```bash
curl -X POST "http://localhost:8080/detection/analyze-test" \
  -F "file=@/caminho/para/imagem_teste.jpg" \
  -F "model_name=cadeira"
```

---

### 3.3 Listar Modelos Ativos e Disponíveis (`GET /detection/models`)
Retorna a lista de modelos voltados para construção civil, segurança e infraestrutura governamental ativos no backend:

```bash
curl -X GET "http://localhost:8080/detection/models"
```
