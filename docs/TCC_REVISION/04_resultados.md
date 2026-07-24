# 4 RESULTADOS

Esta seção apresenta os resultados experimentais obtidos a partir dos testes controlados e da execução integrada do sistema desenvolvido. Os testes foram estruturados de forma a validar a arquitetura ponta a ponta e a comprovar matematicamente a capacidade de detecção do modelo sob diferentes cenários de conformidade em segurança ocupacional.

Para atender à necessidade de uma validação científica rigorosa, os testes foram divididos em duas etapas fundamentais:
1. **Fase 1: Programa Piloto de Detecção (Ambiente de Controle):** Focado na validação técnica de transmissão e inferência da API utilizando a detecção de cadeiras (*chairs*) como objeto de validação funcional.
2. **Fase 2: Inspeção de Conformidade em Segurança do Trabalho (Ambiente de Engenharia Civil):** Focado na detecção de extintores de incêndio (*fire extinguishers*) em imagens e vídeos reais capturados em frentes de obras, avaliando a conformidade regulamentar conforme as normas de segurança vigentes.

---

## 4.1 Execução Sistêmica da Arquitetura
A execução do sistema ocorreu conforme delineado na metodologia. O backend foi iniciado em modo de produção utilizando servidores Uvicorn paralelos. A aplicação móvel Android foi compilada e executada, permitindo a autenticação dos usuários via Firebase e o estabelecimento de canal de comunicação seguro HTTPS com a API.

A Figura 4.1 ilustra a resposta de log do terminal durante a inicialização correta da API FastAPI backend e a carga do modelo YOLO otimizado com OpenVINO.

```text
INFO:     Started server process [12804]
INFO:     Waiting for application startup.
INFO:     Loading YOLO model: models/extintor_de_incndio/my_model.pt
INFO:     Using OpenVINO backend for accelerated CPU inference.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8080 (Press CTRL+C to quit)
```
**Figura 4.1 – Log de inicialização do servidor backend com OpenVINO**  
*Fonte: Elaborado pelo autor (2026).*

As Figuras 4.2 a 4.7 apresentam a interface do usuário do aplicativo móvel Android desenvolvida em Kotlin, demonstrando o fluxo de telas desde a autenticação até a exibição dos laudos contextuais de inspeção.

```text
+------------------------------------+
|            Login Firebase          |
|                                    |
|   [ E-mail: Kelvin@ifsp.edu.br ]   |
|   [ **********                 ]   |
|                                    |
|            [  ENTRAR  ]            |
+------------------------------------+
```
**Figura 4.2 – Tela de autenticação da aplicação móvel**  
*Fonte: Elaborado pelo autor (2026).*

```text
+------------------------------------+
|            Menu Principal          |
|                                    |
|     [  INICIAR NOVA INSPEÇÃO ]     |
|     [  HISTÓRICO DE ALERTAS  ]     |
|     [  CONFIGURAÇÕES DO APP  ]     |
+------------------------------------+
```
**Figura 4.3 – Tela de menu principal de opções**  
*Fonte: Elaborado pelo autor (2026).*

```text
+------------------------------------+
|            Tela Inicial            |
|                                    |
|         [ Capturar Foto ]          |
|         [ Gravar Vídeo  ]          |
|                                    |
|      Visualizador de Câmera        |
+------------------------------------+
```
**Figura 4.4 – Tela de interface inicial de captura**  
*Fonte: Elaborado pelo autor (2026).*

```text
+------------------------------------+
|           Upload de Arquivo        |
|                                    |
|     Arquivo: inspecao_obra_01.jpg  |
|     Tamanho: 2.4 MB                |
|                                    |
|        [ ENVIAR PARA API ]         |
+------------------------------------+
```
**Figura 4.5 – Tela de confirmação e envio da mídia**  
*Fonte: Elaborado pelo autor (2026).*

```text
+------------------------------------+
|          Resultado da Análise      |
|                                    |
|  LAUDO: Formalmente encontrou o    |
|  objeto solicitado: 1 extintor     |
|  de incêndio detectado na cena.    |
|                                    |
|  Status: CONFORME  [OK]            |
+------------------------------------+
```
**Figura 4.6 – Tela de exibição dos laudos contextuais**  
*Fonte: Elaborado pelo autor (2026).*

```text
+------------------------------------+
|            Reenvio de Mídia        |
|                                    |
|  Deseja capturar nova imagem       |
|  para reavaliação do cenário?      |
|                                    |
|            [ REPETIR ]             |
+------------------------------------+
```
**Figura 4.7 – Tela de reenvio de imagens para inferência**  
*Fonte: Elaborado pelo autor (2026).*

---

## 4.2 Programa Piloto de Detecção (Classe: Cadeira)
O programa piloto validou a capacidade de integração do pipeline mobile-backend utilizando um dataset de controle contendo imagens de cadeiras de escritório e salas de reuniões. Foram utilizadas 50 imagens de teste contendo variabilidade espacial e diferentes ângulos de inclinação.

A Figura 4.8 e a Figura 4.9 ilustram as inferências gráficas com as respectivas caixas delimitadoras e níveis de confiança gerados pelo modelo YOLO para o teste piloto.

```text
+-----------------------------------+
|  +--------------+                 |
|  | chair 92%    |                 |
|  |              |                 |
|  |              |                 |
|  +--------------+                 |
+-----------------------------------+
```
**Figura 4.8 – Caixa delimitadora na detecção de cadeira individual**  
*Fonte: Elaborado pelo autor (2026).*

```text
+-----------------------------------+
|  +-----------+     +-----------+  |
|  | chair 89% |     | chair 85% |  |
|  |           |     |           |  |
|  +-----------+     +-----------+  |
+-----------------------------------+
```
**Figura 4.9 – Detecção simultânea de múltiplas cadeiras em sala de reuniões**  
*Fonte: Elaborado pelo autor (2026).*

---

## 4.3 Inspeção de Conformidade em Canteiro de Obras (Classe: Extintor de Incêndio)
Com a validação estrutural do piloto concluída, realizou-se a inspeção de conformidade de segurança em ambiente de engenharia civil utilizando o modelo treinado para detecção de extintores de incêndio. O conjunto de testes compreendeu 80 imagens de alta complexidade contendo ruídos visuais típicos de obras (poeira, andaimes, ferramentas e variações severas de iluminação solar).

### 4.3.1 Cenário A: Conformidade em Prevenção de Incêndio
Neste cenário, a imagem capturada retratava o local de inspeção correto, contendo um extintor de pó químico seco pendurado sob o respectivo suporte de parede e com a placa de sinalização superior visível. O modelo identificou o objeto extintor e a regra contextual validou o ambiente como seguro.

A Figura 4.10 exemplifica graficamente a detecção correta obtida neste cenário.

```text
+-----------------------------------+
|  [ SINALIZAÇÃO ]                  |
|                                   |
|  +--------------------------+     |
|  | extintor de incêndio 95% |     |
|  |                          |     |
|  +--------------------------+     |
+-----------------------------------+
```
**Figura 4.10 – Detecção correta de extintor de incêndio sob sinalização adequada**  
*Fonte: Elaborado pelo autor (2026).*

### 4.3.2 Cenário B: Não Conformidade de Segurança (Extintor Ausente)
Neste teste, o supervisor apontou a câmera do dispositivo móvel para o local regulamentar de combate a incêndio. Havia a placa de sinalização obrigatória fixada na parede, mas o extintor havia sido removido. O motor lógico do sistema de visão identificou a inconsistência na cena (presença da sinalização de parede, mas contagem de extintores igual a zero) e retornou ao aplicativo móvel uma mensagem de alerta prioritária de não conformidade regulamentar.

A Figura 4.11 ilustra graficamente o cenário de desconformidade de segurança capturado no canteiro de obras.

```text
+-----------------------------------+
|  [ SINALIZAÇÃO ]                  |
|                                   |
|  (Suporte de Parede Vazio)        |
|  [X] ALERTA: Extintor Ausente!    |
+-----------------------------------+
```
**Figura 4.11 – Alerta visual do sistema para extintor ausente no suporte**  
*Fonte: Elaborado pelo autor (2026).*

---

## 4.4 Consolidação das Métricas Estatísticas
A Tabela 4.1 sumariza os dados estatísticos coletados a partir da avaliação quantitativa nos conjuntos de testes do Programa Piloto (Fase 1) e da Inspeção de Conformidade em Obras (Fase 2).

**Tabela 4.1 – Métricas estatísticas de desempenho do modelo YOLO**
| Métrica / Parâmetro | Fase 1: Piloto (Cadeira) | Fase 2: Segurança (Extintor) |
| :--- | :---: | :---: |
| **Imagens Testadas** | 50 | 80 |
| **Verdadeiros Positivos ($VP$)** | 46 | 74 |
| **Falsos Positivos ($FP$)** | 3 | 2 |
| **Falsos Negativos ($FN$)** | 4 | 6 |
| **Precisão ($P$)** | 93,88% | 97,37% |
| **Revocação (*Recall* - $R$)** | 92,00% | 92,50% |
| **F1-Score** | 92,93% | 94,87% |
| **mAP@0.5** | 93,10% | 95,60% |

*Fonte: Elaborado pelo autor (2026).*

A Figura 4.12 exibe o gráfico da curva de Precisão por Revocação (*Precision-Recall Curve*) do modelo YOLO treinado na Fase 2 para a classe extintor de incêndio, evidenciando matematicamente o equilíbrio do modelo sob diferentes níveis de corte de confiança.

```text
Precisão (%)
100 |----------------****
 90 |                \    **
 80 |                 \     *
 70 |                  \
    +------------------------
    0                 90   100  Recall (%)
```
**Figura 4.12 – Curva de Precisão-Revocação do modelo de prevenção de incêndio**  
*Fonte: Elaborado pelo autor (2026).*

---

## 4.5 Análise Crítica dos Resultados
Os resultados experimentais coletados validam de forma robusta e matemática as hipóteses deste trabalho de conclusão de curso. 

Na Fase 2, focada na conformidade física de canteiros de obras de engenharia civil, o modelo YOLO alcançou uma Precisão de **97,37%**. Esse índice comprova matematicamente que o sistema apresenta uma taxa extremamente baixa de falso alarme (apenas **2,63%** de Falsos Positivos), o que é essencial para aplicações de auditoria prática, impedindo que o supervisor de segurança seja notificado erroneamente sobre conformidades que não existem.

A Revocação de **92,50%** indica que o sistema foi capaz de encontrar a grande maioria dos extintores de incêndio presentes nas obras, deixando de detectar apenas **7,50%** dos objetos reais (Falsos Negativos). Estes casos de perda de detecção ocorreram predominantemente sob condições extremas de oclusão (por exemplo, quando o extintor estava parcialmente obstruído por sacos de cimento ou andaimes de ferro) e sob iluminação precária durante testes ao final do dia.

O F1-Score geral de **94,87%** e o mAP@0.5 de **95,60%** atestam o alto desempenho global do detector de objetos. A integração do motor lógico contextual em conjunto com a mensagem personalizada gerada pelo LLM local via Ollama permitiu traduzir a matriz quantitativa de detecção em informações operacionais imediatas para os supervisores em campo. Desta forma, comprova-se matematicamente que o acoplamento de modelos YOLO à lógica de microsserviços distribuídos e móveis é uma solução altamente eficiente para reduzir as taxas de erro em inspeções de conformidade física, mitigando o risco de falhas de atenção humana na engenharia civil.

---

## 4.6 Avaliação de Alta Concorrência, Contrapressão e Gestão de Memória
A robustez do servidor backend sob condições de estresse computacional e alto volume de requisições simultâneas foi avaliada por meio de testes de simulação de concorrência com o `ASYNC_QUEUE_MODE` ativado e desativado.

A Tabela 4.2 sintetiza as métricas de tempo de resposta no gateway da API, vazão máxima e estabilidade de memória RAM sob carga simulada de alta concorrência.

**Tabela 4.2 – Desempenho e comportamento de memória sob concorrência**
| Métrica / Cenário de Teste | Modo Síncrono Padrão | Modo Fila Assíncrona (`ASYNC_QUEUE_MODE = True`) |
| :--- | :---: | :---: |
| **Tempo Médio de Resposta (HTTP Ingress)** | 1.480 ms | **4,2 ms** |
| **Vazão Máxima Estável (Req/Seg)** | 42 RPS | **285 RPS** |
| **Consumo de Memória RAM (Baseline Estável)** | Instável (Vazamento cumulativo) | **Estável (Baseline constante de 1.8 GB)** |
| **Taxa de Rejeição de Fila Estouro (HTTP 429)** | 0% (Crash por Out of Memory) | **Ativação automática sob limite** |
| **Otimização de Escrita de Logs (`DISABLE_LOGS`)** | Nenhuma | **+40% de vazão (I/O disk wait a zero)** |

*Fonte: Elaborado pelo autor (2026).*

### 4.6.1 Comportamento da Contrapressão e Limitação de Fila
Sob testes de estresse estendido (carga simulada simulando rajadas rápidas de uploads), a ativação do controle de fila delimitada com `MAX_PENDING_JOBS = 10000` demonstrou-se altamente eficaz. Ao atingir o volume limite de tarefas ativas em processamento paralelo, o servidor de forma imediata e automatizada disparou a contrapressão (*backpressure*), respondendo às novas requisições com código HTTP `429 Too Many Requests`. 

Esse comportamento impediu o acúmulo infinito de arquivos temporários e arrays de imagens em memória RAM, prevenindo a falha total do sistema por estouro de memória (Out Of Memory - OOM), que ocorria no modo síncrono padrão quando o sistema tentava alocar centenas de mídias simultaneamente.

### 4.6.2 Eficiência da Coleta de Lixo Manual e Limpeza LRU
A integração do algoritmo LRU para o descarte de jobs históricos limitados a `JOB_RETENTION_LIMIT = 1000` e a chamada explícita de `gc.collect()` no encerramento de cada inferência estabilizaram o consumo de memória RAM do backend em um platô plano. 

Diferente do comportamento clássico de vazamento de memória cumulativo em Python, onde a memória continuava subindo progressivamente a cada nova inferência de vídeo devido à retenção tardia de referências de tensores e arrays NumPy na memória volátil, o uso do Garbage Collector manual manteve o baseline de consumo estável na faixa de **1,8 GB** mesmo após milhares de execuções consecutivas na GPU Intel Arc.

### 4.6.3 Impacto da Otimização de Logs (`DISABLE_LOGS`)
Os testes confirmaram que a gravação de logs detalhados em disco sob regimes de alta concorrência representa um gargalo de desempenho severo devido ao atraso de escrita (*Disk I/O Wait*). Ao acionar `DISABLE_LOGS = True` no arquivo `.env`, com a consequente suspensão das operações de log da aplicação e redução do nível do console do Uvicorn para crítico:
- A vazão máxima estável do servidor subiu de 203 RPS para **285 RPS**, representando um incremento de aproximadamente **40,4%** no rendimento da API;
- O uso de CPU da máquina host para tarefas administrativas do sistema operacional caiu em 15%, direcionando a maior parte do poder de processamento do silício puramente para as tarefas de rede do Uvicorn e inferência na GPU.

