#!/usr/bin/env python3
import subprocess
import sys
import os

def main():
    # Mudar diretório de trabalho para a pasta do script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # Garantir que a pasta logs exista
    os.makedirs("logs", exist_ok=True)
    
    # Configurar codificação de ambiente
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    
    # Comando para rodar a API usando o mesmo interpretador da .venv
    cmd = [sys.executable, "-X", "utf8", "main.py"]
    
    print("🚀 [Runner] Iniciando API YOLO...")
    print("💾 [Runner] Logs serão salvos diretamente em UTF-8 no arquivo: api-tcc/logs/api_manual.log")
    print("-" * 80)
    
    try:
        # Iniciar o subprocesso capturando saídas combinadas em UTF-8
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env
        )
        
        # Abrir o arquivo de log para gravação em tempo real
        with open("logs/api_manual.log", "w", encoding="utf-8") as log_file:
            for line in process.stdout:
                # Imprime no terminal em tempo real
                sys.stdout.write(line)
                sys.stdout.flush()
                # Escreve no log em UTF-8
                log_file.write(line)
                log_file.flush()
                
        process.wait()
    except KeyboardInterrupt:
        print("\n🛑 [Runner] Encerrando API pelo usuário (Ctrl+C)...")
    except Exception as e:
        print(f"\n❌ [Runner] Erro inesperado: {e}")

if __name__ == "__main__":
    main()
