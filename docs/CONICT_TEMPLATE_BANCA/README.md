# Template CONICT 2026 - Versão Completa para Ajustes da Banca

Esta pasta contém o template **LaTeX completo e revisado** do artigo/resumo expandido para submissão e avaliação pela banca do **17º Congresso de Inovação, Ciência e Tecnologia do IFSP (CONICT 2026)**.

---

## 📁 Estrutura de Arquivos

- **[`main.tex`](file:///c:/Users/aborr/Projeto%20TCC/YOLO26l-API/docs/CONICT_TEMPLATE_BANCA/main.tex)**: Arquivo principal contendo todo o texto (Resumo, Abstract, Introdução, Materiais e Métodos, Resultados e Discussão, Conclusões, Agradecimentos e Referências).
- **[`cabecalho.tex`](file:///c:/Users/aborr/Projeto%20TCC/YOLO26l-API/docs/CONICT_TEMPLATE_BANCA/cabecalho.tex)**: Cabeçalho com o título oficial atualizado, nomes de autores/orientador, e-mail institucional e classificação CNPq.
- **[`preambulo.tex`](file:///c:/Users/aborr/Projeto%20TCC/YOLO26l-API/docs/CONICT_TEMPLATE_BANCA/preambulo.tex)**: Pacotes LaTeX, margens, espaçamento simples e formatação ABNT.
- **[`bibliografia.bib`](file:///c:/Users/aborr/Projeto%20TCC/YOLO26l-API/docs/CONICT_TEMPLATE_BANCA/bibliografia.bib)**: Base de dados de referências bibliográficas no formato ABNT NBR 6023.
- **[`validar_conict.py`](file:///c:/Users/aborr/Projeto%20TCC/YOLO26l-API/docs/CONICT_TEMPLATE_BANCA/validar_conict.py)**: Script Python de verificação automatizada (20 critérios de conformidade do edital e pareceres da banca).
- **Logotipos e Figuras**: `destaque_17_conict.png`, `logo_ifsp.png`, `logo_reitoria.png` e imagens de apoio.

---

## 📌 Título Atualizado

> **DETECÇÃO DE CONFORMIDADE DE SEGURANÇA EM AMBIENTES UTILIZANDO A ARQUITETURA YOLO E ACELERAÇÃO OPENVINO**

---

## 🛠️ Como Realizar Ajustes para a Banca

1. **Alterações no Texto do Artigo**:
   Edite o arquivo **[`main.tex`](file:///c:/Users/aborr/Projeto%20TCC/YOLO26l-API/docs/CONICT_TEMPLATE_BANCA/main.tex)**. Todas as seções estão organizadas de forma limpa.
   
2. **Alterações nos Autores e Título**:
   Edite o arquivo **[`cabecalho.tex`](file:///c:/Users/aborr/Projeto%20TCC/YOLO26l-API/docs/CONICT_TEMPLATE_BANCA/cabecalho.tex)** para ajustar e-mails, ordenação de autores ou novas afiliações.

3. **Inclusão de Novas Citações**:
   Adicione as novas entradas no arquivo **[`bibliografia.bib`](file:///c:/Users/aborr/Projeto%20TCC/YOLO26l-API/docs/CONICT_TEMPLATE_BANCA/bibliografia.bib)** e cite no texto usando `\cite{chave}`.

---

## ⚡ Como Compilar

Para gerar o PDF final:
```bash
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```
*(Também pode ser importado diretamente no Overleaf ou VS Code com extensão LaTeX Workshop).*
