"""Visual layer: palettes (light and dark), global CSS and small HTML building blocks.

Design direction: a professional market terminal in the Yahoo Finance / Finviz family.
- Dense, scannable data; one sans family (Inter) with tabular figures everywhere.
- A navy masthead and a moving ticker tape frame every page; content sits on calm surfaces.
- Green/red only for direction, always with a sign. Every figure carries its provenance.
"""
from __future__ import annotations

import base64
import html

import streamlit as st

PALETTES = {
    "light": {
        "paper": "#F3F5F8", "surface": "#FFFFFF", "raised": "#F7F9FB", "ink": "#0F1A2A", "body": "#2A3647",
        "muted": "#5D6B7E", "faint": "#8794A6", "line": "#DFE4EB", "soft": "#EEF1F5", "accent": "#1F5BD8",
        "up": "#0A8F4E", "down": "#D2342F", "up_bg": "#E2F5EA", "down_bg": "#FCE8E6", "flat_bg": "#EEF1F5",
        "calc": "#5B45C9", "calc_bg": "#EEEBFB", "ai": "#9A5B00", "ai_bg": "#FBF0DC", "rep": "#1F5BD8",
        "rep_bg": "#E6EDFC", "grid": "rgba(15,26,42,0.06)", "fill": "rgba(31,91,216,0.10)", "orange": "#E0782A",
        "violet": "#6E56CF", "teal": "#0E9AA7", "chart_bg": "#FFFFFF",
    },
    "dark": {
        "paper": "#0A0F18", "surface": "#111827", "raised": "#151E2E", "ink": "#E9EEF5", "body": "#C7D1DE",
        "muted": "#93A0B3", "faint": "#6C7A8F", "line": "#222E42", "soft": "#18233A", "accent": "#5E8EFF",
        "up": "#2FC57A", "down": "#F2645B", "up_bg": "rgba(47,197,122,0.14)", "down_bg": "rgba(242,100,91,0.15)",
        "flat_bg": "#1B2740", "calc": "#B3A6FF", "calc_bg": "rgba(179,166,255,0.14)", "ai": "#F2B84B",
        "ai_bg": "rgba(242,184,75,0.14)", "rep": "#8FB2FF", "rep_bg": "rgba(94,142,255,0.15)",
        "grid": "rgba(233,238,245,0.06)", "fill": "rgba(94,142,255,0.14)", "orange": "#F0954B",
        "violet": "#A08CFF", "teal": "#35C2CE", "chart_bg": "#111827",
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
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
:root {{
  --paper:{p['paper']}; --surface:{p['surface']}; --raised:{p['raised']}; --ink:{p['ink']}; --body:{p['body']};
  --muted:{p['muted']}; --faint:{p['faint']}; --line:{p['line']}; --soft:{p['soft']}; --accent:{p['accent']};
  --up:{p['up']}; --down:{p['down']}; --up-bg:{p['up_bg']}; --down-bg:{p['down_bg']}; --flat-bg:{p['flat_bg']};
  --calc:{p['calc']}; --calc-bg:{p['calc_bg']}; --ai:{p['ai']}; --ai-bg:{p['ai_bg']}; --rep:{p['rep']}; --rep-bg:{p['rep_bg']};
  --navy: #0B1526; --navy2: #13213A;
}}
html, body, [class*="css"], .stApp {{ font-family: 'Inter', system-ui, sans-serif; }}
.stApp {{ font-feature-settings: "tnum" 1, "cv11" 1; }}
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"], [data-testid="collapsedControl"] {{ display: none !important; }}
[data-testid="stHeader"] {{ background: transparent; height: 0; }}
[data-testid="stToolbar"] {{ top: 6px; right: 8px; }}
[data-testid="stMainBlockContainer"] {{ max-width: 1400px; padding: 0 1.4rem 3rem; }}
.num {{ font-variant-numeric: tabular-nums; }}
a {{ color: var(--accent); }}
.pos {{ color: var(--up) !important; }} .neg {{ color: var(--down) !important; }}
h1, h2, h3, h4 {{ font-family: 'Inter', system-ui, sans-serif !important; letter-spacing: -0.01em; }}

/* ---------- masthead (top bar) ---------- */
.st-key-topbar {{ background: var(--navy); margin: 0 -1.4rem; padding: 0.55rem 1.4rem 0.5rem; width: calc(100% + 2.8rem) !important; max-width: none !important;
  border-bottom: 1px solid #1E2C47; gap: 0.4rem; }}
.st-key-topbar p, .st-key-topbar label {{ color: #DCE5F2; }}
.mb-logo {{ display: flex; align-items: center; gap: 0.55rem; color: #FFF; font-weight: 700; font-size: 1.12rem;
  letter-spacing: -0.02em; white-space: nowrap; }}
.mb-logo .mark {{ width: 26px; height: 26px; border-radius: 7px; background: linear-gradient(135deg,#3B7BFF,#16C784);
  display: inline-flex; align-items: center; justify-content: center; color: #FFF; font-size: 0.8rem; font-weight: 800; }}
.mb-logo small {{ display: block; color: #8FA3C2; font-weight: 500; font-size: 0.7rem; letter-spacing: 0; }}
.st-key-topbar [data-testid="stButtonGroup"] button {{ background: transparent; border: none; color: #C9D6EA;
  font-weight: 500; padding: 0.3rem 0.75rem; min-height: 2.1rem; }}
.st-key-topbar [data-testid="stButtonGroup"] button:hover {{ background: var(--navy2); color: #FFF; }}
.st-key-topbar [data-testid="stButtonGroup"] button[aria-checked="true"],
.st-key-topbar [data-testid="stButtonGroup"] button[kind="segmented_controlActive"] {{ background: #1F3460; color: #FFF; }}
.st-key-topbar input {{ background: #13213A !important; color: #FFF !important; border-color: #263A5E !important; }}
.st-key-topbar input::placeholder {{ color: #7F93B3 !important; }}
.st-key-topbar [data-baseweb="select"] > div {{ background: #13213A; border-color: #263A5E; color: #FFF; }}

/* ---------- ticker tape ---------- */
.mb-tape {{ margin: 0 -1.4rem 1rem; background: #0F1D33; border-bottom: 1px solid #1E2C47; overflow: hidden;
  white-space: nowrap; position: relative; }}
.mb-tape .track {{ display: inline-flex; animation: mbscroll 70s linear infinite; padding: 0.42rem 0; }}
.mb-tape:hover .track {{ animation-play-state: paused; }}
.mb-tape a {{ display: inline-flex; gap: 0.45rem; align-items: baseline; padding: 0 1.15rem; border-right: 1px solid #1E2C47;
  color: #DCE5F2 !important; text-decoration: none !important; font-size: 0.82rem; }}
.mb-tape a b {{ color: #FFF; font-weight: 600; }}
.mb-tape .u {{ color: #33D17A; }} .mb-tape .d {{ color: #FF6B61; }} .mb-tape .f {{ color: #9FB0C8; }}
@keyframes mbscroll {{ from {{ transform: translateX(0); }} to {{ transform: translateX(-50%); }} }}
@media (prefers-reduced-motion: reduce) {{ .mb-tape .track {{ animation: none; }} .mb-tape {{ overflow-x: auto; }} }}

/* ---------- page header ---------- */
.mb-ph {{ display: flex; justify-content: space-between; align-items: flex-end; gap: 1rem; flex-wrap: wrap; margin: 0.4rem 0 0.9rem; }}
.mb-ph h1 {{ font-size: 1.65rem; font-weight: 700; margin: 0; padding: 0; color: var(--ink); }}
.mb-ph .sub {{ color: var(--muted); font-size: 0.88rem; margin-top: 0.25rem; }}
.mb-dot {{ width: 8px; height: 8px; border-radius: 50%; display: inline-block; margin-right: 0.4rem; vertical-align: 1px; }}
.mb-dot.open {{ background: var(--up); box-shadow: 0 0 0 3px var(--up-bg); }}
.mb-dot.closed {{ background: var(--faint); box-shadow: 0 0 0 3px var(--flat-bg); }}
.mb-clocks {{ display: flex; gap: 1.2rem; }}
.mb-clock {{ text-align: right; }}
.mb-clock .c {{ color: var(--faint); font-size: 0.72rem; }}
.mb-clock .t {{ color: var(--ink); font-size: 0.98rem; font-weight: 600; }}

/* ---------- panels ---------- */
.mb-panel {{ background: var(--surface); border: 1px solid var(--line); border-radius: 10px; padding: 0.85rem 1rem; }}
[class*="st-key-panel_"] {{ background: var(--surface); border: 1px solid var(--line); border-radius: 10px; padding: 0.8rem 1rem 0.6rem; gap: 0.35rem; }}
.mb-h {{ display: flex; justify-content: space-between; align-items: center; gap: 0.6rem; margin: 0 0 0.55rem;
  padding-bottom: 0.5rem; border-bottom: 1px solid var(--soft); }}
.mb-h b {{ font-size: 0.98rem; font-weight: 650; color: var(--ink); }}
.mb-h span {{ color: var(--faint); font-size: 0.76rem; display: inline-flex; gap: 0.4rem; align-items: center; }}
.mb-sec {{ font-size: 1.12rem; font-weight: 700; color: var(--ink); margin: 1.3rem 0 0.6rem; display: flex; gap: 0.55rem; align-items: center; }}
.mb-foot {{ color: var(--faint); font-size: 0.76rem; margin: 0.45rem 0 0; line-height: 1.5; }}

/* ---------- index cards ---------- */
.mb-cards {{ display: grid; grid-template-columns: repeat(var(--cols, 6), minmax(0, 1fr)); gap: 0.65rem; }}
.mb-card {{ background: var(--surface); border: 1px solid var(--line); border-radius: 10px; padding: 0.7rem 0.85rem 0.6rem;
  text-decoration: none !important; display: block; color: inherit !important; }}
a.mb-card:hover {{ border-color: var(--accent); }}
.mb-card .n {{ color: var(--muted); font-size: 0.78rem; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.mb-card .p {{ color: var(--ink); font-size: 1.22rem; font-weight: 650; margin-top: 0.1rem; white-space: nowrap; }}
.mb-card .c {{ font-size: 0.82rem; font-weight: 600; margin-top: 0.05rem; white-space: nowrap; }}
.mb-card .a {{ color: var(--faint); font-size: 0.68rem; margin-top: 0.35rem; }}
@media (max-width: 1100px) {{ .mb-cards {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }} }}
@media (max-width: 640px) {{ .mb-cards {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }} }}

/* ---------- chips, tags, ranges ---------- */
.mb-chip {{ font-size: 0.78rem; font-weight: 600; padding: 0.1rem 0.45rem; border-radius: 5px; white-space: nowrap; }}
.mb-chip.up {{ color: var(--up); background: var(--up-bg); }}
.mb-chip.down {{ color: var(--down); background: var(--down-bg); }}
.mb-chip.flat {{ color: var(--muted); background: var(--flat-bg); }}
.src {{ font-size: 0.66rem; font-weight: 600; padding: 0.06rem 0.38rem; border-radius: 4px; white-space: nowrap; letter-spacing: 0.01em; }}
.src.mkt {{ color: var(--muted); background: var(--flat-bg); }}
.src.rep {{ color: var(--rep); background: var(--rep-bg); }}
.src.calc {{ color: var(--calc); background: var(--calc-bg); }}
.src.ai {{ color: var(--ai); background: var(--ai-bg); }}
.src.ana {{ color: var(--up); background: var(--up-bg); }}
.mb-range {{ margin-top: 0.4rem; min-width: 7rem; }}
.mb-range .track {{ position: relative; height: 4px; border-radius: 4px; background: var(--soft); }}
.mb-range .fill {{ position: absolute; top: 0; bottom: 0; left: 0; border-radius: 4px; background: var(--line); }}
.mb-range .mark {{ position: absolute; top: -3px; width: 3px; height: 10px; border-radius: 2px; background: var(--ink); transform: translateX(-1px); }}
.mb-range .ends {{ display: flex; justify-content: space-between; color: var(--faint); font-size: 0.66rem; margin-top: 0.2rem; gap: 0.4rem; }}
.mb-spark {{ display: block; width: 100%; height: 30px; }}

/* ---------- data tables (Finviz-style) ---------- */
.mb-tbl {{ width: 100%; border-collapse: collapse; font-size: 0.84rem; }}
.mb-tbl th {{ text-align: right; color: var(--muted); font-weight: 600; font-size: 0.74rem; padding: 0.45rem 0.55rem;
  border-bottom: 1px solid var(--line); background: var(--raised); white-space: nowrap; position: sticky; top: 0; }}
.mb-tbl td {{ text-align: right; padding: 0.42rem 0.55rem; border-bottom: 1px solid var(--soft); color: var(--ink); white-space: nowrap; }}
.mb-tbl tr:last-child td {{ border-bottom: none; }}
.mb-tbl tr:hover td {{ background: var(--raised); }}
.mb-tbl .l {{ text-align: left; }}
.mb-tbl a {{ color: var(--accent) !important; font-weight: 600; text-decoration: none !important; }}
.mb-tbl .co {{ color: var(--muted); font-size: 0.78rem; font-weight: 400; display: block; max-width: 14rem; overflow: hidden; text-overflow: ellipsis; }}
.mb-scroll {{ overflow-x: auto; background: var(--surface); border: 1px solid var(--line); border-radius: 10px; }}
.mb-kv {{ display: grid; grid-template-columns: 1fr 1fr; column-gap: 1.4rem; }}
.mb-kv div {{ display: flex; justify-content: space-between; gap: 0.6rem; padding: 0.42rem 0; border-bottom: 1px solid var(--soft); font-size: 0.84rem; }}
.mb-kv div span:first-child {{ color: var(--muted); }}
.mb-kv div span:last-child {{ color: var(--ink); font-weight: 600; text-align: right; }}
@media (max-width: 640px) {{ .mb-kv {{ grid-template-columns: 1fr; }} }}

/* ---------- boards (LatAm, rates) ---------- */
.mb-board {{ background: var(--line); border: 1px solid var(--line); border-radius: 10px; gap: 1px; display: grid;
  grid-template-columns: repeat(var(--cols, 3), minmax(0, 1fr)); overflow: hidden; }}
.mb-cell {{ background: var(--surface); padding: 0.7rem 0.85rem 0.6rem; }}
.mb-cell .name {{ color: var(--muted); font-size: 0.78rem; }}
.mb-cell .row {{ display: flex; align-items: center; justify-content: space-between; gap: 0.3rem 0.5rem; margin-top: 0.12rem; flex-wrap: wrap; }}
.mb-cell .px {{ font-size: 1.15rem; font-weight: 650; color: var(--ink); white-space: nowrap; }}
.mb-cell .asof {{ color: var(--faint); font-size: 0.68rem; margin-top: 0.3rem; }}
@media (max-width: 640px) {{ .mb-board {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }} }}

/* ---------- watch rail ---------- */
.mb-wrow {{ display: grid; grid-template-columns: 1fr 5.5rem auto; gap: 0.6rem; align-items: center; padding: 0.5rem 0;
  border-bottom: 1px solid var(--soft); text-decoration: none !important; color: inherit !important; }}
.mb-wrow:last-child {{ border-bottom: none; }}
.mb-wrow:hover .tk {{ color: var(--accent); }}
.mb-wrow .tk {{ font-weight: 650; color: var(--ink); font-size: 0.9rem; }}
.mb-wrow .co {{ color: var(--muted); font-size: 0.74rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 9rem; }}
.mb-wrow .px {{ text-align: right; font-weight: 600; color: var(--ink); font-size: 0.88rem; }}
.mb-cal div {{ display: grid; grid-template-columns: 4rem 1fr; gap: 0.5rem; padding: 0.4rem 0; border-bottom: 1px solid var(--soft); font-size: 0.82rem; color: var(--body); }}
.mb-cal div:last-child {{ border-bottom: none; }}
.mb-cal span:last-child {{ text-align: right; color: var(--muted); }}

/* ---------- news & note ---------- */
.mb-lead {{ font-size: 1.05rem; line-height: 1.65; color: var(--ink); margin: 0 0 0.9rem; max-width: 95ch; }}
.mb-story {{ background: var(--surface); border: 1px solid var(--line); border-radius: 10px; padding: 0.9rem 1.05rem 0.8rem; }}
.mb-story.top {{ border-left: 3px solid var(--accent); }}
.mb-story h3 {{ font-size: 1.02rem !important; line-height: 1.35; margin: 0 0 0.45rem; color: var(--ink); font-weight: 650; padding: 0; }}
.mb-story.top h3 {{ font-size: 1.2rem !important; }}
.mb-story p, .mb-story li {{ margin: 0 0 0.4rem; line-height: 1.55; font-size: 0.88rem; color: var(--body); }}
.mb-story p b {{ color: var(--ink); font-weight: 600; }}
.mb-story .watch {{ color: var(--muted); }}
.mb-sources {{ display: flex; gap: 0.35rem; flex-wrap: wrap; margin-top: 0.55rem; }}
.mb-src {{ font-size: 0.7rem; padding: 0.12rem 0.5rem; border: 1px solid var(--line); border-radius: 999px;
  color: var(--muted) !important; text-decoration: none !important; }}
.mb-src:hover {{ border-color: var(--accent); color: var(--accent) !important; }}
.mb-grid2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 0.7rem; margin-top: 0.7rem; align-items: start; }}
.mb-grid3 {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.7rem; margin-top: 0.7rem; align-items: start; }}
@media (max-width: 900px) {{ .mb-grid2, .mb-grid3 {{ grid-template-columns: 1fr; }} }}
.mb-note {{ color: var(--faint); font-size: 0.76rem; margin-top: 0.6rem; }}
.mb-skel {{ height: 0.85rem; border-radius: 5px; background: var(--soft); margin: 0.5rem 0; }}
.mb-news a.t {{ color: var(--ink) !important; text-decoration: none !important; font-weight: 550; font-size: 0.9rem; line-height: 1.4; }}
.mb-news a.t:hover {{ color: var(--accent) !important; }}
.mb-news > div {{ padding: 0.55rem 0; border-bottom: 1px solid var(--soft); }}
.mb-news > div:last-child {{ border-bottom: none; }}
.mb-news .m {{ color: var(--faint); font-size: 0.72rem; margin-top: 0.15rem; }}
.mb-news .s {{ color: var(--muted); font-size: 0.82rem; margin-top: 0.2rem; line-height: 1.45; }}

/* ---------- quote header ---------- */
.mb-quote {{ display: flex; justify-content: space-between; align-items: flex-end; gap: 1rem 2rem; flex-wrap: wrap; margin: 0.3rem 0 0.6rem; }}
.mb-quote .idt {{ display: flex; gap: 0.85rem; align-items: center; }}
.mb-quote .logo {{ width: 46px; height: 46px; border-radius: 10px; background: #FFF; border: 1px solid var(--line); object-fit: contain; padding: 5px; }}
.mb-quote .co {{ font-size: 1.55rem; font-weight: 700; color: var(--ink); line-height: 1.15; }}
.mb-quote .meta {{ color: var(--muted); font-size: 0.82rem; margin-top: 0.2rem; display: flex; gap: 0.45rem; flex-wrap: wrap; align-items: center; }}
.mb-quote .px {{ font-size: 2.1rem; font-weight: 700; color: var(--ink); line-height: 1; }}
.mb-quote .chg {{ font-size: 1.05rem; font-weight: 600; margin-left: 0.6rem; }}
.mb-quote .asof {{ color: var(--faint); font-size: 0.74rem; margin-top: 0.35rem; }}
.mb-tag {{ font-size: 0.74rem; font-weight: 600; padding: 0.08rem 0.45rem; border-radius: 5px; background: var(--flat-bg); color: var(--ink); }}
.mb-stats {{ background: var(--line); border: 1px solid var(--line); border-radius: 10px; display: grid; gap: 1px;
  grid-template-columns: repeat(var(--cols, 4), minmax(0, 1fr)); overflow: hidden; }}
.mb-stat {{ background: var(--surface); padding: 0.6rem 0.8rem; }}
.mb-stat .k {{ color: var(--muted); font-size: 0.74rem; }}
.mb-stat .v {{ font-size: 1.08rem; font-weight: 650; color: var(--ink); margin-top: 0.08rem; }}
.mb-stat .s {{ color: var(--faint); font-size: 0.68rem; margin-top: 0.06rem; }}
@media (max-width: 900px) {{ .mb-stats {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }} }}
.mb-callout {{ background: var(--surface); border: 1px solid var(--line); border-left: 3px solid var(--accent);
  border-radius: 8px; padding: 0.7rem 0.95rem; line-height: 1.55; color: var(--body); margin: 0.6rem 0; font-size: 0.88rem; }}
.mb-callout b {{ color: var(--ink); }}
.mb-verdict {{ background: var(--surface); border: 1px solid var(--line); border-radius: 10px; padding: 0.95rem 1.15rem;
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; margin: 0.5rem 0; }}
.mb-verdict .k {{ color: var(--muted); font-size: 0.78rem; }}
.mb-verdict .v {{ font-size: 1.7rem; font-weight: 700; color: var(--ink); line-height: 1.15; }}
.mb-verdict .label {{ font-size: 1.15rem; font-weight: 700; }}
@media (max-width: 760px) {{ .mb-verdict {{ grid-template-columns: 1fr; }} }}
.mb-prob {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 0.6rem; }}
.mb-prob > div {{ background: var(--surface); border: 1px solid var(--line); border-radius: 10px; padding: 0.7rem 0.85rem; }}
.mb-prob .v {{ font-size: 1.5rem; font-weight: 700; color: var(--ink); }}
.mb-prob .k {{ color: var(--muted); font-size: 0.78rem; line-height: 1.35; margin-top: 0.15rem; }}
.mb-prob .bar {{ height: 4px; background: var(--soft); border-radius: 4px; margin-top: 0.5rem; overflow: hidden; }}
.mb-prob .bar i {{ display: block; height: 100%; background: var(--accent); }}
@media (max-width: 900px) {{ .mb-prob {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }} }}

/* ---------- streamlit widgets ---------- */
[data-baseweb="tab-list"] {{ gap: 0.2rem; border-bottom: 1px solid var(--line); }}
[data-baseweb="tab"] {{ padding: 0.5rem 0.75rem !important; }}
[data-baseweb="tab"] p {{ font-size: 0.9rem; font-weight: 550; }}
[data-testid="stExpander"] details {{ background: var(--surface); border-radius: 10px; }}
[data-testid="stCaptionContainer"] {{ color: var(--faint); }}
[data-testid="stPlotlyChart"] {{ background: var(--surface); border: 1px solid var(--line); border-radius: 10px; padding: 0.3rem 0.3rem 0; }}
[class*="st-key-panel_"] [data-testid="stPlotlyChart"], [class*="st-key-bare_"] [data-testid="stPlotlyChart"] {{ border: none; padding: 0; }}
</style>
"""


def inject_css() -> None:
    st.html(_css(P()))


def esc(text) -> str:
    """Escape for HTML, including $ so nothing is ever read as math."""
    return html.escape(str(text or "")).replace("$", "&#36;")


def sgn(x: float, decimals: int = 2, suffix: str = "%") -> str:
    sign = "+" if x > 0 else "−" if x < 0 else ""
    return f"{sign}{abs(x):,.{decimals}f}{suffix}"


def chip(pct_value: float | None, suffix: str = "") -> str:
    """A signed change pill. `pct_value` is already in percent (1.2 = +1.2%)."""
    if pct_value is None:
        return '<span class="mb-chip flat">n/a</span>'
    cls = "up" if pct_value > 0.004 else "down" if pct_value < -0.004 else "flat"
    return f'<span class="mb-chip {cls}">{sgn(pct_value)}{esc(suffix)}</span>'


def signed_class(x: float | None) -> str:
    if x is None:
        return ""
    return "pos" if x > 0 else "neg" if x < 0 else ""


SOURCE_LABELS = {"mkt": "Market data", "rep": "Reported", "calc": "Calculated", "ai": "AI-written", "ana": "Analysts"}


def src(kind: str) -> str:
    """Provenance tag: market data, reported (SEC filings), calculated here, analysts, or AI-written."""
    return f'<span class="src {kind}">{SOURCE_LABELS[kind]}</span>'


def range_bar(low: float | None, high: float | None, value: float | None, fmt: str = "{:,.2f}",
              left: str = "", right: str = "") -> str:
    if not low or not high or value is None or high <= low:
        return ""
    pos = max(0.0, min(1.0, (value - low) / (high - low))) * 100
    return (f'<div class="mb-range"><div class="track"><div class="fill" style="width:{pos:.1f}%"></div>'
            f'<div class="mark" style="left:{pos:.1f}%"></div></div>'
            f'<div class="ends"><span>{esc(left)}{esc(fmt.format(low))}</span><span>{esc(right)}{esc(fmt.format(high))}</span></div></div>')


def spark_svg(values, up: bool | None = None, width: int = 160, height: int = 30) -> str:
    """Tiny trend line, as an <img> with an inline SVG (st.html strips raw <svg> tags)."""
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
           f'stroke-width="1.6" vector-effect="non-scaling-stroke" stroke-linejoin="round"/></svg>')
    return f'<img class="mb-spark" alt="" src="data:image/svg+xml;base64,{base64.b64encode(svg.encode()).decode()}">'


def link(params: dict) -> str:
    """Same-tab link to another view of the app, keeping the watchlist in the address."""
    keep = dict(params)
    w = st.query_params.get("w")
    if w and "w" not in keep:
        keep["w"] = w
    return "?" + "&".join(f"{k}={html.escape(str(v))}" for k, v in keep.items())
