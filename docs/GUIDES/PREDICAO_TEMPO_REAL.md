# Guia de Predição em Tempo Real (Live Streaming SSE)

Esta documentação detalha a arquitetura, o funcionamento interno, os parâmetros de configuração e a integração com o aplicativo móvel da funcionalidade de análise de vídeo em tempo real (Live Stream).

---

## 1. Visão Geral da Arquitetura

O endpoint `/detection/stream` foi projetado para atuar como um barramento de eventos de visão computacional de baixa latência. Ao contrário do fluxo tradicional `/analyze` (que recebe um arquivo completo via POST, processa e fecha a conexão), este fluxo funciona em **tempo real e de maneira contínua**:

```
📱 App Android (EventSource) ──────> [ GET /detection/stream ]
                                               │
                                               ▼
                                      OpenCV VideoCapture
                                (Lê RTSP / WebCam / Arquivo)
                                               │
                                        (frame_stride)
                                               │
                                               ▼
                                   YOLO + OpenVINO GPU Arc
                               (Inferência direta na memória)
                                               │
                                               ▼
📱 App Android (Exibe dados) <─────── Server-Sent Events (SSE)
```

---

## 2. Parâmetros do Endpoint

### `GET /detection/stream`

O endpoint funciona por meio de conexões persistentes **HTTP Server-Sent Events (SSE)**.

| Parâmetro | Tipo | Obrigatório | Padrão | Descrição |
| :--- | :--- | :--- | :--- | :--- |
| `video_source` | `str` | **Sim** | — | Link da live (ex: `rtsp://...`), URL do stream HTTP, arquivo de vídeo local, ou índice da webcam (ex: `"0"`). |
| `frame_stride` | `int` | Não | `3` | Pula N frames entre inferências para economizar GPU. Valores maiores aumentam a performance e a fluidez do feed. |
| `token` / `id_token` | `str` | Não | — | Token JWT do Firebase. A autenticação é opcional localmente para agilizar a prototipagem no Android Studio. |

---

## 3. Funcionamento Interno e Otimizações

### 🧠 Processamento em Memória (Zero Desgaste de Disco)
As transmissões em tempo real lêem dezenas de frames por segundo. Salvar cada frame como um arquivo temporário no disco SSD degradaria o hardware rapidamente. A API decodifica o fluxo do OpenCV diretamente para tensores em memória RAM (arrays NumPy) e os envia em lote para a GPU Intel Arc.

### ⚡ Paralelismo Concorrente de 23 Modelos
O frame capturado é submetido em paralelo para todos os 23 modelos usando um `ThreadPoolExecutor` sincronizado (`max_workers=1`). A compilação e execução no OpenVINO são feitas na GPU dedicada Intel Arc (através do dispositivo `"intel:gpu"`), garantindo latência na casa dos milissegundos para varreduras completas.

### 🛡️ Tolerância a Quedas e Sincronismo (Buffer de Conexão)
* **Reconexão Automática**: Se o stream de vídeo sofrer uma oscilação na rede, a API entra em estado de espera por até 10 segundos (100 frames pulados) antes de encerrar. Se o sinal de vídeo retornar nesse período, as transmissões de dados são retomadas de forma transparente.
* **Auto-fechamento Inteligente**: O fluxo de vídeo só é fechado quando o cliente mobile cancela explicitamente a requisição ou fecha o aplicativo.

---

## 4. Formato de Saída (Payload SSE)

Cada evento gerado pelo servidor é enviado com a assinatura de texto `data: {JSON}\n\n`.

```json
data: {
  "frame_index": 27,
  "class_counts": {
    "Pessoa": 1,
    "Sem Máscara": 1,
    "Sem Colete de Segurança": 1
  },
  "boxes": [
    {
      "frame_index": 27,
      "class_id": 0,
      "class_name": "Pessoa",
      "confidence": 0.96,
      "x1": 150,
      "y1": 100,
      "x2": 450,
      "y2": 820
    },
    {
      "frame_index": 27,
      "class_id": 0,
      "class_name": "Sem Máscara",
      "confidence": 0.89,
      "x1": 270,
      "y1": 120,
      "x2": 320,
      "y2": 190
    }
  ],
  "compliance_status": "NAO_CONFORME",
  "compliance_alerts": [
    "Não conformidade de EPI detectada: 'Sem Máscara' no frame 27.",
    "Não conformidade de EPI detectada: 'Sem Colete de Segurança' no frame 27."
  ]
}
```

---

## 5. Exemplo de Integração

### Exemplo de Consumo no Android (Kotlin + OkHttp EventSource)

Para consumir a rota no Android, recomenda-se usar a biblioteca `okhttp-sse` para manipular conexões Server-Sent Events nativamente:

```kotlin
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.sse.EventSource
import okhttp3.sse.EventSourceListener
import okhttp3.sse.EventSources
import java.util.concurrent.TimeUnit

class RealtimeStreamManager(private val onResultReceived: (String) -> Unit) {

    private val client = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(0, TimeUnit.SECONDS) // Necessário para conexões SSE eternas
        .build()

    private var eventSource: EventSource? = null

    fun startStreaming(videoSource: String, frameStride: Int = 3) {
        val url = "http://192.168.76.200:8080/detection/stream" +
                "?video_source=$videoSource" +
                "&frame_stride=$frameStride"

        val request = Request.Builder()
            .url(url)
            .header("Accept", "text/event-stream")
            .build()

        eventSource = EventSources.createFactory(client)
            .newEventSource(request, object : EventSourceListener() {
                override fun onOpen(eventSource: EventSource, response: Response) {
                    println("🎥 Conexão aberta com o fluxo de detecções em tempo real!")
                }

                override fun onEvent(eventSource: EventSource, id: String?, type: String?, data: String) {
                    // Aqui você recebe o JSON string contendo caixas e contagens do frame
                    onResultReceived(data)
                }

                override fun onClosed(eventSource: EventSource) {
                    println("🔌 Conexão de stream fechada pelo servidor.")
                }

                override fun onFailure(eventSource: EventSource, t: Throwable?, response: Response?) {
                    System.err.println("❌ Falha na conexão de streaming: ${t?.message}")
                }
            })
    }

    fun stopStreaming() {
        eventSource?.cancel()
        eventSource = null
    }
}
```

### Exemplo Rápido via Python

Você pode testar a rota via script Python local usando o módulo `sseclient`:

```python
import sseclient
import requests

url = "http://127.0.0.1:8080/detection/stream?video_source=0&frame_stride=3"
response = requests.get(url, stream=True)
client = sseclient.SSEClient(response)

print("Iniciando escuta do live stream...")
for event in client.events():
    print(f"Frame Processado: {event.data}")
```

---

## 6. Dicas de Ajuste Fino (Performance)

1. **Ajuste de `frame_stride`**:
   * Para feeds de câmera de segurança a 30 FPS, um `frame_stride=3` ou `frame_stride=4` é o ideal. Isso reduz a carga computacional em 75% na GPU enquanto preserva uma taxa de amostragem de ~10 quadros por segundo para análise, que é mais que suficiente para auditoria visual.
2. **Exclusões de Modelos / Filtros**:
   * Se for necessário acelerar ainda mais, modelos específicos não utilizados podem ser temporariamente desabilitados movendo suas pastas do diretório `models/`.
