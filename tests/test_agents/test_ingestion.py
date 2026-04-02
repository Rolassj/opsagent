"""Tests del Ingestion Agent."""

import numpy as np
import pandas as pd
import pytest
from opsagent.agents.ingestion import ingestion_node
from opsagent.state import initial_state


# ── FIXTURES ──────────────────────────────────────────────────────────────────


@pytest.fixture
def datos_manufactura():
    return pd.DataFrame({
        "fecha": ["2025-01-01", "2025-01-02", "2025-01-03"],
        "linea": ["L1", "L1", "L2"],
        "produccion_real": [450, 420, 480],
        "capacidad_teorica": [500, 500, 500],
        "defectos": [15, 18, 10],
        "tiempo_parada_min": [30, 45, 20],
        "horas_planificadas": [8, 8, 8],
    })


@pytest.fixture
def estado_manufactura(datos_manufactura):
    return initial_state(datos_manufactura, "test_manufactura.csv")


@pytest.fixture
def datos_logistica():
    return pd.DataFrame({
        "pedido_id": ["PED-001", "PED-002", "PED-003"],
        "fecha_pedido": ["2025-01-03", "2025-01-05", "2025-01-08"],
        "fecha_entrega_prometida": ["2025-01-06", "2025-01-08", "2025-01-11"],
        "fecha_entrega_real": ["2025-01-06", "2025-01-08", "2025-01-13"],
        "items_pedidos": [50, 30, 45],
        "items_entregados": [50, 30, 45],
        "almacen": ["A1", "A1", "A2"],
    })


@pytest.fixture
def estado_logistica(datos_logistica):
    return initial_state(datos_logistica, "test_logistica.csv")


@pytest.fixture
def datos_con_nulos():
    return pd.DataFrame({
        "fecha": ["2025-01-01", "2025-01-02", "2025-01-03", "2025-01-04"],
        "linea": ["L1", "L1", None, "L2"],
        "produccion_real": [450, np.nan, 480, 460],
        "capacidad_teorica": [500, 500, 500, 500],
        "defectos": [15, 18, np.nan, 10],
        "tiempo_parada_min": [30, 45, 20, 25],
        "horas_planificadas": [8, 8, 8, 8],
    })


@pytest.fixture
def estado_con_nulos(datos_con_nulos):
    return initial_state(datos_con_nulos, "test_nulos.csv")


# ── TESTS ─────────────────────────────────────────────────────────────────────


def test_ingestion_detecta_dominio_manufactura(estado_manufactura):
    resultado = ingestion_node(estado_manufactura)
    assert resultado["detected_domain"] == "manufactura"


def test_ingestion_detecta_dominio_logistica(estado_logistica):
    resultado = ingestion_node(estado_logistica)
    assert resultado["detected_domain"] == "logistica"


def test_ingestion_limpia_valores_nulos(estado_con_nulos):
    resultado = ingestion_node(estado_con_nulos)
    report = resultado["data_quality_report"]
    assert report["filas_validas"] <= report["filas_originales"]
    # Debe reportar nulos aislados en problemas
    assert len(report["problemas"]) > 0


def test_ingestion_genera_reporte_calidad(estado_manufactura):
    resultado = ingestion_node(estado_manufactura)
    report = resultado["data_quality_report"]
    assert "filas_originales" in report
    assert "filas_validas" in report
    assert "filas_eliminadas" in report
    assert "problemas" in report
    assert isinstance(report["problemas"], list)


def test_ingestion_devuelve_estado_correcto(estado_manufactura):
    resultado = ingestion_node(estado_manufactura)
    assert "cleaned_data" in resultado
    assert "data_quality_report" in resultado
    assert "detected_domain" in resultado
    assert "processing_status" in resultado
    assert resultado["processing_status"] == "analyzing"
    assert resultado["cleaned_data"] is not None


def test_ingestion_rechaza_datos_muy_malos():
    # >50% de filas son puro NaN
    df = pd.DataFrame({
        "col1": [np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, 1, 2, 3, 4],
        "col2": [np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, 5, 6, 7, 8],
        "col3": [np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, 9, 10, 11, 12],
    })
    state = initial_state(df, "basura.csv")
    resultado = ingestion_node(state)
    assert resultado["processing_status"] == "error"
    assert resultado["error"] is not None
    assert resultado["cleaned_data"] is None


def test_ingestion_normaliza_columnas():
    df = pd.DataFrame({
        "Fecha Pedido": ["2025-01-01"],
        "PRODUCCION Real": [450],
        "Capacidad Teorica": [500],
    })
    state = initial_state(df, "test_cols.csv")
    resultado = ingestion_node(state)
    columnas = list(resultado["cleaned_data"].columns)
    for col in columnas:
        assert col == col.lower(), f"Columna '{col}' no esta en lowercase"
        assert " " not in col, f"Columna '{col}' tiene espacios"
