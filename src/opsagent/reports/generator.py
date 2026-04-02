"""Generador de reportes PDF profesionales para OpsAgent.

Toma el output del pipeline de diagnostico y genera un PDF descargable
con resumen ejecutivo, KPIs, anomalias y recomendaciones priorizadas.
"""

import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
)


# ── Estilos ──────────────────────────────────────────────────────────────

_BRAND_COLOR = colors.HexColor("#1a56db")
_BRAND_LIGHT = colors.HexColor("#e8edfb")
_SEVERITY_COLORS = {
    "critica": colors.HexColor("#dc2626"),
    "alta": colors.HexColor("#ea580c"),
    "media": colors.HexColor("#ca8a04"),
    "baja": colors.HexColor("#2563eb"),
}


def _build_styles() -> dict:
    """Crear estilos personalizados para el reporte."""
    base = getSampleStyleSheet()
    styles = {}

    styles["title"] = ParagraphStyle(
        "ReportTitle",
        parent=base["Title"],
        fontSize=22,
        textColor=_BRAND_COLOR,
        spaceAfter=4 * mm,
    )
    styles["subtitle"] = ParagraphStyle(
        "ReportSubtitle",
        parent=base["Normal"],
        fontSize=10,
        textColor=colors.gray,
        spaceAfter=6 * mm,
    )
    styles["heading"] = ParagraphStyle(
        "SectionHeading",
        parent=base["Heading2"],
        fontSize=14,
        textColor=_BRAND_COLOR,
        spaceBefore=8 * mm,
        spaceAfter=3 * mm,
    )
    styles["body"] = ParagraphStyle(
        "BodyText",
        parent=base["Normal"],
        fontSize=10,
        leading=14,
        spaceAfter=2 * mm,
    )
    styles["summary_box"] = ParagraphStyle(
        "SummaryBox",
        parent=base["Normal"],
        fontSize=11,
        leading=16,
        spaceAfter=2 * mm,
        backColor=_BRAND_LIGHT,
        borderPadding=8,
    )
    styles["rec_title"] = ParagraphStyle(
        "RecTitle",
        parent=base["Normal"],
        fontSize=11,
        textColor=_BRAND_COLOR,
        fontName="Helvetica-Bold",
    )
    styles["rec_detail"] = ParagraphStyle(
        "RecDetail",
        parent=base["Normal"],
        fontSize=9,
        textColor=colors.gray,
        leftIndent=12,
    )

    return styles


# ── Generador principal ──────────────────────────────────────────────────


def generate_pdf(diagnosis_data: dict, filename: str = "") -> bytes:
    """Generar reporte PDF a partir del output del pipeline.

    Args:
        diagnosis_data: Dict con las claves del DiagnoseResponse
            (status, detected_domain, executive_summary, kpis,
             anomalies, trends, diagnosis, recommendations,
             data_quality_report, processing_time_seconds)
        filename: Nombre del archivo analizado (opcional)

    Returns:
        Bytes del PDF generado, listo para descargar o guardar.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    styles = _build_styles()
    elements = []

    # ── Header ───────────────────────────────────────────────────────
    elements.append(Paragraph("OpsAgent — Reporte de Diagnostico", styles["title"]))

    meta_parts = []
    if filename:
        meta_parts.append(f"Archivo: {filename}")
    domain = diagnosis_data.get("detected_domain", "desconocido")
    meta_parts.append(f"Dominio: {domain.title()}")
    meta_parts.append(f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    processing_time = diagnosis_data.get("processing_time_seconds", 0)
    if processing_time:
        meta_parts.append(f"Tiempo de procesamiento: {processing_time:.1f}s")
    elements.append(Paragraph(" | ".join(meta_parts), styles["subtitle"]))

    elements.append(HRFlowable(width="100%", thickness=1, color=_BRAND_COLOR))
    elements.append(Spacer(1, 4 * mm))

    # ── Resumen Ejecutivo ────────────────────────────────────────────
    summary = diagnosis_data.get("executive_summary", "")
    if summary:
        elements.append(Paragraph("Resumen Ejecutivo", styles["heading"]))
        elements.append(Paragraph(summary, styles["summary_box"]))

    # ── KPIs ─────────────────────────────────────────────────────────
    kpis = diagnosis_data.get("kpis", {})
    if kpis:
        elements.append(Paragraph("KPIs", styles["heading"]))

        # Separar KPIs simples de compuestos
        simple = {k: v for k, v in kpis.items() if not isinstance(v, dict)}
        compound = {k: v for k, v in kpis.items() if isinstance(v, dict)}

        if simple:
            kpi_table_data = [["Metrica", "Valor"]]
            for name, value in simple.items():
                label = name.replace("_", " ").title()
                formatted = _format_kpi(value)
                kpi_table_data.append([label, formatted])

            t = Table(kpi_table_data, colWidths=[90 * mm, 60 * mm])
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), _BRAND_COLOR),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("ALIGN", (1, 0), (1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _BRAND_LIGHT]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            elements.append(t)
            elements.append(Spacer(1, 3 * mm))

        for group_name, sub_kpis in compound.items():
            elements.append(Paragraph(
                f"{group_name.replace('_', ' ').title()}:",
                styles["body"],
            ))
            sub_data = [["Clave", "Valor"]]
            for k, v in sub_kpis.items():
                sub_data.append([str(k), _format_kpi(v)])
            t = Table(sub_data, colWidths=[90 * mm, 60 * mm])
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#6b7280")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ALIGN", (1, 0), (1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]))
            elements.append(t)
            elements.append(Spacer(1, 2 * mm))

    # ── Anomalias ────────────────────────────────────────────────────
    anomalies = diagnosis_data.get("anomalies", [])
    if anomalies:
        elements.append(Paragraph(f"Anomalias ({len(anomalies)})", styles["heading"]))

        anom_data = [["Severidad", "Campo", "Detalle"]]
        for a in anomalies:
            sev = a.get("severidad", "baja").upper()
            campo = a.get("campo", "")
            detalle = a.get("detalle", "")
            anom_data.append([sev, campo, Paragraph(detalle, styles["body"])])

        t = Table(anom_data, colWidths=[25 * mm, 35 * mm, 100 * mm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), _BRAND_COLOR),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))

        # Color de fondo por severidad
        for i, a in enumerate(anomalies, start=1):
            sev = a.get("severidad", "baja")
            bg = _SEVERITY_COLORS.get(sev, colors.white)
            t.setStyle(TableStyle([
                ("TEXTCOLOR", (0, i), (0, i), bg),
                ("FONTNAME", (0, i), (0, i), "Helvetica-Bold"),
            ]))

        elements.append(t)

    # ── Tendencias ───────────────────────────────────────────────────
    trends = diagnosis_data.get("trends", [])
    if trends:
        elements.append(Paragraph(f"Tendencias ({len(trends)})", styles["heading"]))
        for t in trends:
            direction = t.get("direccion", "estable")
            metric = t.get("metrica", "?")
            magnitude = t.get("magnitud", 0)
            arrow = "↑" if direction == "ascendente" else "↓" if direction == "descendente" else "→"
            elements.append(Paragraph(
                f"{arrow} <b>{metric.replace('_', ' ').title()}</b>: {direction} ({magnitude:.1%})",
                styles["body"],
            ))

    # ── Diagnostico Completo ─────────────────────────────────────────
    diag_text = diagnosis_data.get("diagnosis", "")
    if diag_text:
        elements.append(Paragraph("Diagnostico Completo", styles["heading"]))
        for paragraph in diag_text.split("\n\n"):
            paragraph = paragraph.strip()
            if paragraph:
                # Clean markdown bold
                paragraph = paragraph.replace("**", "<b>").replace("</b><b>", "")
                elements.append(Paragraph(paragraph, styles["body"]))

    # ── Recomendaciones ──────────────────────────────────────────────
    recommendations = diagnosis_data.get("recommendations", [])
    if recommendations:
        elements.append(Paragraph(
            f"Recomendaciones ({len(recommendations)})", styles["heading"],
        ))

        for rec in recommendations:
            priority = rec.get("prioridad", 0)
            action = rec.get("accion", "")
            impact = rec.get("impacto", "")
            timeline = rec.get("plazo", "")

            elements.append(Paragraph(
                f"#{priority} — {action}", styles["rec_title"],
            ))
            elements.append(Paragraph(
                f"Impacto: {impact} | Plazo: {timeline}", styles["rec_detail"],
            ))
            elements.append(Spacer(1, 2 * mm))

    # ── Calidad de datos ─────────────────────────────────────────────
    quality = diagnosis_data.get("data_quality_report", {})
    if quality:
        elements.append(Paragraph("Calidad de Datos", styles["heading"]))
        orig = quality.get("filas_originales", "?")
        valid = quality.get("filas_validas", "?")
        removed = quality.get("filas_eliminadas", 0)
        elements.append(Paragraph(
            f"Filas originales: {orig} | Filas validas: {valid} | Eliminadas: {removed}",
            styles["body"],
        ))
        problems = quality.get("problemas", [])
        if problems:
            for p in problems:
                elements.append(Paragraph(f"• {p}", styles["body"]))

    # ── Footer ───────────────────────────────────────────────────────
    elements.append(Spacer(1, 8 * mm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))
    elements.append(Paragraph(
        f"Generado por OpsAgent v0.2.0 — {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        ParagraphStyle("Footer", fontSize=8, textColor=colors.gray, alignment=1),
    ))

    doc.build(elements)
    return buffer.getvalue()


# ── Helpers ──────────────────────────────────────────────────────────────


def _format_kpi(value) -> str:
    """Formatear valor de KPI para mostrar en tabla."""
    if isinstance(value, float):
        if abs(value) < 1:
            return f"{value * 100:.1f}%"
        return f"{value:,.2f}"
    return str(value)
