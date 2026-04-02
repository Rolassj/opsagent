"""Operaciones CRUD para diagnosticos."""

from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from opsagent.db.models import Diagnosis
from opsagent.api.schemas import DiagnoseResponse


async def save_diagnosis(session: AsyncSession, response: DiagnoseResponse, user_id: str, filename: str) -> None:
    """Guardar un diagnostico en la base de datos."""
    diagnosis = Diagnosis(
        id=response.id,
        user_id=user_id,
        filename=filename,
        status=response.status,
        detected_domain=response.detected_domain,
        executive_summary=response.executive_summary,
        kpis=response.kpis,
        anomalies=response.anomalies,
        trends=response.trends,
        diagnosis=response.diagnosis,
        recommendations=[r.model_dump() for r in response.recommendations],
        data_quality_report=response.data_quality_report,
        processing_time_seconds=response.processing_time_seconds,
        error=response.error,
    )
    session.add(diagnosis)
    await session.commit()


async def get_diagnosis(session: AsyncSession, diagnose_id: str, user_id: str) -> DiagnoseResponse | None:
    """Obtener un diagnostico por ID, solo si pertenece al usuario."""
    result = await session.execute(
        select(Diagnosis).where(Diagnosis.id == diagnose_id, Diagnosis.user_id == user_id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        return None
    return _row_to_response(row)


async def get_user_diagnoses(session: AsyncSession, user_id: str, limit: int = 50) -> list[DiagnoseResponse]:
    """Listar diagnosticos de un usuario, ordenados por fecha descendente."""
    result = await session.execute(
        select(Diagnosis)
        .where(Diagnosis.user_id == user_id)
        .order_by(Diagnosis.created_at.desc())
        .limit(limit)
    )
    rows = result.scalars().all()
    return [_row_to_response(row) for row in rows]


def _row_to_response(row: Diagnosis) -> DiagnoseResponse:
    """Convertir un row de SQLAlchemy a DiagnoseResponse."""
    return DiagnoseResponse(
        id=row.id,
        status=row.status,
        detected_domain=row.detected_domain,
        executive_summary=row.executive_summary,
        kpis=row.kpis,
        anomalies=row.anomalies,
        trends=row.trends,
        diagnosis=row.diagnosis,
        recommendations=row.recommendations,
        data_quality_report=row.data_quality_report,
        processing_time_seconds=row.processing_time_seconds,
        error=row.error,
        filename=row.filename,
        created_at=row.created_at.isoformat() if row.created_at else None,
    )
