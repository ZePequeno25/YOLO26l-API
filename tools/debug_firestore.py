#!/usr/bin/env python3
"""
Debug detalhado da conexão com Firestore
"""

import json
import os
import google.auth
import google.auth.transport.requests
import requests

def debug_firestore():
    print("🔍 Debug detalhado do Firestore...")
    
    try:
        # 1. Verificar credenciais
        cred_path = "api-tcc/firebase-service-account.json"
        print(f"1️⃣  Verificando arquivo de credenciais: {cred_path}")
        
        if not os.path.exists(cred_path):
            print("❌ Arquivo não encontrado!")
            return
            
        with open(cred_path, 'r') as f:
            cred_data = json.load(f)
        
        print(f"✅ Arquivo carregado")
        print(f"   • Project ID: {cred_data.get('project_id')}")
        print(f"   • Client Email: {cred_data.get('client_email')}")
        
        # 2. Tentar obter credenciais do Google
        print("\n2️⃣  Obtendo credenciais do Google...")
        credentials, project_id = google.auth.load_credentials_from_file(cred_path)
        print(f"✅ Credenciais obtidas")
        print(f"   • Project ID das credenciais: {project_id}")
        print(f"   • Tipo de credencial: {type(credentials).__name__}")
        
        # 3. Atualizar credenciais para obter token
        print("\n3️⃣  Atualizando credenciais para obter token de acesso...")
        request = google.auth.transport.requests.Request()
        credentials.refresh(request)
        
        print(f"✅ Token obtido")
        print(f"   • Token válido até: {credentials.expiry}")
        
        # 4. Fazer chamada direta à API REST do Firestore
        print("\n4️⃣  Testando API REST do Firestore...")
        url = f"https://firestore.googleapis.com/v1/projects/{project_id}/databases/(default)/documents"
        headers = {
            "Authorization": f"Bearer {credentials.token}",
            "Content-Type": "application/json"
        }
        
        print(f"   • URL: {url}")
        response = requests.get(url, headers=headers, timeout=10)
        
        print(f"   • Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ SUCESSO: Conexão com Firestore funcionando via REST API!")
            data = response.json()
            print(f"   • Resposta: {json.dumps(data, indent=2)[:200]}...")
        else:
            print(f"❌ FALHA: Erro na API REST")
            print(f"   • Resposta: {response.text}")
            
            # Tentar interpretar o erro
            if response.status_code == 404:
                print("\n🔍 ANÁLISE: Erro 404 indica que:")
                print("   • O projeto não existe, OU")
                print("   • O banco de dados '(default)' não existe no projeto, OU")
                print("   • Não há permissão para acessar o Firestore")
                
            elif response.status_code == 403:
                print("\n🔍 ANÁLISE: Erro 403 indica falta de permissão")
                
    except Exception as e:
        print(f"❌ ERRO durante o debug: {str(e)}")
        print(f"Tipo: {type(e).__name__}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_firestore()