import shutil
from pathlib import Path

def standardize_openvino_models():
    root = Path(__file__).resolve().parent.parent
    models_dir = root / "models"
    
    if not models_dir.exists():
        print(f"❌ Diretório de modelos não encontrado: {models_dir}")
        return

    count = 0
    for openvino_dir in models_dir.rglob("*_openvino_model"):
        if not openvino_dir.is_dir():
            continue
            
        xml_files = list(openvino_dir.glob("*.xml"))
        bin_files = list(openvino_dir.glob("*.bin"))
        
        if not xml_files or not bin_files:
            continue

        base_xml = xml_files[0]
        base_bin = bin_files[0]

        # Garantir existências dos nomes padrão: openvino_model.xml e my_model.xml
        target_xmls = [openvino_dir / "openvino_model.xml", openvino_dir / "my_model.xml"]
        target_bins = [openvino_dir / "openvino_model.bin", openvino_dir / "my_model.bin"]

        for t_xml in target_xmls:
            if not t_xml.exists() or t_xml.resolve() != base_xml.resolve():
                shutil.copy2(base_xml, t_xml)

        for t_bin in target_bins:
            if not t_bin.exists() or t_bin.resolve() != base_bin.resolve():
                shutil.copy2(base_bin, t_bin)

        count += 1
        print(f"✅ Padronizado OpenVINO IR: {openvino_dir.parent.name}/{openvino_dir.name}")

    print(f"\n🎉 Total de {count} modelos padronizados com suporte OpenVINO IR nativo!")

if __name__ == "__main__":
    standardize_openvino_models()
