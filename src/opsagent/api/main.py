"""Aplicacion FastAPI principal de OpsAgent.

Para correr (desde salidas/opsagent/):
    uvicorn opsagent.api.main:app --reload --port 8000
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
from fastapi.middleware.cors import CORSMiddleware

from opsagent.api.routes import router
from opsagent.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicializar y cerrar recursos del servidor."""
    # Startup — DB failure is non-fatal: app falls back to in-memory mode
    if settings.db_enabled:
        try:
            from opsagent.db.session import init_db
            await init_db(settings.DATABASE_URL)
            logging.getLogger("opsagent").info("Database connected.")
        except Exception as exc:
            logging.getLogger("opsagent").warning(
                "Database init failed, running without persistence: %s", exc
            )
    yield
    # Shutdown
    if settings.db_enabled:
        try:
            from opsagent.db.session import close_db
            await close_db()
        except Exception:
            pass


app = FastAPI(
    title="OpsAgent API",
    description="API de diagnostico operativo con agentes IA para PyMEs industriales",
    version="0.2.0",
    lifespan=lifespan,
)

# CORS: en produccion, ALLOWED_ORIGINS contiene la URL del frontend Streamlit
# Ejemplo: ALLOWED_ORIGINS=https://opsagent-frontend.up.railway.app
_default_origins = "http://localhost:8501,http://127.0.0.1:8501"
_allowed_origins = os.environ.get("ALLOWED_ORIGINS", _default_origins).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _allowed_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
async def health_check():
    """Verificar que la API y su configuracion estan operativas."""
    status = {
        "status": "ok",
        "version": "0.2.0",
        "database": "connected" if settings.db_enabled else "not_configured",
        "auth": "enabled" if settings.auth_enabled else "disabled",
    }
    if not os.environ.get("ANTHROPIC_API_KEY"):
        status["status"] = "degraded"
        status["warning"] = "ANTHROPIC_API_KEY no configurada"
    return status
