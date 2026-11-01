# Estrutura dos Slides e Roteiro de Apresentação — 17º CONICT 2026

- **Arquivo de Apresentação Gerado**: `CONICT - 2026 - Apresentacao_Kelvin_Albuquerque.pptx`
- **Documento Base**: `TCC-Kelvin-Albuquerque-Completo-V4.pdf`
- **Template Base**: `CONICT - 2026 - Template_Apresentação.pptx`
- **Tempo Total Estimado**: **~7 min 30 s a 8 min 30 s** (dentro da faixa ideal de 5 a 10 minutos para o CONICT)
- **Quantidade de Slides**: **11 slides** (expandindo Metodologia em 3 slides e Resultados em 2 slides para não poluir visualmente e cobrir todos os pontos-chave do artigo)

---

## Slide 1 — Capa (Layout: `Slide de Título`)
**Tempo estimado**: ~30 segundos

### Conteúdo no Slide
- **Título**: DETECÇÃO DE CONFORMIDADE DE SEGURANÇA EM AMBIENTES UTILIZANDO A ARQUITETURA YOLO E ACELERAÇÃO OPENVINO
- **Subtítulo**:
  - Autor: Kelvin A. L. Albuquerque | Coautor: Prof. Dr. Ricardo Sovat
  - Orientador: Prof. Dr. Ricardo Sovat | Tecnologia em Análise e Desenvolvimento de Sistemas — IFSP Câmpus Campinas

### Roteiro de Fala (Para Treino)
> "Olá a todos, bom dia / boa tarde. Meu nome é Kelvin Albuquerque, sou graduando em Análise e Desenvolvimento de Sistemas pelo IFSP Câmpus Campinas, e sob orientação do professor Dr. Ricardo Sovat, apresento o trabalho intitulado *'Detecção de Conformidade de Segurança em Ambientes Utilizando a Arquitetura YOLO e Aceleração OpenVINO'*."

---

## Slide 2 — Introdução (Layout: `Título e Conteúdo`)
**Tempo estimado**: ~50 segundos

### Conteúdo no Slide
- **Contextualização e Relevância Regulamentar**:
  - Auditorias contínuas em canteiros de obras e instalações prediais são essenciais para o cumprimento da NR-18 (2020) e NR-6 (2022), mas inspeções presenciais amostrais sofrem com fadiga humana e falhas de monitoramento.
- **Problema de Pesquisa e Lacuna na Literatura**:
  - Redes da família YOLO entregam detecção rápida, porém caixas delimitadoras isoladas (*bounding boxes*) não validam a coerência espacial e normativa da cena (ex.: placa presente sem o extintor, ou equipamento sem lacre/pressão).
- **Justificativa e Proposta do Estudo**:
  - Arquitetura integrada que une inferência acelerada em GPU dedicada (OpenVINO FP16), motor de sobcamada em cascata, calibração estatística dinâmica de limiares e síntese de laudos técnicos via LLM local.

### Roteiro de Fala (Para Treino)
> "Para contextualizar: a fiscalização contínua de segurança do trabalho, regida por normas como a NR-6 e a NR-18, ainda depende fortemente de inspeções visuais presenciais e amostrais, que são vulneráveis à fadiga humana.
> Embora redes neurais da família YOLO permitam detectar objetos em tempo real, existe uma lacuna importante na literatura: apenas desenhar uma caixa delimitadora ao redor de um objeto não garante a conformidade regulamentar do ambiente. Por exemplo, detectar uma placa de sinalização na parede sem o extintor abaixo dela, ou detectar um extintor que está sem lacre ou descarregado, não significa que o local está seguro.
> Para resolver isso, propomos uma solução de ponta a ponta que une aceleração em hardware via OpenVINO, um motor de sobcamada em cascata, calibração estatística contra falsos alarmes e geração automática de laudos por um LLM local."

---

## Slide 3 — Objetivos e Metodologia (1/3): Pipeline e Backend (Layout: `Duas Partes de Conteúdo`)
**Tempo estimado**: ~55 segundos

### Conteúdo no Slide
**Coluna Esquerda:**
- **Objetivos do Trabalho**:
  - *Geral*: Desenvolver e avaliar em produção real uma API inteligente para auditoria automatizada de conformidade física.
  - *Específicos*: Acelerar modelos YOLO via OpenVINO FP16; validar subcomponentes em cascata; calibrar limiares dinâmicos ($\tau_c$) e gerar laudos via LLM.
- **Dataset e Treinamento YOLO**:
  - ~3.500 imagens reais (Roboflow Universe) com ~13.553 *bounding boxes* (70% Treino, 20% Validação, 10% Teste).
  - Ultralytics YOLO (100 épocas, SGD $\eta = 0,01$), quantizado de FP32 para OpenVINO IR FP16 (`.xml`/`.bin`) em GPU Intel Arc B570.

**Coluna Direita:**
- **Arquitetura RESTful Assíncrona**:
  - Microsserviço em Python 3.10+ (FastAPI e Uvicorn), desacoplando o motor de visão computacional dos clientes móveis/web.
- **Três Otimizações de Ultrabaixa Latência**:
  1. *Streaming Volátil em RAM*: Decodificação direta em matrizes OpenCV (`SAVE_PREDICTION_FILES = False`), zero I/O em disco.
  2. *Amostragem Intercalada (`Vid Stride = 2`)*: Reduz o tempo de processamento de vídeo pela metade.
  3. *Warm-up na GPU*: Pré-carregamento dos modelos na Intel Arc B570 no *startup*, eliminando o *cold start*.

### Roteiro de Fala (Para Treino)
> "Nosso objetivo geral foi construir e validar em produção uma API RESTful capaz de auditar essa conformidade física em tempo real.
> Na preparação dos modelos, utilizamos um dataset com cerca de 3.500 imagens reais e mais de 13.500 anotações. Treinamos os modelos YOLO por 100 épocas e exportamos os pesos de precisão FP32 para o formato intermediário OpenVINO FP16, rodando em uma GPU dedicada Intel Arc B570.
> No backend em FastAPI, aplicamos três otimizações críticas para atingir ultrabaixa latência: primeiro, *streaming* volátil 100% em memória RAM, eliminando gravações em disco; segundo, amostragem intercalada com *stride* igual a 2 para vídeos; e terceiro, um procedimento de *warm-up* que pré-carrega os modelos na GPU já na inicialização da API, zerando o atraso da primeira requisição."

---

## Slide 4 — Metodologia (2/3): Motor de Sobcamada e LLM Local (Layout: `Duas Partes de Conteúdo`)
**Tempo estimado**: ~55 segundos

### Conteúdo no Slide
**Coluna Esquerda:**
- **Motor de Sobcamada em Cascata**:
  - Atua como auditor automatizado: ao localizar o equipamento primário, recorta a Região de Interesse (RoI) e aciona submodelos especialistas.
- **Checklist de 5 Componentes Essenciais**:
  1. Trava e lacre de segurança intactos;
  2. Manômetro de pressão (ponteiro na faixa verde);
  3. Mangueira e difusor de descarga acoplados;
  4. Rótulo e adesivo de instruções de operação;
  5. Placa de sinalização normativa na parede acima.

**Coluna Direita:**
- **Validação de Coerência Espacial**:
  - *Inconsistência Contextual Grave*: Se a placa normativa é detectada mas o extintor está ausente do suporte, o motor reprova a conformidade do ambiente.
  - *Classe Piloto Adicional ("Cadeira")*: Incluída para validar o pipeline assíncrono e controle patrimonial antes da expansão operacional.
- **Síntese de Laudos por LLM Local (Ollama)**:
  - Os dados quantitativos e o *checklist* da sobcamada são enviados ao modelo local `qwen2.5-coder` via Ollama.
  - Gera laudo técnico descritivo e explicável em linguagem natural em menos de ~2 segundos, com total privacidade local.

### Roteiro de Fala (Para Treino)
> "O grande diferencial da nossa metodologia está no Motor de Sobcamada em Cascata. Ele funciona como um auditor humano automatizado: assim que a rede principal localiza um extintor, a API recorta automaticamente essa Região de Interesse — a RoI — e aciona submodelos especialistas para auditar cinco itens obrigatórios: trava e lacre, manômetro de pressão na faixa verde, mangueira e difusor, rótulo de instruções e a placa de sinalização acima do equipamento.
> Além disso, o motor avalia a coerência espacial: se a placa for detectada na parede, mas o extintor estiver ausente, o sistema aponta imediatamente uma inconsistência grave.
> Todo esse checklist estruturado é enviado para uma instância local do Ollama rodando o modelo `qwen2.5-coder`, que em menos de 2 segundos redige um laudo técnico claro e acessível para o gestor."

---

## Slide 5 — Metodologia (3/3): Calibração Dinâmica ($\tau_c$) e Métricas (Layout: `Duas Partes de Conteúdo`)
**Tempo estimado**: ~50 segundos

### Conteúdo no Slide
**Coluna Esquerda:**
- **Calibração Dinâmica de Limiares ($\tau_c$)**:
  - Elimina alarmes falsos causados por reflexos, sombras ou ruídos visuais (`calculate_box_confidence_averages.py`):
  - **Passo 1 (Média Populacional $\mu_c$)**: $\mu_c = \frac{1}{n} \sum c_i$ — certeza média histórica da classe $c$.
  - **Passo 2 (Desvio Padrão $\sigma_c$)**: $\sigma_c = \sqrt{\frac{1}{n} \sum (c_i - \mu_c)^2}$ — dispersão por ângulo/iluminação.
  - **Passo 3 (Função Limite Delimitadora)**:
    $$\tau_{\text{sugerido}} = \max(0,40, \min(0,95, 1,4\cdot\mu_c - 1,5\cdot\sigma_c))$$
    Cobre ~86,6% das detecções legítimas ($-1,5\sigma_c$), com piso de 40% contra ruídos e teto de 95%.

**Coluna Direita:**
- **Métrica Geométrica (IoU — PASCAL VOC)**:
  - $\text{IoU} = \frac{\text{Área}(B_{\text{pred}} \cap B_{\text{gt}})}{\text{Área}(B_{\text{pred}} \cup B_{\text{gt}})}$
  - **Verdadeiro Positivo (VP)**: Sobreposição $\text{IoU} \ge 0,50$ ($\ge 50\%$) e classe correta.
  - **Falso Positivo (FP)**: Sobreposição $\text{IoU} < 0,50$ ou detecção em local incorreto.
- **Telemetria e Auditoria Empírica**:
  - Persistência contínua em banco SQLite (`prediction_metrics.db`) e análise estatística automatizada (`visualizar_metricas.py`).

### Roteiro de Fala (Para Treino)
> "Para evitar que reflexos de iluminação ou sombras gerem falsos alarmes em campo, formulamos um modelo matemático de calibração dinâmica de limiares por classe.
> Calculamos a média populacional $\mu_c$ e o desvio padrão $\sigma_c$ do histórico de detecções de cada classe, e aplicamos a função delimitadora: $\tau_{\text{sugerido}} = \max(0,40, \min(0,95, 1,4\mu_c - 1,5\sigma_c))$. Isso garante cobertura estatística de cerca de 86,6% das detecções legítimas, impondo um corte mínimo de 40% para descartar ruídos espúrios e um teto de 95%.
> Na avaliação espacial, adotamos o padrão PASCAL VOC com Interseção sobre União (IoU) mínima de 50% para Verdadeiros Positivos, persistindo toda a telemetria em banco SQLite."

---

## Slide 6 — Resultados (1/2): Desempenho e Telemetria em Produção (Layout: `Imagem com Legenda`)
**Tempo estimado**: ~55 segundos

### Conteúdo no Slide
**Coluna Esquerda (Legenda Analítica):**
- **Volume em Produção Real**: ~10.836 requisições HTTP auditadas (~6.991 VP; 64,52% de acerto global).
- **Ultrabaixa Latência (GPU)**: ~12,02 ms/quadro via OpenVINO FP16 na Intel Arc B570 (~83 FPS em RAM).
- **Prevenção contra Incêndio**: ~84,50% de taxa de acerto (~2.170 VP em 2.568 req.) e confiança $\mu = 67,70\%$.
- **Modo Multimodelo (`all`)**: ~71,06% de acerto operacional (~4.120 VP em 5.798 requisições).

**Área de Imagem (Direita):**
- Gráfico comparativo + Tabela 1 de telemetria operacional dos modelos ativos em produção real.

### Roteiro de Fala (Para Treino)
> "Passando aos resultados: nossa avaliação empírica analisou um volume real de 10.836 requisições HTTP registradas em produção.
> O primeiro grande destaque é a velocidade: graças à quantização FP16 no OpenVINO e ao processamento direto em RAM na GPU Intel Arc B570, o tempo médio de inferência ficou em apenas 12,02 milissegundos por quadro — o que equivale a uma vazão sustentada superior a 83 quadros por segundo.
> Em termos de precisão, como vemos no gráfico e na Tabela 1 ao lado, o modo multimodelo alcançou 71,06% de acerto em quase 5.800 requisições, enquanto os modelos dedicados à prevenção contra incêndio e sobcamada atingiram expressivos 84,50% de taxa de acerto com confiança média de 67,70%."

---

## Slide 7 — Resultados (2/2): Calibração de Limiares Dinâmicos ($\tau_c$) (Layout: `Imagem com Legenda`)
**Tempo estimado**: ~45 segundos

### Conteúdo no Slide
**Coluna Esquerda (Legenda Analítica):**
- **Amostragem de Caixas**: ~7.116 *bounding boxes* individuais avaliadas nos modelos ativos.
- **Rigor Adaptativo Superior**: Classes estáveis elevaram o limiar: Yamato YA-10NX ($\mu=0,70 \rightarrow \tau=0,63$) e Babcock Davis ($\mu=0,55 \rightarrow \tau=0,46$).
- **Subcomponentes da RoI**: Mangueira calibrada em $\tau=0,42$; manômetro, lacre e adesivo fixados no piso seguro $\tau=0,40$.
- **Filtragem Pré-LLM**: Descarte automático de falsos positivos antes da síntese pelo Ollama.

**Área de Imagem (Direita):**
- Gráfico da Tabela 2: Confiança Média ($\mu_c$), Desvio ($\sigma_c$) e Limiar Calibrado ($\tau_c$) para as 10 classes avaliadas.

### Roteiro de Fala (Para Treino)
> "Neste segundo slide de resultados, apresentamos o efeito da calibração dinâmica sobre 7.116 caixas delimitadoras individuais.
> Observe na figura que objetos com geometria e cor muito bem definidas — como o extintor Yamato YA-10NX e o Babcock Davis — tiveram seus limiares automaticamente elevados pelo algoritmo para 0,63 e 0,46, aumentando o rigor da inspeção.
> Já subcomponentes menores da sobcamada, como mangueira ($\tau = 0,42$), manômetro e lacre ($\tau = 0,40$), foram protegidos pelo piso estatístico de 40%, filtrando detecções espúrias antes que os dados chegassem ao LLM Ollama."

---

## Slide 8 — Discussão (Layout: `Comparação`)
**Tempo estimado**: ~45 segundos

### Conteúdo no Slide
**Coluna Esquerda — Interpretação dos Achados e Limitações:**
- **Interpretação dos Achados**: A cascata RoI + calibração $\tau_c$ impediu falsos positivos em cenários críticos (ex.: placa presente sem o extintor).
- **Limitações do Estudo**:
  - A classe piloto "Cadeira" obteve 28,38% de acerto pela alta diversidade morfológica e oclusões severas em escritórios.
  - Subcomponentes pequenos (lacres e manômetros) demandam agregação ponderada ou isolamento da pontuação do objeto-pai.

**Coluna Direita — Literatura e Contribuições:**
- **Comparação com a Literatura**: Supera a lacuna de detecção sem contexto apontada por Rahman et al. (2021), preservando a inferência em tempo real de Redmon et al. (2016).
- **Contribuições do Trabalho**: Vazão sustentada > 83 FPS 100% em RAM em GPU dedicada acessível (Intel Arc B570) + laudos explicáveis via LLM local.

### Roteiro de Fala (Para Treino)
> "Discutindo esses achados: a combinação entre o recorte em cascata e a calibração dinâmica resolveu na prática o problema de falsos positivos em cenas ambíguas.
> Como limitação, observamos que o modelo piloto para a classe 'Cadeira' teve 28,38% de acerto, explicado pela enorme variedade de formatos de cadeiras e oclusões sob mesas em escritórios — o que comprova por que modelos especialistas de segurança precisam de subcamadas dedicadas. Também identificamos a oportunidade de aplicar média ponderada nos subavaliadores menores, como lacres e manômetros.
> Frente à literatura de Rahman et al. (2021), nosso trabalho avança ao transformar caixas isoladas em auditoria contextual sem abrir mão da execução em tempo real de Redmon et al. (2016)."

---

## Slide 9 — Conclusões (Layout: `Título e Conteúdo`)
**Tempo estimado**: ~40 segundos

### Conteúdo no Slide
- **Síntese dos Resultados frente aos Objetivos**:
  - O sistema comprovou alta eficiência e ultrabaixa latência (~12,02 ms/quadro em OpenVINO FP16 na GPU Intel Arc B570), alcançando ~84,50% de acerto nos modelos de segurança contra incêndio e ~71,06% no modo multimodelo em ~10.836 requisições reais.
- **Contribuições e Aplicações Práticas**:
  - Arquitetura RESTful em memória RAM que converte detecções visuais auditadas pela sobcamada e filtradas por $\tau_c$ em laudos técnicos claros em tempo real (< 2s via LLM Ollama), democratizando a fiscalização da NR-6 e NR-18.
- **Trabalhos Futuros**:
  - Expansão do *dataset* para novas NRs, quantização INT8 para dispositivos de borda (*edge computing*) e avaliação sob baixa iluminação e oclusões severas.

### Roteiro de Fala (Para Treino)
> "Concluímos que a arquitetura proposta é altamente eficiente e viável para operação real, entregando 12,02 ms de latência por quadro e 84,50% de precisão na auditoria de prevenção contra incêndio, gerando laudos técnicos explicáveis em menos de 2 segundos sem depender de APIs pagas em nuvem.
> Como trabalhos futuros, planejamos expandir o dataset para novas Normas Regulamentadoras, aplicar quantização INT8 para execução em dispositivos de borda (*edge computing*) e ampliar os testes em cenários de baixa iluminação."

---

## Slide 10 — Referências (Layout: `Título e Conteúdo`)
**Tempo estimado**: ~10 segundos

### Conteúdo no Slide
- BRASIL. *Norma Regulamentadora n. 18 (2020) e NR-6 (2022)*. Brasília, DF: MTE.
- EVERINGHAM, M. et al. The PASCAL Visual Object Classes (VOC) Challenge. *IJCV*, v. 88, n. 2, p. 303–338, 2010.
- FIELDING, R. T. *Architectural styles and the design of network-based software architectures*. Tese — UC Irvine, 2000.
- INTEL CORPORATION. *OpenVINO Toolkit Documentation*. 2026.
- RAHMAN, M. A.; ULUSOY, I.; MEYDANLI, A. Context-aware object detection: A survey. *IEEE Access*, v. 9, 2021.
- REDMON, J. et al. You Only Look Once: Unified, real-time object detection. In: *IEEE CVPR*, 2016.
- TERVEN, J.; CÓRDOVA-ESPARZA, D. A comprehensive review of YOLO architectures in object detection. *Artificial Intelligence Review*, v. 56, 2023.

### Roteiro de Fala (Para Treino)
> "Aqui estão as principais referências normativas e científicas que fundamentaram o nosso desenvolvimento."

---

## Slide 11 — Encerramento (Layout: `Cabeçalho da Seção`)
**Tempo estimado**: ~15 segundos

### Conteúdo no Slide
- **Título**: Obrigado!
- **Contato e Agradecimentos**:
  - Kelvin A. L. Albuquerque: `kelvin.albuquerque@aluno.ifsp.edu.br`
  - Prof. Dr. Ricardo Sovat (Orientador): `r.sovat@ifsp.edu.br`
  - Agradecimentos ao Instituto Federal de Educação, Ciência e Tecnologia de São Paulo (IFSP) — Câmpus Campinas pelo suporte institucional e de infraestrutura.

### Roteiro de Fala (Para Treino)
> "Agradeço ao IFSP Câmpus Campinas pelo suporte institucional, ao meu orientador Prof. Dr. Ricardo Sovat, e a todos pela atenção. Estou à disposição da banca e do público para dúvidas e sugestões. Muito obrigado!"

