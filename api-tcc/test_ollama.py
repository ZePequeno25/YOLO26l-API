import sys
import time
import subprocess
from pathlib import Path

# Adiciona o diretório atual ao sys.path para evitar problemas de importação
sys.path.insert(0, str(Path(__file__).parent.resolve()))

from config.settings import settings
from app.services.ollama_message_service import OllamaMessageService

def test_ollama():
    print("=== TESTE DE DIAGNÓSTICO DO OLLAMA ===\n")
    
    # 1. Verificar se o executável do Ollama responde
    print("1. Verificando comando 'ollama list'...")
    t0 = time.time()
    try:
        res = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=10
        )
        t_elapsed = time.time() - t0
        if res.returncode == 0:
            print(f"✅ Ollama respondeu com sucesso em {t_elapsed:.2f}s!")
            print("Modelos instalados localmente:")
            print(res.stdout.strip())
        else:
            print(f"❌ Comando 'ollama list' falhou (código de saída {res.returncode}):")
            print(res.stderr.strip())
    except FileNotFoundError:
        print("❌ Erro: O comando 'ollama' não foi encontrado no PATH do sistema.")
        print("Certifique-se de que o Ollama está instalado e adicionado às variáveis de ambiente.")
        return
    except subprocess.TimeoutExpired:
        print("❌ Erro: O comando 'ollama list' expirou (timeout de 10s). O serviço do Ollama está rodando?")
        return
    except Exception as e:
        print(f"❌ Erro ao executar 'ollama list': {e}")
        return

    print("\n" + "="*40 + "\n")

    # 2. Testar geração de mensagem pelo serviço
    print(f"2. Testando geração de mensagem pelo OllamaMessageService...")
    print(f"Configuração do Modelo: {settings.OLLAMA_MODEL}")
    print(f"Timeout configurado: {settings.OLLAMA_TIMEOUT_SECONDS}s")
    
    # Forçar ativação temporária das mensagens personalizadas para o teste
    settings.ENABLE_PERSONALIZED_MESSAGE = True
    
    service = OllamaMessageService()
    
    # Caso de teste 1: Encontrou o objeto solicitado (cadeira)
    test_result_1 = {
        "class_counts": {"cadeira": 2},
        "num_frames_processed": 1,
        "frames_with_detections": 1,
    }
    
    print("\n-> Caso de Teste 1: Solicita 'cadeira', encontra 2 cadeiras.")
    t0 = time.time()
    try:
        msg_1 = service.generate_personalized_message(test_result_1, "cadeira")
        t_elapsed = time.time() - t0
        print(f"Tempo gasto: {t_elapsed:.2f}s")
        print(f"Mensagem gerada: \"{msg_1}\"")
    except Exception as e:
        print(f"❌ Erro ao gerar mensagem 1: {e}")

    # Caso de teste 2: Não encontrou o solicitado, mas encontrou outro objeto
    test_result_2 = {
        "class_counts": {"extintor_de_incndio": 1},
        "num_frames_processed": 1,
        "frames_with_detections": 1,
    }
    
    print("\n-> Caso de Teste 2: Solicita 'cadeira', não encontra cadeira, mas encontra 1 extintor.")
    t0 = time.time()
    try:
        msg_2 = service.generate_personalized_message(test_result_2, "cadeira")
        t_elapsed = time.time() - t0
        print(f"Tempo gasto: {t_elapsed:.2f}s")
        print(f"Mensagem gerada: \"{msg_2}\"")
    except Exception as e:
        print(f"❌ Erro ao gerar mensagem 2: {e}")

    # Caso de teste 3: Não encontrou nada
    test_result_3 = {
        "class_counts": {},
        "num_frames_processed": 1,
        "frames_with_detections": 0,
    }
    
    print("\n-> Caso de Teste 3: Solicita 'cadeira', nenhuma detecção na cena.")
    t0 = time.time()
    try:
        msg_3 = service.generate_personalized_message(test_result_3, "cadeira")
        t_elapsed = time.time() - t0
        print(f"Tempo gasto: {t_elapsed:.2f}s")
        print(f"Mensagem gerada: \"{msg_3}\"")
    except Exception as e:
        print(f"❌ Erro ao gerar mensagem 3: {e}")

if __name__ == "__main__":
    test_ollama()
