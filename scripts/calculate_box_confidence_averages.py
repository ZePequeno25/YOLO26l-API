#!/usr/bin/env python3
"""
Script para agregar os dados de predição do banco de dados e calcular
a média e estatísticas de confiança para cada classe/modelo detectado.
Uso:
    python scripts/calculate_box_confidence_averages.py
"""
import os
import sqlite3
import json
import math
from collections import defaultdict

def get_db_connection():
    # Carregar do SQLite local
    db_path = os.path.join("api-tcc", "data", "prediction_metrics.db")
    if not os.path.exists(db_path):
        db_path = os.path.join("data", "prediction_metrics.db")
        
    if not os.path.exists(db_path):
        print(f"❌ Banco de dados SQLite não encontrado em '{db_path}'.")
        print("Certifique-se de realizar algumas análises/predições primeiro.")
        return None
    return sqlite3.connect(db_path)

def main():
    conn = get_db_connection()
    if not conn:
        return
        
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT box_details FROM prediction_metrics WHERE box_details IS NOT NULL AND box_details != ''")
        rows = cursor.fetchall()
    except Exception as e:
        print(f"❌ Erro ao consultar a tabela: {e}")
        print("Verifique se as migrações automáticas foram executadas iniciando a API.")
        return
    finally:
        conn.close()

    if not rows:
        print("⚠️ Nenhuma métrica com detalhes de caixas delimitadoras encontrada no banco ainda.")
        print("Faça algumas análises de fotos ou vídeos para alimentar os dados.")
        return

    # Agregadores
    class_confidences = defaultdict(list)
    
    for (box_details_str,) in rows:
        try:
            boxes = json.loads(box_details_str)
            for box in boxes:
                cls_name = box.get("class")
                conf = box.get("conf")
                if cls_name and conf is not None:
                    class_confidences[cls_name].append(conf)
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
        suggested = max(0.40, min(0.95, suggested))
        
        row_str = f"{name:<32} {n:>12} {avg:>10.4f} {min_c:>10.4f} {max_c:>10.4f} {std_dev:>15.4f} {suggested:>17.2f}"
        print(row_str)
        
    print("-" * 110)
    print("💡 Nota sobre o Limiar Sugerido:")
    print("   O 'Limiar Sugerido' é calculado como (Média - 1.5 * Desvio Padrão + 40% da Média). Ele visa maximizar o Recall")
    print("   (encontrar mais objetos) ao mesmo tempo que impede a inclusão de falsos positivos estatísticos.")
    print("   Você pode configurar o valor recomendado no seu arquivo .env em DETECTION_CONF_THRESHOLD.")
    print("=" * 110)

if __name__ == "__main__":
    main()
