# Detalhamento de Classes e Métodos - API TCC

Este documento descreve detalhadamente a estrutura de código da API, relatando a finalidade de cada classe, método (`def`), rota e módulo que compõem o sistema.

---

## 1. Módulo Principal (`main.py`)

O arquivo [main.py](file:///c:/Users/aborr/Projeto%20TCC/YOLO26l-API/api-tcc/main.py) é o ponto de entrada da aplicação FastAPI. Ele configura o servidor, inicializa os middlewares de segurança e registra as rotas.

* **`lifespan(app: FastAPI)`** (Context Manager)
  * **Finalidade**: Gerencia o ciclo de vida da aplicação. Executa no boot da API para verificar se o serviço local do Ollama está disponível (caso a geração de mensagens personalizadas esteja ativa). Aborta a inicialização caso o Ollama esteja offline para evitar erros de execução.
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
* **`run_background_analysis(...)`**
  * **Finalidade**: Função executada em uma thread separada pelo gerenciador de tarefas em segundo plano do FastAPI para processar requisições assíncronas em lote quando ativada.

---

## 3. Serviço de Detecção (`app/services/detection_service.py`)

A classe [DetectionService](file:///c:/Users/aborr/Projeto%20TCC/YOLO26l-API/api-tcc/app/services/detection_service.py) gerencia todo o ciclo de carregamento e inferência dos modelos YOLO, utilizando o framework OpenVINO da Intel.

* **`get_model(model_name: str)`**
  * **Finalidade**: Carrega o modelo YOLO do disco (PyTorch `.pt` ou formato compilado OpenVINO) baseado no alias e salva em um dicionário de cache na RAM.
* **`analyze(file: UploadFile, model_name: str)`**
  * **Finalidade**: Método principal de análise de imagens/vídeos. Salva o arquivo temporariamente, chama os processos de detecção, consolida resultados, remove duplicidades e desenha as caixas na imagem resultante.
* **`_run_single_model_inference(model_name: str, source: Any, is_video: bool)`**
  * **Finalidade**: Executa a predição da rede YOLO sobre a mídia. Limita o uso da GPU (Intel Arc via OpenVINO) e ajusta dinamicamente a confiança mínima do modelo para evitar falsos positivos (como limiar de `98%` para máquinas de obras e escavadeiras).
* **`_deduplicate_boxes(boxes: list)`**
  * **Finalidade**: Implementa um algoritmo customizado de Non-Maximum Suppression (NMS) baseado em IoU (Interseção sobre União). Remove bounding boxes de múltiplos modelos que detectaram exatamente o mesmo objeto na mesma posição.
* **`draw_boxes(img_path: Path, detections: list)`**
  * **Finalidade**: Desenha retângulos de detecção coloridos (Bounding Boxes) sobrepostos na imagem original e escreve os nomes das classes e confianças, salvando o arquivo resultante para exibição no celular.
* **`_process_video_frames(video_path: str, model)`**
  * **Finalidade**: Fallback de inferência para vídeos, dividindo a mídia em frames individuais sequenciais caso a função nativa de tracking do YOLO falhe.

---

## 4. Serviço de Mensagem Personalizada LLM (`app/services/ollama_message_service.py`)

A classe [OllamaMessageService](file:///c:/Users/aborr/Projeto%20TCC/YOLO26l-API/api-tcc/app/services/ollama_message_service.py) é responsável pela interface da API com o modelo de inteligência artificial local Ollama para gerar resumos de conformidade naturais em português.

* **`is_available()`**
  * **Finalidade**: Efetua uma chamada de teste rápida à API do Ollama e valida se o processo local está em execução na porta `11434` e com o modelo carregado.
* **`generate_personalized_message(analysis_result: dict, analysis_model: str)`**
  * **Finalidade**: Envia o resumo estruturado de detecções e inconformidades ao Ollama e retorna a descrição contextual gerada.
* **`_build_prompt(analysis_result: dict, requested_model: str)`**
  * **Finalidade**: Constrói a estrutura lógica do prompt de engenharia para o LLM instruindo-o a assumir a persona de um auditor de conformidade de segurança e produzir uma frase técnica única em português.
* **Pós-processador de Mensagem (Limpeza)**:
  * Um conjunto de expressões regulares limpa sequências de escape ANSI, remove termos técnicos do sistema do texto resultante e corta qualquer sufixo duplicado gerado pelo LLM.

---

## 5. Serviço de Conformidade (`app/services/compliance_service.py`)

A classe [ComplianceService](file:///c:/Users/aborr/Projeto%20TCC/YOLO26l-API/api-tcc/app/services/compliance_service.py) opera o motor de regras que classifica se o ambiente analisado está de acordo com as normas de segurança do trabalho baseando-se nas detecções do YOLO.

* **`evaluate_compliance(detections: list)`**
  * **Finalidade**: Analisa a lista de objetos encontrados e executa regras de conformidade estritas:
    * Se `sem_colete_de_seguranca` ou `sem_veste_de_segurana` forem detectados, classifica a cena como `NÃO CONFORME` e emite o alerta.
    * Se `sem_mascara` ou `culos_sem_culos` (óculos faltando) forem detectados perto de pessoas, emite os alertas correspondentes de EPI.
    * Se nenhum item fora de conformidade for encontrado, a cena recebe o status `CONFORME`.

---

## 6. Configuração do Sistema (`config/settings.py`)

A classe [Settings](file:///c:/Users/aborr/Projeto%20TCC/YOLO26l-API/api-tcc/config/settings.py) herda de `BaseSettings` do Pydantic. Ela lê as variáveis do arquivo `.env` de forma fortemente tipada e disponibiliza parâmetros como hosts, portas, caminhos de arquivo, chaves secretas de tokens JWT, e os limites globais de concorrência e DDoS da API.
