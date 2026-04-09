from ultralytics import YOLO
import cv2
import openvino as ov

# Carrega modelo (pode ser .pt ou .onnx)
model = YOLO('C:\\Users\\aborr\\Projeto TCC\\my_model-85%\\my_model.pt')

# Força usar OpenVINO como backend (otimizado para Intel Arc)
model.export(format='openvino')  # gera pasta _openvino_model
model = YOLO('C:\\Users\\aborr\\Projeto TCC\\my_model-85%\\my_model.pt')

# GPU Intel Arc via OpenCL
model.predict('C:\\Users\\aborr\\Downloads\\video cadeiras\\WhatsApp Video 2026-03-21 at 16.11.50.mp4', device='cpu')  # OpenVINO usa OpenCL automático