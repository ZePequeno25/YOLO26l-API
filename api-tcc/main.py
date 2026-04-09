from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.system_routes import router as system_router
from app.routes.auth_routes import router as auth_router
from app.routes.detection_routes import router as detection_router
from app.routes.error_routes import router as error_router

app = FastAPI(title="API TCC - Detecção de Cadeiras (SOA)", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(system_router)
app.include_router(auth_router)
app.include_router(detection_router)
app.include_router(error_router)


if __name__ == "__main__":
    import uvicorn
    from config.settings import settings
    
    uvicorn.run(
        "main:app",                    # ← Isso resolve o warning
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,         # reload continua funcionando
        log_level="info"
    )