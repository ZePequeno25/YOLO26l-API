#!/usr/bin/env python3
"""
Script de Calibração Dinâmica de Limiares (MLOps).
Calcula os limiares de confiança otimizados (tau = max(0.40, min(0.95, 1.4*mu - 1.5*sigma)))
a partir do histórico no SQLite (prediction_metrics.db) e atualiza o dicionário 
CLASS_CONFIDENCE_THRESHOLDS em 'api-tcc/app/services/detection_service.py'.

Uso:
    python scripts/update_class_thresholds.py [--apply]
"""

import os
import re
import sqlite3
import json
import math
import sys
from collections import defaultdict

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

def get_db_connection():
    db_paths = [
        os.path.join("api-tcc", "data", "prediction_metrics.db"),
        os.path.join("data", "prediction_metrics.db"),
        "prediction_metrics.db"
    ]
    for path in db_paths:
        if os.path.exists(path):
            return sqlite3.connect(path), path
    return None, None

def get_service_file_path():
    service_paths = [
        os.path.join("api-tcc", "app", "services", "detection_service.py"),
        os.path.join("app", "services", "detection_service.py"),
    ]
    for path in service_paths:
        if os.path.exists(path):
            return path
    return None

def calculate_thresholds():
    conn, db_path = get_db_connection()
    if not conn:
        print("❌ Banco de dados SQLite 'prediction_metrics.db' não encontrado.")
        return {}

    cursor = conn.cursor()
    try:
        cursor.execute("SELECT box_details FROM prediction_metrics WHERE box_details IS NOT NULL AND box_details != ''")
        rows = cursor.fetchall()
    except Exception as e:
        print(f"❌ Erro ao consultar a tabela prediction_metrics: {e}")
        conn.close()
        return {}
    finally:
        conn.close()

    if not rows:
        print("⚠️ Nenhuma métrica com detalhes de caixas delimitadoras foi encontrada no banco.")
        return {}

    class_confidences = defaultdict(list)
    for (box_details_str,) in rows:
        try:
            boxes = json.loads(box_details_str)
            for box in boxes:
                cname = box.get("class_name") or box.get("class") or box.get("raw_class_name")
                conf = box.get("confidence") if box.get("confidence") is not None else box.get("conf")
                if cname and conf is not None:
                    class_confidences[cname].append(float(conf))
        except Exception:
            continue

    threshold_results = {}
    for name, confs in class_confidences.items():
        n = len(confs)
        if n == 0:
            continue
        avg = sum(confs) / n
        variance = sum((x - avg) ** 2 for x in confs) / n
        std_dev = math.sqrt(variance)

        # Fórmula estatística: tau = 1.4 * mu - 1.5 * sigma (travado entre 0.40 e 0.95)
        suggested = (avg - (1.5 * std_dev)) + (0.40 * avg)
        suggested = max(0.40, min(0.95, round(suggested, 2)))

        threshold_results[name] = {
            "count": n,
            "mean": round(avg, 4),
            "min": round(min(confs), 4),
            "max": round(max(confs), 4),
            "std_dev": round(std_dev, 4),
            "suggested_threshold": suggested
        }

    return threshold_results

def update_detection_service(threshold_results, apply_changes=True):
    service_path = get_service_file_path()
    if not service_path:
        print("⚠️ Arquivo 'detection_service.py' não foi localizado para atualização automática.")
        return False

    with open(service_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Mapeamento pré-calibrado para modelos ativos
    calibrated_overrides = {
        "Cadeira": 0.40,
        "cadeira": 0.40,
        "Extintor de Incêndio": 0.40,
        "extintor de incêndio": 0.40,
        "extintor e sua sinalização": 0.40,
        "Extintor CO2 e Sílica": 0.40,
        "extintor co2 e sílica": 0.40,
        "Extintor CO2 Babcock Davis": 0.40,
        "Extintor CO2 Walker MC-2A": 0.40,
        "Extintor Espuma Walker MF-60": 0.40,
        "Extintor Yamato YA-10NX": 0.40,
        "Placa de Sinalização": 0.45,
        "placa de sinalização": 0.45,
        "placa_sinalizacao": 0.45,
        "submodelo_extintor_componentes": 0.35,
        "submodelo_extintor_avarias": 0.40,
        "submodelo_extintor_detalhes": 0.30,
        "submodelo_pressao_normal": 0.40,
        "Trava / Lacre de Segurança": 0.30,
        "Safety Pin": 0.30,
        "Safety_Pin": 0.30,
        "Manômetro de Pressão": 0.30,
        "Gauge": 0.30,
        "Gauge Good": 0.30,
        "Gauge_Good": 0.30,
        "Mangueira / Difusor": 0.30,
        "Hose": 0.30,
        "Hose Pipe": 0.30,
        "Nozzle": 0.30,
        "Handle": 0.30,
        "Adesivo / Rótulo": 0.30,
        "Sticker": 0.30,
    }
    new_thresholds = dict(calibrated_overrides)

    # Atualiza com dados reais observados do banco de dados, preservando os tetos calibrados dos modelos de extintor/placa
    for name, stats in threshold_results.items():
        if name in calibrated_overrides:
            new_thresholds[name] = calibrated_overrides[name]
        else:
            new_thresholds[name] = stats["suggested_threshold"]

    # Montar bloco de código formatado
    lines = ["CLASS_CONFIDENCE_THRESHOLDS = {"]
    lines.append("    # --- MODELOS E CLASSES ATIVAS ---")
    for k, v in sorted(new_thresholds.items()):
        lines.append(f'    "{k}": {v:.2f},')
    lines.append("}")
    new_code_block = "\n".join(lines)

    # Substituição no arquivo via regex
    pattern = r"CLASS_CONFIDENCE_THRESHOLDS\s*=\s*\{[^}]*\}"
    if re.search(pattern, content):
        updated_content = re.sub(pattern, new_code_block, content)
        if apply_changes:
            with open(service_path, "w", encoding="utf-8") as f:
                f.write(updated_content)
            print(f"[OK] Arquivo '{service_path}' atualizado com sucesso!")
        else:
            print(f"[INFO] Modo simulação: Limiares prontos para aplicar em '{service_path}'.")
        return True
    else:
        print("[AVISO] Não foi possível encontrar a variável CLASS_CONFIDENCE_THRESHOLDS em detection_service.py")
        return False

def main():
    apply_flag = "--apply" in sys.argv or "-a" in sys.argv
    print("=" * 110)
    print(f"{'Calibração MLOps de Limiares por Modelo (CLASS_CONFIDENCE_THRESHOLDS)':^110}")
    print("=" * 110)

    results = calculate_thresholds()
    if results:
        header = f"{'Classe/Modelo':<32} {'Detections':>12} {'Média (mu)':>12} {'Desvio (sigma)':>15} {'Limiar Tau':>15}"
        print(header)
        print("-" * 110)
        for name, stats in sorted(results.items()):
            print(f"{name:<32} {stats['count']:>12} {stats['mean']:>12.4f} {stats['std_dev']:>15.4f} {stats['suggested_threshold']:>15.2f}")
        print("-" * 110)

        # Salvar relatório JSON em logs
        log_dir = os.path.join("api-tcc", "logs", "metrics")
        os.makedirs(log_dir, exist_ok=True)
        json_summary_path = os.path.join(log_dir, "class_thresholds_summary.json")
        with open(json_summary_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"Resumo salvo em JSON: '{json_summary_path}'")

    # Aplicar no backend
    update_detection_service(results, apply_changes=True)
    print("=" * 110)

if __name__ == "__main__":
    main()
