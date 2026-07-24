# Fluxo de Funcionamento do Sistema - API TCC

Este documento descreve a arquitetura geral da API TCC e detalha a jornada completa de uma requisição — desde o momento em que o aplicativo móvel Android realiza o upload de uma mídia até a entrega final dos resultados enriquecidos com Inteligência Artificial.

---

## 1. Visão Geral da Arquitetura

A API é construída sob o framework **FastAPI** (Python 3.12) e opera em conformidade com o padrão de **Microsserviços/SOA**. O sistema se apoia em três pilares fundamentais:
1. **Inferência YOLO**: Processamento paralelo de múltiplos modelos usando o runtime otimizado **Intel OpenVINO** com aceleração via GPU Intel Arc.
2. **Motor de Conformidade (Compliance)**: Validação lógica de regras de segurança do trabalho baseada nos objetos detectados.
3. **Resumo Natural (LLM local com Ollama)**: Geração de laudos e alertas textuais contextuais dinâmicos em português usando o modelo `qwen2.5-coder`.

---

## 2. Diagrama de Sequência do Fluxo de Requisição

O diagrama abaixo ilustra o caminho síncrono completo que uma requisição percorre pela infraestrutura da aplicação:

```mermaid
sequenceDiagram
    autonumber
    actor Android as App Android (Cliente)
    participant Cloudflare as Proxy Cloudflare
    participant FastAPI as Servidor FastAPI (main.py)
    participant Auth as Validador Firebase (firebase.py)
    participant Guard as Trava de Concorrência (analysis_guard.py)
    participant DetectService as Serviço de Detecção (detection_service.py)
    participant YOLO as Motor YOLO (OpenVINO)
    participant Compliance as Motor de Conformidade (compliance_service.py)
    participant Ollama as Serviço de Mensagem LLM (ollama_message_service.py)

    Android->>Cloudflare: POST /detection/analyze (Multipart FormData + JWT + X-Request-ID)
    activate Cloudflare
    Cloudflare->>FastAPI: Encaminha Requisição (Filtros de Gzip / DDoS)
    activate FastAPI
    
    Note over FastAPI: Valida cabeçalho X-Request-ID (Idempotência)<br/>Se já concluído, retorna do cache imediatamente!
    
    FastAPI->>Auth: Valida Token JWT de Autenticação
    activate Auth
    Auth-->>FastAPI: Retorna UID do Usuário
    deactivate Auth

    FastAPI->>Guard: Adquire trava lock(UID)
    activate Guard
    Guard-->>FastAPI: Trava adquirida (Sem concorrência por usuário)
    deactivate Guard

    FastAPI->>DetectService: analyze(arquivo, modelo_solicitado)
    activate DetectService

    Note over DetectService: Resolve Aliases Verbais (ex: "ônibus e caminhões" -> pasta física)<br/>Verifica cache de modelos em memória

    loop Para cada modelo relevante (ou modelo solicitado)
        DetectService->>YOLO: _run_single_model_inference(modelo, imagem)
        activate YOLO
        Note over YOLO: Carrega pesos (.pt ou OpenVINO)<br/>Roda inferência na GPU (conf=0.98 para críticos)
        YOLO-->>DetectService: Retorna Bounding Boxes brutos
        deactivate YOLO
    end

    DetectService->>DetectService: Agrupa boxes e executa Deduplicação IoU (NMS)
    
    DetectService->>Compliance: evaluate_compliance(classes_detectadas)
    activate Compliance
    Compliance-->>DetectService: Retorna Status (CONFORME/NÃO CONFORME) + Alertas
    deactivate Compliance

    DetectService-->>FastAPI: Retorna Dicionário Consolidade (Boxes + Conformidade)
    deactivate DetectService

    FastAPI->>Ollama: generate_personalized_message(resultado)
    activate Ollama
    Note over Ollama: Envia prompt estruturado ao LLM local<br/>Recebe laudo e limpa repetições de prompt
    Ollama-->>FastAPI: Retorna Laudo em Frase Única
    deactivate Ollama

    FastAPI->>FastAPI: Salva resultado no Cache de Idempotência
    
    FastAPI->>Android: Retorna 200 OK (AnalysisResponse JSON completo)
    deactivate FastAPI
    deactivate Cloudflare
```

---

## 3. Detalhamento Etapa por Etapa

### Etapa 1: Envio do Cliente e Mapeamento de Idempotência
* O aplicativo móvel Android efetua um upload de imagem/vídeo para a rota `/detection/analyze`.
* Um cabeçalho único `X-Request-ID` é anexado à chamada.
* Se a rede sofrer oscilações ou falhar no meio do envio e o Android reenviar o arquivo com o mesmo `X-Request-ID`, o servidor intercepta a requisição, localiza o resultado da inferência original já processada e o devolve instantaneamente, economizando recursos de GPU.

### Etapa 2: Barreiras de Segurança e Proteção
* **Gzip Route**: Descompacta payloads comprimidos de forma transparente.
* **Firebase Security**: Valida que o token JWT enviado veio de uma sessão de usuário real e decodifica o UID do usuário.
* **Analysis Guard**: Implementa um semáforo de concorrência por usuário. Se o mesmo usuário enviar 5 fotos ao mesmo tempo, a API serializa as chamadas em fila para não estourar a memória RAM do servidor.

### Etapa 3: Seleção e Carregamento de Modelos
* A API suporta **23 modelos YOLO** individuais.
* A API recebe nomes descritivos e amigáveis em português (como `ônibus e caminhões` ou `extintor e sua sinalização`) e mapeia-os transparentemente para as pastas físicas de pesos correspondentes.
* Os modelos são mantidos em cache na memória RAM (`models_cache`) após o primeiro carregamento para evitar o atraso de leitura de disco nas próximas inferências.

### Etapa 4: Inferência e Regras de Limiar (Threshold)
* O processamento é executado dentro do `ThreadPoolExecutor` global compartilhado para evitar vazamento de threads.
* Para modelos gerais (como cadeira), o limiar de confiança configurado é de `85%`.
* Para modelos de alta incidência de falsos positivos em ambientes normais (como máquinas de obras e escavadeiras que podem confundir mangueiras de extintores), a API força um limiar de **`98%`**, garantindo que apenas objetos reais sejam detectados.

### Etapa 5: Deduplicação de Bounding Boxes (NMS)
* Quando múltiplos modelos são executados sobre a mesma imagem (varredura global `all`), diferentes modelos podem gerar retângulos sobrepostos sobre o mesmo objeto.
* A API aplica um algoritmo customizado de **Interseção sobre União (IoU)** para unificar e limpar detecções redundantes antes de contar os objetos.

### Etapa 6: Motor de Conformidade (EPIs e Segurança)
* Os objetos consolidados são enviados para o `ComplianceService`. Ele valida regras lógicas pré-estabelecidas baseadas nas normas de segurança:
  * Exemplo 1: Se `pessoa` for detectada mas `safety_vest` (colete) ou `hardhat` (capacete) não forem encontrados, a cena é marcada como `NÃO CONFORME` e um alerta de EPI é registrado.

### Etapa 7: Geração de Mensagem Natural (LLM)
* O serviço `OllamaMessageService` envia o resumo de objetos e o status de conformidade para o Ollama local.
* O LLM (`qwen2.5-coder`) gera uma frase humana descritiva em português sobre o estado do ambiente.
* A API faz o pós-processamento da resposta do LLM para remover eventuais resíduos ou repetições.

### Etapa 8: Resposta ao Cliente
* A API responde com o status `200 OK` contendo o payload estruturado `AnalysisResponse` (contagens, caixas delimitadoras detalhadas com coordenadas, status de conformidade, alertas e a mensagem do LLM).
