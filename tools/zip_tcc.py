import zipfile
from pathlib import Path

def zip_latex():
    root = Path(__file__).resolve().parent.parent
    latex_dir = root / "docs" / "TCC_LATEX"
    output_zip = root / "docs" / "TCC_LATEX_Pronto.zip"
    
    if not latex_dir.exists():
        print(f"❌ Diretório não encontrado: {latex_dir}")
        return

    with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in latex_dir.rglob("*"):
            if file.is_file() and not file.name.endswith(".zip"):
                rel_path = file.relative_to(latex_dir)
                zf.write(file, arcname=str(rel_path))
                print(f"  + Adicionado: {rel_path}")

    print(f"\n🎉 Arquivo ZIP gerado com sucesso em: {output_zip}")

if __name__ == "__main__":
    zip_latex()
