"""PDF reports for a stock and for the portfolio, built with ReportLab from the numbers the app already shows.

Pure layout: the views gather the data into plain dicts and this module turns them into a printable, editorial-style
PDF (Spectral headings, Inter text, IBM Plex Mono figures). Nothing is fetched or stored here.
"""
from __future__ import annotations

import datetime as dt
import io
import math
import os
from html import escape

from reportlab.graphics.shapes import Circle, Drawing, Line, PolyLine, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (CondPageBreak, Flowable, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "fonts")
INK, BODY, MUTED, FAINT = colors.HexColor("#111418"), colors.HexColor("#353B45"), colors.HexColor("#6B7280"), colors.HexColor("#9AA1AC")
LINE, BAND, PAPER = colors.HexColor("#E3E5E9"), colors.HexColor("#F4F5F7"), colors.white
ACCENT, ACCENT_SOFT = colors.HexColor("#2F6BFF"), colors.HexColor("#E8EFFF")
UP, DOWN, AMBER = colors.HexColor("#0E9F6E"), colors.HexColor("#D64545"), colors.HexColor("#C98A00")
SERIES = [ACCENT, colors.HexColor("#F08A24"), colors.HexColor("#14A39A"), colors.HexColor("#8B5CF6"), colors.HexColor("#E1567C"),
          colors.HexColor("#D9A400"), colors.HexColor("#5B8DEF"), colors.HexColor("#9AA1AC")]
W, H = A4
MARGIN = 16 * mm
CONTENT_W = W - 2 * MARGIN

_fonts_ready = False


def _fonts() -> None:
    global _fonts_ready
    if _fonts_ready:
        return
    for name, file in (("Serif", "Spectral-Regular.ttf"), ("Serif-Semi", "Spectral-SemiBold.ttf"), ("Serif-It", "Spectral-Italic.ttf"),
                       ("Sans", "Inter-Regular.ttf"), ("Sans-Med", "Inter-Medium.ttf"), ("Sans-Semi", "Inter-SemiBold.ttf"),
                       ("Mono", "IBMPlexMono-Regular.ttf"), ("Mono-Med", "IBMPlexMono-Medium.ttf")):
        pdfmetrics.registerFont(TTFont(name, os.path.join(FONT_DIR, file)))
    for name in ("Serif-Semi", "Serif-It", "Sans-Med", "Sans-Semi", "Mono", "Mono-Med"):
        pdfmetrics.registerFontFamily(name, normal=name, bold=name, italic=name, boldItalic=name)
    pdfmetrics.registerFontFamily("Sans", normal="Sans", bold="Sans-Semi", italic="Sans", boldItalic="Sans-Semi")
    pdfmetrics.registerFontFamily("Serif", normal="Serif", bold="Serif-Semi", italic="Serif-It", boldItalic="Serif-Semi")
    _fonts_ready = True


def _styles() -> dict[str, ParagraphStyle]:
    _fonts()
    return {
        "kicker": ParagraphStyle("kicker", fontName="Sans-Semi", fontSize=7.2, leading=9, textColor=ACCENT, spaceAfter=2),
        "title": ParagraphStyle("title", fontName="Serif-Semi", fontSize=25, leading=29, textColor=INK),
        "sub": ParagraphStyle("sub", fontName="Sans", fontSize=8.8, leading=12, textColor=MUTED),
        "h2": ParagraphStyle("h2", fontName="Serif-Semi", fontSize=14, leading=17, textColor=INK, spaceBefore=4),
        "src": ParagraphStyle("src", fontName="Sans", fontSize=6.8, leading=8.5, textColor=FAINT, alignment=TA_RIGHT),
        "body": ParagraphStyle("body", fontName="Sans", fontSize=8.6, leading=12.4, textColor=BODY),
        "lead": ParagraphStyle("lead", fontName="Serif", fontSize=10.5, leading=14.5, textColor=INK),
        "small": ParagraphStyle("small", fontName="Sans", fontSize=7.2, leading=9.6, textColor=MUTED),
        "cell": ParagraphStyle("cell", fontName="Sans", fontSize=7.8, leading=9.6, textColor=BODY),
        "cell_b": ParagraphStyle("cell_b", fontName="Sans-Med", fontSize=7.8, leading=9.6, textColor=INK),
        "num": ParagraphStyle("num", fontName="Mono", fontSize=7.6, leading=9.6, textColor=INK, alignment=TA_RIGHT),
        "th": ParagraphStyle("th", fontName="Sans-Semi", fontSize=6.6, leading=8, textColor=MUTED),
        "th_r": ParagraphStyle("th_r", fontName="Sans-Semi", fontSize=6.6, leading=8, textColor=MUTED, alignment=TA_RIGHT),
        "kpi_k": ParagraphStyle("kpi_k", fontName="Sans-Semi", fontSize=6.4, leading=8, textColor=MUTED),
        "kpi_v": ParagraphStyle("kpi_v", fontName="Serif-Semi", fontSize=15, leading=18, textColor=INK),
        "kpi_s": ParagraphStyle("kpi_s", fontName="Sans", fontSize=6.8, leading=8.6, textColor=MUTED),
        "bullet": ParagraphStyle("bullet", fontName="Sans", fontSize=8.4, leading=12, textColor=BODY, leftIndent=9, bulletIndent=0),
        "ai": ParagraphStyle("ai", fontName="Serif", fontSize=9.4, leading=13.6, textColor=INK),
    }


def esc(x) -> str:
    return escape(str(x if x is not None else ""))


def tone(x: float | None) -> colors.Color:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return INK
    return UP if x > 0 else DOWN if x < 0 else INK


def hexc(c: colors.Color) -> str:
    return "#" + c.hexval()[2:]


# --------------------------------------------------------------------------- page furniture
class _Doc(SimpleDocTemplate):
    def __init__(self, buf, meta: dict, **kw):
        super().__init__(buf, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN, topMargin=20 * mm, bottomMargin=17 * mm,
                         title=meta.get("title", "Market Brief report"), author="Market Brief", subject=meta.get("subject", ""),
                         creator="Market Brief", **kw)
        self.meta = meta


def _furniture(canvas, doc) -> None:
    m = doc.meta
    canvas.saveState()
    # top band
    canvas.setFillColor(INK)
    canvas.rect(0, H - 9 * mm, W, 9 * mm, stroke=0, fill=1)
    canvas.setFillColor(ACCENT)
    canvas.rect(0, H - 9 * mm, 3.2 * mm, 9 * mm, stroke=0, fill=1)
    canvas.setFillColor(colors.white)
    canvas.setFont("Serif-Semi", 10.5)
    canvas.drawString(MARGIN, H - 6 * mm, "Market")
    canvas.setFillColor(colors.HexColor("#9DB7FF"))
    canvas.drawString(MARGIN + pdfmetrics.stringWidth("Market ", "Serif-Semi", 10.5), H - 6 * mm, "Brief")
    canvas.setFillColor(colors.HexColor("#C9CED6"))
    canvas.setFont("Sans-Med", 6.8)
    canvas.drawRightString(W - MARGIN, H - 5.8 * mm, m.get("band", "").upper())
    # footer
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.6)
    canvas.line(MARGIN, 12 * mm, W - MARGIN, 12 * mm)
    canvas.setFont("Sans", 6.6)
    canvas.setFillColor(FAINT)
    canvas.drawString(MARGIN, 8.2 * mm, m.get("footer", ""))
    canvas.drawRightString(W - MARGIN, 8.2 * mm, m.get("page_fmt", "Page {n}").format(n=doc.page))
    canvas.restoreState()


def _build(meta: dict, story: list) -> bytes:
    _fonts()
    buf = io.BytesIO()
    doc = _Doc(buf, meta)
    doc.build(story, onFirstPage=_furniture, onLaterPages=_furniture)
    return buf.getvalue()


# --------------------------------------------------------------------------- building blocks
def colw(ratio: float, gap: float = 6 * mm) -> float:
    """Width of one side of two_cols(…, ratio)."""
    return (CONTENT_W - gap) * ratio


def section(title: str, source: str = "", st: dict | None = None, width: float = CONTENT_W) -> Flowable:
    st = st or _styles()
    if width < CONTENT_W * 0.7:  # narrow column: source goes under the title
        t = Table([[Paragraph(esc(title), st["h2"])], [Paragraph(esc(source), ParagraphStyle("s2", parent=st["src"], alignment=TA_LEFT))]],
                  colWidths=[width])
        t.setStyle(TableStyle([("LINEBELOW", (0, -1), (-1, -1), 0.8, INK), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                               ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 2), ("TOPPADDING", (0, 0), (-1, -1), 0)]))
        return t
    t = Table([[Paragraph(esc(title), st["h2"]), Paragraph(esc(source), st["src"])]], colWidths=[width * 0.62, width * 0.38])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "BOTTOM"), ("LINEBELOW", (0, 0), (-1, 0), 0.8, INK),
                           ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 3), ("TOPPADDING", (0, 0), (-1, -1), 0)]))
    return t


def kpis(items: list[tuple], st: dict, cols: int | None = None, width: float = CONTENT_W) -> Table:
    """items: (label, value, sub, value_color or None)."""
    cols = cols or len(items)
    cells = []
    cell_w = (width - 3 * mm * (cols - 1)) / cols
    size = 15 if cell_w > 34 * mm else 12.5
    for label, value, sub, col in items:
        v = ParagraphStyle("v", parent=st["kpi_v"], textColor=col or INK, fontSize=size, leading=size + 3)
        cells.append([Paragraph(esc(label).upper(), st["kpi_k"]), Paragraph(esc(value), v), Paragraph(esc(sub or ""), st["kpi_s"])])
    rows = [cells[i:i + cols] for i in range(0, len(cells), cols)]
    for r in rows:
        r += [""] * (cols - len(r))
    gap = 3 * mm
    w = (width - gap * (cols - 1)) / cols
    data, widths = [], []
    for r in rows:
        line = []
        for j, c in enumerate(r):
            line.append(c)
            if j < cols - 1:
                line.append("")
        data.append(line)
    widths = [w if j % 2 == 0 else gap for j in range(2 * cols - 1)]
    t = Table(data, colWidths=widths)
    style = [("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
             ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 7)]
    for i in range(len(rows)):
        for j in range(cols):
            style += [("BACKGROUND", (2 * j, i), (2 * j, i), BAND), ("LINEABOVE", (2 * j, i), (2 * j, i), 1.6, ACCENT if j == 0 and i == 0 else INK)]
        for j in range(cols - 1):
            style += [("LEFTPADDING", (2 * j + 1, i), (2 * j + 1, i), 0), ("RIGHTPADDING", (2 * j + 1, i), (2 * j + 1, i), 0)]
    if len(rows) > 1:
        style += [("TOPPADDING", (0, 1), (-1, -1), 6)]
    t.setStyle(TableStyle(style))
    return t


def table(header: list[str], rows: list[list], st: dict, widths: list[float] | None = None, numeric_from: int = 1,
          bold_first: bool = True, highlight_rows: set[int] | None = None, group_rows: set[int] | None = None) -> Table:
    """Clean data table: hairlines, right-aligned mono numbers, optional colored cells given as (text, color)."""
    n = len(header)
    widths = widths or [CONTENT_W * 0.34] + [CONTENT_W * 0.66 / (n - 1)] * (n - 1)
    has_head = any(h for h in header)
    data = [[Paragraph(esc(h).upper(), st["th"] if j < numeric_from else st["th_r"]) for j, h in enumerate(header)]] if has_head else []
    for i, r in enumerate(rows):
        line = []
        for j, c in enumerate(r):
            text, col = (c if isinstance(c, tuple) else (c, None))
            if group_rows and i in group_rows:
                line.append(Paragraph(esc(text), ParagraphStyle("g", parent=st["th"], textColor=ACCENT)) if j == 0 else "")
            elif j < numeric_from:
                line.append(Paragraph(esc(text), st["cell_b"] if (bold_first and j == 0) else st["cell"]))
            else:
                line.append(Paragraph(esc(text), ParagraphStyle("n", parent=st["num"], textColor=col or INK)))
        data.append(line)
    t = Table(data, colWidths=widths, repeatRows=1 if has_head else 0)
    off = 1 if has_head else 0
    style = [("LINEBELOW", (0, 0), (-1, 0), 0.8, INK) if has_head else ("LINEABOVE", (0, 0), (-1, 0), 0.8, INK),
             ("LINEBELOW", (0, off), (-1, -1), 0.4, LINE),
             ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 3.2), ("BOTTOMPADDING", (0, 0), (-1, -1), 3.2),
             ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3)]
    for i in highlight_rows or set():
        style.append(("BACKGROUND", (0, i + off), (-1, i + off), ACCENT_SOFT))
    for i in group_rows or set():
        style += [("SPAN", (0, i + off), (-1, i + off)), ("TOPPADDING", (0, i + off), (-1, i + off), 6)]
    t.setStyle(TableStyle(style))
    return t


def bullets(items: list[tuple[str, colors.Color | None]], st: dict) -> list[Flowable]:
    out = []
    for text, col in items:
        sty = ParagraphStyle("b", parent=st["bullet"], bulletColor=col or ACCENT, bulletFontName="Sans", bulletFontSize=7)
        out.append(Paragraph(esc(text), sty, bulletText="●"))
        out.append(Spacer(1, 1.2 * mm))
    return out


def callout(text: str, st: dict, color: colors.Color = ACCENT) -> Table:
    t = Table([[Paragraph(text, st["lead"])]], colWidths=[CONTENT_W])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), BAND), ("LINEBEFORE", (0, 0), (0, -1), 2.4, color),
                           ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                           ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
    return t


def two_cols(left: list, right: list, ratio: float = 0.5, gap: float = 6 * mm) -> Table:
    lw = (CONTENT_W - gap) * ratio
    rw = CONTENT_W - gap - lw
    t = Table([[left, "", right]], colWidths=[lw, gap, rw])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
    return t


# --------------------------------------------------------------------------- charts (vector, print friendly)
def _nice_ticks(lo: float, hi: float, n: int = 4) -> list[float]:
    if hi <= lo:
        hi = lo + 1
    raw = (hi - lo) / n
    mag = 10 ** math.floor(math.log10(raw))
    step = min((s * mag for s in (1, 2, 2.5, 5, 10) if s * mag >= raw), default=mag * 10)
    start = math.ceil(lo / step) * step
    ticks, v = [], start
    while v <= hi + 1e-9:
        ticks.append(round(v, 10))
        v += step
    return ticks


def line_chart(series: list[tuple[str, list[float], colors.Color]], dates: list[str], width: float, height: float,
               y_fmt=lambda v: f"{v:,.0f}", fill_first: bool = True, zero_line: bool = False, end_labels: bool = True) -> Drawing:
    """Lines on a shared x (index positions); first series optionally filled to its minimum."""
    d = Drawing(width, height)
    left, right, bottom, top = 0, 40 if end_labels else 6, 14, 6
    pw, ph = width - left - right, height - bottom - top
    vals = [v for _, ys, _ in series for v in ys if v is not None and not math.isnan(v)]
    if not vals:
        return d
    lo, hi = min(vals), max(vals)
    pad = (hi - lo) * 0.08 or abs(hi) * 0.05 or 1
    lo, hi = lo - pad, hi + pad
    n = max(len(ys) for _, ys, _ in series)
    x = lambda i: left + pw * (i / max(n - 1, 1))  # noqa: E731
    y = lambda v: bottom + ph * ((v - lo) / (hi - lo))  # noqa: E731
    for tv in _nice_ticks(lo, hi):
        d.add(Line(left, y(tv), left + pw, y(tv), strokeColor=LINE, strokeWidth=0.4))
        d.add(String(left + 1, y(tv) + 1.6, y_fmt(tv), fontName="Mono", fontSize=5.8, fillColor=FAINT))
    if zero_line and lo < 0 < hi:
        d.add(Line(left, y(0), left + pw, y(0), strokeColor=FAINT, strokeWidth=0.6, strokeDashArray=[2, 2]))
    for k, (name, ys, col) in enumerate(series):
        pts = [(x(i), y(v)) for i, v in enumerate(ys) if v is not None and not math.isnan(v)]
        if len(pts) < 2:
            continue
        if k == 0 and fill_first:
            poly = [(pts[0][0], bottom)] + pts + [(pts[-1][0], bottom)]
            from reportlab.graphics.shapes import Polygon
            d.add(Polygon([c for p_ in poly for c in p_], fillColor=colors.Color(col.red, col.green, col.blue, alpha=0.08), strokeColor=None))
        d.add(PolyLine([c for p_ in pts for c in p_], strokeColor=col, strokeWidth=1.5 if k == 0 else 1.1,
                       strokeDashArray=None if k == 0 else [3, 2]))
        if end_labels:
            lx, ly = pts[-1]
            d.add(Rect(left + pw + 2, ly - 5, right - 4, 10, fillColor=col, strokeColor=None, rx=2, ry=2))
            d.add(String(left + pw + 4.5, ly - 2.6, f"{name[:9]}", fontName="Sans-Semi", fontSize=6, fillColor=colors.white))
    if dates:
        d.add(String(left, 3, dates[0], fontName="Sans", fontSize=6, fillColor=FAINT))
        d.add(String(left + pw, 3, dates[-1], fontName="Sans", fontSize=6, fillColor=FAINT, textAnchor="end"))
        if len(dates) > 2:
            d.add(String(left + pw / 2, 3, dates[len(dates) // 2], fontName="Sans", fontSize=6, fillColor=FAINT, textAnchor="middle"))
    return d


def hbars(labels: list[str], values: list[float], width: float, fmt=lambda v: f"{v:+.2f} pp", row_h: float = 13) -> Drawing:
    """Horizontal bars around zero, green positive and red negative."""
    height = row_h * len(labels) + 8
    d = Drawing(width, height)
    label_w = 78
    vmax = max([abs(v) for v in values] + [1e-9])
    pw = width - label_w - 44
    zero = label_w + pw / 2 if any(v < 0 for v in values) else label_w
    scale = (pw / 2 if any(v < 0 for v in values) else pw) / vmax
    for i, (lb, v) in enumerate(zip(labels, values)):
        yb = height - (i + 1) * row_h
        d.add(String(0, yb + 3, lb[:20], fontName="Sans", fontSize=6.8, fillColor=BODY))
        w_ = abs(v) * scale
        x0 = zero if v >= 0 else zero - w_
        d.add(Rect(x0, yb + 1.5, max(w_, 0.6), row_h - 5, fillColor=UP if v >= 0 else DOWN, strokeColor=None, rx=1.5, ry=1.5))
        tx = zero + w_ + 3 if v >= 0 else zero - w_ - 3
        d.add(String(tx, yb + 3, fmt(v), fontName="Mono", fontSize=6.4, fillColor=INK, textAnchor="start" if v >= 0 else "end"))
    d.add(Line(zero, 2, zero, height - 2, strokeColor=FAINT, strokeWidth=0.6))
    return d


def range_chart(rows: list[tuple[str, float | None, float | None]], price: float, width: float, price_label: str) -> Drawing:
    """Football field: one bar per valuation range against the current price."""
    rows = [r for r in rows if r[1] is not None and r[2] is not None and not (math.isnan(r[1]) or math.isnan(r[2]))]
    row_h = 15
    height = row_h * len(rows) + 22
    d = Drawing(width, height)
    if not rows:
        return d
    label_w = 150
    lo = min([r[1] for r in rows] + [price])
    hi = max([r[2] for r in rows] + [price])
    pad = (hi - lo) * 0.08 or 1
    lo, hi = lo - pad, hi + pad
    pw = width - label_w - 8
    x = lambda v: label_w + pw * (v - lo) / (hi - lo)  # noqa: E731
    for tv in _nice_ticks(lo, hi, 5):
        d.add(Line(x(tv), 12, x(tv), height - 4, strokeColor=LINE, strokeWidth=0.4))
        d.add(String(x(tv), 3, f"${tv:,.0f}", fontName="Mono", fontSize=6, fillColor=FAINT, textAnchor="middle"))
    for i, (lb, a, b) in enumerate(rows):
        yb = height - 6 - (i + 1) * row_h
        d.add(String(0, yb + 4, lb[:44], fontName="Sans", fontSize=6.6, fillColor=BODY))
        col = SERIES[i % len(SERIES)]
        d.add(Rect(x(a), yb + 2, max(x(b) - x(a), 1), row_h - 5, fillColor=col, strokeColor=None, rx=2, ry=2))
        d.add(String(x(a) - 2, yb + 4.2, f"{a:,.0f}", fontName="Mono", fontSize=5.8, fillColor=MUTED, textAnchor="end"))
        d.add(String(x(b) + 2, yb + 4.2, f"{b:,.0f}", fontName="Mono", fontSize=5.8, fillColor=MUTED))
    d.add(Line(x(price), 12, x(price), height - 4, strokeColor=INK, strokeWidth=1.1, strokeDashArray=[3, 2]))
    d.add(String(x(price), height - 3, f"{price_label} ${price:,.2f}", fontName="Sans-Semi", fontSize=6.4, fillColor=INK, textAnchor="middle"))
    return d


def stacked_bar(items: list[tuple[str, float]], width: float, height: float = 14) -> Drawing:
    """A single 100% bar with a legend underneath (allocation)."""
    items = [(lb, w) for lb, w in items if w > 0.0005]
    rows = math.ceil(len(items) / 3)
    d = Drawing(width, height + 6 + rows * 11)
    x0, total = 0.0, sum(w for _, w in items) or 1
    for i, (lb, w) in enumerate(items):
        ww = width * w / total
        d.add(Rect(x0, rows * 11 + 6, ww, height, fillColor=SERIES[i % len(SERIES)], strokeColor=PAPER, strokeWidth=0.8))
        x0 += ww
    col_w = width / 3
    for i, (lb, w) in enumerate(items):
        cx, cy = (i % 3) * col_w, (rows - 1 - i // 3) * 11 + 1
        d.add(Rect(cx, cy, 6, 6, fillColor=SERIES[i % len(SERIES)], strokeColor=None, rx=1, ry=1))
        d.add(String(cx + 9, cy + 0.6, f"{lb[:22]}  {w * 100:.1f}%", fontName="Sans", fontSize=6.6, fillColor=BODY))
    return d


def dots_chart(labels: list[str], expected: list, actual: list, width: float, height: float) -> Drawing:
    """EPS: hollow = estimate, filled = reported (green beat, red miss)."""
    d = Drawing(width, height)
    vals = [v for v in expected + actual if v is not None]
    if not vals:
        return d
    left, right, bottom, top = 4, 30, 14, 8
    pw, ph = width - left - right, height - bottom - top
    lo, hi = min(vals), max(vals)
    pad = (hi - lo) * 0.2 or abs(hi) * 0.2 or 0.5
    lo, hi = lo - pad, hi + pad
    n = len(labels)
    x = lambda i: left + pw * ((i + 0.5) / n)  # noqa: E731
    y = lambda v: bottom + ph * (v - lo) / (hi - lo)  # noqa: E731
    for tv in _nice_ticks(lo, hi):
        d.add(Line(left, y(tv), left + pw, y(tv), strokeColor=LINE, strokeWidth=0.4))
        d.add(String(left + pw + 4, y(tv) - 2.2, f"${tv:,.2f}", fontName="Mono", fontSize=5.8, fillColor=FAINT))
    for i, (lb, e, a) in enumerate(zip(labels, expected, actual)):
        if e is not None:
            d.add(Circle(x(i), y(e), 4.4, fillColor=None, strokeColor=FAINT, strokeWidth=1.1))
        if a is not None:
            d.add(Circle(x(i), y(a), 3.4, fillColor=UP if (e is None or a >= e) else DOWN, strokeColor=None))
        d.add(String(x(i), 3, lb, fontName="Sans", fontSize=5.8, fillColor=MUTED, textAnchor="middle"))
    return d


def _closing(story: list, text: str, st: dict) -> list:
    """The closing note travels with the last block so it never sits alone on a page."""
    tail = []
    while story and isinstance(story[-1], Spacer):
        story.pop()
    if story:
        tail.append(story.pop())
    return [KeepTogether(tail + [Spacer(1, 4 * mm), Paragraph(esc(text), st["small"])])]


# --------------------------------------------------------------------------- stock report
def stock_pdf(r: dict) -> bytes:
    """r: dict prepared by views_stock.report_data (all labels already translated)."""
    st = _styles()
    L = r["labels"]
    story: list = []
    # ---- masthead
    head_l = [Paragraph(esc(L["kicker"]), st["kicker"]), Paragraph(esc(r["name"]), st["title"]),
              Paragraph(esc(r["meta_line"]), st["sub"])]
    pc = ParagraphStyle("pc", fontName="Mono-Med", fontSize=20, leading=23, textColor=INK, alignment=TA_RIGHT)
    head_r = [Paragraph(f'${r["price"]:,.2f}', pc),
              Paragraph(f'<font color="{hexc(tone(r["change_pct"]))}">{esc(r["change_txt"])}</font>',
                        ParagraphStyle("ch", parent=st["num"], fontSize=9, leading=12)),
              Paragraph(esc(r["asof"]), ParagraphStyle("as", parent=st["small"], alignment=TA_RIGHT))]
    story += [two_cols(head_l, head_r, 0.7), Spacer(1, 5 * mm)]
    story.append(kpis(r["kpis"], st, cols=min(6, len(r["kpis"]))))
    story.append(Spacer(1, 4 * mm))
    if r.get("summary"):
        story += [callout(esc(r["summary"]), st), Spacer(1, 4 * mm)]
    # ---- price chart + key stats
    chart_w = colw(0.6)
    ch = line_chart([(r["ticker"], r["chart"]["stock"], ACCENT), ("S&P 500", r["chart"]["bench"], FAINT)], r["chart"]["dates"],
                    chart_w, 62 * mm, y_fmt=lambda v: f"{v:+.0f}%", zero_line=True)
    left = [section(L["perf"], L["src_mkt"], st, width=chart_w), Spacer(1, 2 * mm), ch, Spacer(1, 2 * mm),
            table([L["period"], r["ticker"], "S&P 500", L["diff"]], r["perf_rows"], st,
                  widths=[chart_w * 0.31, chart_w * 0.23, chart_w * 0.23, chart_w * 0.23])]
    kw = colw(0.4)
    right = [section(L["key_stats"], L["src_mkt_calc"], st, width=kw), Spacer(1, 2 * mm),
             table(["", ""], r["key_stats"], st, widths=[kw * 0.55, kw * 0.45])]
    story += [two_cols(left, right, 0.6), Spacer(1, 5 * mm)]
    # ---- financials
    if r.get("fin_rows"):
        story += [CondPageBreak(70 * mm), section(L["financials"], L["src_rep"], st), Spacer(1, 2 * mm)]
        n = len(r["fin_years"])
        story.append(table([""] + [f"FY{y}" for y in r["fin_years"]], r["fin_rows"], st,
                           widths=[CONTENT_W * 0.3] + [CONTENT_W * 0.7 / n] * n, group_rows=r.get("fin_groups")))
        story.append(Spacer(1, 4 * mm))
    if r.get("checks") or r.get("eva"):
        left = [section(L["checks"], L["src_calc"], st, width=colw(0.52)), Spacer(1, 2 * mm)] + bullets(r.get("checks") or [], st)
        right = [section(L["eva"], L["src_calc"], st, width=colw(0.48)), Spacer(1, 2 * mm)]
        if r.get("eva"):
            right += [kpis(r["eva"]["kpis"], st, cols=2, width=colw(0.48)), Spacer(1, 2 * mm), Paragraph(esc(r["eva"]["note"]), st["small"])]
        story += [KeepTogether([two_cols(left, right, 0.52)]), Spacer(1, 5 * mm)]
    # ---- valuation
    if r.get("valuation"):
        v = r["valuation"]
        block = [section(L["valuation"], L["src_calc"], st), Spacer(1, 2 * mm), kpis(v["kpis"], st, cols=len(v["kpis"])), Spacer(1, 3 * mm)]
        if v.get("text"):
            block += [Paragraph(esc(v["text"]), st["body"]), Spacer(1, 3 * mm)]
        if v.get("ranges"):
            block += [range_chart(v["ranges"], r["price"], CONTENT_W, L["price"]), Spacer(1, 1 * mm),
                      Paragraph(esc(v.get("ranges_note", "")), st["small"])]
        story += [CondPageBreak(90 * mm), KeepTogether(block), Spacer(1, 4 * mm)]
    if r.get("comps_rows"):
        story += [KeepTogether([section(L["comps"], L["src_comps"], st), Spacer(1, 2 * mm),
                                table(r["comps_header"], r["comps_rows"], st), Spacer(1, 1.5 * mm),
                                Paragraph(esc(r.get("comps_note", "")), st["small"])]), Spacer(1, 5 * mm)]
    # ---- earnings
    if r.get("earn_rows"):
        e_left = [section(L["earnings"], L["src_earn"], st, width=colw(0.55)), Spacer(1, 2 * mm),
                  table(r["earn_header"], r["earn_rows"], st,
                        widths=[colw(0.55) * w for w in (0.24, 0.19, 0.19, 0.19, 0.19)])]
        e_right = [section(L["eps_chart"], " ", st, width=colw(0.45)), Spacer(1, 2 * mm),
                   dots_chart(r["eps_chart"]["labels"], r["eps_chart"]["expected"], r["eps_chart"]["actual"], colw(0.45), 48 * mm),
                   Paragraph(esc(r.get("earn_note", "")), st["small"])]
        story += [CondPageBreak(70 * mm), KeepTogether([two_cols(e_left, e_right, 0.55)]), Spacer(1, 5 * mm)]
    # ---- risk and street view
    left, right = [], []
    if r.get("risk_rows"):
        left = [section(L["risk"], L["src_calc"], st, width=colw(0.5)), Spacer(1, 2 * mm),
                table(["", ""], r["risk_rows"], st, widths=[colw(0.5) * 0.66, colw(0.5) * 0.34])]
    if r.get("consensus"):
        c = r["consensus"]
        right = [section(L["street"], L["src_ana"], st, width=colw(0.5)), Spacer(1, 2 * mm), kpis(c["kpis"], st, cols=2, width=colw(0.5)), Spacer(1, 2 * mm),
                 Paragraph(esc(c["note"]), st["small"])]
    if left or right:
        story += [CondPageBreak(60 * mm), KeepTogether([two_cols(left or [Spacer(1, 1)], right or [Spacer(1, 1)], 0.5)]), Spacer(1, 5 * mm)]
    if r.get("ai"):
        a = r["ai"]
        story += [CondPageBreak(60 * mm), section(L["ai"], L["src_ai"], st), Spacer(1, 2 * mm)]
        if a.get("lean"):
            story.append(Paragraph(f'<font name="Sans-Semi" color="{hexc(a["color"])}">{esc(a["lean"])}</font>'
                                   f'<font color="{hexc(MUTED)}"> · {esc(a.get("conviction", ""))}</font>', st["body"]))
            story.append(Spacer(1, 1.5 * mm))
        for ptxt in a["paragraphs"]:
            story += [Paragraph(esc(ptxt), st["ai"]), Spacer(1, 2 * mm)]
    story += _closing(story, L["disclaimer"], st)
    return _build({"title": f'{r["ticker"]} · Market Brief', "band": L["band"], "footer": L["footer"], "page_fmt": L["page"],
                   "subject": r["name"]}, story)


# --------------------------------------------------------------------------- portfolio report
def portfolio_pdf(r: dict) -> bytes:
    st = _styles()
    L = r["labels"]
    story: list = [Paragraph(esc(L["kicker"]), st["kicker"]), Paragraph(esc(L["title"]), st["title"]),
                   Paragraph(esc(r["meta_line"]), st["sub"]), Spacer(1, 5 * mm), kpis(r["kpis"], st, cols=4), Spacer(1, 4 * mm)]
    if r.get("summary"):
        story += [callout(esc(r["summary"]), st), Spacer(1, 4 * mm)]
    story += [section(L["holdings"], L["src_mkt_calc"], st), Spacer(1, 2 * mm),
              table(r["hold_header"], r["hold_rows"], st, widths=[CONTENT_W * w for w in (0.11, 0.25, 0.09, 0.1, 0.1, 0.13, 0.09, 0.13)],
                    numeric_from=2), Spacer(1, 3 * mm)]
    story += [two_cols([Paragraph(esc(L["by_position"]).upper(), st["th"]), Spacer(1, 1.5 * mm), stacked_bar(r["alloc_pos"], colw(0.5))],
                       [Paragraph(esc(L["by_sector"]).upper(), st["th"]), Spacer(1, 1.5 * mm), stacked_bar(r["alloc_sec"], colw(0.5))], 0.5),
              Spacer(1, 5 * mm)]
    if r.get("perf"):
        p = r["perf"]
        story += [CondPageBreak(75 * mm), section(L["performance"], L["src_calc"], st), Spacer(1, 2 * mm),
                  line_chart([(L["you"], p["port"], ACCENT), ("S&P 500", p["bench"], FAINT)], p["dates"], CONTENT_W, 58 * mm,
                             y_fmt=lambda v: f"{v:+.0f}%", zero_line=True), Spacer(1, 4 * mm)]
    if r.get("attr"):
        a = r["attr"]
        left = [section(L["attribution"], L["src_calc"], st, width=colw(0.5)), Spacer(1, 2 * mm), kpis(a["kpis"], st, cols=3, width=colw(0.5)),
                Spacer(1, 2 * mm), hbars(a["effect_labels"], a["effect_values"], colw(0.5)), Spacer(1, 1.5 * mm), Paragraph(esc(a["note"]), st["small"])]
        right = [section(L["contrib"], " ", st, width=colw(0.5)), Spacer(1, 2 * mm), hbars(a["tick_labels"], a["tick_values"], colw(0.5))]
        story += [CondPageBreak(80 * mm), KeepTogether([two_cols(left, right, 0.5)]), Spacer(1, 3 * mm)]
        if a.get("sector_rows"):
            story += [table(a["sector_header"], a["sector_rows"], st), Spacer(1, 5 * mm)]
    if r.get("risk_kpis"):
        block = [section(L["risk"], L["src_calc"], st), Spacer(1, 2 * mm), kpis(r["risk_kpis"], st, cols=4)]
        if r.get("risk_rows"):
            block += [Spacer(1, 3 * mm), table(r["risk_header"], r["risk_rows"], st)]
        if r.get("risk_note"):
            block += [Spacer(1, 1.5 * mm), Paragraph(esc(r["risk_note"]), st["small"])]
        story += [CondPageBreak(70 * mm), KeepTogether(block), Spacer(1, 5 * mm)]
    if r.get("profile"):
        pr = r["profile"]
        story += [CondPageBreak(60 * mm), section(L["profile"], L["src_calc"], st), Spacer(1, 2 * mm),
                  Paragraph(esc(pr["line"]), st["lead"]), Spacer(1, 2 * mm)] + bullets(pr["checks"], st) + [Spacer(1, 5 * mm)]
    if r.get("opt"):
        o = r["opt"]
        story += [CondPageBreak(80 * mm), KeepTogether([section(L["recommended"], L["src_calc"], st), Spacer(1, 2 * mm),
                                                        Paragraph(esc(o["line"]), st["body"]), Spacer(1, 2.5 * mm),
                                                        table(o["header"], o["rows"], st), Spacer(1, 3 * mm),
                                                        table(o["move_header"], o["moves"], st) if o.get("moves") else Spacer(1, 1),
                                                        Spacer(1, 1.5 * mm), Paragraph(esc(o["note"]), st["small"])]), Spacer(1, 5 * mm)]
    if r.get("ai"):
        story += [CondPageBreak(50 * mm), section(L["ai"], L["src_ai"], st), Spacer(1, 2 * mm)]
        for ptxt in r["ai"]:
            story += [Paragraph(esc(ptxt), st["ai"]), Spacer(1, 2 * mm)]
    story += _closing(story, L["disclaimer"], st)
    return _build({"title": "Portfolio · Market Brief", "band": L["band"], "footer": L["footer"], "page_fmt": L["page"]}, story)


def stamp() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d")
