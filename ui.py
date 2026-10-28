"""Visual layer: palettes (light and dark), global CSS and small HTML building blocks.

Design direction: a professional market terminal in the Yahoo Finance / Finviz family.
- Dense, scannable data; one sans family (Inter) with tabular figures everywhere.
- A navy (light) or graphite (dark) masthead, prices in JetBrains Mono, and a moving ticker tape frame every page; content sits on calm surfaces.
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
        "mast": "#0B1526", "mast2": "#13213A", "mast_line": "#1E2C47", "tape": "#0F1D33",
    },
    "dark": {
        "paper": "#0B0C0F", "surface": "#15171C", "raised": "#1A1D23", "ink": "#F2F4F7", "body": "#C9CED6",
        "muted": "#9AA1AD", "faint": "#6F7682", "line": "#262A32", "soft": "#1E2128", "accent": "#6E9BFF",
        "up": "#4ADE80", "down": "#F87171", "up_bg": "rgba(74,222,128,0.13)", "down_bg": "rgba(248,113,113,0.14)",
        "flat_bg": "#22262E", "calc": "#B9ADFF", "calc_bg": "rgba(185,173,255,0.13)", "ai": "#F4C152",
        "ai_bg": "rgba(244,193,82,0.13)", "rep": "#93B4FF", "rep_bg": "rgba(110,155,255,0.14)",
        "grid": "rgba(242,244,247,0.06)", "fill": "rgba(110,155,255,0.14)", "orange": "#F59E57",
        "violet": "#A78BFA", "teal": "#3CC8D2", "chart_bg": "#15171C",
        "mast": "#0E1014", "mast2": "#1A1D23", "mast_line": "#22252C", "tape": "#111317",
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
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@500;600;700&display=swap');
:root {{
  --paper:{p['paper']}; --surface:{p['surface']}; --raised:{p['raised']}; --ink:{p['ink']}; --body:{p['body']};
  --muted:{p['muted']}; --faint:{p['faint']}; --line:{p['line']}; --soft:{p['soft']}; --accent:{p['accent']};
  --up:{p['up']}; --down:{p['down']}; --up-bg:{p['up_bg']}; --down-bg:{p['down_bg']}; --flat-bg:{p['flat_bg']};
  --calc:{p['calc']}; --calc-bg:{p['calc_bg']}; --ai:{p['ai']}; --ai-bg:{p['ai_bg']}; --rep:{p['rep']}; --rep-bg:{p['rep_bg']};
  --navy:{p['mast']}; --navy2:{p['mast2']}; --mast-line:{p['mast_line']}; --tape:{p['tape']};
  --mono: 'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, monospace;
}}
html, body, [class*="css"], .stApp {{ font-family: 'Inter', system-ui, sans-serif; }}
.stApp {{ font-feature-settings: "tnum" 1, "cv11" 1; }}
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"], [data-testid="collapsedControl"] {{ display: none !important; }}
[data-testid="stHeader"] {{ background: transparent; height: 0; }}
[data-testid="stToolbar"] {{ top: 6px; right: 8px; }}
/* Streamlit's header/toolbar is a full-width transparent layer above the page: let clicks pass through it
   (only its own buttons stay clickable), otherwise it blocks the top bar menu. */
[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stToolbar"] > div {{ pointer-events: none !important; }}
[data-testid="stToolbar"] button, [data-testid="stToolbar"] a, [data-testid="stToolbarActions"],
[data-testid="stToolbarActions"] *, [data-testid="stMainMenu"], [data-testid="stMainMenu"] * {{ pointer-events: auto !important; }}
[data-testid="stMainBlockContainer"] {{ max-width: 1400px; padding: 0 1.4rem 3rem; }}
.num {{ font-variant-numeric: tabular-nums; }}
a {{ color: var(--accent); }}
.pos {{ color: var(--up) !important; }} .neg {{ color: var(--down) !important; }}
h1, h2, h3, h4 {{ font-family: 'Inter', system-ui, sans-serif !important; letter-spacing: -0.01em; }}

/* ---------- masthead (top bar) ---------- */
.st-key-topbar {{ background: var(--navy); margin: 0 -1.4rem; padding: 0.55rem 1.4rem 0.5rem; width: calc(100% + 2.8rem) !important; max-width: none !important;
  border-bottom: 1px solid var(--mast-line); gap: 0.4rem; }}
.st-key-topbar p, .st-key-topbar label {{ color: #DCE5F2; }}
/* Streamlit Cloud draws its own toolbar (Share / Fork / GitHub / menu) in the top-right corner:
   keep that corner free so it never sits on top of the search box. */
@media (min-width: 641px) {{ .st-key-topbar {{ padding-right: calc(1.4rem + 200px) !important; }} }}
@media (max-width: 1500px) {{ .mb-logo small {{ display: none !important; }} .mb-logo {{ font-size: 1rem !important; }} }}
@media (max-width: 640px) {{ .st-key-topbar {{ padding-top: 2.6rem !important; }} }}
.mb-logo {{ display: flex; align-items: center; gap: 0.55rem; color: #FFF; font-weight: 700; font-size: 1.12rem;
  letter-spacing: -0.02em; white-space: nowrap; }}
.mb-logo .mark {{ width: 26px; height: 26px; border-radius: 7px; background: linear-gradient(135deg,#3B7BFF,#16C784);
  display: inline-flex; align-items: center; justify-content: center; color: #FFF; font-size: 0.8rem; font-weight: 800; }}
.mb-logo small {{ display: block; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 11rem; color: #8FA3C2; font-weight: 500; font-size: 0.7rem; letter-spacing: 0; }}
.st-key-topbar [data-testid="stButtonGroup"] button {{ background: transparent; border: none; color: #C9D6EA;
  font-weight: 500; padding: 0.3rem 0.45rem; min-height: 2.1rem; font-size: 0.88rem; }}
.st-key-topbar [data-testid="stButtonGroup"] button p {{ font-size: 0.88rem; }}
.st-key-topbar [data-testid="stButtonGroup"] button:hover {{ background: var(--navy2); color: #FFF; }}
.st-key-topbar [data-testid="stButtonGroup"] button[aria-checked="true"],
.st-key-topbar [data-testid="stButtonGroup"] button[kind="segmented_controlActive"] {{ background: var(--navy2); color: #FFF; box-shadow: inset 0 -2px 0 var(--accent); }}
.st-key-topbar input {{ background: var(--navy2) !important; color: #FFF !important; border-color: var(--mast-line) !important; }}
.st-key-topbar input::placeholder {{ color: #7F93B3 !important; }}
.st-key-topbar [data-baseweb="select"] > div {{ background: var(--navy2); border-color: var(--mast-line); color: #FFF; }}

/* ---------- ticker tape ---------- */
.mb-tape {{ margin: 0 -1.4rem 1rem; background: var(--tape); border-bottom: 1px solid var(--mast-line); overflow: hidden;
  white-space: nowrap; position: relative; }}
.mb-tape .track {{ display: inline-flex; animation: mbscroll 70s linear infinite; padding: 0.42rem 0; }}
.mb-tape:hover .track {{ animation-play-state: paused; }}
.mb-tape a {{ display: inline-flex; gap: 0.45rem; align-items: baseline; padding: 0 1.15rem; border-right: 1px solid var(--mast-line);
  color: #DCE5F2 !important; text-decoration: none !important; font-size: 0.82rem; }}
.mb-tape a b {{ color: #FFF; font-weight: 600; }}
.mb-tape a span {{ font-family: var(--mono); font-size: 0.78rem; }}
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
.mb-card {{ background: var(--surface); border: 1px solid var(--line); border-radius: 14px; padding: 0.95rem 1.05rem 0.85rem;
  text-decoration: none !important; display: block; color: inherit !important; transition: border-color .15s, transform .15s; }}
a.mb-card:hover {{ border-color: var(--faint); transform: translateY(-1px); }}
.mb-card .hd {{ display: flex; justify-content: space-between; align-items: baseline; gap: 0.5rem; }}
.mb-card .n {{ color: var(--ink); font-size: 0.92rem; font-weight: 650; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.mb-card .via {{ color: var(--faint); font-family: var(--mono); font-size: 0.7rem; letter-spacing: 0.08em; white-space: nowrap; }}
.mb-card .p {{ color: var(--ink); font-family: var(--mono); font-size: 1.55rem; font-weight: 700; margin-top: 0.45rem;
  letter-spacing: -0.02em; white-space: nowrap; line-height: 1.15; }}
.mb-card .c {{ display: flex; align-items: center; gap: 0.45rem; margin-top: 0.4rem; white-space: nowrap; }}
.mb-card .c .abs {{ font-family: var(--mono); font-size: 0.74rem; color: var(--muted); }}
.mb-card .a {{ color: var(--faint); font-size: 0.74rem; margin-top: 0.7rem; }}
.mb-pill {{ font-family: var(--mono); font-size: 0.8rem; font-weight: 600; padding: 0.18rem 0.5rem; border-radius: 6px; }}
.mb-pill.up {{ color: var(--up); background: var(--up-bg); }} .mb-pill.down {{ color: var(--down); background: var(--down-bg); }}
.mb-pill.flat {{ color: var(--muted); background: var(--flat-bg); }}
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
.mb-range .lbl {{ color: var(--faint); font-size: 0.66rem; font-weight: 500; letter-spacing: 0.09em; text-transform: uppercase; margin: 0.75rem 0 0.4rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
@media (max-width: 640px) {{ .mb-card .via {{ display: none; }} .mb-range .lbl {{ letter-spacing: 0.04em; }} }}
.mb-range .track {{ position: relative; height: 5px; border-radius: 5px;
  background: linear-gradient(90deg, color-mix(in srgb, var(--down) 75%, transparent), color-mix(in srgb, #E0B341 70%, transparent) 50%, color-mix(in srgb, var(--up) 75%, transparent)); }}
.mb-range .mark {{ position: absolute; top: -4px; width: 3px; height: 13px; border-radius: 2px; background: var(--ink);
  transform: translateX(-1.5px); box-shadow: 0 0 0 2px var(--surface); }}
.mb-range .ends {{ display: flex; justify-content: space-between; color: var(--muted); font-family: var(--mono); font-size: 0.7rem; margin-top: 0.4rem; gap: 0.4rem; }}
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
.mb-cell .px {{ font-family: var(--mono); letter-spacing: -0.02em; font-size: 1.15rem; font-weight: 650; color: var(--ink); white-space: nowrap; }}
.mb-cell .asof {{ color: var(--faint); font-size: 0.68rem; margin-top: 0.3rem; }}
@media (max-width: 640px) {{ .mb-board {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }} }}

/* ---------- watch rail ---------- */
.mb-wrow {{ display: grid; grid-template-columns: 1fr 5.5rem auto; gap: 0.6rem; align-items: center; padding: 0.5rem 0;
  border-bottom: 1px solid var(--soft); text-decoration: none !important; color: inherit !important; }}
.mb-wrow:last-child {{ border-bottom: none; }}
.mb-wrow:hover .tk {{ color: var(--accent); }}
.mb-wrow .tk {{ font-weight: 650; color: var(--ink); font-size: 0.9rem; }}
.mb-wrow .co {{ color: var(--muted); font-size: 0.74rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 9rem; }}
.mb-wrow .px {{ font-family: var(--mono); text-align: right; font-weight: 600; color: var(--ink); font-size: 0.88rem; }}
.mb-cal div {{ display: grid; grid-template-columns: 4rem 1fr; gap: 0.5rem; padding: 0.4rem 0; border-bottom: 1px solid var(--soft); font-size: 0.82rem; color: var(--body); }}
.mb-cal div:last-child {{ border-bottom: none; }}
.mb-cal span:last-child {{ text-align: right; color: var(--muted); }}

/* ---------- analysts & AI take ---------- */
.mb-take {{ height: 100%; }}
.mb-kicker {{ color: var(--faint); font-size: 0.68rem; font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase; margin-bottom: 0.15rem; }}
.mb-take-row {{ display: flex; align-items: center; gap: 1rem; margin: 0.4rem 0 0.8rem; flex-wrap: wrap; }}
.mb-lean {{ font-family: var(--mono); font-weight: 700; border-radius: 8px; padding: 0.25rem 0.7rem; font-size: 0.95rem; letter-spacing: 0.02em; }}
.mb-lean.big {{ font-size: 1.45rem; padding: 0.4rem 0.95rem; }}
.mb-lean.up {{ color: var(--up); background: var(--up-bg); }} .mb-lean.down {{ color: var(--down); background: var(--down-bg); }}
.mb-lean.hold {{ color: var(--ai); background: var(--ai-bg); }} .mb-lean.flat {{ color: var(--muted); background: var(--flat-bg); }}
.mb-score {{ font-family: var(--mono); font-size: 1.35rem; font-weight: 700; color: var(--ink); }}
.mb-score small {{ font-size: 0.8rem; color: var(--faint); font-weight: 500; }}
.mb-stack {{ display: flex; height: 10px; border-radius: 6px; overflow: hidden; gap: 2px; background: var(--soft); }}
.mb-stack i {{ display: block; height: 100%; }}
.mb-legend {{ display: flex; flex-wrap: wrap; gap: 0.35rem 0.8rem; margin-top: 0.55rem; color: var(--muted); font-size: 0.76rem; }}
.mb-legend b {{ display: inline-block; width: 8px; height: 8px; border-radius: 2px; margin-right: 0.3rem; vertical-align: 0; }}
.mb-p {{ color: var(--body); font-size: 0.88rem; line-height: 1.55; margin: 0 0 0.5rem; }}
.mb-p b {{ color: var(--ink); }}
.mb-chip {{ display: inline-block; margin-bottom: 0.25rem; }}

/* ---------- news desk ---------- */
.mb-sub {{ color: var(--muted); font-size: 0.72rem; font-weight: 600; letter-spacing: 0.09em; text-transform: uppercase;
  margin: 0.9rem 0 0.4rem; display: flex; gap: 0.5rem; align-items: center; }}
.mb-sub:first-child {{ margin-top: 0; }}
.mb-tagx {{ display: inline-block; font-size: 0.66rem; color: var(--muted); background: var(--flat-bg); border-radius: 4px;
  padding: 0.02rem 0.35rem; margin-left: 0.3rem; }}
.mb-ul {{ margin: 0 0 0.5rem 1.1rem; padding: 0; }}
.mb-ul li {{ color: var(--body); font-size: 0.86rem; line-height: 1.5; margin-bottom: 0.25rem; }}
.mb-tones {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(128px, 1fr)); gap: 0.5rem; margin-bottom: 0.6rem; }}
.mb-tone {{ background: var(--surface); border: 1px solid var(--line); border-left: 4px solid var(--faint); border-radius: 8px; padding: 0.5rem 0.7rem; }}
.mb-tone b {{ display: block; color: var(--ink); font-size: 0.84rem; font-weight: 650; }}
.mb-tone span {{ color: var(--muted); font-size: 0.72rem; }}
.mb-tone.up {{ border-left-color: var(--up); }} .mb-tone.down {{ border-left-color: var(--down); }} .mb-tone.hold {{ border-left-color: var(--ai); }}

/* ---------- research ---------- */
.st-key-panel_rs_body h2, .st-key-panel_rs_preview h2 {{ font-size: 1.08rem !important; font-weight: 700; margin: 1rem 0 0.3rem !important; padding: 0 !important; }}
.st-key-panel_rs_body h3, .st-key-panel_rs_preview h3 {{ font-size: 0.98rem !important; }}
.st-key-panel_rs_body p, .st-key-panel_rs_body li {{ font-size: 0.92rem; line-height: 1.6; }}

/* ---------- portfolio ---------- */
.mb-tbl tr.hl td {{ background: var(--raised); }}
.mb-check {{ display: flex; gap: 0.8rem; align-items: flex-start; padding: 0.55rem 0; border-bottom: 1px solid var(--soft); }}
.mb-check:last-child {{ border-bottom: none; }}
.mb-check .mb-lean {{ flex: none; font-size: 0.78rem; }}
.mb-check .mb-p {{ margin: 0.1rem 0 0; }}
.mb-story h3 .mb-lean {{ font-size: 0.74rem; padding: 0.12rem 0.45rem; margin-left: 0.35rem; vertical-align: 2px; }}

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
.mb-quote .px {{ font-family: var(--mono); letter-spacing: -0.03em; font-size: 2.1rem; font-weight: 700; color: var(--ink); line-height: 1; }}
.mb-quote .chg {{ font-size: 1.05rem; font-weight: 600; margin-left: 0.6rem; }}
.mb-quote .asof {{ color: var(--faint); font-size: 0.74rem; margin-top: 0.35rem; }}
.mb-tag {{ font-size: 0.74rem; font-weight: 600; padding: 0.08rem 0.45rem; border-radius: 5px; background: var(--flat-bg); color: var(--ink); }}
.mb-stats {{ background: var(--line); border: 1px solid var(--line); border-radius: 10px; display: grid; gap: 1px;
  grid-template-columns: repeat(var(--cols, 4), minmax(0, 1fr)); overflow: hidden; }}
.mb-stat {{ background: var(--surface); padding: 0.6rem 0.8rem; }}
.mb-stat .k {{ color: var(--muted); font-size: 0.74rem; }}
.mb-stat .v {{ font-family: var(--mono); letter-spacing: -0.02em; font-size: 1.05rem; font-weight: 650; color: var(--ink); margin-top: 0.08rem; }}
.mb-stat .s {{ color: var(--faint); font-size: 0.68rem; margin-top: 0.06rem; }}
@media (max-width: 900px) {{ .mb-stats {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }} }}
.mb-callout {{ background: var(--surface); border: 1px solid var(--line); border-left: 3px solid var(--accent);
  border-radius: 8px; padding: 0.7rem 0.95rem; line-height: 1.55; color: var(--body); margin: 0.6rem 0; font-size: 0.88rem; }}
.mb-callout b {{ color: var(--ink); }}
.mb-verdict {{ background: var(--surface); border: 1px solid var(--line); border-radius: 10px; padding: 0.95rem 1.15rem;
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; margin: 0.5rem 0; }}
.mb-verdict .k {{ color: var(--muted); font-size: 0.78rem; }}
.mb-verdict .v {{ font-family: var(--mono); letter-spacing: -0.03em; font-size: 1.7rem; font-weight: 700; color: var(--ink); line-height: 1.15; }}
.mb-verdict .label {{ font-size: 1.15rem; font-weight: 700; }}
@media (max-width: 760px) {{ .mb-verdict {{ grid-template-columns: 1fr; }} }}
.mb-prob {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 0.6rem; }}
.mb-prob > div {{ background: var(--surface); border: 1px solid var(--line); border-radius: 10px; padding: 0.7rem 0.85rem; }}
.mb-prob .v {{ font-family: var(--mono); letter-spacing: -0.02em; font-size: 1.5rem; font-weight: 700; color: var(--ink); }}
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
SOURCE_LABELS_ES = {"mkt": "Datos de mercado", "rep": "Reportado", "calc": "Calculado", "ai": "Escrito por IA", "ana": "Analistas"}


def src(kind: str) -> str:
    """Provenance tag: market data, reported (SEC filings), calculated here, analysts, or AI-written."""
    labels = SOURCE_LABELS_ES if st.session_state.get("lang_sel") == "ES" else SOURCE_LABELS
    return f'<span class="src {kind}">{labels[kind]}</span>'


def range_bar(low: float | None, high: float | None, value: float | None, fmt: str = "{:,.2f}",
              left: str = "", right: str = "", label: str = "") -> str:
    if not low or not high or value is None or high <= low:
        return ""
    pos = max(0.0, min(1.0, (value - low) / (high - low))) * 100
    head = f'<div class="lbl">{esc(label)}</div>' if label else ""
    return (f'<div class="mb-range">{head}<div class="track"><div class="mark" style="left:{pos:.1f}%"></div></div>'
            f'<div class="ends"><span>{esc(left)}{esc(fmt.format(low))}</span><span>{esc(right)}{esc(fmt.format(high))}</span></div></div>')


def pill(pct_value: float | None) -> str:
    if pct_value is None:
        return '<span class="mb-pill flat">n/a</span>'
    cls = "up" if pct_value > 0 else "down" if pct_value < 0 else "flat"
    return f'<span class="mb-pill {cls}">{sgn(pct_value)}</span>'


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
    if st.session_state.get("lang_sel") == "ES":
        keep["lang"] = "es"
    return "?" + "&".join(f"{k}={html.escape(str(v))}" for k, v in keep.items())
