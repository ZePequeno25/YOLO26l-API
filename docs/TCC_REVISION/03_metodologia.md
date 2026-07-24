# 3 METODOLOGIA

Para estruturar a execução deste trabalho de pesquisa e desenvolvimento de forma científica e reprodutível, a metodologia foi organizada sob o formato de um pipeline de execução sequencial e interdependente. Este pipeline descreve cada etapa da pesquisa, desde a revisão conceitual inicial até a validação experimental de campo por meio de métricas estatísticas formais.

A Figura 3.1 apresenta graficamente as etapas que compõem o pipeline metodológico do projeto:

```text
[Etapa 1: Levantamento Bibliográfico]
                 |
                 v
[Etapa 2: Preparação e Análise do Dataset]
                 |
                 v
[Etapa 3: Treinamento do Modelo YOLO]
                 |
                 v
[Etapa 4: Desenvolvimento da API RESTful Backend]
                 |
                 v
[Etapa 5: Desenvolvimento do Aplicativo Android]
                 |
                 v
[Etapa 6: Integração entre os Componentes]
                 |
                 v
[Etapa 7: Testes e Execução Controlada]
                 |
                 v
[Etapa 8: Avaliação dos Resultados (Métricas Estatísticas)]
```

---

## 3.1 Levantamento Bibliográfico
A fase inicial da pesquisa compreendeu um mapeamento sistemático da literatura científica nacional e internacional focada em algoritmos de detecção de objetos em tempo real (especialmente a família YOLO) e suas aplicações em inspeções de conformidade de segurança e qualidade industrial. A busca concentrou-se em bases acadêmicas como IEEE Xplore, Google Scholar, arXiv e Europe PMC. Os termos indexadores utilizados foram *"YOLO construction safety"*, *"computer vision PPE detection"* e *"inspeção de conformidade visão computacional"*. Os artigos selecionados serviram de fundamentação para a modelagem da rede neural e para o desenho do pipeline de inferência de baixo custo de processamento.

## 3.2 Preparação e Organização dos Dados (Dataset)
A qualidade de inferência de uma rede neural supervisionada é diretamente proporcional à qualidade dos dados utilizados no treinamento. O dataset deste projeto foi estruturado a partir da coleta de imagens digitais contendo objetos específicos do cenário de testes em diferentes condições de iluminação e ângulos. 

O dataset foi processado por meio da plataforma Roboflow Universe, que viabilizou:
- A anotação manual das imagens com caixas delimitadoras (*bounding boxes*);
- A rotulagem rigorosa das classes de interesse;
- A divisão estratificada dos dados nos conjuntos tradicionais de Treinamento (*Train* - 70%), Validação (*Valid* - 20%) e Teste (*Test* - 10%).

Para aumentar a diversidade do dataset e mitigar problemas de sobreajuste (*overfitting*), aplicaram-se técnicas de aumento de dados (*data augmentation*), incluindo rotações aleatórias de imagens, ajustes na escala de brilho e inserção artificial de ruídos gaussianos. O dataset final foi exportado no formato YOLO, contendo arquivos de imagem e seus respectivos arquivos de anotação de coordenadas normativas `.txt`.

## 3.3 Treinamento do Modelo YOLO
O treinamento da rede neural YOLO utilizou a biblioteca oficial Ultralytics. O processo foi conduzido de duas formas:
1. **Treinamento Local:** Conduzido no hardware de desenvolvimento, utilizando o driver Intel XPU com aceleração gráfica Intel Arc B570 para avaliar a eficiência de treinamento em hardware dedicado alternativo.
2. **Treinamento em Nuvem:** Executado de forma paralela em notebooks estruturados no Google Colab, com aceleração por meio de GPUs NVIDIA T4, otimizando o tempo de processamento das épocas de treinamento.

O modelo base adotado foi o YOLO11s (Ultralytics, 2026), por representar um equilíbrio adequado entre velocidade de inferência e capacidade de aprendizado em classes compactas. O modelo foi treinado ao longo de 100 épocas (*epochs*), utilizando algoritmo de otimização SGD com taxa de aprendizado inicial ($\eta$) de 0,01. O modelo treinado final (`best.pt`) foi salvo e exportado para formatos otimizados (como o OpenVINO IR) para integração imediata ao motor de inferência do backend.

## 3.4 Desenvolvimento da API Backend
A API RESTful backend foi desenvolvida utilizando a linguagem Python 3.10+ e o framework assíncrono FastAPI. A API desempenha a função de microsserviço de borda responsável por expor endpoints HTTP protegidos, receber arquivos de imagens ou vídeos enviados pela aplicação móvel, processar a inferência do YOLO em lote ou stream, e gerir a autenticação.

Para a otimização de processamento de vídeos na API, implementaram-se duas técnicas principais discutidas na fundamentação teórica:
- **Vid Stride:** A análise de vídeos curtos (máximo 30 segundos) foi configurada para analisar frames intercalados (`VIDEO_INFERENCE_STRIDE = 2`), reduzindo a latência da API pela metade e evitando a ocorrência de timeouts (HTTP 524) sob conexões HTTP lentas;
- **YOLO Stream:** O modelo YOLO foi configurado com o parâmetro `stream=True` no pipeline de rastreamento (`model.track`), processando os frames de forma iterativa via geradores, o que impede a alocação volumosa de tensores na RAM e garante a estabilidade do sistema sob condições de concorrência.

Adicionalmente, com foco em ambientes reais e cenários de alta concorrência e escalabilidade, integraram-se três novas camadas arquiteturais à API:
1. **Inferência de Vídeo em Tempo Real via Server-Sent Events (SSE):** Para habilitar o processamento de "lives" e fluxos contínuos de câmera (ex: links RTSP ou webcams) sem sobrecarregar a memória, implementou-se o endpoint `GET /detection/stream`. O processamento realiza a decodificação frame a frame na memória volátil (NumPy arrays) utilizando a biblioteca OpenCV, eliminando completamente a gravação de arquivos temporários em disco SSD. A comunicação com o aplicativo móvel ocorre por meio de Server-Sent Events (SSE), que envia blocos de dados estruturados em JSON contendo as coordenadas das detecções atualizadas a cada intervalo de quadros definido por `frame_stride`.
2. **Controle de Concorrência Estilo Java (Fila Delimitada e Semáforo):** Para proteger o sistema contra exaustão de hardware (RAM/VRAM), estruturou-se um semáforo de inferências assíncronas (`MAX_CONCURRENT_INFERENCES = 2`), garantindo que apenas um número controlado de execuções YOLO ocorra simultaneamente nas GPUs Intel Arc. Inspirado no comportamento do `ThreadPoolExecutor` do Java, implementou-se uma fila delimitada (`MAX_PENDING_JOBS = 10000`) para tarefas assíncronas (`ASYNC_QUEUE_MODE`). Se o total de requisições pendentes na fila exceder esse limite, a API ativa imediatamente um mecanismo de contrapressão (*backpressure*), rejeitando novos uploads com código HTTP `429 Too Many Requests` para evitar colapsos por sobrecarga.
3. **Limpeza LRU e Descarte Ativo de Memória:** O armazenamento interno em memória dos laudos processados foi limitado a `JOB_RETENTION_LIMIT = 1000`. Um algoritmo de limpeza estilo LRU (*Least Recently Used*) remove os laudos concluídos ou falhados mais antigos quando novos entram no dicionário de jobs. Para mitigar o comportamento de acúmulo de fragmentação de memória típico em pipelines de visão computacional em Python, a API invoca explicitamente o Garbage Collector (`gc.collect()`) imediatamente após o encerramento do ciclo de vida de cada arquivo ou vídeo pesado.

## 3.5 Desenvolvimento do Aplicativo Android
O aplicativo cliente móvel foi desenvolvido na linguagem Kotlin utilizando o ambiente integrado Android Studio. O app fornece a interface para que o usuário final interaja com o sistema. Ele foi implementado para operar de acordo com o seguinte fluxo:
1. **Autenticação:** Integração com o SDK do Firebase Authentication para autenticação *passwordless* ou por e-mail/Google.
2. **Captura Multimídia:** Utilização das APIs oficiais de câmera do Android para capturar fotos e gravar vídeos de curta duração no formato MP4.
3. **Comunicação:** O aplicativo realiza chamadas seguras à API RESTful utilizando a biblioteca OkHttp, enviando o arquivo capturado via requisições *multipart/form-data* junto ao Bearer JWT Token inserido dinamicamente no cabeçalho HTTP `Authorization`.

## 3.6 Integração entre os Componentes
A integração sistêmica consiste no fluxo unificado de dados entre o aplicativo cliente Android, os servidores do Google Firebase (para controle de usuários e armazenamento do banco Firestore) e a API backend local. Para garantir a segurança nas chamadas de integração, implementou-se uma cadeia de autenticação JWT de duas camadas. 

O aplicativo Android primeiro valida a identidade do usuário no Firebase; o token de identidade resultante é enviado para o endpoint `/auth/token` da API backend, que verifica sua legitimidade junto ao Firebase Admin SDK e retorna um token de acesso de curta duração (24 horas) assinado com segredo simétrico HS256 (`API_JWT_SECRET`). Esse token local é então usado para autorizar as chamadas aos endpoints de inferência `/detection/analyze`.

## 3.7 Execução dos Testes Controlados
A fase de testes consistiu na submissão de diferentes imagens e vídeos reais contendo cenários de inspeção de conformidade de segurança e qualidade. Os arquivos foram gravados no canteiro de obras e em ambientes de controle e enviados através do aplicativo móvel sob cenários estruturados de teste:
- Cenários com iluminação adequada e alta resolução;
- Cenários sob baixa iluminação ou presença de poeira e obstruções parciais;
- Cenários de conformidade (onde todos os objetos regulamentares estavam presentes);
- Cenários de não conformidade (onde elementos obrigatórios de sinalização ou segurança física estavam ausentes, exigindo o alerta contextual do sistema).

## 3.8 Avaliação Lógica e Métricas Estatísticas do Sistema
Diferente da análise de tempo de resposta da API (que foge do escopo do estudo e foi excluída do pipeline de validação), o sistema foi avaliado com foco em sua capacidade de identificar de forma correta e confiável as classes de objetos nos cenários reais. A avaliação foi baseada no cálculo das seguintes métricas estatísticas clássicas de visão computacional:

1. **Verdadeiros Positivos ($VP$):** Quantidade de objetos reais detectados corretamente pelo sistema.
2. **Falsos Positivos ($FP$):** Quantidade de detecções reportadas pelo sistema que não correspondiam a nenhum objeto real ou correspondiam a classes incorretas.
3. **Falsos Negativos ($FN$):** Quantidade de objetos reais presentes na imagem que o sistema não conseguiu detectar.
4. **Precisão ($P$):** Mede a confiabilidade das detecções positivas efetuadas pelo modelo, definida pela fórmula:
$$P = \frac{VP}{VP + FP}$$

5. **Revocação (*Recall* - $R$):** Mede a capacidade do modelo de encontrar todos os objetos reais presentes no cenário, calculada por:
$$R = \frac{VP}{VP + FN}$$

6. **F1-Score:** Representa a média harmônica entre precisão e revocação, fornecendo uma métrica unificada de desempenho balanceado:
$$F1 = 2 \times \frac{P \times R}{P + R}$$

7. **mAP (mean Average Precision):** Média da precisão sob diferentes limites de confiança e níveis de recall, calculada sob a curva de precisão-revocação para o conjunto de testes.

Adicionalmente, avaliou-se qualitativamente a assertividade lógica do motor contextual no envio de avisos detalhados em português em caso de ausência ou desconformidade dos elementos na cena analisada.
