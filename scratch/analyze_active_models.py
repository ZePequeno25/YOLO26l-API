import sqlite3
import json
import os
import math
import sys
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')

db_path = "api-tcc/data/prediction_metrics.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT id, timestamp, filename, requested_model, detected_classes, requested_class_found, confidence_avg, box_details FROM prediction_metrics")
rows = cursor.fetchall()

total_requests = len(rows)
print(f"Total geral de requisições no banco: {total_requests}")

DISABLED_MODELS = {
    "alimentos e utensílios", "alimentos_e_utensilios",
    "frascos e garrafas", "frascos_e_garrafas",
    "queda e epi", "queda_e_epis",
    "caixas e pessoas", "conteiner_e_canteiro",
    "caixas e pacotes", "caixas_e_pacotes",
    "cones de segurança", "cone_seguranca",
    "óculos de proteção", "oculos_protecao",
    "vagas de estacionamento", "vagas_estacionamento",
    "escavadeira e carros", "escavadeira",
    "etiquetas e caixas", "etiquetas_e_caixas",
    "máquinas e obras", "caminhao_betoneira",
    "ônibus e caminhões", "veiculos_pesados",
    "coletes de segurança", "colete_seguranca",
    "máquinas pesadas", "maquinas_pesadas",
    "carros variados", "carro",
    "sinal de parque", "sínal de parque", "sinal_estacionamento",
    "item caixa", "item_caixa",
    "caminhão", "caminho", "caminhao",
    "pessoa", "placa de sinalização", "placa_sinalizacao",
    "chuveiro de emergência", "chuveiro_emergencia"
}

model_stats = defaultdict(lambda: {"reqs": 0, "hits": 0, "confs": []})
class_confidences = defaultdict(list)

for row in rows:
    r_id, ts, fname, req_model, det_classes, req_found, conf_avg, box_str = row
    
    boxes = []
    if box_str:
        try:
            boxes = json.loads(box_str)
        except Exception:
            boxes = []
            
    num_boxes = len(boxes)
    is_hit = 1 if (num_boxes > 0 or req_found == 1) else 0
    
    model_key = req_model if req_model else "Desconhecido"
    model_stats[model_key]["reqs"] += 1
    model_stats[model_key]["hits"] += is_hit
    if conf_avg is not None and conf_avg > 0:
        model_stats[model_key]["confs"].append(float(conf_avg))
        
    for b in boxes:
        cname = b.get("class_name") or b.get("class") or b.get("raw_class_name")
        conf = b.get("confidence") if b.get("confidence") is not None else b.get("conf")
        if cname and conf is not None:
            c_val = float(conf)
            class_confidences[cname].append(c_val)

print("\n" + "="*95)
print(f"{'MÉTRICAS DA TELEMETRIA POR MODELO (PRODUÇÃO REAL)':^95}")
print("="*95)
print(f"{'Modelo / Modo de Inferência':<40} {'Reqs (N)':>10} {'Acertos (VP)':>14} {'Taxa Acerto':>13} {'Conf. Média':>12}")
print("-" * 95)

total_active_n = 0
total_active_vp = 0
active_all_confs = []

for m_name, st in sorted(model_stats.items(), key=lambda x: x[1]["reqs"], reverse=True):
    n = st["reqs"]
    vp = st["hits"]
    acc = (vp / n * 100) if n > 0 else 0
    c_avg = (sum(st["confs"]) / len(st["confs"]) * 100) if st["confs"] else 0
    print(f"{m_name:<40} {n:>10} {vp:>14} {acc:>12.2f}% {c_avg:>11.2f}%")

print("\n" + "="*95)
print(f"{'ESTATÍSTICAS E LIMIARES CALIBRADOS POR CLASSE / MODELO (ALL & ACTIVE)':^95}")
print("="*95)
print(f"{'Classe / Modelo':<38} {'Detecções (n)':>14} {'Média (μ)':>10} {'Desvio (σ)':>10} {'Limiar Sugerido (τ)':>18}")
print("-" * 95)

for cname, confs in sorted(class_confidences.items(), key=lambda x: len(x[1]), reverse=True):
    n = len(confs)
    avg = sum(confs) / n
    var = sum((x - avg)**2 for x in confs) / n
    std = math.sqrt(var)
    tau = max(0.40, min(0.95, round(avg - 1.5 * std + 0.40 * avg, 2)))
    print(f"{cname:<38} {n:>14} {avg:>10.4f} {std:>10.4f} {tau:>18.2f}")

conn.close()
