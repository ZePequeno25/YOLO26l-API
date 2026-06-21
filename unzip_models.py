import zipfile
import os

zip_path = r"c:\Users\aborr\Projeto TCC\YOLO26l-API\models\trained_models.zip"
extract_path = r"c:\Users\aborr\Projeto TCC\YOLO26l-API\models"

print(f"Unzipping {zip_path} to {extract_path}...")
if not os.path.exists(zip_path):
    print("Error: Zip file not found!")
    exit(1)

with zipfile.ZipFile(zip_path, 'r') as zip_ref:
    zip_ref.extractall(extract_path)

print("Unzip completed successfully!")
