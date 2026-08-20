import os
from pathlib import Path
from ultralytics import YOLO

def main():
    # Caminho para o diretório de modelos (um nível acima de api-tcc/models, ou relativo à raiz do projeto)
    current_dir = Path(__file__).resolve().parent
    models_dir = current_dir.parent / "models"
    
    if not models_dir.exists():
        print(f"❌ Diretório de modelos não encontrado em: {models_dir}")
        return

    print(f"🔍 Escaneando diretórios em: {models_dir}")
    
    # Listar todas as pastas dentro de models
    model_folders = [f for f in models_dir.iterdir() if f.is_dir() and not f.name.startswith('.')]
    
    success_count = 0
    skipped_count = 0
    fail_count = 0

    for idx, folder in enumerate(model_folders, 1):
        print(f"\n--------------------------------------------------")
        print(f"📦 [{idx}/{len(model_folders)}] Analisando pasta: {folder.name}")
        
        # Procurar arquivos .pt
        pt_files = list(folder.glob("*.pt"))
        if not pt_files:
            print(f"⚠️ Nenhum arquivo .pt encontrado em {folder.name}. Pulando...")
            skipped_count += 1
            continue
            
        # Pega o primeiro arquivo .pt encontrado
        pt_path = pt_files[0]
        
        # Nome da pasta OpenVINO gerada pelo exportador (substituindo .pt por _openvino_model)
        openvino_folder_name = pt_path.stem + "_openvino_model"
        openvino_path = folder / openvino_folder_name
        
        if openvino_path.exists():
            print(f"ℹ️ O modelo OpenVINO já existe em: {openvino_path.name}")
            print(f"   (Remova esta pasta se desejar forçar a re-exportação)")
            skipped_count += 1
            continue
            
        print(f"🔄 Carregando modelo PyTorch: {pt_path.name}")
        try:
            model = YOLO(str(pt_path))
            print(f"⚡ Exportando {pt_path.name} para OpenVINO (FP16)...")
            # Exporta para OpenVINO com precisão reduzida half=True (FP16)
            model.export(format="openvino", half=True, imgsz=640)
            print(f"✅ Sucesso ao exportar {folder.name}!")
            success_count += 1
        except Exception as e:
            print(f"❌ Erro ao exportar o modelo de {folder.name}: {e}")
            fail_count += 1

    print(f"\n==================================================")
    print(f"📊 Relatório de Exportação finalizado:")
    print(f"   - Sucessos: {success_count}")
    print(f"   - Pulados: {skipped_count}")
    print(f"   - Falhas: {fail_count}")
    print(f"==================================================")

if __name__ == "__main__":
    main()
