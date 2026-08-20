import os
import sqlite3
import json
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger("api.metrics")

# MySQL Configuration (to be loaded from environment variables)
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3306))
MYSQL_USER = os.getenv("MYSQL_USER", "")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DB = os.getenv("MYSQL_DB", "")

def get_connection():
    """
    Tenta abrir conexão com o banco MySQL se as credenciais estiverem no ambiente.
    Caso contrário, ou se houver falha de rede, retorna uma conexão SQLite local.
    """
    if MYSQL_USER and MYSQL_DB:
        try:
            import pymysql
            conn = pymysql.connect(
                host=MYSQL_HOST,
                port=MYSQL_PORT,
                user=MYSQL_USER,
                password=MYSQL_PASSWORD,
                database=MYSQL_DB,
                charset='utf8mb4'
            )
            return conn, "mysql"
        except Exception as e:
            logger.warning("⚠️ Falha ao conectar ao MySQL (%s). Usando SQLite local como fallback.", e)
    
    # SQLite Fallback
    db_path = os.path.join("data", "prediction_metrics.db")
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(db_path)
    return conn, "sqlite"

def init_db():
    """
    Inicializa a tabela de métricas caso ela não exista e roda migrações se necessário.
    """
    conn, db_type = get_connection()
    cursor = conn.cursor()
    try:
        if db_type == "mysql":
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS prediction_metrics (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    filename VARCHAR(255),
                    requested_model VARCHAR(100),
                    detected_classes TEXT,
                    requested_class_found TINYINT,
                    num_frames INT,
                    compliance_status VARCHAR(50),
                    confidence_avg FLOAT,
                    box_details TEXT
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)
            
            # Migração automática: Adicionar coluna box_details se ela não existir
            cursor.execute("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'prediction_metrics' AND COLUMN_NAME = 'box_details';
            """, (MYSQL_DB,))
            if not cursor.fetchone():
                logger.info("⚡ Executando migração MySQL: adicionando coluna 'box_details'...")
                cursor.execute("ALTER TABLE prediction_metrics ADD COLUMN box_details TEXT;")
                conn.commit()
        else:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS prediction_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    filename TEXT,
                    requested_model TEXT,
                    detected_classes TEXT,
                    requested_class_found INTEGER,
                    num_frames INTEGER,
                    compliance_status TEXT,
                    confidence_avg REAL,
                    box_details TEXT
                )
            """)
            
            # Migração automática para SQLite
            cursor.execute("PRAGMA table_info(prediction_metrics);")
            columns = [col[1] for col in cursor.fetchall()]
            if "box_details" not in columns:
                logger.info("⚡ Executando migração SQLite: adicionando coluna 'box_details'...")
                cursor.execute("ALTER TABLE prediction_metrics ADD COLUMN box_details TEXT;")
                conn.commit()

        logger.info("✅ Tabela prediction_metrics inicializada/verificada com sucesso (%s).", db_type)
    except Exception as e:
        logger.error("❌ Erro ao inicializar/migrar tabela de métricas: %s", e)
    finally:
        conn.close()

def log_prediction(filename: str, requested_model: str, final_counts: dict, num_frames: int, compliance_status: str, all_boxes: list):
    """
    Registra os metadados de uma inferência de detecção no banco de dados, incluindo a precisão de cada box.
    """
    expected_class = requested_model.lower()
    
    # Mapeamento de apelidos comuns para classes reais do modelo
    class_aliases = {
        "cadeira": "cadeira",
        "extintor": "sinal_de_extintor_extintor",
        "pessoa": "pessoa"
    }
    target_class = class_aliases.get(expected_class, expected_class)
    
    # Verifica se a classe desejada foi detectada com contagem maior que 0
    target_class = (requested_model or "").lower().strip()
    class_found = 0
    if target_class in ["all", "", "todos", "all_models"] or "," in target_class:
        if len(all_boxes) > 0 or any(c > 0 for c in final_counts.values()):
            class_found = 1
    else:
        for detected_name, count in final_counts.items():
            if count > 0 and (target_class in detected_name.lower() or detected_name.lower() in target_class):
                class_found = 1
                break
            
    # Calcula a média de confiança de todas as detecções do frame/vídeo
    confidences = [box["confidence"] for box in all_boxes if "confidence" in box]
    confidence_avg = sum(confidences) / len(confidences) if confidences else 0.0

    # Extrai a precisão (confiança) de cada Bounding Box individual com seu respectivo rótulo
    box_details = []
    for box in all_boxes:
        if "class_name" in box and "confidence" in box:
            box_details.append({
                "class": box["class_name"],
                "conf": round(box["confidence"], 4)
            })
    box_details_str = json.dumps(box_details)

    conn, db_type = get_connection()
    cursor = conn.cursor()
    try:
        detected_classes_str = json.dumps(final_counts)
        if db_type == "mysql":
            cursor.execute("""
                INSERT INTO prediction_metrics (filename, requested_model, detected_classes, requested_class_found, num_frames, compliance_status, confidence_avg, box_details)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (filename, requested_model, detected_classes_str, class_found, num_frames, compliance_status, confidence_avg, box_details_str))
        else:
            cursor.execute("""
                INSERT INTO prediction_metrics (filename, requested_model, detected_classes, requested_class_found, num_frames, compliance_status, confidence_avg, box_details)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (filename, requested_model, detected_classes_str, class_found, num_frames, compliance_status, confidence_avg, box_details_str))
        conn.commit()
        logger.info("📈 Métrica de predição gravada no %s para o arquivo %s (Boxes: %d, Média: %.2f%%).", db_type, filename, len(box_details), confidence_avg * 100)
    except Exception as e:
        logger.error("❌ Erro ao salvar métrica de predição: %s", e)
    finally:
        conn.close()
