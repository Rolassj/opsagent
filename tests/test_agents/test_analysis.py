"""Tests del Analysis Agent."""

import pandas as pd
import pytest
from opsagent.agents.analysis import analysis_node


# ── FIXTURES ──────────────────────────────────────────────────────────────────


@pytest.fixture
def estado_post_ingestion_manufactura():
    """Simula output del Ingestion Agent con datos de manufactura."""
    df = pd.DataFrame({
        "fecha": pd.to_datetime(["2025-01-01", "2025-01-02", "2025-01-03",
                                  "2025-01-04", "2025-01-05"]),
        "linea": ["L1", "L1", "L1", "L2", "L2"],
        "produccion_real": [450, 420, 480, 460, 440],
        "capacidad_teorica": [500, 500, 500, 500, 500],
        "defectos": [15, 18, 10, 12, 16],
        "tiempo_parada_min": [30, 45, 20, 25, 35],
        "horas_planificadas": [8, 8, 8, 8, 8],
    })
    return {
        "cleaned_data": df,
        "detected_domain": "manufactura",
        "raw_data": df,
        "file_metadata": {"nombre": "test.csv", "filas": 5, "columnas": list(df.columns)},
        "data_quality_report": {},
        "kpis": {},
        "anomalies": [],
        "trends": [],
        "diagnosis": "",
        "recommendations": [],
        "executive_summary": "",
        "messages": [],
        "processing_status": "analyzing",
        "error": None,
    }


@pytest.fixture
def estado_con_anomalia():
    """Datos con anomalia conocida: produccion=150 entre valores ~450."""
    df = pd.DataFrame({
        "fecha": pd.to_datetime([f"2025-01-{i+1:02d}" for i in range(10)]),
        "linea": ["L1"] * 10,
        "produccion_real": [450, 440, 460, 455, 150, 470, 445, 465, 450, 440],
        "capacidad_teorica": [500] * 10,
        "defectos": [15, 18, 10, 12, 10, 14, 16, 11, 13, 15],
        "tiempo_parada_min": [30, 35, 25, 28, 30, 22, 38, 20, 32, 28],
        "horas_planificadas": [8] * 10,
    })
    return {
        "cleaned_data": df,
        "detected_domain": "manufactura",
        "raw_data": df,
        "file_metadata": {},
        "data_quality_report": {},
        "kpis": {},
        "anomalies": [],
        "trends": [],
        "diagnosis": "",
        "recommendations": [],
        "executive_summary": "",
        "messages": [],
        "processing_status": "analyzing",
        "error": None,
    }


@pytest.fixture
def estado_uniforme():
    """Datos perfectamente uniformes — no debe detectar anomalias."""
    df = pd.DataFrame({
        "fecha": pd.to_datetime([f"2025-01-{i+1:02d}" for i in range(10)]),
        "linea": ["L1"] * 10,
        "produccion_real": [450] * 10,
        "capacidad_teorica": [500] * 10,
        "defectos": [15] * 10,
        "tiempo_parada_min": [30] * 10,
        "horas_planificadas": [8] * 10,
    })
    return {
        "cleaned_data": df,
        "detected_domain": "manufactura",
        "raw_data": df,
        "file_metadata": {},
        "data_quality_report": {},
        "kpis": {},
        "anomalies": [],
        "trends": [],
        "diagnosis": "",
        "recommendations": [],
        "executive_summary": "",
        "messages": [],
        "processing_status": "analyzing",
        "error": None,
    }


@pytest.fixture
def estado_con_tendencia():
    """Primera mitad produccion ~450, segunda mitad ~350 (descenso >10%)."""
    df = pd.DataFrame({
        "fecha": pd.to_datetime([f"2025-01-{i+1:02d}" for i in range(10)]),
        "linea": ["L1"] * 10,
        "produccion_real": [450, 455, 448, 460, 445, 350, 340, 355, 360, 345],
        "capacidad_teorica": [500] * 10,
        "defectos": [15] * 10,
        "tiempo_parada_min": [30] * 10,
        "horas_planificadas": [8] * 10,
    })
    return {
        "cleaned_data": df,
        "detected_domain": "manufactura",
        "raw_data": df,
        "file_metadata": {},
        "data_quality_report": {},
        "kpis": {},
        "anomalies": [],
        "trends": [],
        "diagnosis": "",
        "recommendations": [],
        "executive_summary": "",
        "messages": [],
        "processing_status": "analyzing",
        "error": None,
    }


# ── TESTS ─────────────────────────────────────────────────────────────────────


def test_analysis_calcula_kpis_manufactura(estado_post_ingestion_manufactura):
    resultado = analysis_node(estado_post_ingestion_manufactura)
    kpis = resultado["kpis"]
    assert "oee" in kpis
    assert isinstance(kpis["oee"], float)
    assert 0 < kpis["oee"] < 1


def test_analysis_calcula_tasa_defectos(estado_post_ingestion_manufactura):
    resultado = analysis_node(estado_post_ingestion_manufactura)
    kpis = resultado["kpis"]
    assert "tasa_defectos" in kpis
    assert 0 < kpis["tasa_defectos"] < 1


def test_analysis_detecta_anomalias(estado_con_anomalia):
    resultado = analysis_node(estado_con_anomalia)
    assert len(resultado["anomalies"]) >= 1
    # La anomalia de produccion_real=150 debe estar detectada
    campos_anomalos = [a["campo"] for a in resultado["anomalies"]]
    assert "produccion_real" in campos_anomalos


def test_analysis_clasifica_severidad(estado_con_anomalia):
    resultado = analysis_node(estado_con_anomalia)
    severidades_validas = {"critica", "alta", "media", "baja"}
    for anomalia in resultado["anomalies"]:
        assert "severidad" in anomalia
        assert anomalia["severidad"] in severidades_validas


def test_analysis_sin_anomalias(estado_uniforme):
    resultado = analysis_node(estado_uniforme)
    assert resultado["anomalies"] == []


def test_analysis_calcula_tendencias(estado_con_tendencia):
    resultado = analysis_node(estado_con_tendencia)
    assert len(resultado["trends"]) >= 1
    # produccion_real baja de ~450 a ~350 — debe ser descendente
    metricas_tendencia = [t["metrica"] for t in resultado["trends"]]
    assert "produccion_real" in metricas_tendencia
    for t in resultado["trends"]:
        if t["metrica"] == "produccion_real":
            assert t["direccion"] == "descendente"


def test_analysis_devuelve_estado_correcto(estado_post_ingestion_manufactura):
    resultado = analysis_node(estado_post_ingestion_manufactura)
    assert resultado["processing_status"] == "recommending"
    assert "kpis" in resultado
    assert "anomalies" in resultado
    assert "trends" in resultado
