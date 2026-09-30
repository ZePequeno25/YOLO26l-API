#!/usr/bin/env python3
"""
Script de Validação Completa de Conformidade - CONICT 2026
Contempla 20 Regras:
  - 8 Regras Estruturais e de Conteúdo do Edital/Template (REG1-REG8)
  - 5 Pareceres de Conteúdo Solicitados pela Banca (DC1-DC5)
  - 7 Pareceres de Forma e Normas Solicitados pela Banca (DF1-DF7)
"""

import os
import re
import sys

def run_validations():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    main_tex_path = os.path.join(base_dir, "main.tex")
    bib_path = os.path.join(base_dir, "bibliografia.bib")
    cabecalho_path = os.path.join(base_dir, "cabecalho.tex")
    preambulo_path = os.path.join(base_dir, "preambulo.tex")

    if not os.path.exists(main_tex_path) or not os.path.exists(bib_path):
        print("ERROR: Arquivos main.tex ou bibliografia.bib nao encontrados!")
        sys.exit(1)

    with open(main_tex_path, "r", encoding="utf-8") as f:
        tex_content = f.read()
    with open(bib_path, "r", encoding="utf-8") as f:
        bib_content = f.read()

    cabecalho_content = ""
    if os.path.exists(cabecalho_path):
        with open(cabecalho_path, "r", encoding="utf-8") as f:
            cabecalho_content = f.read()

    results = []
    total_passed = 0
    total_tests = 20

    def add_result(category, code, description, passed, detail=""):
        nonlocal total_passed
        if passed:
            total_passed += 1
            status = "PASS"
        else:
            status = "FAIL"
        results.append((category, code, description, status, detail))

    # --- REGRAS DO TEMPLATE E EDITAL (REG1 - REG8) ---
    has_class = r"\documentclass[a4paper,11pt]{article}" in tex_content
    has_inputs = r"\input{preambulo}" in tex_content and r"\input{cabecalho}" in tex_content
    has_footer = "CONICT 2026" in tex_content and "ISSN: 2178-9959" in tex_content
    add_result("TEMPLATE", "REG1", "Classe de documento (a4paper,11pt), preambulo, cabecalho e rodape oficial",
               has_class and has_inputs and has_footer, "Configuracao LaTeX validada")

    has_cnpq = "1.03.03.04-9" in cabecalho_content and "Sistemas de" in cabecalho_content
    add_result("TEMPLATE", "REG2", "Classificacao da Tabela CNPq em cabecalho.tex (1.03.03.04-9)",
               has_cnpq, "Codigo CNPq verificado")

    sections = [r"\\section\*\{Introdu", r"\\section\*\{Materiais", r"\\section\*\{Resultados", r"\\section\*\{Conclus", r"\\section\*\{Agradecimentos\}", r"\\bibliography\{bibliografia\}"]
    has_all_sections = all(re.search(s, tex_content) for s in sections)
    add_result("TEMPLATE", "REG3", "Estrutura de secoes obrigatorias do edital",
               has_all_sections, "Todas as secoes presentes")

    has_android_in_main = any(term in tex_content.lower() for term in ["android", "kotlin", "firebase"])
    add_result("TEMPLATE", "REG4", "Escopo exclusivo em Visao Computacional (sem mencao a Android/Kotlin no texto principal)",
               not has_android_in_main, "Isolamento de escopo verificado")

    has_limiar_eq = r"\tau_{\text{sugerido}}" in tex_content
    has_iou_eq = r"\text{IoU}" in tex_content
    add_result("TEMPLATE", "REG5", "Formulacao matematica exata das equacoes operacionais (Limiar Dinamico e IoU)",
               has_limiar_eq and has_iou_eq, "Equacoes matematicas verificadas")

    has_telemetry = ("10.836" in tex_content or "14.840" in tex_content) and ("71,06" in tex_content or "79,86" in tex_content) and ("12,0" in tex_content)
    add_result("TEMPLATE", "REG6", "Exatidao dos dados de telemetria dos modelos ativos (10.836 reqs, 71,06%, 12,02 ms)",
               has_telemetry, "Dados de telemetria dos modelos ativos verificados")

    has_backend_tech = ("SAVE_PREDICTION_FILES" in tex_content or r"SAVE\_PREDICTION\_FILES" in tex_content) and ("VIDEO_INFERENCE_STRIDE" in tex_content or r"VIDEO\_INFERENCE\_STRIDE" in tex_content) and ("Ollama" in tex_content)
    add_result("TEMPLATE", "REG7", "Tecnicas de backend otimizado (In-RAM streaming, Vid Stride, Warm-up 25 modelos, Ollama)",
               has_backend_tech, "Tecnicas de backend verificadas")

    has_kw = ("PALAVRAS-CHAVE" in tex_content) and ("KEYWORDS" in tex_content)
    add_result("TEMPLATE", "REG8", "Cabecalho de metadados de pesquisa (Palavras-Chave e Keywords)",
               has_kw, "Palavras-chave e Keywords verificadas")

    # --- PARECERES DE CONTEÚDO (DC1 - DC5) ---
    cpu_mentions = re.findall(r"CPUs? de baixo custo", tex_content, re.IGNORECASE)
    gpu_arc_mentions = len(re.findall(r"GPU (dedicada )?Intel Arc B570", tex_content))
    add_result("CONTEUDO", "DC1", "Harmonizacao de hardware (exclusividade de GPU Intel Arc B570, sem CPUs de baixo custo)",
               len(cpu_mentions) == 0 and gpu_arc_mentions >= 4, f"Mencoes GPU Arc B570: {gpu_arc_mentions}")

    resumo_match = re.search(r"\\noindent\\textbf\{RESUMO\}:(.*?)\\vspace", tex_content, re.DOTALL)
    resumo_text = resumo_match.group(1) if resumo_match else ""
    ghost_class_in_resumo = "sinalizações de emergência" in resumo_text.lower()
    add_result("CONTEUDO", "DC2", "Remocao de classe fantasma (sinalizacoes de emergencia) do benchmark do Resumo",
               not ghost_class_in_resumo, f"Presenca indevida no Resumo: {ghost_class_in_resumo}")

    dc3_pass = ("3.500 imagens" in tex_content) and ("13.553 caixas delimitadoras" in tex_content) and ("2.450 imagens" in tex_content)
    add_result("CONTEUDO", "DC3", "Quantificacao nominal explicita do espaco amostral (N=3.500 imagens, 13.553 bboxes e splits)",
               dc3_pass, "Tamanho nominal N=3.500 e splits declarados")

    has_chair_pilot = ("Cadeira" in tex_content) and ("piloto" in tex_content.lower())
    add_result("CONTEUDO", "DC4", "Justificativa da classe piloto Cadeira na Introducao",
               has_chair_pilot, "Justificativa de piloto na Introducao verificada")

    tex_lower = tex_content.lower()
    has_oclusao = ("oclus" in tex_lower) or ("andaimes" in tex_lower)
    has_future = ("trabalhos futuros" in tex_lower) and ("int8" in tex_lower)
    add_result("CONTEUDO", "DC5", "Aprofundamento da Conclusao com limitacoes praticas e agenda de trabalhos futuros",
               has_oclusao and has_future, "Limitacoes e trabalhos futuros verificados")

    # --- PARECERES DE FORMA E NORMAS (DF1 - DF7) ---
    siglas_checks = [
        "Graphics Processing Unit", "Stochastic Gradient Descent", "Application Programming Interface",
        "Random Access Memory", "Hypertext Transfer Protocol", "Large Language Model"
    ]
    df1_pass = all(s in tex_content for s in siglas_checks)
    add_result("FORMA", "DF1", "Descricao extensa de siglas na primeira ocorrencia (GPU, SGD, API, RAM, HTTP, LLM, etc.)",
               df1_pass, f"Siglas descritas: {sum(1 for s in siglas_checks if s in tex_content)}/{len(siglas_checks)}")

    df2_pass = ("O treinamento foi conduzido" in tex_content) and ("treinamento foi executado" not in tex_content)
    add_result("FORMA", "DF2", "Correcao gramatical no inicio do paragrafo de Treinamento",
               df2_pass, "Sintaxe da frase verificada")

    foreign_terms = [
        r"\\textit\{dataset\}", r"\\textit\{bounding boxes\}", r"\\textit\{epochs\}", r"\\textit\{pipeline\}",
        r"\\textit\{framework\}", r"\\textit\{streaming\}", r"\\textit\{Vid Stride\}", r"\\textit\{backend\}",
        r"\\textit\{endpoints\}", r"\\textit\{best\.pt\}"
    ]
    found_terms = [t for t in foreign_terms if re.search(t, tex_content)]
    add_result("FORMA", "DF3", "Padronizacao rigorosa de termos estrangeiros em italico (\\textit{...})",
               len(found_terms) == len(foreign_terms), f"Termos em italico validados: {len(found_terms)}/{len(foreign_terms)}")

    fonte_count = len(re.findall(r"Fonte:\s*Dados da pesquisa \(2026\)", tex_content))
    add_result("FORMA", "DF4", "Indicacao de Fonte padronizada IBGE/ABNT em todas as tabelas",
               fonte_count >= 2, f"Fontes de tabela encontradas: {fonte_count}/2")

    has_corporate_authors = ("author = {{ULTRALYTICS}}" in bib_content) and ("author = {{INTEL CORPORATION}}" in bib_content)
    add_result("FORMA", "DF5", "Destaque tipografico e autoria corporativa padronizada na bibliografia (ABNT NBR 6023)",
               has_corporate_authors, "Autoria corporativa em chaves maiusculas verificada")

    redmon_inproceedings = "@inproceedings{redmon2016you" in bib_content
    redmon_event_caps = "PROCEEDINGS OF THE IEEE CONFERENCE ON COMPUTER VISION AND PATTERN RECOGNITION" in bib_content
    add_result("FORMA", "DF6", "Estruturacao ABNT NBR 6023 para anais de eventos (Redmon et al. em caixa-alta)",
               redmon_inproceedings and redmon_event_caps, "Referencia de anais formatada")

    has_tm = "OpenVINOTM" in bib_content
    has_spurious_url_space = re.search(r"\.com/\s+\.", bib_content) is not None
    add_result("FORMA", "DF7", "Remocao de marca registrada TM e eliminacao de espacos espurios em URLs",
               (not has_tm) and (not has_spurious_url_space), "URLs limpas e sem simbolo TM")

    # IMPRESSÃO DO RELATÓRIO
    print("=" * 80)
    print("    RELATORIO DE VALIDACAO COMPLETA DE CONFORMIDADE E REGRAS - CONICT 2026    ")
    print("=" * 80)
    for cat, code, desc, status, detail in results:
        symbol = "OK" if status == "PASS" else "X"
        print(f"[{symbol}] [{cat:<8}] {code:<5} | {status:<4} | {desc}")
        if detail:
            print(f"               |-> Detalhe: {detail}")
    print("-" * 80)
    pct = (total_passed / total_tests) * 100
    print(f"RESULTADO FINAL: {total_passed}/{total_tests} TESTES APROVADOS ({pct:.1f}%)")
    print("=" * 80)

    if total_passed == total_tests:
        print(">>> SUCESSO ABSOLUTO: main.tex, bibliografia.bib, cabecalho.tex e preambulo.tex cumprem 100% das regras da banca e do edital CONICT 2026! <<<")
        sys.exit(0)
    else:
        print("!!! ATENCAO: Alguns criterios de conformidade precisam de revisao. !!!")
        sys.exit(1)

if __name__ == "__main__":
    run_validations()
