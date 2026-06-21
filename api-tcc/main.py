"""
Main application module.
Configures and initializes the FastAPI application, routers, middlewares,
and Gzip handlers.
"""
import multiprocessing
import os
import platform
import shutil
import sys
from pathlib import Path

def _setup_openh264_dll():
    """
    Garante que a DLL do OpenH264 esteja no diretório do executável Python (.venv/Scripts)
    e no diretório de trabalho, além de registrar os diretórios no caminho de busca de DLLs do Windows
    (para compatibilidade com Python 3.8+ e escrita de vídeo H.264 no OpenCV).
    """
    if platform.system().lower() != "windows":
        return

    try:
        # O diretório raiz da API é o diretório que contém este arquivo (main.py)
        api_root = Path(__file__).resolve().parent
        src_dll = api_root / "openh264-1.8.0-win64.dll"
        
        if not src_dll.exists():
            print(f"⚠️ openh264 DLL de origem não encontrada em: {src_dll}")
            return
            
        # Destino 1: O diretório do executável Python (ex: .venv/Scripts ou C:\Python312)
        py_dir = Path(os.path.dirname(sys.executable))
        dest_dll1 = py_dir / "openh264-1.8.0-win64.dll"
        
        # Copiar se não existir ou se o tamanho for diferente
        if not dest_dll1.exists() or dest_dll1.stat().st_size != src_dll.stat().st_size:
            shutil.copy2(src_dll, dest_dll1)
            print(f"✅ openh264 DLL copiada para o diretório do Python: {dest_dll1}")
            
        # Destino 2: O diretório atual de trabalho (CWD)
        cwd_dir = Path(os.getcwd())
        dest_dll2 = cwd_dir / "openh264-1.8.0-win64.dll"
        if not dest_dll2.exists() or dest_dll2.stat().st_size != src_dll.stat().st_size:
            shutil.copy2(src_dll, dest_dll2)
            print(f"✅ openh264 DLL copiada para o diretório de trabalho: {dest_dll2}")

        # Adicionar os diretórios ao caminho de busca do Windows (essencial para Python 3.8+)
        if hasattr(os, "add_dll_directory"):
            try:
                os.add_dll_directory(str(api_root))
                os.add_dll_directory(str(py_dir))
                os.add_dll_directory(str(cwd_dir))
                print("✅ Diretórios de DLLs registrados no caminho de busca do Python 3.8+")
            except Exception as e:
                print(f"⚠️ Aviso ao registrar caminhos de busca de DLL: {e}")

    except Exception as e:
        print(f"⚠️ Erro ao configurar openh264 DLL no Windows: {e}")

_setup_openh264_dll()

from fastapi import FastAPI, Request, Response
from fastapi.routing import APIRoute
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from fastapi.routing import request_response
import uvicorn

from app.core.gzip_route import GzipRequest, GzipRoute
from app.core.not_found_guard import NotFoundGuard
from app.core.request_protection import RequestProtectionMiddleware
from app.routes.auth_routes import router as auth_router
from app.routes.detection_routes import router as detection_router
from app.routes.error_routes import router as error_router
from app.routes.feedback_routes import router as feedback_router
from app.routes.system_routes import router as system_router
from config.settings import settings

app = FastAPI(title="API TCC - Detecção de Cadeiras (SOA)", version="1.0")
app.router.route_class = GzipRoute

allowed_origins = [
    origin.strip()
    for origin in settings.CORS_ALLOWED_ORIGINS.split(",")
    if origin.strip()
]

allowed_hosts = [
    host.strip()
    for host in settings.ALLOWED_HOSTS.split(",")
    if host.strip()
]

# Bloqueio de IPs que acumulam muitas requisições a rotas inexistentes
app.add_middleware(NotFoundGuard)

# Blindagem de rotas internas, proteção anti-rajada e headers de segurança.
app.add_middleware(RequestProtectionMiddleware)

# Mitiga host header abuse e reduz superfície para phishing/host spoofing.
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=allowed_hosts,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(system_router)
app.include_router(auth_router)
app.include_router(detection_router)
app.include_router(error_router)
app.include_router(feedback_router)


@app.get("/healthz", tags=["Health"])
async def healthz():
    """Health check endpoint to verify API online status."""
    return {"status": "ok"}


# Aplica GzipRequest a todas as rotas registradas na aplicação
# (incluindo rotas importadas/incluídas)
def make_gzip_handler(original_handler):
    """Wraps a route handler with GzipRequest processing."""
    async def custom_route_handler(request: Request) -> Response:
        request = GzipRequest(request.scope, request.receive)
        return await original_handler(request)
    return custom_route_handler

for route in app.routes:
    if isinstance(route, APIRoute):
        route.app = request_response(make_gzip_handler(route.get_route_handler()))


if __name__ == "__main__":
    if settings.DEBUG:
        # Em desenvolvimento, prioriza hot reload.
        print("🔄 Iniciando API em modo debug com hot reload...")
        uvicorn.run(
            "main:app",
            host=settings.HOST,
            port=settings.PORT,
            reload=True,
            log_level="info",
        )
    else:
        # Em produção, prioriza paralelismo com múltiplos workers.
        num_workers = max(2, multiprocessing.cpu_count() // 2)
        print(f"🚀 Iniciando API com {num_workers} workers para processamento paralelo...")
        uvicorn.run(
            "main:app",
            host=settings.HOST,
            port=settings.PORT,
            reload=False,
            workers=num_workers,
            log_level="info",
        )