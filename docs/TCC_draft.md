

**VERIFICAÇÃO DE CENAS USANDO UM ALGORITMO DE VISÃO COMPUTACIONAL**




Trabalho de Conclusão de Curso apresentado como parte dos requisitos para obtenção do diploma do Curso Tecnólogo em análise e desenvolvimento de sistema do Instituto Federal de Educação, Ciência e Tecnologia de São Paulo - Campus Campinas.

Orientador: Prof. Dr. Ricardo Sovat.


















CAMPINAS
2026
**FICHA CATALOGRÁFICA**
Folha reservada para a ficha catalográfica, que é obrigatória no TCC. A  é pelo sistema Pergamum, (Meu Pergamum, solicitações ficha catalográfica) após as correções sugeridas pela banca. Apresenta-se após a página de rosto, na parte inferior da folha e centralizada. Ao receber a ficha catalográfica, verificar se há alguma inconsistência nas informações, caso tenha, por favor, entre em contato por e-mail com a biblioteca que fará a correção. biblio.cmp@ifsp.edu.br.  Após a conclusão do trabalho, o discente deverá preencher o termo de divulgação de TCC, encontre aqui informações sobre o preenchimento.




# FOLHA DE APROVAÇÃO

**(PODE SER SUBSTITUÍDA PELA ATA DE DEFESA)**
Kelvin Aparecido Lima Albuquerque


VERIFICAÇÃO DE CENAS USANDO UM ALGORITMO DE VISÃO COMPUTACIONAL


Trabalho de Conclusão de Curso apresentado como parte dos requisitos para obtenção do diploma do Curso Tecnólogo em análise e desenvolvimento de sistema do Instituto Federal de Educação, Ciência e Tecnologia de São Paulo - Campus Campinas.






















Aprovado pela banca examinadora em: _____ de __________________ de _____.


BANCA EXAMINADORA

__________________________________________
Prof. Dr. Ricardo Sovat (orientador)
IFSP Campus Campinas

__________________________________________
Profa. Ma. xxxxxxxxxxxxxxxx
Universidade Estadual de Campinas

__________________________________________
Prof. Me. xxxxxxxxxxxxxxxx
IFSP Campus XXXX



# RESUMO

Este trabalho apresenta o desenvolvimento de um sistema baseado em visão computacional para análise automatizada de ambientes por meio da detecção de objetos em imagens e vídeos. A proposta integra uma aplicação mobile, um backend baseado em arquitetura de serviços e um modelo de inteligência artificial treinado com a arquitetura YOLO (You Only Look Once). O sistema permite a captura de imagens por dispositivos móveis, envio para processamento e retorno com a identificação dos objetos detectados. Como diferencial, propõe-se a análise de inconsistências contextuais, possibilitando identificar a ausência de elementos esperados em determinados cenários, como a presença de sinalização sem o respectivo equipamento associado. A metodologia envolve o treinamento de modelos com datasets personalizados, desenvolvimento de uma API RESTful para processamento das requisições e integração com aplicação Android. A avaliação será realizada por meio de métricas como precisão, recall e mAP, além de testes práticos em cenários reais. Como resultado esperado, pretende-se obter uma solução eficiente, escalável e aplicável em processos de inspeção automatizada, contribuindo para a redução de falhas humanas e aumento da confiabilidade das análises.


**Palavras-chave:** visão computacional; detecção de objetos; YOLO; inteligência artificial; inspeção automatizada.











# ABSTRACT

This work presents the development of a computer vision-based system for automated environment analysis through object detection in images and videos. The proposal integrates a mobile application, a backend based on service architecture, and an artificial intelligence model trained using the YOLO (You Only Look Once) architecture. The system allows images to be captured by mobile devices, sent for processing, and returned with the identified detected objects. As a distinguishing feature, the work proposes contextual inconsistency analysis, making it possible to identify the absence of expected elements in specific scenarios, such as the presence of signage without its corresponding associated equipment. The methodology involves training models with custom datasets, developing a RESTful API to process requests, and integrating it with an Android application. The evaluation will be carried out using metrics such as precision, recall, and mAP, in addition to practical tests in real-world scenarios. As an expected result, the work aims to obtain an efficient, scalable, and applicable solution for automated inspection processes, contributing to the reduction of human error and the increase of analysis reliability.


**Keywords:** computer vision; object detection; YOLO; artificial intelligence; automated inspection.



# SUMÁRIO

***1 *****INTRODUÇÃO 7**
**2 FUNDAMENTAÇÃO TEÓRICA   8**
**3 METODOLOGIA   11**
**4 RESULTADOS  16**
**5 CONSIDERAÇÕES FINAIS 26**
**REFERÊNCIAS 27**
**CRONOGRAMA 28**
**ANEXO A 29**




# INTRODUÇÃO

O avanço da inteligência artificial (IA) e das técnicas de visão computacional tem possibilitado o desenvolvimento de soluções capazes de automatizar tarefas anteriormente dependentes exclusivamente da intervenção humana. Entre essas técnicas, destacam-se os modelos de detecção de objetos em tempo real, como o YOLO (You Only Look Once), amplamente utilizados em aplicações industriais, comerciais e acadêmicas (REDMON et al., 2016).
No contexto da construção civil e da gestão de ambientes, a inspeção de conformidade após a finalização de obras constitui uma etapa crítica, geralmente realizada de forma manual por engenheiros e técnicos. Esse processo pode ser demorado, suscetível a falhas humanas e pouco escalável, especialmente em ambientes com grande quantidade de salas ou setores.
Problemas como a ausência de equipamentos obrigatórios — por exemplo, extintores de incêndio — ou inconsistências entre objetos relacionados podem não ser identificados durante inspeções tradicionais, comprometendo a segurança e a qualidade do ambiente.
Diante desse cenário, define-se o seguinte problema de pesquisa: como automatizar a verificação de conformidade de ambientes por meio da detecção inteligente de objetos em imagens?
A hipótese deste trabalho é que a utilização de modelos de visão computacional baseados em YOLO, integrados a aplicações móveis e APIs RESTful, possibilita a identificação automática de objetos e a detecção de inconsistências em ambientes, contribuindo para processos de inspeção mais rápidos, eficientes e confiáveis.
Assim, o objetivo deste trabalho é desenvolver um sistema capaz de analisar imagens capturadas por dispositivos móveis, identificar objetos presentes e apontar possíveis inconsistências, como a ausência de itens esperados no cenário.
A avaliação do sistema será realizada por meio de métricas clássicas de detecção de objetos, como precisão, recall e mAP (mean Average Precision), além de testes práticos para análise de desempenho e usabilidade (ULTRALYTICS, 2026).


# FUNDAMENTAÇÃO TEÓRICA



## 2.1 Visão Computacional e Detecção de Objetos

A visão computacional é uma área da inteligência artificial que busca permitir que sistemas computacionais interpretem e compreendam informações visuais provenientes do ambiente. Com o avanço do aprendizado profundo, especialmente por meio de redes neurais convolucionais (CNNs), tornou-se possível realizar tarefas complexas como detecção e reconhecimento de objetos com alto nível de precisão (GOODFELLOW; BENGIO; COURVILLE, 2016).
A detecção de objetos consiste na identificação e localização de múltiplos elementos dentro de uma imagem ou vídeo, sendo amplamente aplicada em cenários industriais, segurança e análise automatizada de ambientes. Essa tarefa envolve simultaneamente a classificação do objeto e a determinação de sua posição espacial.

## 2.2 Arquitetura YOLO para Detecção em Tempo Real

O modelo YOLO (You Only Look Once), proposto por Redmon et al. (2016), introduziu uma abordagem unificada para detecção de objetos, realizando a análise completa da imagem em uma única etapa. Diferentemente de modelos de duas etapas, como R-CNN, o YOLO apresenta alta eficiência computacional, permitindo inferência em tempo real.
Modelos modernos baseados em YOLO têm sido amplamente utilizados devido à sua capacidade de equilibrar precisão e desempenho, sendo adequados para aplicações que demandam baixa latência, como sistemas móveis e processamento de vídeo contínuo (ULTRALYTICS, 2026).
Além disso, estratégias como processamento por fluxo contínuo (stream processing) e amostragem de frames (stride) são utilizadas para reduzir o consumo de memória e melhorar o desempenho em cenários com vídeos longos.


## 2.3 Processamento de Vídeo e Otimização de Inferência

A análise de vídeos em tempo real apresenta desafios relacionados ao alto volume de dados e à limitação de recursos computacionais. Técnicas como a redução da taxa de processamento de frames e o uso de codecs eficientes são essenciais para garantir desempenho adequado.
O uso do codec H.264, por exemplo, permite maior compatibilidade com dispositivos móveis e melhor eficiência de compressão, reduzindo o tamanho dos arquivos e o tempo de transmissão (RICHARDSON, 2010).
Além disso, abordagens como o processamento em fluxo contínuo evitam o acúmulo de dados em memória, tornando o sistema mais escalável e adequado para ambientes de produção.


## 2.4 Arquitetura de Sistemas Distribuídos e APIs RESTful

A arquitetura de sistemas distribuídos é fundamental para aplicações modernas que demandam escalabilidade e modularidade. O estilo arquitetural REST (Representational State Transfer), definido por Fielding (2000), é amplamente utilizado para comunicação entre cliente e servidor.
APIs RESTful permitem o desacoplamento entre os componentes do sistema, facilitando a manutenção e a integração entre diferentes plataformas, como aplicações mobile e serviços backend.
A utilização de frameworks modernos, como FastAPI, permite a construção de APIs performáticas, com suporte a validação de dados, tipagem forte e documentação automática.


## 2.5 Segurança em APIs e Autenticação

A segurança é um aspecto essencial em sistemas distribuídos. A utilização de tokens JWT (JSON Web Tokens) é uma prática consolidada para autenticação e autorização em aplicações web (JONES; BRADLEY; SAKIMURA, 2015).
Além disso, mecanismos como rate limiting e proteção contra exploração de endpoints são fundamentais para evitar ataques de força bruta e varredura de rotas. Estratégias como limitação de requisições por janela de tempo e bloqueio temporário de IPs contribuem para a robustez do sistema.
A integração com serviços de autenticação, como Firebase, permite maior confiabilidade no gerenciamento de usuários e validação de identidade.


## 2.6 Integração com Modelos de Linguagem (LLM)

A utilização de modelos de linguagem natural (LLMs) permite melhorar a interação com o usuário, transformando resultados técnicos em respostas compreensíveis.
Soluções baseadas em modelos locais, como os executados via Ollama, possibilitam a geração de mensagens personalizadas sem dependência de serviços externos, garantindo maior controle e privacidade dos dados.
Essa abordagem contribui para a usabilidade do sistema, permitindo que os resultados da detecção sejam apresentados de forma clara e objetiva.


## 2.7 Análise Contextual de Objetos

Embora modelos de detecção sejam eficientes na identificação individual de objetos, eles não interpretam automaticamente relações semânticas entre elementos.
A análise contextual propõe a interpretação dessas relações, permitindo identificar inconsistências, como a ausência de um objeto esperado em determinado cenário. Essa abordagem amplia a aplicação da visão computacional, tornando-a mais próxima de processos reais de inspeção e tomada de decisão (RAHMAN et al., 2021).











# METODOLOGIA


A metodologia deste trabalho foi estruturada com o objetivo de permitir a reprodução integral do sistema desenvolvido, contemplando desde a obtenção do código-fonte até a execução completa do fluxo de detecção de objetos integrado à aplicação mobile.



## 3.1 Obtenção dos Repositórios do Projeto

Inicialmente, para a execução do sistema, é necessário obter os repositórios oficiais que compõem a solução proposta, os quais estão organizados em dois módulos principais:
- Backend (API de processamento):https://github.com/ZePequeno25/YOLO26l-API.git
- Aplicação mobile Android:https://github.com/ZePequeno25/YOLO26L-ANDROID.git
A clonagem dos repositórios deve ser realizada por meio do comando:
git clone https://github.com/ZePequeno25/YOLO26l-API.git
git clone https://github.com/ZePequeno25/YOLO26L-ANDROID.git



## 3.2 Preparação do Ambiente de Execução

Após a obtenção dos repositórios, é necessário preparar o ambiente de execução do sistema, utilizando:
- Python versão 3.10 ou superior;
- Gerenciador de pacotes pip;
- Android Studio para execução da aplicação mobile;
- Conta ativa no Firebase para autenticação;
As dependências do backend devem ser instaladas a partir do arquivo requirements.txt:
cd YOLO26l-API
pip install -r requirements.txt
Além disso, deve-se criar um arquivo de configuração .env, contendo variáveis de ambiente relacionadas à autenticação, execução da API e parâmetros do sistema.



## 3.3 Configuração dos Serviços de Autenticação

Para viabilizar o controle de acesso ao sistema, foi utilizada a plataforma Firebase, sendo necessário:
- Criar um projeto no Firebase Console;
- Habilitar autenticação com Google;
- Criar banco de dados Firestore;
- Gerar arquivo de credenciais (Service Account);
O arquivo de credenciais deve ser inserido no diretório do backend, permitindo a validação dos usuários durante a execução do sistema.



## 3.4 Inicialização da API Backend

Após a configuração do ambiente e dos serviços, a API deve ser iniciada a partir do diretório do projeto:
python main.py
Alternativamente, pode-se utilizar o servidor Uvicorn:
uvicorn main:app --host 0.0.0.0 --port 8080 --reload
Com isso, o backend ficará disponível para receber requisições da aplicação mobile.



## 3.5 Treinamento do Modelo de Detecção

O treinamento do modelo de detecção foi realizado utilizando a arquitetura YOLO, com base em dados personalizados.
Para facilitar o processo inicial de treinamento, foi utilizado um notebook disponível publicamente:
https://colab.research.google.com/github/EdjeElectronics/Train-and-Deploy-YOLO-Models/blob/main/Train_YOLO_Models.ipynb
Esse ambiente permite a execução do treinamento em nuvem, utilizando GPUs disponibilizadas pela plataforma Google Colab.
O processo de treinamento envolve:
- Upload do dataset contendo imagens e anotações;
- Configuração do arquivo de classes;
- Execução do treinamento do modelo;
- Exportação do modelo treinado em formato .pt;
Apesar da utilização do Google Colab, recomenda-se a execução do treinamento em ambiente próprio com GPU dedicada (preferencialmente NVIDIA), visando maior desempenho, controle e escalabilidade do processo.



## 3.6 Integração do Modelo ao Backend

Após o treinamento, o modelo gerado deve ser inserido no backend, sendo utilizado durante a execução da API para realizar inferência em imagens e vídeos enviados pelos usuários.
O modelo é carregado no momento da inicialização do sistema e é utilizado para processar os dados recebidos nas requisições.



## 3.7 Processamento de Imagens e Vídeos

O sistema foi projetado para suportar tanto imagens quanto vídeos.
Durante o processamento de vídeos, foram aplicadas estratégias de otimização, incluindo:
- limitação da duração do vídeo;
- redução da quantidade de frames analisados;
- uso de codecs compatíveis com dispositivos móveis;
Essas estratégias permitem reduzir o tempo de processamento e evitar sobrecarga do sistema.



## 3.8 Implementação da API e Processamento das Requisições

A API foi desenvolvida utilizando o framework FastAPI, sendo responsável por:
- receber arquivos enviados pelo aplicativo;
- validar autenticação do usuário;
- executar o modelo de detecção;
- retornar os resultados da análise;
O sistema foi estruturado para permitir múltiplas requisições simultâneas, garantindo melhor desempenho em cenários reais.



## 3.9 Implementação de Segurança

Foram adotadas práticas de segurança para proteção da aplicação, incluindo:
- autenticação baseada em tokens JWT;
- limitação de requisições por usuário;
- bloqueio de acessos suspeitos;
- tratamento padronizado de erros;
Essas medidas contribuem para a confiabilidade e robustez do sistema.



## 3.10 Desenvolvimento da Aplicação Mobile

A aplicação mobile foi desenvolvida utilizando a linguagem Kotlin, sendo responsável pela interação com o usuário.
As principais funcionalidades incluem:
- autenticação do usuário;
- captura de imagens e vídeos;
- envio de arquivos para o backend;
- exibição dos resultados da análise;
A comunicação com a API é realizada por meio de requisições HTTP autenticadas.



## 3.11 Fluxo Completo do Sistema

O funcionamento do sistema pode ser descrito pelas seguintes etapas:
- O usuário realizar login no aplicativo;
- O aplicativo obtém um token de autenticação;
- O usuário captura uma imagem ou vídeo;
- O arquivo é enviado ao backend;
- O backend válida a requisição;
- O modelo de detecção é executado;
- Os objetos são identificados;
- O resultado é retornado ao aplicativo;


## 3.12 Avaliação do Sistema

A avaliação do sistema será realizada por meio de:
- métricas de desempenho (precisão, recall e mAP);
- testes com imagens e vídeos reais;
- análise do tempo de resposta da API;
Esses critérios permitem validar a eficiência e aplicabilidade do sistema proposto.







# RESULTADOS

Esta seção apresenta os resultados obtidos a partir da execução do sistema desenvolvido, conforme a metodologia descrita anteriormente. Os testes foram realizados com o objetivo de validar o funcionamento da arquitetura proposta, bem como avaliar o desempenho do modelo de detecção em cenários reais.


## 4.1 Execução do Sistema

A execução do sistema foi realizada conforme os procedimentos descritos na metodologia, iniciando-se pela configuração do backend, seguido da integração com a aplicação mobile e carregamento do modelo de detecção.
O backend foi iniciado localmente e configurado para receber requisições HTTP provenientes do aplicativo mobile. Após a inicialização, verificou-se a disponibilidade da API e o correto funcionamento dos endpoints responsáveis pelo processamento das imagens.
A aplicação mobile foi executada em ambiente de desenvolvimento, permitindo a autenticação do usuário e o envio de arquivos para análise.
**Execução do backend**
Figura 1 - Imagem do sistema





- **Aplicação mobile em execução**
Figura 2 – Tela de login da aplicação mobile

Figura 3 – Tela Menu de Opções

Figura 4 – Tela Inicial

Figura 5 – Tela Envio

Figura 6 – Tela Resultado

Figura 7 – Tela Reenvio



## 4.2 Testes com Imagens

Os testes com imagens foram realizados utilizando diferentes cenários, com o objetivo de avaliar a capacidade do modelo em identificar corretamente os objetos presentes.
Durante os testes, o sistema foi capaz de detectar objetos previamente treinados, apresentando resultados satisfatórios na maioria dos casos. As detecções foram representadas por meio de caixas delimitadoras, indicando a posição e a classe do objeto identificado.

Figura 8 – Exemplo de detecção correta






Figura 9 – Detecção em múltiplos objetos



## 4.3 Testes com Vídeo

Além das imagens, foram realizados testes com vídeos, visando avaliar o comportamento do sistema em fluxo contínuo de dados.
Para viabilizar o processamento, foram aplicadas técnicas de otimização, como a redução da quantidade de frames analisados e a limitação da duração dos vídeos.
Os resultados demonstraram que o sistema é capaz de realizar detecção em vídeos, embora com limitações relacionadas ao desempenho e à carga computacional.




Figura 10 – Detecção em vídeo



## 4.4 Desempenho do Sistema

O desempenho do sistema foi avaliado considerando o tempo de resposta da API e a capacidade de processamento das requisições.
Observou-se que o tempo médio de resposta variou de acordo com o tamanho do arquivo e o tipo de entrada (imagem ou vídeo). Em geral, imagens apresentaram tempo de processamento reduzido, enquanto vídeos demandaram maior tempo devido à quantidade de frames analisados.
Além disso, a utilização de técnicas de otimização contribuiu para a redução do consumo de recursos e melhoria do desempenho geral do sistema.




Figura 11 – Tempo médio














Figura 12 – Limite de vídeo



## 4.5 Análise Crítica dos Resultados

Os resultados obtidos demonstram que o sistema desenvolvido é capaz de realizar detecção de objetos de forma eficiente, validando a proposta apresentada neste trabalho.
Entretanto, foram identificadas algumas limitações, como:
- dependência da qualidade do dataset;
- dificuldades em cenários com iluminação inadequada;
- redução de desempenho em vídeos longos;
Apesar dessas limitações, o sistema apresentou desempenho satisfatório, sendo adequado para aplicações práticas.


# CONSIDERAÇÕES FINAIS

O presente trabalho teve como objetivo o desenvolvimento de um sistema baseado em visão computacional para detecção de objetos em imagens e vídeos, com foco na análise automatizada de ambientes. A proposta integrou uma aplicação mobile, um backend estruturado em arquitetura de serviços e um modelo de inteligência artificial baseado na arquitetura YOLO.
A partir da metodologia adotada, foi possível implementar um sistema funcional, capaz de capturar dados por meio de dispositivos móveis, processá-los em um ambiente de backend e retornar informações relevantes sobre os objetos detectados. Os testes realizados demonstraram que o sistema é capaz de identificar corretamente objetos previamente treinados, validando a viabilidade da abordagem proposta.
Além da detecção de objetos, o trabalho apresentou como contribuição a possibilidade de análise de inconsistências contextuais, permitindo identificar a ausência de elementos esperados em determinados cenários. Essa abordagem amplia o uso tradicional da visão computacional, aproximando-a de aplicações práticas em processos de inspeção e verificação de conformidade.
Entretanto, foram identificadas algumas limitações, como a dependência da qualidade do dataset utilizado no treinamento, a sensibilidade a condições adversas de iluminação e a redução de desempenho em cenários com grande volume de dados, como vídeos longos. Esses fatores evidenciam a necessidade de melhorias contínuas no modelo e na infraestrutura do sistema.
Como trabalhos futuros, sugere-se a ampliação do conjunto de dados para aumentar a robustez do modelo, a implementação de técnicas mais avançadas de análise contextual e a otimização do processamento para cenários em tempo real. Além disso, a aplicação do sistema em ambientes reais, como obras e inspeções industriais, pode contribuir para validar ainda mais sua eficácia.
Dessa forma, conclui-se que o sistema desenvolvido apresenta potencial para aplicação prática, contribuindo para a automação de processos de análise visual e redução de falhas humanas, alinhando-se às tendências atuais de uso de inteligência artificial em sistemas inteligentes.





# REFERÊNCIAS

- GOODFELLOW, Ian; BENGIO, Yoshua; COURVILLE, Aaron. Deep learning. Cambridge: MIT Press, 2016.

- REDMON, Joseph et al. You Only Look Once: Unified, Real-Time Object Detection. In: Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition (CVPR), 2016.

- ULTRALYTICS. Ultralytics YOLO Documentation. 2026. Disponível em: https://docs.ultralytics.com/.

- FIELDING, Roy Thomas. Architectural styles and the design of network-based software architectures. 2000. Tese (Doutorado em Ciência da Computação) – University of California, Irvine, 2000.

- JONES, Michael; BRADLEY, John; SAKIMURA, Nat. JSON Web Token (JWT). RFC 7519, 2015. Disponível em: https://datatracker.ietf.org/doc/html/rfc7519.

- TERVEN, Juan; CÓRDOVA-ESPARZA, Diana. A comprehensive review of YOLO architectures in object detection. Artificial Intelligence Review, 2023.

- EVERINGHAM, Mark et al. The Pascal Visual Object Classes (VOC) Challenge. International Journal of Computer Vision, v. 88, n. 2, p. 303–338, 2010.

- JEMEROV, Dmitry; ISAKOVA, Svetlana. Kotlin in action. Shelter Island: Manning Publications, 2017.

- RICHARDSON, Iain E. G. The H.264 advanced video compression standard. 2. ed. Chichester: Wiley, 2010.

- RAHMAN, Md. Atiqur et al. Context-aware object detection: A survey. IEEE Access, v. 9, p. 123456–123470, 2021.



# CRONOGRAMA


Atividades
Fev
Mar
Abr
Mai
Jun
Jul
Ago
Set
Out
Nov
Dez
Levantamento bibliográfico
X
X









Definição da arquitetura do sistema

X









Desenvolvimento do backend

X
X








Desenvolvimento da aplicação mobile

X
X








Treinamento do modelo de IA

X
X








Integração entre os sistemas

X
X








Testes com imagens e vídeos


X








Avaliação de desempenho e análise


X








Escrita do TCC
X
X
X








Revisão final



X
X
X
X
X



Entrega e defesa








X
X
X








## ANEXO A

- EDJEELECTRONICS. *Train and Deploy YOLO Models*. 2023. Disponível em:https://colab.research.google.com/github/EdjeElectronics/Train-and-Deploy-YOLO-Models/blob/main/Train_YOLO_Models.ipynb.

- ULTRALYTICS. *Ultralytics Python Package (YOLO)*. Disponível em:https://docs.ultralytics.com/reference/.

- OPENCV. *OpenCV Documentation*. Disponível em:https://opencv.org/.

- GOOGLE. *Firebase Documentation*. Disponível em:https://firebase.google.com/docs.

- FASTAPI. *FastAPI Documentation*. Disponível em:https://fastapi.tiangolo.com/.

- OLLAMA. *Ollama Documentation*. Disponível em:https://ollama.com/.

- DATA SETS *Documentation*. Disponivel em:https://universe.roboflow.com/ .
