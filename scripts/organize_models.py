#!/usr/bin/env python3
"""
Script para organizar modelos YOLO por classes detectadas.
Este script:
1. Varre todas as pastas em models/
2. Para cada modelo .pt encontrado, carrega e identifica as classes
3. Renomeia a pasta para o nome da classe principal (se única)
4. Cria arquivos de configuração padronizados
5. Trata conflitos de nomes adicionando sufixos
"""

import json
import os
import re
import shutil
import subprocess  # nosec B404
from collections import defaultdict
from pathlib import Path

from ultralytics import YOLO

DEFAULT_OLLAMA_COMMAND = "ollama"
DEFAULT_OLLAMA_MODEL = "qwen2.5-coder:7b"
DEFAULT_OLLAMA_TIMEOUT_SECONDS = 60


def build_ollama_prompt(class_names):
    """Constrói o prompt para tradução de nomes de classes."""
    return (
        "Você é um assistente que transforma nomes de classes de objetos em etiquetas simples, curtas e únicas em português.\n"
        "Retorne APENAS um JSON válido. As chaves devem ser os nomes originais e os valores os nomes curtos em português.\n"
        "Use uma ou duas palavras no máximo, preferencialmente em singular, e crie valores diferentes para classes diferentes.\n"
        "Não inclua explicações, markdown, exemplos ou texto extra.\n\n"
        f"Classes: {json.dumps(class_names, ensure_ascii=False)}\n"
    )


def extract_json_object(text):
    """Extrai o primeiro JSON válido do texto da saída do Ollama."""
    text = text.strip()
    if not text:
        return None

    match = re.search(r"\{.*\}", text, flags=re.S)
    return match.group(0) if match else text


def simplify_label(name: str) -> str:
    """Fallback simples para nomes quando Ollama não estiver disponível."""
    value = name.strip()
    value = re.sub(r"[_\-]+", " ", value)
    value = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", value)
    value = re.sub(r"\s+", " ", value).strip().lower()

    translations = {
        "fire extinguisher": "extintor",
        "fire extinguisher sign": "extintor",
        "stop sign": "placa de pare",
        "person": "pessoa",
        "chair": "cadeira",
        "door": "porta",
        "window": "janela",
        "table": "mesa",
        "bottle": "garrafa",
        "car": "carro",
        "truck": "caminhão",
    }

    for english, portuguese in translations.items():
        if english in value:
            return portuguese

    if value.endswith(" sign"):
        value = value[: -len(" sign")]
    if value.endswith(" object"):
        value = value[: -len(" object")]
    if value.endswith(" detector"):
        value = value[: -len(" detector")]

    return value or name


def make_unique(values):
    """Garante que as labels sejam únicas, adicionando sufixos curtos se necessário."""
    seen = {}
    unique = []
    for value in values:
        normalized = value.strip().lower() or "objeto"
        if normalized not in seen:
            seen[normalized] = 1
            unique.append(normalized)
        else:
            seen[normalized] += 1
            unique.append(f"{normalized}_{seen[normalized]}")
    return unique


def normalize_folder_name(name: str) -> str:
    """Normaliza o nome da pasta para um identificador curto e seguro."""
    normalized = name.strip().lower()
    normalized = re.sub(r"\s+", "_", normalized)
    normalized = re.sub(r"[^a-z0-9_]+", "", normalized)
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    
    # Limita o tamanho do nome da pasta para evitar erro de MAX_PATH no Windows
    if len(normalized) > 50:
        truncated = normalized[:50]
        last_underscore = truncated.rfind('_')
        if last_underscore > 20:
            normalized = truncated[:last_underscore] + "_etc"
        else:
            normalized = truncated + "_etc"
            
    return normalized or "modelo"


def translate_labels_with_ollama(class_names):
    """Usa Ollama local para traduzir nomes de classes."""
    command = os.getenv("OLLAMA_COMMAND", DEFAULT_OLLAMA_COMMAND)
    model = os.getenv("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)
    timeout = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", DEFAULT_OLLAMA_TIMEOUT_SECONDS))

    prompt = build_ollama_prompt(class_names)
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    try:
        result = subprocess.run(
            [command, "run", model],
            input=prompt,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            env=env,
            check=False,
        )  # nosec B603

        output = (result.stdout or "").strip()
        if result.returncode != 0 or not output:
            raise RuntimeError(
                f"Ollama retornou código {result.returncode}: {result.stderr.strip() if result.stderr else '<sem stderr>'}"
            )

        json_text = extract_json_object(output)
        if not json_text:
            raise ValueError("Não foi possível extrair JSON da resposta do Ollama")

        translated = json.loads(json_text)
        if not isinstance(translated, dict):
            raise ValueError("Resposta do Ollama não é um objeto JSON")

        normalized = [
            simplify_label(str(translated.get(original, original)))
            for original in class_names
        ]
        unique_labels = make_unique(normalized)
        return {original: unique_labels[i] for i, original in enumerate(class_names)}
    except Exception as exc:
        print(f"  ⚠️  Falha na tradução Ollama: {exc}")
        fallback = make_unique([simplify_label(name) for name in class_names])
        return {original: fallback[i] for i, original in enumerate(class_names)}


def get_model_classes(model_path):
    """Carrega o modelo e retorna o dicionário de classes."""
    try:
        model = YOLO(str(model_path))
        return model.names
    except Exception as e:
        print(f"Erro ao carregar modelo {model_path}: {e}")
        return None

def create_model_config(folder_path, model_name, classes):
    """Cria arquivo de configuração para o modelo."""
    config_path = folder_path / "config.yaml"
    classes_list = "\n".join(f'  - "{name}"' for name in classes.values())
    config_content = f"""# Configuração do modelo {model_name}
model:
  name: "{model_name}"
  path: "my_model.pt"
  version: "1.0"
  classes:
{classes_list}
  num_classes: {len(classes)}

training:
  source: "custom"
  epochs: 100
  imgsz: 640

metadata:
  description: "Modelo treinado para detectar {', '.join(classes.values())}"
  created_by: "auto-organizer"
"""

    with open(config_path, "w", encoding="utf-8") as f:
        f.write(config_content)

def create_classes_file(folder_path, classes):
    """Cria arquivo classes.txt com mapeamento ID -> nome."""
    classes_path = folder_path / "classes.txt"
    with open(classes_path, 'w', encoding='utf-8') as f:
        for idx, name in classes.items():
            f.write(f"{idx}: {name}\n")

def organize_models():
    """Organiza os modelos por classes."""
    project_root = Path(__file__).parent.parent
    models_dir = project_root / "models"

    if not models_dir.exists():
        print(f"Diretório models não encontrado: {models_dir}")
        return

    # Se houver uma pasta aninhada models/models devido a descompactação, mover seu conteúdo para fora
    nested_models_dir = models_dir / "models"
    if nested_models_dir.exists() and nested_models_dir.is_dir():
        print("📁 Pasta aninhada models/models encontrada. Movendo conteúdo para a pasta models principal...")
        for item in nested_models_dir.iterdir():
            target_path = models_dir / item.name
            if target_path.exists():
                print(f"  ⚠️  O item {item.name} já existe no diretório models principal.")
                suffix = 1
                while target_path.exists():
                    target_path = models_dir / f"{item.name}_temp_conf_{suffix}"
                    suffix += 1
            print(f"  Movendo {item.name} -> {target_path.name}")
            shutil.move(str(item), str(target_path))
        try:
            nested_models_dir.rmdir()
            print("  ✅ Pasta models/models vazia removida.")
        except Exception as e:
            print(f"  ⚠️  Não foi possível remover a pasta models/models: {e}")

    # Mapa para evitar conflitos de nomes
    class_folders = defaultdict(list)

    print("🔍 Escaneando modelos existentes...")

    # Primeiro, coletar informações de todos os modelos
    for folder in models_dir.iterdir():
        if not folder.is_dir() or folder.name.startswith('.'):
            continue

        print(f"\n📁 Processando pasta: {folder.name}")

        # Procurar arquivos .pt
        pt_files = list(folder.glob("*.pt"))
        if not pt_files:
            print(f"  ⚠️  Nenhum arquivo .pt encontrado em {folder.name}")
            continue

        # Usar o primeiro .pt encontrado
        model_file = pt_files[0]
        print(f"  🤖 Carregando modelo: {model_file.name}")

        classes = get_model_classes(model_file)
        if classes is None:
            continue

        original_names = list(classes.values())
        translated_names = translate_labels_with_ollama(original_names)
        classes_translated = {idx: translated_names[name] for idx, name in classes.items()}

        print(f"  📋 Classes encontradas: {original_names}")
        print(f"  📌 Classes traduzidas: {list(classes_translated.values())}")

        if len(classes_translated) == 1:
            class_name = list(classes_translated.values())[0]
            class_folders[class_name].append((folder, model_file, classes_translated))
        else:
            compound_name = "_".join(classes_translated.values())
            class_folders[compound_name].append((folder, model_file, classes_translated))

    # Agora reorganizar
    print("\n🔄 Reorganizando pastas...")

    for class_name, folders in class_folders.items():
        if len(folders) == 1:
            # Apenas uma pasta para esta classe
            old_folder, model_file, classes = folders[0]
            new_folder_name = normalize_folder_name(class_name)
            new_folder = models_dir / new_folder_name

            if old_folder != new_folder:
                print(f"  📂 Renomeando {old_folder.name} -> {new_folder_name}")
                if new_folder.exists():
                    print(f"  ⚠️  Pasta {new_folder_name} já existe, pulando...")
                    continue
                shutil.move(str(old_folder), str(new_folder))
            else:
                print(f"  ✅ Pasta {old_folder.name} já está correta")

            # Criar arquivos de configuração
            create_model_config(new_folder, new_folder_name, classes)
            create_classes_file(new_folder, classes)

        else:
            # Múltiplas pastas para a mesma classe - adicionar sufixos
            safe_name = normalize_folder_name(class_name)
            for i, (old_folder, model_file, classes) in enumerate(folders, 1):
                new_folder_name = f"{safe_name}_v{i}"
                new_folder = models_dir / new_folder_name

                if old_folder != new_folder:
                    print(f"  📂 Renomeando {old_folder.name} -> {new_folder_name}")
                    if new_folder.exists():
                        print(f"  ⚠️  Pasta {new_folder_name} já existe, pulando...")
                        continue
                    shutil.move(str(old_folder), str(new_folder))
                else:
                    print(f"  ✅ Pasta {old_folder.name} já está correta")

                # Criar arquivos de configuração
                create_model_config(new_folder, new_folder_name, classes)
                create_classes_file(new_folder, classes)

    print("\n✅ Organização concluída!")
    print("\n📊 Resumo das pastas organizadas:")
    for folder in sorted(models_dir.iterdir()):
        if folder.is_dir() and not folder.name.startswith('.'):
            config_file = folder / "config.yaml"
            if config_file.exists():
                print(f"  • {folder.name}/")

def main():
    print("🚀 Iniciando organização automática de modelos YOLO\n")
    organize_models()
    print("\n💡 Dica: Para usar um modelo específico na API, atualize MODEL_PATH em config/settings.py")

if __name__ == "__main__":
    main()