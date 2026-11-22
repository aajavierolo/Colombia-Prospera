from __future__ import annotations

from io import BytesIO
from typing import Any, Dict, Iterable, Optional
from xml.sax.saxutils import escape
import hashlib

_original_md5 = hashlib.md5

def _md5_compatible(*args, **kwargs):
    kwargs.pop("usedforsecurity", None)
    return _original_md5(*args, **kwargs)

hashlib.md5 = _md5_compatible

import matplotlib

# Docker no tiene una pantalla grafica. Agg permite crear los graficos del PDF
# completamente en memoria tanto en el contenedor como en ejecuciones locales.
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams['text.parse_math'] = False
import matplotlib.ticker as mtick
import pandas as pd
import textwrap
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase.pdfmetrics import stringWidth
import math
from pathlib import Path
from modules.promedios import calcular_promedios_gasto
from modules.regla_presupuesto import clasificar_regla
from reportlab.platypus import (
    BaseDocTemplate, Frame, Image, KeepTogether, PageBreak, PageTemplate,
    Paragraph, Spacer, Table, TableStyle, Flowable,
)

PAGE = landscape(A4)
DARK = colors.HexColor("#07111F")
PANEL = colors.HexColor("#0F2238")
BLUE = colors.HexColor("#38BDF8")
GREEN = colors.HexColor("#34D399")
RED = colors.HexColor("#FB7185")
YELLOW = colors.HexColor("#FDE68A")
PURPLE = colors.HexColor("#C084FC")
TEXT = colors.HexColor("#E2E8F0")
MUTED = colors.HexColor("#B4C9D9")
WHITE = colors.white
INK = colors.HexColor("#E2E8F0")

# Paleta de impresión: contrastes altos sobre fondo claro.
PDF_BLUE = "#39D7FF"
PDF_CYAN = "#06B6D4"
PDF_GREEN = "#52E0A4"
PDF_RED = "#FF526E"
PDF_ORANGE = "#F97316"
PDF_PURPLE = "#8B5CF6"
PDF_YELLOW = "#EAB308"
PDF_PALETTE = [PDF_BLUE, PDF_CYAN, PDF_GREEN, PDF_ORANGE, PDF_PURPLE, PDF_RED, PDF_YELLOW, "#14B8A6", "#EC4899", "#84CC16", "#0EA5E9", "#A855F7"]

QUESTIONS = [
    ("1. Resumen", "¿Cómo estoy hoy?", "Sintetiza ingresos, gastos, balance, ahorro y señales prioritarias."),
    ("2. Gastos", "¿En qué se me va el dinero?", "Explica la concentración del gasto por categorías y tipos."),
    ("3. Tendencias", "¿Cómo he evolucionado?", "Compara el comportamiento mensual de ingresos, gastos y balance."),
    ("4. Presupuesto", "¿Estoy cumpliendo mis metas?", "Contrasta la ejecución mensual con el presupuesto disponible."),
    ("5. Ingresos", "¿De dónde proviene el dinero?", "Identifica las principales fuentes y su participación."),
    ("6. Deudas", "¿Qué obligaciones tengo?", "Resume saldos, intereses, pagos y prioridades."),
    ("7. Patrimonio", "¿Cuál es mi riqueza?", "Presenta la composición patrimonial disponible en el archivo."),
    ("8. Felicidad", "¿Mi dinero está alineado con mi bienestar?", "Relaciona empresa, horas trabajadas, valor por hora, tipo de ingreso y patrimonio esperado."),
]


def _money(value: Any) -> str:
    try:
        return f"${float(value):,.0f}".replace(",", ".")
    except (TypeError, ValueError):
        return str(value)


def _number(value: Any) -> str:
    try:
        return f"{float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return str(value)

def _income_type(value: Any) -> str:
    """Clasifica ingresos sin confundir NO LABORAL con LABORAL."""
    if value is None:
        return "Sin clasificar"
    text = str(value).strip().upper().replace("-", " ").replace("_", " ")
    text = " ".join(text.split())
    if not text or text in {"NAN", "NONE", "SIN TIPO", "SIN CLASIFICAR"}:
        return "Sin clasificar"
    if text in {"RESIDUAL", "RESIDUALES", "RENTAS", "RENDIMIENTOS", "INVERSION", "INVERSIONES", "NO LABORAL", "NO LABORALES", "NO LABOR", "NO LABORA"} or text.startswith("NO LABOR"):
        return "Residuales"
    if text in {"OCASIONAL", "OCASIONALES"}:
        return "Ocasionales"
    if text in {"LABORAL", "LABORALES"}:
        return "Laborales"
    if any(token in text for token in ["SALARIO", "SALARIAL", "NOMINA", "EMPLEO", "HONORARIO", "CONTRATO LABORAL"]):
        return "Laborales"
    return "Sin clasificar"


def _safe_text(value: Any, max_len: int = 85) -> str:
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    text = str(value)
    if len(text) > max_len:
        text = text[: max_len - 1] + "…"
    return escape(text, entities={"\n": "<br/>"})


def _footer(canvas, doc, etiqueta="Informe por preguntas"):
    canvas.saveState()
    width, height = PAGE
    for i in range(64):
        t = i / 63
        canvas.setFillColor(colors.Color(.028 + .025*t, .055 + .045*t, .10 + .07*t))
        canvas.rect(0, height*i/64, width, height/64+1, fill=1, stroke=0)
    canvas.setStrokeColor(BLUE)
    canvas.setLineWidth(.8)
    canvas.line(1.2*cm, height-.35*cm, width-1.2*cm, height-.35*cm)
    canvas.setFillColor(DARK)
    canvas.rect(0, 0, width, 0.65 * cm, fill=1, stroke=0)
    canvas.setFillColor(colors.HexColor("#CBD5E1"))
    canvas.setFont("Helvetica", 8)
    canvas.drawString(1.2 * cm, 0.25 * cm, f"Colombia Prospera V26 - {etiqueta}")
    canvas.drawRightString(width - 1.2 * cm, 0.25 * cm, f"Página {doc.page}")
    canvas.restoreState()


def _styles() -> Dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("Title", parent=base["Title"], fontName="Helvetica-Bold", fontSize=24, leading=28, textColor=TEXT, alignment=TA_CENTER, spaceAfter=8),
        "subtitle": ParagraphStyle("Subtitle", parent=base["Normal"], fontName="Helvetica", fontSize=10.5, leading=15, textColor=MUTED, alignment=TA_CENTER),
        "section": ParagraphStyle("Section", parent=base["Heading1"], fontName="Helvetica-Bold", fontSize=16, leading=19, textColor=BLUE, spaceBefore=3, spaceAfter=3),
        "question": ParagraphStyle("Question", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=13, leading=17, textColor=INK, spaceAfter=3),
        "answer": ParagraphStyle("Answer", parent=base["BodyText"], fontName="Helvetica", fontSize=9, leading=13, textColor=MUTED, spaceAfter=8),
        "body": ParagraphStyle("Body", parent=base["BodyText"], fontName="Helvetica", fontSize=8.7, leading=12.5, textColor=INK),
        "small": ParagraphStyle("Small", parent=base["BodyText"], fontName="Helvetica", fontSize=7.2, leading=9.2, textColor=INK),
        "table_header": ParagraphStyle("TH", parent=base["BodyText"], fontName="Helvetica-Bold", fontSize=7.2, leading=9, textColor=WHITE),
        "card_title": ParagraphStyle("CardTitle", parent=base["BodyText"], fontName="Helvetica-Bold", fontSize=9, leading=11, textColor=colors.HexColor("#DCECF5"), alignment=TA_CENTER),
        "card_value": ParagraphStyle("CardValue", parent=base["BodyText"], fontName="Helvetica-Bold", fontSize=14, leading=17, textColor=WHITE, alignment=TA_CENTER),
    }


def _question_header(index: int, styles):
    title, question, answer = QUESTIONS[index]
    box = Table([
        [Paragraph(title, styles["section"])],
        [Paragraph(question, styles["question"])],
        [Paragraph(answer, styles["answer"])],
    ], colWidths=[PAGE[0] - 2.4 * cm])
    box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PANEL),
        ("BOX", (0, 0), (-1, -1), 0.8, BLUE),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return box


class _DashboardCards(Flowable):
    """Tarjetas vectoriales con degradado y tamaño de texto adaptable."""
    def __init__(self, items, styles, width=None):
        Flowable.__init__(self)
        self.items = list(items)
        self.styles = styles
        self.width = width or PAGE[0] - 2.4 * cm
        self.height = 2.75 * cm

    def draw(self):
        c = self.canv
        n = max(len(self.items), 1)
        gap = 10
        width = (self.width - gap * (n - 1)) / n
        height = self.height - 5
        for i, (title, value) in enumerate(self.items):
            x = i * (width + gap)
            accent = colors.HexColor("#68e5ff")
            tone = "blue"
            if title in ("Tiempo ahorrado", "Dinero ahorrado"):
                positivo = any(c in '123456789' for c in str(value))
                tone = "green" if positivo else "blue"
                accent = GREEN if positivo else BLUE
            if title in ("Ingresos", "Gastos", "Disponible"):
                tone = "red" if title == "Gastos" or (title == "Disponible" and "-" in str(value)) else "green"
                accent = RED if tone == "red" else GREEN
            c.setFillColor(colors.HexColor("#030b15"))
            c.roundRect(x+2, 0, width, height, 12, fill=1, stroke=0)
            c.saveState()
            path = c.beginPath()
            path.roundRect(x, 3, width, height, 12)
            c.clipPath(path, stroke=0)
            for strip in range(56):
                t = strip / 55
                c.setFillColor(colors.Color(.035 + .045*t, .075 + .09*t, .135 + .13*t))
                if tone == "green":
                    c.setFillColor(colors.Color(.035, .12 + .12*t, .09 + .07*t))
                elif tone == "red":
                    c.setFillColor(colors.Color(.13 + .13*t, .04 + .04*t, .075 + .06*t))
                c.rect(x + width*strip/56, 3, width/56+1, height, fill=1, stroke=0)
            c.restoreState()
            c.setStrokeColor(accent)
            c.setLineWidth(.8)
            c.roundRect(x, 3, width, height, 12, fill=0, stroke=1)
            label = Paragraph(_safe_text(title), self.styles["card_title"])
            _, label_h = label.wrap(width-16, 26)
            label.drawOn(c, x+8, 3+height-12-label_h)
            size = 21
            while stringWidth(str(value), "Helvetica-Bold", size) > width-20 and size > 10:
                size -= .5
            c.setFont("Helvetica-Bold", size)
            # Blanco a celeste, coherente con las tarjetas del dashboard.
            c.setFillColor(accent if tone != "blue" else colors.HexColor("#b8efff"))
            c.drawCentredString(x+width/2, 3+height*.29, str(value))


def _kpi_table(items: Iterable[tuple[str, str]], styles):
    return _DashboardCards(items, styles)


class _PdfGauge(Flowable):
    """Medidor vectorial con las mismas franjas que el dashboard."""
    def __init__(self, title, value, cuts, colors_hex, suffix="%", width=470, height=220):
        Flowable.__init__(self)
        self.title, self.value, self.cuts = title, value, cuts
        self.colors_hex, self.suffix = colors_hex, suffix
        self.width, self.height = width, height

    def draw(self):
        c = self.canv
        c.setFillColor(colors.HexColor("#0b1728"))
        c.roundRect(0, 0, self.width, self.height, 14, fill=1, stroke=0)
        c.setFillColor(TEXT)
        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(self.width/2, self.height-20, self.title)
        if self.value is None:
            c.setFont("Helvetica", 12)
            c.drawCentredString(self.width/2, self.height/2, "No calculable")
            return
        maximum = self.cuts[-1]
        cx, cy = self.width/2, 28
        radius = min(self.width*.40, self.height*.64)
        for lo, hi, color in zip(self.cuts, self.cuts[1:], self.colors_hex):
            theta = [math.pi*(1-(lo+(hi-lo)*i/60)/maximum) for i in range(61)]
            points = [(cx+radius*math.cos(t), cy+radius*math.sin(t)) for t in theta]
            points += [(cx+radius*.7*math.cos(t), cy+radius*.7*math.sin(t)) for t in reversed(theta)]
            path = c.beginPath(); path.moveTo(*points[0])
            for point in points[1:]: path.lineTo(*point)
            path.close()
            c.setFillColor(colors.HexColor(color)); c.setStrokeColor(DARK); c.setLineWidth(1.5)
            c.drawPath(path, fill=1, stroke=1)
        needle = math.pi*(1-min(max(self.value, 0), maximum)/maximum)
        c.setStrokeColor(WHITE); c.setLineWidth(2.5)
        c.line(cx, cy, cx+radius*.96*math.cos(needle), cy+radius*.96*math.sin(needle))
        c.setFillColor(WHITE); c.circle(cx, cy, 4, fill=1, stroke=0)
        c.setFont("Helvetica", 9)
        for cut in self.cuts:
            theta=math.pi*(1-cut/maximum)
            c.drawCentredString(cx+(radius+14)*math.cos(theta), cy+(radius+14)*math.sin(theta), f"{cut:g}{self.suffix}")
        c.setFont("Helvetica-Bold", 23)
        c.drawCentredString(cx, cy+35, f"{self.value:.2f}{self.suffix}")


def _indice_con_medidor(story, styles, title, value, status, explanation, cuts, suffix="%", palette=None):
    usable = PAGE[0]-2.4*cm
    left = 8.6*cm
    text = f"<b>{_safe_text(status, 150)}</b><br/><br/>{explanation}"
    card = _DashboardCards([(title, f"{value:.2f}{suffix}" if value is not None else "No calculable")], styles, width=left-20)
    gauge = _PdfGauge(title, value, cuts, palette or ["#39FF14", "#FFEA00", "#FF8C00", "#FF1744"], suffix, width=usable-left-20)
    row = Table([[[card, Spacer(1, 8), Paragraph(text, styles["body"])], gauge]], colWidths=[left,usable-left])
    row.setStyle(TableStyle([
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("BACKGROUND",(0,0),(0,0),PANEL),
        ("LEFTPADDING",(0,0),(-1,-1),10),("RIGHTPADDING",(0,0),(-1,-1),10),
        ("TOPPADDING",(0,0),(-1,-1),10),("BOTTOMPADDING",(0,0),(-1,-1),10),
    ]))
    story.extend([row,Spacer(1,12)])


def _hero_table(nombre_persona: str, edad_persona: Any, fecha_desde: Any, fecha_hasta: Any, styles):
    """Portada compacta con la misma identidad oscura y neon del dashboard."""
    usable = PAGE[0] - 2.4 * cm
    hero_title = Paragraph("ALTIUM FINANCIERO V26", ParagraphStyle(
        "HeroTitle", parent=styles["title"], fontSize=25, leading=29,
        textColor=WHITE, alignment=TA_LEFT, spaceAfter=3,
    ))
    hero_tag = Paragraph(
        "INFORME FINANCIERO EJECUTIVO  /  DATOS, DECISIONES Y PROYECCION",
        ParagraphStyle("HeroTag", parent=styles["small"], fontName="Helvetica-Bold",
                       fontSize=8, leading=10, textColor=GREEN, alignment=TA_LEFT),
    )
    person = Paragraph(
        f"<b>{_safe_text(nombre_persona, 120)}</b><br/>"
        f"Edad: {_safe_text(edad_persona)}<br/>"
        f"Periodo: {_safe_text(fecha_desde)} a {_safe_text(fecha_hasta)}",
        ParagraphStyle("HeroPerson", parent=styles["body"], fontSize=9.5, leading=14,
                       textColor=TEXT, alignment=TA_LEFT),
    )
    table = Table([[hero_tag, person], [hero_title, person]], colWidths=[usable * .70, usable * .30])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), DARK),
        ("SPAN", (1, 0), (1, 1)),
        ("BOX", (0, 0), (-1, -1), 1.1, BLUE),
        ("LINEBELOW", (0, 0), (0, 0), .6, colors.HexColor("#1E4C68")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 14),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    return table


def _insight_box(title: str, body: str, styles, tone: str = "blue"):
    """Bloque breve para explicar el significado de los datos, no solo mostrarlos."""
    accents = {"blue": BLUE, "green": GREEN, "red": RED, "yellow": colors.HexColor("#EAB308"), "purple": PURPLE}
    backgrounds = {
        "blue": PANEL, "green": colors.HexColor("#103e32"),
        "red": colors.HexColor("#491923"), "yellow": colors.HexColor("#382e13"),
        "purple": colors.HexColor("#261e43"),
    }
    accent = accents.get(tone, BLUE)
    background = backgrounds.get(tone, backgrounds["blue"])
    content = Paragraph(
        f"<b>{_safe_text(title, 100)}</b><br/>{body}",
        ParagraphStyle("InsightBody", parent=styles["body"], fontSize=8.3, leading=11.5,
                       textColor=INK, spaceAfter=0),
    )
    usable = PAGE[0] - 2.4 * cm
    box = Table([["", content]], colWidths=[.16 * cm, usable - .16 * cm])
    box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), background),
        ("BACKGROUND", (0, 0), (0, 0), accent),
        ("BOX", (0, 0), (-1, -1), .45, accent),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (1, 0), (1, 0), 9),
        ("RIGHTPADDING", (1, 0), (1, 0), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return box


def _format_df(df: pd.DataFrame, money_cols: Optional[Iterable[str]] = None) -> pd.DataFrame:
    out = pd.DataFrame() if df is None else df.copy()
    money_cols = set(money_cols or [])
    for col in out.columns:
        if col in money_cols:
            out[col] = out[col].map(_money)
        elif pd.api.types.is_datetime64_any_dtype(out[col]):
            out[col] = pd.to_datetime(out[col], errors="coerce").dt.strftime("%d/%m/%Y").fillna("")
        elif pd.api.types.is_float_dtype(out[col]):
            out[col] = out[col].map(_number)
        else:
            out[col] = out[col].map(_safe_text)
    return out


def _df_table(df: pd.DataFrame, styles, money_cols=None, max_rows=25, col_widths=None, pct_cols=None):
    if df is None or df.empty:
        return Paragraph("No se encontraron datos para esta sección.", styles["body"])
    view = _format_df(df.head(max_rows), money_cols)
    for col in pct_cols or []:
        if col in view.columns:
            view[col] = pd.to_numeric(df.head(max_rows)[col], errors="coerce").map(lambda v: f"{v:.1f}%" if pd.notna(v) else "Sin dato")
    data = [[Paragraph(_safe_text(c), styles["table_header"]) for c in view.columns]]
    for row in view.itertuples(index=False, name=None):
        data.append([Paragraph(_safe_text(v), styles["small"]) for v in row])
    usable = PAGE[0] - 2.4 * cm
    widths = col_widths or [usable / max(len(view.columns), 1)] * len(view.columns)
    table = Table(data, repeatRows=1, colWidths=widths)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#173A59")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#0d1b2e"), colors.HexColor("#10263c")]),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#24445f")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return table


def _wrap_labels(values, width: int = 24):
    """Divide etiquetas largas para que no desaparezcan al lado izquierdo."""
    return ["\n".join(textwrap.wrap(str(v), width=width)) or "Sin dato" for v in values]


def _style_print_axis(ax, grid_axis="y"):
    ax.set_facecolor("#07111F")
    ax.figure.patch.set_facecolor("#0b1728")
    ax.grid(axis=grid_axis, color="#CBD5E1", alpha=0.55, linewidth=0.7)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.spines["left"].set_color("#94A3B8")
    ax.spines["bottom"].set_color("#94A3B8")
    ax.tick_params(axis="both", labelsize=8.5, colors="#dcecf5")
    ax.xaxis.label.set_color("#dcecf5")
    ax.yaxis.label.set_color("#dcecf5")
    ax.yaxis.set_major_formatter(mtick.StrMethodFormatter("${x:,.0f}")) if grid_axis == "y" else None


def _save_fig(fig) -> BytesIO:
    from matplotlib.text import Text
    fig.patch.set_facecolor("#07111F")
    for ax in fig.axes:
        ax.set_facecolor("#07111F")
        # Evita fórmulas de Matplotlib impresas como texto en las escalas logarítmicas.
        for eje,escala in [(ax.xaxis,ax.get_xscale()),(ax.yaxis,ax.get_yscale())]:
            if escala=='log':
                eje.set_minor_formatter(mtick.NullFormatter())
                if type(eje.get_major_formatter()).__name__.startswith('LogFormatter'):
                    eje.set_major_formatter(mtick.FuncFormatter(lambda valor,_:f'{valor:g}'))
        for text in ax.findobj(match=Text):
            text.set_color("#e2e8f0")
        legend = ax.get_legend()
        if legend:
            legend.get_frame().set_facecolor("#0b1728")
            legend.get_frame().set_edgecolor("#24445f")
    buff = BytesIO()
    fig.savefig(buff, format="png", dpi=170, bbox_inches="tight", facecolor="#07111F")
    plt.close(fig)
    buff.seek(0)
    return buff


def _chart_flow(flujo: pd.DataFrame, title="Ingresos, gastos y balance mensual") -> Optional[BytesIO]:
    if flujo is None or flujo.empty or "MES" not in flujo.columns:
        return None
    f = flujo.copy()
    ingresos = pd.to_numeric(f.get("Ingresos", 0), errors="coerce").fillna(0)
    gastos = pd.to_numeric(f.get("Gastos", 0), errors="coerce").fillna(0)
    balance = pd.to_numeric(f.get("Balance", ingresos - gastos), errors="coerce").fillna(0)
    x = list(range(len(f)))
    fig, ax = plt.subplots(figsize=(11.2, 3.8))
    ax.bar([i - .19 for i in x], ingresos, width=.38, label="Ingresos", color=PDF_GREEN, edgecolor="#047857", linewidth=.6)
    ax.bar([i + .19 for i in x], gastos, width=.38, label="Gastos", color=PDF_RED, edgecolor="#BE123C", linewidth=.6)
    ax.plot(x, balance, marker="o", markersize=5.5, linewidth=2.5, label="Balance", color=PDF_BLUE)
    ax.axhline(0, linewidth=.9, color="#64748B")
    ax.set_xticks(x, f["MES"].astype(str).tolist(), rotation=25, ha="right")
    ax.set_ylabel("Valor")
    ax.set_title(title, fontsize=12.5, fontweight="bold", color="#0F172A", pad=14)
    _style_print_axis(ax, "y")
    ax.legend(ncol=3, loc="upper center", bbox_to_anchor=(.5, 1.01), frameon=False)
    fig.subplots_adjust(left=.10, right=.98, top=.82, bottom=.22)
    return _save_fig(fig)



def _chart_savings_evolution(flujo: pd.DataFrame) -> Optional[BytesIO]:
    """Replica la lectura de ahorro en pesos y capacidad de ahorro del dashboard."""
    if flujo is None or flujo.empty or "MES" not in flujo.columns:
        return None
    f = flujo.copy()
    ingresos = pd.to_numeric(f.get("Ingresos", 0), errors="coerce").fillna(0)
    gastos = pd.to_numeric(f.get("Gastos", 0), errors="coerce").fillna(0)
    ahorro = pd.to_numeric(f.get("Balance", ingresos - gastos), errors="coerce").fillna(0)
    capacidad = pd.Series(
        [valor / ingreso * 100 if ingreso else 0.0 for valor, ingreso in zip(ahorro, ingresos)],
        index=f.index,
    )
    x = list(range(len(f)))
    fig, (ax_ahorro, ax_capacidad) = plt.subplots(2, 1, figsize=(11.2, 6.3), sharex=True, gridspec_kw={"hspace": .34})
    colores = [PDF_GREEN if valor >= 0 else PDF_RED for valor in ahorro]
    barras = ax_ahorro.bar(x, ahorro, color=colores, edgecolor="white", linewidth=.8)
    ax_ahorro.axhline(0, linewidth=.9, color="#64748B")
    ax_ahorro.set_title("Ahorro mensual y capacidad de ahorro", fontsize=12.5, fontweight="bold", color="#0F172A", pad=12)
    ax_ahorro.set_ylabel("Ahorro mensual")
    ax_ahorro.yaxis.set_major_formatter(mtick.StrMethodFormatter("${x:,.0f}"))
    _style_print_axis(ax_ahorro, "y")
    ax_ahorro.bar_label(barras, labels=[f"${valor:,.0f}" for valor in ahorro], padding=3, fontsize=7, color="#334155")

    ax_capacidad.plot(x, capacidad, color=PDF_BLUE, linewidth=2.8, marker="o", markersize=5.5)
    ax_capacidad.fill_between(x, 0, capacidad, where=capacidad >= 0, color=PDF_GREEN, alpha=.16)
    ax_capacidad.fill_between(x, 0, capacidad, where=capacidad < 0, color=PDF_RED, alpha=.16)
    ax_capacidad.axhline(0, linewidth=.9, color="#64748B")
    ax_capacidad.set_ylabel("Capacidad (%)")
    ax_capacidad.set_xticks(x, f["MES"].astype(str).tolist(), rotation=25, ha="right")
    ax_capacidad.yaxis.set_major_formatter(mtick.PercentFormatter())
    _style_print_axis(ax_capacidad, "y")
    fig.subplots_adjust(left=.10, right=.98, top=.90, bottom=.16)
    return _save_fig(fig)


def _chart_income_stability(ingresos: pd.DataFrame) -> Optional[BytesIO]:
    if ingresos is None or ingresos.empty or "INGRESOS_FECHA" not in ingresos.columns or "INGRESOS_CANTIDAD" not in ingresos.columns:
        return None
    tmp = ingresos.copy()
    tmp["INGRESOS_FECHA"] = pd.to_datetime(tmp["INGRESOS_FECHA"], errors="coerce", dayfirst=True)
    tmp["INGRESOS_CANTIDAD"] = pd.to_numeric(tmp["INGRESOS_CANTIDAD"], errors="coerce").fillna(0)
    tmp = tmp.dropna(subset=["INGRESOS_FECHA"])
    if tmp.empty:
        return None
    tmp["PERIODO"] = tmp["INGRESOS_FECHA"].dt.strftime("%Y-%m")
    monthly = tmp.groupby("PERIODO")["INGRESOS_CANTIDAD"].sum().sort_index()
    avg = float(monthly.mean()) if not monthly.empty else 0.0
    fig, ax = plt.subplots(figsize=(11.2, 4.0))
    bars = ax.bar(monthly.index, monthly.values, color=PDF_GREEN, edgecolor="white", linewidth=.9)
    ax.axhline(avg, color="#F4B400", linewidth=2.6, linestyle="--", label=f"Promedio ${avg:,.0f}")
    ax.set_title("Estabilidad mensual de los ingresos", fontsize=12.5, fontweight="bold", color="#0F172A", pad=14)
    ax.set_ylabel("Ingreso")
    ax.tick_params(axis="x", rotation=25)
    ax.yaxis.set_major_formatter(mtick.StrMethodFormatter("${x:,.0f}"))
    _style_print_axis(ax, "y")
    ax.legend(frameon=False, loc="upper center")
    ax.bar_label(bars, labels=[f"${v:,.0f}" for v in monthly.values], padding=4, fontsize=7.5, color="#334155")
    fig.subplots_adjust(left=.12, right=.97, top=.80, bottom=.22)
    return _save_fig(fig)


def _chart_income_calendar(ingresos: pd.DataFrame) -> Optional[BytesIO]:
    """Versión imprimible del calendario de ingresos del dashboard."""
    required = {"INGRESOS_FECHA", "INGRESOS_CANTIDAD"}
    if ingresos is None or ingresos.empty or not required.issubset(ingresos.columns):
        return None
    tmp = ingresos.copy()
    tmp["INGRESOS_FECHA"] = pd.to_datetime(tmp["INGRESOS_FECHA"], errors="coerce", dayfirst=True)
    tmp["INGRESOS_CANTIDAD"] = pd.to_numeric(tmp["INGRESOS_CANTIDAD"], errors="coerce").fillna(0)
    tmp = tmp.dropna(subset=["INGRESOS_FECHA"])
    if tmp.empty:
        return None
    category_col = next((c for c in ["INGRESOS_CATEGORIA", "CATEGORIA"] if c in tmp.columns), None)
    tmp["_tipo"] = tmp[category_col].map(_income_type) if category_col else "Sin clasificar"
    tmp["_periodo"] = tmp["INGRESOS_FECHA"].dt.strftime("%Y-%m")
    tmp["_dia"] = tmp["INGRESOS_FECHA"].dt.day.astype(float)
    for _, indices in tmp.groupby("INGRESOS_FECHA").groups.items():
        if len(indices) > 1:
            tmp.loc[list(indices), "_dia"] += pd.Series(range(len(indices)), index=list(indices)).map(lambda pos: (pos - (len(indices) - 1) / 2) * .22)
    periodos = sorted(tmp["_periodo"].unique())
    posicion_y = {periodo: pos for pos, periodo in enumerate(periodos)}
    colores = {"Laborales": "#84CC16", "Residuales": "#2563EB", "Sin clasificar": "#94A3B8"}
    maximo = max(float(tmp["INGRESOS_CANTIDAD"].max()), 1.0)
    tamanos = 45 + 400 * (tmp["INGRESOS_CANTIDAD"] / maximo).pow(.55)
    fig, ax = plt.subplots(figsize=(11.2, max(3.8, .62 * len(periodos) + 1.7)))
    for tipo, bloque in tmp.groupby("_tipo"):
        ax.scatter(
            bloque["_dia"], bloque["_periodo"].map(posicion_y),
            s=tamanos.loc[bloque.index], color=colores.get(tipo, "#94A3B8"), alpha=.80,
            edgecolors="#172033", linewidths=.8, label=tipo,
        )
    ax.set_xlim(.25, 31.75)
    ax.set_xticks(range(1, 32, 2))
    ax.set_yticks(list(posicion_y.values()), list(posicion_y.keys()))
    ax.set_xlabel("Día del mes")
    ax.set_title("Calendario de entradas de ingresos", fontsize=12.5, fontweight="bold", color="#0F172A", pad=12)
    ax.grid(axis="x", color="#E2E8F0", linewidth=.7)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, loc="upper center", ncol=3)
    fig.subplots_adjust(left=.12, right=.98, top=.80, bottom=.18)
    return _save_fig(fig)


def _chart_income_mix(ingresos: pd.DataFrame) -> Optional[BytesIO]:
    if ingresos is None or ingresos.empty or "INGRESOS_CANTIDAD" not in ingresos.columns:
        return None
    category_col = next((c for c in ["INGRESOS_CATEGORIA", "CATEGORIA"] if c in ingresos.columns), None)
    if category_col is None:
        return None
    tmp = ingresos.copy()
    tmp["_monto"] = pd.to_numeric(tmp["INGRESOS_CANTIDAD"], errors="coerce").fillna(0)
    resumen = tmp.assign(_tipo=tmp[category_col].map(_income_type)).groupby("_tipo")["_monto"].sum()
    resumen = resumen[resumen > 0]
    if resumen.empty:
        return None
    colores = {"Laborales": "#84CC16", "Residuales": "#2563EB", "Sin clasificar": "#94A3B8"}
    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    ax.pie(resumen.values, labels=resumen.index, autopct="%1.1f%%", startangle=90,
           colors=[colores.get(indice, "#94A3B8") for indice in resumen.index],
           wedgeprops={"width": .46, "edgecolor": "white", "linewidth": 1.2},
           textprops={"fontsize": 8.5, "color": "#334155"})
    ax.set_title("Composición de ingresos por tipo", fontsize=12.5, fontweight="bold", color="#0F172A", pad=12)
    return _save_fig(fig)


def _chart_budget(flujo: pd.DataFrame) -> Optional[BytesIO]:
    if flujo is None or flujo.empty or "MES" not in flujo.columns or "Presupuesto mensual" not in flujo.columns:
        return None
    f = flujo.copy()
    gasto = pd.to_numeric(f.get("Gastos", 0), errors="coerce").fillna(0)
    pres = pd.to_numeric(f.get("Presupuesto mensual", 0), errors="coerce").fillna(0)
    x = list(range(len(f)))
    bar_colors = [PDF_GREEN if p > 0 and g <= p else PDF_RED if p > 0 else "#94A3B8" for g, p in zip(gasto, pres)]
    fig, ax = plt.subplots(figsize=(11.2, 3.9))
    bars = ax.bar(x, gasto, width=.58, label="Gasto real", color=bar_colors, edgecolor="white", linewidth=.9)
    ax.plot(x, pres, marker="D", markersize=5.5, linewidth=2.8, linestyle="--", label="Presupuesto", color="#F4B400")
    ax.set_xticks(x, f["MES"].astype(str).tolist(), rotation=25, ha="right")
    ax.set_ylabel("Valor")
    ax.set_title("Ejecución mensual frente al presupuesto", fontsize=12.5, fontweight="bold", color="#0F172A", pad=14)
    _style_print_axis(ax, "y")
    ax.legend(frameon=False, loc="upper center", ncol=3)
    fig.subplots_adjust(left=.10, right=.98, top=.80, bottom=.22)
    return _save_fig(fig)


def _budget_category_summary(gastos: pd.DataFrame, presupuesto_categoria: Optional[Dict[str, Any]]) -> pd.DataFrame:
    """Replica la comparación por categoría de la pestaña Presupuesto."""
    columns = ["Categoría", "Gasto", "Presupuesto", "Diferencia", "% ejecutado", "Estado"]
    if gastos is None or gastos.empty or "GASTOS_CATEGORIA" not in gastos.columns:
        return pd.DataFrame(columns=columns)
    tmp = gastos.copy()
    tmp["_monto"] = pd.to_numeric(tmp.get("GASTOS_CANTIDAD", 0), errors="coerce").fillna(0)
    resumen = tmp.groupby("GASTOS_CATEGORIA", dropna=False)["_monto"].sum().reset_index()
    resumen.columns = ["Categoría", "Gasto"]
    presupuesto_categoria = presupuesto_categoria or {}
    clave = lambda valor: " ".join(str(valor).strip().upper().split())
    resumen["Presupuesto"] = resumen["Categoría"].map(lambda categoria: float(presupuesto_categoria.get(clave(categoria), 0) or 0))
    resumen["Diferencia"] = resumen["Gasto"] - resumen["Presupuesto"]
    resumen["% ejecutado"] = resumen.apply(
        lambda fila: fila["Gasto"] / fila["Presupuesto"] * 100 if fila["Presupuesto"] > 0 else 0.0,
        axis=1,
    )
    resumen["Estado"] = resumen.apply(
        lambda fila: "Sin presupuesto" if fila["Presupuesto"] <= 0 else (
            "Controlado" if fila["% ejecutado"] <= 80 else "Atención" if fila["% ejecutado"] <= 100 else "Excedido"
        ),
        axis=1,
    )
    return resumen.sort_values("Diferencia", ascending=False).reset_index(drop=True)


def _chart_budget_categories(resumen: pd.DataFrame, top: int = 10) -> Optional[BytesIO]:
    if resumen is None or resumen.empty:
        return None
    plot = resumen.reindex(resumen["Diferencia"].abs().sort_values(ascending=False).index).head(top).copy()
    plot = plot.sort_values("Diferencia")
    labels = _wrap_labels(plot["Categoría"], width=25)
    y = list(range(len(plot)))
    fig, ax = plt.subplots(figsize=(11.2, max(4.3, .48 * len(plot) + 1.8)))
    ax.barh(y, plot["Presupuesto"], height=.62, color="#CBD5E1", label="Presupuesto", edgecolor="white", linewidth=.8)
    colores = [PDF_RED if estado == "Excedido" else PDF_YELLOW if estado == "Atención" else PDF_GREEN if estado == "Controlado" else "#94A3B8" for estado in plot["Estado"]]
    barras = ax.barh(y, plot["Gasto"], height=.38, color=colores, label="Gasto real", edgecolor="white", linewidth=.8)
    ax.set_yticks(y, labels)
    ax.set_xlabel("Valor")
    ax.set_title("Desviaciones presupuestales por categoría", fontsize=12.5, fontweight="bold", color="#0F172A", pad=12)
    _style_print_axis(ax, "x")
    ax.xaxis.set_major_formatter(mtick.StrMethodFormatter("${x:,.0f}"))
    ax.legend(frameon=False, loc="lower right")
    ax.bar_label(barras, labels=[f"{valor:.0f}%" if presupuesto > 0 else "Sin presupuesto" for valor, presupuesto in zip(plot["% ejecutado"], plot["Presupuesto"])], padding=4, fontsize=7.2, color="#334155")
    fig.subplots_adjust(left=.30, right=.91, top=.86, bottom=.14)
    return _save_fig(fig)


def _chart_debt_rank_v20(deudas, acumulado=False):
    campo = 'Interés acumulado estimado' if acumulado else 'Saldo'
    datos = deudas.sort_values(campo).tail(12)
    if datos.empty:
        return None
    titulo = 'Interés acumulado estimado desde el inicio' if acumulado else 'Mayor saldo pendiente'
    fig, ax = plt.subplots(figsize=(11.2, 4.5))
    barras = ax.barh(_wrap_labels(datos['Nombre'], 24), datos[campo], color='#FF0000', height=.58)
    ax.bar_label(barras, labels=[_money(v) for v in datos[campo]], padding=4, fontsize=8)
    ax.set_title(titulo, fontsize=12, pad=14)
    _style_print_axis(ax, 'x')
    ax.xaxis.set_major_formatter(mtick.FuncFormatter(lambda x, pos: _money(x)))
    ax.margins(x=.30)
    fig.subplots_adjust(left=.25, right=.94, bottom=.18, top=.85)
    return _save_fig(fig)


def _chart_debt_progress(deudas: pd.DataFrame) -> Optional[BytesIO]:
    required = {"Nombre", "Deuda inicial", "Pagado"}
    if deudas is None or deudas.empty or not required.issubset(deudas.columns):
        return None
    tmp = deudas.copy()
    for col in ["Deuda inicial", "Pagado"]:
        tmp[col] = pd.to_numeric(tmp[col], errors="coerce").fillna(0).clip(lower=0)
    tmp["Pendiente"] = pd.to_numeric(tmp["Saldo"], errors="coerce").fillna(0).clip(lower=0) if "Saldo" in tmp else (tmp["Deuda inicial"] - tmp["Pagado"]).clip(lower=0)
    tmp = tmp.sort_values("Deuda inicial").tail(12)
    if tmp.empty:
        return None
    y = list(range(len(tmp)))
    fig, ax = plt.subplots(figsize=(11.2, max(4.2, .47 * len(tmp) + 1.8)))
    ax.barh(y, tmp["Pagado"], color="#00FF00", height=.64, label="Pagado", edgecolor="white", linewidth=.8)
    ax.barh(y, tmp["Pendiente"], left=tmp["Pagado"], color="#FF0000", height=.64, label="Pendiente", edgecolor="white", linewidth=.8)
    ax.set_yticks(y, _wrap_labels(tmp["Nombre"], width=25))
    ax.set_xlabel("Valor")
    ax.set_title("Avance de pago de cada deuda", fontsize=12.5, fontweight="bold", color="#0F172A", pad=12)
    _style_print_axis(ax, "x")
    ax.xaxis.set_major_formatter(mtick.FuncFormatter(lambda x, pos: _money(x)))
    ax.legend(frameon=False, loc="lower right")
    fig.subplots_adjust(left=.29, right=.96, top=.86, bottom=.14)
    return _save_fig(fig)


def _chart_credit_projection(tabla):
    fig, ax = plt.subplots(figsize=(11.2, 3.7))
    inicial = float(tabla.iloc[0]['Saldo pendiente'])
    pagado = inicial - tabla['Saldo pendiente']
    ax.bar(tabla['Cuota'], pagado, color='#00FF00', width=.8, label='Capital amortizado')
    ax.bar(tabla['Cuota'], tabla['Saldo pendiente'], bottom=pagado, color='#FF0000', width=.8, label='Saldo pendiente')
    _style_print_axis(ax, 'y')
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, pos: _money(x)))
    ax.set_xlabel('Cuotas mensuales desde el saldo actual')
    ax.set_ylabel('Capital del crédito')
    ax.set_title('Proyección del saldo por cuota', fontsize=12, pad=12)
    ax.legend(loc='lower center', bbox_to_anchor=(.5, - .40), ncol=2, frameon=False, fontsize=8)
    ax.xaxis.set_major_locator(mtick.MaxNLocator(integer=True, nbins=9))
    fig.subplots_adjust(left=.18, right=.97, top=.85, bottom=.30)
    return _save_fig(fig)


def _chart_credit_payments(tabla):
    pagos = tabla.loc[tabla['Cuota'].gt(0)]
    fig, ax = plt.subplots(figsize=(11.2, 3.7))
    capital = pagos['Capital'] - pagos['Abono extra']
    ax.bar(pagos['Cuota'], capital, color='#00BB66', label='Capital de la cuota')
    ax.bar(pagos['Cuota'], pagos['Intereses'], bottom=capital, color='#FF0000', label='Intereses')
    if pagos['Abono extra'].gt(0).any():
        ax.bar(pagos['Cuota'], pagos['Abono extra'], bottom=capital+pagos['Intereses'], color='#E5A900', label='Abono extra')
    _style_print_axis(ax, 'y')
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, pos: _money(x)))
    ax.set_xlabel('Número de cuota')
    ax.set_title('Composición de los pagos de la simulación', fontsize=12, pad=12)
    ax.legend(loc='lower center', bbox_to_anchor=(.5, -.40), ncol=3, frameon=False, fontsize=8)
    ax.xaxis.set_major_locator(mtick.MaxNLocator(integer=True, nbins=9))
    fig.subplots_adjust(left=.18, right=.97, top=.85, bottom=.30)
    return _save_fig(fig)


def _chart_debt_concentration(deudas: pd.DataFrame) -> Optional[BytesIO]:
    if deudas is None or deudas.empty or not {'Nombre', 'Saldo'}.issubset(deudas.columns):
        return None
    datos = deudas.copy()
    datos['Saldo'] = pd.to_numeric(datos['Saldo'], errors='coerce').fillna(0).clip(lower=0)
    resumen = datos.groupby('Nombre', dropna=False)['Saldo'].sum()
    resumen = resumen[resumen.gt(0)].sort_values(ascending=False)
    if resumen.empty:
        return None
    fig, ax = plt.subplots(figsize=(11.2, 4.7))
    porciones, _, _ = ax.pie(resumen.values, autopct=lambda p: f'{p:.1f}%'.replace('.', ',') if p >= 4 else '',
        startangle=90, colors=[PDF_PALETTE[i % len(PDF_PALETTE)] for i in range(len(resumen))],
        pctdistance=.79, wedgeprops={'width': .38, 'edgecolor': '#07111F', 'linewidth': 2},
        textprops={'fontsize': 9, 'color': '#E2E8F0'})
    ax.text(0,.08,'Saldo total', ha='center', fontsize=10)
    ax.text(0,-.14,_money(resumen.sum()), ha='center', fontsize=12, fontweight='bold')
    etiquetas = [f'{str(nombre)}  |  {_money(valor)}' for nombre, valor in resumen.items()]
    ax.legend(porciones, etiquetas, loc='center left', bbox_to_anchor=(1.05,.5),
        frameon=False, fontsize=8.5, labelspacing=1.3)
    ax.set_title('Concentración del saldo total', fontsize=12, pad=12)
    fig.subplots_adjust(left=.04, right=.62, top=.88, bottom=.08)
    return _save_fig(fig)


def _chart_asset_liquidity(patrimonio: pd.DataFrame, value_col: str, liquidity_col: str) -> Optional[BytesIO]:
    if patrimonio is None or patrimonio.empty or value_col not in patrimonio.columns or liquidity_col not in patrimonio.columns:
        return None
    tmp = patrimonio.copy()
    tmp["_valor"] = pd.to_numeric(tmp[value_col], errors="coerce").fillna(0).abs()
    resumen = tmp.groupby(liquidity_col, dropna=False)["_valor"].sum().sort_values(ascending=True)
    resumen = resumen[resumen > 0]
    if resumen.empty:
        return None
    colores = [PDF_GREEN if "ALTA" in str(nombre).upper() else PDF_YELLOW if "MEDIA" in str(nombre).upper() else PDF_BLUE for nombre in resumen.index]
    fig, ax = plt.subplots(figsize=(11.2, max(3.8, .52 * len(resumen) + 1.6)))
    barras = ax.barh(_wrap_labels(resumen.index, 24), resumen.values, color=colores, edgecolor="white", linewidth=.8)
    ax.set_xlabel("Valor patrimonial")
    ax.set_title("Liquidez patrimonial", fontsize=12.5, fontweight="bold", color="#0F172A", pad=12)
    _style_print_axis(ax, "x")
    ax.xaxis.set_major_formatter(mtick.StrMethodFormatter("${x:,.0f}"))
    ax.bar_label(barras, labels=[f"${valor:,.0f}" for valor in resumen.values], padding=4, fontsize=7.5, color="#334155")
    fig.subplots_adjust(left=.27, right=.91, top=.86, bottom=.14)
    return _save_fig(fig)


def _chart_liquidity_rent_v20(patrimonio):
    from modules.core import calcular_distribucion_renta_patrimonio
    activos = patrimonio.loc[patrimonio["Tipo"].astype(str).str.upper().eq("ACTIVO")].copy()
    activos = activos.loc[activos["Valor neto"].gt(0)]
    renta = calcular_distribucion_renta_patrimonio(activos)
    if activos.empty or renta.empty:
        return None
    liquidez = activos.groupby("Liquidez")["Valor neto"].sum()
    fig, axes = plt.subplots(1,2,figsize=(11.2,4.8))
    for ax, etiquetas, valores, titulo in [
        (axes[0],liquidez.index,liquidez.values,"Liquidez patrimonial"),
        (axes[1],renta["Estado renta"],renta["Valor"],"Patrimonio que produce renta mensual"),
    ]:
        ax.pie(valores,labels=None,autopct=lambda p:f"{p:.1f}%".replace(".",","),pctdistance=.8,
               colors=[PDF_GREEN,PDF_ORANGE,PDF_CYAN,PDF_PURPLE],wedgeprops=dict(width=.35,edgecolor="#07111F"),startangle=55)
        ax.set_title(titulo,fontsize=10,pad=15)
        ax.legend(etiquetas,loc="upper center",bbox_to_anchor=(.5,-.05),fontsize=8,frameon=False,ncol=2)
    fig.subplots_adjust(wspace=.35,bottom=.2,top=.9)
    return _save_fig(fig)


def _chart_wealth_growth_v20(patrimonio, desde, hasta):
    datos = patrimonio.copy()
    datos["Fecha"] = pd.to_datetime(datos["Fecha"],errors="coerce")
    datos = datos.loc[datos["Fecha"].le(pd.Timestamp(hasta))].dropna(subset=["Fecha"])
    if datos.empty:
        return None
    datos["Periodo"] = datos["Fecha"].dt.to_period("M")
    movimientos = datos.groupby("Periodo")["Valor neto"].sum()
    periodos = pd.period_range(movimientos.index.min(),pd.Timestamp(hasta).to_period("M"),freq="M")
    movimientos = movimientos.reindex(periodos,fill_value=0)
    acumulado = movimientos.cumsum()
    seleccion = periodos >= pd.Timestamp(desde).to_period("M")
    if not seleccion.any(): return None
    inicial = float(acumulado[seleccion].iloc[0]-movimientos[seleccion].iloc[0])
    crecimiento = acumulado[seleccion]-inicial
    fig,ax=plt.subplots(figsize=(11.2,4.3))
    ax.bar(range(len(crecimiento)),movimientos[seleccion],bottom=(crecimiento-movimientos[seleccion]),
           color=[PDF_GREEN if v>=0 else PDF_RED for v in movimientos[seleccion]],width=.5)
    ax.plot(range(len(crecimiento)),crecimiento,color=PDF_BLUE,marker="o",linewidth=2)
    ax.set_xticks(range(len(crecimiento)));ax.set_xticklabels([str(p) for p in crecimiento.index])
    ax.set_title("Crecimiento del patrimonio sobre el valor inicial",fontsize=12,pad=15)
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x,pos:_money(x)))
    _style_print_axis(ax)
    ax.axhline(0,color="#94A3B8",linestyle=":")
    fig.subplots_adjust(left=.16,bottom=.17,top=.85)
    return _save_fig(fig)


def _chart_wealth_currency(patrimonio: pd.DataFrame, value_col: str, title: str, investment_only: bool = False) -> Optional[BytesIO]:
    if patrimonio is None or patrimonio.empty or value_col not in patrimonio.columns:
        return None
    currency_col = next((col for col in ["Moneda", "MONEDA", "Divisa"] if col in patrimonio.columns), None)
    if currency_col is None:
        return None
    tmp = patrimonio.copy()
    if investment_only:
        category_col = next((col for col in ["Categoría", "CATEGORIA"] if col in tmp.columns), None)
        if category_col is None:
            return None
        categoria = tmp[category_col].fillna("").astype(str).str.upper()
        tmp = tmp[categoria.str.contains("FONDO DE EMERGENCIA|INVERSION", regex=True, na=False)].copy()
    tmp["_valor"] = pd.to_numeric(tmp[value_col], errors="coerce").fillna(0).abs()
    resumen = tmp.groupby(currency_col, dropna=False)["_valor"].sum()
    resumen = resumen[resumen > 0]
    if resumen.empty:
        return None
    etiquetas = ["Pesos colombianos (COP)" if str(indice).upper() == "COP" else "Dólares estadounidenses (USD)" if str(indice).upper() == "USD" else str(indice) for indice in resumen.index]
    fig, ax = plt.subplots(figsize=(8.2, 4.8))
    ax.pie(resumen.values, labels=etiquetas, autopct="%1.1f%%", startangle=90,
           colors=[PDF_GREEN, PDF_BLUE, PDF_PURPLE, PDF_ORANGE][:len(resumen)],
           wedgeprops={"width": .45, "edgecolor": "white", "linewidth": 1.2},
           textprops={"fontsize": 8, "color": "#334155"})
    ax.set_title(title, fontsize=12.5, fontweight="bold", color="#0F172A", pad=12)
    return _save_fig(fig)


def _chart_score_components(componentes: Iterable[Dict[str, Any]]) -> Optional[BytesIO]:
    tabla = pd.DataFrame(list(componentes or []))
    if tabla.empty or "Indicador" not in tabla.columns or "Puntos" not in tabla.columns:
        return None
    tabla["Puntos"] = pd.to_numeric(tabla["Puntos"], errors="coerce").fillna(0)
    maximo_col = next((col for col in tabla.columns if str(col).upper() in {"MÁXIMO", "MAXIMO"}), None)
    tabla["_maximo"] = pd.to_numeric(tabla[maximo_col], errors="coerce").fillna(0) if maximo_col else tabla["Puntos"]
    tabla = tabla.sort_values("Puntos")
    fig, ax = plt.subplots(figsize=(11.2, max(4.2, .50 * len(tabla) + 1.8)))
    y = list(range(len(tabla)))
    ax.barh(y, tabla["_maximo"], color="#CBD5E1", height=.62, label="Máximo", edgecolor="white", linewidth=.8)
    barras = ax.barh(y, tabla["Puntos"], color=PDF_PURPLE, height=.38, label="Puntos logrados", edgecolor="white", linewidth=.8)
    ax.set_yticks(y, _wrap_labels(tabla["Indicador"], 27))
    ax.set_xlabel("Puntos")
    ax.set_title("Componentes del score financiero", fontsize=12.5, fontweight="bold", color="#0F172A", pad=12)
    _style_print_axis(ax, "x")
    ax.legend(frameon=False, loc="lower right")
    ax.bar_label(barras, labels=[f"{valor:.1f}" for valor in tabla["Puntos"]], padding=4, fontsize=7.5, color="#334155")
    fig.subplots_adjust(left=.30, right=.93, top=.86, bottom=.14)
    return _save_fig(fig)


def _chart_goal_progress(metas: pd.DataFrame) -> Optional[BytesIO]:
    required = {"Meta", "Objetivo", "Actual"}
    if not isinstance(metas, pd.DataFrame) or metas.empty or not required.issubset(metas.columns):
        return None
    tmp = metas.copy()
    for col in ["Objetivo", "Actual"]:
        tmp[col] = pd.to_numeric(tmp[col], errors="coerce").fillna(0).clip(lower=0)
    tmp["Actual visible"] = tmp[["Actual", "Objetivo"]].min(axis=1)
    tmp["Faltante"] = (tmp["Objetivo"] - tmp["Actual visible"]).clip(lower=0)
    tmp = tmp.sort_values("Objetivo").tail(12)
    if tmp.empty:
        return None
    y = list(range(len(tmp)))
    fig, ax = plt.subplots(figsize=(11.2, max(4.2, .50 * len(tmp) + 1.8)))
    ax.barh(y, tmp["Actual visible"], color=PDF_GREEN, height=.62, label="Actual", edgecolor="white", linewidth=.8)
    ax.barh(y, tmp["Faltante"], left=tmp["Actual visible"], color="#24445f", height=.62, label="Faltante", edgecolor="#426481", linewidth=.8)
    ax.set_yticks(y, _wrap_labels(tmp["Meta"], 27))
    ax.set_xlabel("Valor")
    ax.set_title("Progreso de metas financieras", fontsize=12.5, fontweight="bold", color="#0F172A", pad=12)
    _style_print_axis(ax, "x")
    ax.xaxis.set_major_formatter(mtick.StrMethodFormatter("${x:,.0f}"))
    ax.legend(frameon=False, loc="lower right")
    fig.subplots_adjust(left=.30, right=.96, top=.86, bottom=.14)
    return _save_fig(fig)


def _altium_compass(
    *, total_ingresos: float, balance: float, patrimonio: pd.DataFrame,
    ingresos: pd.DataFrame, felicidad: pd.DataFrame, edad: Any,
    fecha_desde: Any, fecha_hasta: Any,
) -> tuple[Optional[BytesIO], Dict[str, float]]:
    """Replica la síntesis Dinero–Tiempo–Bienestar de la Brújula Altium."""
    limitar = lambda valor: max(0.0, min(float(valor), 100.0))
    try:
        edad_num = float(edad)
    except (TypeError, ValueError):
        edad_num = 0.0
    patrimonio_neto = 0.0
    if isinstance(patrimonio, pd.DataFrame) and not patrimonio.empty:
        valor_col = next((col for col in ["Valor neto", "VALOR_NETO", "Valor", "VALOR"] if col in patrimonio.columns), None)
        if valor_col:
            patrimonio_neto = float(pd.to_numeric(patrimonio[valor_col], errors="coerce").fillna(0).sum())
    ing = pd.DataFrame() if ingresos is None else ingresos.copy()
    if not ing.empty:
        ing["_monto"] = pd.to_numeric(ing.get("INGRESOS_CANTIDAD", 0), errors="coerce").fillna(0)
        ing["_fecha"] = pd.to_datetime(ing.get("INGRESOS_FECHA"), errors="coerce", dayfirst=True)
        ing["_periodo"] = ing["_fecha"].dt.to_period("M").astype(str)
        mensual = ing.dropna(subset=["_fecha"]).groupby("_periodo")["_monto"].sum()
        promedio_mensual = float(mensual.mean()) if not mensual.empty else 0.0
        estabilidad = limitar((1 - min(float(mensual.std(ddof=0) / mensual.mean()), 1.0)) * 100) if len(mensual) >= 2 and mensual.mean() else (50.0 if len(mensual) == 1 else 0.0)
        fuente_col = next((col for col in ["INGRESOS_FUENTE", "FUENTE"] if col in ing.columns), None)
        principal_pct = float(ing.groupby(fuente_col)["_monto"].sum().max() / ing["_monto"].sum() * 100) if fuente_col and ing["_monto"].sum() else 100.0
        tipo_col = next((col for col in ["INGRESOS_CATEGORIA", "CATEGORIA"] if col in ing.columns), None)
        no_laboral_pct = float(ing.loc[ing[tipo_col].map(_income_type).eq("Residuales"), "_monto"].sum() / ing["_monto"].sum() * 100) if tipo_col and ing["_monto"].sum() else 0.0
    else:
        promedio_mensual = estabilidad = 0.0
        principal_pct, no_laboral_pct = 100.0, 0.0
    idr = promedio_mensual * edad_num * 1.2
    ratio_idr = patrimonio_neto / idr if idr > 0 else 0.0
    dinero = limitar(limitar((balance / total_ingresos * 100 if total_ingresos else 0.0) / 30 * 100) * .40 + limitar(ratio_idr / 2 * 100) * .35 + estabilidad * .25)
    fel = pd.DataFrame() if felicidad is None else felicidad.copy()
    horas_semana, horas_eficientes_pct = 0.0, 0.0
    if not fel.empty and "HORAS" in fel.columns:
        fel["HORAS"] = pd.to_numeric(fel["HORAS"], errors="coerce").fillna(0)
        total_horas = float(fel["HORAS"].sum())
        inicio, fin = pd.to_datetime(fecha_desde, errors="coerce", dayfirst=True), pd.to_datetime(fecha_hasta, errors="coerce", dayfirst=True)
        semanas = max(((fin - inicio).days + 1) / 7, 1) if pd.notna(inicio) and pd.notna(fin) else 1
        horas_semana = total_horas / semanas
        if "VALOR_HORA" in fel.columns and total_horas:
            fel["VALOR_HORA"] = pd.to_numeric(fel["VALOR_HORA"], errors="coerce").fillna(0)
            referencia = float(fel["VALOR_HORA"].mean())
            horas_eficientes_pct = float(fel.loc[fel["VALOR_HORA"].ge(referencia), "HORAS"].sum() / total_horas * 100) if referencia else 0.0
    carga = 100 if horas_semana <= 30 else 100 - (horas_semana - 30) * 3 if horas_semana <= 40 else 70 - (horas_semana - 40) * 3.75 if horas_semana <= 48 else 40 - (horas_semana - 48) * (40 / 22) if horas_semana <= 70 else 0
    tiempo = limitar(limitar(carga) * .70 + horas_eficientes_pct * .30)
    bienestar = limitar(limitar((1 - max(principal_pct - 25, 0) / 75) * 100) * .45 + limitar(no_laboral_pct / 30 * 100) * .25 + estabilidad * .30)
    valores = {"Dinero": dinero, "Tiempo": tiempo, "Bienestar financiero": bienestar}
    angulos = [0, 2 * 3.14159265 / 3, 4 * 3.14159265 / 3, 0]
    radios = list(valores.values()) + [dinero]
    fig, ax = plt.subplots(figsize=(7.6, 5.4), subplot_kw={"projection": "polar"})
    ax.plot(angulos, radios, color=PDF_CYAN, linewidth=2.8, marker="o")
    ax.fill(angulos, radios, color=PDF_CYAN, alpha=.22)
    ax.set_xticks(angulos[:-1], list(valores.keys()))
    ax.set_ylim(0, 100)
    ax.set_yticks([25, 50, 75, 100])
    ax.set_yticklabels(["25", "50", "75", "100"], fontsize=7)
    ax.set_title("Brújula Altium · equilibrio actual", fontsize=12.5, fontweight="bold", color="#0F172A", pad=20)
    return _save_fig(fig), valores


def _chart_happiness_company(felicidad: pd.DataFrame) -> Optional[BytesIO]:
    """Muestra valor hora por empresa, que es la lectura central de la pestaña Felicidad."""
    if felicidad is None or felicidad.empty or "EMPRESA" not in felicidad.columns:
        return None
    tmp = felicidad.copy()
    for col in ["VALOR", "HORAS", "VALOR_HORA"]:
        if col in tmp.columns:
            tmp[col] = pd.to_numeric(tmp[col], errors="coerce")
    if "VALOR_HORA" not in tmp.columns:
        return None
    resumen = (
        tmp.dropna(subset=["VALOR_HORA"])
        .groupby("EMPRESA", as_index=False)
        .agg(VALOR_HORA=("VALOR_HORA", "mean"), HORAS=("HORAS", "sum"), VALOR=("VALOR", "sum"))
        .sort_values("VALOR_HORA", ascending=True)
        .tail(12)
    )
    if resumen.empty:
        return None
    labels = _wrap_labels(resumen["EMPRESA"], 23)
    fig, ax = plt.subplots(figsize=(11.2, max(4.2, .45 * len(resumen) + 1.6)))
    bars = ax.barh(labels, resumen["VALOR_HORA"], color=PDF_PURPLE, edgecolor="white", linewidth=.8)
    ax.set_xlabel("Valor promedio por hora")
    ax.set_title("Valor por hora según empresa o trabajo", fontsize=12.5, fontweight="bold", color="#0F172A", pad=12)
    _style_print_axis(ax, "x")
    ax.xaxis.set_major_formatter(mtick.StrMethodFormatter("${x:,.0f}"))
    ax.bar_label(bars, labels=[f"${v:,.0f}" for v in resumen["VALOR_HORA"]], padding=4, fontsize=7.5, color="#334155")
    fig.subplots_adjust(left=.31, right=.91, top=.88, bottom=.14)
    return _save_fig(fig)


def _chart_happiness_income_mix(felicidad: pd.DataFrame) -> Optional[BytesIO]:
    if felicidad is None or felicidad.empty or "CATEGORIA" not in felicidad.columns or "VALOR" not in felicidad.columns:
        return None
    tmp = felicidad.copy()
    tmp["VALOR"] = pd.to_numeric(tmp["VALOR"], errors="coerce").fillna(0)
    tmp["TIPO"] = tmp["CATEGORIA"].map(_income_type)
    resumen = tmp.groupby("TIPO")["VALOR"].sum()
    if resumen.empty or resumen.sum() == 0:
        return None
    fig, ax = plt.subplots(figsize=(7.4, 4.3))
    ax.pie(resumen.values, labels=resumen.index, autopct="%1.1f%%", startangle=90,
           colors=[PDF_GREEN, PDF_BLUE], wedgeprops={"width": .46, "edgecolor": "white", "linewidth": 1.2},
           textprops={"fontsize": 8.5, "color": "#334155"})
    ax.set_title("Ingresos laborales y residuales", fontsize=12.5, fontweight="bold", color="#0F172A", pad=12)
    return _save_fig(fig)

def _chart_group(df: pd.DataFrame, group_col: str, value_col: str, title: str, top=12) -> Optional[BytesIO]:
    if df is None or df.empty or group_col not in df.columns or value_col not in df.columns:
        return None
    values = pd.to_numeric(df[value_col], errors="coerce").fillna(0)
    tmp = df.assign(_valor=values).groupby(group_col, dropna=False)["_valor"].sum().sort_values().tail(top)
    if tmp.empty:
        return None
    labels = _wrap_labels(tmp.index, width=25)
    height = max(4.2, 0.42 * len(tmp) + 1.6)
    fig, ax = plt.subplots(figsize=(11.2, height))
    colors_bar = [PDF_PALETTE[i % len(PDF_PALETTE)] for i in range(len(tmp))]
    bars = ax.barh(labels, tmp.values, color=colors_bar, edgecolor="white", linewidth=.7)
    ax.set_xlabel("Valor")
    ax.set_title(title, fontsize=12.5, fontweight="bold", color="#0F172A", pad=12)
    _style_print_axis(ax, "x")
    ax.xaxis.set_major_formatter(mtick.StrMethodFormatter("${x:,.0f}"))
    ax.bar_label(bars, labels=[f"${v:,.0f}" for v in tmp.values], padding=4, fontsize=7.5, color="#334155")
    # Margen izquierdo amplio: evita que desaparezcan categorías largas.
    fig.subplots_adjust(left=.31, right=.91, top=.88, bottom=.14)
    return _save_fig(fig)


def _chart_fixed_variable(gastos: pd.DataFrame) -> Optional[BytesIO]:
    if gastos is None or gastos.empty or "TIPO_GASTO" not in gastos.columns:
        return None
    tmp = gastos.groupby("TIPO_GASTO")["GASTOS_CANTIDAD"].sum().sort_values(ascending=False)
    if tmp.empty:
        return None
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    colors_pie = [PDF_PALETTE[i % len(PDF_PALETTE)] for i in range(len(tmp))]
    ax.pie(tmp.values, labels=_wrap_labels(tmp.index, 17), autopct="%1.1f%%", startangle=90,
           colors=colors_pie, pctdistance=.78, labeldistance=1.08,
           wedgeprops={"width": .43, "edgecolor": "white", "linewidth": 1.2},
           textprops={"fontsize": 8, "color": "#334155"})
    ax.set_title("Composición por tipo de gasto", fontsize=12.5, fontweight="bold", color="#0F172A", pad=12)
    fig.subplots_adjust(left=.08, right=.92, top=.86, bottom=.08)
    return _save_fig(fig)


def _chart_top_expense_movements(gastos: pd.DataFrame, top: int = 10) -> Optional[BytesIO]:
    """Muestra los movimientos individuales que más explican el gasto."""
    if gastos is None or gastos.empty or "GASTOS_CANTIDAD" not in gastos.columns:
        return None
    label_col = next(
        (col for col in ["GASTOS_DESCRIPCION", "GASTOS_SUBCATEGORIA", "GASTOS_CATEGORIA"] if col in gastos.columns),
        None,
    )
    if not label_col:
        return None
    tmp = gastos.copy()
    tmp["_valor"] = pd.to_numeric(tmp["GASTOS_CANTIDAD"], errors="coerce").fillna(0)
    tmp["_etiqueta"] = tmp[label_col].fillna("Sin descripción").astype(str).str.strip().replace("", "Sin descripción")
    top_movimientos = tmp.nlargest(top, "_valor").sort_values("_valor", ascending=True)
    if top_movimientos.empty:
        return None
    fig, ax = plt.subplots(figsize=(11.2, max(4.2, 0.48 * len(top_movimientos) + 1.7)))
    colores = ["#FF4D6D" if i == len(top_movimientos) - 1 else "#F97316" for i in range(len(top_movimientos))]
    barras = ax.barh(_wrap_labels(top_movimientos["_etiqueta"], width=28), top_movimientos["_valor"], color=colores, edgecolor="white", linewidth=.8)
    ax.set_xlabel("Valor del movimiento")
    ax.set_title("Top movimientos individuales de gasto", fontsize=12.5, fontweight="bold", color="#0F172A", pad=12)
    _style_print_axis(ax, "x")
    ax.xaxis.set_major_formatter(mtick.StrMethodFormatter("${x:,.0f}"))
    ax.bar_label(barras, labels=[f"${valor:,.0f}" for valor in top_movimientos["_valor"]], padding=4, fontsize=7.5, color="#334155")
    fig.subplots_adjust(left=.30, right=.91, top=.88, bottom=.14)
    return _save_fig(fig)


def _best_label_column(df: pd.DataFrame, title: str, value_col: str) -> Optional[str]:
    """Selecciona una columna descriptiva y evita usar fechas como etiquetas laterales."""
    candidates = [c for c in df.columns if c != value_col]
    if not candidates:
        return None

    title_norm = str(title).upper()
    if "PATRIMONIO" in title_norm:
        preferred_tokens = ["NOMBRE", "CONCEPTO", "ACTIVO", "ELEMENTO", "DESCRIP", "TIPO", "CATEGORIA"]
    elif "BIENESTAR" in title_norm or "FELICIDAD" in title_norm:
        preferred_tokens = ["NOMBRE", "TRABAJO", "EMPRESA", "FUENTE", "CONCEPTO", "DESCRIP", "ACTIVIDAD"]
    else:
        preferred_tokens = ["NOMBRE", "CONCEPTO", "DESCRIP", "CATEGORIA", "TIPO", "FUENTE"]

    def is_date_column(col: str) -> bool:
        name = str(col).upper()
        if any(token in name for token in ["FECHA", "DATE", "MES", "AÑO", "ANIO"]):
            return True
        return pd.api.types.is_datetime64_any_dtype(df[col])

    non_date = [c for c in candidates if not is_date_column(c)]
    search_space = non_date or candidates

    for token in preferred_tokens:
        for col in search_space:
            if token in str(col).upper():
                return col

    text_cols = [
        c for c in search_space
        if not pd.api.types.is_numeric_dtype(df[c])
        and df[c].astype(str).str.strip().replace({"nan": "", "None": ""}).ne("").any()
    ]
    if text_cols:
        return max(text_cols, key=lambda c: df[c].astype(str).nunique(dropna=True))
    return search_space[0] if search_space else None


def _best_value_column(df: pd.DataFrame, title: str) -> Optional[str]:
    numeric = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    if not numeric:
        return None
    title_norm = str(title).upper()
    preferred = (
        ["VALOR", "MONTO", "SALDO", "PATRIMONIO"]
        if "PATRIMONIO" in title_norm
        else ["FELICIDAD", "PUNTAJE", "VALOR", "INDICE", "NIVEL"]
    )
    for token in preferred:
        for col in numeric:
            if token in str(col).upper():
                return col
    return numeric[-1]


def _chart_generic_numeric(df: pd.DataFrame, title: str) -> Optional[BytesIO]:
    if df is None or df.empty:
        return None
    value_col = _best_value_column(df, title)
    if value_col is None:
        return None
    label_col = _best_label_column(df, title, value_col)
    if label_col is None:
        return None
    return _chart_group(df, label_col, value_col, title, top=10)


def _projection_data(gastos: pd.DataFrame, ingresos: pd.DataFrame, settings=None) -> Optional[Dict[str, Any]]:
    """Replica la proyeccion del dashboard: salarios laborales menos gastos."""
    ing = pd.DataFrame() if ingresos is None else ingresos.copy()
    gas = pd.DataFrame() if gastos is None else gastos.copy()
    if ing.empty and gas.empty:
        return None

    salary_monthly = pd.Series(dtype=float)
    if {"INGRESOS_FECHA", "INGRESOS_CANTIDAD"}.issubset(ing.columns):
        ing["INGRESOS_FECHA"] = pd.to_datetime(ing["INGRESOS_FECHA"], errors="coerce", dayfirst=True)
        ing["INGRESOS_CANTIDAD"] = pd.to_numeric(ing["INGRESOS_CANTIDAD"], errors="coerce").fillna(0)
        ing = ing.dropna(subset=["INGRESOS_FECHA"])
        category_col = next((c for c in ["INGRESOS_CATEGORIA", "CATEGORIA"] if c in ing.columns), None)
        if category_col:
            ing = ing[ing[category_col].map(_income_type).eq("Laborales")].copy()
        ing["_PERIODO"] = ing["INGRESOS_FECHA"].dt.to_period("M")
        salary_monthly = ing.groupby("_PERIODO")["INGRESOS_CANTIDAD"].sum()

    expense_monthly = pd.Series(dtype=float)
    if {"GASTOS_FECHA", "GASTOS_CANTIDAD"}.issubset(gas.columns):
        gas["GASTOS_FECHA"] = pd.to_datetime(gas["GASTOS_FECHA"], errors="coerce", dayfirst=True)
        gas["GASTOS_CANTIDAD"] = pd.to_numeric(gas["GASTOS_CANTIDAD"], errors="coerce").fillna(0)
        gas = gas.dropna(subset=["GASTOS_FECHA"])
        gas["_PERIODO"] = gas["GASTOS_FECHA"].dt.to_period("M")
        expense_monthly = gas.groupby("_PERIODO")["GASTOS_CANTIDAD"].sum()

    known = sorted(set(salary_monthly.index).union(expense_monthly.index))
    if not known:
        return None
    observed = pd.period_range(known[0], known[-1], freq="M")
    avg_salary = float(salary_monthly.reindex(observed, fill_value=0).mean())
    avg_expense = float(expense_monthly.reindex(observed, fill_value=0).mean())
    monthly_net = avg_salary - avg_expense
    months = 30 * 12
    settings = settings or {}
    maximum = max(int(round(float(salary_monthly.sum()) - float(expense_monthly.sum()))), 0)
    capital = min(max(float(settings.get("capital_proyeccion") if settings.get("capital_proyeccion") is not None else maximum),0),maximum)
    monthly_net *= capital/maximum if maximum else 0
    rate = float(settings.get("tasa_proyeccion",10))
    simple = [capital + monthly_net * month for month in range(1, months + 1)]
    monthly_rate = ((1+rate/100) ** (1 / 12)) - 1
    compound = []
    for _ in range(months):
        capital = capital * (1 + monthly_rate) + monthly_net
        compound.append(capital)
    horizons = [10, 20, 30]
    return {
        "rate": rate,
        "capital": min(max(float(settings.get("capital_proyeccion") if settings.get("capital_proyeccion") is not None else maximum),0),maximum),
        "observed_months": len(observed),
        "avg_salary": avg_salary,
        "avg_expense": avg_expense,
        "monthly_net": monthly_net,
        "monthly_rate": monthly_rate,
        "simple": simple,
        "compound": compound,
        "simple_horizons": {year: simple[year * 12 - 1] for year in horizons},
        "compound_horizons": {year: compound[year * 12 - 1] for year in horizons},
    }


def _projection_cards(values: Dict[int, float], styles, prefix: str = ""):
    cells = []
    for year in [10, 20, 30]:
        value = float(values.get(year, 0))
        accent = GREEN if value >= 0 else RED
        state = "Saldo a favor" if value >= 0 else "Deuda proyectada"
        cell = Table([
            [Paragraph(f"{prefix}{year} AÑOS", styles["card_title"])],
            [Paragraph(_money(abs(value)), styles["card_value"])],
            [Paragraph(state, ParagraphStyle("ProjectionState", parent=styles["small"],
                                             textColor=accent, alignment=TA_CENTER, fontName="Helvetica-Bold"))],
        ], colWidths=[(PAGE[0] - 3.2 * cm) / 3], rowHeights=[.52 * cm, .72 * cm, .48 * cm])
        cell.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), PANEL),
            ("BOX", (0, 0), (-1, -1), 1.0, accent),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        cells.append(cell)
    outer = Table([cells], colWidths=[(PAGE[0] - 2.4 * cm) / 3] * 3)
    outer.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4)]))
    return outer


def _chart_projection(data: Dict[str, Any], compound: bool = False) -> Optional[BytesIO]:
    values = data["compound"] if compound else data["simple"]
    if not values:
        return None
    years = [month / 12 for month in range(1, len(values) + 1)]
    positive = [v if v >= 0 else 0 for v in values]
    negative = [v if v < 0 else 0 for v in values]
    fig, ax = plt.subplots(figsize=(11.2, 4.0))
    ax.plot(years, values, color=PDF_YELLOW if compound else PDF_BLUE, linewidth=2.7)
    ax.fill_between(years, 0, positive, color=PDF_GREEN, alpha=.20)
    ax.fill_between(years, 0, negative, color=PDF_RED, alpha=.20)
    ax.axhline(0, color="#64748B", linewidth=1)
    for year in [10, 20, 30]:
        value = values[year * 12 - 1]
        ax.axvline(year, color="#94A3B8", linewidth=.8, linestyle=":")
        ax.scatter([year], [value], s=46, color=PDF_GREEN if value >= 0 else PDF_RED,
                   edgecolor="white", linewidth=.8, zorder=5)
        ax.annotate(f"{year} años\n{_money(value)}", (year, value), xytext=(0, 10),
                    textcoords="offset points", ha="center", fontsize=7.6,
                    color="#172033", fontweight="bold")
    ax.set_xlim(0, 31)
    ax.set_xlabel("Horizonte en años")
    ax.set_ylabel("Capital acumulado")
    ax.set_title(f"Saldo mensual invertido al {data['rate']:g}% efectivo anual" if compound
                 else "Continuidad del saldo promedio entre salarios y gastos",
                 fontsize=12.5, fontweight="bold", color="#0F172A", pad=14)
    _style_print_axis(ax, "y")
    fig.subplots_adjust(left=.12, right=.97, top=.82, bottom=.18)
    return _save_fig(fig)


def _add_chart(story, buff: Optional[BytesIO], width=24.6 * cm, height=8.0 * cm):
    if buff:
        image = Image(buff)
        scale = min(width / image.imageWidth, height / image.imageHeight)
        image.drawWidth = image.imageWidth * scale
        image.drawHeight = image.imageHeight * scale
        image.hAlign = "CENTER"
        story.extend([Spacer(1, .25 * cm), image, Spacer(1, .2 * cm)])


def generar_proyeccion_credito_pdf(nombre, tabla, detalle, vista_grafico, *, tabla_base=None, cuota_excel=None, pago_mensual=None):
    """Exporta la simulación activa de un solo crédito."""
    output = BytesIO()
    doc = BaseDocTemplate(
        output, pagesize=PAGE, leftMargin=1.2 * cm, rightMargin=1.2 * cm,
        topMargin=.9 * cm, bottomMargin=.9 * cm,
        title="Proyección de amortización", author="Altium Financiero",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height)
    doc.addPageTemplates(PageTemplate(
        id="amortizacion", frames=[frame],
        onPage=lambda canvas, doc: _footer(canvas, doc, "Proyección de amortización"),
    ))
    styles = _styles()
    story = [
        Paragraph("Proyección de amortización", styles["title"]),
        Paragraph(_safe_text(nombre), styles["subtitle"]),
        Paragraph("El valor de la cuota incluye seguro y costos extra. El desembolso total agrega los abonos extraordinarios.", styles["answer"]),
    ]
    story.extend([
        _kpi_table([
            ('Cuotas restantes estimadas', str(len(tabla) - 1)),
            ('Cuota con seguro y cargos', _money(cuota_excel or 0)),
            ('Intereses futuros estimados', _money(tabla['Intereses'].sum())),
            ('Total por pagar estimado', _money(tabla['Pago'].sum())),
            ('Cuota mensual', _money(pago_mensual or 0)),
        ], styles),
        Spacer(1, .2 * cm),
    ])
    if tabla_base is not None:
        cuotas_ahorradas = max(0, len(tabla_base) - len(tabla))
        dinero_ahorrado = max(0.0, float(tabla_base['Intereses'].sum() - tabla['Intereses'].sum()))
        story.extend([
            _kpi_table([
                ('Tiempo ahorrado', str(cuotas_ahorradas) + ' cuotas'),
                ('Dinero ahorrado', _money(dinero_ahorrado)),
            ], styles),
            Paragraph('Ahorro de dinero calculado sobre los intereses frente a la proyección de referencia del dashboard.', styles['small']),
        ])
    chart = _chart_credit_payments if vista_grafico == "Cuota mensual" else _chart_credit_projection
    _add_chart(story, chart(tabla))
    story.extend([
        PageBreak(),
        Paragraph("Tabla de proyección", styles["section"]),
        _df_table(detalle, styles, money_cols=list(detalle.columns[1:]), max_rows=len(detalle),
                  col_widths=[(doc.width - 12) / len(detalle.columns)] * len(detalle.columns)),
    ])
    doc.build(story)
    return output.getvalue()


def generar_informe_financiero_pdf(
    *, nombre_persona: str, edad_persona: Any, fecha_desde: Any, fecha_hasta: Any,
    total_ingresos: float, total_gastos: float, balance: float,
    gastos: pd.DataFrame, ingresos: pd.DataFrame, flujo: pd.DataFrame,
    deudas: pd.DataFrame, patrimonio: pd.DataFrame, metas: Any,
    felicidad: pd.DataFrame, presupuesto_periodo: float = 0.0,
    presupuesto_categoria: Optional[Dict[str, Any]] = None,
    score_financiero: Optional[float] = None,
    componentes_score: Optional[Iterable[Dict[str, Any]]] = None,
    dashboard_data: Optional[Dict[str, Any]] = None,
) -> bytes:
    styles = _styles()
    output = BytesIO()
    doc = BaseDocTemplate(
        output, pagesize=PAGE, leftMargin=1.2 * cm, rightMargin=1.2 * cm,
        topMargin=.9 * cm, bottomMargin=.9 * cm,
        title="Colombia Prospera V26 - Informe por preguntas", author="Altium Financiero",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    doc.addPageTemplates(PageTemplate(id="main", frames=[frame], onPage=_footer))
    story = [
        Spacer(1, .4 * cm),
        _hero_table(nombre_persona, edad_persona, fecha_desde, fecha_hasta, styles),
        Spacer(1, .55 * cm),
        _kpi_table([
            ("Ingresos", _money(total_ingresos)), ("Gastos", _money(total_gastos)),
            ("Balance", _money(balance)),
            ("Capacidad de ahorro", f"{(balance / total_ingresos * 100):.1f}%" if total_ingresos else "0,0%"),
        ], styles),
        Spacer(1, .6 * cm),
        Paragraph("Una lectura visual de las ocho secciones del dashboard, con indicadores, graficos comparativos y escenarios de ahorro a largo plazo. Las proyecciones son orientativas y dependen del periodo filtrado.", styles["body"]),
        PageBreak(),
    ]

    # 1. Resumen
    story += [_question_header(0, styles), Spacer(1, .25 * cm)]
    deuda_saldo = float(pd.to_numeric(deudas.get("Saldo", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()) if deudas is not None and not deudas.empty else 0.0
    story.append(_kpi_table([
        ("Resultado", "Superávit" if balance >= 0 else "Déficit"),
        ("Transacciones", f"{len(gastos):,}".replace(",", ".")),
        ("Presupuesto del periodo", _money(presupuesto_periodo)),
        ("Saldo de deudas", _money(deuda_saldo)),
    ], styles))
    from modules.report_v20 import resumen_noche, sankey_noche, distribucion_noche, frecuencia_noche, perfil_semanal_pdf, polar_semanal_pdf, anillos_distribucion_pdf, mapas_categorias_pdf
    if flujo is not None and not flujo.empty:
        ahorro_mes = float(flujo["Balance"].mean())
        meses_ingreso = flujo.loc[flujo["Ingresos"].gt(0), "Ingresos"]
        ingreso_medio = float(meses_ingreso.mean()) if not meses_ingreso.empty else 0.0
        story.extend([
            Spacer(1, .3*cm), Paragraph("Ahorro y liquidez", styles["section"]),
            _kpi_table([
                ("Ahorro mensual", _money(ahorro_mes)),
                ("Ahorro anual", _money(ahorro_mes*12)),
                ("Referencia para invertir", _money(ingreso_medio*.20)),
                ("Referencia para ahorrar", _money(ingreso_medio*.10)),
            ], styles),
            Spacer(1, .15*cm),
            Paragraph("Referencias del dashboard: 20% y 10% del ingreso promedio de los meses con ingresos. Ahorro anual proyectado a partir del balance mensual medio.", styles["small"]),
        ])
    _add_chart(story, _chart_flow(flujo), height=6.0*cm)
    if total_ingresos:
        gasto_pct_resumen = total_gastos / total_ingresos * 100
        resumen_texto = (
            f"El periodo deja un <b>{'superávit' if balance >= 0 else 'déficit'} de {_money(abs(balance))}</b>. "
            f"Por cada $100 recibidos se utilizaron aproximadamente <b>${gasto_pct_resumen:.0f}</b> en gastos. "
            + ("Existe margen para ahorrar, invertir o reducir deuda." if balance >= 0
               else "El gasto supera la capacidad de ingreso y requiere ajustar el presupuesto o aumentar ingresos.")
        )
    else:
        resumen_texto = "No existen ingresos suficientes para medir la relación entre gasto, ahorro y capacidad financiera."
    story.append(_insight_box("Lectura del periodo", resumen_texto, styles, "green" if balance >= 0 else "red"))
    story.append(PageBreak())
    story += [Spacer(1,.25*cm),Paragraph("Indicadores de riesgo y composición - Altium Noche",styles["section"])]
    _add_chart(story,_save_fig(resumen_noche(gastos,total_ingresos,balance)),height=12.5*cm)
    story.append(Paragraph("Deudas / ingresos usa pagos detectados por texto en los gastos, no saldos de Pasivos. Capacidad de ahorro = balance / ingresos × 100; referencias: 30% para deuda y 20% para ahorro. Sin ingresos positivos se muestra ausencia de datos. La dona muestra la composición de fijos y variables; su centro conserva el total registrado.",styles["small"]))
    story.append(PageBreak())
    story += [Spacer(1,.25*cm), Paragraph("Flujo general de tu dinero",styles["section"])]
    figura_sankey=sankey_noche(gastos,ingresos)
    if figura_sankey is not None:
        _add_chart(story,_save_fig(figura_sankey),height=13.5*cm)
        story.append(Paragraph("Movimientos positivos de los filtros activos. Se excluyen devoluciones y ajustes negativos. Disponible no significa ahorro realizado; déficit no identifica una fuente de financiación. Los enlaces de distintos niveles representan el mismo dinero.",styles["small"]))
    story.append(PageBreak())

    # Promedios sobre todo el calendario, igual que Resumen.
    inicio_pdf = pd.to_datetime(fecha_desde, dayfirst=True).date()
    cierre_pdf = pd.to_datetime(fecha_hasta, dayfirst=True).date()
    diario, semanal, mensual, dias, meses = calcular_promedios_gasto(total_gastos, inicio_pdf, cierre_pdf)
    story += [Paragraph("Promedios de gasto", styles["section"]),
              _kpi_table([("Diario", _money(diario)), ("Semanal", _money(semanal)), ("Mensual equivalente", _money(mensual))], styles),
              Paragraph(f"Total dividido entre {dias} días calendario, incluidos días sin gastos. Semanal = diario × 7. Mensual = total dividido entre {meses:.2f} meses equivalentes; cada mes parcial cuenta por su proporción de días.", styles["small"])]
    _add_chart(story,_save_fig(distribucion_noche(gastos,[diario,semanal,mensual],panel=0)),height=9*cm)
    story.append(Paragraph("Barras verticales: promedios sobre todo el calendario, incluidos los días sin movimientos.",styles["small"]))
    story += [PageBreak(), Paragraph("Perfil por día de la semana",styles["section"])]
    _add_chart(story,_save_fig(perfil_semanal_pdf(gastos,inicio_pdf,cierre_pdf)),height=9*cm)
    story.append(Paragraph("Promedio por día de la semana = gasto neto acumulado de ese día / número de fechas de ese día en el periodo. Incluye fechas sin movimientos como cero y los ajustes negativos. Se respetan las categorías y fechas filtradas.",styles["small"]))
    story += [PageBreak(), Paragraph("Distribución de montos de gasto",styles["section"])]
    _add_chart(story,_save_fig(distribucion_noche(gastos,[diario,semanal,mensual],panel=1)),height=10*cm)
    story.append(Paragraph("Intervalos logarítmicos de montos positivos. La altura cuenta transacciones; ceros y ajustes negativos se excluyen de esta distribución. Las etiquetas del eje se reducen y separan para facilitar su lectura.",styles["small"]))
    if not gastos.empty:
        regla = gastos.groupby(["GASTOS_CATEGORIA", "GASTOS_SUBCATEGORIA"], dropna=False, as_index=False)["GASTOS_CANTIDAD"].sum()
        regla["Grupo"] = [clasificar_regla(c, sub) for c, sub in regla[["GASTOS_CATEGORIA", "GASTOS_SUBCATEGORIA"]].itertuples(index=False, name=None)]
        for indice, cambios in (dashboard_data or {}).get("regla_ediciones", {}).get("edited_rows", {}).items():
            if int(indice) in regla.index and cambios.get("Grupo") in ["Necesidades", "Gustos", "Ahorro"]:
                regla.loc[int(indice), "Grupo"] = cambios["Grupo"]
        grupos = regla.groupby("Grupo")["GASTOS_CANTIDAD"].sum()
        montos = [float(grupos.get(g, 0)) for g in ["Necesidades", "Gustos", "Ahorro"]]
        montos.append(max(total_ingresos-total_gastos, 0))
        nombres = ["Necesidades", "Gustos", "Ahorro", "No utilizado"]
        objetivos = [.5, .3, .2, None]
        colores = [PDF_BLUE, PDF_PURPLE, PDF_YELLOW, PDF_GREEN]
        for i, limite in enumerate(objetivos[:3]):
            if total_ingresos > 0 and montos[i] > total_ingresos*limite:
                colores[i] = "#FF1A1A"
        tabla_regla = pd.DataFrame({"Grupo":nombres,"Monto":montos,
            "% ingresos":[_number(v/total_ingresos*100)+"%" if total_ingresos>0 else "Sin ingresos" for v in montos],
            "Referencia":["50%", "30%", "20%", "Sin asignar"]})
        story += [PageBreak(), Paragraph("Distribución general del dinero y Regla 50/30/20", styles["section"])]
        if sum(montos)>0:
            _add_chart(story,_save_fig(anillos_distribucion_pdf(gastos,total_ingresos,nombres,montos,colores)),height=10*cm)
        story.append(_df_table(tabla_regla,styles,money_cols=["Monto"]))
        story.append(Paragraph("Porcentajes calculados sobre ingresos. Rojo: supera la referencia; en ahorro significa superar la meta. No utilizado no es ahorro realizado. Si hay déficit, las salidas superan el 100% de los ingresos y las porciones representan su reparto.",styles["small"]))
    story.append(PageBreak())

    # Nuevas vistas del Resumen. Los importes y los períodos vienen de la app.
    resumen_actual = (dashboard_data or {}).get('resumen_v22')
    if resumen_actual:
        from modules.report_resumen_v22 import graficos_diario_mapa, graficos_momentum_escudos
        story.append(Paragraph("Flujo diario y mapa de gastos", styles['section']))
        story.append(Paragraph(f"Período filtrado: {_safe_text(fecha_desde)} - {_safe_text(fecha_hasta)}. Valores en COP.",styles['small']))
        _add_chart(story,graficos_diario_mapa(resumen_actual),height=11.6*cm)
        items_mapa=resumen_actual.get('mapa_items',[])
        if items_mapa:
            detalle_mapa=' · '.join(f"{i+1}. {_safe_text(n)}: {_money(v)}" for i,(n,v) in enumerate(items_mapa))
            story.append(Paragraph(detalle_mapa,styles['small']))
        story.append(Paragraph("El acumulado parte de cero y no equivale al saldo bancario. Las áreas del mapa corresponden a categorías con gasto neto positivo; los ajustes negativos se conservan en el total neto.",styles['small']))
        story.extend([PageBreak(),Paragraph("Momentum y escudo de estado",styles['section'])])
        _add_chart(story,graficos_momentum_escudos(resumen_actual),height=11.7*cm)
        metas_texto=' · '.join(f"{_safe_text(r['grupo'])}: {r['objetivo']} %" for r in resumen_actual.get('escudos',[]))
        story.append(Paragraph('Metas del escudo: '+metas_texto+'. Se calculan sobre los ingresos del filtro; el saldo no utilizado no cuenta como ahorro realizado.',styles['small']))
        if resumen_actual.get('momentum_nota'):
            story.append(Paragraph(_safe_text(resumen_actual['momentum_nota'],max_len=600),styles['small']))
        tabla_momentum=resumen_actual.get('momentum_tabla')
        if tabla_momentum is not None:
            nuevos=tabla_momentum.loc[tabla_momentum['Estado'].eq('Gasto nuevo')]
            if not nuevos.empty:
                story.append(Paragraph('Gastos nuevos sin base porcentual anterior: '+' · '.join(f"{_safe_text(n)}: {_money(v)}" for n,v in nuevos[['Categoría','Gasto actual']].itertuples(index=False,name=None)),styles['small']))
        story.append(PageBreak())
    # Última vista de Resumen, igual que en pantalla.
    story += [Paragraph("Distribución por días - calendario polar",styles["section"])]
    _add_chart(story,_save_fig(polar_semanal_pdf(gastos,inicio_pdf,cierre_pdf)),height=13*cm)
    story.append(Paragraph("Cada anillo representa una semana de lunes a domingo, de la más antigua dentro a la más reciente fuera. Solo se dibujan las fechas filtradas. Verde: $0; amarillo: promedio neto de todos los días filtrados, incluidos ceros; naranja y rojo: superior al promedio, hasta rojo intenso en el doble del promedio. Los negativos quedan verdes. La lista lateral identifica las fechas incluidas por semana.",styles["small"]))
    story.append(PageBreak())

    # 2. Gastos
    story += [_question_header(1, styles), Spacer(1, .2 * cm)]
    if gastos is not None and not gastos.empty:
        cat = gastos.groupby("GASTOS_CATEGORIA", dropna=False).agg(Monto=("GASTOS_CANTIDAD", "sum"), Transacciones=("GASTOS_CANTIDAD", "count")).reset_index().sort_values("Monto", ascending=False)
        _add_chart(story, _chart_group(gastos, "GASTOS_CATEGORIA", "GASTOS_CANTIDAD", "Principales categorías de gasto"), height=8.6 * cm)
        if not cat.empty:
            categoria_top = cat.iloc[0]
            participacion_top = float(categoria_top["Monto"]) / float(cat["Monto"].sum()) * 100 if float(cat["Monto"].sum()) else 0
            concentracion_txt = (
                f"La categoría <b>{_safe_text(categoria_top['GASTOS_CATEGORIA'])}</b> concentra <b>{participacion_top:.1f}%</b> del gasto total. "
                + ("Es una concentración alta: cualquier ajuste en esta categoría tendría un efecto importante en el resultado." if participacion_top >= 40
                   else "El gasto está relativamente distribuido; conviene revisar también las siguientes categorías del ranking.")
            )
            story += [Spacer(1, .12 * cm), _insight_box("Qué explica el gasto", concentracion_txt, styles, "yellow" if participacion_top >= 40 else "blue")]
        fixed_chart = _chart_fixed_variable(gastos)
        if fixed_chart:
            _add_chart(story, fixed_chart, width=15.0 * cm, height=8.0 * cm)
        if "GASTOS_SUBCATEGORIA" in gastos.columns:
            _add_chart(story, _chart_group(
                gastos, "GASTOS_SUBCATEGORIA", "GASTOS_CANTIDAD",
                "Subcategorias con mayor gasto", top=12,
            ), height=8.6 * cm)
        _add_chart(story, _chart_top_expense_movements(gastos), height=8.6 * cm)
        mapa_categorias, anillos_categorias = mapas_categorias_pdf(gastos)
        story += [PageBreak(), Paragraph("En qué categorías gasto - mapa de descripciones",styles["section"])]
        _add_chart(story,_save_fig(mapa_categorias),height=12*cm)
        story.append(Paragraph("Cada categoría contiene las descripciones con importe agrupado positivo. Las devoluciones o ajustes que dejan saldo no positivo no ocupan área; el total representado puede diferir del gasto neto.",styles["small"]))
        story += [PageBreak(), Paragraph("Categorías y subcategorías - Sunburst",styles["section"])]
        _add_chart(story,_save_fig(anillos_categorias),height=12*cm)
        story.append(Paragraph("Vista estática de la jerarquía. Categorías en el anillo interior y subcategorías en el exterior. La leyenda muestra la participación del importe positivo representado. La exploración de categorías y los tooltips se utilizan en la aplicación.",styles["small"]))
        chart_frecuencia=frecuencia_noche(gastos)
        if chart_frecuencia is not None:
            story.append(PageBreak())
            _add_chart(story,_save_fig(chart_frecuencia),height=9*cm)
            story.append(Paragraph("Ambos ejes son logarítmicos. El tamaño y el color representan el monto acumulado, sin dividirlo entre el número de movimientos. Se excluyen subcategorías con monto neto no positivo.",styles["small"]))

        story.append(PageBreak())
        story.append(_df_table(cat, styles, money_cols=["Monto"], max_rows=18))
        top_cols = [c for c in ["GASTOS_FECHA", "GASTOS_DESCRIPCION", "GASTOS_CATEGORIA", "GASTOS_SUBCATEGORIA", "GASTOS_CANTIDAD"] if c in gastos.columns]
        if top_cols:
            story += [Spacer(1, .35 * cm), Paragraph("Movimientos individuales que más explican el gasto", styles["section"])]
            top_mov = gastos[top_cols].sort_values("GASTOS_CANTIDAD", ascending=False).head(15)
            story.append(_df_table(top_mov, styles, money_cols=["GASTOS_CANTIDAD"], max_rows=15))
    else:
        story.append(Paragraph("No hay gastos para el periodo seleccionado.", styles["body"]))
    story.append(PageBreak())

    # 3. Tendencias
    story += [_question_header(2, styles), Spacer(1, .2 * cm)]
    if flujo is not None and len(flujo) >= 2:
        gastos_tend = pd.to_numeric(flujo.get("Gastos", 0), errors="coerce").fillna(0)
        balances_tend = pd.to_numeric(flujo.get("Balance", 0), errors="coerce").fillna(0)
        gasto_anterior, gasto_ultimo = float(gastos_tend.iloc[-2]), float(gastos_tend.iloc[-1])
        cambio_gasto = (gasto_ultimo - gasto_anterior) / gasto_anterior * 100 if gasto_anterior else 0.0
        direccion = "aumentó" if cambio_gasto > 0 else "disminuyó" if cambio_gasto < 0 else "se mantuvo estable"
        balance_ultimo = float(balances_tend.iloc[-1])
        tendencia_texto = (
            f"Frente al mes anterior, el gasto <b>{direccion} {abs(cambio_gasto):.1f}%</b>. "
            f"El último balance mensual fue <b>{_money(balance_ultimo)}</b>. "
            + ("El periodo reciente sigue generando saldo a favor." if balance_ultimo >= 0 else "El último mes cerró en déficit y merece revisar qué categorías explicaron el aumento.")
        )
        story += [_insight_box("Qué cambió recientemente", tendencia_texto, styles, "green" if balance_ultimo >= 0 else "red"), Spacer(1, .08 * cm)]
    _add_chart(story, _chart_flow(flujo, "Evolución mensual del flujo financiero"), height=7.2 * cm)
    _add_chart(story, _chart_savings_evolution(flujo), height=10.3 * cm)
    cols = [c for c in ["MES", "Ingresos", "Gastos", "Balance", "Balance acumulado", "Capacidad ahorro %"] if flujo is not None and c in flujo.columns]
    story.append(_df_table(flujo[cols] if cols else flujo, styles, money_cols=["Ingresos", "Gastos", "Balance", "Balance acumulado"], max_rows=18))
    story.append(PageBreak())

    # Escenarios de largo plazo incluidos en la pestaña Tendencias.
    projection = _projection_data(gastos, ingresos, dashboard_data)
    story += [Paragraph("PROYECCIONES DE LARGO PLAZO", styles["section"]), Spacer(1, .12 * cm)]
    if projection:
        story.append(Paragraph(
            f"Capital inicial: {_money(projection['capital'])}. Base mensual observada en {projection['observed_months']} meses: salarios laborales promedio de "
            f"<b>{_money(projection['avg_salary'])}</b>, gastos promedio de <b>{_money(projection['avg_expense'])}</b> "
            f"y saldo neto de <b>{_money(projection['monthly_net'])}</b>.", styles["body"],
        ))
        story += [Spacer(1, .25 * cm), Paragraph("Escenario 1 - Continuidad del ritmo actual", styles["question"])]
        story.append(_projection_cards(projection["simple_horizons"], styles))
        _add_chart(story, _chart_projection(projection), height=8.1 * cm)
        story += [Spacer(1, .2 * cm), Paragraph(f"Escenario 2 - Saldo invertido al {projection['rate']:g}% efectivo anual", styles["question"])]
        story.append(_projection_cards(projection["compound_horizons"], styles, prefix=f"{projection['rate']:g}% EA / "))
        _add_chart(story, _chart_projection(projection, compound=True), height=8.1 * cm)
        diferencia_interes = projection["compound_horizons"][30] - projection["simple_horizons"][30]
        story.append(_insight_box(
            "Cómo leer los escenarios",
            f"Sin rendimiento, el resultado depende únicamente del saldo mensual promedio. Al invertir al {projection['rate']:g}% EA, "
            f"la diferencia estimada al año 30 sería de <b>{_money(diferencia_interes)}</b> por efecto de la capitalización. "
            f"Se usa una tasa mensual equivalente de <b>{projection['monthly_rate'] * 100:.3f}%</b>. No se incluyen inflación, impuestos ni cambios futuros en salarios o gastos.",
            styles, "purple",
        ))
    else:
        story.append(Paragraph("No hay salarios laborales o gastos con fechas validas suficientes para construir la proyeccion.", styles["body"]))
    story.append(PageBreak())

    # 4. Presupuesto
    story += [_question_header(3, styles), Spacer(1, .2 * cm)]
    presupuesto_total_pdf = float(pd.to_numeric(flujo.get("Presupuesto mensual", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()) if flujo is not None and not flujo.empty else float(presupuesto_periodo or 0)
    gasto_total_pdf = float(pd.to_numeric(flujo.get("Gastos", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()) if flujo is not None and not flujo.empty else float(total_gastos)
    disponible_pdf = presupuesto_total_pdf - gasto_total_pdf
    ejecucion_pdf = gasto_total_pdf / presupuesto_total_pdf * 100 if presupuesto_total_pdf else 0.0
    story.append(_kpi_table([
        ("Presupuesto", _money(presupuesto_total_pdf)),
        ("Ejecutado", _money(gasto_total_pdf)),
        ("Disponible", _money(disponible_pdf)),
        ("Ejecución", f"{ejecucion_pdf:.1f}%"),
    ], styles))
    presupuesto_categorias_pdf = _budget_category_summary(gastos, presupuesto_categoria)
    if not presupuesto_categorias_pdf.empty:
        conteo_estados = presupuesto_categorias_pdf["Estado"].value_counts()
        story += [Spacer(1, .14 * cm), _kpi_table([
            ("Controlado", str(int(conteo_estados.get("Controlado", 0)))),
            ("Atención", str(int(conteo_estados.get("Atención", 0)))),
            ("Excedido", str(int(conteo_estados.get("Excedido", 0)))),
            ("Sin presupuesto", str(int(conteo_estados.get("Sin presupuesto", 0)))),
        ], styles)]
    if presupuesto_total_pdf > 0:
        if ejecucion_pdf > 100:
            presupuesto_texto = f"Se superó el presupuesto en <b>{_money(abs(disponible_pdf))}</b>. La ejecución llegó a <b>{ejecucion_pdf:.1f}%</b>, por lo que el siguiente paso es identificar las categorías responsables del exceso."
            presupuesto_tono = "red"
        elif ejecucion_pdf >= 90:
            presupuesto_texto = f"El gasto está muy cerca del límite: se ha utilizado <b>{ejecucion_pdf:.1f}%</b> y quedan <b>{_money(disponible_pdf)}</b>. Hay poco margen para movimientos no previstos."
            presupuesto_tono = "yellow"
        else:
            presupuesto_texto = f"La ejecución se mantiene dentro del plan en <b>{ejecucion_pdf:.1f}%</b>, con <b>{_money(disponible_pdf)}</b> todavía disponibles."
            presupuesto_tono = "green"
        story += [Spacer(1, .14 * cm), _insight_box("Estado del presupuesto", presupuesto_texto, styles, presupuesto_tono)]
    _add_chart(story, _chart_budget(flujo), height=6.9 * cm)
    _add_chart(story, _chart_budget_categories(presupuesto_categorias_pdf), height=8.4 * cm)
    budget_cols = [c for c in ["MES", "Gastos", "Presupuesto mensual", "Diferencia vs presupuesto", "Estado presupuesto"] if flujo is not None and c in flujo.columns]
    story.append(_df_table(flujo[budget_cols] if budget_cols else flujo, styles, money_cols=["Gastos", "Presupuesto mensual", "Diferencia vs presupuesto"], max_rows=10))
    if not presupuesto_categorias_pdf.empty:
        story += [Spacer(1, .28 * cm), Paragraph("Semáforo y cumplimiento por categoría", styles["section"])]
        story.append(_df_table(
            presupuesto_categorias_pdf,
            styles,
            money_cols=["Gasto", "Presupuesto", "Diferencia"],
            pct_cols=["% ejecutado"],
            max_rows=18,
        ))
    story.append(PageBreak())

    # 5. Ingresos
    story += [_question_header(4, styles), Spacer(1, .2 * cm)]
    if ingresos is None or ingresos.empty or "INGRESOS_CANTIDAD" not in ingresos.columns:
        story.append(Paragraph("No hay ingresos registrados para el periodo seleccionado.", styles["body"]))
    else:
        ing = ingresos.copy()
        ing["INGRESOS_CANTIDAD"] = pd.to_numeric(ing["INGRESOS_CANTIDAD"], errors="coerce").fillna(0)
        if "INGRESOS_FECHA" in ing.columns:
            ing["INGRESOS_FECHA"] = pd.to_datetime(ing["INGRESOS_FECHA"], errors="coerce", dayfirst=True)
            ing["PERIODO"] = ing["INGRESOS_FECHA"].dt.strftime("%Y-%m")
        total_ing_pdf = float(ing["INGRESOS_CANTIDAD"].sum())
        meses_ing_pdf = max(int(ing.get("PERIODO", pd.Series(dtype=str)).dropna().nunique()), 1)
        promedio_ing_pdf = total_ing_pdf / meses_ing_pdf
        fuente_col = next((c for c in ["INGRESOS_FUENTE", "FUENTE"] if c in ing.columns), None)
        tipo_col = next((c for c in ["INGRESOS_CATEGORIA", "CATEGORIA"] if c in ing.columns), None)
        fuente_principal_pdf = "Sin fuente"
        pct_principal_pdf = 0.0
        numero_fuentes_pdf = 0
        resumen_fuentes_pdf = pd.Series(dtype=float)
        if fuente_col:
            resumen_fuentes_pdf = ing.groupby(fuente_col, dropna=False)["INGRESOS_CANTIDAD"].sum().sort_values(ascending=False)
            numero_fuentes_pdf = int(resumen_fuentes_pdf.size)
            if not resumen_fuentes_pdf.empty:
                fuente_principal_pdf = str(resumen_fuentes_pdf.index[0])
                pct_principal_pdf = float(resumen_fuentes_pdf.iloc[0]) / total_ing_pdf * 100 if total_ing_pdf else 0.0
        if tipo_col:
            ing["TIPO_INGRESO"] = ing[tipo_col].map(_income_type)
        else:
            ing["TIPO_INGRESO"] = "Sin clasificar"
        resumen_tipo_pdf = ing.groupby("TIPO_INGRESO")["INGRESOS_CANTIDAD"].sum()
        laboral_pdf = float(resumen_tipo_pdf.get("Laborales", 0))
        no_laboral_pdf = float(resumen_tipo_pdf.get("Residuales", 0))
        sin_clasificar_pdf = float(resumen_tipo_pdf.get("Sin clasificar", 0))
        pct_no_laboral_pdf = no_laboral_pdf / total_ing_pdf * 100 if total_ing_pdf else 0.0
        participaciones_pdf = resumen_fuentes_pdf / total_ing_pdf if total_ing_pdf and not resumen_fuentes_pdf.empty else pd.Series(dtype=float)
        hhi_pdf = float(participaciones_pdf.pow(2).sum() * 10000) if not participaciones_pdf.empty else 10000.0
        mensual_pdf = ing.groupby("PERIODO")["INGRESOS_CANTIDAD"].sum() if "PERIODO" in ing.columns else pd.Series(dtype=float)
        cv_pdf = float(mensual_pdf.std(ddof=0) / mensual_pdf.mean() * 100) if len(mensual_pdf) > 1 and mensual_pdf.mean() else 0.0
        recurrencia_pdf = (
            float(ing.dropna(subset=["INGRESOS_FECHA"]).groupby(fuente_col)["PERIODO"].nunique().mean())
            if fuente_col and "INGRESOS_FECHA" in ing.columns and not ing.empty else 0.0
        )
        score_pdf = round(max(0.0, min(100.0,
            30 * (1 - min(hhi_pdf, 10000) / 10000)
            + 30 * (1 - min(cv_pdf, 100) / 100)
            + 20 * min(recurrencia_pdf / meses_ing_pdf, 1)
            + 15 * (1 - pct_principal_pdf / 100)
            + (5 if sin_clasificar_pdf == 0 else max(0, 5 * (1 - sin_clasificar_pdf / total_ing_pdf)))
        )), 1)
        story.append(_kpi_table([
            ("Ingresos totales", _money(total_ing_pdf)),
            ("Promedio mensual", _money(promedio_ing_pdf)),
            ("Fuentes activas", str(numero_fuentes_pdf)),
            ("Calidad ingresos", f"{score_pdf:.1f}/100"),
        ], styles))
        story += [Spacer(1, .2 * cm), _kpi_table([
            ("Laborales", _money(laboral_pdf)),
            ("Residuales", _money(no_laboral_pdf)),
            ("Sin clasificar", _money(sin_clasificar_pdf)),
            ("Residual %", f"{pct_no_laboral_pdf:.1f}%"),
        ], styles)]
        dependencia_txt = (
            f"La principal fuente es <b>{_safe_text(fuente_principal_pdf)}</b> y aporta <b>{pct_principal_pdf:.1f}%</b> del ingreso. "
            + ("Existe una dependencia alta: una interrupción de esa fuente afectaría de forma importante el flujo mensual. Conviene fortalecer fuentes complementarias." if pct_principal_pdf > 60
               else "La distribución entre fuentes reduce la dependencia de un solo pagador.")
            + f" Los ingresos residuales representan <b>{pct_no_laboral_pdf:.1f}%</b> del total."
        )
        story += [Spacer(1, .2 * cm), _insight_box("Estabilidad y dependencia de ingresos", dependencia_txt, styles, "yellow" if pct_principal_pdf > 60 else "green")]
        _add_chart(story, _chart_income_stability(ingresos), height=8.2 * cm)
        if fuente_col:
            _add_chart(story, _chart_group(ing, fuente_col, "INGRESOS_CANTIDAD", "Principales fuentes de ingreso"), height=8.3 * cm)
        _add_chart(story, _chart_income_calendar(ingresos), height=7.6 * cm)
        _add_chart(story, _chart_income_mix(ingresos), width=15.0 * cm, height=8.0 * cm)
        story += [Spacer(1, .25 * cm), Paragraph("Composición por tipo de ingreso", styles["section"])]
        tipo_res_pdf = ing.groupby("TIPO_INGRESO", dropna=False)["INGRESOS_CANTIDAD"].sum().reset_index().sort_values("INGRESOS_CANTIDAD", ascending=False)
        story.append(_df_table(tipo_res_pdf, styles, money_cols=["INGRESOS_CANTIDAD"], max_rows=15))
        ing_cols = [c for c in ["INGRESOS_FECHA", "MES", "INGRESOS_FUENTE", "INGRESOS_CATEGORIA", "INGRESOS_CANTIDAD", "INGRESOS_DESCRIPCION"] if c in ing.columns]
        story += [Spacer(1, .3 * cm), Paragraph("Detalle de ingresos", styles["section"])]
        story.append(_df_table(ing[ing_cols] if ing_cols else ing, styles, money_cols=["INGRESOS_CANTIDAD"], max_rows=25))
    story.append(PageBreak())

    # 6. Deudas
    story += [_question_header(5, styles), Spacer(1, .2 * cm)]
    if deudas is not None and not deudas.empty:
        from modules.report_deudas import preparar_deudas, proyeccion_deuda, credito_frances, metodo_credito
        deuda_pdf = preparar_deudas(deudas, cierre_pdf)
        deuda_pdf["Capital + interés estimado"] = deuda_pdf["Pago económico estimado"]
        total_inicial_pdf = float(deuda_pdf.get("Deuda inicial", pd.Series(dtype=float)).sum())
        total_saldo_pdf = float(deuda_pdf.get("Saldo", pd.Series(dtype=float)).sum())
        total_pagado_pdf = float(deuda_pdf.get("Pagado", pd.Series(dtype=float)).sum())
        avance_pdf = total_pagado_pdf / total_inicial_pdf * 100 if total_inicial_pdf else 0.0
        interes_pond_pdf = (
            float((deuda_pdf["Interés"] * deuda_pdf["Saldo"]).sum() / total_saldo_pdf * 100)
            if total_saldo_pdf and {"Interés", "Saldo"}.issubset(deuda_pdf.columns) else 0.0
        )
        story.append(_kpi_table([
            ("Deuda inicial", _money(total_inicial_pdf)),
            ("Saldo pendiente", _money(total_saldo_pdf)),
            ("Abonado a capital", _money(total_pagado_pdf)),
            ("Avance global", f"{avance_pdf:.1f}%"),
            ("Interés ponderado", f"{interes_pond_pdf:.2f}%"),
        ], styles))
        if {"Nombre", "Saldo"}.issubset(deuda_pdf.columns):
            _add_chart(story, _chart_debt_rank_v20(deuda_pdf), height=8.3 * cm)
            _add_chart(story, _chart_debt_concentration(deuda_pdf), width=24.6 * cm, height=8.0 * cm)
        _add_chart(story, _chart_debt_progress(deuda_pdf), height=8.5 * cm)
        if {"Nombre", "Interés", "Saldo"}.issubset(deuda_pdf.columns):
            deuda_pdf["Interés %"] = deuda_pdf["Interés"] * 100
            deuda_pdf["Costo mensual estimado"] = deuda_pdf["Interés"] * deuda_pdf["Saldo"]
            deuda_pdf["Costo anual estimado"] = deuda_pdf["Costo mensual estimado"] * 12
            _add_chart(story, _chart_debt_rank_v20(deuda_pdf, acumulado=True), height=8.3*cm)
            story += [PageBreak(), Paragraph("Capital abonado e intereses estimados", styles["section"]),
                      _df_table(deuda_pdf[["Nombre","Pagado","Costo mensual estimado","Interés acumulado estimado","Capital + interés estimado"]],styles,
                                money_cols=["Pagado","Costo mensual estimado","Interés acumulado estimado","Capital + interés estimado"]),
                      Paragraph("Capital abonado = deuda inicial menos saldo. Capital + interés estimado no representa pagos históricos confirmados. Los créditos ingleses cuentan meses completos vencidos desde Inicio del crédito; los demás conservan la aproximación temporal del dashboard. Se utiliza saldo promedio: si hubo abonos, faltan sus fechas para reconstruir el interés real. Una fecha vacía no permite estimar el acumulado.",styles["small"])]
            prioridad_pdf = deuda_pdf.sort_values(["Interés", "Saldo"], ascending=[False, False]).copy()
            prioridad_pdf["Prioridad"] = range(1, len(prioridad_pdf) + 1)
            prioridad_pdf["Participación saldo %"] = prioridad_pdf["Saldo"] / total_saldo_pdf * 100 if total_saldo_pdf else 0.0
            cols_deuda_pdf = [c for c in ["Prioridad", "Nombre", "Interés %", "Deuda inicial", "Pagado", "Saldo", "Avance", "Costo anual estimado", "Participación saldo %"] if c in prioridad_pdf.columns]
            story += [Spacer(1, .25 * cm), Paragraph("Prioridad de pago y costo estimado", styles["section"])]
            story.append(_df_table(prioridad_pdf[cols_deuda_pdf], styles, money_cols=["Deuda inicial", "Pagado", "Saldo", "Costo anual estimado"], max_rows=25))
            primera = prioridad_pdf.iloc[0]
            deuda_tono = "red" if interes_pond_pdf >= 20 else "yellow" if total_saldo_pdf > 0 else "green"
            story += [Spacer(1, .2 * cm), _insight_box(
                "Qué deuda conviene atender primero",
                f"Por el método avalancha, la primera obligación es <b>{_safe_text(primera.get('Nombre', 'Sin nombre'))}</b>, "
                f"con tasa de <b>{float(primera.get('Interés %', 0)):.2f}%</b> y saldo de <b>{_money(primera.get('Saldo', 0))}</b>. "
                f"En conjunto ya se ha pagado <b>{avance_pdf:.1f}%</b> de la deuda inicial. El costo anual es una aproximación y no reemplaza el extracto contractual.",
                styles, deuda_tono,
            )]
        else:
            story.append(_df_table(deuda_pdf, styles, money_cols=["Deuda inicial", "Interés", "Saldo", "Pagado"], max_rows=25))
        simulaciones = (dashboard_data or {}).get('simulaciones_deudas', {})
        for posicion, (_, credito) in enumerate(deudas.iterrows(), start=1):
            if not metodo_credito(credito) or float(credito.get('Saldo', 0)) <= 0:
                continue
            story += [PageBreak(), Paragraph('Proyección de crédito · ' + metodo_credito(credito) + ': ' + _safe_text(credito.get('Nombre', 'Sin nombre')), styles['section'])]
            try:
                proyeccion = proyeccion_deuda(credito, simulaciones.get(str(posicion)))
            except (ValueError, TypeError, OverflowError) as exc:
                story.append(Paragraph('No se pudo calcular esta proyección: ' + _safe_text(str(exc), 300), styles['body']))
                continue
            if proyeccion is None:
                story.append(Paragraph('Falta una cuota mensual válida o el plazo total para estimarla. Completa esos datos en el dashboard y vuelve a preparar el informe.', styles['body']))
                continue
            tabla = proyeccion['tabla']
            modalidad = 'Reducir cuota' if proyeccion['modo'] == 'cuota' else 'Reducir tiempo'
            story += [Spacer(1, .25 * cm), _kpi_table([
                ('Saldo de partida', _money(proyeccion['saldo'])),
                ('Cuotas restantes', str(len(tabla) - 1)),
                ('Cuota después de abonos' if proyeccion['abonos'] and proyeccion['modo'] == 'cuota' else 'Cuota de capital e intereses', _money(proyeccion['cuota_resultado'])),
                ('Intereses futuros', _money(tabla['Intereses'].sum())),
            ], styles)]
            story += [Spacer(1, .15 * cm), _kpi_table([
                ('Total por pagar', _money(tabla['Pago'].sum())),
                ('Abonos aplicados', _money(tabla['Abono extra'].sum())),
                ('Tiempo ahorrado', str(proyeccion['meses_ahorrados']) + ' meses'),
                ('Dinero ahorrado', _money(proyeccion['ahorro_intereses'])),
            ], styles)]
            cuota_nota = 'Cuota calculada o editada en la simulación activa del dashboard.'
            story += [Spacer(1, .15 * cm), Paragraph(
                modalidad + '. Tasa mensual: ' + _number(proyeccion['tasa'] * 100) + ' %. ' + cuota_nota +
                ' Se incluyen solo los abonos aplicados en la simulación; los cambios de la tabla sin aplicar no se exportan. Ahorro de dinero = intereses evitados frente a la proyección sin abonos. Los seguros y costos extra se reflejan en el desembolso total de la tabla.', styles['small'])]
            _add_chart(story, _chart_credit_projection(tabla), height=7.3 * cm)
            story += [PageBreak(), Paragraph('Cuotas de la simulación: ' + _safe_text(credito.get('Nombre', 'Sin nombre')), styles['section'])]
            _add_chart(story, _chart_credit_payments(tabla), height=7.3 * cm)
            story += [PageBreak(), Paragraph('Tabla de proyección: ' + _safe_text(credito.get('Nombre', 'Sin nombre')), styles['section']),
                Paragraph('Importes sin decimales visibles, con puntos de miles. Los cálculos conservan la precisión completa. Cuota 0 es el saldo inicial. Valor cuota incluye seguro y costos extra. Pago total corresponde al pago aplicado al crédito. Desembolso total = valor cuota + abono extra.', styles['small']), Spacer(1, .15 * cm)]
            detalle = proyeccion['detalle'].copy()
            detalle['Abono extra'] = detalle['Abono extra'].map(lambda v: _money(v) if v else '')
            story.append(_df_table(detalle, styles,
                money_cols=[c for c in detalle.columns if c not in ('Cuota número', 'Abono extra')],
                max_rows=len(detalle)))
    else:
        story.append(Paragraph("No hay deudas registradas.", styles["body"]))
    story.append(PageBreak())

    # 7. Patrimonio
    story += [_question_header(6, styles), Spacer(1, .2 * cm)]
    if patrimonio is None or patrimonio.empty:
        story.append(Paragraph("No hay registros patrimoniales para el periodo seleccionado.", styles["body"]))
    else:
        pat_pdf = patrimonio.copy()
        for col in ["Valor actual", "Saldo pendiente", "Valor neto", "VALOR", "Valor", "MONTO", "Monto", "SALDO", "Saldo"]:
            if col in pat_pdf.columns:
                pat_pdf[col] = pd.to_numeric(pat_pdf[col], errors="coerce").fillna(0)
        valor_col = next((c for c in ["Valor neto", "VALOR_NETO", "Valor actual", "VALOR", "Valor", "MONTO", "Monto"] if c in pat_pdf.columns), None)
        tipo_col = next((c for c in ["Tipo", "TIPO"] if c in pat_pdf.columns), None)
        nombre_col = next((c for c in ["Descripción", "DESCRIPCION", "Subcategoría", "SUBCATEGORIA", "Categoría", "CATEGORIA", "Entidad", "ENTIDAD"] if c in pat_pdf.columns), None)
        if valor_col:
            if tipo_col:
                tipo_norm_pdf = pat_pdf[tipo_col].astype(str).str.upper().str.strip()
                activos_pdf = float(pat_pdf.loc[tipo_norm_pdf.eq("ACTIVO"), valor_col].abs().sum())
                pasivos_pdf = float(pat_pdf.loc[~tipo_norm_pdf.eq("ACTIVO"), valor_col].abs().sum())
            else:
                activos_pdf = float(pat_pdf.loc[pat_pdf[valor_col] >= 0, valor_col].sum())
                pasivos_pdf = abs(float(pat_pdf.loc[pat_pdf[valor_col] < 0, valor_col].sum()))
            neto_pdf = activos_pdf - pasivos_pdf
            endeuda_pdf = pasivos_pdf / activos_pdf * 100 if activos_pdf else 0
            liquidez_col = next((c for c in ["Liquidez", "LIQUIDEZ"] if c in pat_pdf.columns), None)
            liquidos_pdf = 0.0
            if liquidez_col:
                liq_norm_pdf = pat_pdf[liquidez_col].astype(str).str.upper()
                liquidos_pdf = float(pat_pdf.loc[liq_norm_pdf.str.contains("ALTA|MEDIA|LIQUID", regex=True, na=False) & tipo_norm_pdf.eq("ACTIVO"), valor_col].abs().sum())
            liquidez_pct_pdf = liquidos_pdf / activos_pdf * 100 if activos_pdf else 0.0
            story.append(_kpi_table([
                ("Activos", _money(activos_pdf)), ("Pasivos", _money(pasivos_pdf)),
                ("Patrimonio neto", _money(neto_pdf)), ("Pasivos / activos", f"{endeuda_pdf:.1f}%"),
                ("Activos líquidos", _money(liquidos_pdf)),
            ], styles))
            if nombre_col:
                # El eje usa nombres o descripciones; nunca fechas.
                chart_pat = _chart_group(pat_pdf.assign(**{nombre_col: pat_pdf[nombre_col].fillna("Sin nombre").astype(str)}), nombre_col, valor_col, "Composición del patrimonio por nombre", top=14)
                _add_chart(story, chart_pat, height=7.6 * cm)
            if liquidez_col:
                _add_chart(story, _chart_liquidity_rent_v20(pat_pdf), height=8.4 * cm)
            _add_chart(story, _chart_wealth_currency(pat_pdf, valor_col, "Patrimonio por moneda"), width=15.0 * cm, height=8.0 * cm)
            _add_chart(story, _chart_wealth_currency(pat_pdf, valor_col, "Inversiones y fondo de emergencia por moneda", investment_only=True), width=15.0 * cm, height=8.0 * cm)
            concentracion_pat_txt = ""
            if nombre_col and not pat_pdf.empty:
                valores_abs = pat_pdf.groupby(nombre_col, dropna=False)[valor_col].sum().abs().sort_values(ascending=False)
                if not valores_abs.empty and valores_abs.sum() > 0:
                    principal_pat_nombre = valores_abs.index[0]
                    principal_pat_pct = float(valores_abs.iloc[0] / valores_abs.sum() * 100)
                    concentracion_pat_txt = (
                        f" El componente de mayor peso es <b>{_safe_text(principal_pat_nombre)}</b>, con <b>{principal_pat_pct:.1f}%</b> del valor patrimonial registrado."
                    )
            nivel_deuda_pat = "bajo" if endeuda_pdf < 30 else "moderado" if endeuda_pdf <= 60 else "alto"
            patrimonio_texto = (
                f"El patrimonio neto es <b>{_money(neto_pdf)}</b>: los activos "
                f"{'superan' if neto_pdf >= 0 else 'no alcanzan a cubrir'} los pasivos por <b>{_money(abs(neto_pdf))}</b>. "
                f"Por cada $100 en activos existen aproximadamente <b>${endeuda_pdf:.0f} en pasivos</b>, un nivel de apalancamiento <b>{nivel_deuda_pat}</b>. "
                f"Los activos líquidos representan <b>{liquidez_pct_pdf:.1f}%</b> de los activos; esta es la parte que puede responder más rápidamente ante una emergencia."
                + concentracion_pat_txt
            )
            patrimonio_tono = "green" if neto_pdf >= 0 and endeuda_pdf < 50 else "yellow" if neto_pdf >= 0 else "red"
            story += [Spacer(1, .2 * cm), _insight_box("Qué está ocurriendo con el patrimonio", patrimonio_texto, styles, patrimonio_tono)]
        if "Producción mensual" in pat_pdf.columns:
            from modules.core import calcular_distribucion_renta_patrimonio
            prod = pat_pdf.loc[pat_pdf["Tipo"].astype(str).str.upper().eq("ACTIVO")].copy()
            prod["Producción mensual"] = pd.to_numeric(prod["Producción mensual"],errors="coerce")
            story += [Spacer(1,.3*cm), Paragraph("Producción mensual propia",styles["section"]),
                      _kpi_table([("Producción propia registrada",_money(prod["Producción mensual"].sum()))],styles),
                      Paragraph("Los importes ya corresponden a tu participación: no se vuelve a aplicar el porcentaje de propiedad. La producción usa la moneda del activo convertida a COP. Es una expectativa mensual; no se suma de nuevo a los ingresos transaccionales.",styles["small"])]
            cols_prod = [c for c in [nombre_col,"Producción mensual"] if c]
            story.append(_df_table(prod.loc[prod["Producción mensual"].notna(),cols_prod],styles,money_cols=["Producción mensual"]))
            renta = calcular_distribucion_renta_patrimonio(pat_pdf)
            if not renta.empty:
                story += [Paragraph("Patrimonio que produce renta mensual",styles["section"]),
                          _df_table(renta[["Estado renta","Valor","Porcentaje"]],styles,money_cols=["Valor"]),
                          Paragraph("La tabla muestra el valor de los activos, no el ingreso mensual. Producción positiva: produce renta; cero: no produce; vacío: clasificación por tipo de producto.",styles["small"])]
        _add_chart(story, _chart_wealth_growth_v20(pat_pdf,inicio_pdf,cierre_pdf),height=8*cm)
        story.append(Paragraph("Cada fila patrimonial se interpreta como movimiento neto: el acumulado conserva los meses sin movimientos. La línea cero representa el patrimonio al inicio del período, igual que en la aplicación.",styles["small"]))
        money_pat_cols = [c for c in ["Valor actual", "Saldo pendiente", "Valor neto", "VALOR", "Valor", "MONTO", "Monto", "SALDO", "Saldo"] if c in pat_pdf.columns]
        story += [Spacer(1, .3 * cm), Paragraph("Detalle patrimonial", styles["section"])]
        detalle_cols = [c for c in [nombre_col, tipo_col, "Moneda", "Valor actual", "Saldo pendiente", "Valor neto"] if c and c in pat_pdf.columns]
        detalle_cols = list(dict.fromkeys(detalle_cols))
        story.append(_df_table(pat_pdf[detalle_cols] if detalle_cols else pat_pdf, styles, money_cols=money_pat_cols, max_rows=30))
    story.append(PageBreak())

    # 8. Felicidad
    story += [_question_header(7, styles), Spacer(1, .2 * cm)]
    datos_panel = dashboard_data or {}
    if "fondo" in datos_panel:
        fondo = float(datos_panel["fondo"])
        gasto_mes = float(datos_panel.get("gasto_mensual", 0))
        meta_fondo = gasto_mes * 3
        dias_fondo = fondo / (gasto_mes / 30) if gasto_mes > 0 else 0
        story.extend([
            Paragraph("Fondo de emergencia", styles["section"]),
            _kpi_table([
                ("Fondo actual", _money(fondo)), ("Meta 3 meses", _money(meta_fondo)),
                ("Días cubiertos", f"{dias_fondo:,.0f} días"),
                ("Faltante", _money(max(meta_fondo-fondo, 0))),
            ], styles),
            Spacer(1, .2*cm),
            Paragraph("Cobertura calculada con el mismo fondo y gasto mensual promedio del dashboard.", styles["body"]),
        ])
    if isinstance(metas, pd.DataFrame) and not metas.empty:
        story.extend([Spacer(1, .3*cm), Paragraph("Metas financieras", styles["section"])])
        _add_chart(story, _chart_goal_progress(metas), height=7.0*cm)
        story.append(_df_table(metas, styles, money_cols=["Actual", "Objetivo"], max_rows=20))
    if "fondo" in datos_panel or (isinstance(metas, pd.DataFrame) and not metas.empty):
        story.extend([PageBreak(), Paragraph("Trabajo, tiempo y bienestar financiero", styles["section"])])
    if felicidad is None or felicidad.empty:
        story.append(Paragraph(
            "No hay registros de trabajo en la tabla de ingresos para el periodo seleccionado.",
            styles["body"],
        ))
    else:
        fel = felicidad.copy()
        for col in ["VALOR", "HORAS", "VALOR_HORA"]:
            if col in fel.columns:
                fel[col] = pd.to_numeric(fel[col], errors="coerce")
        total_valor_fel = float(fel.get("VALOR", pd.Series(dtype=float)).fillna(0).sum())
        total_horas_fel = float(fel.get("HORAS", pd.Series(dtype=float)).fillna(0).sum())
        valor_hora_fel = total_valor_fel / total_horas_fel if total_horas_fel > 0 else float(fel.get("VALOR_HORA", pd.Series(dtype=float)).mean() or 0)
        fechas_fel = pd.to_datetime(fel.get("FECHA", pd.Series(dtype="datetime64[ns]")), errors="coerce").dropna()
        meses_fel = max((fechas_fel.max().year-fechas_fel.min().year)*12+fechas_fel.max().month-fechas_fel.min().month+1, 1) if not fechas_fel.empty else 1
        promedio_mensual_fel = total_valor_fel / meses_fel
        try:
            edad_num = float(edad_persona)
        except (TypeError, ValueError):
            edad_num = 0.0
        tipos_fel = fel.get("CATEGORIA", pd.Series("", index=fel.index)).map(_income_type)
        valor_idr_fel = float(fel.loc[tipos_fel.eq("Laborales"), "VALOR"].sum())
        if datos_panel.get("idr_incluir_no_laborales", True):
            valor_idr_fel += float(fel.loc[tipos_fel.eq("Residuales"), "VALOR"].sum())
        idr_pdf = valor_idr_fel / meses_fel * edad_num * 1.2
        patrimonio_neto_pdf = 0.0
        if patrimonio is not None and not patrimonio.empty:
            for candidate in ["Valor neto", "VALOR_NETO", "Valor", "VALOR"]:
                if candidate in patrimonio.columns:
                    patrimonio_neto_pdf = float(pd.to_numeric(patrimonio[candidate], errors="coerce").fillna(0).sum())
                    break
        ratio_idr_pdf = patrimonio_neto_pdf / idr_pdf if idr_pdf > 0 else 0.0
        estado_idr_pdf = "Excelente constructor de patrimonio" if ratio_idr_pdf >= 2 else "Constructor de patrimonio" if ratio_idr_pdf >= 1 else "Destructor de patrimonio"
        story.append(_kpi_table([
            ("Ingresos de trabajos", _money(total_valor_fel)),
            ("Horas registradas", f"{total_horas_fel:,.1f}"),
            ("Valor hora promedio", _money(valor_hora_fel)),
            ("Patrimonio / IDR", f"{ratio_idr_pdf:.2f}x"),
        ], styles))
        felicidad_texto = (
            f"La lectura es <b>{_safe_text(estado_idr_pdf)}</b>. El patrimonio equivale a <b>{ratio_idr_pdf:.2f} veces</b> el IDR estimado de {_money(idr_pdf)}. "
            f"El trabajo produjo en promedio <b>{_money(valor_hora_fel)} por hora</b>; este indicador permite comparar si el tiempo invertido está generando una remuneración coherente con la acumulación patrimonial. "
            "No es una medición clínica de felicidad."
        )
        story += [Spacer(1, .22 * cm), _insight_box("Trabajo, tiempo y patrimonio", felicidad_texto, styles, "purple")]
        _add_chart(story, _chart_happiness_company(fel), height=8.2 * cm)
        _add_chart(story, _chart_happiness_income_mix(fel), width=14.5 * cm, height=8.0 * cm)
        fel_cols = [c for c in ["FECHA", "EMPRESA", "CATEGORIA", "HORAS", "VALOR", "VALOR_HORA"] if c in fel.columns]
        story.append(_df_table(fel[fel_cols] if fel_cols else fel, styles, money_cols=["VALOR", "VALOR_HORA"], max_rows=24))
        story.extend([PageBreak(),Paragraph("Patrimonio neto / IDR",styles["section"]),Spacer(1,10)])
        _indice_con_medidor(
            story, styles, "Patrimonio neto / IDR", ratio_idr_pdf if idr_pdf>0 else None,
            estado_idr_pdf if idr_pdf>0 else "No calculable",
            f"Patrimonio neto: <b>{_money(patrimonio_neto_pdf)}</b>.<br/>IDR: <b>{_money(idr_pdf)}</b>.<br/><br/>Menos de 1: Destructor de patrimonio.<br/>Desde 1 hasta menos de 2: Constructor de patrimonio.<br/>Desde 2: Excelente constructor de patrimonio.<br/><br/>La aguja se limita a 3; el valor real se conserva.",
            [0,1,2,3],suffix="x",palette=["#FF1744","#FFEA00","#39FF14"],
        )

    indicadores = datos_panel.get("indicadores")
    if indicadores:
        story.extend([PageBreak(),Paragraph("Indicadores de prosperidad y dependencia financiera",styles["section"]),Spacer(1,12)])
        dependencia = indicadores["dependencia_ind"]
        story.append(_kpi_table([
            ("Flujo de efectivo mensual", _money(indicadores["ingreso_mensual_ind"]-indicadores["egreso_mensual_ind"])),
            ("Patrimonio líquido", _money(indicadores["liquido_ind"])),
            ("Prosperidad financiera", indicadores["prosperidad_texto"]),
            ("Índice de Dependencia (ID)", f"{dependencia:.1f}%" if dependencia is not None else "No calculable"),
        ],styles))
        story.extend([Spacer(1,12),_insight_box(
            "Fórmulas que definiste para Felicidad",
            "<b>Patrimonio líquido</b> = total activos menos total pasivos. Esta definición se aplica solo a Felicidad; no equivale a efectivo disponible.<br/>"
            "<b>Prosperidad financiera</b> = ese patrimonio dividido entre egreso promedio mensual; se expresa en meses o años y meses completos.<br/>"
            "<b>Dependencia</b> = (egresos totales menos ingresos residuales) dividido entre egresos totales, por 100. Ambos importes corresponden al período seleccionado.<br/>"
            f"Egreso promedio mensual: <b>{_money(indicadores['egreso_mensual_ind'])}</b>. Promedios calculados sobre <b>{indicadores['meses_indicadores']}</b> meses seleccionados.",styles),
            PageBreak(),Paragraph("Deuda mensual y endeudamiento",styles["section"]),Spacer(1,8)])
        for tipo in ["flujo","endeudamiento"]:
            es_flujo=tipo=="flujo"
            value=indicadores["flujo_deuda_ind" if es_flujo else "endeudamiento_ind"]
            status=indicadores["estado_flujo_ind" if es_flujo else "estado_endeudamiento_ind"]
            maximo=max(100,(int(value//10)+1)*10) if value is not None else 100
            lectura=(f"Por cada $100 de ingreso mensual promedio, <b>${value:.1f}</b> corresponden a pagos de la categoría CRÉDITOS." if es_flujo else f"Por cada $100 del valor de tus activos, tienes <b>${value:.1f}</b> en deudas.") if value is not None else "Faltan datos positivos para calcular el índice."
            rangos=("0%: Ideal. Más de 0 a 10%: Muy bien. Más de 10 a 30%: Adecuado. Más de 30 a 40%: Crítico. Más de 40%: Sobreendeudado." if es_flujo else "0%: Todo lo que tienes es tuyo. Más de 0 a 15%: Nivel bueno. Más de 15 a 40%: Manejable. Más de 40 a 60%: Crítico. Más de 60%: Sobreendeudado.")
            _indice_con_medidor(story,styles,"Flujo de deuda mensual" if es_flujo else "Índice de endeudamiento",value,status,
                lectura+"<br/><br/>"+rangos+"<br/><br/>Clasificación según tus rangos."+ (" Pagos estimados por los textos de los gastos." if es_flujo else ""),
                [0,10,30,40,maximo] if es_flujo else [0,15,40,60,maximo])

    story += [PageBreak(), Paragraph("Tu nivel de progreso financiero",styles["section"])]
    meses_nivel = max(len(flujo),1)
    residual = ingresos.loc[ingresos["INGRESOS_CATEGORIA"].map(_income_type).eq("Residuales")].copy() if not ingresos.empty else ingresos.copy()
    gasto_nivel = total_gastos/meses_nivel
    if gasto_nivel > 0 and not ingresos.empty:
        residual_mes = float(residual["INGRESOS_CANTIDAD"].sum())/meses_nivel
        cobertura = residual_mes/gasto_nivel
        fuentes = residual.loc[residual["INGRESOS_CANTIDAD"].gt(0),"INGRESOS_FUENTE"].dropna().astype(str).str.strip().str.upper()
        cantidad = fuentes.loc[~fuentes.isin(["","NAN","NONE","SIN FUENTE","SIN EMPRESA"])].nunique()
        animal, nivel, archivo = ("Hámster","Dependencia financiera","hamster.png")
        if cobertura>=1: animal,nivel,archivo = "Delfín","Independencia financiera","delfin.png"
        if cobertura>=3: animal,nivel,archivo = "Águila","Autonomía financiera","aguila.png"
        if cobertura>=10 and cantidad>=2:
            animal,nivel,archivo = "Rinoceronte","Libertad financiera","rinoceronte.png"
            if (dashboard_data or {}).get("colibri_confirmado"):
                animal,nivel,archivo = "Colibrí","Prosperidad financiera","colibri.png"
        story.append(_insight_box(animal+" - "+nivel,f"Ingreso residual mensual estimado: {_money(residual_mes)}; gastos mensuales: {_money(gasto_nivel)}. Cobertura: {_number(cobertura)} veces; fuentes positivas: {cantidad}. Escala: 1× Delfín; 3× Águila; 10× y varias fuentes Rinoceronte. Colibrí exige además tu confirmación personal de crecimiento y transmisión de conocimientos.",styles))
        imagen = Path(__file__).resolve().parent.parent/"imagenes"/archivo
        if imagen.is_file():
            from PIL import Image as PILImage
            with PILImage.open(imagen) as im: ancho,alto=im.size
            story.append(Image(str(imagen),width=6*cm,height=6*cm*alto/ancho))
    else:
        story.append(Paragraph("Se necesitan ingresos y gastos positivos para determinar el nivel.",styles["body"]))

    # Evita una última página vacía cuando el último medidor llena la hoja.
    while story and isinstance(story[-1], (Spacer, PageBreak)):
        story.pop()
    doc.build(story)
    output.seek(0)
    return output.getvalue()
