"""Tests de integracion del grafo completo.

Verificar que el pipeline Ingestion -> Analysis -> Recommendations
funciona de punta a punta.
"""

from unittest.mock import patch, MagicMock

import numpy as np
import pandas as pd
import pytest

from opsagent.graph import build_graph
from opsagent.models import DiagnosticOutput, Recommendation
from opsagent.state import initial_state


# ── FIXTURES ──────────────────────────────────────────────────────────────────


@pytest.fixture
def df_manufactura():
    """DataFrame de manufactura valido."""
    return pd.DataFrame({
        "fecha": pd.to_datetime([f"2025-01-{i+1:02d}" for i in range(10)]),
        "linea": ["L1"] * 5 + ["L2"] * 5,
        "produccion_real": [450, 420, 480, 460, 440, 455, 430, 470, 445, 460],
        "capacidad_teorica": [500] * 10,
        "defectos": [15, 18, 10, 12, 16, 14, 20, 8, 13, 11],
        "tiempo_parada_min": [30, 45, 20, 25, 35, 28, 40, 15, 32, 22],
        "horas_planificadas": [8] * 10,
    })


@pytest.fixture
def df_datos_malos():
    """DataFrame con >50% filas nulas — debe rechazarse."""
    return pd.DataFrame({
        "col1": [np.nan] * 6 + [1, 2, 3, 4],
        "col2": [np.nan] * 6 + [5, 6, 7, 8],
        "col3": [np.nan] * 6 + [9, 10, 11, 12],
    })


@pytest.fixture
def mock_diagnostic():
    """DiagnosticOutput para mock del LLM."""
    return DiagnosticOutput(
        diagnosis="Diagnostico de prueba para pipeline completo.",
        recommendations=[
            Recommendation(prioridad=1, accion="Accion de prueba", impacto="Impacto de prueba", plazo="1 semana"),
        ],
        executive_summary="Resumen ejecutivo de prueba.",
    )


# ── TESTS CON MOCK ───────────────────────────────────────────────────────────


@patch("opsagent.agents.recommendations._get_llm")
def test_pipeline_completo_manufactura(mock_get_llm, df_manufactura, mock_diagnostic):
    """Pipeline completo: CSV manufactura -> diagnostico estructurado."""
    mock_structured = MagicMock()
    mock_structured.invoke.return_value = mock_diagnostic
    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value = mock_structured
    mock_get_llm.return_value = mock_llm

    graph = build_graph()
    state = initial_state(df_manufactura, "test_manufactura.csv")
    result = graph.invoke(state)

    assert result["processing_status"] == "done"
    assert result["detected_domain"] == "manufactura"
    assert result["kpis"]["oee"] > 0
    assert result["diagnosis"] != ""
    assert len(result["recommendations"]) >= 1
    assert result["executive_summary"] != ""


def test_pipeline_datos_malos_termina_temprano(df_datos_malos):
    """Datos con <50% filas validas — pipeline termina en ingestion."""
    graph = build_graph()
    state = initial_state(df_datos_malos, "basura.csv")
    result = graph.invoke(state)

    assert result["processing_status"] == "error"
    assert result["error"] is not None
    assert result["cleaned_data"] is None
    assert result["kpis"] == {}
    assert result["recommendations"] == []


# ── TESTS DE INTEGRACION ─────────────────────────────────────────────────────


@pytest.mark.integration
def test_integration_pipeline_completo_manufactura(df_manufactura):
    """Test con API real: pipeline completo con datos de manufactura."""
    graph = build_graph()
    state = initial_state(df_manufactura, "test_manufactura.csv")
    result = graph.invoke(state)

    assert result["processing_status"] == "done"
    assert result["diagnosis"] != ""
    assert len(result["recommendations"]) >= 1
    assert result["executive_summary"] != ""
