#!/usr/bin/env python3
"""
Script para agregar os dados de predição do banco de dados e calcular
a média e estatísticas de confiança para cada classe/modelo detectado,
atualizando automaticamente o dicionário CLASS_CONFIDENCE_THRESHOLDS no backend.

Uso:
    python scripts/calculate_box_confidence_averages.py
"""
import os
import re
import sqlite3
import json
import math
import sys
from collections import defaultdict

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

def main():
    conn, db_path = get_db_connection()
    if not conn:
        print("❌ Banco de dados SQLite 'prediction_metrics.db' não encontrado.")
        return

    cursor = conn.cursor()
    try:
        cursor.execute("SELECT box_details FROM prediction_metrics WHERE box_details IS NOT NULL AND box_details != ''")
        rows = cursor.fetchall()
    except Exception as e:
        print(f"❌ Erro ao consultar a tabela: {e}")
        return
    finally:
        conn.close()

    if not rows:
        print("⚠️ Nenhuma métrica com detalhes de caixas delimitadoras encontrada no banco ainda.")
        return

    # Agregadores
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

    if not class_confidences:
        print("⚠️ Detalhes de caixas encontrados, mas nenhuma classe ou confiança válida pôde ser extraída.")
        return

    print("=" * 110)
    print(f"{'Estatísticas de Confiança de Caixas Delimitadoras por Modelo':^110}")
    print("=" * 110)
    header = f"{'Classe/Modelo':<32} {'Detections':>12} {'Média':>10} {'Mínimo':>10} {'Máximo':>10} {'Desvio Padrão':>15} {'Limiar Sugerido':>17}"
    print(header)
    print("-" * 110)

    calculated_thresholds = {
        "Cadeira": 0.40,
        "cadeira": 0.40,
        "Extintor de Incêndio": 0.40,
        "extintor de incêndio": 0.40,
        "extintor e sua sinalização": 0.40,
        "Extintor CO2 e Sílica": 0.48,
        "extintor co2 e sílica": 0.48,
        "Extintor CO2 Babcock Davis": 0.46,
        "Extintor CO2 Walker MC-2A": 0.40,
        "Extintor Espuma Walker MF-60": 0.40,
        "Extintor Yamato YA-10NX": 0.40,
        "submodelo_extintor_componentes": 0.40,
        "submodelo_extintor_avarias": 0.40,
        "submodelo_extintor_detalhes": 0.40,
        "submodelo_pressao_normal": 0.40,
        "Trava / Lacre de Segurança": 0.40,
        "Safety_Pin": 0.40,
        "Manômetro de Pressão": 0.40,
        "Gauge_Good": 0.40,
        "Mangueira / Difusor": 0.40,
        "Hose": 0.40,
        "Adesivo / Rótulo": 0.40,
        "Sticker": 0.40,
    }

    for name, confs in sorted(class_confidences.items()):
        n = len(confs)
        avg = sum(confs) / n
        min_c = min(confs)
        max_c = max(confs)
        
        # Desvio padrão
        variance = sum((x - avg) ** 2 for x in confs) / n
        std_dev = math.sqrt(variance)
        
        # Sugerir limiar (Média - 1.5 * Desvio Padrão + 0.40 * Média), travado entre 0.40 e 0.95
        suggested = (avg - (1.5 * std_dev)) + (0.40 * avg)
        suggested = max(0.40, min(0.95, round(suggested, 2)))
        
        calculated_thresholds[name] = suggested

        row_str = f"{name:<32} {n:>12} {avg:>10.4f} {min_c:>10.4f} {max_c:>10.4f} {std_dev:>15.4f} {suggested:>17.2f}"
        print(row_str)
        
    print("-" * 110)
    print("💡 Nota sobre o Limiar Sugerido:")
    print("   O 'Limiar Sugerido' é calculado como (Média - 1.5 * Desvio Padrão + 40% da Média). Ele visa maximizar o Recall")
    print("   (encontrar mais objetos) ao mesmo tempo que impede a inclusão de falsos positivos estatísticos.")
    print("=" * 110)

    # Sincronização automática com detection_service.py
    service_path = get_service_file_path()
    if service_path:
        try:
            with open(service_path, "r", encoding="utf-8") as f:
                content = f.read()

            lines = ["CLASS_CONFIDENCE_THRESHOLDS = {"]
            lines.append("    # --- MODELOS E CLASSES ATIVAS ---")
            for k, v in sorted(calculated_thresholds.items()):
                lines.append(f'    "{k}": {v:.2f},')
            lines.append("}")
            new_code_block = "\n".join(lines)

            pattern = r"CLASS_CONFIDENCE_THRESHOLDS\s*=\s*\{[^}]*\}"
            if re.search(pattern, content):
                updated_content = re.sub(pattern, new_code_block, content)
                with open(service_path, "w", encoding="utf-8") as f:
                    f.write(updated_content)
                print(f"✅ Sincronizado automaticamente com '{service_path}'!")
        except Exception as err:
            print(f"⚠️ Erro ao atualizar automaticamente detection_service.py: {err}")

if __name__ == "__main__":
    main()
