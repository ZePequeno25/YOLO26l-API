# 🏗️ Estrutura Organizada do Projeto TCC

## 📁 Estrutura de Pastas

```
Projeto TCC/
├── 📂 api-tcc/                    # Código da API FastAPI
│   ├── main.py                    # Ponto de entrada da API
│   ├── requirements.txt           # Dependências Python
│   ├── app/                       # Código da aplicação
│   │   ├── routes/                # Endpoints da API
│   │   ├── services/              # Lógica de negócio
│   │   ├── models/                # Modelos Pydantic
│   │   ├── core/                  # Configurações core
│   │   └── utils/                 # Utilitários
│   └── config/
│       └── settings.py            # Configurações da API
│
├── 📂 models/                     # 🤖 MODELOS TREINADOS
│   └── chair_detection_v1/        # Modelo de detecção de cadeiras v1
│       ├── my_model.pt            # Arquivo do modelo YOLO
│       ├── my_model_backup.pt     # Backup do modelo
│       ├── yolo11s_base.pt        # Modelo base YOLOv11
│       ├── config.yaml            # Configuração completa do modelo
│       └── classes.txt            # Mapeamento de classes
│
├── 📂 data/                       # 📊 DADOS DE TREINAMENTO
│   ├── content/                   # Dataset original
│   │   └── custom_data/
│   │       ├── data.yaml          # Configuração do dataset
│   │       ├── test/              # Dados de teste
│   │       ├── train/             # Dados de treinamento
│   │       └── valid/             # Dados de validação
│   ├── training_chair_v1/         # Resultados do treinamento v1
│   │   ├── train/
│   │   ├── my_model_openvino_model/
│   │   └── results.csv
│   ├── training_yolo_base/        # Treinamento base YOLO
│   └── runs/                      # Logs de detecção
│
└── 📂 scripts/                   # 🛠️ SCRIPTS DE TESTE E DEBUG
    ├── debug_class_names.py       # Debug de classes do modelo
    ├── test_detection_simple.py   # Teste básico da API
    ├── test_class_names_final.py  # Teste completo com diagnóstico
    ├── test_api_full.py           # Teste end-to-end da API
    └── [outros scripts...]        # Scripts diversos de teste
```

## 🎯 Como Usar

### 1. **Para Treinar um Novo Modelo**
```bash
# Coloque seus dados em data/training_[nome]/
# Treine o modelo
# Salve em models/[nome_do_modelo]/
# Atualize config.yaml e classes.txt
```

### 2. **Para Usar um Modelo Diferente**
```python
# Em config/settings.py
MODEL_PATH: str = str(Path("../../models/[nome_do_modelo]/model.pt"))
```

### 3. **Estrutura de um Modelo**
Cada pasta em `models/` deve ter:
- `model.pt` - Arquivo do modelo YOLO
- `config.yaml` - Configuração completa
- `classes.txt` - Mapeamento ID → nome da classe

## 📋 Exemplo de Modelo

### models/chair_detection_v1/
```
my_model.pt           # Modelo treinado
config.yaml          # Configuração
classes.txt          # Classes: 0="0", 1="Kursi", 2="chair", etc.
```

### config.yaml
```yaml
model:
  name: "chair_detection_v1"
  version: "1.0"
  type: "yolov8"
  path: "models/chair_detection_v1/my_model.pt"

classes:
  0: "0"
  1: "Kursi"
  2: "chair"
  3: "door"
  4: "teste_01 - v3 2024-01-16 12-29am"

metadata:
  trained_on: "2024-01-16"
  accuracy: "85%"
  dataset: "custom_data"
```

## 🚀 Benefícios da Organização

✅ **Separação clara**: código ↔ dados ↔ modelos
✅ **Versionamento**: múltiplas versões do mesmo modelo
✅ **Reutilização**: modelos podem ser compartilhados
✅ **Manutenibilidade**: fácil encontrar e atualizar
✅ **Escalabilidade**: adicionar novos modelos é simples

## 📝 Próximos Passos

1. **Testar API** com novo caminho do modelo
2. **Adicionar mais modelos** conforme necessário
3. **Documentar** cada modelo com seus resultados
4. **Versionar** modelos por data/accuracy