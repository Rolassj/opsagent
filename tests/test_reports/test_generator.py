"""Tests del generador de reportes PDF."""

import pytest
from opsagent.reports.generator import generate_pdf, _format_kpi


@pytest.fixture
def sample_diagnosis():
    """Datos de diagnostico completos para generar PDF."""
    return {
        "id": "test-pdf-123",
        "status": "done",
        "detected_domain": "manufactura",
        "executive_summary": "La planta opera al 72% de eficiencia. Se requiere mantenimiento preventivo.",
        "kpis": {
            "oee": 0.72,
            "tasa_defectos": 0.034,
            "throughput_promedio": 450.0,
            "throughput_por_linea": {"L1": 460.0, "L2": 440.0},
        },
        "anomalies": [
            {"campo": "produccion_real", "severidad": "alta", "detalle": "Caida del 35% en dia 5"},
            {"campo": "defectos", "severidad": "media", "detalle": "Pico de defectos en L2"},
        ],
        "trends": [
            {"metrica": "produccion_real", "direccion": "descendente", "magnitud": 0.22},
        ],
        "diagnosis": "El OEE esta por debajo del benchmark.\n\nSe recomienda accion inmediata.",
        "recommendations": [
            {"prioridad": 1, "accion": "Mantenimiento preventivo", "impacto": "Reduce paradas 60%", "plazo": "2 semanas"},
            {"prioridad": 2, "accion": "Capacitacion operarios", "impacto": "Reduce defectos 30%", "plazo": "1 mes"},
        ],
        "data_quality_report": {
            "filas_originales": 100,
            "filas_validas": 95,
            "filas_eliminadas": 5,
            "problemas": ["5 filas duplicadas eliminadas"],
        },
        "processing_time_seconds": 17.3,
        "filename": "datos_planta.csv",
    }


def test_generate_pdf_returns_bytes(sample_diagnosis):
    """generate_pdf retorna bytes no vacios."""
    result = generate_pdf(sample_diagnosis, filename="datos.csv")
    assert isinstance(result, bytes)
    assert len(result) > 0


def test_generate_pdf_starts_with_pdf_header(sample_diagnosis):
    """El output comienza con el magic number de PDF."""
    result = generate_pdf(sample_diagnosis)
    assert result[:5] == b"%PDF-"


def test_generate_pdf_minimal_data():
    """Genera PDF incluso con datos minimos."""
    minimal = {
        "status": "done",
        "detected_domain": "desconocido",
        "executive_summary": "",
        "kpis": {},
        "anomalies": [],
        "trends": [],
        "diagnosis": "",
        "recommendations": [],
        "data_quality_report": {},
        "processing_time_seconds": 0,
    }
    result = generate_pdf(minimal)
    assert result[:5] == b"%PDF-"


def test_generate_pdf_with_error_status():
    """Genera PDF incluso cuando el status es error."""
    error_data = {
        "status": "error",
        "detected_domain": "desconocido",
        "executive_summary": "",
        "kpis": {},
        "anomalies": [],
        "trends": [],
        "diagnosis": "",
        "recommendations": [],
        "data_quality_report": {},
        "processing_time_seconds": 0,
        "error": "Pipeline fallo",
    }
    result = generate_pdf(error_data)
    assert isinstance(result, bytes)
    assert len(result) > 0


def test_format_kpi_percentage():
    """_format_kpi formatea decimales < 1 como porcentaje."""
    assert _format_kpi(0.72) == "72.0%"
    assert _format_kpi(0.034) == "3.4%"


def test_format_kpi_large_number():
    """_format_kpi formatea numeros >= 1 con 2 decimales."""
    assert _format_kpi(450.0) == "450.00"


def test_format_kpi_string():
    """_format_kpi retorna strings sin cambios."""
    assert _format_kpi("L1") == "L1"


def test_pdf_endpoint(sample_diagnosis):
    """GET /diagnose/{id}/pdf retorna PDF valido."""
    from unittest.mock import patch
    from fastapi.testclient import TestClient
    from opsagent.api.main import app
    from opsagent.auth.dependencies import get_current_user

    app.dependency_overrides[get_current_user] = lambda: "test-user"
    client = TestClient(app)

    # Primero crear un diagnostico
    mock_result = {
        "processing_status": "done",
        "detected_domain": "manufactura",
        "executive_summary": "Test summary.",
        "kpis": {"oee": 0.72},
        "anomalies": [],
        "trends": [],
        "diagnosis": "Test diagnosis.",
        "recommendations": [{"prioridad": 1, "accion": "Test", "impacto": "Alto", "plazo": "1 sem"}],
        "data_quality_report": {"filas_originales": 10, "filas_validas": 10, "filas_eliminadas": 0, "problemas": []},
        "error": None,
    }
    csv_bytes = b"fecha,linea,produccion\n2024-01-01,L1,450\n"

    with patch("opsagent.api.routes._run_pipeline", return_value=mock_result):
        post_resp = client.post("/diagnose", files={"file": ("d.csv", csv_bytes, "text/csv")})
    diagnose_id = post_resp.json()["id"]

    # Descargar PDF
    pdf_resp = client.get(f"/diagnose/{diagnose_id}/pdf")
    assert pdf_resp.status_code == 200
    assert pdf_resp.headers["content-type"] == "application/pdf"
    assert pdf_resp.content[:5] == b"%PDF-"
