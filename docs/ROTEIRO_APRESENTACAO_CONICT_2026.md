# ROTEIRO DE APRESENTAÇÃO E GUIA DE SLIDES — 17º CONICT 2026

- **Apresentação PowerPoint (13 Slides):** `CONICT - 2026 - Apresentacao_Kelvin_Albuquerque.pptx`
- **Arquivo PDF do Roteiro:** `ROTEIRO_APRESENTACAO_CONICT_2026.pdf`
- **Autor:** Kelvin A. L. Albuquerque (`kelvin.albuquerque@aluno.ifsp.edu.br`)
- **Orientador:** Prof. Dr. Ricardo Sovat (`sovat@ifsp.edu.br`) — IFSP Câmpus Campinas
- **Trabalho:** Detecção de Conformidade de Segurança em Ambientes Utilizando a Arquitetura YOLO e Aceleração OpenVINO
- **Tempo Total Estimado:** ~10 a 11 minutos (13 Slides)

---

## Slide 1 — Capa (Slide de Título | ~30 seg)
- **Título:** DETECÇÃO DE CONFORMIDADE DE SEGURANÇA EM AMBIENTES UTILIZANDO A ARQUITETURA YOLO E ACELERAÇÃO OPENVINO
- **Autores:** Kelvin A. L. Albuquerque | Prof. Dr. Ricardo Sovat (*sovat@ifsp.edu.br*)
- **Curso / Instituição:** Tecnologia em Análise e Desenvolvimento de Sistemas — IFSP Câmpus Campinas

> **Fala sugerida (Treino):**
> “Olá a todos, bom dia / boa tarde. Meu nome é Kelvin Albuquerque, estou concluindo o curso de Análise e Desenvolvimento de Sistemas pelo IFSP Câmpus Campinas e, sob orientação do professor Dr. Ricardo Sovat, apresento o trabalho intitulado ‘Detecção de Conformidade de Segurança em Ambientes Utilizando a Arquitetura YOLO e Aceleração OpenVINO’.”

---

## Slide 2 — Contextualização e O Problema na Prática (Título e Conteúdo | ~1 min 05 seg)
- **Situação concreta (NR-18 e NR-6):** Obras e prédios precisam de auditoria (conferir se os equipamentos estão no lugar certo e prontos para uso).
- **Problema humano:** Inspeções feitas apenas no olho humano sofrem com cansaço, distração e tamanho do local.
- **Explicação dos termos:** **YOLO** (IA que reconhece objetos em fotos); **Caixas Delimitadoras** (quadrados desenhados ao redor do objeto); **Coerência Espacial** (verificar se a placa e o extintor estão na posição correta um em relação ao outro).

> **Fala sugerida (Treino):**
> “Para começar, vamos imaginar uma situação bem prática: todo prédio, fábrica ou canteiro de obras precisa seguir normas de segurança, como a NR-18 e a NR-6. Para garantir isso, existe a auditoria — que nada mais é do que um fiscal caminhar pelo local conferindo se os equipamentos, como extintores e placas de sinalização, estão no lugar certo e em boas condições. O problema é que essa vistoria humana é cansativa: em um prédio grande, a pessoa pode se distrair ou deixar passar uma falha. Hoje já existem sistemas de Visão Computacional, como a rede chamada YOLO, que funciona como um olho eletrônico rápido: ela olha para uma foto e desenha o que chamamos de caixas delimitadoras — que são aqueles quadrados coloridos marcando onde está cada objeto. Porém, existe uma lacuna tecnológica nas soluções atuais: falta a coerência espacial. Por exemplo: não basta a IA achar uma placa de incêndio na parede e achar um extintor em outro canto; ela precisa entender se o extintor está realmente instalado embaixo daquela placa e se ele tem todas as peças para funcionar.”

---

## Slide 3 — Objetivo do Trabalho (Slide Dedicado ao Objetivo | ~45 seg)
- **Objetivo Principal:** Desenvolver um sistema de visão computacional para auxiliar o fiscal na inspeção de segurança, verificando o equipamento, seus componentes e sua posição no ambiente, gerando um laudo escrito automático.
- **Visão Geral da Solução:** Servidor Web (recebe a foto) → Aceleração na Placa de Vídeo → Subcamada de Peças → Nota de Corte Inteligente → Relatório em Português.

> **Fala sugerida (Treino):**
> “Diante desse problema, o objetivo do nosso trabalho foi desenvolver e avaliar um sistema inteligente de visão computacional que ajude o fiscal nessa vistoria. A ideia é que o sistema não diga apenas ‘achei um extintor’, mas que ele verifique se as peças do extintor estão completas, se ele está posicionado corretamente embaixo da placa e, no final, entregue um relatório escrito em português claro para o responsável pela segurança.”

---

## Slide 4 — Metodologia (1/3): Treinamento, Aceleração e Servidor (Duas Partes de Conteúdo | ~1 min 05 seg)
- **Dataset (Roboflow Universe):** ~3.500 fotos reais com objetos marcados (~13.553 marcações) para ensinar a IA.
- **Treinamento e OpenVINO:** Treinado usando computador local e nuvem; otimizado com **OpenVINO** para rodar rápido na placa de vídeo Intel.
- **Servidor (API FastAPI) e Otimizações:** Funciona como uma central web que recebe a imagem e devolve a análise, com 3 otimizações para ser rápido mesmo em computadores menos potentes.

> **Fala sugerida (Treino):**
> “Como nós construímos isso? Primeiro, para ensinar a Inteligência Artificial a reconhecer os equipamentos, usamos um banco de dados público chamado Roboflow Universe, com cerca de 3.500 fotos reais onde cada objeto e peça já estava marcado. Como esse treinamento exige bastante cálculo, nós dividimos a tarefa entre uma máquina local e computadores em nuvem. Depois que o modelo aprendeu, usamos uma ferramenta chamada OpenVINO, que serve para deixar o modelo mais leve e adaptado para rodar com máxima velocidade na placa de vídeo da Intel. Para que qualquer aplicação consiga usar essa IA, criamos um servidor web — uma API ou microsserviço: a aplicação envia a foto para o servidor, o servidor analisa e devolve a resposta na hora. Além disso, fizemos três otimizações no servidor para evitar lentidão e permitir que o sistema rode bem mesmo em máquinas menos potentes.”

---

## Slide 5 — Metodologia (2/3): Subcamada, Verificações e Laudo (Duas Partes de Conteúdo | ~1 min 15 seg)
- **Sequência em 5 passos:** (1) Identifica o equipamento principal → (2) Recorta a Região de Interesse (zoom) → (3) Aciona a Subcamada (modelos especialistas) → (4) Confere componentes e posição → (5) Gera o laudo escrito.
- **Diferença importante:** Verificar *componentes físicos* (trava, manômetro no verde, mangueira, rótulo) vs. verificar a *relação espacial* (placa acima do extintor). Cadeira foi usada primeiro como *modelo piloto*.

> **Fala sugerida (Treino):**
> “Neste slide vemos o coração do funcionamento do sistema, que acontece em uma sequência de cinco passos simples: Primeiro, o sistema olha a foto inteira e encontra o equipamento principal — nós começamos testando o servidor com cadeiras de escritório, que foi o nosso modelo piloto, e depois avançamos para os extintores de incêndio. Segundo, assim que ele acha o extintor, ele seleciona a Região de Interesse — ou seja, ele faz um recorte, um ‘zoom’ apenas na área daquele extintor. Terceiro, entra o que chamamos de subcamada: são modelos especialistas treinados especificamente para procurar peças pequenas dentro desse recorte. Quarto, o sistema faz dois tipos de checagem: ele confere se as quatro peças do extintor estão ali — a trava de segurança, o manômetro com ponteiro no verde, a mangueira e o rótulo de instruções — e também confere a relação espacial no ambiente, verificando se a placa de sinalização está na parede acima do extintor. Se a placa estiver lá, mas o extintor tiver sido retirado, ele aponta uma falha grave. E quinto: como o resultado do computador é cheio de números técnicos, nós passamos esses dados para um modelo de linguagem local chamado Ollama, que transforma tudo em um laudo escrito em português claro em menos de dois segundos.”

---

## Slide 6 — Metodologia (3/3): Limiar Dinâmico, SQLite e Avaliação (Duas Partes de Conteúdo | ~1 min 15 seg)
- **O que é Limiar (Threshold):** Nota de corte usada para aceitar ou descartar uma detecção da IA.
- **Banco SQLite e Limiar Dinâmico:** O SQLite guarda o objeto detectado, a nota de confiança e o tempo de cada análise. A partir da média e variação dessas notas, o sistema recalcula o limite de cada classe (entre 40% e 95%).
- **Confiança ≠ Acurácia e Avaliação Geométrica (IoU):** Confiança é o quanto a IA diz ter certeza; taxa de acerto é se ela realmente acertou (usando o critério PASCAL VOC de pelo menos 50% de sobreposição com o objeto real).

> **Fala sugerida (Treino):**
> “Um grande desafio na prática é que a iluminação do ambiente muda: às vezes bate sol, faz sombra ou reflexo no metal do extintor, e isso afeta o reconhecimento da IA. Para lidar com isso, trabalhamos com o conceito de limiar — ou threshold — que nada mais é do que uma nota de corte: qual é a certeza mínima que a IA precisa ter para aceitarmos aquela detecção como válida? Para que essa nota de corte não fique fixa, usamos um banco de dados chamado SQLite. Toda vez que o sistema analisa uma imagem, ele guarda no SQLite qual objeto foi visto, qual foi a nota de confiança da IA e o tempo gasto. Depois, o nosso cálculo lê esse histórico de detecções registradas, calcula a média e a variação das notas daquele objeto e ajusta a nota de corte automaticamente — mantendo sempre um mínimo de 40% para barrar alarmes falsos e um teto máximo de 95%. Aqui vale destacar uma diferença importante: a ‘confiança’ é apenas o grau de certeza que a IA estima na imagem; já para saber a ‘taxa de acerto’ real do modelo, usamos um critério geométrico conhecido na literatura chamado IoU (do padrão PASCAL VOC), que verifica se o quadrado desenhado pela IA coincide em pelo menos 50% com a posição real do objeto.”

---

## Slide 7 — Resultados (1/3): Desempenho dos Modelos (Imagem com Legenda (Gráfico de Desempenho) | ~1 min 10 seg)
- **Significado das barras neste slide:** **Verde-escuro** = Taxa de Acerto Real (%) | **Verde-claro** = Confiança Média da IA (%).
- **Evolução de baixo para cima:** Piloto com cadeiras (28,38%) → Consolidado geral (64,52%) → Modo multimodelo (71,06%) → Prevenção contra incêndio no topo (**84,50% de acerto** em ~12 ms).
- **Ponte direta para o Slide 8:** Fechar dizendo que os ~15% restantes e a variação de confiança acontecem porque os equipamentos e peças mudam muito de formato e tamanho — preparando as fotos do Slide 8.

> **Fala sugerida (Treino):**
> “Agora vamos olhar para este gráfico, que resume o desempenho dos nossos modelos em mais de 10 mil análises registradas. Primeiro, o que significam as cores aqui? A barra verde-escura mostra a taxa de acerto real do sistema, e a barra verde-clara mostra a confiança média que a IA teve nas detecções. Olhando de baixo para cima, vemos toda a evolução da pesquisa: Lá embaixo está o modelo piloto de cadeiras de escritório, com 28,38% de acerto, que serviu como primeiro teste de estrutura do servidor. Subindo, temos o consolidado geral com 64,52% e o modo multimodelo, onde todos os modelos rodam juntos, chegando a 71,06% de acerto. E no topo estão os modelos especialistas de prevenção contra incêndio — avaliando o extintor, suas peças e a placa —, alcançando 84,50% de taxa de acerto em apenas 12 milissegundos por imagem. Como é uma pesquisa em evolução, esses 84,5% mostram um resultado muito sólido, mas também mostram que ainda temos cerca de 15% para evoluir — principalmente por causa das diferenças físicas entre os equipamentos, como vou mostrar rapidinho nas fotos a seguir.”

---

## Slide 8 — Novo Slide (6 e meio): Variação Visual dos Extintores (Imagem com Legenda (Fotos Comparativas — Ponte Rápida) | ~25 a 30 seg)
- **Objetivo deste slide (Ponte de 25 seg):** Não perder tempo listando cada detalhe das fotos; usar apenas como gancho visual rápido entre o Slide 7 e o Slide 9.
- **Contraste rápido em 1 frase:** Na esquerda (Yamato) a mangueira é fina na lateral; na direita (CO2 Babcock) tem uma corneta preta larga — e peças como lacre e manômetro são minúsculas perto do cilindro.
- **Gancho imediato para o Slide 9:** Por terem tamanhos e formatos tão diferentes, cada item precisa de uma nota de corte própria (que é o gráfico do Slide 9).

> **Fala sugerida (Treino):**
> “Pessoal, trouxe essas duas fotos só para vocês visualizarem um ponto rápido na prática: para a câmera, os extintores não são todos iguais. Reparem como o Yamato, na esquerda, tem uma mangueira fina presa na lateral, enquanto o modelo de CO2, na direita, tem essa corneta preta bem larga na ponta. Além disso, vejam como peças como o lacre e o manômetro são minúsculas perto do cilindro inteiro. É exatamente por causa dessa diferença de tamanho e formato que o sistema precisa ajustar a nota de corte de cada item separadamente, como vemos no próximo gráfico.”

---

## Slide 9 — Resultados (2/3): Limiares Calibrados por Objeto (Imagem com Legenda (Gráfico de Limiares e Confiança) | ~1 min)
- **1º Passo — Explicar as cores e a linha para a plateia (igual à didática do Slide 7):** **Linha vermelha tracejada** = limiar mínimo inicial de 0,40 (40%); **Barra verde-clara** = confiança média da IA (certeza média ao ver o objeto); **Barra verde-escura** = nota de corte calibrada (limiar dinâmico) definida pelo sistema.
- **2º Passo — Mostrar o topo vs. parte de baixo usando as cores:** No topo (Yamato, Babcock e Mangueira), como a **barra verde-clara** (confiança) foi alta, o sistema subiu a **barra verde-escura** (nota de corte, chegando a 0,63). Já nas peças pequenas (lacre, manômetro, adesivo), como tiveram poucos registros e a **barra verde-clara** ficou baixa, o sistema travou a **barra verde-escura** exatamente em cima da **linha vermelha (0,40)**.
- **3º Passo — Diferença entre fotos de treino e detecções:** As **7.116 detecções** no título são o total de objetos encontrados nos testes (já que uma foto pode ter vários objetos), diferente das **3.500 fotos** usadas no treinamento.

> **Fala sugerida (Treino):**
> “Neste gráfico, nós vemos a nota de corte calculada para cada objeto separadamente. Primeiro, vamos entender o que significa cada elemento na tela: a linha vermelha tracejada no meio é o nosso limite mínimo inicial de 40% (0,40), abaixo do qual o sistema descarta a leitura; a barra verde-clara mostra a confiança média da IA, ou seja, a certeza média que o modelo teve ao detectar aquele item; e a barra verde-escura mostra a nova nota de corte — o limiar calibrado — que o sistema definiu para aquele objeto. Sabendo disso, vejam o que aconteceu na prática: lá no topo estão os dois extintores das fotos que acabamos de ver — o Yamato e o Babcock — junto com a mangueira. Como a barra verde-clara deles foi alta, o sistema subiu a barra verde-escura automaticamente, chegando a 0,63 no Yamato. Já do meio para baixo estão as peças menores, como o lacre, o manômetro e o adesivo. Como são peças pequenas e tiveram poucas leituras — entre 15 e 60 registros —, a barra verde-clara ficou baixa e, por segurança, o sistema travou a barra verde-escura exatamente em cima da linha vermelha de 0,40. Por fim, vale notar ali no título que essas 7.116 detecções são o total de objetos encontrados nos nossos testes — diferente das 3.500 fotos usadas no treinamento, porque uma única foto pode ter vários objetos detectados ao mesmo tempo.”

---

## Slide 10 — Discussão e Limitações (Comparação | ~55 seg)
- **Linguagem acessível:** Explicar *variação morfológica* como **diferenças de formato entre os objetos**, e *oclusão* como **algo que encobre parte do objeto**.
- **Por que e quando retreinar:** Quando um objeto tem formatos muito variados (como cadeiras) ou poucas amostras de peças pequenas (como lacres), a queda de desempenho indica a necessidade de coletar mais imagens e retreinar o modelo.

> **Fala sugerida (Treino):**
> “Discutindo esses resultados de forma prática: o grande avanço do trabalho foi mostrar que podemos ir além de apenas desenhar quadrados na tela, verificando se o equipamento está completo e na posição certa em relação à placa. Por outro lado, a pesquisa também revelou limitações importantes. Por que o modelo piloto de cadeiras teve apenas 28,38% de acerto? Por dois motivos do dia a dia: primeiro, as diferenças de formato — o que chamamos de variação morfológica —, já que existem cadeiras de madeira, estofadas, giratórias e de formatos muito diferentes; e segundo, a oclusão, que acontece quando uma mesa, uma mochila ou uma pessoa encobre metade da cadeira na foto. O mesmo vale para peças muito pequenas do extintor, como o lacre: quando temos poucos registros e o objeto é difícil de enxergar de longe, isso nos mostra que é preciso coletar mais fotos focadas nessas peças e fazer um novo treinamento.”

---

## Slide 11 — Conclusão e Trabalhos Futuros (Duas Partes de Conteúdo | ~50 seg)
- **Conclusão (verbo corrigido):** O sistema **apresentou** alto desempenho de processamento (~12 ms por imagem, ou mais de 83 quadros por segundo — explicando a sigla **FPS**), aliando a verificação dos componentes, a calibração de limiares (84,50% em incêndio) e a geração automática dos laudos.
- **Trabalhos Futuros (distinção clara):** (1) Expandir o dataset com mais fotos e casos; (2) Incluir e testar **novos modelos de reconhecimento** (que é diferente de apenas pôr mais fotos no mesmo modelo); (3) Executar em dispositivos embarcados (quantização INT8); e (4) Testar sob baixa iluminação e oclusão.

> **Fala sugerida (Treino):**
> “Concluindo a apresentação: o sistema desenvolvido apresentou um ótimo desempenho de processamento, levando cerca de 12 milissegundos por imagem — o que significa uma taxa acima de 83 FPS, ou seja, a capacidade de analisar mais de 83 quadros por segundo. A arquitetura apresentou resultados consistentes ao unir a verificação das peças na subcamada, o ajuste dinâmico da nota de corte — chegando a 84,50% de acerto nos modelos de incêndio — e a geração automática do laudo em português em menos de dois segundos. Como trabalhos futuros, organizamos quatro frentes: primeiro, expandir o nosso banco de imagens com mais fotos de peças pequenas e novas normas; segundo, incluir e testar novos modelos de reconhecimento — ou seja, experimentar novas arquiteturas de IA, e não apenas colocar mais dados no mesmo modelo; terceiro, aplicar a compactação INT8 para rodar diretamente em dispositivos embarcados portáteis; e quarto, realizar testes específicos em locais com iluminação precária e objetos parcialmente encobertos.”

---

## Slide 12 — Referências Principais (Título e Conteúdo | ~10 seg)
- BRASIL (NR-18, 2020; NR-6, 2022)  |  EVERINGHAM et al. (PASCAL VOC, 2010)  |  FIELDING (REST, 2000)  |  INTEL CORPORATION (OpenVINO, 2026)  |  RAHMAN, ULUSOY & MEYDANLI (2021)  |  REDMON et al. (YOLO, 2016)  |  TERVEN & CÓRDOVA-ESPARZA (2023).

> **Fala sugerida (Treino):**
> “Aqui estão as principais referências normativas e científicas que embasaram o desenvolvimento da nossa pesquisa.”

---

## Slide 13 — Obrigado! (Cabeçalho da Seção | ~15 seg)
- **Contato:** kelvin.albuquerque@aluno.ifsp.edu.br  |  sovat@ifsp.edu.br
- **Agradecimentos:** Instituto Federal de Educação, Ciência e Tecnologia de São Paulo (IFSP) — Câmpus Campinas.

> **Fala sugerida (Treino):**
> “Agradeço ao IFSP Câmpus Campinas pelo suporte, ao meu orientador professor Dr. Ricardo Sovat por toda a orientação e apoio durante o trabalho, e a todos vocês pela atenção. Deixo nossos contatos na tela e fico à disposição para perguntas. Muito obrigado!”

---
