# Standardize OpenVINO filenames in models directory
$modelsDir = "c:\Users\aborr\Projeto TCC\YOLO26l-API\models"

Get-ChildItem -Path $modelsDir -Recurse -Directory -Filter "*_openvino_model" | ForEach-Object {
    $dir = $_.FullName
    $xmlFiles = Get-ChildItem -Path $dir -Filter "*.xml"
    if ($xmlFiles.Count -gt 0) {
        $srcXml = $xmlFiles[0].FullName
        Copy-Item $srcXml (Join-Path $dir "openvino_model.xml") -Force
        Copy-Item $srcXml (Join-Path $dir "my_model.xml") -Force
    }
    $binFiles = Get-ChildItem -Path $dir -Filter "*.bin"
    if ($binFiles.Count -gt 0) {
        $srcBin = $binFiles[0].FullName
        Copy-Item $srcBin (Join-Path $dir "openvino_model.bin") -Force
        Copy-Item $srcBin (Join-Path $dir "my_model.bin") -Force
    }
    Write-Host "✅ OpenVINO padronizado:" $_.Parent.Name
}
