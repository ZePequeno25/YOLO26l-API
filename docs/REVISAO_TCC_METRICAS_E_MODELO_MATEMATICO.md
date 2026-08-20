# REVISÃO DO TCC: INTEGRAÇÃO DE MÉTRICAS E MODELO MATEMÁTICO DE PRECISÃO

Este documento consolida os textos, fórmulas matemáticas e tabelas referentes às três ferramentas de avaliação do sistema (`scripts/average_model_precision.py`, `scripts/calculate_box_confidence_averages.py` e `visualizar_metricas.py`) para inclusão direta no TCC (`TCC-Kelvin-Albuquerque-REVISADO.docx` / `docs/TCC_completo.md`).

---

## 1. CAPÍTULO 2 — FUNDAMENTAÇÃO TEÓRICA

### Adicionar Subseção 2.10: Modelo Matemático de Avaliação e Limiares de Detecção

A avaliação e calibração de modelos de detecção de objetos em tempo real fundamentam-se em métricas formais de visão computacional e em distribuições estatísticas das predições.

#### 2.10.1 Interseção sobre União (IoU)
A precisão de localização de uma caixa delimitadora predita ($\mathcal{B}_{\text{pred}}$) em relação à caixa de referência (*Ground Truth*, $\mathcal{B}_{\text{gt}}$) é quantificada pelo índice de Jaccard, conhecido como Interseção sobre União (IoU):

$$\text{IoU} = \frac{\text{Área}(\mathcal{B}_{\text{pred}} \cap \mathcal{B}_{\text{gt}})}{\text{Área}(\mathcal{B}_{\text{pred}} \cup \mathcal{B}_{\text{gt}})}$$

Uma detecção é classificada como **Verdadeiro Positivo ($VP$)** se $\text{IoU} \ge \text{limiar}$ (geralmente $0,50$) e a classe prevista estiver correta. Caso contrário, é considerada um **Falso Positivo ($FP$)**. Objetos reais não detectados constituem **Falsos Negativos ($FN$)**.

#### 2.10.2 Precisão ($P$), Revocação ($R$) e F1-Score
Dado um limiar de confiança $\tau$:

$$P(\tau) = \frac{VP(\tau)}{VP(\tau) + FP(\tau)}$$

$$R(\tau) = \frac{VP(\tau)}{VP(\tau) + FN(\tau)}$$

$$F1(\tau) = 2 \cdot \frac{P(\tau) \cdot R(\tau)}{P(\tau) + R(\tau)}$$

#### 2.10.3 Mean Average Precision (mAP)
A precisão média ($\text{AP}$) interpola a curva de Precisão-Revocação para uma determinada classe:

$$\text{AP} = \int_{0}^{1} P(R) \, dR$$

O $\text{mAP}$ representa a média aritmética dos valores de $\text{AP}$ entre todas as $N$ classes do dataset:

$$\text{mAP} = \frac{1}{N} \sum_{i=1}^{N} \text{AP}_i$$

- **$\text{mAP}@0.5$**: Avaliado sob limiar fixo de $\text{IoU} = 0,50$.
- **$\text{mAP}@[0.5:0.95]$**: Média obtida ao variar o limiar de IoU de $0,50$ a $0,95$ em passos de $0,05$.

#### 2.10.4 Modelo Matemático do Limiar Dinâmico Sugerido ($\tau_{\text{sugerido}}$)
Para mitigar falsos alarmes e otimizar o compromisso entre *Precision* e *Recall*, aplica-se uma calibração estatística sobre a distribuição de confianças de cada classe $c$. Sendo $c_1, c_2, \dots, c_n$ as confianças observadas:

$$\mu_c = \frac{1}{n} \sum_{i=1}^{n} c_i$$

$$\sigma_c = \sqrt{\frac{1}{n} \sum_{i=1}^{n} (c_i - \mu_c)^2}$$

O **Limiar Sugerido ($\tau_{\text{sugerido}}$)** é formalizado pela equação:

$$\tau_{\text{base}} = (\mu_c - 1,5 \cdot \sigma_c) + 0,40 \cdot \mu_c = 1,4 \cdot \mu_c - 1,5 \cdot \sigma_c$$

$$\tau_{\text{sugerido}} = \max\left(0,40, \; \min\left(0,95, \; 1,4 \cdot \mu_c - 1,5 \cdot \sigma_c\right)\right)$$

- **Significado Físico/Estatístico:** A subtração $1,5\sigma_c$ abrange aproximadamente 86,6% da distribuição de probabilidade das detecções válidas (preservando o *Recall*), enquanto o termo $+0,40\mu_c$ eleva o piso de corte para descartar detecções de baixa qualidade geradas por ruídos visuais (otimizando a *Precisão*). O *clamping* garante um piso mínimo de $0,40$ e teto máximo de $0,95$.

---

## 2. CAPÍTULO 3 — METODOLOGIA

### Atualização da Seção 3.8: Arquitetura de Tripla Camada de Avaliação

O sistema integra três ferramentas automatizadas de avaliação complementar:

1. **Camada de Validação do Treino (`scripts/average_model_precision.py`):**
   - Agrega métricas clássicas de benchmark ($\text{Precisão}$, $\text{Recall}$, $\text{mAP50}$, $\text{mAP50-95}$) a partir do arquivo CSV `prediction_metrics.csv`.
2. **Camada de Calibração Estatística (`scripts/calculate_box_confidence_averages.py`):**
   - Processa o banco SQLite (`prediction_metrics.db`), extrai a distribuição ($\mu_c, \sigma_c$) de cada classe e calcula os limiares dinâmicos sugeridos para alimentar a constante `CLASS_CONFIDENCE_THRESHOLDS` no backend.
3. **Camada de Monitoramento Operacional (`visualizar_metricas.py`):**
   - Avalia a eficiência da API em produção a partir do histórico de requisições reais do banco SQLite, monitorando o percentual de acertos (`requested_class_found`), volume de requisições por modelo e taxa global de conformidade.

---

## 3. CAPÍTULO 4 — RESULTADOS E DISCUSSÃO

### Inserir Seções 4.4, 4.5 e 4.6

#### 4.4 Consolidação de Métricas de Treino por Modelo
Resultados extraídos por `average_model_precision.py` a partir das predições tabulares.

#### 4.5 Tabela de Limiares Calculados por Classe e Calibração Fina
Valores obtidos com `calculate_box_confidence_averages.py` e aplicados em `CLASS_CONFIDENCE_THRESHOLDS`:

| Classe / Modelo | Detections ($n$) | Média ($\mu$) | Desvio Padrão ($\sigma$) | Limiar Sugerido ($\tau$) |
|---|:---:|:---:|:---:|:---:|
| **Máscara** | 1 | 0.6304 | 0.0000 | **0.88** |
| **Ônibus Grande** | 1 | 0.4688 | 0.0000 | **0.66** |
| **Caminhão** | 2505 | 0.6952 | 0.2241 | **0.64** |
| **Lata** | 3 | 0.4912 | 0.0495 | **0.61** |
| **Garrafa de Vidro Transparente** | 853 | 0.6629 | 0.2484 | **0.56** |
| **Rolinho Primavera** | 14 | 0.5659 | 0.1693 | **0.54** |
| **Empilhadeira** | 1106 | 0.5413 | 0.1852 | **0.48** |
| **Extintor CO2 Babcock Davis** | 797 | 0.5445 | 0.2016 | **0.46** |
| **Cadeira / Pessoa / Carro / EPI** | Variado | ~0.40 - 0.47 | ~0.11 - 0.17 | **0.40** |

#### 4.6 Métricas Operacionais de Produção da API
Métricas extraídas via `visualizar_metricas.py`:
- **Total de predições efetuadas:** 9.838 requisições.
- **Acertos confirmados:** 3.912 (`39,76%` de taxa de acerto global).
- **Modelo `all` (varredura multimodelo):** 3.900 requisições, 2.885 acertos (**73,97%** de taxa de sucesso).

---

## 4. CAPÍTULO 5 — CONSIDERAÇÕES FINAIS

### Adicionar à Seção 5.2 (Trabalhos Futuros)
- **MLOps e Calibração Dinâmica Automática:** Automatizar o reajuste periódico do dicionário `CLASS_CONFIDENCE_THRESHOLDS` via cron job que executa `calculate_box_confidence_averages.py` periodicamente conforme o banco SQLite de produção acumula novas amostras.
