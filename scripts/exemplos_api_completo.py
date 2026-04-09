#!/usr/bin/env python3
"""
Exemplo completo: Analisar imagem/vídeo e fazer download do resultado.
"""

import requests
from pathlib import Path
import json

class DetectionClient:
    def __init__(self, api_url="http://localhost:8000", auth_token=None):
        self.api_url = api_url
        self.auth_token = auth_token
        self.headers = {}
        if auth_token:
            self.headers["Authorization"] = f"Bearer {auth_token}"
    
    def list_models(self):
        """Lista modelos disponíveis."""
        response = requests.get(f"{self.api_url}/detection/models")
        return response.json()
    
    def analyze_file(self, file_path, model="chair", use_auth=False):
        """
        Analisa um arquivo (imagem ou vídeo).
        
        Args:
            file_path: Caminho para o arquivo
            model: Nome do modelo a usar
            use_auth: Se deve usar autenticação
            
        Returns:
            dict com resultado da análise
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")
        
        endpoint = "/detection/analyze" if use_auth else "/detection/analyze-test"
        
        with open(file_path, "rb") as f:
            files = {"file": f}
            data = {"model": model}
            
            if use_auth and self.auth_token:
                data["id_token"] = self.auth_token
            
            response = requests.post(
                f"{self.api_url}{endpoint}",
                files=files,
                data=data,
                headers=self.headers
            )
        
        if response.status_code != 200:
            raise Exception(f"Erro: {response.status_code} - {response.text}")
        
        return response.json()
    
    def download_analyzed_file(self, analyzed_file_path, output_path=None):
        """
        Faz download de um arquivo analisado.
        
        Args:
            analyzed_file_path: Caminho ou nome do arquivo analisado
            output_path: Onde salvar o arquivo (padrão: nome original)
            
        Returns:
            Caminho do arquivo salvo
        """
        # Extrair apenas o nome do arquivo
        filename = Path(analyzed_file_path).name
        
        response = requests.get(
            f"{self.api_url}/detection/download/{filename}",
            headers=self.headers
        )
        
        if response.status_code != 200:
            raise Exception(f"Erro no download: {response.status_code}")
        
        # Determinar caminho de saída
        if output_path is None:
            output_path = Path.cwd() / filename
        else:
            output_path = Path(output_path)
        
        # Criar diretório se necessário
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Salvar arquivo
        with open(output_path, "wb") as f:
            f.write(response.content)
        
        return output_path
    
    def analyze_and_download(self, file_path, output_dir=None, model="chair", use_auth=False):
        """
        Analisa um arquivo e faz download do resultado em uma operação.
        
        Args:
            file_path: Arquivo a analisar
            output_dir: Diretório para salvar resultado (padrão: ./downloads)
            model: Modelo a usar
            use_auth: Se deve usar autenticação
            
        Returns:
            Tuple (resultado_analise, caminho_arquivo_baixado)
        """
        # Analisar
        print(f"📁 Analisando: {file_path}")
        resultado = self.analyze_file(file_path, model, use_auth)
        print(f"✅ Análise concluída!")
        print(f"   Detecções: {resultado['class_counts']}")
        
        if not resultado.get('analyzed_file'):
            raise Exception("Arquivo analisado não foi retornado")
        
        # Fazer download
        analyzed_file = resultado['analyzed_file']
        if output_dir:
            output_path = Path(output_dir) / Path(analyzed_file).name
        else:
            output_path = Path("downloads") / Path(analyzed_file).name
        
        print(f"📥 Fazendo download...")
        caminho_salvo = self.download_analyzed_file(analyzed_file, output_path)
        print(f"✅ Arquivo salvo: {caminho_salvo}")
        
        return resultado, caminho_salvo


# ============================================================================
# EXEMPLOS DE USO
# ============================================================================

def exemplo_basico():
    """Exemplo 1: Uso básico - analisar e fazer download"""
    print("=" * 60)
    print("EXEMPLO 1: Análise Básica")
    print("=" * 60 + "\n")
    
    client = DetectionClient()
    
    # Listar modelos disponíveis
    print("📋 Modelos disponíveis:")
    models = client.list_models()
    for model in models['models']:
        print(f"   • {model}")
    print()
    
    # Analisar imagem
    resultado, arquivo_salvo = client.analyze_and_download(
        "data/content/custom_data/test/images/110_png_jpg.rf.18b130280ec44c73e4452afecfc09ea9.jpg",
        output_dir="downloads",
        model="chair"
    )
    
    print(f"\n📊 Resultado completo:")
    print(json.dumps(resultado, indent=2, ensure_ascii=False))


def exemplo_multiplos_modelos():
    """Exemplo 2: Analisar com múltiplos modelos"""
    print("\n" + "=" * 60)
    print("EXEMPLO 2: Múltiplos Modelos")
    print("=" * 60 + "\n")
    
    client = DetectionClient()
    
    # Obter lista de modelos
    models = client.list_models()['models']
    
    arquivo_teste = "data/content/custom_data/test/images/110_png_jpg.rf.18b130280ec44c73e4452afecfc09ea9.jpg"
    
    for model_name in models[:2]:  # Testar primeiros 2 modelos
        print(f"\n🔄 Analisando com modelo: {model_name}")
        try:
            resultado, _ = client.analyze_and_download(
                arquivo_teste,
                output_dir="downloads",
                model=model_name
            )
            print(f"   → Detecções: {resultado['class_counts']}")
        except Exception as e:
            print(f"   ✗ Erro: {e}")


def exemplo_batch_processing():
    """Exemplo 3: Processar múltiplas imagens"""
    print("\n" + "=" * 60)
    print("EXEMPLO 3: Processamento em Lote")
    print("=" * 60 + "\n")
    
    client = DetectionClient()
    
    # Encontrar imagens test
    test_dir = Path("data/content/custom_data/test/images")
    imagens = list(test_dir.glob("*.jpg"))[:3]  # Primeiras 3 imagens
    
    resultados = []
    for i, imagem in enumerate(imagens, 1):
        print(f"\n[{i}/{len(imagens)}] Processando: {imagem.name}")
        try:
            resultado, arquivo = client.analyze_and_download(
                str(imagem),
                output_dir="downloads/batch",
                model="chair"
            )
            resultados.append({
                "arquivo": imagem.name,
                "deteccoes": resultado['class_counts'],
                "total": sum(resultado['class_counts'].values()),
                "resultado_salvo": str(arquivo)
            })
        except Exception as e:
            print(f"   ✗ Erro: {e}")
    
    # Resumo
    print(f"\n📊 Resumo do Processamento em Lote:")
    print(f"   Total: {len(resultados)} imagens processadas")
    total_deteccoes = sum(r['total'] for r in resultados)
    print(f"   Detecções totais: {total_deteccoes}")


def exemplo_tratamento_erros():
    """Exemplo 4: Tratamento de erros"""
    print("\n" + "=" * 60)
    print("EXEMPLO 4: Tratamento de Erros")
    print("=" * 60 + "\n")
    
    client = DetectionClient()
    
    # Teste 1: Arquivo inexistente
    print("1️⃣  Testando arquivo inexistente...")
    try:
        client.analyze_file("arquivo_que_nao_existe.jpg")
    except FileNotFoundError as e:
        print(f"   ✓ Erro capturado: {e}")
    print()
    
    # Teste 2: Arquivo inválido
    print("2️⃣  Testando arquivo inválido...")
    try:
        # Criar arquivo texto
        Path("teste.txt").write_text("isso não é uma imagem")
        client.analyze_file("teste.txt")
    except Exception as e:
        print(f"   ✓ Erro capturado: {type(e).__name__}")
    finally:
        Path("teste.txt").unlink()
    print()
    
    # Teste 3: Modelo inexistente
    print("3️⃣  Testando modelo inexistente...")
    try:
        resultado = client.analyze_file(
            "data/content/custom_data/test/images/110_png_jpg.rf.18b130280ec44c73e4452afecfc09ea9.jpg",
            model="modelo_que_nao_existe"
        )
        print(f"   Resultado: {resultado['class_counts']}")
    except Exception as e:
        print(f"   ✓ Erro capturado: {type(e).__name__}")


# ============================================================================
# EXECUTAR EXEMPLOS
# ============================================================================

if __name__ == "__main__":
    print("🚀 Exemplos de Uso da API de Detecção\n")
    
    try:
        exemplo_basico()
        exemplo_multiplos_modelos()
        exemplo_batch_processing()
        exemplo_tratamento_erros()
        
        print("\n" + "=" * 60)
        print("✅ Todos os exemplos executados com sucesso!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Erro ao executar exemplos: {e}")
        import traceback
        traceback.print_exc()