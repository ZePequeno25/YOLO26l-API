#!/usr/bin/env python3
"""
Script para testar o tempo de resposta (latência) da API de Detecção local.
"""
import time
import requests
import json
from pathlib import Path

def run_timer_test():
    # A API roda na porta 8080 conforme o arquivo .env
    base_url = "http://127.0.0.1:8080"
    
    # Imagem padrão de testes incluída no projeto
    image_path = Path(__file__).parent / "test_result.jpg"
    
    print("=" * 70)
    print("⏱️ TESTE DE TEMPO DE RESPOSTA DA API")
    print("=" * 70)
    print(f"📁 Imagem: {image_path.name} ({image_path.resolve()})")
    
    if not image_path.exists():
        print(f"❌ Erro: Imagem de teste não encontrada em {image_path}")
        return

    # 1. Gerar token de teste
    print("\n🔑 Gerando token de teste...")
    try:
        resp = requests.get(f"{base_url}/auth/test-token", timeout=5)
        if resp.status_code != 200:
            print(f"❌ Falha ao obter token: {resp.status_code} - {resp.text}")
            return
        token = resp.json()["token"]
        print("✅ Token gerado com sucesso!")
    except Exception as e:
        print(f"❌ Erro ao conectar na API. Verifique se o servidor está ativo na porta 8080.\nErro: {e}")
        return

    # 2. Executar predição síncrona
    print("\n🎯 Enviando imagem para análise (Modelo: cadeira)...")
    start_time = time.perf_counter()
    try:
        with open(image_path, "rb") as f:
            files = {"file": (image_path.name, f, "image/jpeg")}
            data = {"id_token": token, "model": "cadeira"}
            resp = requests.post(f"{base_url}/detection/analyze", files=files, data=data, timeout=60)
        
        elapsed = time.perf_counter() - start_time
        
        print("-" * 70)
        print(f"⏱️ TEMPO TOTAL DA REQUISIÇÃO: {elapsed:.3f} segundos")
        print("-" * 70)
        print(f"Status HTTP: {resp.status_code}")
        
        if resp.status_code == 200:
            result = resp.json()
            print("📊 Resultado da Detecção:")
            print(f"   - Cadeiras Encontradas: {result.get('detected_chairs', 0)}")
            print(f"   - Contagem Geral: {result.get('class_counts')}")
            print(f"   - Status de Conformidade: {result.get('compliance_status')}")
            print(f"   - Mensagem IA (Ollama): {result.get('message')}")
        else:
            print(f"❌ Resposta de erro da API: {resp.text}")
            
    except Exception as e:
        print(f"❌ Falha ao realizar requisição de análise: {e}")
    
    print("=" * 70)

if __name__ == "__main__":
    run_timer_test()
