# ROTEIRO E GUIA DE SLIDES (VERSÃO TÉCNICA) — 17º CONICT 2026

- **Apresentação PowerPoint Técnica (11 Slides):** `Slide_Tecnico_CONICT_2026.pptx`
- **Arquivo PDF do Roteiro Técnico:** `ROTEIRO_SLIDE_TECNICO_CONICT_2026.pdf`
- **Autor:** Kelvin A. L. Albuquerque (`kelvin.albuquerque@aluno.ifsp.edu.br`)
- **Orientador:** Prof. Dr. Ricardo Sovat (`sovat@ifsp.edu.br`) — IFSP Câmpus Campinas
- **Foco Técnico (Ideal para Perguntas Técnicas da Banca):** Arquitetura YOLO (Ultralytics), Roboflow Universe, OpenVINO IR FP16 (`.xml`/`.bin`), GPU dedicada Intel Arc B570 e GPUs NVIDIA T4, Backend RESTful Assíncrono (Python 3.10+, FastAPI, Uvicorn), Processamento 100% em RAM via OpenCV (`SAVE_PREDICTION_FILES = False`, `VIDEO_INFERENCE_STRIDE = 2`, *Warm-up* na GPU), Motor de Sobcamada em Cascata (recorte de RoI), Modelo Matemático de Calibração Estatística Dinâmica ($\tau_c, \mu_c, \sigma_c$ — `calculate_box_confidence_averages.py`), LLM Local via Ollama (`qwen2.5-coder`), Métrica Geométrica IoU (PASCAL VOC) e Telemetria em SQLite (`prediction_metrics.db` / `visualizar_metricas.py`).
- **Tempo Total Estimado:** ~7 min 30 s (11 Slides)

---

## Slide 1 — Capa (Slide de Título | ~30 seg)
- **Título:** DETECÇÃO DE CONFORMIDADE DE SEGURANÇA EM AMBIENTES UTILIZANDO A ARQUITETURA YOLO E ACELERAÇÃO OPENVINO
- **Autores:** Kelvin A. L. Albuquerque | Prof. Dr. Ricardo Sovat (*sovat@ifsp.edu.br*)
- **Curso / Instituição:** Tecnologia em Análise e Desenvolvimento de Sistemas — IFSP Câmpus Campinas

> **Fala técnica sugerida:**
> “Olá a todos, bom dia / boa tarde. Meu nome é Kelvin Albuquerque, estou concluindo o curso de Análise e Desenvolvimento de Sistemas pelo IFSP Câmpus Campinas e, sob orientação do professor Dr. Ricardo Sovat, apresento o trabalho intitulado ‘Detecção de Conformidade de Segurança em Ambientes Utilizando a Arquitetura YOLO e Aceleração OpenVINO’.”

---

## Slide 2 — Introdução (Título e Conteúdo | ~50 seg)
- **Contextualização e Relevância (NR-18 e NR-6):** Auditorias presenciais em canteiros de obras e instalações prediais baseiam-se em inspeções visuais amostrais, vulneráveis à fadiga humana e a falhas de monitoramento.
- **Problema de Pesquisa e Lacuna Tecnológica:** Redes neurais YOLO oferecem detecção em tempo real, mas a emissão isolada de caixas delimitadoras (*bounding boxes*) não assegura a coerência espacial e normativa da cena (ex.: placa presente sem o extintor exigido).
- **Tecnologias Integradas e Contribuições Desenvolvidas:** (a) API RESTful assíncrona (FastAPI/Uvicorn); (b) Aceleração OpenVINO IR FP16 em GPU Intel Arc B570; (c) Motor de sobcamada em cascata (RoI); (d) Calibração estatística dinâmica de limiares (τc); e (e) Laudos técnicos via LLM local (Ollama / qwen2.5-coder).

> **Fala técnica sugerida:**
> “Para contextualizar: a auditoria contínua de conformidade física em ambientes industriais e prediais, regida pela NR-18 e NR-6, ainda depende de inspeções visuais amostrais sujeitas à fadiga humana. Embora redes neurais da família YOLO ofereçam detecção em tempo real, a emissão isolada de caixas delimitadoras não garante a coerência espacial e regulamentar do ambiente — como identificar uma placa de sinalização na parede sem o extintor exigido abaixo dela. Para superar essa limitação, desenvolvemos uma arquitetura integrada composta por cinco pilares tecnológicos: uma API RESTful assíncrona em FastAPI, aceleração via OpenVINO FP16 em GPU dedicada Intel Arc B570, um motor de sobcamada em cascata, calibração estatística dinâmica de limiares e geração autônoma de laudos via LLM local.”

---

## Slide 3 — Objetivos e Tecnologias de Backend (1/3) (Duas Partes de Conteúdo | ~55 seg)
- **Treinamento YOLO e Aceleração OpenVINO:** Dataset no **Roboflow Universe** (~3.500 imagens reais, ~13.553 *bounding boxes*: 70% Treino, 20% Validação, 10% Teste). Treinamento híbrido no framework **Ultralytics YOLO** (100 épocas, SGD η = 0,01) em **GPU local Intel Arc B570** e **GPUs NVIDIA T4** em nuvem. Pesos (*best.pt*) exportados de FP32 para **OpenVINO IR FP16** (*.xml* e *.bin*).
- **Arquitetura de Microsserviços RESTful:** Backend assíncrono em **Python 3.10+** com **FastAPI** e servidor ASGI **Uvicorn**, desacoplando o motor de IA para integração via HTTP.
- **Engenharia de Otimização no Backend:** (a) *Inferência Direta em RAM (Streaming Volátil)* via matrizes **OpenCV** (*SAVE_PREDICTION_FILES = False*), sem I/O em disco; (b) *Amostragem Intercalada* (*VIDEO_INFERENCE_STRIDE = 2*); e (c) *Warm-up na GPU* Intel Arc B570 no startup, eliminando o *cold start*.

> **Fala técnica sugerida:**
> “Na metodologia, estruturamos um pipeline tecnológico de seis módulos. O dataset contou com cerca de 3.500 imagens reais anotadas no Roboflow Universe e mais de 13.500 bounding boxes. O treinamento no framework Ultralytics YOLO ocorreu por 100 épocas de forma híbrida entre GPU local Intel Arc B570 e GPUs NVIDIA T4 em nuvem. Em seguida, exportamos os pesos best.pt de FP32 para a representação intermediária OpenVINO IR FP16 em arquivos .xml e .bin, maximizando a vazão na GPU dedicada. No backend, desenvolvemos uma arquitetura de microsserviços RESTful assíncrona em Python 3.10+ utilizando FastAPI e Uvicorn, com três otimizações de engenharia: decodificação de quadros HTTP direto em matrizes OpenCV na memória RAM com SAVE_PREDICTION_FILES igual a False eliminando I/O em disco, salto amostral VIDEO_INFERENCE_STRIDE igual a 2 e warm-up dos modelos na GPU durante o startup para eliminar o cold start.”

---

## Slide 4 — Metodologia (2/3): Motor de Sobcamada e LLM Local (Duas Partes de Conteúdo | ~55 seg)
- **Motor de Sobcamada em Cascata (Desenvolvido):** Ao localizar o equipamento primário, a API recorta automaticamente em memória a **Região de Interesse (RoI)** e aciona submodelos especialistas para auditar **5 componentes essenciais**: (1) Trava e lacre (*Handle*); (2) Manômetro na faixa verde (*Gauge*); (3) Mangueira e difusor (*Hose Pipe*); (4) Rótulo/adesivo (*Sticker*); e (5) Placa normativa acima.
- **Análise de Coerência Espacial e Contextual:** Placa detectada sem o extintor no suporte aciona alerta de *inconsistência contextual grave*. Etapa piloto adicional com a classe 'Cadeira' para validar o pipeline assíncrono e controle patrimonial.
- **Geração de Laudos via LLM Local (Ollama):** Integração com o servidor local **Ollama** executando o modelo **qwen2.5-coder**, gerando laudo técnico descritivo em menos de ~2 segundos.

> **Fala técnica sugerida:**
> “Para superar a limitação das caixas delimitadoras simples, desenvolvemos o Motor de Sobcamada em Cascata. Assim que o equipamento primário é localizado, a API recorta em memória a Região de Interesse — a RoI — e aciona submodelos especialistas para inspecionar cinco componentes: trava e lacre, manômetro de pressão na faixa verde, mangueira e difusor, rótulo de instruções e a placa normativa acima do equipamento. Se a placa for detectada mas o extintor estiver ausente do suporte, o motor aponta uma inconsistência contextual grave. Todos os dados quantitativos e o checklist da sobcamada são enviados ao servidor local Ollama executando o modelo de linguagem qwen2.5-coder, que sintetiza em menos de 2 segundos um laudo técnico explicativo em linguagem clara.”

---

## Slide 5 — Metodologia (3/3): Calibração e Telemetria SQLite (Duas Partes de Conteúdo | ~50 seg)
- **Algoritmo de Limiares Dinâmicos (τc):** Script desenvolvido (*calculate_box_confidence_averages.py*) para eliminar alarmes falsos causados por reflexos, sombras ou ruídos visuais.
- **Modelo Matemático em 3 Passos:** Passo 1 (Média Populacional): µc = (1/n)·Σ ci  |  Passo 2 (Desvio Padrão): σc = √[(1/n)·Σ(ci − µc)²]  |  Passo 3 (Equação Limite): **τ_sugerido = max(0,40, min(0,95, 1,4·µc − 1,5·σc))** (cobre ~86,6% das detecções legítimas, piso 40% e teto 95%).
- **Avaliação Geométrica (IoU — PASCAL VOC) e Persistência SQLite:** IoU = Área(B_pred ∩ B_gt) / Área(B_pred ∪ B_gt) (VP se IoU ≥ 0,50; FP se IoU < 0,50). Telemetria persistida em banco **SQLite** (*prediction_metrics.db*) e analisada pelo script desenvolvido *visualizar_metricas.py*.

> **Fala técnica sugerida:**
> “Para impedir que reflexos, sombras ou ruídos de fundo gerem alarmes falsos, desenvolvemos o script calculate_box_confidence_averages.py, que implementa um modelo matemático de calibração estatística por classe. Calculamos a média populacional mi-c e o desvio padrão sigma-c do histórico de detecções e aplicamos a função limite delimitadora: tau sugerido igual ao máximo entre 0,40 e o mínimo entre 0,95 e 1,4 vezes a média menos 1,5 vezes o desvio padrão. Isso garante 86,6% de cobertura estatística das detecções legítimas, piso mínimo de 40% contra detecções espúrias e teto de 95%. A precisão espacial foi avaliada pela métrica IoU sob o critério PASCAL VOC de 50%, com toda a telemetria persistida em banco SQLite prediction_metrics.db e processada pelo script visualizar_metricas.py.”

---

## Slide 6 — Resultados (1/2): Telemetria Backend em Produção (Imagem com Legenda (Gráfico + Tabela 1) | ~55 seg)
- **Telemetria SQLite (Produção Real):** ~10.836 requisições HTTP processadas (~6.991 VP confirmados; taxa de acerto global de ~64,52% e confiança média µ = 56,81%).
- **Aceleração OpenVINO FP16:** Latência média de inferência de **~12,02 ms por quadro** na GPU dedicada Intel Arc B570 (vazão sustentada > **83 FPS** em memória RAM).
- **Prevenção contra Incêndio e Modo Multimodelo:** **~84,50% de acerto** (~2.170 VP em 2.568 req., µ = 67,70%, latência 11,85 ms) nos modelos de incêndio e sobcamada; **~71,06% de acerto** (~4.120 VP em 5.798 req.) no modo multimodelo (*model=all*).

> **Fala técnica sugerida:**
> “Passando aos resultados extraídos do banco SQLite em produção real: avaliamos um histórico de 10.836 requisições HTTP. A aceleração dos modelos via OpenVINO FP16 na GPU dedicada Intel Arc B570, somada à decodificação direta em memória RAM, alcançou latência média de apenas 12,02 milissegundos por quadro — equivalente a uma vazão sustentada superior a 83 FPS. Como detalhado na Tabela 1 e no gráfico ao lado, o modo multimodelo atingiu 71,06% de acerto em 5.798 requisições, enquanto os modelos especialistas de prevenção contra incêndio e sobcamada alcançaram 84,50% de taxa de acerto e confiança média de 67,70%.”

---

## Slide 7 — Resultados (2/2): Calibração de Limiares Dinâmicos (τc) (Imagem com Legenda (Gráfico da Tabela 2) | ~45 seg)
- **Execução do Algoritmo:** ~7.116 *bounding boxes* individuais processadas nos modelos ativos (Tabela 2).
- **Limiares de Alta Estabilidade:** Extintor Yamato YA-10NX (n=2.142, µ=0,70 → **τ=0,63**) e Extintor CO2 Babcock Davis (n=1.290, µ=0,55 → **τ=0,46**).
- **Submodelos da Sobcamada e Filtro Pré-LLM:** Mangueira/Difusor calibrada em **τ=0,42**; manômetro, trava/lacre e adesivo fixados no piso seguro **τ=0,40**, descartando detecções espúrias antes da consolidação do laudo pelo LLM Ollama.

> **Fala técnica sugerida:**
> “Neste segundo slide de resultados, vemos a execução do algoritmo de calibração sobre 7.116 caixas delimitadoras individuais detectadas nos modelos ativos. Classes de alta estabilidade visual tiveram seus limiares elevados automaticamente, como o extintor Yamato YA-10NX para 0,63 e o CO2 Babcock Davis para 0,46. Já nos submodelos da sobcamada, a mangueira convergiu para 0,42, enquanto manômetro, trava e rótulo foram protegidos pelo piso de 0,40, garantindo o descarte automatizado de falsos positivos antes da consolidação do laudo pelo LLM Ollama.”

---

## Slide 8 — Discussão (Comparação | ~45 seg)
- **Inspeção Contextual em Produção:** O motor de sobcamada em cascata + calibração τc identificou com precisão tanto cenários de conformidade quanto de inconsistência contextual (placa presente sem o extintor).
- **Limitações e Calibração de Submodelos:** O modelo piloto 'Cadeira' obteve 28,38% pela variação morfológica e oclusões; para estabilizar os subavaliadores (lacres, manômetros e mangueiras) no laudo Ollama, projeta-se média ponderada ou isolamento da pontuação do objeto-pai.
- **Avanço frente à Literatura e Diferenciais Tecnológicos:** Supera a limitação de detecção sem contexto de Rahman et al. (2021) mantendo o tempo real de Redmon et al. (2016) (> 83 FPS em RAM via OpenCV/FastAPI + OpenVINO FP16 + LLM local qwen2.5-coder).

> **Fala técnica sugerida:**
> “Na discussão técnica dos resultados: os ensaios práticos mostraram que o motor de sobcamada aliado aos limiares dinâmicos distingue com precisão cenários conformes de inconsistências contextuais graves, como a presença da placa sem o extintor. Observamos que a classe piloto Cadeira teve 28,38% de acerto devido à diversidade morfológica e oclusões em escritórios, e identificamos como evolução arquitetural a agregação por média ponderada dos subavaliadores para estabilizar ainda mais o laudo do Ollama. Frente à literatura de Rahman et al. (2021) e Redmon et al. (2016), a arquitetura desenvolvida entrega auditoria contextual explicável mantendo mais de 83 FPS em memória RAM.”

---

## Slide 9 — Conclusões (Título e Conteúdo | ~40 seg)
- **Síntese dos Resultados e Tecnologias:** A aceleração dos modelos YOLO via OpenVINO IR FP16 na GPU dedicada Intel Arc B570, integrada ao backend FastAPI com processamento 100% em memória RAM, apresentou ultrabaixa latência (~12,02 ms/quadro, > 83 FPS).
- **Contribuições e Validação Empírica:** O motor de sobcamada em cascata e a calibração estatística dinâmica (τc), validados em ~10.836 requisições HTTP reais no SQLite, alcançaram ~84,50% de acerto em prevenção contra incêndio e ~71,06% no modo multimodelo, com laudos em tempo real (< 2s) via LLM local Ollama.
- **Trabalhos Futuros:** Expansão do dataset para novas normas regulamentares, inclusão de novos modelos de reconhecimento, quantização INT8 para dispositivos de borda (*edge computing*) e testes sob iluminação reduzida e oclusões severas.

> **Fala técnica sugerida:**
> “Concluímos que o sistema desenvolvido apresentou alta eficiência e ultrabaixa latência para automação de auditorias de conformidade física. A aceleração YOLO via OpenVINO FP16 na GPU Intel Arc B570 com inferência 100% em RAM atingiu 12,02 milissegundos por quadro, enquanto o motor de sobcamada e a calibração dinâmica alcançaram 84,50% de acerto nos modelos de segurança contra incêndio com geração de laudos técnicos em tempo real via LLM local Ollama. Como trabalhos futuros, destacamos a expansão do dataset para novas NRs, o teste de novos modelos de reconhecimento, a quantização INT8 para edge computing e testes sob iluminação reduzida e oclusões severas.”

---

## Slide 10 — Referências (Título e Conteúdo | ~10 seg)
- BRASIL (NR-18, 2020; NR-6, 2022)  |  EVERINGHAM et al. (PASCAL VOC, 2010)  |  FIELDING (REST, 2000)  |  INTEL CORPORATION (OpenVINO, 2026)  |  RAHMAN, ULUSOY & MEYDANLI (2021)  |  REDMON et al. (YOLO, 2016)  |  TERVEN & CÓRDOVA-ESPARZA (2023)  |  ULTRALYTICS (2026).

> **Fala técnica sugerida:**
> “Aqui estão as referências normativas e científicas utilizadas no desenvolvimento deste trabalho.”

---

## Slide 11 — Obrigado! (Cabeçalho da Seção | ~15 seg)
- **Contato:** kelvin.albuquerque@aluno.ifsp.edu.br  |  sovat@ifsp.edu.br
- **Agradecimentos:** Instituto Federal de Educação, Ciência e Tecnologia de São Paulo (IFSP) — Câmpus Campinas.

> **Fala técnica sugerida:**
> “Agradeço ao IFSP Câmpus Campinas pelo suporte institucional e de infraestrutura, ao meu orientador Prof. Dr. Ricardo Sovat pelo direcionamento metodológico, e a todos pela atenção. Estou à disposição para perguntas. Muito obrigado!”

---
