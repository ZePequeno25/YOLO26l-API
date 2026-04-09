# Estrutura de Múltiplos Modelos YOLO

## Visão Geral
O sistema agora suporta múltiplos modelos YOLO organizados por classes detectadas. Cada modelo fica em sua própria pasta nomeada pela classe principal.

## Estrutura de Pastas
```
models/
├── chair/                    # Modelo para detectar cadeiras
│   ├── my_model.pt          # Arquivo do modelo
│   ├── config.yaml          # Configuração do modelo
│   └── classes.txt          # Mapeamento ID -> nome das classes
├── table/                   # Exemplo: modelo para mesas
│   ├── table_detector.pt
│   ├── config.yaml
│   └── classes.txt
└── ...
```

## Scripts Disponíveis

### 1. `inspect_model_classes.py`
Inspeciona as classes de um modelo específico.
```bash
python scripts/inspect_model_classes.py models/chair/my_model.pt
```

### 2. `organize_models.py`
Organiza automaticamente os modelos existentes:
- Varre todas as pastas em `models/`
- Carrega cada modelo .pt
- Identifica as classes detectadas
- Renomeia pastas para o nome da classe principal
- Cria arquivos `config.yaml` e `classes.txt` padronizados
```bash
python scripts/organize_models.py
```

### 3. `test_new_model.py`
Testa um modelo específico com uma imagem de exemplo.
```bash
python scripts/test_new_model.py
```

## API Endpoints

### Listar Modelos Disponíveis
```
GET /detection/models
```
Resposta:
```json
{
  "success": true,
  "models": ["chair", "table", "car"],
  "default_model": "chair"
}
```

### Detectar com Modelo Específico
```
POST /detection/analyze
```
Parâmetros (multipart/form-data):
- `file`: Arquivo de imagem ou vídeo
- `id_token`: Token de autenticação
- `model`: Nome do modelo (opcional, padrão: "chair")

## Como Adicionar um Novo Modelo

1. **Treine seu modelo YOLO** e salve como `.pt`

2. **Crie uma pasta** em `models/` com o nome da classe principal:
   ```
   models/sua_classe/
   └── seu_modelo.pt
   ```

3. **Execute o script de organização**:
   ```bash
   python scripts/organize_models.py
   ```
   Ele irá:
   - Identificar as classes do modelo
   - Renomear a pasta se necessário
   - Criar `config.yaml` e `classes.txt`

4. **Teste o modelo**:
   ```bash
   python scripts/test_new_model.py  # Modifique o script para apontar para seu modelo
   ```

5. **Use na API**:
   - Liste modelos: `GET /detection/models`
   - Detecte: `POST /detection/analyze` com `model=sua_classe`

## Exemplo de Uso na API

```python
import requests

# Listar modelos
response = requests.get("http://localhost:8000/detection/models")
print(response.json())
# {"success": true, "models": ["chair", "table"], "default_model": "chair"}

# Detectar com modelo específico
files = {"file": open("imagem.jpg", "rb")}
data = {"id_token": "seu_token", "model": "table"}
response = requests.post("http://localhost:8000/detection/analyze", files=files, data=data)
```

## Notas Técnicas

- **Cache de Modelos**: Os modelos são carregados uma vez e mantidos em cache para performance
- **Fallback**: Se o modelo especificado não existir, usa o modelo padrão ("chair")
- **Vídeos**: Suportam processamento com tracking e fallback frame-a-frame
- **Organização Automática**: O script `organize_models.py` trata conflitos de nomes adicionando sufixos (_v2, _v3, etc.)