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

import os
import shutil
from pathlib import Path
from ultralytics import YOLO
from collections import defaultdict

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
    config_content = f"""# Configuração do modelo {model_name}
model:
  name: "{model_name}"
  path: "{model_name}.pt"
  version: "1.0"
  classes: {list(classes.values())}
  num_classes: {len(classes)}

training:
  source: "custom"
  epochs: 100
  imgsz: 640

metadata:
  description: "Modelo treinado para detectar {', '.join(classes.values())}"
  created_by: "auto-organizer"
"""

    with open(config_path, 'w', encoding='utf-8') as f:
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

        print(f"  📋 Classes encontradas: {classes}")

        # Para modelos com uma classe, usar o nome da classe como nome da pasta
        if len(classes) == 1:
            class_name = list(classes.values())[0]
            class_folders[class_name].append((folder, model_file, classes))
        else:
            # Para múltiplas classes, manter nome atual ou criar nome composto
            compound_name = "_".join(classes.values())
            class_folders[compound_name].append((folder, model_file, classes))

    # Agora reorganizar
    print("\n🔄 Reorganizando pastas...")

    for class_name, folders in class_folders.items():
        if len(folders) == 1:
            # Apenas uma pasta para esta classe
            old_folder, model_file, classes = folders[0]
            new_folder_name = class_name.lower().replace(" ", "_")
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
            for i, (old_folder, model_file, classes) in enumerate(folders, 1):
                new_folder_name = f"{class_name.lower().replace(' ', '_')}_v{i}"
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