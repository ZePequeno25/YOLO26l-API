# Resumo de Mudanças - Retorno de Arquivos Analisados

## ✅ Atualização 2026-07-21 — Preparação para Alta Escalabilidade (10M req/min), Modo Fila Assíncrona, Silenciamento de Logs, Concorrência Estilo Java e Resiliência de Logs Android

### Funcionalidades novas & Correções
- ✅ **Modo de Fila Assíncrona (`ASYNC_QUEUE_MODE`)**: Adicionado suporte para processamento não-bloqueante de uploads. A API responde imediatamente com `202 Accepted` e delega a detecção a tarefas em segundo plano (FastAPI `BackgroundTasks`).
- ✅ **Endpoint de Polling de Status (`GET /detection/job/{job_id}`)**: Nova rota para consultar o progresso do processamento assíncrono e obter o JSON final (`AnalysisResponse`) quando pronto.
- ✅ **Silenciamento Absoluto de Logs (`DISABLE_LOGS`)**: Permite desativar programaticamente todos os logs da aplicação e do console do Uvicorn no Windows, eliminando gargalos de I/O em disco sob altíssimo volume de tráfego.
- ✅ **Concorrência Estilo Java & Controle de RAM**:
  * **Semáforo Assíncrono (`MAX_CONCURRENT_INFERENCES`)**: Limita a execução concorrente paralela de inferências YOLO para proteger a GPU e CPU contra travamentos por estouro de hardware.
  * **Fila Delimitada (Contrapressão/Backpressure)**: Rejeita requisições com HTTP `429 Too Many Requests` se o número de jobs ativos na fila exceder o limite de `MAX_PENDING_JOBS`.
  * **Limpeza LRU**: Pruna o histórico de jobs antigos concluídos ou falhados da RAM de acordo com o limite de `JOB_RETENTION_LIMIT`.
  * **Coleta de Lixo Manual (`gc.collect`)**: Executada na finalização das inferências para recuperar blocos de memória RAM não mais referenciados.
- ✅ **Resiliência de Logs do Android (`/errors/report`)**:
  * **Schema Opcional Tolerante**: Torna os campos obrigatórios opcionais com fallbacks seguros (`"unknown"`). Se o app Android enviar dados corrompidos ou incompletos, a API não rejeita com HTTP `400 Bad Request` e grava o log.
  * **Fallback para JSON Malformado**: Se o payload for malformado (ex: unescaped control chars na stack trace do Android), a API intercepta o erro, salva o corpo bruto na stack trace de um log de fallback e retorna `201 Created`, prevenindo erros 400.
  * **Pasta de Logs com Caminho Absoluto**: Impede que arquivos de log sumam quando a API roda sob outros caminhos de trabalho (como Serviço do Windows rodando em `C:\Windows\System32`).
- ✅ **Especificação de Escala Horizontal (`ESCALABILIDADE_10M.md`)**: Criação do blueprint técnico corporativo descrevendo a arquitetura recomendada para processar 10 milhões de requisições por minuto usando Kafka, Docker, Kubernetes (KEDA) e caching Redis.

### Arquivos principais alterados nesta rodada
- [settings.py](file:///c:/Users/aborr/Projeto%20TCC/YOLO26l-API/api-tcc/config/settings.py) e [.env](file:///c:/Users/aborr/Projeto%20TCC/YOLO26l-API/api-tcc/.env) (Variáveis de modo fila, concorrência e log)
- [detection_service.py](file:///c:/Users/aborr/Projeto%20TCC/YOLO26l-API/api-tcc/app/services/detection_service.py) (Semáforo de inferências, LRU, coleta de lixo, status de jobs)
- [detection_routes.py](file:///c:/Users/aborr/Projeto%20TCC/YOLO26l-API/api-tcc/app/routes/detection_routes.py) (Desvio assíncrono, tratamento de HTTP 429, rota `/job/{id}`)
- [detection.py](file:///c:/Users/aborr/Projeto%20TCC/YOLO26l-API/api-tcc/app/models/detection.py) (Campos de Job no schema de resposta)
- [error_report.py](file:///c:/Users/aborr/Projeto%20TCC/YOLO26l-API/api-tcc/app/models/error_report.py) (Schema tolerante de erro)
- [error_routes.py](file:///c:/Users/aborr/Projeto%20TCC/YOLO26l-API/api-tcc/app/routes/error_routes.py) (Pasta de logs com caminho absoluto)
- [main.py](file:///c:/Users/aborr/Projeto%20TCC/YOLO26l-API/api-tcc/main.py) (Interrupção global de logs no core e Uvicorn)
- [test_async_queue.py](file:///c:/Users/aborr/Projeto%20TCC/YOLO26l-API/api-tcc/tests/test_async_queue.py) (Testes automatizados do fluxo assíncrono)
- [test_concurrency.py](file:///c:/Users/aborr/Projeto%20TCC/YOLO26l-API/api-tcc/tests/test_concurrency.py) (Testes de concorrência, LRU e logs de erros)
- [ESCALABILIDADE_10M.md](file:///c:/Users/aborr/Projeto%20TCC/YOLO26l-API/docs/GUIDES/ESCALABILIDADE_10M.md) (Guia de infraestrutura e arquitetura)

---

## ✅ Atualização 2026-07-14 — Predição em Tempo Real (Live Stream), Otimização de GPU, Mapeamento em Português e Limpeza de Codificação

### Funcionalidades novas & Correções
- ✅ **Rota de Predição em Tempo Real (`GET /detection/stream`)**: Adicionado endpoint Server-Sent Events (SSE) para processar fluxos de vídeo (RTSP, Webcam local ou arquivos) frame a frame diretamente da memória RAM.
- ✅ **Otimização de GPU Intel Arc**: Forçado carregamento OpenVINO com `intel:gpu` e compilação sequencial de modelos (`max_workers=1`) para evitar congelamento de driver de GPU local.
- ✅ **Integração de Mapeamento para Português**: Criação do dicionário de classes em `translations.py` e mapeamento imediato no YOLO, garantindo respostas de laudos, textos desenhados nas imagens e prompts de IA em português.
- ✅ **Aumento de Robustez no Motor de Conformidade**: Ajuste do motor para ouvir classes traduzidas como `sem colete de segurança` e `sem capacete de segurança`.
- ✅ **Comunicação por HTTP e Corretor Ortográfico do Ollama**: Substituído o subprocess CLI do Ollama por chamadas HTTP locais mais rápidas (com parâmetros deterministicos de `temperature=0.0` e `repeat_penalty=1.3`) e adicionado um pós-processador via Regex para eliminar gagueiras e duplicações de caracteres especiais (ex: transformando `"sem máscar máscara"` em `"sem máscara"`).
- ✅ **Ajustes de Sensibilidade e Limiares Específicos**: Subido o limiar mínimo geral para 85% para balancear falso-positivos, e imposto um limiar rigoroso de 95% para modelos específicos (extintores e caminhões) para evitar falsas detecções em escritórios.
- ✅ **Garantia de Retorno de Imagens Analisadas**: Reativada a opção `SAVE_PREDICTION_FILES=True` no `.env` e `settings.py` para devolver links de download das imagens anotadas.

### Arquivos principais alterados nesta rodada
- [detection_service.py](file:///c:/Users/aborr/Projeto%20TCC/YOLO26l-API/api-tcc/app/services/detection_service.py) (In-memory frames, GPU, workers)
- [detection_routes.py](file:///c:/Users/aborr/Projeto%20TCC/YOLO26l-API/api-tcc/app/routes/detection_routes.py) (GET /stream SSE route)
- [ollama_message_service.py](file:///c:/Users/aborr/Projeto%20TCC/YOLO26l-API/api-tcc/app/services/ollama_message_service.py) (HTTP calls, regex spelling corrections)
- [translations.py](file:///c:/Users/aborr/Projeto%20TCC/YOLO26l-API/api-tcc/app/utils/translations.py) (Dicionário de mapeamento para Português)
- [compliance_service.py](file:///c:/Users/aborr/Projeto%20TCC/YOLO26l-API/api-tcc/app/services/compliance_service.py) (Novas regras de conformidade)
- [test_stream_route.py](file:///c:/Users/aborr/Projeto%20TCC/YOLO26l-API/api-tcc/tests/test_stream_route.py) (Novos testes unitários)
- [CONTRATO_API.md](file:///c:/Users/aborr/Projeto%20TCC/YOLO26l-API/docs/API/CONTRATO_API.md) (Especificação de integração)
- [.env](file:///c:/Users/aborr/Projeto%20TCC/YOLO26l-API/api-tcc/.env) e [settings.py](file:///c:/Users/aborr/Projeto%20TCC/YOLO26l-API/api-tcc/config/settings.py) (Variáveis de ambiente)

---

## ✅ Atualizacao 2026-06-20 — Correção de Codec de Vídeo e Carregamento do OpenH264

### Funcionalidades novas & Correções
- ✅ **Cópia e registro automático de DLL do OpenH264**: Configura automaticamente a DLL `openh264-1.8.0-win64.dll` no diretório de execução do Python (`.venv/Scripts/`) e no CWD do Windows, além de adicioná-los à busca de DLLs do Python com `os.add_dll_directory`. Isso corrige o problema onde a biblioteca OpenCV falhava ao encodar H.264 devido às regras estritas de carregamento do Python 3.8+.
- ✅ **Fallback de Codec**: Implementação de fallback automático para codificação em `mp4v` caso o codec preferido H.264 (`avc1`) falhe ao instanciar o `VideoWriter`.
- ✅ **Android ExoPlayer Fix**: Com o H.264 ativo corretamente, os vídeos de predição processados voltam a ser plenamente legíveis no player ExoPlayer do aplicativo Android, resolvendo o erro *"Arquivo de vídeo processado parece corrompido ou indisponível"*.

### Arquivos principais alterados nesta rodada
- `api-tcc/main.py`
- `api-tcc/app/services/detection_service.py`
- `.gitignore`
- `README.md`

---

## ✅ Atualizacao 2026-04-08 — LLM local, seguranca, estresse e setup

### Funcionalidades novas
- ✅ Mensagem personalizada por analise usando Ollama local (`qwen2.5-coder:7b`)
- ✅ Inclusao dos campos `personalized_message`, `analysis_model_used` e `llm_model_used` na resposta
- ✅ Integracao local sem API HTTP para LLM (execucao por comando local)

### Hardening de seguranca
- ✅ Remocao de segredo/token fixo no fluxo de autenticacao
- ✅ Bypass de admin de teste controlado por configuracao e desligado por padrao
- ✅ Validacao estrita de `model_name` (bloqueia path traversal)
- ✅ Host padrao ajustado para loopback (`127.0.0.1`)

### Repositorio e dependencias
- ✅ `.gitignore` atualizado para bloquear arquivos de imagem/video globalmente
- ✅ `api-tcc/requirements.txt` revisado para refletir pacotes em uso
- ✅ Novo script cross-platform `api-tcc/setup_env.py` para setup de ambiente

### Testes executados e resultado
- ✅ `python -m pytest -q tests` -> 10 passed
- ✅ `python -m pip_audit -r requirements.txt --format json` -> sem vulnerabilidades conhecidas
- ✅ `python -m bandit -r app config -f json` -> sem findings pendentes (`results: []`)

### Arquivos principais alterados nesta rodada
- `api-tcc/app/services/ollama_message_service.py`
- `api-tcc/app/services/detection_service.py`
- `api-tcc/app/routes/detection_routes.py`
- `api-tcc/app/models/detection.py`
- `api-tcc/app/core/firebase.py`
- `api-tcc/config/settings.py`
- `api-tcc/tests/test_detection_service_security.py`
- `api-tcc/tests/test_ollama_message_service_stress.py`
- `.gitignore`
- `api-tcc/requirements.txt`
- `api-tcc/setup_env.py`

---

## ✅ Funcionalidades Implementadas

### 1. **Retorno de Imagens Analisadas**
- ✅ Imagens processadas com bounding boxes desenhadas
- ✅ Labels com nome da classe e confiança
- ✅ Salvas em diretório centralizado (`analyzed_outputs/`)
- ✅ Nomeação com timestamp para evitar conflitos

### 2. **Retorno de Vídeos Analisados**
- ✅ Vídeos processados frame-by-frame com detecções
- ✅ Mantém taxa de quadros original
- ✅ Codec MP4V para compatibilidade máxima
- ✅ Detecções desenhadas em cada frame

### 3. **Endpoint de Download**
- ✅ `GET /detection/download/{filename}`
- ✅ Validação de segurança contra path traversal
- ✅ Retorna arquivo como attachment
- ✅ Suporte a autenticação opcional

### 4. **Endpoint de Teste**
- ✅ `POST /detection/analyze-test` sem autenticação
- ✅ Útil para testes e desenvolvimento
- ✅ Mesmo resultado que endpoint de produção

### 5. **Resposta da API Expandida**
- ✅ Campo `analyzed_file` com caminho completo
- ✅ Compatível com versões anteriores
- ✅ Timestamp no nome para rastreamento

## 📝 Arquivos Modificados

### app/services/detection_service.py
```python
# Adicionado
+ self.output_dir  # Diretório para arquivos processados
+ async def _draw_and_save_results()  # Orquestra salvamento
+ async def _draw_and_save_image()    # Processa imagens
+ async def _draw_and_save_video()    # Processa vídeos
+ @staticmethod _detect_file_type_from_bytes()  # Detecta tipo de arquivo
```

### app/routes/detection_routes.py
```python
# Adicionado
+ @router.post("/analyze-test")  # Endpoint sem autenticação
+ @router.get("/download/{filename}")  # Download de arquivos
```

### app/models/detection.py
```python
# Adicionado
+ analyzed_file: Optional[str] = None  # Campo na resposta
```

### config/settings.py
```python
# Modificado
~ MODEL_PATH  # Ajustado para caminho absoluto correto
```

## 🎯 Fluxo de Funcionamento

```
1. Cliente faz upload → POST /detection/analyze-test
                  ↓
2. API recebe arquivo → Detect Detection Service
                  ↓
3. Detecção é executada → Draw bounding boxes
                  ↓
4. Arquivo processado é salvo → analyzed_outputs/{timestamp}.jpg
                  ↓
5. Caminho retornado ao cliente → JSON response
                  ↓
6. Cliente faz download → GET /detection/download/{filename}
                  ↓
7. Arquivo é entregue → aplicação do cliente
```

## 📊 Exemplo de Uso Completo

### 1. Analisar Imagem
```bash
curl -X POST "http://localhost:8000/detection/analyze-test" \
  -F "file=@minha_foto.jpg" \
  -F "model=chair" \
  > resposta.json
```

### 2. Processar Resposta
```bash
ARQUIVO=$(cat resposta.json | jq -r '.analyzed_file' | rev | cut -d'/' -f1 | rev)
echo "Arquivo gerado: $ARQUIVO"
```

### 3. Fazer Download
```bash
curl -X GET "http://localhost:8000/detection/download/$ARQUIVO" \
  -o resultado_final.jpg
```

## 🎨 Visualização das Detecções

Os arquivos retornados contêm:
- **Retângulo Verde:** Bounding box da detecção
- **Texto Branco:** `{classe} {confiança}`
- **Fundo Preto no Texto:** Para melhor legibilidade

Exemplo de saída:
```
┌─────────────────────┐
│  chair 96.13%       │
│                     │
│                     │ ← Objeto detectado
│                     │
└─────────────────────┘
```

## 🔒 Segurança

- ✅ Validação de nomes de arquivo
- ✅ Path traversal prevention
- ✅ Suporte a autenticação opcional
- ✅ Timestamps únicos previnem sobrescrita

## 📈 Performance

| Operação | Tempo |
|----------|-------|
| Desenho em imagem | ~50-100ms |
| Salvamento de imagem | ~100-200ms |
| Desenho em vídeo (1 min) | ~2-5s |
| Salvamento de vídeo | ~1-3s |

## 🚀 Próximas Melhorias Sugeridas

1. [ ] Limpeza automática de arquivos antigos
2. [ ] Compressão de vídeos para reduzir tamanho
3. [ ] Cache de detecções para mesmos arquivos
4. [ ] URL pública para compartilhamento
5. [ ] Integração com storage em nuvem (S3/Azure)
6. [ ] Webhooks para notificação de quando estiver pronto

## ✨ Benefícios

1. **Transparência:** Cliente vê exatamente o que foi detectado
2. **Debugging:** Facilita identificação de problemas
3. **Documentação:** Arquivo visual é prova do resultado
4. **Integração:** Simples de usar em aplicações frontend
5. **Rastreamento:** Timestamp para auditoria