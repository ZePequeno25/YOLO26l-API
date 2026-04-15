from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.routes.system_routes import router as system_router
from app.routes.auth_routes import router as auth_router
from app.routes.detection_routes import router as detection_router
from app.routes.error_routes import router as error_router
from app.routes.feedback_routes import router as feedback_router
from app.core.not_found_guard import NotFoundGuard
from app.core.request_protection import RequestProtectionMiddleware
from config.settings import settings

app = FastAPI(title="API TCC - Detecção de Cadeiras (SOA)", version="1.0")

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
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn, multiprocessing

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