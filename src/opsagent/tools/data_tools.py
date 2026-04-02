"""Herramientas de carga y procesamiento de datos.

Funciones puras para validar, limpiar, y clasificar datos operativos.
Usadas internamente por el Ingestion Agent (no son @tool para Claude).
"""

import re

import pandas as pd


def normalizar_columnas(df: pd.DataFrame) -> pd.DataFrame:
    """Normalizar nombres de columnas a snake_case y convertir fechas.

    - Lowercase, espacios a _, eliminar caracteres especiales
    - Columnas con "fecha" se convierten a datetime
    """
    df = df.copy()

    nuevos_nombres = {}
    for col in df.columns:
        nuevo = col.strip().lower()
        nuevo = re.sub(r"[^a-z0-9_\s]", "", nuevo)
        nuevo = re.sub(r"\s+", "_", nuevo)
        nuevo = re.sub(r"_+", "_", nuevo).strip("_")
        nuevos_nombres[col] = nuevo

    df = df.rename(columns=nuevos_nombres)

    for col in df.columns:
        if "fecha" in col:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    return df


def limpiar_dataframe(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Limpiar y normalizar un DataFrame de datos operativos.

    Returns:
        Tupla (df_limpio, reporte_calidad)
    """
    filas_originales = len(df)
    problemas: list[str] = []

    # Eliminar filas duplicadas
    duplicados = df.duplicated().sum()
    if duplicados > 0:
        df = df.drop_duplicates()
        problemas.append(f"{duplicados} filas duplicadas eliminadas")

    # Eliminar filas con > 50% de valores nulos
    umbral_nulos = len(df.columns) * 0.5
    filas_muy_nulas = df.isnull().sum(axis=1) > umbral_nulos
    n_muy_nulas = filas_muy_nulas.sum()
    if n_muy_nulas > 0:
        df = df[~filas_muy_nulas]
        problemas.append(f"{n_muy_nulas} filas con >50% nulos eliminadas")

    # Reportar columnas numéricas con nulos aislados (no eliminar)
    for col in df.select_dtypes(include="number").columns:
        n_nulos = df[col].isnull().sum()
        if n_nulos > 0:
            pct = (n_nulos / len(df)) * 100
            problemas.append(f"Columna '{col}': {n_nulos} valores nulos ({pct:.1f}%)")

    filas_validas = len(df)
    reporte = {
        "filas_originales": filas_originales,
        "filas_validas": filas_validas,
        "filas_eliminadas": filas_originales - filas_validas,
        "problemas": problemas,
    }

    return df, reporte


# ── Mapeo inteligente de columnas ────────────────────────────────────────


# Mapeo de alias comunes a nombres canonicos del schema interno
COLUMN_ALIASES: dict[str, list[str]] = {
    # Manufactura
    "produccion_real": [
        "produccion", "prod", "output", "unidades_producidas", "prod_diaria",
        "cantidad_producida", "total_producido", "production", "qty_produced",
        "unidades", "piezas_producidas", "piezas",
    ],
    "capacidad_teorica": [
        "capacidad", "cap_teorica", "capacidad_maxima", "cap_max",
        "capacidad_nominal", "theoretical_capacity", "max_output",
    ],
    "defectos": [
        "defecto", "rechazos", "rechazo", "unidades_defectuosas",
        "piezas_defectuosas", "scrap", "defects", "no_conformes",
        "productos_defectuosos", "fallas",
    ],
    "tiempo_parada_min": [
        "parada", "paradas", "downtime", "tiempo_parada",
        "minutos_parada", "parada_min", "tiempo_inactivo",
        "stoppage", "tiempo_muerto",
    ],
    "horas_planificadas": [
        "horas_plan", "horas_programadas", "planned_hours",
        "hrs_planificadas", "horas_disponibles", "turno_horas",
    ],
    "linea": [
        "linea_produccion", "line", "production_line", "maquina",
        "equipo", "estacion", "machine", "celda",
    ],
    "fecha": [
        "date", "dia", "fecha_produccion", "production_date",
        "periodo", "timestamp",
    ],
    # Logistica
    "items_pedidos": [
        "items_solicitados", "cantidad_pedida", "qty_ordered",
        "unidades_pedidas", "pedido_cantidad",
    ],
    "items_entregados": [
        "items_enviados", "cantidad_entregada", "qty_delivered",
        "unidades_entregadas", "entrega_cantidad", "qty_shipped",
    ],
    "fecha_entrega_prometida": [
        "fecha_prometida", "promised_date", "due_date",
        "fecha_compromiso", "delivery_date",
    ],
    "fecha_entrega_real": [
        "fecha_real", "actual_date", "fecha_efectiva",
        "fecha_despacho", "ship_date",
    ],
}

# Invertir: alias -> nombre canonico
_ALIAS_TO_CANONICAL: dict[str, str] = {}
for canonical, aliases in COLUMN_ALIASES.items():
    for alias in aliases:
        _ALIAS_TO_CANONICAL[alias] = canonical


def mapear_columnas(df: pd.DataFrame) -> pd.DataFrame:
    """Intentar mapear columnas con nombres no estandar al schema interno.

    Busca coincidencias por nombre exacto (post snake_case) y por alias.
    Solo renombra si el nombre canonico no existe ya en el DataFrame.

    Returns:
        DataFrame con columnas renombradas donde se encontro match.
    """
    df = df.copy()
    existing = set(df.columns)
    rename_map = {}

    for col in df.columns:
        # Si la columna ya es un nombre canonico, no tocar
        if col in COLUMN_ALIASES:
            continue
        # Buscar en aliases
        if col in _ALIAS_TO_CANONICAL:
            canonical = _ALIAS_TO_CANONICAL[col]
            # Solo renombrar si el nombre canonico no existe ya
            if canonical not in existing and canonical not in rename_map.values():
                rename_map[col] = canonical

    if rename_map:
        df = df.rename(columns=rename_map)

    return df


def detectar_dominio(columnas: list[str]) -> str:
    """Detectar el dominio industrial basado en nombres de columnas.

    Returns:
        "manufactura" | "logistica" | "alimentos" | "desconocido"
    """
    columnas_lower = [c.lower() for c in columnas]
    texto = " ".join(columnas_lower)

    keywords = {
        "manufactura": [
            "produccion", "defecto", "maquina", "linea", "turno",
            "oee", "capacidad", "parada",
        ],
        "logistica": [
            "pedido", "entrega", "inventario", "despacho", "stock",
            "almacen", "items",
        ],
        "alimentos": [
            "lote", "temperatura", "vencimiento", "merma",
            "rendimiento", "bpm",
        ],
    }

    scores: dict[str, int] = {}
    for dominio, kws in keywords.items():
        scores[dominio] = sum(1 for kw in kws if kw in texto)

    mejor = max(scores, key=scores.get)
    if scores[mejor] == 0:
        return "desconocido"
    return mejor
