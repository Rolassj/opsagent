"""Tests para los endpoints de la API FastAPI de OpsAgent."""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from opsagent.api.main import app
from opsagent.auth.dependencies import get_current_user

# Override de auth para tests: todos los requests son de "test-user"
app.dependency_overrides[get_current_user] = lambda: "test-user"

client = TestClient(app)


# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture
def mock_pipeline_result():
    """Resultado simulado del pipeline para evitar llamadas reales a Claude."""
    return {
        "processing_status": "done",
        "detected_domain": "manufactura",
        "executive_summary": "La planta opera al 72% de eficiencia.",
        "kpis": {"oee": 0.72, "tasa_defectos": 0.034},
        "anomalies": [{"campo": "produccion", "severidad": "alta", "detalle": "Caida del 35%"}],
        "trends": [{"metrica": "oee", "direccion": "descendente", "magnitud": 0.08}],
        "diagnosis": "El OEE esta por debajo del benchmark industrial del 85%.",
        "recommendations": [{"prioridad": 1, "accion": "Mantenimiento preventivo", "impacto": "Reduce paradas 60%", "plazo": "2 semanas"}],
        "data_quality_report": {"filas_originales": 10, "filas_validas": 10, "filas_eliminadas": 0, "problemas": []},
        "error": None,
    }


@pytest.fixture
def csv_manufactura_bytes():
    """CSV sintetico de manufactura como bytes."""
    content = (
        "fecha,linea,produccion,defectos,horas_planificadas,paradas,capacidad\n"
        "2024-01-01,L1,450,12,8,0.5,500\n"
        "2024-01-02,L1,480,8,8,0.3,500\n"
        "2024-01-03,L2,420,15,8,1.0,500\n"
    )
    return content.encode("utf-8")


# ── Tests: GET /health ────────────────────────────────────────────────────


def test_health_check_ok():
    """GET /health retorna 200 cuando la API key esta configurada."""
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-ant-test"}):
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_health_check_sin_api_key():
    """GET /health retorna degraded cuando falta ANTHROPIC_API_KEY."""
    import os
    original = os.environ.pop("ANTHROPIC_API_KEY", None)
    try:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "degraded"
    finally:
        if original is not None:
            os.environ["ANTHROPIC_API_KEY"] = original


# ── Tests: POST /diagnose ─────────────────────────────────────────────────


def test_post_diagnose_exitoso(csv_manufactura_bytes, mock_pipeline_result):
    """POST /diagnose con CSV valido retorna diagnostico completo."""
    with patch("opsagent.api.routes._run_pipeline", return_value=mock_pipeline_result):
        response = client.post(
            "/diagnose",
            files={"file": ("datos.csv", csv_manufactura_bytes, "text/csv")},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "done"
    assert data["detected_domain"] == "manufactura"
    assert "id" in data
    assert "kpis" in data
    assert len(data["recommendations"]) == 1


def test_post_diagnose_retorna_id_unico(csv_manufactura_bytes, mock_pipeline_result):
    """Dos llamadas a POST /diagnose retornan IDs distintos."""
    with patch("opsagent.api.routes._run_pipeline", return_value=mock_pipeline_result):
        r1 = client.post("/diagnose", files={"file": ("a.csv", csv_manufactura_bytes, "text/csv")})
        r2 = client.post("/diagnose", files={"file": ("b.csv", csv_manufactura_bytes, "text/csv")})
    assert r1.json()["id"] != r2.json()["id"]


def test_post_diagnose_formato_no_soportado():
    """POST /diagnose con formato invalido retorna 422."""
    response = client.post(
        "/diagnose",
        files={"file": ("datos.txt", b"no es un csv", "text/plain")},
    )
    assert response.status_code == 422


def test_post_diagnose_sin_archivo():
    """POST /diagnose sin archivo retorna 422."""
    response = client.post("/diagnose")
    assert response.status_code == 422


# ── Tests: GET /diagnose/{id} ─────────────────────────────────────────────


def test_get_diagnose_por_id(csv_manufactura_bytes, mock_pipeline_result):
    """GET /diagnose/{id} retorna el diagnostico guardado."""
    with patch("opsagent.api.routes._run_pipeline", return_value=mock_pipeline_result):
        post_resp = client.post("/diagnose", files={"file": ("d.csv", csv_manufactura_bytes, "text/csv")})
    diagnose_id = post_resp.json()["id"]

    get_resp = client.get(f"/diagnose/{diagnose_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == diagnose_id


def test_get_diagnose_id_inexistente():
    """GET /diagnose/{id} con ID desconocido retorna 404."""
    response = client.get("/diagnose/id-que-no-existe-123")
    assert response.status_code == 404


# ── Tests: GET /diagnoses ────────────────────────────────────────────────


def test_get_diagnoses_lista_vacia():
    """GET /diagnoses retorna lista vacia si no hay diagnosticos."""
    response = client.get("/diagnoses")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_diagnoses_con_resultados(csv_manufactura_bytes, mock_pipeline_result):
    """GET /diagnoses retorna diagnosticos despues de crear uno."""
    with patch("opsagent.api.routes._run_pipeline", return_value=mock_pipeline_result):
        client.post("/diagnose", files={"file": ("d.csv", csv_manufactura_bytes, "text/csv")})
    response = client.get("/diagnoses")
    assert response.status_code == 200
    assert len(response.json()) >= 1
