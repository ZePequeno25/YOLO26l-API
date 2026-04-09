# 📋 Guia Rápido: Como Criar o Firestore no Firebase Console

## 🚨 Problema Identificado
Seu código está correto, mas o erro persiste:
```
404 The database (default) does not exist for project tcc-kelvin
```

Isso significa que o **banco de dados Firestore NÃO foi criado** no projeto Firebase `tcc-kelvin`.

## ✅ Solução: Criar o Banco de Dados Firestore

### Método 1: Link Direto (Recomendado)
1. **Clique neste link**: 
   [https://console.cloud.google.com/datastore/setup?project=tcc-kelvin](https://console.cloud.google.com/datastore/setup?project=tcc-kelvin)
   
2. **Na tela que abrir**:
   - Selecione **"Modo de teste"** (ideal para desenvolvimento)
   - Escolha uma localização (ex: `nam5` para EUA)
   - Clique em **"Criar banco de dados"**

### Método 2: Através do Firebase Console
1. Acesse: [https://console.firebase.google.com/](https://console.firebase.google.com/)
2. Selecione seu projeto: **`tcc-kelvin`**
3. No menu lateral: **Build** → **Firestore Database**
4. Clique em **"Criar banco de dados"**
5. Escolha o modo e localização, depois clique em **"Ativar"**

## 🔍 Como Verificar se Funcionou

Após criar o banco, você deve ver no Firebase Console:
- ✅ **Nenhuma mensagem de erro** sobre banco não existente
- ✅ Interface do Firestore com abas: **Dados**, **Regras**, **Índices**
- ✅ Possibilidade de criar coleções (como `users`)

## 🧪 Teste Após a Criação

Execute novamente:
```bash
cd "C:\Users\aborr\Projeto TCC"
python scripts\test_auth_google.py
```

## 📝 Esperado Após Sucesso

Primeira chamada (novo usuário):
```json
{
  "success": true,
  "message": "Usuário criado com sucesso",
  "uid": "usuario@gmail.com",
  "email": "usuario@gmail.com",
  "name": "João Silva",
  "email_verified": true,
  "is_new_user": true
}
```

Segunda chamada (mesmo usuário - update):
```json
{
  "success": true,
  "message": "Autenticação concluída com sucesso",
  "uid": "usuario@gmail.com",
  "email": "usuario@gmail.com",
  "name": "João Silva Atualizado",
  "email_verified": true,
  "is_new_user": false
}
```

## ⚠️ Observações Importantes

1. **Modo de teste expira em 30 dias** - perfeito para desenvolvimento
2. **Nunca use modo de teste em produção** - configure regras de segurança adequadas
3. **As credenciais já estão corretas** no arquivo `api-tcc/firebase-service-account.json`
4. **Seu código está pronto** - só falta o banco existir!

## 🔗 Links Úteis

- Firebase Console: https://console.firebase.google.com/
- Link direto para criação: https://console.cloud.google.com/datastore/setup?project=tcc-kelvin
- Documentação Firestore: https://firebase.google.com/docs/firestore

---

**Após criar o banco, seus testes de autenticação Google funcionarão perfeitamente!** 🎉