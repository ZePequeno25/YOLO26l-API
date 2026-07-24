#!/usr/bin/env python3
import os
from pathlib import Path
from ultralytics import YOLO

def main():
    # Ajustar diretório de trabalho para a pasta do script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # Caminho base dos modelos (YOLO26l-API/models)
    root_dir = Path(script_dir).parent
    models_dir = root_dir / "models"
    
    models_to_export = ["cadeira", "extinguidor"]
    
    print("🚀 [Exporter] Iniciando conversão de modelos PyTorch (.pt) para OpenVINO...")
    print(f"📁 [Exporter] Pasta de modelos: {models_dir}\n")
    
    for name in models_to_export:
        pt_path = models_dir / name / "my_model.pt"
        if not pt_path.exists():
            print(f"❌ [Exporter] Arquivo .pt não encontrado para '{name}' em: {pt_path}")
            continue
            
        print("-" * 60)
        print(f"📦 [Exporter] Carregando e compilando '{name}' ({pt_path.name})...")
        try:
            # Carregar o modelo PyTorch
            model = YOLO(str(pt_path))
            
            # Exportar para OpenVINO
            # Isso criará uma pasta chamada 'my_model_openvino_model' no mesmo diretório do arquivo .pt
            print(f"⚡ [Exporter] Executando exportação OpenVINO (isso pode levar de 1 a 2 minutos)...")
            output_dir = model.export(format="openvino")
            
            print(f"✅ [Exporter] Sucesso! Modelo '{name}' exportado para: {output_dir}")
        except Exception as e:
            print(f"❌ [Exporter] Erro ao exportar '{name}': {e}")
            
    print("=" * 60)
    print("🏁 [Exporter] Processo concluído! Reinicie a API para carregar os novos formatos.")

if __name__ == "__main__":
    main()
