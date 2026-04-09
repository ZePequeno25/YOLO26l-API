#!/usr/bin/env python3
"""
Script definitivo para verificar se o Firestore foi criado corretamente
"""

import json
import os
import requests
import time

def verify_firestore_exists():
    print("🔍 VERIFICAÇÃO DEFINITIVA: Firestore existe no projeto tcc-kelvin?")
    print("=" * 70)
    
    try:
        # 1. Ler credenciais para obter project_id
        cred_path = "api-tcc/firebase-service-account.json"
        with open(cred_path, 'r') as f:
            cred_data = json.load(f)
        
        project_id = cred_data.get('project_id')
        print(f"📋 Project ID das credenciais: {project_id}")
        
        if project_id != "tcc-kelvin":
            print(f"❌ ERRO: Project ID nas credenciais é '{project_id}', esperado 'tcc-kelvin'")
            return False
        
        print("✅ Project ID correto")
        
        # 2. Tentar acessar o Firestore via API REST com token de serviço
        print("\n🔧 Tentando acesso direto à API do Firestore...")
        
        # Usar o método de serviço account para obter token
        from google.oauth2 import service_account
        import google.auth.transport.requests
        
        SCOPES = ['https://www.googleapis.com/auth/datastore']
        credentials = service_account.Credentials.from_service_account_file(
            cred_path, scopes=SCOPES)
        
        request = google.auth.transport.requests.Request()
        credentials.refresh(request)
        
        # 3. Fazer chamada para verificar se o banco existe
        url = f"https://firestore.googleapis.com/v1/projects/{project_id}/databases/(default)"
        headers = {
            "Authorization": f"Bearer {credentials.token}",
            "Content-Type": "application/json"
        }
        
        print(f"🌐 Chamando: {url}")
        response = requests.get(url, headers=headers, timeout=10)
        
        print(f"📊 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ SUCESSO: Banco de dados Firestore EXISTE e é acessível!")
            try:
                data = response.json()
                print(f"📄 Informações do banco:")
                print(f"   • Nome: {data.get('name')}")
                print(f"   • Localização: {data.get('locationId', 'Não especificada')}")
                print(f"   • Estado: {data.get('state', 'Desconhecido')}")
                return True
            except Exception as e:
                print(f"✅ Banco acessível (erro ao parsear JSON: {e})")
                return True
                
        elif response.status_code == 404:
            print("❌ CONFIRMADO: Banco de dados Firestore NÃO EXISTE")
            print("📝 O erro 404 significa que o recurso '/databases/(default)' não foi encontrado")
            print("🔧 Você PRECISA criar o banco de dados no Firebase Console")
            return False
            
        elif response.status_code == 403:
            print("⚠️  ACESSO NEGADO (403) - Banco pode existir mas sem permissão")
            print("🔧 Verifique:")
            print("   • Se a conta de serviço tem papel adequado no IAM do Firebase")
            print("   • Se a API do Firestore Cloud está ativada")
            print(f"   • Token obtido: {credentials.token[:20]}...")
            return False
            
        else:
            print(f"❓ STATUS INESPERADO: {response.status_code}")
            print(f"📄 Resposta: {response.text[:200]}...")
            return False
            
    except Exception as e:
        print(f"💥 ERRO durante verificação: {str(e)}")
        print(f"Tipo: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False

def provide_creation_instructions():
    print("\n" + "=" * 70)
    print("📝 INSTRUÇÕES PARA CRIAR O FIRESTORE")
    print("=" * 70)
    print("""
1️⃣  MÉTODO RECOMENDADO - LINK DIRETO:
   👉 CLIQUE AQUI: https://console.cloud.google.com/datastore/setup?project=tcc-kelvin
   
   Na página que abrir:
   • Selecione "Modo de teste" (ideal para desenvolvimento)
   • Escolha uma localização (ex: nam5 para EUA)
   • Clique em "Criar banco de dados"

2️⃣  MÉTODO ALTERNATIVO - VIA FIREBASE CONSOLE:
   👉 Acesse: https://console.firebase.google.com/
   👉 Selecione o projeto: tcc-kelvin
   👉 Menu lateral: Build → Firestore Database
   👉 Clique em "Criar banco de dados"
   👉 Escolha o modo e localização, depois "Ativar"

3️⃣  APÓS CRIAR:
   • Aguarde 30-60 segundos para propagação
   • Execute este script novamente para verificar
   • Depois teste sua autenticação: python scripts\\test_auth_google.py

⚠️  IMPORTANTE:
   • O "Modo de teste" permite leitura/escrita livre por 30 dias (perfeito para dev)
   • NÃO use modo de teste em produção - configure regras de segurança adequadas
   • Se ainda vir erro após criar, verifique se está no projeto CORRETO (tcc-kelvin)
""")

if __name__ == "__main__":
    exists = verify_firestore_exists()
    
    if not exists:
        provide_creation_instructions()
        print("\n🎯 PRÓXIMO PASSO: Crie o Firestore usando as instruções acima,")
        print("   então execute este script novamente para verificar.")
    else:
        print("\n🎉 FIRESTORE CONFIRMADO! Seu banco de dados está pronto.")
        print("   Agora você pode testar a autenticação Google:")
        print("   python scripts\\test_auth_google.py")