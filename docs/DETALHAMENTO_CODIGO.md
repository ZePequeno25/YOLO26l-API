# Detalhamento de Classes e Métodos - API TCC

Este documento descreve detalhadamente a estrutura de código da API, relatando a finalidade de cada classe, método (`def`), rota e módulo que compõem o sistema.

---

## 1. Módulo Principal (`main.py`)

O arquivo [main.py](file:///c:/Users/aborr/Projeto%20TCC/YOLO26l-API/api-tcc/main.py) é o ponto de entrada da aplicação FastAPI. Ele configura o servidor, inicializa os middlewares de segurança e registra as rotas.

* **`lifespan(app: FastAPI)`** (Context Manager)
  * **Finalidade**: Gerencia o ciclo de vida da aplicação. Executa no boot da API para:
    1. Verificar se o serviço local do Ollama está disponível (se ativo no `.env`).
    2. Inicializar as tabelas do banco de dados SQLite (`prediction_metrics.db`).
    3. Executar o **Warm-Up dos modelos YOLO** (`preload_all_models`), aquecendo a memória RAM/GPU antes que as requisições cheguem.
* **`make_gzip_handler(original_handler)`** e **`GzipRoute`**
  * **Finalidade**: Intercepta requisições HTTP e compacta as respostas em Gzip automaticamente, otimizando o consumo de banda de rede do app Android.
* **Middlewares Configurados**:
  * `CORSMiddleware`: Gerencia as permissões de acesso Cross-Origin.
  * `TrustedHostMiddleware`: Protege o host de cabeçalhos de requisição forjados.
  * `RequestProtectionMiddleware` (Customizado): Middleware para interceptar ataques e aplicar proteção anti-DDoS e rate-limiting por IP.

---

## 2. Endpoints e Rotas (`app/routes/`)

### Rota de Detecção (`detection_routes.py`)
Centraliza as operações de processamento de mídia da API.

* **`POST /analyze`**
  * **Finalidade**: Ponto de entrada de produção para o aplicativo Android. Recebe o arquivo de imagem/vídeo, valida autenticação JWT e o cabeçalho de idempotência. Executa a inferência YOLO de forma síncrona ou enfileira assincronamente dependendo do `.env`.
* **`POST /analyze-test`**
  * **Finalidade**: Rota de testes rápidos de auditoria sem validação de tokens JWT (pode ser chamada por ferramentas como Postman/Curl).
* **`GET /status/{job_id}`**
  * **Finalidade**: Retorna o status de processamento de um trabalho em lote/assíncrono.
* **`GET /models`**
  * **Finalidade**: Retorna a lista de modelos ativos e disponíveis para inferência (filtrando os modelos desativados em `DISABLED_MODELS`).

---

## 3. Serviço de Detecção (`app/services/detection_service.py`)

A classe [DetectionService](file:///c:/Users/aborr/Projeto%20TCC/YOLO26l-API/api-tcc/app/services/detection_service.py) gerencia todo o ciclo de carregamento e inferência dos modelos YOLO, utilizando o framework OpenVINO da Intel.

* **`preload_all_models()`**
  * **Finalidade**: Varre os modelos ativos na pasta `models/` e realiza o pré-carregamento para `models_cache` durante o boot da aplicação, zerando a latência da primeira inferência em tempo real.
* **`get_model(model_name: str)`**
  * **Finalidade**: Carrega o modelo YOLO do disco (PyTorch `.pt` ou formato compilado OpenVINO) baseado no alias e salva em um dicionário de cache na RAM com proteção por trava de concorrência (`_model_load_lock`).
* **`analyze(file: UploadFile, model_name: str)`**
  * **Finalidade**: Método principal de análise de imagens/vídeos. Salva o arquivo temporariamente, chama a inferência, aplica a filtragem por limiares dinâmicos (`CLASS_CONFIDENCE_THRESHOLDS`), invoca a inspeção em sobcamada (`SubLayerManager`) e gera os laudos contextuais.
* **`_run_single_model_inference(model_name: str, source: Any, is_video: bool)`**
  * **Finalidade**: Executa a predição da rede YOLO sobre a mídia utilizando aceleração gráfica OpenVINO em piso seguro de `conf=0.40`.
* **`list_available_models()`**
  * **Finalidade**: Retorna apenas os modelos ativos focados em construção civil, segurança e infraestrutura governamental, ignorando modelos desativados mapeados em `DISABLED_MODELS`.

---

## 4. Serviço de Classificação em Sobcamada (`app/services/sublayer_service.py`)

A classe [SubLayerManager](file:///c:/Users/aborr/Projeto%20TCC/YOLO26l-API/api-tcc/app/services/sublayer_service.py) gerencia as verificações hierárquicas em cascata sobre as regiões de interesse (RoI) dos objetos detectados.

* **`SUB_LAYER_INSPECTOR_CONFIG`**
  * **Finalidade**: Dicionário de configuração contendo o mapeamento de sub-inspetores categorizados por objeto (Extintores, EPIs de Trabalhadores, Maquinário Pesado, Cones, Vagas, Contêineres).
* **`inspect_cropped_roi(class_name: str, roi_img: np.ndarray, context_boxes: list)`**
  * **Finalidade**: Recorta a imagem do objeto detectado e avalia sub-características (como presença de trava/lacre, pressão no manômetro, mangueira conectada, faixas reflexivas, placas de sinalização de emergência). Retorna os itens aprovados e reprovados com os alertas correspondentes.

---

## 5. Serviço de Mensagem Personalizada LLM (`app/services/ollama_message_service.py`)

A classe [OllamaMessageService](file:///c:/Users/aborr/Projeto%20TCC/YOLO26l-API/api-tcc/app/services/ollama_message_service.py) é responsável pela interface da API com o modelo local Ollama para gerar laudos formais de conformidade em português.

* **`generate_personalized_message(analysis_result: dict, analysis_model: str)`**
  * **Finalidade**: Consolida o resultado de detecções e os alertas gerados pela inspeção de sobcamada e gera uma frase técnica única em português para a aplicação móvel.

---

## 6. Serviço de Conformidade (`app/services/compliance_service.py`)

A classe [ComplianceService](file:///c:/Users/aborr/Projeto%20TCC/YOLO26l-API/api-tcc/app/services/compliance_service.py) opera o motor de regras contextuais de cena, verificando ausências de EPIs (NR 6) e regras físicas de meio de canteiro de obras (NR 18).
