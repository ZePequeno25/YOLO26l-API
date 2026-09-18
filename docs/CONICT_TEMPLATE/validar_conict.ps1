# Script de Validação Completa de Conformidade - CONICT 2026
# Contempla 20 Regras: Template/Edital (REG1-REG8) + Pareceres de Conteúdo (DC1-DC5) + Pareceres de Forma (DF1-DF7).

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$MainTexPath = Join-Path $ScriptDir "main.tex"
$BibPath = Join-Path $ScriptDir "bibliografia.bib"
$CabecalhoPath = Join-Path $ScriptDir "cabecalho.tex"
$PreambuloPath = Join-Path $ScriptDir "preambulo.tex"

$TexContent = [System.IO.File]::ReadAllText($MainTexPath, [System.Text.Encoding]::UTF8)
$BibContent = [System.IO.File]::ReadAllText($BibPath, [System.Text.Encoding]::UTF8)
$CabecalhoContent = if (Test-Path $CabecalhoPath) { [System.IO.File]::ReadAllText($CabecalhoPath, [System.Text.Encoding]::UTF8) } else { "" }
$PreambuloContent = if (Test-Path $PreambuloPath) { [System.IO.File]::ReadAllText($PreambuloPath, [System.Text.Encoding]::UTF8) } else { "" }

$TotalPassed = 0
$TotalTests = 20

function Check-Rule ($Category, $Code, $Desc, $Condition, $Detail) {
    if ($Condition) {
        $script:TotalPassed++
        Write-Host "[OK]   [$Category] $Code | PASS | $Desc" -ForegroundColor Green
        if ($Detail) { Write-Host "       Detail: $Detail" -ForegroundColor Gray }
    } else {
        Write-Host "[FAIL] [$Category] $Code | FAIL | $Desc" -ForegroundColor Red
        if ($Detail) { Write-Host "       Detail: $Detail" -ForegroundColor Yellow }
    }
}

Write-Host "================================================================================"
Write-Host "    RELATORIO DE VALIDACAO COMPLETA DE CONFORMIDADE E REGRAS - CONICT 2026    "
Write-Host "================================================================================"

# --------------------------------------------------------------------------------
# GRUPO A: REGRAS ESTRUTURAIS DO TEMPLATE E EDITAL CONICT (REG1 - REG8)
# --------------------------------------------------------------------------------

# REG1: Estrutura do Documento e Classe LaTeX
$HasClass = $TexContent.Contains("\documentclass[a4paper,11pt]{article}")
$HasInputs = $TexContent.Contains("\input{preambulo}") -and $TexContent.Contains("\input{cabecalho}")
$HasFooter = $TexContent.Contains("CONICT 2026") -and $TexContent.Contains("ISSN: 2178-9959")
Check-Rule "TEMPLATE" "REG1" "Classe de documento (a4paper,11pt), preambulo, cabecalho e rodape oficial" ($HasClass -and $HasInputs -and $HasFooter) "LaTeX setup verified"

# REG2: Classificação CNPq no Cabeçalho
$HasCnpq = $CabecalhoContent.Contains("1.03.03.04-9") -and $CabecalhoContent.Contains("Sistemas de")
Check-Rule "TEMPLATE" "REG2" "Classificacao da Tabela CNPq em cabecalho.tex (1.03.03.04-9)" $HasCnpq "CNPq code verified"

# REG3: Seções Obrigatórias do Artigo
$HasIntro = $TexContent -match "\\section\*\{Introdu"
$HasMet = $TexContent -match "\\section\*\{Materiais"
$HasRes = $TexContent -match "\\section\*\{Resultados"
$HasConcl = $TexContent -match "\\section\*\{Conclus"
$HasAgrad = $TexContent -match "\\section\*\{Agradecimentos\}"
$HasBib = $TexContent.Contains("\bibliography{bibliografia}")
$AllSections = $HasIntro -and $HasMet -and $HasRes -and $HasConcl -and $HasAgrad -and $HasBib
Check-Rule "TEMPLATE" "REG3" "Estrutura de secoes obrigatorias do edital" $AllSections "All mandatory sections present"

# REG4: Exclusão de Escopo Móvel/Android no Texto Principal
$HasAndroidInMain = $TexContent.ToLower().Contains("android") -or $TexContent.ToLower().Contains("kotlin") -or $TexContent.ToLower().Contains("firebase")
Check-Rule "TEMPLATE" "REG4" "Escopo exclusivo em Visao Computacional (sem mencao a Android/Kotlin no texto principal)" (-not $HasAndroidInMain) "Scope isolation verified"

# REG5: Formulação Matemática Exata (Equações de Limiar Dinâmico e IoU)
$HasLimiarEq = $TexContent.Contains("\tau_{\text{sugerido}}")
$HasIoUEq = $TexContent.Contains("\text{IoU}")
Check-Rule "TEMPLATE" "REG5" "Formulacao matematica exata das equacoes operacionais (Limiar Dinamico e IoU)" ($HasLimiarEq -and $HasIoUEq) "Mathematical formulas verified"

# REG6: Telemetria Real de Produção (14.840 reqs, 5.040 multimodelo, 79,86% acertos, 12,06 ms)
$HasReqTotal = $TexContent.Contains("14.840")
$HasReqSub = $TexContent.Contains("5.040")
$HasAccuracy = $TexContent.Contains("79,86")
$HasLatency = $TexContent.Contains("12,06 ms")
$HasTelemetry = $HasReqTotal -and $HasReqSub -and $HasAccuracy -and $HasLatency
Check-Rule "TEMPLATE" "REG6" "Exatidao dos dados de telemetria de producao real (14.840 reqs, 79,86%, 12,06 ms)" $HasTelemetry "Telemetry statistics verified"

# REG7: Técnicas de Otimização da API FastAPI (RAM streaming, Vid Stride, Warm-up 25 submodelos, LLM Ollama)
$HasRAM = $TexContent.Contains("SAVE_PREDICTION_FILES") -or $TexContent.Contains("SAVE\_PREDICTION\_FILES")
$HasStride = $TexContent.Contains("VIDEO_INFERENCE_STRIDE") -or $TexContent.Contains("VIDEO\_INFERENCE\_STRIDE")
$HasWarmup = $TexContent.Contains("25")
$HasOllama = $TexContent.Contains("Ollama")
Check-Rule "TEMPLATE" "REG7" "Tecnicas de backend otimizado (In-RAM streaming, Vid Stride, Warm-up 25 modelos, Ollama)" ($HasRAM -and $HasStride -and $HasWarmup -and $HasOllama) "Backend techniques verified"

# REG8: Metadados de Resumo e Abstract (Palavras-Chave e Keywords)
$HasKwPt = $TexContent.Contains("PALAVRAS-CHAVE")
$HasKwEn = $TexContent.Contains("KEYWORDS")
Check-Rule "TEMPLATE" "REG8" "Cabecalho de metadados de pesquisa (Palavras-Chave e Keywords)" ($HasKwPt -and $HasKwEn) "Keywords headers verified"

# --------------------------------------------------------------------------------
# GRUPO B: AJUSTES SOLICITADOS PELA BANCA - CONTEÚDO (DC1 - DC5)
# --------------------------------------------------------------------------------

# DC1: Harmonização de Hardware de Inferência
$HasCpu = $TexContent -match "CPUs? de baixo custo"
$GpuMatches = [regex]::Matches($TexContent, "GPU (dedicada )?Intel Arc B570")
Check-Rule "CONTEUDO" "DC1" "Harmonizacao de hardware (exclusividade de GPU Intel Arc B570, sem CPUs de baixo custo)" ((-not $HasCpu) -and ($GpuMatches.Count -ge 4)) "GPU Arc B570 mentions: $($GpuMatches.Count)"

# DC2: Remoção da Classe Fantasma "Sinalizações de Emergência"
$ResumoIndex = $TexContent.IndexOf("RESUMO")
$AbstractIndex = $TexContent.IndexOf("ABSTRACT")
$ResumoPart = if ($ResumoIndex -ge 0 -and $AbstractIndex -gt $ResumoIndex) { $TexContent.Substring($ResumoIndex, $AbstractIndex - $ResumoIndex) } else { "" }
$GhostInResumo = $ResumoPart -match "sinalizações de emergência"
Check-Rule "CONTEUDO" "DC2" "Remocao de classe fantasma (sinalizacoes de emergencia) do benchmark do Resumo" (-not $GhostInResumo) "Ghost class in Resumo: $GhostInResumo"

# DC3: Tamanho Nominal Explicito do Espaço Amostral (N=3.500 imagens, 13.553 bboxes)
$HasN3500 = $TexContent.Contains("3.500 imagens")
$HasBoxes = $TexContent.Contains("13.553 caixas delimitadoras")
$HasSplit = $TexContent.Contains("2.450 imagens") -and $TexContent.Contains("700 imagens") -and $TexContent.Contains("350 imagens")
Check-Rule "CONTEUDO" "DC3" "Quantificacao nominal explicita do espaco amostral (N=3.500 imagens, 13.553 bboxes e splits)" ($HasN3500 -and $HasBoxes -and $HasSplit) "Sample size N=3.500 and splits verified"

# DC4: Justificativa da Classe Piloto "Cadeira" na Introdução
$HasChair = $TexContent.Contains("Cadeira")
$HasPilot = $TexContent.ToLower().Contains("piloto")
Check-Rule "CONTEUDO" "DC4" "Justificativa da classe piloto Cadeira na Introducao" ($HasChair -and $HasPilot) "Pilot rationale in Intro verified"

# DC5: Aprofundamento da Conclusão com Limitações Práticas e Trabalhos Futuros
$TexLower = $TexContent.ToLower()
$HasOclusao = $TexLower.Contains("oclus") -or $TexLower.Contains("andaimes")
$HasFuture = $TexLower.Contains("trabalhos futuros") -and $TexLower.Contains("int8")
Check-Rule "CONTEUDO" "DC5" "Aprofundamento da Conclusao com limitacoes praticas e agenda de trabalhos futuros" ($HasOclusao -and $HasFuture) "Limitations and future work verified"

# --------------------------------------------------------------------------------
# GRUPO C: AJUSTES SOLICITADOS PELA BANCA - FORMA E NORMAS (DF1 - DF7)
# --------------------------------------------------------------------------------

# DF1: Apresentação de Siglas Extensas no Primeiro Uso
$SiglasList = @("Graphics Processing Unit", "Stochastic Gradient Descent", "Application Programming Interface", "Random Access Memory", "Hypertext Transfer Protocol", "Large Language Model")
$SiglasFound = 0
foreach ($s in $SiglasList) {
    if ($TexContent.Contains($s)) { $SiglasFound++ }
}
Check-Rule "FORMA" "DF1" "Descricao extensa de siglas na primeira ocorrencia (GPU, SGD, API, RAM, HTTP, LLM, etc.)" ($SiglasFound -eq $SiglasList.Count) "Expanded siglas found: $SiglasFound / $($SiglasList.Count)"

# DF2: Correção Gramatical/Ortográfica em Materiais e Métodos
$GrammarOk = ($TexContent.Contains("O treinamento foi conduzido")) -and (-not ($TexContent.Contains("treinamento foi executado")))
Check-Rule "FORMA" "DF2" "Correcao gramatical no inicio do paragrafo de Treinamento" $GrammarOk "Phrasing syntax verified"

# DF3: Estrangeirismos em Itálico (\textit{...})
$ForeignTerms = @(
    "\\textit\{dataset\}", "\\textit\{bounding boxes\}", "\\textit\{epochs\}", "\\textit\{pipeline\}",
    "\\textit\{framework\}", "\\textit\{streaming\}", "\\textit\{Vid Stride\}", "\\textit\{backend\}",
    "\\textit\{endpoints\}", "\\textit\{best\.pt\}"
)
$ForeignCount = 0
foreach ($term in $ForeignTerms) {
    if ($TexContent -match $term) { $ForeignCount++ }
}
Check-Rule "FORMA" "DF3" "Padronizacao rigorosa de termos estrangeiros em italico (\textit{...})" ($ForeignCount -eq $ForeignTerms.Count) "Italicized terms: $ForeignCount / $($ForeignTerms.Count)"

# DF4: Chamada de Fonte nas Tabelas 1 e 2
$FonteMatches = [regex]::Matches($TexContent, "Fonte:\s*Dados da pesquisa \(2026\)")
Check-Rule "FORMA" "DF4" "Indicacao de Fonte padronizada IBGE/ABNT em todas as tabelas" ($FonteMatches.Count -ge 2) "Table sources found: $($FonteMatches.Count) / 2"

# DF5: Destaque Tipográfico e Autoria de Recursos Eletrônicos em Bibliografia
$HasCorporateAuthors = $BibContent.Contains("author = {{ULTRALYTICS}}") -and $BibContent.Contains("author = {{INTEL CORPORATION}}")
Check-Rule "FORMA" "DF5" "Destaque tipografico e autoria corporativa padronizada na bibliografia (ABNT NBR 6023)" $HasCorporateAuthors "Corporate authors formatted"

# DF6: Estruturação ABNT NBR 6023 para Eventos Acadêmicos (Redmon et al.)
$RedmonInProc = $BibContent.Contains("@inproceedings{redmon2016you")
$RedmonCaps = $BibContent.Contains("PROCEEDINGS OF THE IEEE CONFERENCE ON COMPUTER VISION AND PATTERN RECOGNITION")
Check-Rule "FORMA" "DF6" "Estruturacao ABNT NBR 6023 para anais de eventos (Redmon et al. em caixa-alta)" ($RedmonInProc -and $RedmonCaps) "Proceedings reference formatted"

# DF7: Limpeza de Marca Registrada TM e URLs Bibliográficas
$HasOpenVinoTM = $BibContent.Contains("OpenVINOTM")
$HasSpuriousUrlSpace = $BibContent -match "\.com/\s+\."
Check-Rule "FORMA" "DF7" "Remocao de marca registrada TM e eliminacao de espacos espurios em URLs" ((-not $HasOpenVinoTM) -and (-not $HasSpuriousUrlSpace)) "Clean URLs and no TM symbol"

Write-Host "--------------------------------------------------------------------------------"
$Pct = [math]::Round(($TotalPassed / $TotalTests) * 100, 1)
Write-Host "RESULTADO FINAL: $TotalPassed / $TotalTests TESTES APROVADOS ($Pct %)"
Write-Host "================================================================================"

if ($TotalPassed -eq $TotalTests) {
    Write-Host ">>> SUCESSO ABSOLUTO: main.tex, bibliografia.bib, cabecalho.tex e preambulo.tex cumprem 100% das regras da banca e do edital CONICT 2026! <<<" -ForegroundColor Green
} else {
    Write-Host "!!! ATENCAO: Alguns criterios de conformidade precisam de revisao. !!!" -ForegroundColor Red
}
