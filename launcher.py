#!/usr/bin/env python3
"""Cross-platform launcher for the YOLO26l API.

This script keeps the setup flow friendly:
- validates the local machine;
- creates/updates api-tcc/.venv;
- optionally starts Ollama;
- installs Windows services when running on Windows;
- starts the API in foreground mode on Linux/macOS.
"""

from __future__ import annotations

import os
import platform
import queue
import shutil
import socket
import subprocess
import threading
import time
import webbrowser
from pathlib import Path
from typing import List, Optional

try:
    import tkinter as tk
    from tkinter import messagebox, ttk
except Exception as exc:  # pragma: no cover
    print(f"Tkinter nao esta disponivel: {exc}")
    raise


ROOT_DIR = Path(__file__).resolve().parent
API_DIR = ROOT_DIR / "api-tcc"
LOG_DIR = API_DIR / "logs" / "launcher"
API_PORT = 8080
OLLAMA_PORT = 11434


def is_windows() -> bool:
    """Returns True if running on Windows OS."""
    return platform.system().lower() == "windows"


def venv_python() -> Path:
    """Returns the path to virtual environment python executable."""
    if is_windows():
        return API_DIR / ".venv" / "Scripts" / "python.exe"
    return API_DIR / ".venv" / "bin" / "python"


def local_ip() -> str:
    """Returns the local network IP address."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"


def port_open(host: str, port: int, timeout: float = 0.6) -> bool:
    """Returns True if the port is open and listening."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def command_exists(command: str) -> bool:
    """Returns True if the command is available on the system PATH."""
    return shutil.which(command) is not None


# pylint: disable=too-many-instance-attributes
class LauncherApp:
    """Tkinter-based GUI app to launch the API and manage subprocesses."""

    def __init__(self, root: tk.Tk) -> None:
        """Initializes GUI elements, window state, and queues."""
        self.root = root
        self.root.title("YOLO26l API Launcher")
        self.root.geometry("880x620")
        self.root.minsize(760, 520)

        self.log_queue: queue.Queue[str] = queue.Queue()
        self.worker: threading.Thread | None = None
        self.api_process: subprocess.Popen[str] | None = None
        self.ollama_process: subprocess.Popen[str] | None = None

        self.auto_install = tk.BooleanVar(value=True)
        self.install_services = tk.BooleanVar(value=is_windows())
        self.start_ollama = tk.BooleanVar(value=True)

        self._build_ui()
        self.root.after(100, self._drain_log_queue)
        self.log("Projeto: " + str(ROOT_DIR))
        self.log("API local: http://localhost:8080/docs")
        self.log("API na rede: http://" + local_ip() + ":8080/docs")

    def _build_ui(self) -> None:
        """Assembles frames, checkboxes, buttons, and logs log viewer."""
        frame = ttk.Frame(self.root, padding=14)
        frame.pack(fill=tk.BOTH, expand=True)

        title = ttk.Label(frame, text="YOLO26l API Launcher", font=("Segoe UI", 18, "bold"))
        title.pack(anchor=tk.W)

        subtitle = ttk.Label(
            frame,
            text="Valida ambiente, prepara dependencias e inicia/instala a API com poucos cliques.",
        )
        subtitle.pack(anchor=tk.W, pady=(2, 12))

        options = ttk.LabelFrame(frame, text="Opcoes")
        options.pack(fill=tk.X, pady=(0, 10))

        ttk.Checkbutton(
            options,
            text="Instalar dependencias automaticamente quando faltar algo",
            variable=self.auto_install,
        ).pack(anchor=tk.W, padx=10, pady=(8, 2))

        ttk.Checkbutton(
            options,
            text="Iniciar Ollama automaticamente se estiver instalado",
            variable=self.start_ollama,
        ).pack(anchor=tk.W, padx=10, pady=2)

        service_text = "Instalar como servico do Windows"
        if not is_windows():
            service_text += " (indisponivel fora do Windows)"
        service_check = ttk.Checkbutton(options, text=service_text, variable=self.install_services)
        service_check.pack(anchor=tk.W, padx=10, pady=(2, 8))
        if not is_windows():
            service_check.configure(state=tk.DISABLED)

        buttons = ttk.Frame(frame)
        buttons.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(
            buttons, text="Validar ambiente", command=self.validate_environment
        ).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(
            buttons, text="Preparar dependencias", command=self.prepare_environment
        ).pack(side=tk.LEFT, padx=8)
        ttk.Button(
            buttons, text="Instalar/Iniciar API", command=self.install_or_start
        ).pack(side=tk.LEFT, padx=8)
        ttk.Button(
            buttons, text="Abrir Swagger",
            command=lambda: webbrowser.open("http://localhost:8080/docs")
        ).pack(side=tk.LEFT, padx=8)
        ttk.Button(
            buttons, text="Parar app local", command=self.stop_local_processes
        ).pack(side=tk.LEFT, padx=8)

        status = ttk.LabelFrame(frame, text="Saida")
        status.pack(fill=tk.BOTH, expand=True)

        self.output = tk.Text(status, wrap=tk.WORD, height=20)
        self.output.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll = ttk.Scrollbar(status, orient=tk.VERTICAL, command=self.output.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.output.configure(yscrollcommand=scroll.set)

    def log(self, text: str) -> None:
        """Pushes a log line to the log queue."""
        self.log_queue.put(text.rstrip() + "\n")

    def _drain_log_queue(self) -> None:
        """Drains the log queue and appends logs into the text widget."""
        while True:
            try:
                item = self.log_queue.get_nowait()
            except queue.Empty:
                break
            self.output.insert(tk.END, item)
            self.output.see(tk.END)
        self.root.after(100, self._drain_log_queue)

    def run_worker(self, name: str, target) -> None:
        """Starts a background worker thread to run task safely without blocking GUI."""
        if self.worker and self.worker.is_alive():
            messagebox.showinfo("Aguarde", "Ja existe uma tarefa em execucao.")
            return

        def wrapped() -> None:
            self.log("")
            self.log("== " + name + " ==")
            try:
                target()
            except Exception as exc:  # pylint: disable=broad-exception-caught
                self.log("[erro] " + str(exc))
                messagebox.showerror("Erro", str(exc))

        self.worker = threading.Thread(target=wrapped, daemon=True)
        self.worker.start()

    def run_command(
        self,
        cmd: List[str],
        cwd: Optional[Path] = None,
        check: bool = True,
        stream: bool = True,
    ) -> int:
        """Runs an external command and logs output."""
        self.log("[cmd] " + " ".join(cmd))
        # pylint: disable=consider-using-with
        process = subprocess.Popen(
            cmd,
            cwd=str(cwd or ROOT_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if process.stdout and stream:
            for line in process.stdout:
                self.log(line.rstrip())
        code = process.wait()
        if check and code != 0:
            raise RuntimeError(f"Comando falhou com codigo {code}: {' '.join(cmd)}")
        return code

    def validate_environment(self) -> None:
        """Triggers environment validation on a background thread."""
        self.run_worker("Validacao do ambiente", self._validate_environment)

    def _validate_environment(self) -> None:
        """Performs checks on directories, files, python executable, and ports."""
        sys_py_exists = (
            command_exists("python") or command_exists("python3") or command_exists("py")
        )
        checks = [
            ("Pasta api-tcc", API_DIR.exists()),
            ("requirements.txt", (API_DIR / "requirements.txt").exists()),
            ("main.py", (API_DIR / "main.py").exists()),
            ("Python do sistema", sys_py_exists),
            ("Python da .venv", venv_python().exists()),
            ("Ollama instalado", command_exists("ollama")),
            ("Porta API 8080 respondendo", port_open("127.0.0.1", API_PORT)),
            ("Porta Ollama 11434 respondendo", port_open("127.0.0.1", OLLAMA_PORT)),
        ]
        if is_windows():
            checks.append(("PowerShell", command_exists("powershell")))

        for label, ok in checks:
            self.log(("[ok] " if ok else "[pendente] ") + label)

        self.log("IP de rede detectado: " + local_ip())

    def prepare_environment(self) -> None:
        """Triggers dependency preparation on a background thread."""
        self.run_worker("Preparacao de dependencias", self._prepare_environment)

    def _prepare_environment(self) -> None:
        """Creates venv, upgrades pip, and installs requirements."""
        if not API_DIR.exists():
            raise RuntimeError("Pasta api-tcc nao encontrada.")
        if not (API_DIR / "requirements.txt").exists():
            raise RuntimeError("requirements.txt nao encontrado.")

        py = self._system_python()
        if not venv_python().exists():
            self.run_command([py, "-m", "venv", str(API_DIR / ".venv")], cwd=API_DIR)

        self.run_command(
            [
                str(venv_python()), "-m", "pip", "install", "--upgrade",
                "pip", "setuptools", "wheel"
            ],
            cwd=API_DIR
        )
        self.run_command(
            [str(venv_python()), "-m", "pip", "install", "-r", str(API_DIR / "requirements.txt")],
            cwd=API_DIR
        )
        self.log("[ok] Ambiente Python pronto.")

    def install_or_start(self) -> None:
        """Triggers installation or launch sequence on a worker thread."""
        self.run_worker("Instalacao/inicializacao", self._install_or_start)

    def _install_or_start(self) -> None:
        """Main orchestrator to start Ollama and launch API."""
        if self.auto_install.get() and not venv_python().exists():
            self._prepare_environment()

        if self.start_ollama.get():
            self._ensure_ollama()

        if is_windows() and self.install_services.get():
            self._install_windows_services()
        else:
            self._start_api_foreground()

        self._wait_for_api()

    def _system_python(self) -> str:
        """Finds a viable system Python command."""
        candidates = ["python", "python3"]
        if is_windows():
            candidates.insert(0, "py")
        for candidate in candidates:
            if command_exists(candidate):
                return candidate
        raise RuntimeError("Python nao encontrado. Instale Python 3 e tente novamente.")

    def _ensure_ollama(self) -> None:
        """Starts local Ollama instance if it is installed but not running."""
        if port_open("127.0.0.1", OLLAMA_PORT):
            self.log("[ok] Ollama ja responde em 11434.")
            return
        if not command_exists("ollama"):
            self.log("[aviso] Ollama nao encontrado. A API usa fallback local para mensagens.")
            return
        self.log("Iniciando Ollama...")
        # pylint: disable=consider-using-with
        self.ollama_process = subprocess.Popen(
            ["ollama", "serve"],
            cwd=str(API_DIR),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        for _ in range(20):
            if port_open("127.0.0.1", OLLAMA_PORT):
                self.log("[ok] Ollama iniciado.")
                return
            time.sleep(0.5)
        self.log("[aviso] Ollama foi chamado, mas ainda nao respondeu em 11434.")

    def _install_windows_services(self) -> None:
        """Installs API and database as Windows services."""
        script = API_DIR / "install_windows_services.ps1"
        if not script.exists():
            raise RuntimeError("install_windows_services.ps1 nao encontrado.")
        if not messagebox.askyesno(
            "Permissao de administrador",
            "O Windows vai pedir permissao para instalar servicos e liberar a porta 8080. Continuar?",
        ):
            raise RuntimeError("Instalacao cancelada pelo usuario.")

        cmd = [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            f"Start-Process -FilePath 'powershell.exe' -ArgumentList "
            f"'-NoProfile -ExecutionPolicy Bypass -File \"{script}\"' "
            f"-Verb RunAs -Wait",
        ]
        self.run_command(cmd, cwd=API_DIR, check=True)
        self.log("[ok] Instalador de servicos finalizado.")

    def _start_api_foreground(self) -> None:
        """Launches the API server in a separate process."""
        if not venv_python().exists():
            raise RuntimeError("Ambiente .venv nao encontrado. Rode Preparar dependencias primeiro.")
        if port_open("127.0.0.1", API_PORT):
            self.log("[ok] API ja responde em 8080.")
            return

        env = os.environ.copy()
        env["HOST"] = "0.0.0.0"
        env["PORT"] = str(API_PORT)
        env["PYTHONPATH"] = str(API_DIR)
        env["OLLAMA_HOST"] = f"http://127.0.0.1:{OLLAMA_PORT}"

        self.log("Iniciando API em modo aplicativo...")
        # pylint: disable=consider-using-with
        self.api_process = subprocess.Popen(
            [
                str(venv_python()), "-m", "uvicorn", "main:app",
                "--host", "0.0.0.0", "--port", str(API_PORT)
            ],
            cwd=str(API_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
        )

        def pipe_logs(process: subprocess.Popen[str]) -> None:
            if process.stdout:
                for line in process.stdout:
                    self.log("[api] " + line.rstrip())

        threading.Thread(target=pipe_logs, args=(self.api_process,), daemon=True).start()

    def _wait_for_api(self) -> None:
        """Blocks until the API port responds or timeout expires."""
        for _ in range(40):
            if port_open("127.0.0.1", API_PORT):
                self.log("[ok] API pronta: http://localhost:8080/docs")
                self.log("[ok] Acesso na rede: http://" + local_ip() + ":8080/docs")
                return
            time.sleep(0.5)
        self.log("[aviso] API ainda nao respondeu em 8080. Veja os logs acima.")

    def stop_local_processes(self) -> None:
        """Terminates uvicorn and Ollama subprocesses if running."""
        if self.api_process and self.api_process.poll() is None:
            self.api_process.terminate()
            self.log("[ok] API local encerrada.")
        if self.ollama_process and self.ollama_process.poll() is None:
            self.ollama_process.terminate()
            self.log("[ok] Ollama iniciado pelo launcher foi encerrado.")


def main() -> int:
    """Main launcher entry point."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    root = tk.Tk()
    LauncherApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
