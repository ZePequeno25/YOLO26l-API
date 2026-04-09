#!/usr/bin/env python3
"""Cross-platform setup script for the API environment.

Usage examples:
  python setup_env.py
  python setup_env.py --venv .venv --requirements requirements.txt
  python setup_env.py --skip-venv
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str], cwd: Path | None = None) -> None:
    print("[cmd]", " ".join(cmd))
    subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=True)


def resolve_venv_python(venv_dir: Path) -> Path:
    if sys.platform.startswith("win"):
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Setup Python environment for api-tcc")
    parser.add_argument("--venv", default=".venv", help="Virtual environment directory name")
    parser.add_argument(
        "--requirements",
        default="requirements.txt",
        help="Requirements file path relative to this script",
    )
    parser.add_argument(
        "--skip-venv",
        action="store_true",
        help="Install dependencies in current interpreter instead of creating venv",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_dir = Path(__file__).resolve().parent
    req_file = project_dir / args.requirements

    if not req_file.exists():
        print(f"[erro] requirements nao encontrado: {req_file}")
        return 1

    if args.skip_venv:
        python_exec = Path(sys.executable)
        print(f"[info] usando interpretador atual: {python_exec}")
    else:
        venv_dir = project_dir / args.venv
        if not venv_dir.exists():
            print(f"[info] criando ambiente virtual em {venv_dir}")
            run([sys.executable, "-m", "venv", str(venv_dir)], cwd=project_dir)

        python_exec = resolve_venv_python(venv_dir)
        if not python_exec.exists():
            print(f"[erro] python do venv nao encontrado: {python_exec}")
            return 1

    run([str(python_exec), "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"], cwd=project_dir)
    run([str(python_exec), "-m", "pip", "install", "-r", str(req_file)], cwd=project_dir)

    print("[ok] ambiente configurado com sucesso")
    print(f"[ok] python: {python_exec}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
