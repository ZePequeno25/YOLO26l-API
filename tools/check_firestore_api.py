#!/usr/bin/env python3
"""
Verificar se a API do Firestore está ativada e testar com escopos corretos
"""

import json
import os
import google.auth
import google.auth.transport.requests
import requests
from google.oauth2 import service_account

def check_firestore_setup():
    print("🔍 Verificando configuração do Firestore...")
    
    try:
        # 1. Carregar credenciais
        cred_path = "api-tcc/firebase-service-account.json"
        print(f"1️⃣  Carregando credenciais de: {cred_path}")
        
        with open(cred_path, 'r') as f:
            cred_data = json.load(f)
        
        project_id = cred_data.get('project_id')
        print(f"✅ Project ID: {project_id}")
        
        # 2. Criar credenciais com escopos específicos para Firestore
        print("\n2️⃣  Criando credenciais com escopos do Firestore...")
        SCOPES = [
            'https://www.googleapis.com/auth/datastore',  # Escopo legado do Datastore/Firestore
            'https://www.googleapis.com/auth/cloud-platform'  # Escopo amplo
        ]
        
        credentials = service_account.Credentials.from_service_account_file(
            cred_path, scopes=SCOPES)
        
        print("✅ Credenciais com escopos criadas")
        
        # 3. Obter token de acesso
        print("\n3️⃣  Obtendo token de acesso...")
        request = google.auth.transport.requests.Request()
        credentials.refresh(request)
        
        print(f"✅ Token obtido, válido até: {credentials.expiry}")
        
        # 4. Testar API do Firestore
        print("\n4️⃣  Testando API do Firestore...")
        url = f"https://firestore.googleapis.com/v1/projects/{project_id}/databases/(default)/documents"
        headers = {
            "Authorization": f"Bearer {credentials.token}",
            "Content-Type": "application/json"
        }
        
        print(f"   Chamando: {url}")
        response = requests.get(url, headers=headers, timeout=15)
        
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ SUCESSO: Firestore acessível!")
            try:
                data = response.json()
                print(f"   Resposta: {json.dumps(data, indent=2)[:300]}...")
            except:
                print(f"   Resposta (texto): {response.text[:200]}...")
        else:
            print(f"❌ FALHA: {response.status_code}")
            print(f"   Resposta: {response.text}")
            
            # Análise específica do erro
            if response.status_code == 403:
                print("\n🔍 ANÁLISE 403: Permissão insuficiente")
                print("   Possíveis causas:")
                print("   • A conta de serviço não tem papel adequado no IAM")
                print("   • A API do Firestore Cloud não está ativada")
                print("   • Escopos insuficientes")
                
            elif response.status_code == 404:
                print("\n🔍 ANÁLISE 404: Recurso não encontrado")
                print("   Possíveis causas:")
                print("   • O projeto ID está incorreto")
                print("   • O banco de dados '(default)' não foi criado")
                print("   • O nome do banco está errado (deve ser '(default)')")
                
        # 5. Tentar verificar se a API está ativada via Cloud Resource Manager
        print("\n5️⃣  Verificando status da API do Firestore...")
        api_url = f"https://serviceusage.googleapis.com/v1/projects/{project_id}/services/firestore.googleapis.com"
        api_response = requests.get(api_url, headers=headers, timeout=10)
        
        if api_response.status_code == 200:
            api_data = api_response.json()
            state = api_data.get('state', 'UNKNOWN')
            print(f"   Estado da API Firestore: {state}")
            if state == 'ENABLED':
                print("   ✅ API do Firestore está ativada")
            else:
                print("   ⚠️  API do Firestore pode não estar ativada")
        else:
            print(f"   Não foi possível verificar estado da API: {api_response.status_code}")
            
    except Exception as e:
        print(f"❌ ERRO: {str(e)}")
        print(f"Tipo: {type(e).__name__}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_firestore_setup()