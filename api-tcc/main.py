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

def _download_and_extract_dll(url: str, dest_path: Path):
    """Downloads a .bz2 file from a URL and extracts it to dest_path."""
    import urllib.request
    import bz2
    print(f"📥 Baixando OpenH264 DLL de {url}...")
    try:
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            bz2_data = response.read()
            
        print("🔓 Descomprimindo arquivo .bz2...")
        dll_data = bz2.decompress(bz2_data)
        dest_path.write_bytes(dll_data)
        print(f"✅ DLL descompactada com sucesso em: {dest_path}")
        return True
    except Exception as e:
        print(f"⚠️ Falha ao baixar ou extrair DLL: {e}")
        return False

def _setup_openh264_dll():
    """
    Garante que as DLLs do OpenH264 (versões 1.8.0, 2.5.0 e 2.6.0) estejam no diretório do executável
    Python e no diretório de trabalho. Para evitar erros de dependência do MSVC Runtime da versão 2.5.0
    em algumas máquinas Windows, clonamos o arquivo binário da versão 1.8.0 (altamente estável)
    para o nome da 2.5.0, garantindo compatibilidade total e sem downloads.
    """
    if platform.system().lower() != "windows":
        return

    try:
        api_root = Path(__file__).resolve().parent
        py_dir = Path(os.path.dirname(sys.executable))
        cwd_dir = Path(os.getcwd())

        src_1_8_0 = api_root / "openh264-1.8.0-win64.dll"

        # Se por alguma razão o 1.8.0 não existir localmente, tenta fazer download
        if not src_1_8_0.exists():
            url = "http://ciscobinary.openh264.org/openh264-1.8.0-win64.dll.bz2"
            _download_and_extract_dll(url, src_1_8_0)

        if not src_1_8_0.exists():
            print("⚠️ openh264 DLL de referência (1.8.0) não encontrada e download falhou.")
            return

        # Lista de nomes de DLL que o OpenCV costuma carregar nas diferentes versões
        dll_names_to_setup = [
            "openh264-1.8.0-win64.dll",
            "openh264-2.5.0-win64.dll",
            "openh264-2.6.0-win64.dll"
        ]

        for dll_name in dll_names_to_setup:
            # Destino na raiz da API (se for 2.5.0, clonamos o binário do 1.8.0 local para evitar bugs de MSVC runtime)
            api_dest = api_root / dll_name
            if not api_dest.exists() or api_dest.stat().st_size != src_1_8_0.stat().st_size:
                try:
                    shutil.copy2(src_1_8_0, api_dest)
                    print(f"✅ openh264 DLL ({dll_name}) criada na raiz da API.")
                except Exception as cp_err:
                    print(f"⚠️ Erro ao clonar {dll_name} na API root: {cp_err}")

            # Destino 1: Diretório do executável Python (Scripts)
            dest_dll1 = py_dir / dll_name
            if not dest_dll1.exists() or dest_dll1.stat().st_size != src_1_8_0.stat().st_size:
                try:
                    shutil.copy2(src_1_8_0, dest_dll1)
                    print(f"✅ openh264 DLL ({dll_name}) copiada para o diretório do Python: {dest_dll1}")
                except Exception as cp_err:
                    print(f"⚠️ Erro ao copiar {dll_name} para Python dir: {cp_err}")
                    if "Permission" in str(cp_err) or "Access" in str(cp_err):
                        print("   👉 DICA: A DLL está bloqueada por outro processo Python em segundo plano. Feche todos os processos Python e tente novamente!")

            # Destino 2: Diretório atual de trabalho (CWD)
            dest_dll2 = cwd_dir / dll_name
            if not dest_dll2.exists() or dest_dll2.stat().st_size != src_1_8_0.stat().st_size:
                try:
                    shutil.copy2(src_1_8_0, dest_dll2)
                    print(f"✅ openh264 DLL ({dll_name}) copiada para o diretório de trabalho: {dest_dll2}")
                except Exception as cp_err:
                    print(f"⚠️ Erro ao copiar {dll_name} para CWD: {cp_err}")
                    if "Permission" in str(cp_err) or "Access" in str(cp_err):
                        print("   👉 DICA: A DLL está bloqueada por outro processo Python em segundo plano. Feche todos os processos Python e tente novamente!")

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

if settings.DISABLE_LOGS:
    import logging
    logging.disable(logging.CRITICAL)

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Valida se serviços externos necessários (como o Ollama) estão online antes da API começar a aceitar conexões."""
    from app.services.ollama_message_service import OllamaMessageService
    from config.settings import settings
    import sys

    if settings.ENABLE_PERSONALIZED_MESSAGE:
        print("🔍 Verificando disponibilidade do Ollama...")
        ollama_service = OllamaMessageService()
        if not ollama_service.is_available():
            print("\n" + "="*80)
            print("❌ ERRO CRÍTICO DE INICIALIZAÇÃO: O serviço local do Ollama não está ativo!")
            print("👉 Certifique-se de iniciar o Ollama ('ollama serve') e baixar o modelo.")
            print("👉 Caso queira desativar as mensagens personalizadas geradas pelo LLM e iniciar a API offline,")
            print("   defina a seguinte flag no seu arquivo .env: ENABLE_PERSONALIZED_MESSAGE=False")
            print("="*80 + "\n")
            sys.exit(1)
        else:
            print("✅ Ollama verificado com sucesso e pronto para uso!")
    yield

app = FastAPI(title="API TCC - Detecção de Cadeiras (SOA)", version="1.0", lifespan=lifespan)
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

from fastapi.exceptions import RequestValidationError
from json import JSONDecodeError
from fastapi.responses import JSONResponse
import logging

app_logger = logging.getLogger("app.main")

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    try:
        body = await request.body()
        body_str = body.decode("utf-8", errors="replace")
    except Exception:
        body_str = "<indisponível>"
    app_logger.error("❌ Erro de validação de requisição (422) no path %s: %s | Corpo: %s", request.url.path, exc.errors(), body_str)
    from fastapi.exception_handlers import request_validation_exception_handler
    return await request_validation_exception_handler(request, exc)

@app.exception_handler(JSONDecodeError)
async def json_decode_exception_handler(request: Request, exc: JSONDecodeError):
    try:
        body = await request.body()
        body_str = body.decode("utf-8", errors="replace")
    except Exception:
        body_str = "<indisponível>"
    app_logger.error("❌ JSON inválido (400) no path %s: %s | Corpo: %s", request.url.path, str(exc), body_str)
    return JSONResponse(
        status_code=400,
        content={"detail": f"JSON inválido ou malformado: {str(exc)}"}
    )

app.include_router(system_router)
app.include_router(auth_router)
app.include_router(detection_router)
app.include_router(error_router)
app.include_router(feedback_router)

# Rota de status de Job alias global na raiz (GET /status/{job_id})
@app.get("/status/{job_id}", tags=["Detecção"])
async def get_job_status_root(job_id: str, response: Response):
    from app.routes.detection_routes import get_job_status
    return await get_job_status(job_id, response)


@app.get("/healthz", tags=["Health"])
async def healthz():
    """Health check endpoint to verify API online status."""
    return {"status": "ok"}


# A checagem de serviços foi migrada para o lifespan context manager acima.


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
    uvicorn_log_level = "critical" if settings.DISABLE_LOGS else "info"
    if settings.DEBUG:
        # Em desenvolvimento, prioriza hot reload.
        if not settings.DISABLE_LOGS:
            print("🔄 Iniciando API em modo debug com hot reload...")
        uvicorn.run(
            "main:app",
            host=settings.HOST,
            port=settings.PORT,
            reload=True,
            reload_includes=[".env"],
            log_level=uvicorn_log_level,
        )
    else:
        # Em produção, prioriza paralelismo com múltiplos workers.
        num_workers = max(2, multiprocessing.cpu_count() // 2)
        if not settings.DISABLE_LOGS:
            print(f"🚀 Iniciando API com {num_workers} workers para processamento paralelo...")
        uvicorn.run(
            "main:app",
            host=settings.HOST,
            port=settings.PORT,
            reload=False,
            workers=num_workers,
            log_level=uvicorn_log_level,
        )