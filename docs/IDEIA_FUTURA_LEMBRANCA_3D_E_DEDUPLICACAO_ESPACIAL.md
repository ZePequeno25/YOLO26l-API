# 🧠 Ideia Futura: Lembrança 3D & Deduplicação Espacial Georreferenciada

Este documento registra a concepção arquitetural da **Lembrança 3D (Spatial Memory Indexing)** e **Deduplicação Georreferenciada de Objetos**, uma funcionalidade avançada projetada para evitar contagens duplicadas do mesmo objeto em auditorias físicas de canteiros de obras.

---

## 🎯 O Problema que a Lembrança 3D Resolve

Em inspeções em tempo real (vídeo ou sequência de fotos em movimento), quando um supervisor caminha ao redor de um extintor ou máquina pesada, a visão computacional tradicional detecta o objeto em múltiplos frames (ex: 30 vezes em 10 segundos). 

Sem inteligência de espaço, o sistema registraria 30 extintores no banco de dados. A **Lembrança 3D** utiliza a fusão dos sensores do smartphone (GPS + IMU Giroscópio/Bússola) para entender que todas essas detecções pertencem ao **mesmo objeto físico no espaço 3D do mundo real**.

---

## 📐 Como Funciona o Algoritmo de Projeção 3D

```mermaid
graph TD
    A[Dispositivo Android] -->|1. Transmite Foto + GPS + Giroscópio/Bússola| B[Backend FastAPI]
    B -->|2. YOLO + OpenVINO| C[Bounding Box 2D na Imagem: x, y, w, h]
    
    subgraph Engine de Lembrança 3D (Spatial Memory)
        B -->|3. Leitura IMU/GPS| D[Vetor de Câmera: Lat, Long, Alt, Pitch, Roll, Yaw]
        C & D -->|4. Projeção de Raios 3D| E[Cálculo da Coordenada Global: P_objeto = X, Y, Z]
        E -->|5. Distância Haversine 3D com a Memória| F{Distância < 1.5 metros?}
        F -->|Sim e mesma classe| G[DEDUPLICAÇÃO: É o mesmo objeto já auditado!]
        F -->|Não| H[NOVA INSTÂNCIA: Registra novo objeto no mapa 3D da obra]
    end
```

---

## 🛰️ Metadados Enviados pelo Aplicativo Android

No payload Multipart da requisição POST `/detection/analyze`, o Android anexa um cabeçalho JSON `X-Spatial-Telemetry`:

```json
{
  "gps": {
    "latitude": -23.550520,
    "longitude": -46.633308,
    "altitude": 760.5,
    "accuracy": 1.2
  },
  "orientation_imu": {
    "pitch": -12.4,
    "roll": 0.5,
    "yaw_azimuth": 185.2
  },
  "camera_params": {
    "fov_horizontal": 68.0,
    "estimated_depth_meters": 2.5
  }
}
```

---

## 🧮 Fórmula da Projeção 3D no Backend

A posição tridimensional do objeto no mundo real ($P_{\text{objeto}}$) é calculada por trigonometria esférica e vetorial:

$$X_{\text{objeto}} = X_{\text{camera}} + D \cdot \sin(\text{Yaw}) \cdot \cos(\text{Pitch})$$
$$Y_{\text{objeto}} = Y_{\text{camera}} + D \cdot \cos(\text{Yaw}) \cdot \cos(\text{Pitch})$$
$$Z_{\text{objeto}} = Z_{\text{camera}} + D \cdot \sin(\text{Pitch})$$

Onde $D$ é a distância estimada entre a câmera do celular e o objeto detectado no frame.

---

## 💡 Aplicações Futuras Impressionantes

1. **Planta Baixa 3D Interativa da Obra (BIM / GIS):** Plotagem automática de todos os extintores, cones, EPIs e máquinas em um mapa 3D da construção civil (usando WebGL / Three.js no painel web).
2. **Histórico de Movimentação:** Identificar se um extintor foi movido de lugar entre a auditoria da manhã e a da tarde.
3. **Auditoria com Latência Zero:** Se a câmera passar por um extintor já auditado há 5 segundos, a API reutiliza instantaneamente a análise de sobcamada salva na **Lembrança 3D**, sem precisar reprocessar o Ollama.
