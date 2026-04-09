# API de Detecção com Retorno de Arquivos Analisados

## Visão Geral
A API agora retorna as imagens e vídeos analisados com as detecções desenhadas (bounding boxes, classes e confiança).

## Estrutura de Diretórios
```
projeto/
├── analyzed_outputs/           # Pasta automática para arquivos analisados
└── downloaded_outputs/         # Pasta para downloads de testes
```

## Endpoints Disponíveis

### 1. POST `/detection/analyze` (Produção)
**Análise com autenticação obrigatória**

```bash
curl -X POST "http://localhost:8000/detection/analyze" \
  -F "file=@imagem.jpg" \
  -F "id_token=seu_token_firebase" \
  -F "model=chair"
```

**Parâmetros:**
- `file` (obrigatório): Arquivo de imagem ou vídeo
- `id_token` (obrigatório): Token de autenticação Firebase
- `model` (opcional): Nome do modelo a usar (padrão: "chair")

**Resposta:**
```json
{
  "success": true,
  "message": "1 cadeira(s) detectada(s)",
  "class_counts": {"chair": 1},
  "num_frames_processed": 1,
  "detected_chairs": 1,
  "frames_with_detections": 1,
  "analyzed_file": "/caminho/completo/analyzed_image_20260325_235149.jpg"
}
```

### 2. POST `/detection/analyze-test` (Testes)
**Análise sem autenticação para testes**

```bash
curl -X POST "http://localhost:8000/detection/analyze-test" \
  -F "file=@imagem.jpg" \
  -F "model=chair"
```

### 3. GET `/detection/download/{filename}`
**Fazer download de um arquivo analisado**

```bash
curl -X GET "http://localhost:8000/detection/download/analyzed_image_20260325_235149.jpg" \
  -o imagem_com_deteccoes.jpg
```

**Parâmetros:**
- `filename` (obrigatório): Nome do arquivo do caminho anterior
- `id_token` (opcional): Token de autenticação (para controle de acesso)

### 4. GET `/detection/models`
**Listar modelos disponíveis**

```bash
curl -X GET "http://localhost:8000/detection/models"
```

**Resposta:**
```json
{
  "success": true,
  "models": ["chair", "table", "person"],
  "default_model": "chair"
}
```

## Formato dos Arquivos Analisados

### Imagens
- **Formato:** JPG preservado do original
- **Conteúdo:** Retângulos verdes com labels
- **Exemplo:** `analyzed_foto_20260325_235149.jpg`

### Vídeos
- **Formato:** MP4 (codec mp4v)
- **Conteúdo:** Detecções desenhadas em cada frame
- **Exemplo:** `analyzed_video_20260325_235149.mp4`

### Labels nos Arquivos
Cada detecção mostra:
- **Nome da classe** (ex: "chair", "table")
- **Confiança** em percentual (ex: "96.13%")
- **Bounding box** em verde (#00FF00)

## Exemplo de Uso em Python

```python
import requests
from pathlib import Path

# 1. Listar modelos disponíveis
response = requests.get("http://localhost:8000/detection/models")
models = response.json()['models']
print(f"Modelos disponíveis: {models}")

# 2. Fazer análise
with open("foto.jpg", "rb") as f:
    files = {"file": f}
    data = {"model": "chair"}  # modelo específico
    
    response = requests.post(
        "http://localhost:8000/detection/analyze-test",
        files=files,
        data=data
    )

result = response.json()
print(f"Detecções: {result['class_counts']}")
analyzed_file = result['analyzed_file']
print(f"Arquivo analisado: {Path(analyzed_file).name}")

# 3. Fazer download do arquivo analisado
filename = Path(analyzed_file).name
download_response = requests.get(
    f"http://localhost:8000/detection/download/{filename}"
)

with open("resultado.jpg", "wb") as f:
    f.write(download_response.content)
    print("Arquivo salvo localmente!")
```

## Exemplo de Uso com cURL

### Analisar e fazer download em um comando

```bash
# Fazer upload e obter resultado
RESULTADO=$(curl -s -X POST "http://localhost:8000/detection/analyze-test" \
  -F "file=@test.jpg" \
  -F "model=chair")

# Extrair nome do arquivo analisado
ARQUIVO=$(echo $RESULTADO | grep -o '"analyzed_file":"[^"]*' | cut -d'"' -f4 | rev | cut -d'/' -f1 | rev)

# Fazer download
curl -X GET "http://localhost:8000/detection/download/$ARQUIVO" \
  -o resultado.jpg

echo "Análise: $RESULTADO"
echo "Download: $ARQUIVO"
```

## Estrutura de Resposta Detalhada

```python
{
    "success": bool,                    # Sempre True se sucesso
    "message": str,                     # Descrição legível
    "class_counts": {str: int},         # {"chair": 1, "table": 2}
    "num_frames_processed": int,        # Total de frames (1 para imagem)
    "detected_chairs": int,             # Quantidade de cadeiras (legado)
    "frames_with_detections": int,      # Frames com pelo menos 1 detecção
    "analyzed_file": str                # Caminho completo do arquivo (NOVO)
}
```

## Armazenamento

- **Diretório:** `C:\Users\aborr\Projeto TCC\analyzed_outputs\`
- **Nomeação:** `analyzed_{nome_original}_{timestamp}.{extensão}`
- **Limpeza:** Arquivos permanecem no servidor (integrar limpeza se necessário)
- **Segurança:** Path traversal validation active in download endpoint

## Performance

| Tipo | Tempo Típico | Tamanho Máximo |
|------|--------------|----------------|
| Imagem JPG | 200-500ms | 500 MB |
| Imagem PNG | 300-600ms | 500 MB |
| Vídeo (30fps) | 2-10s/min | 500 MB |
| Vídeo (60fps) | 4-15s/min | 500 MB |

## Configuração

### Adicionar Limpeza Automática (opcional)

```python
# Em config/settings.py
ANALYZED_FILES_CLEANUP_DAYS: int = 7  # Limpar arquivos com mais de 7 dias

# Em app/services/detection_service.py
import datetime

def cleanup_old_files(days=7):
    cutoff = datetime.datetime.now() - datetime.timedelta(days=days)
    for file_path in self.output_dir.glob("*.jpg") + self.output_dir.glob("*.mp4"):
        if datetime.datetime.fromtimestamp(file_path.stat().st_mtime) < cutoff:
            file_path.unlink()
```

## Tratamento de Erros

| Erro | Causa | Solução |
|------|-------|---------|
| 404 | Arquivo não encontrado | Verifique se o download foi logo após análise |
| 400 | Nome inválido | Use o nome exato retornado pela análise |
| 500 | Erro na análise | Verifique logs da API |
| 413 | Arquivo muito grande | Máximo 500 MB |

## Notas Técnicas

- **Codec de Vídeo:** MP4V (compatível com maioria dos players)
- **Taxa de Quadros:** Preservada do vídeo original
- **Resolução:** Mantida do arquivo original
- **Quality:** Máxima para imagens (100), padrão para vídeos
- **Thread-safe:** Sim, nomes com timestamp garantem unicidade