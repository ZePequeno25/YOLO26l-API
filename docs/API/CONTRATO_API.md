# Contrato da API - Integracao Android

Documento de contrato atual da API para integracao com o app Android.

## Base URL

- Emulador Android: `http://10.0.2.2:8000/`
- Dispositivo fisico: `http://192.168.76.200:8000/`

Nao usar `localhost` no app Android.

---

## Autenticacao

### `POST /auth/google`

Login e cadastro no mesmo endpoint.

Headers:
```
Content-Type: application/json
```

Body:
```json
{
  "id_token": "FIREBASE_ID_TOKEN",
  "email": "usuario@gmail.com",
  "displayName": "Joao Silva"
}
```

Resposta:
```json
{
  "success": true,
  "message": "Autenticação concluída com sucesso",
  "uid": "abc123",
  "email": "usuario@gmail.com",
  "name": "Joao Silva",
  "email_verified": true,
  "is_new_user": false
}
```

- `is_new_user = true`: criou cadastro
- `is_new_user = false`: fez login (usuario ja existia)

### `POST /auth/verify`

Valida token e retorna dados do usuario.

Headers:
```
Content-Type: application/x-www-form-urlencoded
```

Body (form):
```
id_token=FIREBASE_ID_TOKEN
```

### `GET /auth/test-token`

Gera token de teste. Uso apenas local/dev.

Observacao de seguranca:
- endpoint depende de `TEST_JWT_SECRET` configurado.
- bypass admin fixo foi removido do fluxo padrao.
- tokens de teste nao devem ser usados em producao.

---

## Deteccao

### `POST /detection/analyze`

Analise com autenticacao.

Body `multipart/form-data`:
- `file`: imagem ou video
- `id_token`: token Firebase do usuario
- `model` (opcional): nome do modelo a usar (ex: `chair`)

### `POST /detection/analyze-test`

Analise sem autenticacao (teste local).

Body `multipart/form-data`:
- `file`: imagem ou video
- `model` (opcional): nome do modelo a usar

### Resposta da deteccao

```json
{
  "success": true,
  "message": "Analise concluida com o modelo 'chair'. Resultado: chair: 1.",
  "personalized_message": "Analise concluida com o modelo 'chair'. Resultado: chair: 1.",
  "analysis_model_used": "chair",
  "llm_model_used": "qwen2.5-coder:7b",
  "class_counts": { "chair": 1 },
  "num_frames_processed": 1,
  "detected_chairs": 1,
  "frames_with_detections": 1,
  "analyzed_file": "...caminho completo...",
  "analyzed_output": {
    "path": "...caminho completo...",
    "filename": "analyzed_result.jpg",
    "download_url": "/detection/download/analyzed_result.jpg"
  },
  "boxes": [
    {
      "frame_index": 0,
      "class_id": 2,
      "class_name": "chair",
      "confidence": 0.94,
      "x1": 120,
      "y1": 80,
      "x2": 300,
      "y2": 410,
      "track_id": null
    }
  ]
}
```

Notas:
- `message` pode vir personalizado pelo LLM local.
- `personalized_message` contem a versao personalizada da mensagem.
- `analysis_model_used` indica o modelo de deteccao efetivamente usado.
- `llm_model_used` indica o modelo local do Ollama usado na geracao da mensagem.

### `GET /detection/download/{filename}`

Download do arquivo anotado. Usar o campo `analyzed_output.download_url` diretamente.

---

## Relatorio de Erros

### `POST /errors/report`

Recebe excecoes capturadas no app mobile e salva em log organizado por usuario e data.

Headers:
```
Content-Type: application/json
```

Body:
```json
{
  "username": "joao.silva@gmail.com",
  "exception_type": "NullPointerException",
  "message": "Attempt to invoke virtual method on a null object reference",
  "stack_trace": "java.lang.NullPointerException\n\tat com.example.MainActivity.onCreate(MainActivity.java:42)",
  "screen": "MainActivity",
  "app_version": "1.0.3",
  "device_info": "Android 13 / Samsung Galaxy A54",
  "model_used": "chair"
}
```

Campos obrigatorios:
- `username`: email ou nome da conta do usuario
- `exception_type`: tipo/classe da excecao
- `message`: mensagem da excecao

Campos opcionais:
- `stack_trace`: stack trace completo
- `screen`: tela/Activity onde ocorreu
- `app_version`: versao do app
- `device_info`: informacoes do dispositivo
- `model_used`: modelo de deteccao em uso quando o erro ocorreu

Resposta (201):
```json
{
  "success": true,
  "message": "Erro registrado com sucesso",
  "log_file": "logs/errors/joao.silva@gmail.com/2026-03-29.log"
}
```

Estrutura de arquivos gerada no servidor:
```
logs/errors/
  joao.silva@gmail.com/
    2026-03-29.log
    2026-03-30.log
  outro.usuario@gmail.com/
    2026-03-29.log
```

Cada entrada no `.log` contem timestamp preciso (hora/min/seg), todos os campos recebidos e separador visual entre excecoes.

---

## Contratos Kotlin

```kotlin
// --- Auth ---

data class GoogleAuthRequest(
    val id_token: String,
    val email: String,
    val displayName: String
)

data class GoogleAuthResponse(
    val success: Boolean,
    val message: String,
    val uid: String,
    val email: String,
    val name: String,
    val email_verified: Boolean,
    val is_new_user: Boolean
)

// --- Deteccao ---

data class AnalyzeBox(
    val frame_index: Int,
    val class_id: Int,
    val class_name: String,
    val confidence: Double,
    val x1: Int,
    val y1: Int,
    val x2: Int,
    val y2: Int,
    val track_id: Int?
)

data class AnalyzedOutput(
    val path: String,
    val filename: String,
    val download_url: String
)

data class AnalyzeResponse(
    val success: Boolean,
    val message: String,
  val personalized_message: String?,
  val analysis_model_used: String?,
  val llm_model_used: String?,
    val class_counts: Map<String, Int>,
    val num_frames_processed: Int,
    val detected_chairs: Int,
    val frames_with_detections: Int?,
    val analyzed_file: String?,
    val analyzed_output: AnalyzedOutput?,
    val boxes: List<AnalyzeBox>?
)

// --- Relatorio de Erros ---

data class ErrorReportRequest(
    val username: String,
    val exception_type: String,
    val message: String,
    val stack_trace: String? = null,
    val screen: String? = null,
    val app_version: String? = null,
    val device_info: String? = null,
    val model_used: String? = null
)

data class ErrorReportResponse(
    val success: Boolean,
    val message: String,
    val log_file: String
)
```

---

## Resumo rapido

```
AUTH LOGIN/CADASTRO
POST /auth/google
JSON: { id_token, email, displayName }

AUTH VALIDACAO
POST /auth/verify
FORM: id_token=...

DETECCAO (PROD)
POST /detection/analyze
multipart: file, id_token, model?

DETECCAO (TESTE)
POST /detection/analyze-test
multipart: file, model?

RELATORIO DE ERROS
POST /errors/report
JSON: { username, exception_type, message, stack_trace?, screen?, app_version?, device_info?, model_used? }
```
