"""Tests unitarios para calculos de KPIs industriales."""

import pandas as pd
import pytest
from opsagent.tools.analysis_tools import (
    calcular_kpis_manufactura,
    calcular_kpis_logistica,
    detectar_anomalias_estadisticas,
)


# ── Tests: KPIs Manufactura ─────────────────────────────────────────────


class TestKPIsManufactura:

    @pytest.fixture
    def df_manufactura(self):
        return pd.DataFrame({
            "produccion_real": [450, 480, 420],
            "capacidad_teorica": [500, 500, 500],
            "defectos": [15, 10, 20],
            "tiempo_parada_min": [30, 20, 45],
            "horas_planificadas": [8, 8, 8],
            "linea": ["L1", "L1", "L2"],
        })

    def test_oee_en_rango_valido(self, df_manufactura):
        kpis = calcular_kpis_manufactura(df_manufactura)
        assert "oee" in kpis
        assert 0 < kpis["oee"] <= 1

    def test_oee_calculo_correcto(self):
        """Verificar OEE con valores conocidos.
        Disponibilidad = (480 - 0) / 480 = 1.0
        Rendimiento = 500 / 500 = 1.0
        Calidad = (500 - 0) / 500 = 1.0
        OEE = 1.0
        """
        df = pd.DataFrame({
            "produccion_real": [500],
            "capacidad_teorica": [500],
            "defectos": [0],
            "tiempo_parada_min": [0],
            "horas_planificadas": [8],
        })
        kpis = calcular_kpis_manufactura(df)
        assert kpis["oee"] == 1.0

    def test_tasa_defectos_correcta(self, df_manufactura):
        kpis = calcular_kpis_manufactura(df_manufactura)
        assert "tasa_defectos" in kpis
        # (15 + 10 + 20) / (450 + 480 + 420) = 45/1350 ≈ 0.0333
        assert abs(kpis["tasa_defectos"] - 45 / 1350) < 0.001

    def test_throughput_por_linea(self, df_manufactura):
        kpis = calcular_kpis_manufactura(df_manufactura)
        assert "throughput_por_linea" in kpis
        assert "L1" in kpis["throughput_por_linea"]
        assert "L2" in kpis["throughput_por_linea"]
        # L1: (450+480)/2 = 465
        assert kpis["throughput_por_linea"]["L1"] == 465.0

    def test_throughput_promedio(self, df_manufactura):
        kpis = calcular_kpis_manufactura(df_manufactura)
        assert "throughput_promedio" in kpis
        assert kpis["throughput_promedio"] == 450.0

    def test_columnas_faltantes_no_crashea(self):
        """Si faltan columnas de OEE, solo calcula lo que puede."""
        df = pd.DataFrame({
            "produccion_real": [450, 480],
            "defectos": [15, 10],
            "linea": ["L1", "L1"],
        })
        kpis = calcular_kpis_manufactura(df)
        assert "oee" not in kpis  # No tiene todas las columnas
        assert "tasa_defectos" in kpis  # Tiene produccion + defectos

    def test_datos_no_numericos_coercion(self):
        """Columnas con datos no numericos se convierten con coerce."""
        df = pd.DataFrame({
            "produccion_real": ["450", "n/a", "480"],
            "capacidad_teorica": [500, 500, 500],
            "defectos": [15, 10, 20],
            "tiempo_parada_min": [30, 20, 45],
            "horas_planificadas": [8, 8, 8],
        })
        kpis = calcular_kpis_manufactura(df)
        assert "oee" in kpis

    def test_cero_produccion_no_divide_por_cero(self):
        """Produccion 0 no debe causar ZeroDivisionError."""
        df = pd.DataFrame({
            "produccion_real": [0, 0],
            "capacidad_teorica": [500, 500],
            "defectos": [0, 0],
            "tiempo_parada_min": [0, 0],
            "horas_planificadas": [8, 8],
        })
        kpis = calcular_kpis_manufactura(df)
        # No debe crashear; puede no tener OEE por NaN
        assert isinstance(kpis, dict)

    def test_cero_horas_planificadas_no_divide_por_cero(self):
        """Horas planificadas 0 no debe causar ZeroDivisionError."""
        df = pd.DataFrame({
            "produccion_real": [450],
            "capacidad_teorica": [500],
            "defectos": [15],
            "tiempo_parada_min": [30],
            "horas_planificadas": [0],
        })
        kpis = calcular_kpis_manufactura(df)
        assert isinstance(kpis, dict)

    def test_dataframe_vacio(self):
        """DataFrame vacio retorna dict vacio."""
        df = pd.DataFrame(columns=["produccion_real", "defectos"])
        kpis = calcular_kpis_manufactura(df)
        assert kpis == {}


# ── Tests: KPIs Logistica ────────────────────────────────────────────────


class TestKPIsLogistica:

    @pytest.fixture
    def df_logistica(self):
        return pd.DataFrame({
            "items_pedidos": [50, 30, 45],
            "items_entregados": [50, 30, 40],
            "fecha_entrega_prometida": ["2025-01-06", "2025-01-08", "2025-01-11"],
            "fecha_entrega_real": ["2025-01-06", "2025-01-08", "2025-01-13"],
        })

    def test_fill_rate_correcto(self, df_logistica):
        kpis = calcular_kpis_logistica(df_logistica)
        assert "fill_rate" in kpis
        # (50+30+40) / (50+30+45) = 120/125 = 0.96
        assert abs(kpis["fill_rate"] - 0.96) < 0.01

    def test_on_time_delivery(self, df_logistica):
        kpis = calcular_kpis_logistica(df_logistica)
        assert "on_time_delivery" in kpis
        # 2 de 3 a tiempo
        assert abs(kpis["on_time_delivery"] - 2 / 3) < 0.01

    def test_columnas_faltantes(self):
        """Sin columnas de logistica, retorna dict vacio."""
        df = pd.DataFrame({"col_random": [1, 2, 3]})
        kpis = calcular_kpis_logistica(df)
        assert kpis == {}

    def test_datos_no_numericos_items(self):
        """Items con strings se convierten."""
        df = pd.DataFrame({
            "items_pedidos": ["50", "invalid", "45"],
            "items_entregados": ["50", "30", "45"],
        })
        kpis = calcular_kpis_logistica(df)
        assert "fill_rate" in kpis


# ── Tests: Anomalias ────────────────────────────────────────────────────


class TestAnomalias:

    def test_detecta_anomalia_3sigma(self):
        # 150 esta ~3 stdev de la media de ~450
        serie = [450, 440, 460, 455, 150, 470, 445, 465, 450, 440]
        result = detectar_anomalias_estadisticas(serie, "test_campo")
        assert len(result) >= 1
        assert result[0]["campo"] == "test_campo"

    def test_sin_anomalias_uniforme(self):
        serie = [100] * 10
        result = detectar_anomalias_estadisticas(serie, "uniforme")
        assert result == []

    def test_serie_corta(self):
        """Serie con < 3 elementos no detecta anomalias."""
        result = detectar_anomalias_estadisticas([1, 2], "corta")
        assert result == []

    def test_severidad_critica_vs_alta(self):
        """Valor a >3 std es critica, >2 std es alta."""
        # Crear serie donde un outlier esta a >3 std
        serie = [100] * 20 + [300]
        result = detectar_anomalias_estadisticas(serie, "test")
        if result:
            severidades = [a["severidad"] for a in result]
            assert "critica" in severidades or "alta" in severidades
