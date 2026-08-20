## 3. RESULTADOS E DISCUSSÃO
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

A otimização com o OpenVINO resultou em latência média de inferência reduzida na GPU dedicada Intel Arc B570, garantindo taxas estáveis superiores a 30 quadros por segundo, o que valida a aplicação do sistema para auditorias preditivas em tempo real.

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
| mAP@0.5 de Campo | 93,10% | 95,60% |