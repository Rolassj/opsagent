"""Tests del Recommendations Agent."""

from unittest.mock import patch, MagicMock

import pytest
from opsagent.agents.recommendations import recommendations_node, _build_context_message
from opsagent.models import DiagnosticOutput, Recommendation


# ── FIXTURES ──────────────────────────────────────────────────────────────────


@pytest.fixture
def estado_post_analysis_manufactura():
    """Estado completo post-analysis con datos de manufactura."""
    return {
        "raw_data": None,
        "file_metadata": {"nombre": "manufactura_enero.csv", "filas": 30, "columnas": []},
        "cleaned_data": None,
        "data_quality_report": {
            "filas_originales": 30,
            "filas_validas": 28,
            "filas_eliminadas": 2,
            "problemas": ["2 valores nulos aislados en columnas numericas"],
        },
        "detected_domain": "manufactura",
        "kpis": {
            "oee": 0.7960,
            "tasa_defectos": 0.0321,
            "throughput_promedio": 447.5,
            "throughput_por_linea": {"L1": 445.0, "L2": 450.0},
        },
        "anomalies": [
            {"campo": "produccion_real", "indice": 9, "valor": 150.0, "severidad": "critica",
             "detalle": "produccion_real=150.0 esta a 4.2 std de la media (447.5)"},
            {"campo": "defectos", "indice": 19, "valor": 85.0, "severidad": "critica",
             "detalle": "defectos=85.0 esta a 5.1 std de la media (15.2)"},
            {"campo": "tiempo_parada_min", "indice": 24, "valor": 300.0, "severidad": "critica",
             "detalle": "tiempo_parada_min=300.0 esta a 6.3 std de la media (32.1)"},
        ],
        "trends": [
            {"metrica": "produccion_real", "direccion": "descendente", "magnitud": 0.12},
        ],
        "diagnosis": "",
        "recommendations": [],
        "executive_summary": "",
        "messages": [],
        "processing_status": "recommending",
        "error": None,
    }


@pytest.fixture
def estado_sin_datos():
    """Estado sin KPIs ni anomalias."""
    return {
        "raw_data": None,
        "file_metadata": {},
        "cleaned_data": None,
        "data_quality_report": {},
        "detected_domain": "desconocido",
        "kpis": {},
        "anomalies": [],
        "trends": [],
        "diagnosis": "",
        "recommendations": [],
        "executive_summary": "",
        "messages": [],
        "processing_status": "recommending",
        "error": None,
    }


@pytest.fixture
def mock_diagnostic_output():
    """DiagnosticOutput de ejemplo para mock."""
    return DiagnosticOutput(
        diagnosis="La planta opera a un OEE del 79.6%, por debajo del benchmark industrial del 85%. "
                  "Se detectaron 3 anomalias criticas que afectan produccion, calidad y disponibilidad.",
        recommendations=[
            Recommendation(
                prioridad=1,
                accion="Investigar causa raiz de la parada de 300 minutos (5 horas) registrada el dia 25",
                impacto="Eliminar paradas no planificadas puede mejorar disponibilidad en un 10-15%",
                plazo="1 semana",
            ),
            Recommendation(
                prioridad=2,
                accion="Revisar proceso de control de calidad: 85 defectos en un dia indica falla sistematica",
                impacto="Reducir tasa de defectos del 3.2% al <2%",
                plazo="2 semanas",
            ),
            Recommendation(
                prioridad=3,
                accion="Analizar causa de la caida de produccion a 150 unidades (vs promedio 447)",
                impacto="Estabilizar produccion diaria y reducir variabilidad",
                plazo="1 semana",
            ),
        ],
        executive_summary="Su planta produce al 79.6% de su capacidad. Hubo 3 incidentes criticos "
                          "que requieren atencion inmediata. Corrigiendo las paradas no planificadas "
                          "y los picos de defectos, puede alcanzar el 85% en 2-3 semanas.",
    )


# ── TESTS UNITARIOS ──────────────────────────────────────────────────────────


def test_recommendations_sin_datos_retorna_error(estado_sin_datos):
    """Sin KPIs ni anomalias, debe retornar error."""
    resultado = recommendations_node(estado_sin_datos)
    assert resultado["processing_status"] == "error"
    assert resultado["error"] is not None
    assert resultado["diagnosis"] == ""
    assert resultado["recommendations"] == []


def test_build_context_message_manufactura(estado_post_analysis_manufactura):
    """El mensaje de contexto debe incluir KPIs, anomalias y tendencias."""
    msg = _build_context_message(estado_post_analysis_manufactura)
    assert "manufactura" in msg.lower()
    assert "oee" in msg.lower()
    assert "0.7960" in msg
    assert "CRITICA" in msg
    assert "produccion_real" in msg
    assert "descendente" in msg


def test_build_context_message_sin_anomalias():
    """Sin anomalias, el mensaje debe indicarlo."""
    state = {
        "detected_domain": "manufactura",
        "file_metadata": {},
        "data_quality_report": {},
        "kpis": {"oee": 0.88},
        "anomalies": [],
        "trends": [],
    }
    msg = _build_context_message(state)
    assert "Ninguna detectada" in msg


@patch("opsagent.agents.recommendations._get_llm")
def test_recommendations_genera_diagnostico(mock_get_llm, estado_post_analysis_manufactura, mock_diagnostic_output):
    """Con mock del LLM, debe generar diagnostico estructurado."""
    mock_structured = MagicMock()
    mock_structured.invoke.return_value = mock_diagnostic_output
    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value = mock_structured
    mock_get_llm.return_value = mock_llm

    resultado = recommendations_node(estado_post_analysis_manufactura)

    assert resultado["processing_status"] == "done"
    assert resultado["diagnosis"] != ""
    assert "OEE" in resultado["diagnosis"]
    assert len(resultado["recommendations"]) == 3
    assert resultado["executive_summary"] != ""


@patch("opsagent.agents.recommendations._get_llm")
def test_recommendations_prioriza_correctamente(mock_get_llm, estado_post_analysis_manufactura, mock_diagnostic_output):
    """Las recomendaciones deben tener prioridad ordenada."""
    mock_structured = MagicMock()
    mock_structured.invoke.return_value = mock_diagnostic_output
    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value = mock_structured
    mock_get_llm.return_value = mock_llm

    resultado = recommendations_node(estado_post_analysis_manufactura)
    recs = resultado["recommendations"]

    assert recs[0]["prioridad"] == 1
    assert recs[1]["prioridad"] == 2
    assert recs[2]["prioridad"] == 3


@patch("opsagent.agents.recommendations._get_llm")
def test_recommendations_formato_recomendacion(mock_get_llm, estado_post_analysis_manufactura, mock_diagnostic_output):
    """Cada recomendacion debe tener los campos requeridos."""
    mock_structured = MagicMock()
    mock_structured.invoke.return_value = mock_diagnostic_output
    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value = mock_structured
    mock_get_llm.return_value = mock_llm

    resultado = recommendations_node(estado_post_analysis_manufactura)

    for rec in resultado["recommendations"]:
        assert "prioridad" in rec
        assert "accion" in rec
        assert "impacto" in rec
        assert "plazo" in rec
        assert isinstance(rec["prioridad"], int)


@patch("opsagent.agents.recommendations._get_llm")
def test_recommendations_maneja_error_api(mock_get_llm, estado_post_analysis_manufactura):
    """Si la API de Claude falla, debe retornar error gracefully."""
    mock_llm = MagicMock()
    mock_llm.with_structured_output.side_effect = Exception("API timeout")
    mock_get_llm.return_value = mock_llm

    resultado = recommendations_node(estado_post_analysis_manufactura)

    assert resultado["processing_status"] == "error"
    assert "Error al generar recomendaciones" in resultado["error"]


@patch("opsagent.agents.recommendations._get_llm")
def test_recommendations_resumen_no_vacio(mock_get_llm, estado_post_analysis_manufactura, mock_diagnostic_output):
    """El resumen ejecutivo no debe estar vacio."""
    mock_structured = MagicMock()
    mock_structured.invoke.return_value = mock_diagnostic_output
    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value = mock_structured
    mock_get_llm.return_value = mock_llm

    resultado = recommendations_node(estado_post_analysis_manufactura)

    assert resultado["executive_summary"] != ""
    assert len(resultado["executive_summary"]) > 20


# ── TESTS DE INTEGRACION ─────────────────────────────────────────────────────


@pytest.mark.integration
def test_integration_recommendations_manufactura(estado_post_analysis_manufactura):
    """Test con API real: genera diagnostico coherente para manufactura."""
    resultado = recommendations_node(estado_post_analysis_manufactura)

    assert resultado["processing_status"] == "done"
    assert resultado["diagnosis"] != ""
    assert len(resultado["recommendations"]) >= 2
    assert resultado["executive_summary"] != ""
    for rec in resultado["recommendations"]:
        assert "prioridad" in rec
        assert "accion" in rec
