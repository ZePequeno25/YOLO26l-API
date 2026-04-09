# 🔐 Rota POST /auth/google - Nova Funcionalidade de Autenticação Google

## 📋 Visão Geral

Nova rota para autenticação de usuários através do Google, permitindo login/registro via Google Sign-In.

## 🔌 Endpoint

```
POST /auth/google
```

## 📊 Corpo da Requisição

```json
{
  "id_token": "token_jwt_do_google",
  "email": "usuario@gmail.com",
  "displayName": "João Silva"
}
```

### Campos Obrigatórios

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id_token` | string | Token JWT válido fornecido pelo Google |
| `email` | string | Email do usuário do Google |
| `displayName` | string | Nome de exibição do usuário |

## 📤 Resposta (Sucesso)

**Status: 200 OK**

```json
{
  "success": true,
  "message": "Autenticação concluída com sucesso",
  "uid": "usuario@gmail.com",
  "email": "usuario@gmail.com",
  "name": "João Silva",
  "email_verified": true,
  "is_new_user": false
}
```

### Campos da Resposta

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `success` | boolean | Sempre `true` em caso de sucesso |
| `message` | string | Mensagem descritiva (novo usuário ou login) |
| `uid` | string | ID único do usuário |
| `email` | string | Email do usuário |
| `name` | string | Nome de exibição |
| `email_verified` | boolean | Se o email foi verificado |
| `is_new_user` | boolean | `true` se foi criado novo usuário, `false` se foi atualizado |

## ⚠️ Resposta (Erro)

**Status: 401 Unauthorized**

```json
{
  "detail": "Erro na autenticação Google: Token inválido"
}
```

**Status: 422 Unprocessable Entity**

```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "displayName"],
      "msg": "Field required"
    }
  ]
}
```

## 🔄 Fluxo de Funcionamento

```
1. Cliente faz POST com dados do Google
        ↓
2. API valida o id_token com Firebase
        ↓
3. Se válido, verifica se usuário existe no Firestore
        ↓
4. Se novo → CRIAR com timestamps
   Se existe → ATUALIZAR last_login
        ↓
5. Retornar dados do usuário + flag is_new_user
```

## 📚 Exemplos de Uso

### cURL

```bash
curl -X POST "http://localhost:8000/auth/google" \
  -H "Content-Type: application/json" \
  -d '{
    "id_token": "eyJhbGciOiJSUzI1NiIsImtpZCI6IjEifQ...",
    "email": "usuario@gmail.com",
    "displayName": "João Silva"
  }'
```

### Python (requests)

```python
import requests

data = {
    "id_token": "seu_token_do_google",
    "email": "usuario@gmail.com",
    "displayName": "João Silva"
}

response = requests.post("http://localhost:8000/auth/google", json=data)
result = response.json()

if response.status_code == 200:
    print(f"✅ Autenticado como: {result['email']}")
    print(f"👤 Novo usuário: {result['is_new_user']}")
else:
    print(f"❌ Erro: {result['detail']}")
```

### JavaScript/Fetch

```javascript
async function loginWithGoogle(idToken, email, displayName) {
    const response = await fetch('http://localhost:8000/auth/google', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            id_token: idToken,
            email: email,
            displayName: displayName
        })
    });

    const result = await response.json();
    
    if (response.ok) {
        console.log(`✅ Autenticado como: ${result.email}`);
        console.log(`👤 Novo usuário: ${result.is_new_user}`);
        // Salvar resultado em localStorage/sessão
        localStorage.setItem('user', JSON.stringify(result));
    } else {
        console.error(`❌ Erro: ${result.detail}`);
    }
}
```

### PowerShell

```powershell
$body = @{
    id_token = "seu_token_do_google"
    email = "usuario@gmail.com"
    displayName = "João Silva"
} | ConvertTo-Json

$response = Invoke-WebRequest -Uri "http://localhost:8000/auth/google" `
    -Method Post `
    -ContentType "application/json" `
    -Body $body

$result = $response.Content | ConvertFrom-Json
Write-Host "Autenticado como: $($result.email)"
```

## 🗄️ Dados Salvos no Firestore

Quando um novo usuário se autentica com Google, os seguintes dados são salvos:

```python
{
    "uid": "usuario@gmail.com",
    "email": "usuario@gmail.com",
    "name": "João Silva",
    "auth_provider": "google",
    "created_at": Timestamp(2026, 3, 26, ...),  # SERVER_TIMESTAMP
    "last_login": Timestamp(2026, 3, 26, ...),  # SERVER_TIMESTAMP
    "is_active": True
}
```

Em logins subsequentes, apenas `last_login` é atualizado (além de email/name se mudarem).

## 🔒 Segurança

### Validação

- ✅ Token ID é validado com Firebase
- ✅ Campos obrigatórios são verificados
- ✅ Email é preservado do Google (fonte confiável)
- ✅ Timestamp de último login é registrado para auditoria

### Boas Práticas

1. **Use HTTPS em Produção**: Sempre transmita tokens por HTTPS
2. **Implemente Rate Limiting**: Para prevenir brute force
3. **Valide no Frontend**: Verifique id_token antes de enviar
4. **Expire Tokens**: Implemente refresh tokens com expiração

## 🧪 Testando

Execute o script de teste fornecido:

```bash
python scripts/test_auth_google.py
```

Este script testa:
- ✅ Autenticação bem-sucedida
- ✅ Segunda autenticação (update)
- ✅ Token inválido (deve falhar)
- ✅ Campos faltantes (deve falhar)

## 📋 Checklist de Implementação

- [x] Modelo Pydantic para validação
- [x] Rota POST /auth/google
- [x] Validação de id_token
- [x] Criar usuário novo no Firestore
- [x] Atualizar usuário existente
- [x] Logging de eventos
- [x] Tratamento de erros
- [x] Script de testes
- [x] Documentação

## 🔗 Integração com Frontend

### Exemplo: React com Google Sign-In

```jsx
import { GoogleLogin } from '@react-oauth/google';

function LoginComponent() {
    const handleGoogleSuccess = async (credentialResponse) => {
        const response = await fetch('http://localhost:8000/auth/google', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                id_token: credentialResponse.credential,
                email: credentialResponse.profileObj.email,
                displayName: credentialResponse.profileObj.name
            })
        });

        const result = await response.json();
        if (response.ok) {
            // Login bem-sucedido
            localStorage.setItem('user_token', result.uid);
            window.location.href = '/dashboard';
        }
    };

    return (
        <GoogleLogin
            onSuccess={handleGoogleSuccess}
            onError={() => console.log('Login Failed')}
        />
    );
}
```

## 🎯 Próximas Melhorias

1. [ ] Implementar refresh tokens
2. [ ] Adicionar rota de logout
3. [ ] Implementar rate limiting
4. [ ] Adicionar suporte a múltiplos provedores (GitHub, etc)
5. [ ] Integrar com autenticação de dois fatores

## 📞 Troubleshooting

### Erro: "database (default) does not exist"
**Solução**: Configure o Firestore no Firebase Console

### Erro: "Token inválido"
**Solução**: Verifique se o id_token é um JWT válido do Google

### Erro: "Field required"
**Solução**: Certifique-se de enviar todos os campos obrigatórios

## 📖 Documentação Relacionada

- [README_FINAL.md](README_FINAL.md) - Visão geral do sistema
- [scripts/test_auth_google.py](scripts/test_auth_google.py) - Script de teste