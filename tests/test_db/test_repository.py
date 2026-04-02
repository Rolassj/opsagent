"""Tests del repository de diagnosticos (con mock de session)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from opsagent.api.schemas import DiagnoseResponse, RecommendationSchema
from opsagent.db.repository import _row_to_response


@pytest.fixture
def sample_diagnosis_row():
    """Simular un row de SQLAlchemy."""
    row = MagicMock()
    row.id = "test-id-123"
    row.user_id = "user-456"
    row.filename = "datos.csv"
    row.status = "done"
    row.detected_domain = "manufactura"
    row.executive_summary = "La planta opera al 72%."
    row.kpis = {"oee": 0.72}
    row.anomalies = [{"campo": "produccion", "severidad": "alta", "detalle": "Caida"}]
    row.trends = []
    row.diagnosis = "OEE bajo."
    row.recommendations = [{"prioridad": 1, "accion": "Mantener", "impacto": "Alto", "plazo": "2 sem"}]
    row.data_quality_report = {"filas_validas": 10}
    row.processing_time_seconds = 15.5
    row.error = None
    row.created_at = datetime(2026, 4, 1, 12, 0, 0)
    return row


def test_row_to_response_convierte_correctamente(sample_diagnosis_row):
    """_row_to_response convierte un row de DB a DiagnoseResponse."""
    result = _row_to_response(sample_diagnosis_row)
    assert isinstance(result, DiagnoseResponse)
    assert result.id == "test-id-123"
    assert result.detected_domain == "manufactura"
    assert result.filename == "datos.csv"
    assert result.created_at == "2026-04-01T12:00:00"


def test_row_to_response_con_error(sample_diagnosis_row):
    """_row_to_response maneja rows con error."""
    sample_diagnosis_row.status = "error"
    sample_diagnosis_row.error = "Pipeline fallo"
    result = _row_to_response(sample_diagnosis_row)
    assert result.status == "error"
    assert result.error == "Pipeline fallo"


def test_row_to_response_sin_created_at(sample_diagnosis_row):
    """_row_to_response maneja created_at None."""
    sample_diagnosis_row.created_at = None
    result = _row_to_response(sample_diagnosis_row)
    assert result.created_at is None
