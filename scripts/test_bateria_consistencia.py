#!/usr/bin/env python3
"""
Bateria de Testes de Consistência (5 Execuções por Pasta) - YOLO26l-API.
Verifica:
1. Se o serviço Ollama está ativo em http://127.0.0.1:11434/ (iniciando em novo CMD caso não esteja).
2. 5 execuções completas e independentes para cada uma das 3 pastas em TESTES/:
   - EXTINTOR COM PLACA: Deve encontrar Extintor + Placa de Sinalização + Submodelos (Status: CONFORME).
   - EXTINTOR SEM PLACA: Deve encontrar apenas Extintor + Submodelos (sem Placa) e retornar alerta sobre inexistência da placa de sinalização (Status: NÃO CONFORME).
   - PLACA SEM EXTINTOR: Deve encontrar apenas Placa de Sinalização (sem Extintor e sem Submodelos) e retornar alerta de extintor ausente (Status: NÃO CONFORME).
3. Verificação estrita de consistência entre as 5 tentativas (mesmas contagens, mesmas caixas, mesmas confianças, mesmos alertas e mesmo status).
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True, write_through=True)
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", line_buffering=True, write_through=True)

ROOT_DIR = Path(__file__).resolve().parent.parent
API_TCC_DIR = ROOT_DIR / "api-tcc"
SITE_PACKAGES = API_TCC_DIR / ".venv" / "Lib" / "site-packages"
if SITE_PACKAGES.exists():
    sys.path.insert(0, str(SITE_PACKAGES))
sys.path.insert(0, str(API_TCC_DIR))

import cv2
import numpy as np
from ultralytics import YOLO
from config.settings import settings
from app.services.detection_service import detection_service


def ensure_ollama_running() -> bool:
    """Verifica se o Ollama está respondendo na porta 11434; caso contrário, inicia em novo CMD."""
    import socket
    try:
        with socket.create_connection(("127.0.0.1", 11434), timeout=1.0):
            print("[OLLAMA] Ativo e respondendo em http://127.0.0.1:11434/", flush=True)
            return True
    except Exception:
        pass

    print("[OLLAMA] Porta 11434 inacessível no ambiente atual; verificando processo Ollama...", flush=True)
    ollama_exe = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe"
    if ollama_exe.exists():
        try:
            subprocess.Popen(
                [str(ollama_exe), "serve"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=True,
                creationflags=subprocess.CREATE_NEW_CONSOLE if hasattr(subprocess, "CREATE_NEW_CONSOLE") else 0,
            )
            time.sleep(1.0)
            with socket.create_connection(("127.0.0.1", 11434), timeout=1.0):
                print("[OLLAMA] Iniciado com sucesso em novo CMD!", flush=True)
                return True
        except Exception:
            pass

    print("[OLLAMA] Usando modo determinístico local (laudo técnico estruturado).", flush=True)
    return False


def evaluate_folder_expectations(folder_name: str, result: Dict[str, Any]) -> Dict[str, Any]:
    """Avalia se o resultado da imagem cumpre os requisitos da pasta de teste."""
    counts = result.get("class_counts", {})
    status = result.get("compliance_status", "")
    alerts = result.get("compliance_alerts", [])
    sub_layer = result.get("sub_layer_analysis", [])

    ext_classes = [
        k for k, v in counts.items()
        if v > 0 and any(w in k.lower() for w in ["extintor", "babcock", "walker", "yamato"])
    ]
    sign_classes = [
        k for k, v in counts.items()
        if v > 0 and ("placa" in k.lower() or "sinaliza" in k.lower())
    ]
    submodel_classes = [
        k for k, v in counts.items()
        if v > 0 and k in (
            "Handle", "Manômetro de Pressão", "Mangueira / Difusor",
            "Trava / Lacre de Segurança", "Adesivo / Rótulo"
        )
    ]

    has_ext = len(ext_classes) > 0
    has_sign = len(sign_classes) > 0
    has_sub = len(submodel_classes) > 0 and len(sub_layer) > 0

    if folder_name == "EXTINTOR COM PLACA":
        passed = (
            has_ext
            and has_sign
            and has_sub
            and status == "CONFORME"
            and len(alerts) == 0
        )
    elif folder_name == "EXTINTOR SEM PLACA":
        has_missing_sign_alert = any("placa de sinalização" in a.lower() and "ausente" in a.lower() for a in alerts)
        passed = (
            has_ext
            and has_sub
            and (not has_sign)
            and status == "NÃO CONFORME"
            and has_missing_sign_alert
        )
    elif folder_name == "PLACA SEM EXTINTOR":
        has_missing_ext_alert = any("extintor" in a.lower() and "ausente" in a.lower() for a in alerts)
        passed = (
            has_sign
            and (not has_ext)
            and (not has_sub)
            and status == "NÃO CONFORME"
            and has_missing_ext_alert
        )
    else:
        passed = False

    return {
        "passed": passed,
        "has_extinguisher": has_ext,
        "has_sign": has_sign,
        "has_submodels": has_sub,
        "ext_classes": ext_classes,
        "sign_classes": sign_classes,
        "submodel_classes": submodel_classes,
        "compliance_status": status,
        "compliance_alerts": alerts,
    }


def extract_signature(result: Dict[str, Any]) -> Dict[str, Any]:
    """Extrai assinatura determinística da resposta para comparar consistência entre as 5 execuções."""
    boxes_sig = [
        {
            "class_name": b.get("class_name"),
            "confidence": round(float(b.get("confidence", 0.0)), 4),
            "x1": b.get("x1"),
            "y1": b.get("y1"),
            "x2": b.get("x2"),
            "y2": b.get("y2"),
            "model_source": b.get("model_source"),
        }
        for b in result.get("boxes", [])
    ]
    return {
        "class_counts": dict(sorted(result.get("class_counts", {}).items())),
        "boxes": boxes_sig,
        "compliance_status": result.get("compliance_status"),
        "compliance_alerts": list(result.get("compliance_alerts", [])),
        "sub_layer_analysis": result.get("sub_layer_analysis", []),
    }


def run_battery(num_runs: int = 5):
    ollama_ok = ensure_ollama_running()
    settings.SAVE_TRAINING_ARTIFACTS = False
    settings.SAVE_PREDICTION_FILES = False
    settings.ENABLE_PERSONALIZED_MESSAGE = ollama_ok

    testes_dir = ROOT_DIR / "TESTES"
    folders = ["EXTINTOR COM PLACA", "EXTINTOR SEM PLACA", "PLACA SEM EXTINTOR"]

    report: Dict[str, Any] = {
        "num_runs": num_runs,
        "folders": {},
        "overall_accuracy_passed": True,
        "overall_consistency_100_percent": True,
    }

    print("\n" + "=" * 105, flush=True)
    print(f"{'BATERIA DE TESTES DE CONSISTÊNCIA (5 EXECUÇÕES POR PASTA)':^105}", flush=True)
    print("=" * 105, flush=True)

    for folder_name in folders:
        folder_path = testes_dir / folder_name
        files = sorted([p for p in folder_path.iterdir() if p.is_file()])

        print(f"\n📂 PASTA: {folder_name} ({len(files)} arquivos | {num_runs} execuções)", flush=True)
        print("-" * 105, flush=True)

        runs_data: List[Dict[str, Dict[str, Any]]] = []

        for run_idx in range(1, num_runs + 1):
            run_results: Dict[str, Dict[str, Any]] = {}
            passed_in_run = 0
            t0 = time.perf_counter()

            for img_path in files:
                content = img_path.read_bytes()
                res = detection_service.analyze_image_bytes(
                    content,
                    img_path.name,
                    model_name="extintor de incêndio",
                    log_to_db=(run_idx == 1),
                )

                eval_info = evaluate_folder_expectations(folder_name, res)
                sig = extract_signature(res)
                if eval_info["passed"]:
                    passed_in_run += 1

                run_results[img_path.name] = {
                    "evaluation": eval_info,
                    "signature": sig,
                    "compliance_report": res.get("compliance_report"),
                }

            elapsed = time.perf_counter() - t0
            runs_data.append(run_results)
            print(
                f"  ▶ Execução {run_idx}/{num_runs}: {passed_in_run}/{len(files)} aprovados "
                f"({(passed_in_run / len(files)) * 100:.1f}%) | Tempo: {elapsed:.2f}s",
                flush=True,
            )

        consistent_files = 0
        folder_file_summaries = {}

        for img_path in files:
            fname = img_path.name
            base_sig = runs_data[0][fname]["signature"]
            is_identical_across_5_runs = all(
                runs_data[r][fname]["signature"] == base_sig
                for r in range(1, num_runs)
            )
            all_runs_passed = all(
                runs_data[r][fname]["evaluation"]["passed"]
                for r in range(num_runs)
            )
            if is_identical_across_5_runs:
                consistent_files += 1
            else:
                report["overall_consistency_100_percent"] = False
                for r in range(1, num_runs):
                    sig_r = runs_data[r][fname]["signature"]
                    if sig_r != base_sig:
                        for k in base_sig:
                            if base_sig[k] != sig_r[k]:
                                print(f"      [DIFF Run 1 vs Run {r+1} em '{k}']: Run1={base_sig[k]} | Run{r+1}={sig_r[k]}", flush=True)
                        break

            if not all_runs_passed:
                report["overall_accuracy_passed"] = False

            ev0 = runs_data[0][fname]["evaluation"]
            status_tag = "OK" if (all_runs_passed and is_identical_across_5_runs) else "FALHA"
            print(
                f"    [{status_tag}] {fname:<65} | "
                f"Ext={str(ev0['has_extinguisher']):<5} "
                f"Placa={str(ev0['has_sign']):<5} "
                f"Sub={str(ev0['has_submodels']):<5} | "
                f"Status={ev0['compliance_status']:<12} | "
                f"Consistente 5/5={is_identical_across_5_runs}",
                flush=True,
            )

            folder_file_summaries[fname] = {
                "all_5_runs_passed": all_runs_passed,
                "identical_across_5_runs": is_identical_across_5_runs,
                "class_counts": base_sig["class_counts"],
                "compliance_status": base_sig["compliance_status"],
                "compliance_alerts": base_sig["compliance_alerts"],
                "sample_ollama_report": runs_data[0][fname]["compliance_report"],
            }

        print(
            f"  ✅ Resumo '{folder_name}': "
            f"Consistência {consistent_files}/{len(files)} (100% idêntico nas {num_runs} execuções)",
            flush=True,
        )

        report["folders"][folder_name] = {
            "total_files": len(files),
            "consistent_files": consistent_files,
            "files": folder_file_summaries,
        }

    metrics_dir = API_TCC_DIR / "logs" / "metrics"
    metrics_dir.mkdir(parents=True, exist_ok=True)
    report_path = metrics_dir / "bateria_5_execucoes_report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\n" + "=" * 105, flush=True)
    print(f"📄 Relatório detalhado salvo em: {report_path}", flush=True)
    print("=" * 105, flush=True)

    if not report["overall_accuracy_passed"] or not report["overall_consistency_100_percent"]:
        sys.exit(1)


if __name__ == "__main__":
    run_battery(5)
