"""Visual layer: global CSS and small HTML building blocks.

Design notes
- Ink on cool paper for reading, a navy sidebar as the fixed "desk".
- Newsreader (serif) for headlines and the daily note, IBM Plex Sans for data and UI,
  tabular figures everywhere numbers sit in columns.
- Green/red are reserved for price direction and always paired with a sign (+/−).
"""
from __future__ import annotations

import html

import streamlit as st

INK = "#13202F"
MUTED = "#5B6878"
LINE = "#DCE2EA"
SURFACE = "#FFFFFF"
ACCENT = "#2457D6"
UP = "#0E8A3E"
DOWN = "#C8362F"

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=Newsreader:opsz,wght@6..72,400;6..72,500;6..72,600&display=swap');

:root {{
  --ink: {INK}; --muted: {MUTED}; --line: {LINE}; --surface: {SURFACE};
  --accent: {ACCENT}; --up: {UP}; --down: {DOWN};
  --up-bg: #E3F4E9; --down-bg: #FBE7E5; --flat-bg: #EEF1F5;
  --serif: 'Newsreader', Georgia, serif;
  --sans: 'IBM Plex Sans', system-ui, sans-serif;
}}

[data-testid="stHeader"] {{ background: transparent; }}
[data-testid="stMainBlockContainer"] {{ max-width: 1180px; padding-top: 2.2rem; }}
.mb-num, [data-testid="stMetricValue"], .mb-board, .mb-stats, table {{ font-variant-numeric: tabular-nums; }}

/* ---------- sidebar ---------- */
[data-testid="stSidebar"] .mb-brand {{ font-family: var(--serif); font-size: 1.55rem; font-weight: 600;
  color: #FFFFFF; letter-spacing: -0.01em; margin: 0 0 0.1rem; }}
[data-testid="stSidebar"] .mb-brand-sub {{ color: #9FB0C6; font-size: 0.82rem; margin-bottom: 0.4rem; }}
[data-testid="stSidebar"] [role="radiogroup"] {{ gap: 2px; }}
[data-testid="stSidebar"] [role="radiogroup"] label {{ padding: 0.45rem 0.7rem; border-radius: 8px; width: 100%;
  margin: 0; transition: background-color .15s ease; }}
[data-testid="stSidebar"] [role="radiogroup"] label:hover {{ background: #1A2B42; }}
[data-testid="stSidebar"] [data-testid="stRadioOption"][data-selected="true"] {{ background: #22385A; }}
[data-testid="stSidebar"] [data-testid="stRadioOption"] > div > div:not([data-testid="stMarkdownContainer"]) {{ display: none; }}
[data-testid="stSidebar"] [role="radiogroup"] label p {{ font-size: 0.97rem; font-weight: 500; color: #E6ECF3; }}
[data-testid="stSidebar"] .mb-side-h {{ color: #9FB0C6; font-size: 0.82rem; font-weight: 500; margin: 0.2rem 0 0.4rem; }}
[data-testid="stSidebar"] [class*="st-key-open_"] button > div {{ justify-content: flex-start; width: 100%; }}
[data-testid="stSidebar"] [class*="st-key-open_"] button {{ background: transparent; border: none; color: #E6ECF3; width: 100%;
  justify-content: flex-start; padding: 0.25rem 0.55rem; min-height: 2rem; font-weight: 600; letter-spacing: 0.02em; }}
[data-testid="stSidebar"] [class*="st-key-open_"] button:hover {{ background: #1A2B42; color: #FFFFFF; }}
[data-testid="stSidebar"] [class*="st-key-rm_"] button {{ background: transparent; border: none; color: #7C8DA4;
  min-height: 2rem; padding: 0 0.4rem; }}
[data-testid="stSidebar"] [class*="st-key-rm_"] button:hover {{ color: #FFB4AC; background: transparent; }}

/* ---------- masthead ---------- */
.mb-date {{ font-family: var(--serif); font-size: clamp(2.2rem, 4.2vw, 3.3rem); font-weight: 600; line-height: 1.05;
  letter-spacing: -0.02em; color: var(--ink); margin: 0; }}
.mb-dek {{ color: var(--muted); font-size: 1rem; margin: 0.5rem 0 1.4rem; display: flex; align-items: center;
  gap: 0.6rem; flex-wrap: wrap; }}
.mb-dot {{ width: 9px; height: 9px; border-radius: 50%; display: inline-block; }}
.mb-dot.open {{ background: var(--up); box-shadow: 0 0 0 4px var(--up-bg); }}
.mb-dot.closed {{ background: #8A97A8; box-shadow: 0 0 0 4px var(--flat-bg); }}

/* ---------- market board ---------- */
.mb-board {{ background: var(--line); border: 1px solid var(--line); border-radius: 14px; gap: 1px;
  display: grid; grid-template-columns: repeat(var(--cols, 3), minmax(0, 1fr)); overflow: hidden; }}
.mb-cell {{ background: var(--surface); padding: 0.95rem 1.15rem 0.85rem; }}
.mb-board-h {{ color: var(--ink); font-weight: 600; font-size: 0.95rem; margin: 1.3rem 0 0.5rem; }}
.mb-cell .name {{ color: var(--muted); font-size: 0.86rem; }}
.mb-cell .row {{ display: flex; align-items: center; justify-content: space-between; gap: 0.6rem; margin-top: 0.15rem; }}
.mb-cell .px {{ font-size: 1.45rem; font-weight: 600; color: var(--ink); }}
.mb-cell .asof {{ color: #8A97A8; font-size: 0.74rem; margin-top: 0.2rem; }}
.mb-chip {{ font-size: 0.82rem; font-weight: 600; padding: 0.12rem 0.5rem; border-radius: 999px; white-space: nowrap; }}
.mb-chip.up {{ color: var(--up); background: var(--up-bg); }}
.mb-chip.down {{ color: var(--down); background: var(--down-bg); }}
.mb-chip.flat {{ color: var(--muted); background: var(--flat-bg); }}
.mb-foot {{ color: #8A97A8; font-size: 0.78rem; margin: 0.5rem 0 0; }}
@media (max-width: 760px) {{ .mb-board {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
  .mb-cell {{ padding: 0.8rem 0.85rem; }} .mb-cell .row {{ flex-wrap: wrap; }} .mb-cell .px {{ font-size: 1.2rem; }} }}

/* ---------- daily note ---------- */
.mb-section {{ font-family: var(--serif); font-size: 1.6rem; font-weight: 600; color: var(--ink);
  margin: 2.2rem 0 0.8rem; letter-spacing: -0.01em; }}
.mb-lead {{ font-family: var(--serif); font-size: 1.32rem; line-height: 1.6; color: var(--ink);
  max-width: 68ch; margin: 0 0 1.4rem; }}
.mb-story {{ background: var(--surface); border: 1px solid var(--line); border-radius: 12px; padding: 1.15rem 1.3rem 1rem;
  height: 100%; }}
.mb-story.top {{ border-left: 4px solid var(--accent); padding-left: 1.4rem; }}
.mb-story h3 {{ font-family: var(--serif); font-size: 1.28rem; line-height: 1.3; margin: 0 0 0.6rem; color: var(--ink);
  font-weight: 600; padding: 0; }}
.mb-story.top h3 {{ font-size: 1.6rem; }}
.mb-story p {{ margin: 0 0 0.45rem; line-height: 1.55; font-size: 0.96rem; color: #263445; }}
.mb-story p b {{ color: var(--ink); font-weight: 600; }}
.mb-story .watch {{ color: var(--muted); }}
.mb-sources {{ display: flex; gap: 0.4rem; flex-wrap: wrap; margin-top: 0.7rem; }}
.mb-src {{ font-size: 0.78rem; padding: 0.15rem 0.55rem; border: 1px solid var(--line); border-radius: 999px;
  color: var(--muted) !important; text-decoration: none !important; }}
.mb-src:hover {{ border-color: var(--accent); color: var(--accent) !important; }}
.mb-grid2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 0.9rem; margin-top: 0.9rem; }}
@media (max-width: 760px) {{ .mb-grid2 {{ grid-template-columns: 1fr; }} }}
.mb-note {{ color: #8A97A8; font-size: 0.8rem; margin-top: 0.8rem; }}

/* ---------- headline list ---------- */
.mb-list {{ background: var(--surface); border: 1px solid var(--line); border-radius: 12px; padding: 0.2rem 1.2rem; }}
.mb-item {{ display: grid; grid-template-columns: 1fr auto; gap: 1rem; padding: 0.7rem 0; border-bottom: 1px solid #EDF0F4; }}
.mb-item:last-child {{ border-bottom: none; }}
.mb-item a {{ color: var(--ink) !important; text-decoration: none !important; font-weight: 500; line-height: 1.4; }}
.mb-item a:hover {{ color: var(--accent) !important; }}
.mb-item .meta {{ color: #8A97A8; font-size: 0.8rem; white-space: nowrap; text-align: right; }}
.mb-item .sum {{ color: var(--muted); font-size: 0.88rem; margin-top: 0.2rem; line-height: 1.45; }}

/* ---------- watchlist rows ---------- */
[class*="st-key-wl_"] {{ background: var(--surface); border: 1px solid var(--line); border-radius: 12px;
  padding: 0.6rem 1rem 0.4rem; }}
.mb-tk {{ font-weight: 600; font-size: 1.05rem; color: var(--ink); letter-spacing: 0.01em; }}
.mb-co {{ color: var(--ink); font-size: 0.92rem; }}
.mb-sub {{ color: #8A97A8; font-size: 0.8rem; }}
.mb-price {{ font-size: 1.35rem; font-weight: 600; color: var(--ink); }}
.mb-mini {{ display: flex; gap: 1rem; color: var(--muted); font-size: 0.8rem; }}
.mb-mini b {{ font-weight: 600; }}
.pos {{ color: var(--up); }} .neg {{ color: var(--down); }}

/* ---------- stock header & stats ---------- */
.mb-stock {{ display: flex; justify-content: space-between; align-items: flex-end; gap: 1.5rem; flex-wrap: wrap;
  margin: 0.3rem 0 1rem; }}
.mb-stock .co {{ font-family: var(--serif); font-size: clamp(2rem, 3.6vw, 2.8rem); font-weight: 600; line-height: 1.05;
  letter-spacing: -0.02em; color: var(--ink); }}
.mb-stock .meta {{ color: var(--muted); margin-top: 0.4rem; display: flex; gap: 0.5rem; align-items: center; }}
.mb-tag {{ font-size: 0.8rem; font-weight: 600; padding: 0.1rem 0.5rem; border-radius: 6px; background: #E8ECF2; color: var(--ink); }}
.mb-stock .quote {{ text-align: right; }}
.mb-stock .big {{ font-size: 2.2rem; font-weight: 600; color: var(--ink); line-height: 1; }}
.mb-stock .asof {{ color: #8A97A8; font-size: 0.78rem; margin-top: 0.45rem; }}
.mb-stats {{ background: var(--surface); border: 1px solid var(--line); border-radius: 12px; display: grid;
  grid-template-columns: repeat(4, 1fr); overflow: hidden; margin: 0.6rem 0 0.4rem; }}
.mb-stat {{ padding: 0.8rem 1rem; border-right: 1px solid #EDF0F4; border-bottom: 1px solid #EDF0F4; }}
.mb-stat:nth-child(4n) {{ border-right: none; }}
.mb-stat .k {{ color: var(--muted); font-size: 0.82rem; }}
.mb-stat .v {{ font-size: 1.3rem; font-weight: 600; color: var(--ink); margin-top: 0.1rem; }}
.mb-stat .v.pos {{ color: var(--up); }} .mb-stat .v.neg {{ color: var(--down); }}
@media (max-width: 760px) {{ .mb-stats {{ grid-template-columns: repeat(2, 1fr); }} }}

.mb-callout {{ background: var(--surface); border: 1px solid var(--line); border-left: 4px solid var(--accent);
  border-radius: 10px; padding: 0.9rem 1.1rem; line-height: 1.55; color: #263445; margin: 0.8rem 0; }}
.mb-callout b {{ color: var(--ink); }}

/* ---------- valuation verdict ---------- */
.mb-verdict {{ background: var(--surface); border: 1px solid var(--line); border-radius: 14px; padding: 1.2rem 1.4rem;
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; margin: 0.6rem 0 0.4rem; }}
.mb-verdict .k {{ color: var(--muted); font-size: 0.85rem; }}
.mb-verdict .v {{ font-size: 2rem; font-weight: 600; color: var(--ink); line-height: 1.15; }}
.mb-verdict .label {{ font-family: var(--serif); font-size: 1.35rem; font-weight: 600; }}
@media (max-width: 760px) {{ .mb-verdict {{ grid-template-columns: 1fr; }} }}

/* ---------- streamlit widgets ---------- */
[data-baseweb="tab-list"] {{ gap: 1.4rem; border-bottom: 1px solid var(--line); }}
[data-baseweb="tab"] p {{ font-size: 1rem; font-weight: 500; }}
[data-testid="stExpander"] details {{ background: var(--surface); border-radius: 12px; }}
[data-testid="stCaptionContainer"] {{ color: #8A97A8; }}
</style>
"""


def inject_css() -> None:
    st.html(CSS)


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
