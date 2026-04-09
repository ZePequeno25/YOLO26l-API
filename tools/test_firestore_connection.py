#!/usr/bin/env python3
"""
Teste direto de conexão com Firestore usando as mesmas credenciais do projeto
"""

import firebase_admin
from firebase_admin import credentials, firestore
import os

def test_firestore_connection():
    print("🔍 Testando conexão direta com Firestore...")
    
    try:
        # Caminho para o arquivo de credenciais
        cred_path = "api-tcc/firebase-service-account.json"
        
        if not os.path.exists(cred_path):
            print(f"❌ Arquivo de credenciais não encontrado: {cred_path}")
            return False
            
        print(f"✅ Arquivo de credenciais encontrado: {cred_path}")
        
        # Inicializar o app Firebase (se ainda não estiver)
        try:
            app = firebase_admin.get_app()
            print("✅ App Firebase já inicializado")
        except ValueError:
            # App não inicializado, vamos inicializar
            cred = credentials.Certificate(cred_path)
            app = firebase_admin.initialize_app(cred)
            print("✅ App Firebase inicializado com sucesso")
        
        # Tentar acessar o Firestore
        db = firestore.client()
        print("✅ Cliente Firestore criado")
        
        # Tentar uma operação simples - ler uma coleção (mesmo que vazia)
        collections = db.collections()
        collection_list = list(collections)
        print(f"✅ Conexão Firestore estabelecida. Coleções encontradas: {len(collection_list)}")
        
        # Tentar acessar a coleção 'users' especificamente
        users_ref = db.collection('users')
        print("✅ Referência à coleção 'users' criada")
        
        # Tentar contar documentos (operação leve)
        docs = users_ref.limit(1).get()
        print(f"✅ Consulta à coleção 'users' executada. Documentos encontrados: {len(list(docs))}")
        
        print("\n🎉 SUCESSO: Conexão com Firestore funcionando perfeitamente!")
        return True
        
    except Exception as e:
        print(f"❌ ERRO na conexão com Firestore: {str(e)}")
        print(f"Tipo do erro: {type(e).__name__}")
        import traceback
        print("Traceback completo:")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_firestore_connection()