"""Tests para mapeo inteligente de columnas y herramientas de datos."""

import pandas as pd
import pytest
from opsagent.tools.data_tools import (
    normalizar_columnas,
    mapear_columnas,
    detectar_dominio,
    limpiar_dataframe,
)


# ── Tests: Mapeo inteligente de columnas ─────────────────────────────────


class TestMapeoColumnas:

    def test_mapea_alias_produccion(self):
        """'output' se mapea a 'produccion_real'."""
        df = pd.DataFrame({"output": [450, 480], "defectos": [15, 10]})
        result = mapear_columnas(df)
        assert "produccion_real" in result.columns

    def test_mapea_multiples_alias(self):
        """Mapea multiples columnas a la vez."""
        df = pd.DataFrame({
            "prod": [450],
            "scrap": [15],
            "downtime": [30],
            "cap_max": [500],
            "horas_plan": [8],
        })
        result = mapear_columnas(df)
        assert "produccion_real" in result.columns
        assert "defectos" in result.columns
        assert "tiempo_parada_min" in result.columns
        assert "capacidad_teorica" in result.columns
        assert "horas_planificadas" in result.columns

    def test_no_sobreescribe_existente(self):
        """Si 'produccion_real' ya existe, no renombra 'output' a 'produccion_real'."""
        df = pd.DataFrame({
            "produccion_real": [450],
            "output": [460],
        })
        result = mapear_columnas(df)
        assert "output" in result.columns  # No se renombro
        assert "produccion_real" in result.columns

    def test_columnas_canonicas_sin_cambios(self):
        """Columnas que ya son canonicas no se tocan."""
        df = pd.DataFrame({
            "produccion_real": [450],
            "defectos": [15],
            "linea": ["L1"],
        })
        result = mapear_columnas(df)
        assert list(result.columns) == ["produccion_real", "defectos", "linea"]

    def test_columnas_desconocidas_sin_cambios(self):
        """Columnas que no matchean ningun alias se mantienen."""
        df = pd.DataFrame({
            "col_random": [1],
            "otra_columna": [2],
        })
        result = mapear_columnas(df)
        assert list(result.columns) == ["col_random", "otra_columna"]

    def test_mapeo_logistica(self):
        """Alias de logistica se mapean correctamente."""
        df = pd.DataFrame({
            "qty_ordered": [50],
            "qty_delivered": [48],
            "due_date": ["2025-01-10"],
            "ship_date": ["2025-01-09"],
        })
        result = mapear_columnas(df)
        assert "items_pedidos" in result.columns
        assert "items_entregados" in result.columns
        assert "fecha_entrega_prometida" in result.columns
        assert "fecha_entrega_real" in result.columns

    def test_mapeo_preserva_datos(self):
        """Los datos no cambian, solo los nombres de columnas."""
        df = pd.DataFrame({"prod": [450, 480, 420]})
        result = mapear_columnas(df)
        assert list(result["produccion_real"]) == [450, 480, 420]


# ── Tests: Pipeline completo con mapeo ───────────────────────────────────


class TestPipelineConMapeo:

    def test_ingestion_con_alias(self):
        """Ingestion Agent mapea columnas y detecta dominio correctamente."""
        from opsagent.agents.ingestion import ingestion_node
        from opsagent.state import initial_state

        # CSV con nombres no estandar
        df = pd.DataFrame({
            "Fecha": ["2025-01-01", "2025-01-02", "2025-01-03"],
            "Line": ["L1", "L1", "L2"],
            "Output": [450, 480, 420],
            "Cap Max": [500, 500, 500],
            "Scrap": [15, 10, 20],
            "Downtime": [30, 20, 45],
            "Planned Hours": [8, 8, 8],
        })
        state = initial_state(df, "planta_real.xlsx")
        result = ingestion_node(state)

        assert result["detected_domain"] == "manufactura"
        assert result["processing_status"] == "analyzing"
        # Las columnas mapeadas deben permitir calcular KPIs
        cols = list(result["cleaned_data"].columns)
        assert "produccion_real" in cols
        assert "defectos" in cols


# ── Tests: Deteccion de dominio ──────────────────────────────────────────


class TestDeteccionDominio:

    def test_manufactura(self):
        assert detectar_dominio(["produccion", "defectos", "linea"]) == "manufactura"

    def test_logistica(self):
        assert detectar_dominio(["pedido", "entrega", "inventario"]) == "logistica"

    def test_alimentos(self):
        assert detectar_dominio(["lote", "temperatura", "merma"]) == "alimentos"

    def test_desconocido(self):
        assert detectar_dominio(["col1", "col2", "col3"]) == "desconocido"


# ── Tests: Limpieza de datos ─────────────────────────────────────────────


class TestLimpiezaDatos:

    def test_elimina_duplicados(self):
        df = pd.DataFrame({"a": [1, 1, 2], "b": [3, 3, 4]})
        cleaned, report = limpiar_dataframe(df)
        assert len(cleaned) == 2
        assert report["filas_eliminadas"] == 1

    def test_elimina_filas_muy_nulas(self):
        df = pd.DataFrame({
            "a": [1, None, 3],
            "b": [4, None, 6],
            "c": [7, None, 9],
        })
        cleaned, report = limpiar_dataframe(df)
        assert len(cleaned) == 2

    def test_reporta_nulos_aislados(self):
        df = pd.DataFrame({
            "a": [1, None, 3, 4],
            "b": [5, 6, 7, 8],
        })
        cleaned, report = limpiar_dataframe(df)
        assert any("nulos" in p for p in report["problemas"])
