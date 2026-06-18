"""
Metrics reporting service module.
Appends sample evaluation metrics (precision, recall, mAP) to a tabular CSV report file.
"""
from __future__ import annotations

import csv
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterable


# pylint: disable=too-few-public-methods
class MetricsReportService:
    """Persiste métricas de avaliação em CSV tabular para análise posterior."""

    FIELDNAMES = [
        "created_at",
        "source",
        "sample_id",
        "model_name",
        "classes",
        "predictions_count",
        "ground_truth_count",
        "tp",
        "fp",
        "fn",
        "precision",
        "recall",
        "mAP50",
        "mAP50_95",
    ]

    def __init__(self, report_path: Path | None = None):
        base_dir = Path(__file__).resolve().parents[2] / "logs" / "metrics"
        self.report_path = report_path or (base_dir / "prediction_metrics.csv")
        self.lock_path = self.report_path.with_suffix(self.report_path.suffix + ".lock")
        self.report_path.parent.mkdir(parents=True, exist_ok=True)

    def append_row(self, row: Dict[str, Any]) -> Path:
        """
        Normalizes and appends a single row of metrics to the CSV file.
        """
        normalized = self._normalize_row(row)
        self._write_rows([normalized])
        return self.report_path

    def append_sample_metrics(self, metrics: Dict[str, Any], source: str) -> Path:
        """
        Extracts relevant metrics from the dictionary and appends them to the CSV report.
        """
        row = {
            "created_at": metrics["created_at"],
            "source": source,
            "sample_id": metrics["sample_id"],
            "model_name": metrics["model_name"],
            "classes": ",".join(metrics.get("classes", [])),
            "predictions_count": metrics["predictions_count"],
            "ground_truth_count": metrics["ground_truth_count"],
            "tp": metrics["tp"],
            "fp": metrics["fp"],
            "fn": metrics["fn"],
            "precision": metrics["precision"],
            "recall": metrics["recall"],
            "mAP50": metrics["mAP50"],
            "mAP50_95": metrics["mAP50_95"],
        }
        return self.append_row(row)

    def _normalize_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """
        Formats float and integer metric fields for consistent CSV writing.
        """
        normalized = {field: row.get(field, "") for field in self.FIELDNAMES}
        for metric_name in ("precision", "recall", "mAP50", "mAP50_95"):
            value = normalized.get(metric_name, "")
            if value != "":
                normalized[metric_name] = f"{float(value):.6f}"
        for int_name in ("predictions_count", "ground_truth_count", "tp", "fp", "fn"):
            value = normalized.get(int_name, "")
            if value != "":
                normalized[int_name] = int(value)
        return normalized

    def _write_rows(self, rows: Iterable[Dict[str, Any]]) -> None:
        """
        Writes rows to the CSV file with headers, locking the file during the write operation.
        """
        self.report_path.parent.mkdir(parents=True, exist_ok=True)
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)

        with self._locked_file():
            file_exists = self.report_path.exists()
            with open(self.report_path, "a", encoding="utf-8", newline="") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=self.FIELDNAMES)
                if not file_exists or self.report_path.stat().st_size == 0:
                    writer.writeheader()
                writer.writerows(rows)

    @contextmanager
    def _locked_file(self):
        """
        Context manager that locks/unlocks the lock file for NT or POSIX.
        """
        self.lock_path.touch(exist_ok=True)
        with open(self.lock_path, "r+", encoding="utf-8") as lock_file:
            self._acquire_lock(lock_file)
            try:
                yield
            finally:
                self._release_lock(lock_file)

    @staticmethod
    def _acquire_lock(lock_file) -> None:
        """
        Acquires an exclusive OS-level lock on the specified file object.
        """
        if os.name == "nt":
            import msvcrt  # pylint: disable=import-outside-toplevel

            lock_file.seek(0)
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)
            return

        import fcntl  # pylint: disable=import-outside-toplevel

        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)

    @staticmethod
    def _release_lock(lock_file) -> None:
        """
        Releases an exclusive OS-level lock on the specified file object.
        """
        if os.name == "nt":
            import msvcrt  # pylint: disable=import-outside-toplevel

            lock_file.seek(0)
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
            return

        import fcntl  # pylint: disable=import-outside-toplevel

        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


metrics_report_service = MetricsReportService()