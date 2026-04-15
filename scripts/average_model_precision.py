"""Agrega o CSV tabular de métricas e calcula médias por modelo.

Uso:
    python scripts/average_model_precision.py
    python scripts/average_model_precision.py --csv api-tcc/logs/metrics/prediction_metrics.csv
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CSV = ROOT / "api-tcc" / "logs" / "metrics" / "prediction_metrics.csv"


def parse_args():
    parser = argparse.ArgumentParser(description="Calcula médias de precisão/recall/mAP por modelo")
    parser.add_argument("--csv", default=str(DEFAULT_CSV), help="Caminho do CSV tabular de métricas")
    parser.add_argument(
        "--output",
        default=str(ROOT / "api-tcc" / "logs" / "metrics" / "model_precision_summary.csv"),
        help="CSV de saída com as médias por modelo",
    )
    return parser.parse_args()


def _to_float(value: str) -> float | None:
    value = (value or "").strip()
    if not value:
        return None
    return float(value)


def load_rows(csv_path: Path):
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV não encontrado: {csv_path}")

    with open(csv_path, encoding="utf-8", newline="") as csvfile:
        return list(csv.DictReader(csvfile))


def summarize_by_model(rows):
    grouped = defaultdict(lambda: {
        "samples": 0,
        "precision_sum": 0.0,
        "recall_sum": 0.0,
        "map50_sum": 0.0,
        "map50_95_sum": 0.0,
        "precision_count": 0,
        "recall_count": 0,
        "map50_count": 0,
        "map50_95_count": 0,
    })

    for row in rows:
        model_name = (row.get("model_name") or "").strip() or "desconhecido"
        bucket = grouped[model_name]
        bucket["samples"] += 1

        precision = _to_float(row.get("precision", ""))
        recall = _to_float(row.get("recall", ""))
        map50 = _to_float(row.get("mAP50", ""))
        map50_95 = _to_float(row.get("mAP50_95", ""))

        if precision is not None:
            bucket["precision_sum"] += precision
            bucket["precision_count"] += 1
        if recall is not None:
            bucket["recall_sum"] += recall
            bucket["recall_count"] += 1
        if map50 is not None:
            bucket["map50_sum"] += map50
            bucket["map50_count"] += 1
        if map50_95 is not None:
            bucket["map50_95_sum"] += map50_95
            bucket["map50_95_count"] += 1

    summary_rows = []
    for model_name, bucket in sorted(grouped.items()):
        summary_rows.append({
            "model_name": model_name,
            "samples": bucket["samples"],
            "avg_precision": _safe_avg(bucket["precision_sum"], bucket["precision_count"]),
            "avg_recall": _safe_avg(bucket["recall_sum"], bucket["recall_count"]),
            "avg_mAP50": _safe_avg(bucket["map50_sum"], bucket["map50_count"]),
            "avg_mAP50_95": _safe_avg(bucket["map50_95_sum"], bucket["map50_95_count"]),
        })
    return summary_rows


def _safe_avg(total: float, count: int) -> float:
    return round(total / count, 6) if count > 0 else 0.0


def write_summary_csv(output_path: Path, rows) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8", newline="") as csvfile:
        writer = csv.DictWriter(
            csvfile,
            fieldnames=["model_name", "samples", "avg_precision", "avg_recall", "avg_mAP50", "avg_mAP50_95"],
        )
        writer.writeheader()
        writer.writerows(rows)


def print_summary(rows) -> None:
    if not rows:
        print("Nenhuma linha encontrada no CSV de métricas.")
        return

    print("\nResumo por modelo\n")
    print(f"{'Modelo':<24} {'Amostras':>8} {'Precisão':>12} {'Recall':>12} {'mAP50':>12} {'mAP50-95':>12}")
    print("-" * 84)
    for row in rows:
        print(
            f"{row['model_name']:<24} {row['samples']:>8} "
            f"{row['avg_precision']:>12.6f} {row['avg_recall']:>12.6f} "
            f"{row['avg_mAP50']:>12.6f} {row['avg_mAP50_95']:>12.6f}"
        )


def main():
    args = parse_args()
    csv_path = Path(args.csv)
    output_path = Path(args.output)

    rows = load_rows(csv_path)
    summary = summarize_by_model(rows)
    write_summary_csv(output_path, summary)
    print_summary(summary)
    print(f"\nCSV resumo salvo em: {output_path}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"[ERRO] {exc}")
        sys.exit(1)