# Informações e Refinamentos do TCC (CONICT 2026)

Este documento centraliza as informações de cadastro, classificação CNPq e os refinamentos aplicados na estrutura acadêmica do trabalho.

---

## 1. Área do Conhecimento (Tabela CNPq)
*   **Classificação:** `1.03.03.04-9 Sistemas de Informação`  
    *(Grande Área: Ciências Exatas e da Terra / Área: Ciência da Computação)*

---

## 2. Assuntos e Palavras-Chave (Keywords)
*   **Em Português (Palavras-Chave):**
    *   Visão computacional
    *   Detecção de objetos
    *   YOLO
    *   Inteligência artificial
    *   Segurança do trabalho
*   **Em Inglês (Keywords):**
    *   Computer vision
    *   Object detection
    *   YOLO
    *   Artificial intelligence
    *   Occupational safety

---

## 3. Refinamentos Adicionais Aplicados ao Trabalho
1.  **Foco Exclusivo em Visão Computacional:**  
    Remoção de referências secundárias a arquitetura SOA, desenvolvimento móvel (Android/Kotlin), servidores ou bancos de dados adicionais, centrando o trabalho puramente na engenharia de IA, datasets e otimização.
2.  **Aceleração na GPU Dedicada da Intel:**  
    Atualização técnica detalhando a quantização e conversão de FP32 para FP16 com o toolkit Intel OpenVINO especificamente para otimização da taxa de frames por segundo (superior a 30 FPS) rodando na GPU dedicada **Intel Arc B570**.
3.  **Tabelas de Resultados Separadas:**  
    *   **Tabela 1:** Dados estatísticos de treinamento extraídos diretamente dos logs reais da rede (`results.csv`), registrando mAP@0.5 de 86,19% (cadeira) e 89,75% (extintor).
    *   **Tabela 2:** Resultados dos testes operacionais em campo com dados independentes (auditoria prática), registrando precisão prática de até 97,37%.
4.  **Limitação Físico-Temporal da Introdução:**  
    Introdução adaptada diretamente do PDF original do TCC e resumida para 17 linhas de texto corrido (respeitando o teto de 20 linhas do edital).
5.  **Alineação Completa das Referências:**  
    Inclusão das referências bibliográficas formais e links para a documentação do Intel OpenVINO e do Roboflow Universe no final do trabalho.
6.  **Anonimização de Submissão:**  
    Criação da pasta `TCC_CONICT_Avaliacao` contendo as seções totalmente desprovidas de autoria, filiação ou e-mails institucionais, atendendo às exigências de revisão duplo-cega da 1ª etapa de submissão do edital.
