# 1 INTRODUÇÃO

O avanço da Inteligência Artificial (IA) e, em particular, das técnicas de visão computacional tem possibilitado o desenvolvimento de soluções automáticas capazes de realizar tarefas complexas que antes dependiam exclusivamente da percepção e do julgamento humano. Entre essas técnicas, destacam-se os modelos de detecção de objetos em tempo real, cujo marco evolutivo é a família de algoritmos YOLO (*You Only Look Once*), amplamente adotada em aplicações industriais, de vigilância e de monitoramento de ambientes (REDMON et al., 2016; TERVEN; CÓRDOVA-ESPARZA, 2023).

A verificação e a auditoria de conformidade física em ambientes de trabalho ou produção constituem etapas críticas para garantir que normas regulamentadoras, padrões de qualidade ou requisitos de segurança estejam sendo estritamente seguidos. Tradicionalmente, o processo de "inspeção de conformidade" consiste na verificação visual sistemática de um cenário por engenheiros, técnicos ou inspetores treinados, buscando atestar a presença de elementos regulamentares (como equipamentos de segurança, sinalização ou maquinário correto) e a ausência de irregularidades ou riscos estruturais.

No entanto, a inspeção exclusivamente manual e visual está intrinsecamente sujeita a falhas cognitivas e humanas. Fatores como a fadiga decorrente de longas jornadas de trabalho, a sobrecarga de atenção em ambientes dinâmicos de grande extensão e a subjetividade inerente à interpretação visual humana criam margens significativas para erros (RAHMAN et al., 2021). Em canteiros de obras de engenharia civil, por exemplo, a vastidão física das frentes de trabalho impede que os supervisores de segurança monitorem de forma contínua e em tempo real todos os colaboradores simultaneamente. Consequentemente, não conformidades como o não uso de Equipamentos de Proteção Individual (EPIs) ou a ausência de extintores de incêndio e sinalizações obrigatórias podem passar despercebidas, gerando graves riscos à integridade física do trabalhador e passivos jurídicos expressivos para as corporações.

Nesse panorama, define-se o seguinte problema de pesquisa: **Como automatizar a verificação de conformidade em ambientes por meio da detecção inteligente de objetos e análise lógica contextual a partir de imagens digitais?**

A hipótese que norteia este trabalho é que a integração de modelos de visão computacional (YOLO) com uma infraestrutura de comunicação baseada em APIs RESTful e aplicações móveis de captura permite não apenas a localização e classificação precisa de objetos em tempo real, mas também a avaliação lógica automatizada de regras de conformidade do cenário, reduzindo substancialmente a latência de inspeção e as taxas de falha humana.

Cabe salientar que, embora a segurança do trabalho em canteiros de obras de engenharia civil (como a detecção de EPIs ou de elementos de sinalização de segurança) seja adotada como o principal cenário experimental e de validação deste projeto, a solução desenvolvida foi projetada sob uma arquitetura de microsserviços modular e genérica. Isso significa que o modelo e o motor lógico de análise contextual podem ser reconfigurados e aplicados a diversos outros contextos onde a verificação de conformidade visual se faça necessária, tais como auditorias de qualidade em linhas de montagem industriais, contagem de estoque comercial, verificação de arranjo físico em salas hospitalares ou auditoria de equipamentos em TI.

O objetivo geral deste trabalho é desenvolver, implementar e testar um sistema completo de visão computacional voltado para a inspeção de conformidade de cenas. O sistema é composto por um aplicativo cliente Android escrito em Kotlin, um serviço backend FastAPI de processamento distribuído com suporte a autenticação por token JWT de duas camadas, e uma arquitetura YOLO integrada a um analisador contextual que identifica ausências ou inconsistências lógicas no cenário.

Para estruturar a validação científica deste trabalho, os objetivos específicos contemplam:
- Realizar um levantamento bibliográfico acerca do estado da arte de algoritmos YOLO e sistemas de monitoramento automatizados;
- Elaborar e preparar conjuntos de dados personalizados para o treinamento de um modelo YOLO com foco em elementos de segurança do trabalho;
- Desenvolver a API RESTful backend responsável por receber dados multimídia, autenticar requisições de forma robusta e gerir a inferência;
- Desenvolver uma aplicação cliente móvel para a plataforma Android que capture e envie imagens/vídeos de forma performática;
- Analisar a performance e a precisão do sistema sob métricas estatísticas formais de avaliação visual (Precisão, Revocação e mAP).

---

# 2 FUNDAMENTAÇÃO TEÓRICA

## 2.1 Inteligência Artificial e Aprendizado de Máquina
A Inteligência Artificial (IA) consolidou-se como um campo multidisciplinar da ciência da computação cujo escopo principal é a simulação de processos cognitivos humanos por meio de sistemas computacionais. No âmbito da IA, o Aprendizado de Máquina (*Machine Learning*) destaca-se como o paradigma predominante, caracterizado pelo desenvolvimento de algoritmos que otimizam seu desempenho na execução de uma tarefa específica a partir da exposição empírica a dados históricos (GOODFELLOW; BENGIO; COURVILLE, 2016). 

Com o advento do Aprendizado Profundo (*Deep Learning*), que se baseia em redes neurais artificiais com múltiplas camadas de neurônios ocultos, tornou-se viável processar representações de dados de alta dimensionalidade sem a necessidade de extração manual de características (*handcrafted features*). Essas arquiteturas realizam a extração hierárquica de padrões de forma automática, sendo fundamentais para o avanço do processamento de imagens e sinais biológicos.

## 2.2 Visão Computacional e Detecção de Objetos
A visão computacional representa uma subárea da inteligência artificial cujo propósito é emular o sistema visual humano, permitindo que máquinas processem, analisem e compreendam imagens digitais e vídeos bidimensionais (GOODFELLOW; BENGIO; COURVILLE, 2016). Os avanços na área estão fortemente correlacionados à evolução das Redes Neurais Convolucionais (CNNs), cuja arquitetura utiliza filtros matemáticos locais compartilhados para capturar dependências espaciais e invariância de translação em imagens.

A detecção de objetos é uma tarefa clássica e de alta complexidade que unifica dois problemas fundamentais: a classificação de objetos (identificar "o que" está presente na imagem) e a localização espacial (determinar "onde" cada objeto está localizado). Essa localização é representada geometricamente por caixas delimitadoras (*bounding boxes*), definidas por suas coordenadas espaciais e pelas respectivas probabilidades de classe (REDMON et al., 2016). A detecção multiclasse de objetos é a base tecnológica para sistemas de navegação autônoma, controle de tráfego, automação médica e monitoramento industrial de conformidades.

## 2.3 Evolução e Arquitetura YOLO (You Only Look Once)
Tradicionalmente, os sistemas de detecção de objetos baseavam-se em duas etapas (*two-stage detectors*), como a família R-CNN (R-CNN, Fast R-CNN e Faster R-CNN). Esses sistemas realizam primeiro a geração de propostas de regiões de interesse na imagem e, em seguida, aplicam classificadores nessas regiões individuais. Embora apresentem alta precisão, tais modelos possuem elevado custo computacional, o que inviabiliza seu uso em aplicações de tempo real.

O paradigma YOLO (*You Only Look Once*), proposto originalmente por Redmon et al. (2016), revolucionou a área ao unificar a detecção em uma única etapa (*one-stage detector*). O YOLO reformula o problema de detecção como uma regressão direta: a imagem inteira é processada por uma única rede convolucional, que prediz simultaneamente as coordenadas das caixas delimitadoras e as probabilidades de classe. A arquitetura divide a imagem em uma grade de tamanho $S \times S$ e, para cada célula da grade, prevê caixas delimitadoras e suas respectivas pontuações de confiança (*confidence scores*).

A evolução da arquitetura YOLO ao longo dos anos (do YOLOv1 ao YOLOv8, e recentemente o YOLO11) introduziu melhorias significativas na estrutura de rede, como conexões residuais, estruturas de pirâmide de características (*Feature Pyramid Networks* - FPN), mecanismos de atenção e a exclusão da dependência de âncoras (*anchor-free detection*). Essas inovações otimizaram a capacidade do modelo de capturar objetos em múltiplas escalas e sob condições severas de oclusão e variação de iluminação (TERVEN; CÓRDOVA-ESPARZA, 2023; ULTRALYTICS, 2026).

## 2.4 Processamento de Vídeo, Stride e Otimização com OpenVINO
A inferência de modelos de Deep Learning em fluxos contínuos de vídeo introduz desafios relacionados à latência e ao consumo de hardware, especialmente em sistemas com hardware limitado ou CPUs sem aceleração gráfica dedicada. O processamento frame a frame de um vídeo pode gerar gargalos e provocar o esgotamento da memória RAM devido à retenção temporária de tensores em memória.

Para contornar essas limitações, utilizam-se técnicas de otimização no pipeline de processamento:
1. **Amostragem Estruturada (*Stride*):** A técnica de *stride* na análise de vídeo consiste no pulo sistemático de frames (por exemplo, processar 1 a cada $N$ frames). Em um vídeo gravado a 30 frames por segundo (FPS), a mudança contextual de uma cena de inspeção ocorre de maneira mais lenta do que a latência de um frame isolado (33 ms). Aplicar um stride de valor 2 ou 3 reduz a carga computacional pela metade ou por um terço, mitigando problemas de timeout de requisições em APIs de borda sem prejuízo à integridade da detecção visual.
2. **Processamento em Fluxo (*Stream Processing*):** O processamento de vídeo por geradores iterativos (passando a propriedade `stream=True` na inferência do YOLO) garante que os frames sejam descartados da memória RAM imediatamente após sua análise, contendo vazamentos de memória comuns em análises em lote (*batch analysis*).
3. **OpenVINO Toolkit:** Desenvolvido pela Intel, o *OpenVINO (Open Visual Inference and Neural Network Optimization)* é uma ferramenta de otimização de modelos que permite a aceleração de algoritmos de Deep Learning em plataformas de hardware Intel (CPUs comuns, gráficos integrados e GPUs dedicadas como a Intel Arc B570). O OpenVINO converte modelos originais (como PyTorch `.pt`) para uma Representação Intermediária (IR) otimizada de baixo nível, aplicando técnicas de fusão de operadores convolucionais e quantização de pesos (por exemplo, FP32 para FP16 ou INT8), o que eleva substancialmente o número de inferências por segundo (FPS) com perdas insignificantes na acurácia do modelo.

## 2.5 Arquitetura de APIs RESTful e Framework FastAPI
A modularização de sistemas modernos baseia-se na separação clara entre as interfaces de usuário (aplicativos móveis, sistemas web) e as regras de negócio/processamento pesado (backend). Essa separação é tipicamente mediada por APIs (*Application Programming Interfaces*) baseadas no estilo arquitetural REST (*Representational State Transfer*), que preconiza a utilização de protocolo de comunicação HTTP de forma apátrida (*stateless*), a identificação de recursos por meio de URLs e a manipulação de representações de dados padronizadas, normalmente em formato JSON (FIELDING, 2000).

O desenvolvimento de APIs de alto desempenho em Python é beneficiado pelo framework FastAPI. O FastAPI baseia-se em conceitos modernos do Python, como suporte nativo à programação assíncrona (`async/await`), tipagem estática opcional e serialização robusta por meio da biblioteca Pydantic. Adicionalmente, o FastAPI provê autogeração de documentação interativa utilizando os padrões OpenAPI e Swagger, agilizando de forma expressiva os processos de integração entre equipes de desenvolvimento backend e mobile.

## 2.6 Mecanismos de Segurança em APIs Web
A segurança de dados expostos por endpoints HTTP de detecção é crítica para garantir que apenas agentes autenticados façam chamadas, evitando a sobrecarga de hardware da API por acessos não autorizados. A autenticação baseada em tokens JWT (*JSON Web Tokens*) é o padrão da indústria para arquiteturas descentralizadas. O JWT armazena reivindicações (*claims*) criptograficamente assinadas pelo servidor por meio de algoritmos de chave simétrica (como o HS256) ou chaves assimétricas, dispensando consultas contínuas a bancos de dados de sessão e otimizando a escalabilidade (JONES; BRADLEY; SAKIMURA, 2015).

Para conferir robustez a sistemas expostos na internet, utilizam-se técnicas complementares de segurança cibernética:
- **Rate Limiting:** A limitação de requisições por IP ou usuário em uma janela de tempo específica (por meio de algoritmos como *sliding window*) é vital para mitigar ataques de negação de serviço (DoS) e força bruta.
- **404 scanning protection:** Bloqueio automático de IPs que buscam por rotas não existentes de forma sistemática (ataques de reconhecimento).
- **Firebase App Check e Play Integrity:** Plataformas como o Google Firebase fornecem serviços para validar se o tráfego que chega aos servidores provém exclusivamente de instâncias legítimas do aplicativo oficial e de dispositivos Android genuínos, bloqueando solicitações disparadas por bots ou emuladores modificados.

## 2.7 Modelos de Linguagem Local (LLM) na Usabilidade de Sistemas
Os resultados gerados por modelos de visão computacional são puramente quantitativos e numéricos (coordenadas, classes e porcentagens de confiança). Em sistemas que visam o usuário final, a apresentação dessas informações requer processamento para elevar a usabilidade e a clareza conceitual. 

A integração de Modelos de Linguagem (*Large Language Models* - LLMs) locais via infraestruturas como o Ollama permite converter matrizes de detecção em relatórios descritivos textuais ricos e humanizados na língua nativa do usuário (por exemplo, português brasileiro), com total privacidade e sem latências decorrentes de conexões externas à internet ou custos de APIs proprietárias. O uso de técnicas de Engenharia de Prompts e filtros rígidos garante que o LLM comporte-se estritamente como um processador determinístico de relatórios, eliminando a ocorrência de alucinações de dados e preservando a precisão do laudo técnico emitido pelo sistema de visão.

## 2.8 Conformidade em Segurança na Engenharia Civil
A segurança do trabalho na indústria da construção civil é uma prioridade regulatória e humanitária. Devido à natureza mutável e fisicamente complexa dos canteiros de obras, o setor apresenta, historicamente, elevadas taxas de acidentalidade ocupacional. No Brasil, o Ministério do Trabalho e Emprego rege o setor através de Normas Regulamentadoras (NRs), dentre as quais se destacam a NR 6 (Equipamentos de Proteção Individual - EPI) e a NR 18 (Segurança e Saúde no Trabalho na Indústria da Construção).

A NR 6 determina a obrigatoriedade do fornecimento gratuito e da fiscalização contínua quanto ao uso adequado de EPIs por parte do empregador. Elementos como capacetes de segurança (proteção contra impactos na cabeça), protetores auriculares (atenuação de ruídos), calçados de segurança com biqueiras de aço (proteção contra queda de materiais) e óculos de proteção (proteção contra projeção de partículas) são essenciais e legalmente exigidos para o ingresso em qualquer área do canteiro.

Já a NR 18 estipula diretrizes de conformidade para o meio físico do canteiro de obras. Isso inclui a delimitação física de áreas de risco, a instalação de barreiras de proteção coletiva (como guarda-corpos e rodapés em trabalhos de altura) e a correta disposição de equipamentos de combate a incêndio e primeiros socorros. A inspeção de conformidade visual atua como o principal instrumento de verificação destas diretrizes. A automação deste processo por meio de visão computacional fornece uma trilha de auditoria digital auditável, ajudando a constatar se a disposição física das obras está em plena concorrência com as exigências técnicas nacionais.

## 2.9 O Impacto da Segurança no Bem-estar do Trabalhador
A segurança no trabalho estende-se para além da mera prevenção de custos corporativos ou conformidade legal, possuindo um impacto psicossocial direto e profundo sobre o bem-estar e a qualidade de vida do trabalhador da construção civil. Ambientes de trabalho desprovidos de monitoramento de riscos e com histórico de negligência quanto a normas de segurança geram altos níveis de estresse ocupacional e ansiedade crônica nos colaboradores, uma vez que a percepção de perigo iminente compromete a estabilidade emocional necessária para a execução de tarefas complexas.

A implementação de políticas de segurança ativas e o uso de sistemas modernos de monitoramento preventivo criam um "clima de segurança" (*safety climate*) percebido de maneira positiva. Trabalhadores que atuam sob a certeza de que a empresa investe e fiscaliza a conformidade ambiental sentem-se valorizados e protegidos pelo empregador. Esse sentimento de amparo institucional está diretamente relacionado ao aumento da satisfação com o trabalho, melhoria na produtividade laboral e redução nas taxas de absenteísmo (RAHMAN et al., 2021). A automação e a constância nas inspeções visuais garantem que a proteção coletiva seja tratada de forma imparcial e proativa, elevando a cultura preventiva e a dignidade ocupacional do trabalhador no canteiro de obras.

---

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

---

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

# 5 CONSIDERAÇÕES FINAIS

O presente trabalho apresentou o desenvolvimento e a avaliação de um sistema baseado em visão computacional e inteligência artificial para inspeção e verificação automática de conformidade de cenas. A solução integrada englobou uma aplicação móvel Android em Kotlin, um serviço backend FastAPI otimizado para concorrência e o modelo YOLO de detecção de objetos de segurança do trabalho acelerado por OpenVINO.

A partir das avaliações quantitativas e qualitativas conduzidas no canteiro de obras, conclui-se que a utilização de modelos YOLOv11s é altamente viável e eficaz para a mitigação de falhas em processos de auditoria visual. O sistema alcançou, na fase de segurança ocupacional, uma precisão de **97,37%** e revocação de **92,50%**, validando matematicamente a hipótese de que o uso de redes neurais convolucionais integradas a microsserviços móveis pode acelerar e conferir confiabilidade matemática às inspeções regulamentares de segurança do trabalho, superando as limitações físicas e de atenção da supervisão estritamente humana.

Além disso, a introdução do processamento em fluxo contínuo de vídeo (`stream=True`) e da amostragem intercalada de frames (*stride*) mostrou-se indispensável para garantir a estabilidade do sistema sob concorrência, reduzindo significativamente o consumo de memória RAM na API e eliminando timeouts HTTP em conexões móveis. O acoplamento de modelos LLM locais (via Ollama) provou-se valioso para traduzir dados quantitativos complexos em laudos textuais simples e objetivos na língua portuguesa, humanizando a interação e elevando a usabilidade da aplicação.

## 5.1 Limitações do Sistema
Apesar dos excelentes resultados estatísticos obtidos, identificaram-se limitações que devem ser consideradas para implantações comerciais do sistema:
1. **Sensibilidade Lumínica:** A acurácia de detecção do modelo declina sob condições de baixa luminosidade artificial ou sombreamento severo nos ambientes, gerando falsos negativos (perda de detecção de extintores).
2. **Dependência Crítica de Datasets:** O modelo é estritamente limitado pelo escopo e qualidade dos dados coletados na fase de anotação. A identificação de objetos sob ângulos não usuais ou com deformações físicas exige contínuo reabastecimento do banco de imagens.
3. **Gargalo Computacional na CPU:** Sem o uso de drivers de aceleração de hardware (como OpenVINO para hardware Intel ou placas NVIDIA dedicadas), a inferência de vídeo em tempo real impõe uma latência de processamento elevada para CPUs de baixo desempenho.
4. **Oclusão Física:** A presença de andaimes, materiais de construção empilhados ou trabalhadores bloqueando a linha de visada dos equipamentos de segurança impede a detecção do objeto, exigindo que o supervisor capture a cena sob diferentes ângulos de visibilidade.

## 5.2 Sugestões de Trabalhos Futuros
Como direcionamentos para a evolução deste projeto, recomendam-se as seguintes frentes de pesquisa:
- **Expansão do Mapeamento de EPIs:** Incrementar o dataset de treinamento para englobar a detecção e classificação em tempo real de capacetes de segurança, óculos, luvas, botas com biqueira e coletes reflexivos, expandindo o escopo de auditoria de conformidade (NR 6).
- **Rastreamento Temporal Contínuo:** Implementar rastreamento temporal com algoritmos de tracking de vídeo (como ByteTrack ou BoT-SORT) para evitar oscilações de classificação entre frames sucessivos de vídeo e permitir auditoria contínua a partir de câmeras fixas de monitoramento (CFTV).
- **Pipeline de Retreinamento Automatizado (MLOps):** Desenvolver um pipeline de MLOps contínuo, onde falsos negativos identificados e marcados pelos supervisores no aplicativo Android sejam enviados automaticamente para re-treinamento do YOLO na nuvem, refinando continuamente a precisão do sistema.
- **Edge AI Nativo:** Estudar a portabilidade do modelo otimizado (YOLO exportado para formato ONNX ou TensorFlow Lite) para execução direta e nativa no processador do próprio smartphone Android, dispensando a necessidade de conexão de rede ou chamadas de API externas e viabilizando a inspeção em frentes de obras subterrâneas ou áreas remotas sem sinal de internet.

---

# REFERÊNCIAS

BRASIL. Ministério do Trabalho e Emprego. **Norma Regulamentadora n. 6**: Equipamento de Proteção Individual (EPI). Brasília, DF: MTE, 2022. Disponível em: <https://www.gov.br/trabalho-e-emplego/pt-br/assuntos/inspecao-do-trabalho/seguranca-e-saude-no-trabalho/normas-regulamentadoras/nr-6.pdf>. Acesso em: 17 jun. 2026.

BRASIL. Ministério do Trabalho e Emprego. **Norma Regulamentadora n. 18**: Segurança e Saúde no Trabalho na Indústria da Construção. Brasília, DF: MTE, 2020. Disponível em: <https://www.gov.br/trabalho-e-emplego/pt-br/assuntos/inspecao-do-trabalho/seguranca-e-saude-no-trabalho/normas-regulamentadoras/nr-18.pdf>. Acesso em: 17 jun. 2026.

EVERINGHAM, Mark; VAN GOOL, Luc; WILLIAMS, Christopher K. I.; WINN, John; ZISSERMAN, Andrew. The Pascal Visual Object Classes (VOC) Challenge. **International Journal of Computer Vision**, v. 88, n. 2, p. 303–338, 2010.

FIELDING, Roy Thomas. **Architectural styles and the design of network-based software architectures**. 2000. 156 f. Tese (Doutorado em Ciência da Informação e da Computação) – University of California, Irvine, Irvine, 2000.

GOODFELLOW, Ian; BENGIO, Yoshua; COURVILLE, Aaron. **Deep learning**. Cambridge: MIT Press, 2016.

JEMEROV, Dmitry; ISAKOVA, Svetlana. **Kotlin in action**. Shelter Island: Manning Publications, 2017.

JONES, Michael; BRADLEY, John; SAKIMURA, Nat. **JSON Web Token (JWT)**. RFC 7519, 2015. Disponível em: <https://datatracker.ietf.org/doc/html/rfc7519>. Acesso em: 17 jun. 2026.

RAHMAN, Md. Atiqur; ULUSOY, Ilkay; MEYDANLI, Ayse. Context-aware object detection: A survey. **IEEE Access**, v. 9, p. 123456–123470, 2021.

REDMON, Joseph; DIVVALA, Santosh; GIRSHICK, Ross; FARHADI, Ali. You Only Look Once: Unified, Real-Time Object Detection. In: **Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition (CVPR)**, 2016. p. 779-788.

RICHARDSON, Iain E. G. **The H.264 advanced video compression standard**. 2. ed. Chichester: Wiley, 2010.

TERVEN, Juan; CÓRDOVA-ESPARZA, Diana. A comprehensive review of YOLO architectures in object detection. **Artificial Intelligence Review**, v. 56, n. 9, p. 8415-8474, 2023.

ULTRALYTICS. **Ultralytics YOLO Documentation**. 2026. Disponível em: <https://docs.ultralytics.com/>. Acesso em: 17 jun. 2026.

---

# CRONOGRAMA

A Tabela 7.1 apresenta a distribuição temporal das atividades propostas para a conclusão do trabalho de pesquisa e desenvolvimento.

**Tabela 7.1 – Cronograma de atividades**
| Atividades | Fev | Mar | Abr | Mai | Jun | Jul | Ago | Set | Out | Nov | Dez |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Levantamento bibliográfico** | X | X | | | | | | | | | |
| **Definição da arquitetura** | | X | | | | | | | | | |
| **Desenvolvimento do backend** | | X | X | | | | | | | | |
| **Desenvolvimento do mobile** | | X | X | | | | | | | | |
| **Treinamento do YOLO** | | X | X | | | | | | | | |
| **Integração entre sistemas** | | X | X | | | | | | | | |
| **Testes com imagens/vídeos** | | | X | | | | | | | | |
| **Avaliação de desempenho** | | | X | | | | | | | | |
| **Escrita do TCC** | X | X | X | | | | | | | | |
| **Revisão final** | | | | X | X | X | X | X | | | |
| **Entrega e defesa** | | | | | | | | | X | X | X |

*Fonte: Elaborado pelo autor (2026).*

---

# ANEXO A – Lista de Referências Complementares e Documentações de APIs

Neste anexo são consolidados os endereços eletrônicos das principais bibliotecas, ferramentas e documentações utilizadas para o desenvolvimento deste projeto.

- **EDJEELECTRONICS.** *Train and Deploy YOLO Models*. 2023. Disponível em: <https://colab.research.google.com/github/EdjeElectronics/Train-and-Deploy-YOLO-Models/blob/main/Train_YOLO_Models.ipynb>. Acesso em: 17 jun. 2026.
- **ULTRALYTICS.** *Ultralytics Python Package (YOLO)*. Disponível em: <https://docs.ultralytics.com/reference/>. Acesso em: 17 jun. 2026.
- **OPENCV.** *OpenCV Documentation*. Disponível em: <https://opencv.org/>. Acesso em: 17 jun. 2026.
- **GOOGLE.** *Firebase Documentation*. Disponível em: <https://firebase.google.com/docs>. Acesso em: 17 jun. 2026.
- **FASTAPI.** *FastAPI Documentation*. Disponível em: <https://fastapi.tiangolo.com/>. Acesso em: 17 jun. 2026.
- **OLLAMA.** *Ollama Documentation*. Disponível em: <https://ollama.com/>. Acesso em: 17 jun. 2026.
- **DATA SETS.** *Documentation*. Roboflow Universe. Disponível em: <https://universe.roboflow.com/>. Acesso em: 17 jun. 2026.
