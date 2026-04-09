#!/usr/bin/env python3
"""
Script de teste para a nova rota de autenticação Google: POST /auth/google
"""

import requests
import json
from pathlib import Path

API_URL = "http://localhost:8000"

def test_google_auth():
    """Testa a autenticação com Google."""
    print("=" * 70)
    print("🧪 Testando Rota POST /auth/google")
    print("=" * 70 + "\n")
    
    # Dados de teste
    google_auth_data = {
        "id_token": "admin_master_token",  # Token fixo para testes locais
        "email": "usuario@gmail.com",
        "displayName": "João Silva"
    }
    
    print(f"📤 Enviando requisição para: POST {API_URL}/auth/google")
    print(f"📋 Corpo da requisição:")
    print(json.dumps(google_auth_data, indent=2, ensure_ascii=False))
    print()
    
    try:
        response = requests.post(
            f"{API_URL}/auth/google",
            json=google_auth_data
        )
        
        print(f"📊 Status Code: {response.status_code}\n")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Autenticação bem-sucedida!")
            print(f"📋 Resposta:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            
            print(f"\n🔍 Detalhes:")
            print(f"   • UID: {result['uid']}")
            print(f"   • Email: {result['email']}")
            print(f"   • Name: {result['name']}")
            print(f"   • Email Verificado: {result['email_verified']}")
            print(f"   • Novo Usuário: {result['is_new_user']}")
            print(f"   • Mensagem: {result['message']}")
        else:
            print(f"❌ Erro na resposta:")
            print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    
    except requests.exceptions.ConnectionError:
        print("❌ Erro: Não foi possível conectar à API")
        print("   Verifique se o servidor está rodando em http://localhost:8000")
    except Exception as e:
        print(f"❌ Erro: {e}")
    
    print()


def test_google_auth_second_login():
    """Testa segunda autenticação do mesmo usuário (deve atualizar last_login)."""
    print("=" * 70)
    print("🧪 Testando Segunda Autenticação (Update)")
    print("=" * 70 + "\n")
    
    google_auth_data = {
        "id_token": "admin_master_token",
        "email": "usuario@gmail.com",
        "displayName": "João Silva Atualizado"
    }
    
    print(f"📤 Enviando segunda requisição para o mesmo usuário...")
    print(f"📋 Corpo da requisição:")
    print(json.dumps(google_auth_data, indent=2, ensure_ascii=False))
    print()
    
    try:
        response = requests.post(
            f"{API_URL}/auth/google",
            json=google_auth_data
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Segunda autenticação bem-sucedida!")
            print(f"\n🔍 Detalhes:")
            print(f"   • UID: {result['uid']}")
            print(f"   • Email: {result['email']}")
            print(f"   • Name: {result['name']}")
            print(f"   • Novo Usuário: {result['is_new_user']} (deve ser False)")
            print(f"   • Mensagem: {result['message']}")
        else:
            print(f"❌ Erro na resposta: {response.status_code}")
            print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    
    except Exception as e:
        print(f"❌ Erro: {e}")
    
    print()


def test_google_auth_invalid_token():
    """Testa autenticação com token inválido."""
    print("=" * 70)
    print("🧪 Testando Autenticação com Token Inválido")
    print("=" * 70 + "\n")
    
    google_auth_data = {
        "id_token": "token_invalido_xyz123",
        "email": "usuario@gmail.com",
        "displayName": "João Silva"
    }
    
    print(f"📤 Enviando requisição com token inválido...")
    
    try:
        response = requests.post(
            f"{API_URL}/auth/google",
            json=google_auth_data
        )
        
        print(f"📊 Status Code: {response.status_code}\n")
        
        if response.status_code != 200:
            print(f"✅ Erro detectado corretamente (esperado)")
            print(f"📋 Detalhes do erro:")
            print(json.dumps(response.json(), indent=2, ensure_ascii=False))
        else:
            print(f"⚠️  Token inválido foi aceito (inesperado)")
    
    except Exception as e:
        print(f"Erro: {e}")
    
    print()


def test_google_auth_missing_fields():
    """Testa autenticação com campos faltantes."""
    print("=" * 70)
    print("🧪 Testando Autenticação com Campos Faltantes")
    print("=" * 70 + "\n")
    
    # Faltando displayName
    google_auth_data = {
        "id_token": "admin_master_token",
        "email": "usuario@gmail.com"
    }
    
    print(f"📤 Enviando requisição sem campo 'displayName'...")
    print(f"📋 Corpo da requisição:")
    print(json.dumps(google_auth_data, indent=2, ensure_ascii=False))
    print()
    
    try:
        response = requests.post(
            f"{API_URL}/auth/google",
            json=google_auth_data
        )
        
        print(f"📊 Status Code: {response.status_code}\n")
        
        if response.status_code != 200:
            print(f"✅ Validação funcionou corretamente")
            print(f"📋 Detalhes do erro:")
            print(json.dumps(response.json(), indent=2, ensure_ascii=False))
        else:
            print(f"⚠️  Validação não rejeitou dados incompletos")
    
    except Exception as e:
        print(f"Erro: {e}")
    
    print()


def show_curl_examples():
    """Mostra exemplos de uso com cURL."""
    print("=" * 70)
    print("📚 Exemplos de Uso com cURL")
    print("=" * 70 + "\n")
    
    print("1️⃣  Autenticação Básica:")
    print("""
curl -X POST "http://localhost:8000/auth/google" \\
  -H "Content-Type: application/json" \\
  -d '{
    "id_token": "seu_token_do_google",
    "email": "usuario@gmail.com",
    "displayName": "João Silva"
  }'
""")
    
    print("\n2️⃣  Com Token de Teste (dev only):")
    print("""
curl -X POST "http://localhost:8000/auth/google" \\
  -H "Content-Type: application/json" \\
  -d '{
    "id_token": "admin_master_token",
    "email": "usuario@gmail.com",
    "displayName": "João Silva"
  }'
""")
    
    print("\n3️⃣  Em PowerShell:")
    print("""
$body = @{
    id_token = "seu_token_do_google"
    email = "usuario@gmail.com"
    displayName = "João Silva"
} | ConvertTo-Json

Invoke-WebRequest -Uri "http://localhost:8000/auth/google" `
  -Method Post `
  -ContentType "application/json" `
  -Body $body
""")
    
    print("\n4️⃣  Em Python (requests):")
    print("""
import requests

data = {
    "id_token": "seu_token_do_google",
    "email": "usuario@gmail.com",
    "displayName": "João Silva"
}

response = requests.post("http://localhost:8000/auth/google", json=data)
print(response.json())
""")


def main():
    print("\n🚀 Script de Teste da Rota POST /auth/google\n")
    
    # Mostrar exemplos
    show_curl_examples()
    
    print("\n" + "=" * 70)
    print("🧪 Executando Testes...")
    print("=" * 70 + "\n")
    
    try:
        # Testar autenticação básica
        test_google_auth()
        
        # Testar segunda autenticação
        test_google_auth_second_login()
        
        # Testar token inválido
        test_google_auth_invalid_token()
        
        # Testar campos faltantes
        test_google_auth_missing_fields()
        
        print("=" * 70)
        print("✅ Todos os testes foram executados!")
        print("=" * 70)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Testes interrompidos pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro geral: {e}")


if __name__ == "__main__":
    main()