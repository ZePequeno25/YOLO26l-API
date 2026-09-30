import sqlite3, json, math, sys
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')

db_path = "api-tcc/data/prediction_metrics.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT requested_model, detected_classes, requested_class_found, confidence_avg, box_details FROM prediction_metrics")
rows = cursor.fetchall()

# Active models categories
ACTIVE_KEYWORDS = ["cadeira", "extintor", "submodelo"]

active_model_groups = {
    "Modo Multimodelo (model=all / Ativos)": {"reqs": 0, "hits": 0, "confs": []},
    "Cadeiras e Ambientes de Escritório": {"reqs": 0, "hits": 0, "confs": []},
    "Extintores e Sobcamada de Segurança": {"reqs": 0, "hits": 0, "confs": []},
}

active_box_confs = defaultdict(list)

for req_model, det_classes, req_found, conf_avg, box_str in rows:
    rm_lower = (req_model or "").lower().strip()
    
    # Check if this request is for an active model
    is_cadeira = "cadeira" in rm_lower
    is_extintor = ("extintor" in rm_lower) or ("submodelo" in rm_lower)
    is_multimodelo = (rm_lower in ["all", "multimodelo"]) or ("cadeira" in rm_lower and "extintor" in rm_lower)
    
    boxes = []
    if box_str:
        try:
            boxes = json.loads(box_str)
        except Exception:
            pass
            
    is_hit = 1 if (len(boxes) > 0 or req_found == 1) else 0
    c_avg = float(conf_avg) if conf_avg and conf_avg > 0 else None
    
    if is_multimodelo:
        active_model_groups["Modo Multimodelo (model=all / Ativos)"]["reqs"] += 1
        active_model_groups["Modo Multimodelo (model=all / Ativos)"]["hits"] += is_hit
        if c_avg: active_model_groups["Modo Multimodelo (model=all / Ativos)"]["confs"].append(c_avg)
    elif is_cadeira:
        active_model_groups["Cadeiras e Ambientes de Escritório"]["reqs"] += 1
        active_model_groups["Cadeiras e Ambientes de Escritório"]["hits"] += is_hit
        if c_avg: active_model_groups["Cadeiras e Ambientes de Escritório"]["confs"].append(c_avg)
    elif is_extintor:
        active_model_groups["Extintores e Sobcamada de Segurança"]["reqs"] += 1
        active_model_groups["Extintores e Sobcamada de Segurança"]["hits"] += is_hit
        if c_avg: active_model_groups["Extintores e Sobcamada de Segurança"]["confs"].append(c_avg)
        
    # Extract boxes for active classes
    for b in boxes:
        cname = b.get("class_name") or b.get("class") or b.get("raw_class_name")
        conf = b.get("confidence") if b.get("confidence") is not None else b.get("conf")
        if cname and conf is not None:
            c_lower = cname.lower()
            if any(k in c_lower for k in ["cadeira", "extintor", "safety", "lacre", "manômetro", "gauge", "mangueira", "hose", "adesivo", "sticker", "trava", "sinalização", "placa", "handle", "nozzle"]):
                active_box_confs[cname].append(float(conf))

print("="*95)
print(f"{'TABELA 1: TELEMETRIA OPERACIONAL DOS MODELOS ATIVOS':^95}")
print("="*95)
print(f"{'Modelo / Modo de Inferência em Produção':<42} {'N':>8} {'VP':>8} {'Taxa Acerto':>13} {'Conf. (μ)':>12}")
print("-" * 95)

total_reqs = 0
total_vp = 0
all_confs = []

for name, data in active_model_groups.items():
    n = data["reqs"]
    vp = data["hits"]
    acc = (vp / n * 100) if n > 0 else 0
    c_m = (sum(data["confs"]) / len(data["confs"]) * 100) if data["confs"] else 0
    total_reqs += n
    total_vp += vp
    all_confs.extend(data["confs"])
    print(f"{name:<42} {n:>8} {vp:>8} {acc:>12.2f}% {c_m:>11.2f}%")

tot_acc = (total_vp / total_reqs * 100) if total_reqs > 0 else 0
tot_conf = (sum(all_confs) / len(all_confs) * 100) if all_confs else 0
print("-" * 95)
print(f"{'Consolidado dos Modelos Ativos':<42} {total_reqs:>8} {total_vp:>8} {tot_acc:>12.2f}% {tot_conf:>11.2f}%")
print("="*95)

print("\n" + "="*95)
print(f"{'TABELA 2: ESTATÍSTICAS DE CONFIANÇA E LIMIARES DAS CLASSES ATIVAS':^95}")
print("="*95)
print(f"{'Classe / Categoria do Objeto (Modelos Ativos)':<45} {'Detecções (n)':>12} {'Média (μ)':>10} {'Desvio (σ)':>10} {'Limiar (τ)':>12}")
print("-" * 95)

total_boxes = 0
for cname, confs in sorted(active_box_confs.items(), key=lambda x: len(x[1]), reverse=True):
    n = len(confs)
    total_boxes += n
    avg = sum(confs) / n
    var = sum((x - avg)**2 for x in confs) / n
    std = math.sqrt(var)
    tau = max(0.40, min(0.95, round(avg - 1.5 * std + 0.40 * avg, 2)))
    print(f"{cname:<45} {n:>12} {avg:>10.4f} {std:>10.4f} {tau:>12.2f}")

print(f"\nTotal de caixas delimitadoras ativas analisadas: {total_boxes}")
conn.close()
