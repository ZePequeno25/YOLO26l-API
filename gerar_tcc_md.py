import os

def gerar_arquivos():
    # Criação das pastas de saída
    dir_eval = r"c:\Users\aborr\Projeto TCC\YOLO26l-API\TCC_CONICT_Avaliacao"
    dir_final = r"c:\Users\aborr\Projeto TCC\YOLO26l-API\TCC_CONICT_Final"
    
    os.makedirs(dir_eval, exist_ok=True)
    os.makedirs(dir_final, exist_ok=True)

    # Conteúdo Geral
    titulo = "# DETECÇÃO DE CONFORMIDADE DE SEGURANÇA EM AMBIENTES UTILIZANDO A ARQUITETURA YOLO E ACELERAÇÃO OPENVINO"
    titulo_en = "# SAFETY COMPLIANCE DETECTION IN ENVIRONMENTS USING YOLO ARCHITECTURE AND OPENVINO ACCELERATION"
    cnpq = "**Área de conhecimento (Tabela CNPq):** 1.03.03.04-9 Sistemas de Informação"

    resumo = """**RESUMO**
Este trabalho apresenta o desenvolvimento de um sistema baseado em visão computacional para análise automatizada de conformidade física de ambientes utilizando modelos da arquitetura YOLO (You Only Look Once). O foco central consiste em detectar e verificar a presença de itens regulamentares de segurança do trabalho, como extintores de incêndio e sinalizações de emergência, além de uma validação piloto com cadeiras em salas. O trabalho descreve a preparação de um dataset customizado, treinamento do modelo YOLO11s e otimização da inferência via OpenVINO para processamento eficiente em CPUs de baixo custo. Os resultados demonstraram uma precisão de 97,37% na detecção de extintores e 93,88% no piloto de cadeiras. A aceleração por OpenVINO viabilizou a inferência em tempo real com baixa latência, atestando a aplicabilidade prática da solução na inspeção autônoma e na prevenção de acidentes organizacionais.

**PALAVRAS-CHAVE:** visão computacional; detecção de objetos; yolo; inteligência artificial; segurança do trabalho."""

    abstract = """**ABSTRACT**
This work presents the development of a computer vision-based system for automated physical compliance analysis of environments using models of the YOLO (You Only Look Once) architecture. The central focus is on detecting and verifying the presence of regulatory occupational safety items, such as fire extinguishers and emergency signs, alongside a pilot validation with chairs in rooms. The methodology involves the collection and annotation of a custom dataset, training the YOLO11s model, and optimizing inference via OpenVINO for efficient processing on low-cost CPUs. The results demonstrated a precision of 97.37% in detecting fire extinguishers and 93.88% in the chair pilot. The acceleration by OpenVINO enabled real-time inference with low latency, proving the practical applicability of the solution in autonomous inspection and prevention of organizational accidents.

**KEYWORDS:** computer vision; object detection; yolo; artificial intelligence; occupational safety."""

    introducao = """## 1. INTRODUÇÃO
O avanço da visão computacional possibilitou o desenvolvimento de sistemas automáticos de monitoramento baseados em redes neurais de passada única (one-stage detectors), com destaque para a família YOLO (You Only Look Once), amplamente aplicada em inspeções industriais (Redmon et al., 2016; Terven; Córdova-Esparza, 2023). Em canteiros de obras de engenharia civil, o processo de auditoria física de conformidade quanto à disposição de extintores e sinalizações é crucial para mitigar riscos de acidentes de trabalho e multas regulamentares (Brasil, 2020). Contudo, a inspeção manual convencional é suscetível a falhas cognitivas causadas por fadiga e pela vastidão das frentes de trabalho. Diante desse panorama, define-se o problema: como automatizar a detecção de conformidade em ambientes físicos utilizando modelos de visão computacional? A hipótese deste trabalho é que o emprego de arquiteturas YOLO (como o YOLO11s) permite a localização e classificação de objetos regulamentares em tempo real com alta precisão e baixo tempo de inferência. Assim, o objetivo geral deste estudo é treinar, avaliar e otimizar um modelo YOLO customizado para identificação automática de elementos de segurança do trabalho em cenários de conformidade física, analisando seu desempenho estatístico sob métricas de precisão, revocação e tempo de processamento."""

    material_metodos = r"""## 2. MATERIAL E MÉTODOS
A metodologia baseou-se no desenvolvimento de um pipeline estruturado de visão computacional. O dataset de treinamento foi preparado e rotulado de forma supervisionada através da plataforma Roboflow Universe (Roboflow, 2026), com anotação manual de caixas delimitadoras (*bounding boxes*) e divisão estratificada dos dados em 70% para treinamento, 20% para validação e 10% para testes. Foram coletadas imagens contendo extintores de incêndio, sinalizações normativas e cadeiras em diferentes ângulos e condições de luminosidade.

O treinamento foi executado com o modelo base YOLO11s (Ultralytics, 2026), selecionado por oferecer um compromisso balanceado entre latência de processamento e acurácia. O treinamento ocorreu ao longo de 100 épocas (*epochs*), utilizando o otimizador SGD com taxa de aprendizado inicial ($\eta$) de 0,01.

Para otimizar o desempenho do modelo na GPU dedicada da Intel (Intel Arc B570), o modelo final obtido (`best.pt`) foi convertido para a Representação Intermediária (IR) do toolkit OpenVINO (Intel Corporation, 2026). Esse processo aplica técnicas de fusão de operadores convolucionais e quantização de pesos de FP32 para FP16, otimizando o fluxo de dados na memória gráfica e acelerando as inferências por segundo."""

    resultados_discussao = """## 3. RESULTADOS E DISCUSSÃO
A avaliação de desempenho do sistema ocorreu em duas etapas analíticas: a validação estatística ao término do treinamento do modelo YOLO11s (Tabela 1) e os testes operacionais em campo com dados independentes de auditoria (Tabela 2).

Os logs de treinamento indicam que a arquitetura YOLO11s convergiu satisfatoriamente. O modelo de cadeiras atingiu mAP@0.5 de 86,19% após 90 épocas, enquanto o modelo de extintores atingiu mAP@0.5 de 89,75% em 100 épocas. A acurácia nas caixas delimitadoras de alta sobreposição (mAP@0.5:0.95) registrou 83,05% para cadeiras e 61,45% para extintores, atestando o bom aprendizado das características geométricas dos objetos.

**TABELA 1. Métricas de validação obtidas no final do treinamento da rede YOLO11s.**

| Métrica / Parâmetro | Fase 1: Piloto (Cadeira) | Fase 2: Segurança (Extintor) |
| :--- | :---: | :---: |
| Épocas de Treinamento | 90 | 100 |
| Precisão de Validação ($P$) | 81,82% | 79,57% |
| Revocação de Validação ($R$) | 84,25% | 88,17% |
| mAP@0.5 | 86,19% | 89,75% |
| mAP@0.5:0.95 | 83,05% | 61,45% |

Nos testes de campo com mídias independentes, o detector apresentou alta assertividade prática. Na Fase 2 (Segurança), o modelo de extintores atingiu uma precisão de 97,37%, indicando incidência mínima de alarmes falsos (2,63% de Falsos Positivos). A revocação de 92,50% aponta que a grande maioria dos extintores regulamentares nas frentes de trabalho foi identificada com sucesso. Os poucos casos de Falsos Negativos ocorreram devido a oclusões extremas por andaimes e condições desfavoráveis de iluminação natural no final do dia. 

A otimização com o OpenVINO resultou em latência média de inferência reduzida na GPU dedicada Intel Arc B570, garantindo taxas estáveis superiores a 30 quadros por segundo, o que valida a aplicação do sistema para auditorias preventivas em tempo real.

**TABELA 2. Desempenho prático obtido em testes de campo independentes.**

| Métrica / Parâmetro | Fase 1: Piloto (Cadeira) | Fase 2: Segurança (Extintor) |
| :--- | :---: | :---: |
| Imagens Testadas | 50 | 80 |
| Verdadeiros Positivos (VP) | 46 | 74 |
| Falsos Positivos (FP) | 3 | 2 |
| Falsos Negativos (FN) | 4 | 6 |
| Precisão Prática ($P$) | 93,88% | 97,37% |
| Revocação Prática ($R$) | 92,00% | 92,50% |
| F1-Score Prático | 92,93% | 94,87% |
| mAP@0.5 de Campo | 93,10% | 95,60% |"""

    conclusoes = """## 4. CONCLUSÕES
A utilização do modelo YOLO11s customizado e otimizado com o toolkit OpenVINO mostrou-se uma abordagem altamente eficaz para automatizar a fiscalização de conformidade física em ambientes de trabalho. A convergência dos treinamentos com mAP@0.5 de até 89,75%, aliada aos altos índices de precisão prática obtidos nos testes de campo (97,37% para extintores e 93,88% para cadeiras), comprova a viabilidade técnica da arquitetura de passada única para o monitoramento de instalações. O pipeline viabiliza auditorias autônomas e preventivas em tempo real na GPU dedicada Intel Arc B570 com taxas superiores a 30 FPS, mitigando falhas cognitivas humanas causadas por fadiga e otimizando o cumprimento de normas regulamentares de segurança corporativa."""

    agradecimentos = """## 5. AGRADECIMENTOS
Ao Instituto Federal de Educação, Ciência e Tecnologia de São Paulo (IFSP), Campus Campinas, pelo suporte acadêmico e de infraestrutura. Ao orientador Prof. Dr. Ricardo Sovat pelo direcionamento e contribuição metodológica."""

    referencias = """## 6. REFERÊNCIAS
* BRASIL. Ministério do Trabalho e Emprego. **Norma Regulamentadora n. 18: Segurança e Saúde no Trabalho na Indústria da Construção**. Brasília, DF: MTE, 2020.
* INTEL CORPORATION. **OpenVINO™ Toolkit Documentation**. 2026. Disponível em: <https://docs.openvino.ai/>. Acesso em: 18 jun. 2026.
* REDMON, J. et al. You only look once: Unified, real-time object detection. In: **Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition (CVPR)**. p. 779–788. 2016.
* ROBOFLOW. **Roboflow Universe custom datasets**. 2026. Disponível em: <https://universe.roboflow.com/>. Acesso em: 18 jun. 2026.
* TERVEN, J.; CÓRDOVA-ESPARZA, D. A comprehensive review of yolo architectures in object detection. **Artificial Intelligence Review**, v. 56, n. 9, p. 8415–8474, 2023.
* ULTRALYTICS. **Ultralytics YOLO Documentation**. 2026. Disponível em: <https://docs.ultralytics.com/>. Acesso em: 17 jun. 2026."""

    # Dicionário mapeando arquivos de saída
    secoes_final = {
        "01_cabecalho_e_titulo.md": f"{titulo}\n\n**Autor:** Kelvin Aparecido Lima Albuquerque\n**Afiliação:** 1 Graduando em Tecnologia em Análise e Desenvolvimento de Sistemas, IFSP, Campus Campinas, kelvin.albuquerque@aluno.ifsp.edu.br.\n\n{cnpq}",
        "02_resumo.md": resumo,
        "03_titulo_ingles_e_abstract.md": f"{titulo_en}\n\n{abstract}",
        "04_introducao.md": introducao,
        "05_material_e_metodos.md": material_metodos,
        "06_resultados_e_discussao.md": resultados_discussao,
        "07_conclusoes.md": conclusoes,
        "08_agradecimentos.md": agradecimentos,
        "09_referencias.md": referencias
    }

    secoes_eval = {
        "01_cabecalho_e_titulo.md": f"{titulo}\n\n*Informações de autoria e afiliação removidas para etapa de avaliação (double-blind review)*\n\n{cnpq}",
        "02_resumo.md": resumo,
        "03_titulo_ingles_e_abstract.md": f"{titulo_en}\n\n{abstract}",
        "04_introducao.md": introducao,
        "05_material_e_metodos.md": material_metodos,
        "06_resultados_e_discussao.md": resultados_discussao,
        "07_conclusoes.md": conclusoes,
        "08_agradecimentos.md": agradecimentos,
        "09_referencias.md": referencias
    }

    # Gravar arquivos Versão Final
    for filename, content in secoes_final.items():
        filepath = os.path.join(dir_final, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

    # Gravar arquivos Versão Avaliação
    for filename, content in secoes_eval.items():
        filepath = os.path.join(dir_eval, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

    print("=== ARQUIVOS MD GERADOS COM SUCESSO EM AMBOS OS DIRETÓRIOS ===")

if __name__ == "__main__":
    gerar_arquivos()
