from pathlib import Path
import sqlite3

# Caminho dinâmico do banco de dados local
ROOT_DIR = Path(__file__).resolve().parent.parent
db_path = ROOT_DIR / "api-tcc" / "data" / "prediction_metrics.db"

def visualizar():
    if not db_path.exists():
        print(f"⚠️ O arquivo de banco de dados não foi encontrado em: {db_path}")
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Consultar estatísticas gerais de acurácia
        cursor.execute("""
            SELECT COUNT(*), SUM(requested_class_found) 
            FROM prediction_metrics;
        """)
        total_req, total_found = cursor.fetchone()
        total_found = total_found or 0
        
        # Consultar estatísticas detalhadas agrupadas por modelo
        cursor.execute("""
            SELECT 
                COALESCE(requested_model, 'todos (multimodelo)') as modelo,
                COUNT(*) as total,
                SUM(CASE WHEN requested_class_found = 1 THEN 1 ELSE 0 END) as acertos,
                AVG(confidence_avg) as conf_media
            FROM prediction_metrics
            GROUP BY requested_model
            ORDER BY total DESC;
        """)
        model_stats = cursor.fetchall()
        
        if not model_stats or total_req == 0:
            print("\n=== Banco inicializado, mas nenhuma métrica foi gravada ainda ===")
            conn.close()
            return
            
        print("\n" + "="*100)
        print("🎯 ESTATÍSTICA DE DETECÇÃO E ACERTO POR MODELO (HISTÓRICO COMPLETO)")
        print("="*100)
        print(f"{'Modelo / Classe':<35} | {'Requisições':<12} | {'Acertos':<10} | {'Taxa de Acerto':<16} | {'Conf. Média':<11}")
        print("-"*100)
        for stat in model_stats:
            modelo, total, acertos, conf_avg = stat
            acertos = acertos or 0
            taxa_perc = (acertos / total) * 100 if total > 0 else 0.0
            taxa_str = f"{taxa_perc:.2f}%"
            conf_avg_str = f"{conf_avg*100:.1f}%" if (conf_avg is not None) else "0.0%"
            model_name_disp = (modelo[:32] + "...") if len(modelo) > 35 else modelo
            print(f"{model_name_disp:<35} | {total:<12} | {acertos:<10} | {taxa_str:<16} | {conf_avg_str:<11}")
        print("="*100)

        if total_req > 0:
            acerto_perc = (total_found / total_req) * 100
            print(f"📈 ESTATÍSTICA GERAL TOTAL: {total_found} acertos de {total_req} predições ({acerto_perc:.2f}% de Taxa de Acerto)")
            print("="*100 + "\n")
            
        conn.close()
    except Exception as e:
        print(f"❌ Erro ao abrir ou ler o banco de dados: {e}")

if __name__ == "__main__":
    visualizar()
