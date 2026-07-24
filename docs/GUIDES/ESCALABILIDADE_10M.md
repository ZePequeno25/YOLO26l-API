# Arquitetura de Alta Escalabilidade — 10 Milhões de Recomendações por Minuto

Este guia descreve os princípios arquiteturais e a infraestrutura necessária para implantar a API YOLO em nível de produção corporativa, suportando uma carga contínua de **10 milhões de requisições por minuto** (equivalente a aproximadamente **166.666 requisições por segundo (RPS)**).

---

## 1. O Desafio Físico da Inferência de Visão Computacional

A execução de modelos de Deep Learning (como o YOLOv8) envolve bilhões de operações matemáticas de ponto flutuante por frame. 
* Mesmo com otimizações OpenVINO em uma GPU dedicada de alto desempenho (latência média de ~15ms por modelo executado), um único hardware físico consegue processar no máximo **50 a 100 inferências por segundo**.
* Processar 166.000 RPS de forma síncrona (esperando a inferência terminar antes de responder ao cliente) exigiria mais de **1.600 GPUs de última geração rodando em paralelo** de forma síncrona, o que é inviável, gera gargalos de rede e estoura timeouts de proxies/load balancers.

### A Solução: Arquitetura Orientada a Eventos (Ingress/Queue Pattern)
Para resolver esse problema, a API separa a **recepção da requisição** (Ingress) do **processamento neural** (Inference Worker):

```
                                    ┌───────────────────────┐
                                    │   Internet / Clientes │
                                    └───────────┬───────────┘
                                                │ ~166k RPS
                                                ▼
                                    ┌───────────────────────┐
                                    │    Load Balancer      │
                                    │  (NGINX / Cloudflare) │
                                    └───────────┬───────────┘
                                                │
                  ┌─────────────────────────────┼─────────────────────────────┐
                  ▼                             ▼                             ▼
       ┌────────────────────┐        ┌────────────────────┐        ┌────────────────────┐
       │   API Gateway 1    │        │   API Gateway 2    │        │   API Gateway N    │
       │ (FastAPI Ingress)  │        │ (FastAPI Ingress)  │        │ (FastAPI Ingress)  │
       └──────────┬─────────┘        └──────────┬─────────┘        └──────────┬─────────┘
                  │                             │                             │
                  │ Salva Mídia                 │ Grava Job                   │ Publica Evento
                  ▼                             ▼                             ▼
       ┌────────────────────┐        ┌────────────────────┐        ┌────────────────────┐
       │   Object Storage   │        │  Redis / Firestore │        │    Apache Kafka    │
       │ (MinIO / AWS S3)   │        │ (Cache de Status)  │        │  (Mensageria/Fila) │
       └────────────────────┘        └────────────────────┘        └──────────┬─────────┘
                                                                              │
                  ┌─────────────────────────────┬─────────────────────────────┘
                  ▼                             ▼
       ┌────────────────────┐        ┌────────────────────┐
       │  Inference Worker 1│        │  Inference Worker M│
       │   (YOLO + GPU)     │        │   (YOLO + GPU)     │
       └────────────────────┘        └────────────────────┘
```

---

## 2. Detalhamento dos Componentes

### 1. Camada de Ingress (API Gateway)
* **Função**: Receber os uploads de imagens/vídeos dos dispositivos móveis, validar a assinatura da requisição, salvar a mídia no Storage e enfileirar o Job.
* **Comportamento**: Utiliza o modo assíncrono (`ASYNC_QUEUE_MODE=True`). A resposta é imediata (`202 Accepted` contendo um `job_id`) e leva **menos de 5ms**.
* **Tecnologia**: Escalonada horizontalmente usando **FastAPI + Uvicorn** dentro de containers Docker.

### 2. Mensageria e Fila de Mensagens (Message Broker)
* **Função**: Armazenar temporariamente os metadados das imagens a serem analisadas e distribuir a carga de forma justa entre os nós de processamento.
* **Tecnologia**: **Apache Kafka** ou **RabbitMQ**. O Kafka é altamente recomendado para esse volume devido ao seu particionamento nativo de logs de escrita, permitindo persistir milhões de eventos por segundo de forma distribuída.

### 3. Armazenamento de Mídia (Object Storage)
* **Função**: Guardar as imagens/vídeos recebidos e os resultados processados anotados.
* **Tecnologia**: **MinIO** (on-premise de alta performance) ou **AWS S3**. Os API Gateways geram URLs pré-assinadas (Presigned URLs) para que os trabalhadores façam download das imagens diretamente por rede local de alta velocidade.

### 4. Camada de Processamento (Inference Workers)
* **Função**: Consumir os caminhos de mídias da fila do Kafka, baixar o arquivo do Object Storage, rodar as redes YOLO e atualizar o status do Job no banco de dados.
* **Tecnologia**: Nós Kubernetes (K8s) dedicados equipados com GPUs Intel Arc / NVIDIA. O auto-scaling desses workers é gerenciado pelo **KEDA** (Kubernetes Event-driven Autoscaling), que escala a quantidade de containers contendo a GPU YOLO de acordo com o tamanho da fila pendente no Kafka.

### 5. Banco de Dados e Cache de Status (Data Store)
* **Função**: Armazenar os status dos jobs (`PENDENTE`, `PROCESSANDO`, `CONCLUIDO`) e o resultado das caixas delimitadoras (`boxes`) para que o aplicativo mobile consulte.
* **Tecnologia**: **Redis Cluster** em memória para respostas rápidas (tempo de leitura < 1ms) das consultas de status dos jobs pelos clientes móveis.

---

## 3. Otimizações de Desempenho Críticas

### 🤫 Silenciamento de Logs (`DISABLE_LOGS=True`)
Em testes de estresse com milhões de requisições, a gravação de logs em disco gera um gargalo físico conhecido como **Disk I/O Wait**. Ao definir `DISABLE_LOGS=True` no arquivo `.env`:
* Silenciamos todas as chamadas de logs da aplicação (`logging.disable(logging.CRITICAL)`).
* O Uvicorn roda no nível `critical`, imprimindo apenas falhas totais do servidor.
* Isso poupa a CPU e o disco de bilhões de gravações de texto por minuto, aumentando a taxa de requisições em até **40%**.

### ⚡ Caching de Autenticação (Redis)
O Firebase Auth possui limites de requisições por segundo (rate limiting) para validação de ID Tokens. Sob uma carga de 10 milhões de requisições por minuto, o serviço do Firebase bloquearia a API.
* **Solução**: Assim que um token JWT é validado pela primeira vez, os metadados do usuário (ex: `uid`, `email`) são armazenados em um cache local no Redis com tempo de expiração curto (ex: 5 a 15 minutos).
* As requisições seguintes utilizam a leitura em memória do Redis para autenticar, reduzindo o tráfego externo para o Firebase a quase zero.

### 📦 Agrupamento de Inferências (Inference Batching)
Os workers não devem rodar inferência imagem por imagem. O runtime do OpenVINO e as GPUs são otimizadas para processar múltiplos dados simultaneamente em formato de matrizes:
* **Dynamic Batching**: O worker acumula requisições da fila por uma janela curtíssima (ex: 5ms ou até atingir 16 ou 32 imagens) e envia o lote de uma única vez para a GPU (`batch=16` ou `batch=32`).
* Isso aumenta a eficiência do paralelismo do silício da GPU, aumentando o rendimento de inferências em até **300%**.
