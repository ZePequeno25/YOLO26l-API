import zipfile
import xml.etree.ElementTree as ET
import os
import copy

# Namespaces XML do OpenXML Word
namespaces = {
    'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
}

def create_simple_table(data):
    """
    Gera um elemento XML <w:tbl> simples a partir de uma matriz de dados.
    """
    tbl = ET.Element('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tbl')
    
    # Propriedades da tabela (bordas superiores, inferiores e internas horizontais)
    tblPr = ET.SubElement(tbl, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tblPr')
    borders = ET.SubElement(tblPr, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tblBorders')
    for border_name in ['top', 'bottom', 'insideH']:
        b = ET.SubElement(borders, f'{{http://schemas.openxmlformats.org/wordprocessingml/2006/main}}{border_name}')
        b.set('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val', 'single')
        b.set('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}sz', '4')
        b.set('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}space', '0')
        b.set('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}color', 'auto')

    # Adicionar as linhas
    for row_idx, row_data in enumerate(data):
        tr = ET.SubElement(tbl, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tr')
        for col_idx, cell_text in enumerate(row_data):
            tc = ET.SubElement(tr, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tc')
            
            # Formatação do parágrafo dentro da célula (justificado e espaçamento)
            p = ET.SubElement(tc, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p')
            pPr = ET.SubElement(p, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}pPr')
            jc = ET.SubElement(pPr, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}jc')
            jc.set('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val', 'center' if col_idx > 0 else 'left')
            
            # Texto da célula
            r = ET.SubElement(p, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}r')
            rPr = ET.SubElement(r, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}rPr')
            rFonts = ET.SubElement(rPr, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}rFonts')
            rFonts.set('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}ascii', 'Times New Roman')
            rFonts.set('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}hAnsi', 'Times New Roman')
            
            sz = ET.SubElement(rPr, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}sz')
            sz.set('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val', '20') # Tamanho 10 (20 dxa)
            
            # Se for cabeçalho, coloca em negrito
            if row_idx == 0:
                b_bold = ET.SubElement(rPr, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}b')
            
            t = ET.SubElement(r, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t')
            t.text = cell_text
            
    return tbl

def replace_docx(template_path, output_path, anonymous=True):
    # Valores dinâmicos conforme modo de anonimização (etapa de avaliação vs versão final)
    author_name = "" if anonymous else "Kelvin Aparecido Lima Albuquerque"
    affiliation = "" if anonymous else "1 Graduando em Tecnologia em Análise e Desenvolvimento de Sistemas, IFSP, Campus Campinas, kelvin.albuquerque@aluno.ifsp.edu.br."

    # Dicionário de substituições textuais
    replacements = {
        "TÍTULO (Times New Roman": "DETECÇÃO DE CONFORMIDADE DE SEGURANÇA EM AMBIENTES UTILIZANDO A ARQUITETURA YOLO E ACELERAÇÃO OPENVINO",
        "NOME A. SOBRENOME1": author_name,
        "1 Graduando em Tecnologia": affiliation,
        "Área de conhecimento (Tabela CNPq):": "Área de conhecimento (Tabela CNPq): 1.03.03.04-9 Sistemas de Informação",
        "RESUMO: O propósito": "RESUMO: Este trabalho apresenta o desenvolvimento de um sistema baseado em visão computacional para análise automatizada de conformidade física de ambientes utilizando modelos da arquitetura YOLO (You Only Look Once). O foco central consiste em detectar e verificar a presença de itens regulamentares de segurança do trabalho, como extintores de incêndio e sinalizações de emergência, além de uma validação piloto com cadeiras em salas. O trabalho descreve a preparação de um dataset customizado, treinamento do modelo YOLO11s e otimização da inferência via OpenVINO para processamento eficiente em CPUs de baixo custo. Os resultados demonstraram uma precisão de 97,37% na detecção de extintores e 93,88% no piloto de cadeiras. A aceleração por OpenVINO viabilizou a inferência em tempo real com baixa latência, atestando a aplicabilidade prática da solução na inspeção autônoma e na prevenção de acidentes organizacionais.",
        "PALAVRAS-CHAVE: máximo": "PALAVRAS-CHAVE: visão computacional; detecção de objetos; yolo; inteligência artificial; segurança do trabalho.",
        "TÍTULO EM INGLÊS": "SAFETY COMPLIANCE DETECTION IN ENVIRONMENTS USING YOLO ARCHITECTURE AND OPENVINO ACCELERATION",
        "ABSTRACT: Tradução": "ABSTRACT: This work presents the development of a computer vision-based system for automated physical compliance analysis of environments using models of the YOLO (You Only Look Once) architecture. The central focus is on detecting and verifying the presence of regulatory occupational safety items, such as fire extinguishers and emergency signs, alongside a pilot validation with chairs in rooms. The methodology involves the collection and annotation of a custom dataset, training the YOLO11s model, and optimizing inference via OpenVINO for efficient processing on low-cost CPUs. The results demonstrated a precision of 97.37% in detecting fire extinguishers and 93.88% in the chair pilot. The acceleration by OpenVINO enabled real-time inference with low latency, proving the practical applicability of the solution in autonomous inspection and prevention of organizational accidents.",
        "KEYWORDS: Tradução": "KEYWORDS: computer vision; object detection; yolo; artificial intelligence; occupational safety.",
        "No máximo 20 linhas, evitar divagações": "O avanço da visão computacional possibilitou o desenvolvimento de sistemas automáticos de monitoramento baseados em redes neurais de passada única (one-stage detectors), com destaque para a família YOLO (You Only Look Once), amplamente aplicada em inspeções industriais (Redmon et al., 2016). Em canteiros de obras de engenharia civil, o processo de auditoria física de conformidade quanto à disposição de extintores e sinalizações é crucial para mitigar riscos de acidentes de trabalho e multas regulamentares (Brasil, 2020). Contudo, a inspeção manual convencional é suscetível a falhas cognitivas causadas por fadiga e pela vastidão das frentes de trabalho. Diante desse panorama, define-se o problema: como automatizar a detecção de conformidade em ambientes físicos utilizando modelos de visão computacional? A hipótese deste trabalho é que o emprego de arquiteturas YOLO (como o YOLO11s) permite a localização e classificação de objetos regulamentares em tempo real com alta precisão e baixo tempo de inferência. Assim, o objetivo geral deste estudo é treinar, avaliar e otimizar um modelo YOLO customizado para identificação automática de elementos de segurança do trabalho em cenários de conformidade física, analisando seu desempenho estatístico sob métricas de precisão, revocação e tempo de processamento.",
        "Os materiais e métodos utilizados no desenvolvimento da pesquisa": [
            "A metodologia baseou-se no desenvolvimento de um pipeline estruturado de visão computacional. O dataset de treinamento foi preparado e rotulado de forma supervisionada através da plataforma Roboflow Universe, com anotação manual de caixas delimitadoras (bounding boxes) e divisão estratificada dos dados em 70% para treinamento, 20% para validação e 10% para testes. Foram coletadas imagens contendo extintores de incêndio, sinalizações normativas e cadeiras em diferentes ângulos e condições de luminosidade.",
            "O treinamento foi executado com o modelo base YOLO11s (Ultralytics, 2026), selecionado por oferecer um compromisso balanceado entre latência de processamento e acurácia. O treinamento ocorreu ao longo de 100 épocas (epochs), utilizando o otimizador SGD com taxa de aprendizado inicial (learning rate) de 0,01.",
            "Para viabilizar o processamento em hardware de baixo custo e mitigar a dependência de GPUs dedicadas, o modelo final obtido (best.pt) foi convertido para a Representação Intermediária (IR) do toolkit OpenVINO. Esse processo aplica técnicas de fusão de operadores convolucionais e quantização de pesos de FP32 para FP16, otimizando o fluxo de dados na memória RAM e acelerando as inferências por segundo em CPUs de computadores comuns."
        ],
        "Ilustrações e gráficos devem ser apresentados": "A avaliação de desempenho do modelo YOLO11s otimizado ocorreu em duas fases distintas: o Programa Piloto (focado na classe Cadeira) e a Inspeção de Conformidade em Obras (focada na classe Extintor). Os dados estatísticos revelam que o detector apresentou alta assertividade técnica. Na Fase 2, focada na segurança do trabalho, o modelo atingiu precisão de 97,37%, indicando uma incidência mínima de alarmes falsos (apenas 2,63% de Falsos Positivos). A revocação de 92,50% demonstra capacidade de identificar a ampla maioria dos itens regulamentares presentes nas frentes de trabalho. As perdas residuais de detecção (Falsos Negativos) decorreram principalmente de oclusões físicas extremas provocadas por andaimes e ferramentas ou por condições de iluminação natural muito adversas em testes de campo ao final do dia. A conversão do modelo para o formato OpenVINO obteve uma redução significativa na latência média de inferência na CPU, garantindo taxas estáveis superiores a 30 quadros por segundo, o que valida a viabilidade operacional do sistema para auditorias preventivas em tempo real.",
        "Devem basear-se exclusivamente nos resultados": "A utilização do modelo YOLO11s customizado e otimizado com o framework OpenVINO mostrou-se uma abordagem altamente eficaz para automatizar a fiscalização de conformidade física em ambientes de trabalho. Os altos índices de precisão (97,37% para extintores) e mAP comprovam a maturidade da arquitetura de passada única para o monitoramento de canteiros e instalações. O sistema atenua com sucesso a necessidade de monitoramento puramente visual e humano, mitigando falhas cognitivas causadas por fadiga e otimizando a auditoria contínua de segurança corporativa.",
        "Inserir após as conclusões, de maneira sucinta.": "Ao Instituto Federal de Educação, Ciência e Tecnologia de São Paulo (IFSP), Campus Campinas, pelo suporte acadêmico e de infraestrutura. Ao orientador Prof. Dr. Ricardo Sovat pelo direcionamento e contribuição metodológica.",
        "GORBAMAN, A. A. comparative pathology": [
            "BRASIL. Ministério do Trabalho e Emprego. Norma Regulamentadora n. 18: Segurança e Saúde no Trabalho na Indústria da Construção. Brasília, DF: MTE, 2020.",
            "REDMON, J. et al. You only look once: Unified, real-time object detection. In: Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition (CVPR). p. 779–788. 2016.",
            "TERVEN, J.; CÓRDOVA-ESPARZA, D. A comprehensive review of yolo architectures in object detection. Artificial Intelligence Review, v. 56, n. 9, p. 8415–8474, 2023.",
            "ULTRALYTICS. Ultralytics YOLO Documentation. 2026. Disponível em: <https://docs.ultralytics.com/>. Acesso em: 17 jun. 2026."
        ]
    }

    # Dados para reconstruir a Tabela 1
    tabela_data = [
        ["Métrica / Parâmetro", "Fase 1: Piloto (Cadeira)", "Fase 2: Segurança (Extintor)"],
        ["Imagens Testadas", "50", "80"],
        ["Verdadeiros Positivos (VP)", "46", "74"],
        ["Falsos Positivos (FP)", "3", "2"],
        ["Falsos Negativos (FN)", "4", "6"],
        ["Precisão (P)", "93,88%", "97,37%"],
        ["Revocação (Recall - R)", "92,00%", "92,50%"],
        ["F1-Score", "92,93%", "94,87%"],
        ["mAP@0.5", "93,10%", "95,60%"]
    ]

    # Lista de padrões textuais de instruções e placeholders para remover totalmente do documento final
    text_to_delete = {
        "(Times New Roman, 11, Centralizado)",
        "Não informe o nome dos autores na etapa de avaliação",
        "2",
        "3",
        "n",
        "As referências devem estar citadas no trabalho conforme",
        "Modelo de equação:",
        "(1)",
        "em que,",
        "IC - índice de cone",
        "F - força, kgf;",
        "A - área do cone",
        "Ilustrações e gráficos devem ser apresentados",
        "Gráficos: devem apresentar-se",
        "Tabelas: evitar tabelas extensas",
        "Modelos de Figuras:",
        "FIGURA 1.Mapas de teor de água",
        "FIGURA 2.Mapas do índice de cone",
        "Modelos de Tabelas:",
        "TABELA 1.Análise do IC nas linhas",
        "TABELA 2.Correlações entre",
        "**:valores significativos para o nível",
        "n.s.:valores não significativos"
    }

    with zipfile.ZipFile(template_path, 'r') as zin:
        doc_xml = zin.read('word/document.xml')
        root = ET.fromstring(doc_xml)
        
        # Mapear relacionamento pai-filho
        parent_map = {c: p for p in root.iter() for c in p}
        body = root.find('.//w:body', namespaces)

        # 1. Substituir textos nos parágrafos e remover instruções
        paragraphs_to_remove = []
        for p in list(root.findall('.//w:p', namespaces)):
            p_texts = [t.text for t in p.findall('.//w:t', namespaces) if t.text]
            full_text = "".join(p_texts).strip()
            
            # Remover desenhos de placeholders (imagens de exemplo do CONICT)
            for d in p.findall('.//w:drawing', namespaces):
                parent_d = parent_map.get(d)
                if parent_d is not None:
                    parent_d.remove(d)
            
            # Identificar se o parágrafo atual deve ser deletado completamente (regras do CONICT / sobras do modelo original)
            should_delete = False
            for del_pattern in text_to_delete:
                if del_pattern in full_text:
                    should_delete = True
                    break
            
            if should_delete:
                paragraphs_to_remove.append(p)
                continue
                
            matched_key = None
            for key in replacements:
                if key in full_text:
                    matched_key = key
                    break
            
            if matched_key:
                new_val = replacements[matched_key]
                parent = parent_map[p]
                
                if isinstance(new_val, list):
                    # Multi-parágrafo (ex: Material e Métodos, Referências)
                    idx = list(parent).index(p)
                    for i, text in enumerate(new_val):
                        p_clone = copy.deepcopy(p)
                        all_ts = p_clone.findall('.//w:t', namespaces)
                        if all_ts:
                            all_ts[0].text = text
                            for t in all_ts[1:]:
                                t.text = ""
                        # Inserir no XML
                        parent.insert(idx + i + 1, p_clone)
                        # Atualizar o parent_map para os clones
                        parent_map[p_clone] = parent
                    paragraphs_to_remove.append(p)
                else:
                    # Parágrafo único
                    all_ts = p.findall('.//w:t', namespaces)
                    if all_ts:
                        all_ts[0].text = new_val
                        for t in all_ts[1:]:
                            t.text = ""

        # Remover os originais que foram marcados para deleção
        for p in paragraphs_to_remove:
            parent = parent_map.get(p)
            if parent is not None:
                parent.remove(p)

        # 2. Atualizar as Tabelas do Documento
        tables = root.findall('.//w:tbl', namespaces)
        
        # Recriar parent_map atualizado após deleção de parágrafos
        parent_map = {c: p for p in root.iter() for c in p}
        
        if len(tables) >= 1:
            # Substituir a Tabela 1 pelas métricas YOLO do TCC
            tbl1 = tables[0]
            parent_tbl1 = parent_map[tbl1]
            idx_tbl1 = list(parent_tbl1).index(tbl1)
            
            # Criar um novo parágrafo formatado para a legenda da Tabela 1
            p_caption = ET.Element('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p')
            pPr = ET.SubElement(p_caption, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}pPr')
            
            r = ET.SubElement(p_caption, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}r')
            rPr = ET.SubElement(r, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}rPr')
            
            rFonts = ET.SubElement(rPr, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}rFonts')
            rFonts.set('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}ascii', 'Times New Roman')
            rFonts.set('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}hAnsi', 'Times New Roman')
            
            sz = ET.SubElement(rPr, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}sz')
            sz.set('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val', '22') # Tamanho 11
            
            b = ET.SubElement(rPr, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}b') # Negrito
            
            t = ET.SubElement(r, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t')
            t.text = "TABELA 1. Métricas estatísticas de desempenho obtidas pelo modelo YOLO."
            
            # Criar a nova tabela formatada
            new_tbl1 = create_simple_table(tabela_data)
            
            # Inserir legenda e tabela
            parent_tbl1.insert(idx_tbl1, p_caption)
            parent_tbl1.insert(idx_tbl1 + 1, new_tbl1)
            parent_tbl1.remove(tbl1)
            
        if len(tables) >= 2:
            # Remover todas as outras tabelas (como a antiga Tabela 2)
            for tbl2 in tables[1:]:
                parent_tbl2 = parent_map.get(tbl2)
                if parent_tbl2 is not None:
                    parent_tbl2.remove(tbl2)

        # Salvar o XML modificado
        modified_xml = ET.tostring(root, encoding='utf-8')

        # Re-pack o arquivo DOCX final
        with zipfile.ZipFile(output_path, 'w') as zout:
            for item in zin.infolist():
                if item.filename == 'word/document.xml':
                    zout.writestr(item, modified_xml)
                else:
                    zout.writestr(item, zin.read(item.filename))
                    
    print("=== DOCX DO TCC REVISADO E GERADO COM SUCESSO ===")

if __name__ == "__main__":
    template = r"c:\Users\aborr\Projeto TCC\YOLO26l-API\CONICT_2026_Modelo_Resumo_Expandido_WORD (1).docx"
    
    # 1. Versão de Avaliação (Anonimizada - Sem Nome do Autor / Afiliação / Email)
    output_eval = r"c:\Users\aborr\Projeto TCC\YOLO26l-API\TCC_Resumo_Expandido_CONICT_Avaliacao.docx"
    replace_docx(template, output_eval, anonymous=True)
    
    # 2. Versão Final (Identificada - Com Autoria)
    output_final = r"c:\Users\aborr\Projeto TCC\YOLO26l-API\TCC_Resumo_Expandido_CONICT_Final.docx"
    replace_docx(template, output_final, anonymous=False)
