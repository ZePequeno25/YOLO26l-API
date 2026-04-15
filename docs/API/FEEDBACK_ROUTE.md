# Rota de Feedback — `/feedback`

## Visão Geral

Permite que o usuário envie um feedback textual sobre o app. O primeiro feedback é sempre aceito; os seguintes exigem um intervalo mínimo de **5 dias** desde o último envio.

---

## Endpoint

```
POST https://kelvin-tech-api.online/feedback
Content-Type: application/json
```

---

## Request Body

| Campo | Tipo | Obrigatório | Restrições |
|-------|------|:-----------:|-----------|
| `username` | string | ✅ | Email ou display name do usuário |
| `text` | string | ✅ | Máximo de **1000 caracteres** |
| `app_version` | string | ❌ | Ex: `"1.0.3"` |
| `device_info` | string | ❌ | Ex: `"Android 13 / Samsung Galaxy A54"` |

**Exemplo:**
```json
{
  "username": "joao@gmail.com",
  "text": "O app está ótimo, mas a detecção poderia ser mais rápida.",
  "app_version": "1.0.3",
  "device_info": "Android 13 / Samsung Galaxy A54"
}
```

---

## Respostas

### `201 Created` — Feedback registrado com sucesso

```json
{
  "success": true,
  "message": "Feedback enviado com sucesso! Obrigado pela sua opinião.",
  "next_allowed_date": "2026-04-16"
}
```

> Use `next_allowed_date` para salvar localmente no app e controlar quando o botão de feedback fica disponível novamente.

---

### `429 Too Many Requests` — Cooldown ativo

Ocorre quando o usuário tenta enviar um feedback antes dos 5 dias de intervalo.

```json
{
  "detail": {
    "error": "cooldown",
    "message": "Você já enviou um feedback recentemente. O próximo poderá ser enviado a partir de 2026-04-16.",
    "next_allowed_date": "2026-04-16"
  }
}
```

---

### `422 Unprocessable Entity` — Validação falhou

Ocorre quando o texto está vazio ou ultrapassa 1000 caracteres.

```json
{
  "detail": [
    {
      "msg": "O feedback não pode ter mais de 1000 caracteres."
    }
  ]
}
```

---

### `500 Internal Server Error`

```json
{
  "detail": "Não foi possível registrar o feedback."
}
```

---

## Regras de Negócio

| Regra | Detalhe |
|-------|---------|
| Primeiro feedback | Sempre aceito, sem restrição de data |
| Cooldown | 5 dias desde o último envio bem-sucedido |
| Limite de caracteres | 1000 (validado na API, retorna 422) |
| Anti-flood diário | Máximo de 3 envios no mesmo dia por usuário (segurança interna) |

---

## Implementação Sugerida no Android

```kotlin
// Após receber resposta 201, salvar a próxima data permitida
prefs.edit()
    .putString("next_feedback_date", response.next_allowed_date)
    .apply()

// Antes de exibir/habilitar o botão de feedback
val next = prefs.getString("next_feedback_date", null)
val canSend = next == null || LocalDate.now() >= LocalDate.parse(next)
feedbackButton.isEnabled = canSend
```

---

## Localização dos Logs no Servidor

```
api-tcc/logs/feedback/{username}/{YYYY-MM-DD}.log
```

**Exemplo de entrada gerada:**
```
============================================================
TIMESTAMP   : 2026-04-11 14:35:22
USUARIO     : joao@gmail.com
FEEDBACK    : O app está ótimo, mas a detecção poderia ser mais rápida.
VERSAO APP  : 1.0.3
DISPOSITIVO : Android 13 / Samsung Galaxy A54
============================================================
```
