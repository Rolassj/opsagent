"""Endpoints de la API REST de OpsAgent."""

import io
import uuid
import asyncio
import time
import logging
from typing import Annotated, Optional

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from opsagent.api.schemas import DiagnoseResponse
from opsagent.auth.dependencies import get_current_user
from opsagent.config import settings
from opsagent.graph import build_graph
from opsagent.reports.generator import generate_pdf
from opsagent.state import initial_state

logger = logging.getLogger("opsagent.api")

router = APIRouter()

# Fallback in-memory si DB no esta configurada (modo desarrollo)
_diagnose_store: dict[str, DiagnoseResponse] = {}


def _parse_file(content: bytes, filename: str) -> pd.DataFrame:
    """Parsear bytes de archivo a DataFrame. Soporta CSV y Excel."""
    name = filename.lower()
    if name.endswith(".csv"):
        return pd.read_csv(io.BytesIO(content))
    elif name.endswith((".xlsx", ".xls")):
        return pd.read_excel(io.BytesIO(content))
    else:
        raise ValueError(f"Formato no soportado: {filename}. Usar CSV o Excel.")


def _run_pipeline(df: pd.DataFrame, filename: str) -> dict:
    """Ejecutar pipeline LangGraph (sincrono). Llamar en executor."""
    graph = build_graph()
    state = initial_state(df, filename)
    return graph.invoke(state)


async def _get_db_session() -> Optional[AsyncSession]:
    """Obtener session de DB si esta configurada e inicializada, o None."""
    if not settings.db_enabled:
        return None
    from opsagent.db.session import get_session, async_session_factory
    if async_session_factory is None:
        return None
    async for session in get_session():
        return session
    return None


@router.post("/diagnose", response_model=DiagnoseResponse)
async def create_diagnose(
    file: Annotated[UploadFile, File(description="CSV o Excel con datos operativos")],
    user_id: str = Depends(get_current_user),
):
    """Ejecutar diagnostico operativo sobre un archivo subido."""
    content = await file.read()

    loop = asyncio.get_running_loop()
    try:
        df = await loop.run_in_executor(None, _parse_file, content, file.filename)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Error al leer el archivo: {e}")

    start = time.time()
    try:
        result = await loop.run_in_executor(None, _run_pipeline, df, file.filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en el pipeline: {e}")
    elapsed = time.time() - start

    diagnose_id = str(uuid.uuid4())

    try:
        response = DiagnoseResponse(
            id=diagnose_id,
            status=result.get("processing_status", "done"),
            detected_domain=result.get("detected_domain", "desconocido"),
            executive_summary=result.get("executive_summary", ""),
            kpis=result.get("kpis", {}),
            anomalies=result.get("anomalies", []),
            trends=result.get("trends", []),
            diagnosis=result.get("diagnosis", ""),
            recommendations=result.get("recommendations", []),
            data_quality_report=result.get("data_quality_report", {}),
            processing_time_seconds=round(elapsed, 2),
            error=result.get("error"),
            filename=file.filename,
        )
    except Exception as e:
        logger.error("Error al construir DiagnoseResponse: %s | result keys: %s", e, list(result.keys()))
        raise HTTPException(status_code=500, detail=f"Error al procesar resultado del pipeline: {e}")

    # Persistir en DB o fallback in-memory
    session = await _get_db_session()
    if session:
        from opsagent.db.repository import save_diagnosis
        try:
            await save_diagnosis(session, response, user_id, file.filename)
        except Exception as e:
            logger.error("Error al guardar en DB, usando fallback in-memory: %s", e)
            _diagnose_store[diagnose_id] = response
    else:
        _diagnose_store[diagnose_id] = response

    return response


@router.get("/diagnose/{diagnose_id}", response_model=DiagnoseResponse)
async def get_diagnose(
    diagnose_id: str,
    user_id: str = Depends(get_current_user),
):
    """Obtener resultado de un diagnostico anterior por ID."""
    session = await _get_db_session()
    if session:
        from opsagent.db.repository import get_diagnosis
        result = await get_diagnosis(session, diagnose_id, user_id)
        if result is None:
            raise HTTPException(status_code=404, detail=f"Diagnostico '{diagnose_id}' no encontrado.")
        return result
    else:
        if diagnose_id not in _diagnose_store:
            raise HTTPException(status_code=404, detail=f"Diagnostico '{diagnose_id}' no encontrado.")
        return _diagnose_store[diagnose_id]


@router.get("/diagnoses", response_model=list[DiagnoseResponse])
async def list_diagnoses(
    user_id: str = Depends(get_current_user),
):
    """Listar diagnosticos del usuario autenticado."""
    session = await _get_db_session()
    if session:
        from opsagent.db.repository import get_user_diagnoses
        return await get_user_diagnoses(session, user_id)
    else:
        return list(_diagnose_store.values())


@router.get("/diagnose/{diagnose_id}/pdf")
async def download_diagnose_pdf(
    diagnose_id: str,
    user_id: str = Depends(get_current_user),
):
    """Descargar reporte PDF de un diagnostico."""
    # Reusar la logica de get_diagnose para obtener el resultado
    session = await _get_db_session()
    if session:
        from opsagent.db.repository import get_diagnosis
        result = await get_diagnosis(session, diagnose_id, user_id)
        if result is None:
            raise HTTPException(status_code=404, detail=f"Diagnostico '{diagnose_id}' no encontrado.")
    else:
        if diagnose_id not in _diagnose_store:
            raise HTTPException(status_code=404, detail=f"Diagnostico '{diagnose_id}' no encontrado.")
        result = _diagnose_store[diagnose_id]

    data = result.model_dump() if hasattr(result, "model_dump") else result
    pdf_bytes = generate_pdf(data, filename=data.get("filename", ""))

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="diagnostico-{diagnose_id[:8]}.pdf"'},
    )
