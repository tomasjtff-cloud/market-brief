"""Visual layer: palettes for light and dark mode, global CSS and small HTML building blocks.

Design notes
- A financial "morning paper": Newsreader serif for headlines and the note, IBM Plex Sans for data.
- Navy sidebar as the fixed desk; content on cool paper (light) or deep ink (dark).
- Every number carries where it came from: market data, reported (SEC), calculated, or AI-written.
- Green/red only for direction, always with a sign. Yield moves stay neutral.
"""
from __future__ import annotations

import html

import streamlit as st

PALETTES = {
    "light": {
        "paper": "#F4F6F9", "surface": "#FFFFFF", "raised": "#F8FAFC", "ink": "#13202F", "body": "#263445",
        "muted": "#5B6878", "faint": "#8A97A8", "line": "#DCE2EA", "soft": "#EDF0F4", "accent": "#2457D6",
        "up": "#0E8A3E", "down": "#C8362F", "up_bg": "#E3F4E9", "down_bg": "#FBE7E5", "flat_bg": "#EEF1F5",
        "calc": "#5B45C9", "calc_bg": "#EEEBFB", "ai": "#9A5B00", "ai_bg": "#FBF0DC", "rep": "#2457D6",
        "rep_bg": "#E6EDFC", "grid": "rgba(19,32,47,0.07)", "fill": "rgba(36,87,214,0.10)", "orange": "#E07A2E",
    },
    "dark": {
        "paper": "#0B1220", "surface": "#111A2A", "raised": "#152034", "ink": "#E8EDF4", "body": "#C9D3E0",
        "muted": "#93A1B5", "faint": "#6F7F96", "line": "#223049", "soft": "#1A263A", "accent": "#6E9BFF",
        "up": "#3CCB7F", "down": "#F26B61", "up_bg": "rgba(60,203,127,0.14)", "down_bg": "rgba(242,107,97,0.15)",
        "flat_bg": "#1C2840", "calc": "#B3A6FF", "calc_bg": "rgba(179,166,255,0.14)", "ai": "#F2B84B",
        "ai_bg": "rgba(242,184,75,0.14)", "rep": "#8FB2FF", "rep_bg": "rgba(110,155,255,0.15)",
        "grid": "rgba(232,237,244,0.07)", "fill": "rgba(110,155,255,0.14)", "orange": "#F0954B",
    },
}


def mode() -> str:
    try:
        return "dark" if st.context.theme.type == "dark" else "light"
    except Exception:
        return "light"


def P() -> dict:
    return PALETTES[mode()]


def _css(p: dict) -> str:
    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=Newsreader:opsz,wght@6..72,400;6..72,500;6..72,600&display=swap');
:root {{
  --paper:{p['paper']}; --surface:{p['surface']}; --raised:{p['raised']}; --ink:{p['ink']}; --body:{p['body']};
  --muted:{p['muted']}; --faint:{p['faint']}; --line:{p['line']}; --soft:{p['soft']}; --accent:{p['accent']};
  --up:{p['up']}; --down:{p['down']}; --up-bg:{p['up_bg']}; --down-bg:{p['down_bg']}; --flat-bg:{p['flat_bg']};
  --calc:{p['calc']}; --calc-bg:{p['calc_bg']}; --ai:{p['ai']}; --ai-bg:{p['ai_bg']}; --rep:{p['rep']}; --rep-bg:{p['rep_bg']};
  --serif:'Newsreader', Georgia, serif; --sans:'IBM Plex Sans', system-ui, sans-serif;
}}
[data-testid="stHeader"] {{ background: transparent; }}
[data-testid="stMainBlockContainer"] {{ max-width: 1320px; padding-top: 1.6rem; }}
.num, .mb-board, .mb-stats, .mb-rail, table {{ font-variant-numeric: tabular-nums; }}
a {{ color: var(--accent); }}

/* sidebar */
[data-testid="stSidebar"] .mb-brand {{ font-family: var(--serif); font-size: 1.55rem; font-weight: 600; color: #FFF;
  letter-spacing: -0.01em; }}
[data-testid="stSidebar"] .mb-brand-sub {{ color: #9FB0C6; font-size: 0.82rem; margin: 0.1rem 0 0.4rem; }}
[data-testid="stSidebar"] [role="radiogroup"] {{ gap: 2px; }}
[data-testid="stSidebar"] [data-testid="stRadioOption"] {{ padding: 0.45rem 0.7rem; border-radius: 8px; width: 100%; margin: 0; }}
[data-testid="stSidebar"] [data-testid="stRadioOption"]:hover {{ background: #1A2B42; }}
[data-testid="stSidebar"] [data-testid="stRadioOption"][data-selected="true"] {{ background: #22385A; }}
[data-testid="stSidebar"] [data-testid="stRadioOption"] > div > div:not([data-testid="stMarkdownContainer"]) {{ display: none; }}
[data-testid="stSidebar"] [data-testid="stRadioOption"] p {{ font-size: 0.97rem; font-weight: 500; color: #E6ECF3; }}
[data-testid="stSidebar"] .mb-side-h {{ color: #9FB0C6; font-size: 0.82rem; font-weight: 500; margin: 0.2rem 0 0.4rem; }}
[data-testid="stSidebar"] [class*="st-key-open_"] button > div {{ justify-content: flex-start; width: 100%; }}
[data-testid="stSidebar"] [class*="st-key-open_"] button {{ background: transparent; border: none; color: #E6ECF3; width: 100%;
  padding: 0.25rem 0.55rem; min-height: 2rem; font-weight: 600; letter-spacing: 0.02em; }}
[data-testid="stSidebar"] [class*="st-key-open_"] button:hover {{ background: #1A2B42; color: #FFF; }}
[data-testid="stSidebar"] [class*="st-key-rm_"] button {{ background: transparent; border: none; color: #7C8DA4;
  min-height: 2rem; padding: 0 0.4rem; }}
[data-testid="stSidebar"] [class*="st-key-rm_"] button:hover {{ color: #FFB4AC; background: transparent; }}

[data-testid="stSidebar"] [data-testid="stHorizontalBlock"] {{ flex-wrap: nowrap !important; gap: 0.3rem; }}
[data-testid="stSidebar"] [data-testid="stColumn"] {{ min-width: 0 !important; width: auto !important; }}
[data-testid="stSidebar"] [data-testid="stColumn"]:last-child {{ flex: 0 0 2.4rem !important; }}

/* masthead */
.mb-mast {{ display: flex; justify-content: space-between; align-items: flex-end; gap: 1.2rem; flex-wrap: wrap;
  padding-bottom: 1rem; border-bottom: 1px solid var(--line); margin-bottom: 1.2rem; }}
.mb-date {{ font-family: var(--serif); font-size: clamp(2.2rem, 4vw, 3.3rem); font-weight: 600; line-height: 1.02;
  letter-spacing: -0.02em; color: var(--ink); margin: 0; }}
.mb-dek {{ color: var(--muted); font-size: 0.98rem; margin-top: 0.5rem; }}
.mb-dot {{ width: 9px; height: 9px; border-radius: 50%; display: inline-block; margin-right: 0.45rem; vertical-align: 1px; }}
.mb-dot.open {{ background: var(--up); box-shadow: 0 0 0 4px var(--up-bg); }}
.mb-dot.closed {{ background: var(--faint); box-shadow: 0 0 0 4px var(--flat-bg); }}
.mb-clocks {{ display: flex; gap: 1.4rem; }}
.mb-clock .city {{ color: var(--faint); font-size: 0.78rem; }}
.mb-clock .t {{ color: var(--ink); font-size: 1.15rem; font-weight: 600; }}

/* boards */
.mb-board-h {{ display: flex; justify-content: space-between; align-items: baseline; margin: 1.2rem 0 0.5rem; }}
.mb-board-h b {{ color: var(--ink); font-weight: 600; font-size: 0.98rem; }}
.mb-board-h span {{ color: var(--faint); font-size: 0.78rem; }}
.mb-board {{ background: var(--line); border: 1px solid var(--line); border-radius: 14px; gap: 1px; display: grid;
  grid-template-columns: repeat(var(--cols, 3), minmax(0, 1fr)); overflow: hidden; }}
.mb-cell {{ background: var(--surface); padding: 0.9rem 1.05rem 0.8rem; }}
.mb-cell .name {{ color: var(--muted); font-size: 0.85rem; }}
.mb-cell .row {{ display: flex; align-items: center; justify-content: space-between; gap: 0.3rem 0.5rem; margin-top: 0.15rem; flex-wrap: wrap; }}
.mb-cell .px {{ font-size: 1.42rem; font-weight: 600; color: var(--ink); white-space: nowrap; }}
.mb-cell .asof {{ color: var(--faint); font-size: 0.74rem; margin-top: 0.35rem; }}
.mb-chip {{ font-size: 0.8rem; font-weight: 600; padding: 0.12rem 0.5rem; border-radius: 999px; white-space: nowrap; }}
.mb-chip.up {{ color: var(--up); background: var(--up-bg); }}
.mb-chip.down {{ color: var(--down); background: var(--down-bg); }}
.mb-chip.flat {{ color: var(--muted); background: var(--flat-bg); }}
.mb-range {{ margin-top: 0.55rem; }}
.mb-range .track {{ position: relative; height: 4px; border-radius: 4px; background: var(--soft); }}
.mb-range .fill {{ position: absolute; top: 0; bottom: 0; border-radius: 4px; background: var(--line); }}
.mb-range .mark {{ position: absolute; top: -4px; width: 3px; height: 12px; border-radius: 2px; background: var(--ink);
  transform: translateX(-1px); }}
.mb-range .ends {{ display: flex; justify-content: space-between; color: var(--faint); font-size: 0.7rem; margin-top: 0.25rem; }}
.mb-foot {{ color: var(--faint); font-size: 0.78rem; margin: 0.5rem 0 0; line-height: 1.5; }}
@media (max-width: 760px) {{
  .mb-board {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
  .mb-cell {{ padding: 0.8rem 0.85rem; }} .mb-cell .row {{ flex-wrap: wrap; }} .mb-cell .px {{ font-size: 1.2rem; }}
}}

/* provenance tags */
.src {{ font-size: 0.7rem; font-weight: 600; padding: 0.08rem 0.42rem; border-radius: 5px; white-space: nowrap; vertical-align: 1px; }}
.src.mkt {{ color: var(--muted); background: var(--flat-bg); }}
.src.rep {{ color: var(--rep); background: var(--rep-bg); }}
.src.calc {{ color: var(--calc); background: var(--calc-bg); }}
.src.ai {{ color: var(--ai); background: var(--ai-bg); }}

/* note */
.mb-section {{ font-family: var(--serif); font-size: 1.6rem; font-weight: 600; color: var(--ink); margin: 2rem 0 0.7rem;
  letter-spacing: -0.01em; display: flex; align-items: center; gap: 0.6rem; }}
.mb-lead {{ font-family: var(--serif); font-size: 1.3rem; line-height: 1.62; color: var(--ink); max-width: 70ch; margin: 0 0 1.2rem; }}
.mb-story {{ background: var(--surface); border: 1px solid var(--line); border-radius: 12px; padding: 1.1rem 1.25rem 1rem; }}
.mb-story.top {{ border-left: 4px solid var(--accent); padding-left: 1.35rem; }}
.mb-story h3 {{ font-family: var(--serif); font-size: 1.24rem; line-height: 1.3; margin: 0 0 0.55rem; color: var(--ink);
  font-weight: 600; padding: 0; }}
.mb-story.top h3 {{ font-size: 1.55rem; }}
.mb-story p, .mb-story li {{ margin: 0 0 0.45rem; line-height: 1.55; font-size: 0.95rem; color: var(--body); }}
.mb-story p b {{ color: var(--ink); font-weight: 600; }}
.mb-story .watch {{ color: var(--muted); }}
.mb-sources {{ display: flex; gap: 0.4rem; flex-wrap: wrap; margin-top: 0.7rem; }}
.mb-src {{ font-size: 0.76rem; padding: 0.15rem 0.55rem; border: 1px solid var(--line); border-radius: 999px;
  color: var(--muted) !important; text-decoration: none !important; }}
.mb-src:hover {{ border-color: var(--accent); color: var(--accent) !important; }}
.mb-grid2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 0.85rem; margin-top: 0.85rem; align-items: start; }}
.mb-grid3 {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.85rem; margin-top: 0.85rem; align-items: start; }}
@media (max-width: 900px) {{ .mb-grid2, .mb-grid3 {{ grid-template-columns: 1fr; }} }}
.mb-note {{ color: var(--faint); font-size: 0.8rem; margin-top: 0.8rem; }}
.mb-skel {{ height: 0.95rem; border-radius: 6px; background: var(--soft); margin: 0.55rem 0; }}

/* lists */
.mb-list {{ background: var(--surface); border: 1px solid var(--line); border-radius: 12px; padding: 0.2rem 1.15rem; }}
.mb-item {{ display: grid; grid-template-columns: 1fr auto; gap: 1rem; padding: 0.68rem 0; border-bottom: 1px solid var(--soft); }}
.mb-item:last-child {{ border-bottom: none; }}
.mb-item a {{ color: var(--ink) !important; text-decoration: none !important; font-weight: 500; line-height: 1.4; }}
.mb-item a:hover {{ color: var(--accent) !important; }}
.mb-item .meta {{ color: var(--faint); font-size: 0.78rem; white-space: nowrap; text-align: right; line-height: 1.5; }}
.mb-item .sum {{ color: var(--muted); font-size: 0.87rem; margin-top: 0.2rem; line-height: 1.45; }}

/* right rail */
.mb-rail-h {{ font-family: var(--serif); font-size: 1.3rem; font-weight: 600; color: var(--ink); margin: 0.2rem 0 0.6rem; }}
[class*="st-key-rail_"] {{ background: var(--surface); border: 1px solid var(--line); border-radius: 12px; padding: 0.7rem 0.85rem 0.55rem; gap: 0.3rem; }}
[class*="st-key-rail_"]:hover {{ border-color: var(--accent); }}
[class*="st-key-rail_"] button {{ min-height: 1.9rem; padding: 0.1rem 0.6rem; font-size: 0.82rem; }}
.mb-rrow {{ display: flex; justify-content: space-between; align-items: flex-start; gap: 0.5rem; }}
.mb-rrow .tk {{ font-weight: 600; color: var(--ink); letter-spacing: 0.02em; }}
.mb-rrow .co {{ color: var(--muted); font-size: 0.8rem; max-width: 12rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.mb-rrow .px {{ font-weight: 600; color: var(--ink); text-align: right; }}
.mb-spark {{ display: block; width: 100%; height: 34px; margin: 0.35rem 0 0.1rem; }}
.mb-cal {{ background: var(--surface); border: 1px solid var(--line); border-radius: 12px; padding: 0.3rem 0.9rem; }}
.mb-cal div {{ display: grid; grid-template-columns: 4.2rem 1fr; gap: 0.5rem; padding: 0.5rem 0; border-bottom: 1px solid var(--soft); font-size: 0.86rem; color: var(--body); }}
.mb-cal span:last-child {{ text-align: right; color: var(--muted); }}
.mb-cal div:last-child {{ border-bottom: none; }}
.mb-cal b {{ color: var(--ink); }}

/* watchlist table */
[class*="st-key-wl_"] {{ background: var(--surface); border: 1px solid var(--line); border-radius: 12px; padding: 0.85rem 1.1rem; }}
[class*="st-key-wl_"]:hover {{ border-color: var(--accent); }}
.mb-table {{ padding: 0 1.1rem; }}
.mb-tr {{ display: grid; grid-template-columns: 1.7fr 1fr 1.6fr 1.2fr 1fr 1.25fr; gap: 1rem; align-items: center;
  padding: 0.85rem 1.1rem; border-bottom: 1px solid var(--soft); }}
.mb-tr:last-child {{ border-bottom: none; }}
.mb-tr.head {{ color: var(--faint); font-size: 0.78rem; padding: 0 1.1rem 0.1rem; border: none; }}
.mb-tr .tk {{ font-weight: 600; color: var(--ink); font-size: 1.02rem; }}
.mb-tr .co {{ color: var(--muted); font-size: 0.82rem; }}
.mb-tr .px {{ font-weight: 600; color: var(--ink); font-size: 1.08rem; }}
.mb-tr .small {{ color: var(--muted); font-size: 0.8rem; line-height: 1.55; }}
.mb-tr .small b {{ color: var(--ink); font-weight: 600; }}
@media (max-width: 900px) {{ .mb-tr {{ grid-template-columns: 1fr 1fr; }} .mb-tr.head {{ display: none; }} }}
.pos {{ color: var(--up) !important; }} .neg {{ color: var(--down) !important; }}

/* stock page */
.mb-stock {{ display: flex; justify-content: space-between; align-items: flex-end; gap: 1.5rem; flex-wrap: wrap; margin: 0.5rem 0 1rem; }}
.mb-stock .idt {{ display: flex; gap: 1rem; align-items: center; }}
.mb-stock .logo {{ width: 54px; height: 54px; border-radius: 12px; background: #FFF; border: 1px solid var(--line);
  object-fit: contain; padding: 6px; }}
.mb-stock .co {{ font-family: var(--serif); font-size: clamp(1.9rem, 3.4vw, 2.7rem); font-weight: 600; line-height: 1.05;
  letter-spacing: -0.02em; color: var(--ink); }}
.mb-stock .meta {{ color: var(--muted); margin-top: 0.35rem; display: flex; gap: 0.5rem; align-items: center; flex-wrap: wrap; font-size: 0.92rem; }}
.mb-tag {{ font-size: 0.78rem; font-weight: 600; padding: 0.1rem 0.5rem; border-radius: 6px; background: var(--flat-bg); color: var(--ink); }}
.mb-stock .quote {{ text-align: right; }}
.mb-stock .big {{ font-size: 2.2rem; font-weight: 600; color: var(--ink); line-height: 1; }}
.mb-stock .asof {{ color: var(--faint); font-size: 0.78rem; margin-top: 0.45rem; }}
.mb-stats {{ background: var(--line); border: 1px solid var(--line); border-radius: 12px; display: grid; gap: 1px;
  grid-template-columns: repeat(var(--cols, 4), minmax(0, 1fr)); overflow: hidden; margin: 0.5rem 0 0.4rem; }}
.mb-stat {{ background: var(--surface); padding: 0.75rem 0.95rem; }}
.mb-stat .k {{ color: var(--muted); font-size: 0.8rem; display: flex; justify-content: space-between; gap: 0.3rem; }}
.mb-stat .v {{ font-size: 1.28rem; font-weight: 600; color: var(--ink); margin-top: 0.12rem; }}
.mb-stat .s {{ color: var(--faint); font-size: 0.72rem; margin-top: 0.1rem; }}
@media (max-width: 900px) {{ .mb-stats {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }} }}
.mb-callout {{ background: var(--surface); border: 1px solid var(--line); border-left: 4px solid var(--accent);
  border-radius: 10px; padding: 0.85rem 1.1rem; line-height: 1.55; color: var(--body); margin: 0.75rem 0; }}
.mb-callout b {{ color: var(--ink); }}
.mb-rt {{ width: 100%; border-collapse: collapse; background: var(--surface); border: 1px solid var(--line); border-radius: 12px; overflow: hidden; }}
.mb-rt th {{ text-align: right; color: var(--faint); font-weight: 500; font-size: 0.78rem; padding: 0.6rem 0.9rem; background: var(--raised); }}
.mb-rt th:first-child, .mb-rt td:first-child {{ text-align: left; }}
.mb-rt td {{ text-align: right; padding: 0.6rem 0.9rem; border-top: 1px solid var(--soft); color: var(--ink); font-size: 0.92rem; }}
.mb-verdict {{ background: var(--surface); border: 1px solid var(--line); border-radius: 14px; padding: 1.15rem 1.35rem;
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; margin: 0.6rem 0 0.4rem; }}
.mb-verdict .k {{ color: var(--muted); font-size: 0.84rem; }}
.mb-verdict .v {{ font-size: 2rem; font-weight: 600; color: var(--ink); line-height: 1.15; }}
.mb-verdict .label {{ font-family: var(--serif); font-size: 1.35rem; font-weight: 600; }}
@media (max-width: 760px) {{ .mb-verdict {{ grid-template-columns: 1fr; }} }}
.mb-h3 {{ font-family: var(--serif); font-size: 1.3rem; font-weight: 600; color: var(--ink); margin: 1.4rem 0 0.5rem;
  display: flex; align-items: center; gap: 0.5rem; }}

/* streamlit widgets */
[data-baseweb="tab-list"] {{ gap: 1.4rem; border-bottom: 1px solid var(--line); }}
[data-baseweb="tab"] p {{ font-size: 1rem; font-weight: 500; }}
[data-testid="stExpander"] details {{ background: var(--surface); border-radius: 12px; }}
[data-testid="stCaptionContainer"] {{ color: var(--faint); }}
</style>
"""


def inject_css() -> None:
    st.html(_css(P()))


def esc(text) -> str:
    """Escape for HTML, including $ so nothing is ever read as math."""
    return html.escape(str(text or "")).replace("$", "&#36;")


def chip(pct_value: float | None, suffix: str = "") -> str:
    """A signed change pill. `pct_value` is already in percent (1.2 = +1.2%)."""
    if pct_value is None:
        return '<span class="mb-chip flat">n/a</span>'
    cls = "up" if pct_value > 0.004 else "down" if pct_value < -0.004 else "flat"
    sign = "+" if pct_value > 0 else "−" if pct_value < 0 else ""
    return f'<span class="mb-chip {cls}">{sign}{abs(pct_value):.2f}%{esc(suffix)}</span>'


def signed_class(x: float | None) -> str:
    if x is None:
        return ""
    return "pos" if x > 0 else "neg" if x < 0 else ""


SOURCE_LABELS = {"mkt": "Market data", "rep": "Reported", "calc": "Calculated", "ai": "AI-written"}


def src(kind: str) -> str:
    """Provenance tag: market data, reported (SEC filings), calculated here, or AI-written."""
    return f'<span class="src {kind}">{SOURCE_LABELS[kind]}</span>'


def range_bar(low: float | None, high: float | None, value: float | None, fmt: str = "${:,.2f}",
              left: str = "Low", right: str = "High") -> str:
    if not low or not high or value is None or high <= low:
        return ""
    pos = max(0.0, min(1.0, (value - low) / (high - low))) * 100
    return (f'<div class="mb-range"><div class="track"><div class="fill" style="left:0;width:{pos:.1f}%"></div>'
            f'<div class="mark" style="left:{pos:.1f}%"></div></div>'
            f'<div class="ends"><span>{left} {esc(fmt.format(low))}</span><span>{right} {esc(fmt.format(high))}</span></div></div>')


def spark_svg(values, up: bool | None = None, width: int = 220, height: int = 34) -> str:
    """Tiny trend line, as an <img> with an inline SVG (st.html strips raw <svg> tags)."""
    import base64

    vals = [float(v) for v in values if v == v]
    if len(vals) < 2:
        return ""
    lo, hi = min(vals), max(vals)
    span = (hi - lo) or 1.0
    step = width / (len(vals) - 1)
    pts = [(i * step, height - 3 - (v - lo) / span * (height - 6)) for i, v in enumerate(vals)]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    area = f"0,{height} " + line + f" {width},{height}"
    rising = vals[-1] >= vals[0] if up is None else up
    p = P()
    color = p["up"] if rising else p["down"]
    fill = p["up_bg"] if rising else p["down_bg"]
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" preserveAspectRatio="none">'
           f'<polygon points="{area}" fill="{fill}"/><polyline points="{line}" fill="none" stroke="{color}" '
           f'stroke-width="1.8" vector-effect="non-scaling-stroke" stroke-linejoin="round"/></svg>')
    b64 = base64.b64encode(svg.encode()).decode()
    return f'<img class="mb-spark" alt="" src="data:image/svg+xml;base64,{b64}">'
