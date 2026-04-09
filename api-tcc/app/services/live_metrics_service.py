from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from threading import Lock
from typing import Any, Dict, Iterable, List, Optional, Tuple


BBox = Tuple[float, float, float, float]


@dataclass
class EvalDetection:
    class_name: str
    confidence: float
    bbox: BBox


@dataclass
class EvalSample:
    sample_id: str
    model_name: str
    timestamp: datetime
    predictions: List[EvalDetection]
    ground_truth: List[EvalDetection]


class LiveMetricsService:
    """Mantem amostras recentes e calcula precision/recall/mAP em tempo real."""

    def __init__(self, window_seconds: int = 300):
        self.window_seconds = window_seconds
        self._samples: deque[EvalSample] = deque()
        self._pending_predictions: Dict[str, Dict[str, Any]] = {}
        self._lock = Lock()

    def set_window(self, window_seconds: int) -> None:
        if window_seconds <= 0:
            raise ValueError("window_seconds deve ser > 0")
        with self._lock:
            self.window_seconds = window_seconds
            self._prune_locked()

    def reset(self) -> None:
        with self._lock:
            self._samples.clear()
            self._pending_predictions.clear()

    def add_prediction_sample(self, sample_id: str, model_name: str, predictions: List[Dict[str, Any]]) -> None:
        parsed_predictions = self._parse_detections(predictions)
        with self._lock:
            self._pending_predictions[sample_id] = {
                "model_name": model_name,
                "predictions": parsed_predictions,
                "timestamp": datetime.utcnow(),
            }
            self._prune_locked()

    def add_ground_truth(self, sample_id: str, ground_truth: List[Dict[str, Any]], model_name: Optional[str] = None) -> Dict[str, Any]:
        parsed_ground_truth = self._parse_detections(ground_truth, confidence_default=1.0)

        with self._lock:
            pending = self._pending_predictions.pop(sample_id, None)

            if pending is None:
                if model_name is None:
                    raise ValueError("sample_id nao encontrado nas predicoes pendentes e model_name nao informado")
                sample = EvalSample(
                    sample_id=sample_id,
                    model_name=model_name,
                    timestamp=datetime.utcnow(),
                    predictions=[],
                    ground_truth=parsed_ground_truth,
                )
            else:
                sample = EvalSample(
                    sample_id=sample_id,
                    model_name=pending["model_name"],
                    timestamp=datetime.utcnow(),
                    predictions=pending["predictions"],
                    ground_truth=parsed_ground_truth,
                )

            self._samples.append(sample)
            self._prune_locked()

        return {
            "sample_id": sample_id,
            "model_name": sample.model_name,
            "predictions_count": len(sample.predictions),
            "ground_truth_count": len(sample.ground_truth),
        }

    def get_live_metrics(self, iou_threshold: float = 0.5, map_step: float = 0.05) -> Dict[str, Any]:
        if not (0.0 < iou_threshold <= 1.0):
            raise ValueError("iou_threshold deve estar entre 0 e 1")
        if not (0.0 < map_step <= 0.5):
            raise ValueError("map_step deve estar entre 0 e 0.5")

        with self._lock:
            self._prune_locked()
            samples = list(self._samples)
            pending_count = len(self._pending_predictions)
            window_seconds = self.window_seconds

        if not samples:
            return {
                "window_seconds": window_seconds,
                "samples_evaluated": 0,
                "pending_samples": pending_count,
                "precision": 0.0,
                "recall": 0.0,
                "mAP50": 0.0,
                "mAP50_95": 0.0,
                "per_class": {},
                "totals": {"tp": 0, "fp": 0, "fn": 0},
            }

        classes = self._classes_from_ground_truth(samples)
        if not classes:
            classes = sorted(self._classes_from_predictions(samples))

        per_class: Dict[str, Dict[str, Any]] = {}
        total_tp = 0
        total_fp = 0
        total_fn = 0

        iou_thresholds = self._build_map_thresholds(step=map_step)

        for class_name in classes:
            tp, fp, fn = self._compute_tp_fp_fn_for_class(samples, class_name, iou_threshold)
            ap50 = self._compute_ap_for_class(samples, class_name, 0.5)
            ap_multi = [self._compute_ap_for_class(samples, class_name, thr) for thr in iou_thresholds]
            ap50_95 = sum(ap_multi) / len(ap_multi) if ap_multi else 0.0

            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0

            per_class[class_name] = {
                "precision": round(precision, 6),
                "recall": round(recall, 6),
                "AP50": round(ap50, 6),
                "AP50_95": round(ap50_95, 6),
                "tp": tp,
                "fp": fp,
                "fn": fn,
            }

            total_tp += tp
            total_fp += fp
            total_fn += fn

        map50 = sum(item["AP50"] for item in per_class.values()) / len(per_class) if per_class else 0.0
        map50_95 = sum(item["AP50_95"] for item in per_class.values()) / len(per_class) if per_class else 0.0

        precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
        recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0

        return {
            "window_seconds": window_seconds,
            "samples_evaluated": len(samples),
            "pending_samples": pending_count,
            "precision": round(precision, 6),
            "recall": round(recall, 6),
            "mAP50": round(map50, 6),
            "mAP50_95": round(map50_95, 6),
            "per_class": per_class,
            "totals": {"tp": total_tp, "fp": total_fp, "fn": total_fn},
        }

    def _prune_locked(self) -> None:
        cutoff = datetime.utcnow() - timedelta(seconds=self.window_seconds)

        while self._samples and self._samples[0].timestamp < cutoff:
            self._samples.popleft()

        expired_pending = [
            sample_id
            for sample_id, payload in self._pending_predictions.items()
            if payload["timestamp"] < cutoff
        ]
        for sample_id in expired_pending:
            self._pending_predictions.pop(sample_id, None)

    def _classes_from_ground_truth(self, samples: List[EvalSample]) -> List[str]:
        return sorted({det.class_name for sample in samples for det in sample.ground_truth})

    def _classes_from_predictions(self, samples: List[EvalSample]) -> Iterable[str]:
        return {det.class_name for sample in samples for det in sample.predictions}

    def _compute_tp_fp_fn_for_class(self, samples: List[EvalSample], class_name: str, iou_threshold: float) -> Tuple[int, int, int]:
        tp = 0
        fp = 0
        fn = 0

        for sample in samples:
            gt = [det for det in sample.ground_truth if det.class_name == class_name]
            preds = [det for det in sample.predictions if det.class_name == class_name]
            preds = sorted(preds, key=lambda x: x.confidence, reverse=True)

            matched_gt = set()
            for pred in preds:
                best_idx = -1
                best_iou = 0.0
                for idx, gt_det in enumerate(gt):
                    if idx in matched_gt:
                        continue
                    iou = self._iou(pred.bbox, gt_det.bbox)
                    if iou >= iou_threshold and iou > best_iou:
                        best_iou = iou
                        best_idx = idx

                if best_idx >= 0:
                    matched_gt.add(best_idx)
                    tp += 1
                else:
                    fp += 1

            fn += len(gt) - len(matched_gt)

        return tp, fp, fn

    def _compute_ap_for_class(self, samples: List[EvalSample], class_name: str, iou_threshold: float) -> float:
        gt_by_sample: Dict[str, List[EvalDetection]] = {}
        total_gt = 0

        for sample in samples:
            gt_list = [det for det in sample.ground_truth if det.class_name == class_name]
            gt_by_sample[sample.sample_id] = gt_list
            total_gt += len(gt_list)

        if total_gt == 0:
            return 0.0

        ranked_predictions = []
        for sample in samples:
            preds = [det for det in sample.predictions if det.class_name == class_name]
            for pred in preds:
                ranked_predictions.append((sample.sample_id, pred.confidence, pred.bbox))

        if not ranked_predictions:
            return 0.0

        ranked_predictions.sort(key=lambda item: item[1], reverse=True)

        matched: Dict[str, set[int]] = defaultdict(set)
        tp_flags: List[int] = []
        fp_flags: List[int] = []

        for sample_id, _confidence, pred_bbox in ranked_predictions:
            gt_list = gt_by_sample.get(sample_id, [])
            best_idx = -1
            best_iou = 0.0

            for idx, gt_det in enumerate(gt_list):
                if idx in matched[sample_id]:
                    continue
                iou = self._iou(pred_bbox, gt_det.bbox)
                if iou >= iou_threshold and iou > best_iou:
                    best_iou = iou
                    best_idx = idx

            if best_idx >= 0:
                matched[sample_id].add(best_idx)
                tp_flags.append(1)
                fp_flags.append(0)
            else:
                tp_flags.append(0)
                fp_flags.append(1)

        cum_tp: List[int] = []
        cum_fp: List[int] = []
        running_tp = 0
        running_fp = 0

        for tp_flag, fp_flag in zip(tp_flags, fp_flags):
            running_tp += tp_flag
            running_fp += fp_flag
            cum_tp.append(running_tp)
            cum_fp.append(running_fp)

        recalls = [tp / total_gt for tp in cum_tp]
        precisions = [tp / (tp + fp) if (tp + fp) > 0 else 0.0 for tp, fp in zip(cum_tp, cum_fp)]

        return self._ap_from_pr_curve(recalls, precisions)

    @staticmethod
    def _ap_from_pr_curve(recalls: List[float], precisions: List[float]) -> float:
        if not recalls:
            return 0.0

        mrec = [0.0] + recalls + [1.0]
        mpre = [0.0] + precisions + [0.0]

        for i in range(len(mpre) - 2, -1, -1):
            mpre[i] = max(mpre[i], mpre[i + 1])

        ap = 0.0
        for i in range(len(mrec) - 1):
            if mrec[i + 1] != mrec[i]:
                ap += (mrec[i + 1] - mrec[i]) * mpre[i + 1]

        return float(ap)

    @staticmethod
    def _build_map_thresholds(step: float = 0.05) -> List[float]:
        thresholds = []
        value = 0.5
        while value <= 0.95 + 1e-9:
            thresholds.append(round(value, 2))
            value += step
        return thresholds

    @staticmethod
    def _parse_detections(payload: List[Dict[str, Any]], confidence_default: float = 0.0) -> List[EvalDetection]:
        detections: List[EvalDetection] = []
        for item in payload:
            class_name = item.get("class_name")
            if not class_name:
                raise ValueError("Cada box precisa de class_name")

            x1 = float(item.get("x1"))
            y1 = float(item.get("y1"))
            x2 = float(item.get("x2"))
            y2 = float(item.get("y2"))
            conf = float(item.get("confidence", confidence_default))

            if x2 <= x1 or y2 <= y1:
                raise ValueError("Box invalida: x2/y2 devem ser maiores que x1/y1")

            detections.append(
                EvalDetection(
                    class_name=class_name,
                    confidence=conf,
                    bbox=(x1, y1, x2, y2),
                )
            )

        return detections

    @staticmethod
    def _iou(box_a: BBox, box_b: BBox) -> float:
        ax1, ay1, ax2, ay2 = box_a
        bx1, by1, bx2, by2 = box_b

        inter_x1 = max(ax1, bx1)
        inter_y1 = max(ay1, by1)
        inter_x2 = min(ax2, bx2)
        inter_y2 = min(ay2, by2)

        inter_w = max(0.0, inter_x2 - inter_x1)
        inter_h = max(0.0, inter_y2 - inter_y1)
        inter_area = inter_w * inter_h

        area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
        area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)

        union = area_a + area_b - inter_area
        if union <= 0:
            return 0.0

        return inter_area / union


live_metrics_service = LiveMetricsService()
