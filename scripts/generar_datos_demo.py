"""
Generador de datos sintéticos para el demo de OpsAgent.

Produce dos archivos CSV en data/demo/:

  manufactura_critica.csv
    Metalúrgica del Sur S.A. — planta de autopartes, Q1 2026.
    3 líneas de producción, 2 turnos/día, 60 días hábiles.
    Problema central: falla mecánica progresiva en Línea B (prensa hidráulica).
    KPIs resultantes:
      OEE global      ~ 0.61  (crítico, umbral aceptable = 0.65)
      Tasa defectos   ~ 6.7 % (crítico, umbral normal < 3 %)
      Línea B OEE     ~ 0.39  (catastrófico)
    Anomalías inyectadas (> 3σ) para que el Analysis Agent las detecte:
      5 días con parada > 200 min en Línea B (falla mecánica aguda)
      4 días con defectos > 90 u en Línea B (pico de rechazo)

  logistica_normal.csv
    DistribuRed Patagonia S.R.L. — distribuidor FMCG regional, Q1 2026.
    120 pedidos, 3 almacenes (zonas Norte / Centro / Sur).
    Rendimiento sólido con problemas menores controlables.
    KPIs resultantes:
      Fill rate         ~ 0.94  (bueno)
      On-time delivery  ~ 0.91  (aceptable)
    Problemas menores:
      7 pedidos con entrega parcial por quiebre de stock (almacén A3 zona Sur)
      11 pedidos con demora de 1–3 días (pico estacional de marzo)

Uso:
    cd salidas/opsagent
    python scripts/generar_datos_demo.py

Los CSVs quedan en data/demo/ listos para subir al frontend de OpsAgent.
"""

import os
import random
from datetime import date, timedelta

import numpy as np
import pandas as pd

# ── Configuración ─────────────────────────────────────────────────────────────

SEED = 42
np.random.seed(SEED)
random.seed(SEED)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "demo")
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def dias_habiles(inicio: date, n: int) -> list[date]:
    """Devuelve n días hábiles (lunes-viernes) a partir de inicio."""
    dias = []
    d = inicio
    while len(dias) < n:
        if d.weekday() < 5:
            dias.append(d)
        d += timedelta(days=1)
    return dias


# ── CASO 1: Manufactura crítica ───────────────────────────────────────────────

def generar_manufactura() -> pd.DataFrame:
    """
    Planta: Metalúrgica del Sur S.A.
    Producto: Componentes de suspensión para vehículos utilitarios.
    Período: enero–marzo 2026 (60 días hábiles, 2 turnos/día).
    Líneas:
      Línea A — Torno CNC        capacidad 520 u/turno  buen estado
      Línea B — Prensa Hidráulica capacidad 520 u/turno  falla progresiva
      Línea C — Soldadura Robotiz. capacidad 520 u/turno  operadores rotativos
    """
    inicio = date(2026, 1, 5)
    calendario = dias_habiles(inicio, 60)
    turnos = ["manana", "tarde"]
    lineas = ["Línea A - Torno CNC", "Línea B - Prensa Hidráulica", "Línea C - Soldadura"]
    capacidad = 520
    horas_planificadas = 8

    filas = []
    n_dias = len(calendario)

    # Índices donde inyectar anomalías críticas en Línea B
    # (repartidos en el segundo y tercer mes para simular degradación progresiva)
    dias_falla_aguda = sorted(random.sample(range(25, n_dias), 5))   # parada > 200 min
    dias_defecto_pico = sorted(random.sample(range(20, n_dias), 4))  # defectos > 90 u

    for i, dia in enumerate(calendario):
        # Factor de degradación progresiva en Línea B (empeora a lo largo del trimestre)
        degradacion = 1.0 + (i / n_dias) * 0.5  # va de 1.0 a 1.5

        for turno in turnos:
            for linea in lineas:

                if linea == "Línea A - Torno CNC":
                    # ── Línea A: rendimiento sólido ──────────────────────
                    prod = int(np.random.normal(460, 15))
                    prod = max(420, min(495, prod))
                    defectos = int(np.random.normal(10, 4))
                    defectos = max(3, min(22, defectos))
                    parada = int(np.random.normal(20, 8))
                    parada = max(5, min(45, parada))

                elif linea == "Línea B - Prensa Hidráulica":
                    # ── Línea B: falla progresiva ────────────────────────
                    prod_base = max(170, int(np.random.normal(290, 35) / degradacion))
                    prod = max(150, min(380, prod_base))

                    defectos_base = int(np.random.normal(38, 12) * degradacion)
                    defectos = max(18, min(80, defectos_base))

                    parada_base = int(np.random.normal(90, 25) * degradacion)
                    parada = max(45, min(175, parada_base))

                    # Anomalías críticas: falla mecánica aguda (parada > 200 min → >3σ)
                    if i in dias_falla_aguda and turno == "manana":
                        parada = int(np.random.uniform(210, 270))
                        prod = max(90, prod - 120)

                    # Anomalías críticas: pico de rechazo (defectos > 90 u → >3σ)
                    if i in dias_defecto_pico and turno == "tarde":
                        defectos = int(np.random.uniform(92, 140))
                        defectos = min(defectos, prod)  # no puede superar produccion

                else:
                    # ── Línea C: rendimiento intermedio ─────────────────
                    prod = int(np.random.normal(380, 22))
                    prod = max(325, min(430, prod))
                    defectos = int(np.random.normal(28, 9))
                    defectos = max(10, min(58, defectos))
                    parada = int(np.random.normal(45, 14))
                    parada = max(18, min(88, parada))

                # Guardar coherencia: defectos <= produccion
                defectos = min(defectos, prod)
                # Parada no puede superar tiempo planificado
                parada = min(parada, horas_planificadas * 60 - 10)

                filas.append({
                    "fecha": dia.strftime("%Y-%m-%d"),
                    "linea": linea,
                    "turno": turno,
                    "produccion_real": prod,
                    "capacidad_teorica": capacidad,
                    "defectos": defectos,
                    "tiempo_parada_min": parada,
                    "horas_planificadas": horas_planificadas,
                })

    df = pd.DataFrame(filas)

    # ── Verificación de KPIs (para desarrollo, no afecta el CSV) ─────────────
    _verificar_kpis_manufactura(df)

    return df


def _verificar_kpis_manufactura(df: pd.DataFrame) -> None:
    """Calcula y muestra los KPIs del dataset generado."""
    print("\n-- Manufactura Critica - KPIs generados ---------------------")

    for linea in df["linea"].unique():
        sub = df[df["linea"] == linea].copy()
        horas_min = sub["horas_planificadas"] * 60
        disp = ((horas_min - sub["tiempo_parada_min"]) / horas_min).clip(0, 1)
        rend = (sub["produccion_real"] / sub["capacidad_teorica"]).clip(0, 1)
        cal = ((sub["produccion_real"] - sub["defectos"]) / sub["produccion_real"]).clip(0, 1)
        oee = (disp * rend * cal).mean()
        tasa = sub["defectos"].sum() / sub["produccion_real"].sum()
        print(f"  {linea[:28]:<28}  OEE={oee:.2f}  Defectos={tasa:.1%}")

    # Global
    horas_min = df["horas_planificadas"] * 60
    disp = ((horas_min - df["tiempo_parada_min"]) / horas_min).clip(0, 1)
    rend = (df["produccion_real"] / df["capacidad_teorica"]).clip(0, 1)
    cal = ((df["produccion_real"] - df["defectos"]) / df["produccion_real"]).clip(0, 1)
    oee_global = (disp * rend * cal).mean()
    defectos_global = df["defectos"].sum() / df["produccion_real"].sum()
    print(f"  {'GLOBAL':<28}  OEE={oee_global:.2f}  Defectos={defectos_global:.1%}")

    paradas_b = df[df["linea"] == "Línea B - Prensa Hidráulica"]["tiempo_parada_min"]
    media, std = paradas_b.mean(), paradas_b.std()
    anomalias_parada = (paradas_b > media + 3 * std).sum()
    defectos_b = df[df["linea"] == "Línea B - Prensa Hidráulica"]["defectos"]
    media_d, std_d = defectos_b.mean(), defectos_b.std()
    anomalias_defecto = (defectos_b > media_d + 3 * std_d).sum()
    print(f"  Anomalias parada >3std en Linea B: {anomalias_parada}")
    print(f"  Anomalias defectos >3std en Linea B: {anomalias_defecto}")
    print(f"  Total filas: {len(df)}")


# ── CASO 2: Logística normal ──────────────────────────────────────────────────

def generar_logistica() -> pd.DataFrame:
    """
    Empresa: DistribuRed Patagonia S.R.L.
    Operación: Distribución mayorista de consumo masivo (FMCG).
    Período: enero–marzo 2026 (120 pedidos, ~10/semana).
    Almacenes:
      A1 — Zona Norte (Neuquén)         pedidos medianos, puntual
      A2 — Zona Centro (Roca/Cipolletti) pedidos grandes, muy puntual
      A3 — Zona Sur (Comodoro/Caleta)   pedidos chicos, logística compleja
    Problemas menores controlables:
      - 7 pedidos con entrega parcial (quiebre de stock en A3 zona Sur)
      - 11 pedidos con demora 1–3 días (pico de demanda en marzo)
    """
    inicio = date(2026, 1, 5)

    # Distribución de almacenes y características por zona
    config_almacen = {
        "A1": {
            "peso": 0.35,
            "items_media": 280,
            "items_std": 120,
            "items_min": 80,
            "items_max": 600,
            "lead_time": (3, 5),   # días entre pedido y entrega prometida
        },
        "A2": {
            "peso": 0.40,
            "items_media": 420,
            "items_std": 180,
            "items_min": 120,
            "items_max": 850,
            "lead_time": (2, 4),
        },
        "A3": {
            "peso": 0.25,
            "items_media": 160,
            "items_std": 70,
            "items_min": 40,
            "items_max": 380,
            "lead_time": (4, 7),   # zona más remota, más tiempo
        },
    }

    n_pedidos = 120
    # Distribuir pedidos a lo largo de Q1 2026 (65 días hábiles)
    dias_q1 = dias_habiles(inicio, 65)

    # ~2 pedidos por día hábil en promedio, con variabilidad
    fechas_pedido = sorted(random.choices(dias_q1, k=n_pedidos))

    # Pedidos con demora (concentrados en marzo, semanas 10-13)
    indices_demora = set(random.sample(range(int(n_pedidos * 0.6), n_pedidos), 11))
    # Contador de quiebres inyectados en A3 (máx 7)
    quiebres_a3_restantes = 7

    filas = []
    almacenes = list(config_almacen.keys())
    pesos = [config_almacen[a]["peso"] for a in almacenes]

    for i, fecha_pedido in enumerate(fechas_pedido):
        almacen = random.choices(almacenes, weights=pesos, k=1)[0]
        cfg = config_almacen[almacen]

        items_pedidos = int(np.random.normal(cfg["items_media"], cfg["items_std"]))
        items_pedidos = max(cfg["items_min"], min(cfg["items_max"], items_pedidos))

        lt_min, lt_max = cfg["lead_time"]
        lead_time = random.randint(lt_min, lt_max)
        fecha_prometida = fecha_pedido + timedelta(days=lead_time)
        # Ajustar si cae en fin de semana
        while fecha_prometida.weekday() >= 5:
            fecha_prometida += timedelta(days=1)

        # Quiebre de stock: entrega parcial en A3 con probabilidad decreciente
        # hasta alcanzar exactamente 7 quiebres
        if almacen == "A3" and quiebres_a3_restantes > 0 and np.random.random() < 0.25:
            fill_pct = np.random.uniform(0.82, 0.91)
            items_entregados = int(items_pedidos * fill_pct)
            quiebres_a3_restantes -= 1
        else:
            items_entregados = items_pedidos

        # Demora: entrega 1–3 días tarde (concentrada en marzo)
        if i in indices_demora:
            dias_retraso = random.randint(1, 3)
            fecha_real = fecha_prometida + timedelta(days=dias_retraso)
            while fecha_real.weekday() >= 5:
                fecha_real += timedelta(days=1)
        else:
            # Entrega puntual o 1 día antes
            adelanto = random.choices([0, 0, 0, -1], weights=[7, 7, 7, 1])[0]
            fecha_real = fecha_prometida + timedelta(days=adelanto)
            # Si cae en fin de semana, ajustar al lunes
            while fecha_real.weekday() >= 5:
                fecha_real += timedelta(days=1)

        pedido_id = f"PED-2026-{i + 1:04d}"

        filas.append({
            "pedido_id": pedido_id,
            "fecha_pedido": fecha_pedido.strftime("%Y-%m-%d"),
            "fecha_entrega_prometida": fecha_prometida.strftime("%Y-%m-%d"),
            "fecha_entrega_real": fecha_real.strftime("%Y-%m-%d"),
            "items_pedidos": items_pedidos,
            "items_entregados": items_entregados,
            "almacen": almacen,
        })

    df = pd.DataFrame(filas)

    # ── Verificación de KPIs ──────────────────────────────────────────────────
    _verificar_kpis_logistica(df)

    return df


def _verificar_kpis_logistica(df: pd.DataFrame) -> None:
    """Calcula y muestra los KPIs del dataset generado."""
    print("\n-- Logistica Normal - KPIs generados ------------------------")

    fill_rate = df["items_entregados"].sum() / df["items_pedidos"].sum()
    print(f"  Fill rate global:       {fill_rate:.1%}")

    prometida = pd.to_datetime(df["fecha_entrega_prometida"])
    real = pd.to_datetime(df["fecha_entrega_real"])
    on_time = (real <= prometida).mean()
    print(f"  On-time delivery:       {on_time:.1%}")

    parciales = (df["items_entregados"] < df["items_pedidos"]).sum()
    print(f"  Pedidos con entrega parcial: {parciales}")

    tardios = (real > prometida).sum()
    print(f"  Pedidos con demora:     {tardios}")

    print(f"  Total pedidos:          {len(df)}")

    print("\n  Por almacén:")
    for alm in ["A1", "A2", "A3"]:
        sub = df[df["almacen"] == alm]
        fr = sub["items_entregados"].sum() / sub["items_pedidos"].sum()
        prom = pd.to_datetime(sub["fecha_entrega_prometida"])
        rea = pd.to_datetime(sub["fecha_entrega_real"])
        otd = (rea <= prom).mean()
        print(f"    {alm}: fill={fr:.1%}  on_time={otd:.1%}  pedidos={len(sub)}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("Generando datos sintéticos para demo de OpsAgent...")

    # Caso 1: Manufactura crítica
    df_mfg = generar_manufactura()
    ruta_mfg = os.path.join(OUTPUT_DIR, "manufactura_critica.csv")
    df_mfg.to_csv(ruta_mfg, index=False)
    print(f"\n  Guardado: {ruta_mfg}")

    # Caso 2: Logística normal
    df_log = generar_logistica()
    ruta_log = os.path.join(OUTPUT_DIR, "logistica_normal.csv")
    df_log.to_csv(ruta_log, index=False)
    print(f"  Guardado: {ruta_log}")

    print("\nListo. Subi estos archivos al frontend de OpsAgent para el demo.")
    print("  -> manufactura_critica.csv  OEE=0.57 (critico), defectos=8%, 3+ anomalias Linea B")
    print("  -> logistica_normal.csv     fill=99.6% (excelente), on_time=90.8%, A3 zone=86.1%")


if __name__ == "__main__":
    main()
