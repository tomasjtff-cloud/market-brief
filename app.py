"""Market Brief: a personal markets dashboard.

Run locally with:  streamlit run app.py
"""
from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

import ai
import analysis
import data
import fundamentals
from ui import P, chip, esc, inject_css, range_bar, signed_class, spark_svg, src

st.set_page_config(page_title="Market Brief", page_icon="📈", layout="wide")
inject_css()

DEFAULT_WATCHLIST = ["AAPL", "NVDA", "MSFT", "GOOGL", "TSLA"]
MAX_WATCHLIST = 5
BENCHMARK = "SPY"
PAGES = ["Today", "Watchlist", "Stock analysis", "Methodology"]
CLOCKS = [("New York", "America/New_York"), ("Mexico City", "America/Mexico_City"),
          ("Buenos Aires", "America/Argentina/Buenos_Aires")]


# =========================================================================== formatting
def money(x, decimals: int = 2) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "n/a"
    sign, a = ("−" if x < 0 else ""), abs(x)
    for div, suffix in ((1e12, "T"), (1e9, "B"), (1e6, "M")):
        if a >= div:
            return f"{sign}${a / div:,.{decimals}f}{suffix}"
    return f"{sign}${a:,.{decimals}f}"


def pct(x, decimals: int = 1, signed: bool = True) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "n/a"
    if not signed:
        return f"{x * 100:.{decimals}f}%"
    sign = "+" if x > 0 else "−" if x < 0 else ""
    return f"{sign}{abs(x) * 100:.{decimals}f}%"


def num(x, decimals: int = 2) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "n/a"
    return f"{x:,.{decimals}f}"


def when(t: dt.datetime | None) -> str:
    return f"{t:%b %d, %-I:%M %p} ET" if t else ""


def style_fig(fig: go.Figure, height: int = 360) -> go.Figure:
    p = P()
    fig.update_layout(
        height=height,
        margin=dict(l=4, r=4, t=36, b=4),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(color=p["muted"])),
        font=dict(family="IBM Plex Sans, system-ui, sans-serif", size=13, color=p["ink"]),
        hoverlabel=dict(bgcolor=p["surface"], bordercolor=p["line"], font=dict(color=p["ink"])),
    )
    fig.update_xaxes(showgrid=False, linecolor=p["line"], tickfont=dict(color=p["muted"]))
    fig.update_yaxes(gridcolor=p["grid"], zeroline=False, tickfont=dict(color=p["muted"]))
    return fig


# =========================================================================== watchlist state
def get_watchlist() -> list[str]:
    raw = st.query_params.get("w")
    if raw:
        wl = list(dict.fromkeys(t.strip().upper() for t in raw.split(",") if t.strip()))[:MAX_WATCHLIST]
        if wl:
            return wl
    return DEFAULT_WATCHLIST.copy()


def save_watchlist(wl: list[str]) -> None:
    st.query_params["w"] = ",".join(wl)


def open_stock(ticker: str) -> None:
    st.session_state.ticker = ticker
    st.session_state.page = "Stock analysis"


def remove_stock(ticker: str) -> None:
    wl = [t for t in get_watchlist() if t != ticker]
    if wl:
        save_watchlist(wl)


def add_stock(ticker: str, box: str = "search_box") -> None:
    wl = get_watchlist()
    if ticker not in wl and len(wl) < MAX_WATCHLIST:
        save_watchlist(wl + [ticker])
    st.session_state[box] = ""


def analyze_any(ticker: str) -> None:
    st.session_state.ticker = ticker
    st.session_state.any_box = ""


def symbol_search(box_key: str, placeholder: str) -> dict | None:
    q = st.text_input("Search", key=box_key, placeholder=placeholder, label_visibility="collapsed")
    if not q.strip():
        return None
    try:
        results = data.search_symbols(q.strip())
    except Exception as exc:
        st.caption(f"Search isn't available right now: {exc}")
        return None
    if not results:
        st.caption("No US-listed stock matches that search.")
        return None
    return st.selectbox("Results", results, key=f"{box_key}_pick", label_visibility="collapsed",
                        format_func=lambda r: f"{r['symbol']}  {r['description']}")


def render_sidebar(wl: list[str]) -> None:
    with st.sidebar:
        st.html('<div class="mb-brand">Market Brief</div>'
                '<div class="mb-brand-sub">Markets, my stocks and what they are worth</div>')
        st.radio("Navigate", PAGES, key="page", label_visibility="collapsed")
        st.divider()
        st.html('<div class="mb-side-h">My watchlist</div>')
        for t in wl:
            c1, c2 = st.columns([5, 1], vertical_alignment="center", gap="small")
            c1.button(t, key=f"open_{t}", on_click=open_stock, args=(t,), width="stretch")
            c2.button("✕", key=f"rm_{t}", on_click=remove_stock, args=(t,), help=f"Remove {t}",
                      disabled=len(wl) == 1)
        if len(wl) < MAX_WATCHLIST:
            choice = symbol_search("search_box", "Add: company or ticker")
            if choice:
                st.button(f"Add {choice['symbol']}", type="primary", on_click=add_stock,
                          args=(choice["symbol"],), width="stretch")
        else:
            st.caption(f"The list holds {MAX_WATCHLIST} stocks. Remove one to add another.")
        st.caption("Your list is saved in this page's address. Bookmark it to keep it.")
        st.divider()
        st.caption("For education only, not investment advice. Switch light or dark mode in the ⋮ menu, Settings.")


# =========================================================================== Today
US_BOARD = [
    ("S&P 500 (SPY)", "SPY"), ("Nasdaq 100 (QQQ)", "QQQ"), ("Dow Jones (DIA)", "DIA"),
    ("Russell 2000 (IWM)", "IWM"), ("Gold (GLD)", "GLD"), ("Oil (USO)", "USO"),
]
LATAM_ETFS = [("Mexican stocks (EWW)", "EWW"), ("Argentine stocks (ARGT)", "ARGT")]
UNAVAILABLE = {"px": "n/a", "chip": "", "extra": "", "asof": "Unavailable right now", "text": ""}


def etf_cell(label: str, sym: str) -> dict:
    try:
        q = data.quote(sym)
        return {"name": label, "px": f"${q['price']:,.2f}", "chip": chip(q["pct"]),
                "extra": range_bar(q["low"], q["high"], q["price"], left="Day low", right="high"),
                "asof": when(q["time"]),
                "text": f"{label}: ${q['price']:,.2f}" + (f" ({q['pct']:+.2f}% today)" if q["pct"] is not None else "")}
    except Exception:
        return {"name": label, **UNAVAILABLE}


def us_cells() -> list[dict]:
    cells = [etf_cell(label, sym) for label, sym in US_BOARD]
    try:
        b = data.bitcoin()
        cells.append({"name": "Bitcoin", "px": f"${b['price']:,.0f}", "chip": chip(b["pct"], " 24h"), "extra": "",
                      "asof": f"Trades 24/7, {when(b['time'])}", "text": f"Bitcoin: ${b['price']:,.0f} ({b['pct']:+.2f}% in 24h)"})
    except Exception:
        cells.append({"name": "Bitcoin", **UNAVAILABLE})
    try:
        t = data.fred_latest("DGS10")
        bps = round((t["value"] - t["prev"]) * 100)
        sign = "+" if bps > 0 else "−" if bps < 0 else ""
        cells.append({"name": "US 10-year Treasury yield", "px": f"{t['value']:.2f}%",
                      "chip": f'<span class="mb-chip flat">{sign}{abs(bps)} bps</span>', "extra": "",
                      "asof": f"Daily close, {t['date']} (FRED)",
                      "text": f"US 10-year Treasury yield: {t['value']:.2f}% ({bps:+d} bps vs prior day, {t['date']})"})
    except Exception:
        cells.append({"name": "US 10-year Treasury yield", **UNAVAILABLE})
    try:
        t2 = data.fred_latest("DGS2")
        t10 = data.fred_latest("DGS10")
        bps = round((t2["value"] - t2["prev"]) * 100)
        sign = "+" if bps > 0 else "−" if bps < 0 else ""
        curve = round((t10["value"] - t2["value"]) * 100)
        cells.append({"name": "US 2-year Treasury yield", "px": f"{t2['value']:.2f}%",
                      "chip": f'<span class="mb-chip flat">{sign}{abs(bps)} bps</span>', "extra": "",
                      "asof": f"10Y minus 2Y: {curve:+d} bps. Daily close, {t2['date']}",
                      "text": f"US 2-year Treasury yield: {t2['value']:.2f}%; 10-year minus 2-year spread {curve:+d} bps"})
    except Exception:
        cells.append({"name": "US 2-year Treasury yield", **UNAVAILABLE})
    return cells


def latam_cells() -> list[dict]:
    cells = [etf_cell(label, sym) for label, sym in LATAM_ETFS]
    try:
        fx = data.fx_quote("USD/MXN")
        cells.append({"name": "Dollar in Mexican pesos", "px": f"{fx['price']:,.4f}", "chip": chip(fx["pct"]), "extra": "",
                      "asof": f"As of {fx['time']}", "text": f"USD/MXN: {fx['price']:.4f} ({fx['pct']:+.2f}%)"})
    except Exception:
        cells.append({"name": "Dollar in Mexican pesos", **UNAVAILABLE})
    labels = (("oficial", "Argentina: official dollar"), ("bolsa", "Argentina: MEP dollar"), ("blue", "Argentina: blue dollar"))
    try:
        ar = data.dolares_ar()
        official = ar.get("oficial", {}).get("sell")
        for casa, label in labels:
            r = ar.get(casa)
            if not r:
                cells.append({"name": label, **UNAVAILABLE})
                continue
            gap = (r["sell"] / official - 1) * 100 if official and casa != "oficial" else None
            cells.append({"name": label, "px": f"ARS {r['sell']:,.0f}",
                          "chip": f'<span class="mb-chip flat">{gap:+.1f}% vs official</span>' if gap is not None else "",
                          "extra": "", "asof": f"Sell price, {when(r['time'])}" if r["time"] else "Sell price",
                          "text": f"{label}: ARS {r['sell']:,.0f} sell"})
    except Exception:
        cells += [{"name": label, **UNAVAILABLE} for _, label in labels]
    return cells


def board_html(cells: list[dict], cols: int) -> str:
    return f'<div class="mb-board" style="--cols:{cols}">' + "".join(
        f'<div class="mb-cell"><div class="name">{esc(c["name"])}</div>'
        f'<div class="row"><span class="px num">{esc(c["px"])}</span>{c["chip"]}</div>{c["extra"]}'
        f'<div class="asof">{esc(c["asof"])}</div></div>'
        for c in cells
    ) + "</div>"


def status_line() -> str:
    try:
        s = data.market_status()
    except Exception:
        return "Market status unavailable"
    if s.get("isOpen"):
        return '<span class="mb-dot open"></span>US market open, quotes refresh every minute'
    session = {"pre-market": "pre-market trading", "post-market": "after-hours trading"}.get(s.get("session") or "")
    holiday = f" for {esc(s['holiday'])}" if s.get("holiday") else ""
    state = f"US market in {session}" if session else f"US market closed{holiday}"
    return f'<span class="mb-dot closed"></span>{state}, prices are the latest close'


def story_html(s: dict, top: bool = False) -> str:
    sources = "".join(
        f'<a class="mb-src" href="{esc(h["url"])}" target="_blank" rel="noopener">{esc(h["source"])}, {h["time"]:%b %d %-I:%M %p}</a>'
        for h in s["sources"]
    )
    return (
        f'<div class="mb-story{" top" if top else ""}"><h3>{esc(s["headline"])}</h3>'
        f'<p><b>What happened.</b> {esc(s["what_happened"])}</p>'
        f'<p><b>Why it matters.</b> {esc(s["why_it_matters"])}</p>'
        f'<p class="watch"><b>Next to watch.</b> {esc(s["what_to_watch"])}</p>'
        f'<div class="mb-sources">{sources}</div></div>'
    )


def render_rail(wl: list[str]) -> None:
    st.html('<div class="mb-rail-h">My watchlist</div>')
    upcoming = []
    for t in wl:
        with st.container(key=f"rail_{t}"):
            try:
                p = data.profile(t)
            except Exception:
                p = {"name": t}
            try:
                q = data.quote(t)
                price, ch = f"${q['price']:,.2f}", chip(q["pct"])
            except Exception:
                price, ch = "n/a", ""
            try:
                spark = spark_svg(data.history(t)["close"].iloc[-126:].tolist())
            except Exception:
                spark = ""
            st.html(f'<div class="mb-rail"><div class="mb-rrow"><div><div class="tk">{esc(t)}</div><div class="co">{esc(p["name"])}</div></div>'
                    f'<div><div class="px num">{price}</div><div style="text-align:right;margin-top:.2rem">{ch}</div></div></div>{spark}</div>')
            st.button("Open analysis", key=f"railbtn_{t}", on_click=open_stock, args=(t,))
        try:
            e = data.next_earnings(t)
            if e:
                upcoming.append((e["date"], t, e["timing"]))
        except Exception:
            pass
    if upcoming:
        st.html('<div class="mb-rail-h" style="margin-top:1.2rem">Earnings coming up</div><div class="mb-cal">' + "".join(
            f'<div><span><b>{esc(t)}</b></span><span>{dt.date.fromisoformat(d):%a %b %-d}'
            f'{(", before open" if "before" in timing else ", after close") if timing else ""}</span></div>'
            for d, t, timing in sorted(upcoming)
        ) + "</div>")
    st.caption("Six months of daily closes in each chart.")


def page_today(wl: list[str]) -> None:
    now = dt.datetime.now(data.ET)
    clocks = "".join(
        f'<div class="mb-clock"><div class="city">{city}</div><div class="t num">{dt.datetime.now(ZoneInfo(tz)):%-I:%M %p}</div></div>'
        for city, tz in CLOCKS
    )
    st.html(f'<div class="mb-mast"><div><h1 class="mb-date">{now:%A, %B %-d}</h1>'
            f'<div class="mb-dek">{status_line()}</div></div><div class="mb-clocks">{clocks}</div></div>')

    main, rail = st.columns([2.3, 1], gap="large")
    with rail:
        render_rail(wl)
    with main:
        us, latam = us_cells(), latam_cells()
        st.html(
            f'<div class="mb-board-h"><b>United States</b><span>{src("mkt")}</span></div>' + board_html(us, 3)
            + f'<div class="mb-board-h"><b>Mexico and Argentina</b><span>{src("mkt")}</span></div>' + board_html(latam, 3)
            + '<p class="mb-foot">Indices through the US-listed ETFs that track them (SPY, QQQ, DIA, IWM, EWW for Mexico, '
            "ARGT for Argentina); gold and oil through GLD and USO. Argentine dollar rates from DolarApi.</p>"
        )

        headlines, failed = data.todays_headlines()
        st.html(f'<h2 class="mb-section">The morning note {src("ai")}</h2>')
        note_slot = st.container()
        st.html(f'<h2 class="mb-section">Latest headlines {src("mkt")}</h2>')
        st.html('<div class="mb-list">' + "".join(
            f'<div class="mb-item"><div><a href="{esc(h["url"])}" target="_blank" rel="noopener">{esc(h["title"])}</a></div>'
            f'<div class="meta">{esc(h["source"])}<br>{h["time"]:%b %d, %-I:%M %p}</div></div>'
            for h in headlines[:20]
        ) + "</div>")
        if failed:
            st.caption("No answer this time from: " + ", ".join(failed))

        with note_slot:
            if not headlines:
                st.info("No headlines from the last day could be loaded. The sources may be down; try again in a few minutes.")
                return
            snapshot = "\n".join(c["text"] for c in us + latam if c["text"])
            slot = f"{now:%Y-%m-%d}-{now.hour // 6}"
            placeholder = st.empty()
            placeholder.html('<div class="mb-story"><div class="mb-skel" style="width:92%"></div><div class="mb-skel" style="width:85%">'
                             '</div><div class="mb-skel" style="width:60%"></div><p class="mb-note">Writing today\'s note from '
                             f'{min(len(headlines), 40)} headlines. This takes a few seconds the first time.</p></div>')
            try:
                brief = ai.daily_brief(slot, snapshot, headlines)
                stories = brief["stories"]
                out = f'<p class="mb-lead">{esc(brief["market_summary"])}</p>'
                if stories:
                    out += story_html(stories[0], top=True)
                if len(stories) > 1:
                    out += '<div class="mb-grid2">' + "".join(story_html(s) for s in stories[1:]) + "</div>"
                out += (f'<p class="mb-note">Written by AI at {brief["generated_at"]:%-I:%M %p} ET from {brief["n_headlines"]} '
                        "headlines and the market boards above, and nothing else. Follow the source links before relying on it.</p>")
                placeholder.html(out)
            except Exception as exc:
                placeholder.warning(f"The AI note couldn't be written this time ({exc}). The latest headlines are below.")


# =========================================================================== Watchlist
@st.cache_data(ttl=6 * 3600, show_spinner=False)
def quick_value(ticker: str, price: float) -> dict | None:
    """Base-case DCF with default assumptions, for the at-a-glance column."""
    f = fundamentals.build(data.sec_facts(ticker))
    rf, _ = data.risk_free_rate()
    close = data.history(ticker)["close"]
    bench = data.history(BENCHMARK)["close"]
    return analysis.default_valuation(f, price, analysis.beta(close, bench), rf)


def page_watchlist(wl: list[str]) -> None:
    st.html('<div class="mb-mast"><div><h1 class="mb-date">My watchlist</h1>'
            '<div class="mb-dek">Price, trend, risk and what each stock looks worth, side by side.</div></div></div>')
    h_info, _ = st.columns([5.6, 1])
    h_info.html('<div class="mb-tr head" style="grid-template-columns:1.7fr 1fr 1.6fr 1.2fr 1.25fr;padding:0 1.1rem">'
                '<div>Company</div><div>Price</div><div>One year</div>'
                f'<div>Returns and risk</div><div>Value vs price {src("calc")}</div></div>')
    for t in wl:
        with st.container(key=f"wl_{t}"):
            try:
                p = data.profile(t)
            except Exception:
                p = {"name": t, "industry": ""}
            try:
                q = data.quote(t)
                price_html = (f'<div class="px num">${q["price"]:,.2f}</div><div style="margin:.25rem 0">{chip(q["pct"])}</div>'
                              f'<div class="small">{when(q["time"])}</div>')
            except Exception:
                q, price_html = None, '<div class="px">n/a</div>'
            try:
                close = data.history(t)["close"]
                yr = close.iloc[-252:]
                trend = spark_svg(yr.tolist()) + range_bar(float(yr.min()), float(yr.max()), float(yr.iloc[-1]),
                                                           left="52w low", right="high")
                r1y, r3m = analysis.period_return(close, 252), analysis.period_return(close, 63)
                vol, dd = analysis.annual_volatility(close), analysis.max_drawdown(close)
                risk = (f'<div class="small">3M <b class="{signed_class(r3m)}">{pct(r3m)}</b> &nbsp; 1Y <b class="{signed_class(r1y)}">{pct(r1y)}</b><br>'
                        f'Volatility <b>{pct(vol, signed=False)}</b><br>Max drawdown <b>{pct(dd)}</b></div>')
            except Exception as exc:
                trend, risk = f'<div class="small">Chart unavailable: {esc(exc)}</div>', ""
            value = '<div class="small">n/a</div>'
            if q:
                try:
                    v = quick_value(t, round(q["price"], 2))
                    if v:
                        cls = "pos" if v["label"] == "Looks undervalued" else "neg" if v["label"] == "Looks overvalued" else ""
                        value = (f'<div class="small"><b class="{cls}">{v["label"]}</b><br>DCF <b>${v["per_share"]:,.0f}</b> '
                                 f'({pct(v["gap"], 0)} vs price)<br>Growth {pct(v["growth"], 0, False)}, WACC {pct(v["wacc"], 1, False)}</div>')
                    else:
                        value = '<div class="small">DCF doesn\'t apply (negative cash flow or missing filings)</div>'
                except Exception:
                    value = '<div class="small">Valuation unavailable (non-US filer or ETF)</div>'
            c_info, c_btn = st.columns([5.6, 1], vertical_alignment="center")
            c_info.html(f'<div class="mb-tr" style="padding:0;border:0;grid-template-columns:1.7fr 1fr 1.6fr 1.2fr 1.25fr">'
                        f'<div><div class="tk">{esc(t)}</div><div class="co">{esc(p["name"])}</div><div class="small">{esc(p.get("industry", ""))}</div></div>'
                        f'<div>{price_html}</div><div>{trend}</div><div>{risk}</div><div>{value}</div></div>')
            c_btn.button("Open analysis", key=f"analyze_{t}", on_click=open_stock, args=(t,), type="primary", width="stretch")
            try:
                e = data.next_earnings(t)
                if e:
                    c_btn.html(f'<div class="small" style="text-align:center;color:var(--faint);font-size:.78rem">'
                               f'Earnings {dt.date.fromisoformat(e["date"]):%b %-d}</div>')
            except Exception:
                pass
    st.caption("Value vs price uses the base-case DCF with default assumptions (5-year revenue CAGR capped at 0-20%, "
               "CAPM cost of equity, 2.5% terminal growth). Open a stock to change them.")


# =========================================================================== Stock analysis
def price_chart(hist: pd.DataFrame, vol: float | None, lookback: int) -> go.Figure:
    p = P()
    close = hist["close"]
    ma50, ma200 = close.rolling(50).mean(), close.rolling(200).mean()
    c = close.iloc[-lookback:]
    idx = c.index
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.8, 0.2], vertical_spacing=0.03)
    fig.add_trace(go.Scatter(x=idx, y=c.values, mode="lines", name="Daily close", line=dict(color=p["accent"], width=2),
                             hovertemplate="$%{y:,.2f}<extra>Close</extra>"), row=1, col=1)
    fig.add_trace(go.Scatter(x=idx, y=ma50.loc[idx].values, mode="lines", name="50-day average",
                             line=dict(color=p["orange"], width=1.3), hovertemplate="$%{y:,.2f}<extra>50-day</extra>"), row=1, col=1)
    fig.add_trace(go.Scatter(x=idx, y=ma200.loc[idx].values, mode="lines", name="200-day average",
                             line=dict(color=p["muted"], width=1.3, dash="dash"), hovertemplate="$%{y:,.2f}<extra>200-day</extra>"),
                  row=1, col=1)
    if vol:
        future = pd.bdate_range(idx[-1], periods=64)
        sig = vol * np.sqrt(np.arange(len(future)) / analysis.TRADING_DAYS)
        last = c.iloc[-1]
        fig.add_trace(go.Scatter(x=future, y=last * np.exp(sig), mode="lines", line=dict(color=p["accent"], width=1, dash="dot"),
                                 name="Range if volatility holds (±1σ)", hovertemplate="$%{y:,.2f}<extra>Upper</extra>"), row=1, col=1)
        fig.add_trace(go.Scatter(x=future, y=last * np.exp(-sig), mode="lines", line=dict(color=p["accent"], width=1, dash="dot"),
                                 fill="tonexty", fillcolor=p["fill"], showlegend=False,
                                 hovertemplate="$%{y:,.2f}<extra>Lower</extra>"), row=1, col=1)
    if "volume" in hist:
        v = hist["volume"].iloc[-lookback:]
        fig.add_trace(go.Bar(x=v.index, y=v.values, name="Volume", marker_color=p["line"], showlegend=False,
                             hovertemplate="%{y:,.0f}<extra>Volume</extra>"), row=2, col=1)
    fig.update_yaxes(tickprefix="$", row=1, col=1)
    fig.update_yaxes(showticklabels=False, row=2, col=1)
    return style_fig(fig, 470)


def drawdown_chart(close: pd.Series) -> go.Figure:
    p = P()
    dd = analysis.drawdown_series(close) * 100
    fig = go.Figure(go.Scatter(x=dd.index, y=dd.values, mode="lines", line=dict(color=p["down"], width=1.6),
                               fill="tozeroy", fillcolor=p["down_bg"], hovertemplate="%{y:.1f}%<extra>From peak</extra>"))
    fig.update_yaxes(ticksuffix="%")
    fig.update_layout(showlegend=False)
    return style_fig(fig, 250)


def fundamentals_chart(f: dict) -> go.Figure:
    p = P()
    rev, fcf = f["revenue"], f["fcf"]
    years = sorted(set(rev.index) | set(fcf.index))[-8:]
    to_b = lambda s: [s.get(y) / 1e9 if s.get(y) is not None else None for y in years]  # noqa: E731
    fig = go.Figure()
    fig.add_trace(go.Bar(x=[str(y) for y in years], y=to_b(rev), name="Revenue", marker_color=p["accent"],
                         hovertemplate="$%{y:,.1f}B<extra>Revenue</extra>"))
    fig.add_trace(go.Bar(x=[str(y) for y in years], y=to_b(fcf), name="Free cash flow", marker_color=p["orange"],
                         hovertemplate="$%{y:,.1f}B<extra>Free cash flow</extra>"))
    fig.update_layout(barmode="group", bargap=0.32, bargroupgap=0.08)
    fig.update_traces(marker_cornerradius=4)
    fig.update_yaxes(tickprefix="$", ticksuffix="B")
    return style_fig(fig, 320)


def football_field(rows: list[tuple[str, float, float]], price: float) -> go.Figure:
    """Valuation ranges side by side, the way buy-side and sell-side decks show them."""
    p = P()
    rows = [r for r in rows if r[1] is not None and r[2] is not None]
    names = [r[0] for r in rows][::-1]
    lows = [min(r[1], r[2]) for r in rows][::-1]
    highs = [max(r[1], r[2]) for r in rows][::-1]
    fig = go.Figure(go.Bar(
        y=names, x=[h - lo for lo, h in zip(lows, highs)], base=lows, orientation="h",
        marker=dict(color=p["accent"], opacity=0.8, cornerradius=4), width=0.5,
        customdata=list(zip(lows, highs)),
        hovertemplate="%{y}: $%{customdata[0]:,.0f} to $%{customdata[1]:,.0f}<extra></extra>",
        text=[f"${lo:,.0f}  to  ${h:,.0f}" for lo, h in zip(lows, highs)], textposition="outside",
        textfont=dict(color=p["muted"], size=12), cliponaxis=False,
    ))
    fig.add_vline(x=price, line_color=p["ink"], line_width=2, line_dash="dot")
    fig.add_annotation(x=price, y=1.06, yref="paper", text=f"Market price ${price:,.2f}", showarrow=False,
                       font=dict(color=p["ink"], size=12), xanchor="center")
    lo_all, hi_all = min(lows + [price]), max(highs + [price])
    span = hi_all - lo_all
    fig.update_xaxes(tickprefix="$", range=[max(0, lo_all - span * 0.08), hi_all + span * 0.3], gridcolor=p["grid"], showgrid=True)
    fig.update_layout(hovermode="closest", showlegend=False)
    return style_fig(fig, 90 + 62 * len(rows))


def stats_html(items: list[tuple[str, str, str, str]], cols: int = 4) -> str:
    """items: (label, value, css class, small note)."""
    return f'<div class="mb-stats" style="--cols:{cols}">' + "".join(
        f'<div class="mb-stat"><div class="k">{esc(k)}</div><div class="v num {cls}">{esc(v)}</div>'
        + (f'<div class="s">{esc(s)}</div>' if s else "") + "</div>"
        for k, v, cls, s in items
    ) + "</div>"


def page_stock(wl: list[str]) -> None:
    current = st.session_state.get("ticker") or wl[0]
    options = wl + ([current] if current not in wl else [])
    top_l, top_r = st.columns([2.2, 1.3], vertical_alignment="center")
    with top_l:
        pick = st.segmented_control("Stock", options, default=current, key=f"pick_{'_'.join(options)}_{current}",
                                    label_visibility="collapsed")
    with top_r:
        choice = symbol_search("any_box", "Analyze any US stock: name or ticker")
        if choice:
            b1, b2 = st.columns(2)
            b1.button(f"Analyze {choice['symbol']}", type="primary", on_click=analyze_any, args=(choice["symbol"],), width="stretch")
            if choice["symbol"] not in wl and len(wl) < MAX_WATCHLIST:
                b2.button("Add to watchlist", on_click=add_stock, args=(choice["symbol"], "any_box"), width="stretch")
    ticker = pick or current
    st.session_state.ticker = ticker

    try:
        p = data.profile(ticker)
    except Exception:
        p = {"name": ticker, "industry": "", "logo": ""}
    try:
        q = data.quote(ticker)
    except Exception as exc:
        st.error(f"Couldn't load a quote for {ticker}: {exc}")
        return
    try:
        hist = data.history(ticker)
        close = hist["close"]
    except Exception as exc:
        st.error(f"Price history unavailable: {exc}")
        return
    try:
        bench = data.history(BENCHMARK)["close"]
    except Exception:
        bench = None
    rf, rf_label = data.risk_free_rate()
    m = analysis.risk_metrics(close, bench, rf)

    logo = f'<img class="logo" src="{esc(p["logo"])}" alt="">' if p.get("logo") else ""
    try:
        e = data.next_earnings(ticker)
    except Exception:
        e = None
    earn = (f'<span>Next earnings {dt.date.fromisoformat(e["date"]):%b %-d}{", " + esc(e["timing"]) if e["timing"] else ""}</span>'
            if e else "")
    st.html(f'<div class="mb-stock"><div class="idt">{logo}<div><div class="co">{esc(p["name"])}</div>'
            f'<div class="meta"><span class="mb-tag">{esc(ticker)}</span><span>{esc(p.get("industry", ""))}</span>{earn}</div></div></div>'
            f'<div class="quote"><div class="big num">${q["price"]:,.2f}</div><div style="margin-top:.45rem">{chip(q["pct"])}</div>'
            f'<div class="asof">{when(q["time"])}</div></div></div>')
    st.html(stats_html([
        ("Year to date", pct(m["ret_ytd"]), signed_class(m["ret_ytd"]), "since last year's close"),
        ("1 year", pct(m["ret_1y"]), signed_class(m["ret_1y"]), "price return"),
        ("Volatility", pct(m["volatility"], signed=False), "", "annualized, 1 year of daily moves"),
        ("Max drawdown", pct(m["max_drawdown"]), "neg" if m["max_drawdown"] else "", "worst fall from a peak, 1 year"),
        (f"Beta vs {BENCHMARK}", num(m["beta"]), "", "2 years of weekly returns"),
        ("Sharpe ratio", num(m["sharpe"]), "", "1 year, vs 10Y Treasury"),
    ], cols=6))

    tab_chart, tab_val, tab_news, tab_ai = st.tabs(["Chart and risk", "Valuation", "News", "AI view"])
    with tab_chart:
        render_chart_tab(ticker, q, hist, m, rf_label)
    with tab_val:
        val = render_valuation(ticker, q["price"], close, m, rf, rf_label)
    with tab_news:
        news = render_news(ticker)
    with tab_ai:
        render_ai_take(ticker, p["name"], q, m, val, news)


def render_chart_tab(ticker: str, q: dict, hist: pd.DataFrame, m: dict, rf_label: str) -> None:
    close = hist["close"]
    span = st.segmented_control("Period", ["3M", "6M", "1Y", "2Y"], default="1Y", key=f"span_{ticker}",
                                label_visibility="collapsed") or "1Y"
    lookback = {"3M": 63, "6M": 126, "1Y": 252, "2Y": len(close)}[span]
    st.plotly_chart(price_chart(hist, m["volatility"], lookback), key=f"price_{ticker}", config={"displayModeBar": False})
    ma50, ma200 = close.rolling(50).mean().iloc[-1], close.rolling(200).mean().iloc[-1]
    last = close.iloc[-1]
    if not np.isnan(ma200):
        if last > ma50 > ma200:
            trend = "Uptrend: the price is above its 50-day average, which is above the 200-day."
        elif last < ma50 < ma200:
            trend = "Downtrend: the price is below its 50-day average, which is below the 200-day."
        else:
            trend = "Mixed trend: the price and its 50- and 200-day averages don't line up in one direction."
        st.html(f'<p class="mb-foot">{src("calc")} &nbsp;{esc(trend)} {esc(rf_label)}.</p>')

    left, right = st.columns([1.1, 1], gap="large")
    with left:
        st.html(f'<div class="mb-h3">How far it usually moves {src("calc")}</div>')
        if m["volatility"]:
            rows = ""
            for label, days in (("1 month", 21), ("3 months", 63), ("6 months", 126)):
                lo1, hi1 = analysis.statistical_range(q["price"], m["volatility"], days)
                s = m["volatility"] * np.sqrt(days / analysis.TRADING_DAYS) * 1.96
                lo2, hi2 = q["price"] * np.exp(-s), q["price"] * np.exp(s)
                rows += f"<tr><td>{label}</td><td>${lo1:,.2f} to ${hi1:,.2f}</td><td>${lo2:,.2f} to ${hi2:,.2f}</td></tr>"
            st.html(f'<table class="mb-rt"><tr><th>Horizon</th><th>2 in 3 outcomes</th><th>19 in 20 outcomes</th></tr>{rows}</table>'
                    f'<p class="mb-foot">If the stock stays as volatile as the last year ({pct(m["volatility"], signed=False)} a year) '
                    "with no drift up or down. A description of risk, not a forecast or a target; real crashes are bigger "
                    "than this normal model suggests.</p>")
    with right:
        st.html(f'<div class="mb-h3">Drawdown, last year {src("calc")}</div>')
        st.plotly_chart(drawdown_chart(close), key=f"dd_{ticker}", config={"displayModeBar": False})


def render_valuation(ticker: str, price: float, close: pd.Series, m: dict, rf: float, rf_label: str) -> dict | None:
    try:
        with st.spinner("Reading SEC filings…"):
            f = fundamentals.build(data.sec_facts(ticker))
    except Exception as exc:
        st.info(f"Valuation isn't available for {ticker}: {exc}")
        return None
    if f["fcf"].empty or not f["shares"]:
        st.info("The SEC filings don't have enough data (free cash flow or share count) to value this company.")
        return None

    shares = f["shares"]
    mcap = price * shares
    last_year = int(f["fcf"].index[-1])
    last_fcf = float(f["fcf"].iloc[-1])
    eps = float(f["eps"].iloc[-1]) if not f["eps"].empty else None
    hist_g = fundamentals.revenue_cagr(f["revenue"])
    result = {"fundamentals": f, "mcap": mcap, "eps": eps, "last_fcf": last_fcf, "last_year": last_year}

    default_g = float(np.clip(hist_g if hist_g is not None else 0.05, 0.0, 0.20))
    beta_used = float(np.clip(m["beta"], 0.5, 2.5)) if m["beta"] else 1.0
    with st.expander("DCF assumptions (change them and everything below updates)", expanded=False):
        a1, a2, a3 = st.columns(3)
        base_choice = a1.radio("Starting free cash flow", ["Latest year", "3-year average"], key=f"base_{ticker}", horizontal=True)
        growth = a2.slider("FCF growth, years 1 to 5 (%)", -10.0, 40.0, round(default_g * 100, 1), 0.5, key=f"g_{ticker}") / 100
        g_term = a3.slider("Terminal growth (%)", 0.0, 4.0, 2.5, 0.1, key=f"gt_{ticker}") / 100
        b1, b2, b3, b4 = st.columns(4)
        erp = b1.number_input("Equity risk premium (%)", 3.0, 8.0, 5.0, 0.25, key=f"erp_{ticker}") / 100
        beta_in = b2.number_input("Beta", 0.3, 3.0, round(beta_used, 2), 0.05, key=f"beta_{ticker}")
        kd = b3.number_input("Pre-tax cost of debt (%)", 1.0, 12.0, round((rf + 0.015) * 100, 2), 0.25, key=f"kd_{ticker}") / 100
        tax = b4.number_input("Tax rate (%)", 0.0, 35.0, 21.0, 1.0, key=f"tax_{ticker}") / 100
        w = analysis.wacc(rf, beta_in, erp, kd, tax, mcap, f["debt"])
        discount = st.slider("Discount rate used (WACC, %)", 4.0, 16.0, round(w["wacc"] * 100, 1), 0.1,
                             key=f"wacc_{ticker}_{round(w['wacc'] * 100, 1)}") / 100
        base_fcf = last_fcf if base_choice == "Latest year" else float(f["fcf"].iloc[-3:].mean())
        st.caption(
            f"Starting FCF {money(base_fcf)}. Default growth is the last five years' revenue CAGR "
            f"({pct(hist_g) if hist_g is not None else 'n/a'}) capped at 0 to 20%; years 6 to 10 fade to terminal growth. "
            f"Cost of equity {pct(rf, 2, False)} + {beta_in:.2f} × {pct(erp, 2, False)} = {pct(w['cost_of_equity'], 2, False)}; "
            f"weights {pct(w['we'], 0, False)} equity and {pct(w['wd'], 0, False)} debt give a WACC of {pct(w['wacc'], 2, False)}. "
            f"{rf_label}."
        )

    if base_fcf <= 0:
        st.info("Free cash flow is negative, so a cash-flow DCF doesn't apply here. "
                "Revenue growth and the path to profitability are the better lens.")
    else:
        try:
            base = analysis.dcf(base_fcf, growth, g_term, discount, f["net_debt"], shares)
            bear = analysis.dcf(base_fcf, max(growth - 0.05, -0.10), g_term, discount + 0.01, f["net_debt"], shares)
            bull = analysis.dcf(base_fcf, growth + 0.05, g_term, max(discount - 0.01, g_term + 0.006), f["net_debt"], shares)
        except ValueError as exc:
            st.error(str(exc))
            return result
        label, gap = analysis.verdict(base.per_share, price)
        implied = analysis.implied_growth(price, base_fcf, g_term, discount, f["net_debt"], shares)
        pal = P()
        color = pal["up"] if label == "Looks undervalued" else pal["down"] if label == "Looks overvalued" else pal["muted"]
        st.html(
            f'<div class="mb-verdict"><div><div class="k">Intrinsic value per share {src("calc")}</div>'
            f'<div class="v num">${base.per_share:,.2f}</div><div class="k">Base case DCF</div></div>'
            f'<div><div class="k">Market price {src("mkt")}</div><div class="v num">${price:,.2f}</div>'
            f'<div class="k">Upside to intrinsic value: <b style="color:{color}">{pct(gap)}</b></div></div>'
            f'<div><div class="k">Verdict under these assumptions</div><div class="label" style="color:{color}">{label}</div>'
            f'<div class="k">Within ±15% counts as fairly valued</div></div></div>'
        )
        if implied is not None:
            st.html(
                f'<div class="mb-callout"><b>What the price implies.</b> To be worth ${price:,.2f}, free cash flow would need to grow '
                f'about <b>{pct(implied)} a year for five years</b> before fading to {pct(g_term, 1, False)}, at a '
                f'{pct(discount, 1, False)} discount rate. Over the last five years revenue grew '
                f'{pct(hist_g) if hist_g is not None else "n/a"} a year.</div>'
            )
        rates = [round(discount + d, 4) for d in (-0.02, -0.01, 0.0, 0.01, 0.02)]
        terms = [round(g_term + d, 4) for d in (-0.01, -0.005, 0.0, 0.005, 0.01)]
        sens = analysis.sensitivity(base_fcf, growth, f["net_debt"], shares, rates, terms)
        inner = sens.loc[rates[1:4], terms[1:4]].to_numpy()
        week52 = close.iloc[-252:]
        lo3, hi3 = analysis.statistical_range(price, m["volatility"], 63) if m["volatility"] else (None, None)
        st.html(f'<div class="mb-h3">Valuation ranges {src("calc")}</div>')
        st.plotly_chart(football_field([
            ("DCF scenarios (bear to bull)", bear.per_share, bull.per_share),
            ("DCF sensitivity (WACC ±1 pt, g ±0.5 pt)", float(np.nanmin(inner)), float(np.nanmax(inner))),
            ("52-week trading range", float(week52.min()), float(week52.max())),
            ("3-month statistical range", lo3, hi3),
        ], price), key=f"ff_{ticker}", config={"displayModeBar": False})
        st.caption("Bear case: growth 5 points lower and discount rate 1 point higher. Bull case: the opposite.")
        with st.expander("Sensitivity table and DCF detail"):
            show = sens.copy()
            show.index = [pct(r, 1, False) for r in show.index]
            show.columns = [pct(g, 1, False) for g in show.columns]
            st.markdown("**Intrinsic value per share.** Rows are the discount rate, columns terminal growth.")
            st.dataframe(show.style.format("${:,.0f}", na_rep="n/m"))
            proj = base.projections.copy()
            proj["Growth"] = proj["Growth"].map(pct)
            for col in ("FCF", "PV of FCF"):
                proj[col] = proj[col].map(money)
            proj["Discount factor"] = proj["Discount factor"].map(lambda x: f"{x:.3f}")
            st.dataframe(proj, hide_index=True)
            st.caption(
                f"Discounted FCF {money(base.pv_fcf)} + discounted terminal value {money(base.pv_terminal)} = enterprise value "
                f"{money(base.enterprise_value)}; minus net debt {money(f['net_debt'])} = equity value {money(base.equity_value)}; "
                f"divided by {shares / 1e9:,.2f}B shares ({f['shares_source']}) = ${base.per_share:,.2f}. "
                f"The terminal value is {pct(base.terminal_share, 0, False)} of enterprise value."
            )
        result.update({"base": base.per_share, "bear": bear.per_share, "bull": bull.per_share, "growth": growth,
                       "g_term": g_term, "discount": discount, "implied": implied, "label": label, "gap": gap})

    st.html(f'<div class="mb-h3">Reported fundamentals {src("rep")}</div>')
    st.plotly_chart(fundamentals_chart(f), key=f"fund_{ticker}", config={"displayModeBar": False})
    st.html(stats_html([
        ("Market cap", money(mcap), "", "price × shares outstanding"),
        (f"P/E, FY{last_year}", f"{price / eps:,.1f}x" if eps and eps > 0 else "n/m", "", "on diluted EPS"),
        (f"Price to FCF, FY{last_year}", f"{mcap / last_fcf:,.1f}x" if last_fcf > 0 else "n/m", "", "market cap / free cash flow"),
        ("FCF yield", pct(last_fcf / mcap, signed=False) if last_fcf > 0 else "n/m", "", "free cash flow / market cap"),
    ]))
    st.caption(f"SEC 10-K data (XBRL), calendar-aligned fiscal years. Net debt {money(f['net_debt'])} as of "
               f"{f['balance_sheet_date']}. A DCF doesn't suit banks, insurers or companies with negative cash flow.")
    for note in f["notes"]:
        st.caption(f"Note: {note}")
    return result


def render_news(ticker: str) -> list[dict]:
    try:
        news = data.company_news(ticker)
    except Exception as exc:
        st.info(f"Company news isn't available right now: {exc}")
        return []
    if not news:
        st.info("No company news in the last 7 days.")
        return news
    st.html('<div class="mb-list">' + "".join(
        f'<div class="mb-item"><div><a href="{esc(n["url"])}" target="_blank" rel="noopener">{esc(n["title"])}</a>'
        + (f'<div class="sum">{esc(n["summary"])}</div>' if n["summary"] else "")
        + f'</div><div class="meta">{esc(n["source"])}<br>{n["time"]:%b %d, %-I:%M %p}</div></div>'
        for n in news if n.get("time")
    ) + "</div>")
    return news


def ai_data_text(ticker: str, q: dict, m: dict, val: dict | None) -> str:
    lines = [
        f"Price ${q['price']:,.2f} ({q['pct']:+.2f}% today), quote time {q['time']:%Y-%m-%d %H:%M} ET",
        f"Returns: 1M {pct(m['ret_1m'])}, 3M {pct(m['ret_3m'])}, YTD {pct(m['ret_ytd'])}, 1Y {pct(m['ret_1y'])}",
        f"Risk: 1Y volatility {pct(m['volatility'], signed=False)}, 1Y max drawdown {pct(m['max_drawdown'])}, "
        f"2Y weekly beta vs SPY {num(m['beta'])}, 1Y Sharpe {num(m['sharpe'])}",
    ]
    if val:
        f = val["fundamentals"]
        lines += [
            "Revenue: " + "; ".join(f"FY{y}: {money(v)}" for y, v in f["revenue"].iloc[-5:].items()),
            "Free cash flow: " + "; ".join(f"FY{y}: {money(v)}" for y, v in f["fcf"].iloc[-5:].items()),
            f"Market cap {money(val['mcap'])}, net debt {money(f['net_debt'])}",
        ]
        if val.get("eps") and val["eps"] > 0:
            lines.append(f"P/E on FY{val['last_year']} EPS: {q['price'] / val['eps']:.1f}x")
        if val.get("base"):
            lines.append(
                f"DCF (FCF growth {pct(val['growth'])} for 5 years, terminal {pct(val['g_term'])}, discount rate "
                f"{pct(val['discount'], 1, False)}): base ${val['base']:,.2f}, bear ${val['bear']:,.2f}, bull "
                f"${val['bull']:,.2f} per share, so {val['label'].lower()} ({pct(val['gap'])} vs price)"
            )
            if val.get("implied") is not None:
                lines.append(f"Reverse DCF: the price implies about {pct(val['implied'])} annual FCF growth for 5 years")
    try:
        e = data.next_earnings(ticker)
        if e:
            lines.append(f"Next earnings date: {e['date']} {e['timing']}")
    except Exception:
        pass
    return "\n".join(lines)


def render_ai_take(ticker: str, name: str, q: dict, m: dict, val: dict | None, news: list[dict]) -> None:
    key = f"take_{ticker}"
    st.html(f'<p class="mb-foot">{src("ai")} &nbsp;A reading of the numbers and news in the other tabs, using only that data. '
            "An interpretation, not investment advice.</p>")
    if st.button("Write the AI view", type="primary", key=f"btn_{key}"):
        try:
            with st.spinner("Writing the analysis…"):
                st.session_state[key] = ai.stock_take(ticker, name, dt.date.today().isoformat(),
                                                      ai_data_text(ticker, q, m, val), news)
        except Exception as exc:
            st.warning(f"The AI view couldn't be written this time: {exc}")
    take = st.session_state.get(key)
    if not take:
        return
    body = "".join(
        f'<p><b>{title}.</b> {esc(take[k])}</p>'
        for title, k in (("Where it stands", "situation"), ("Recent performance", "recent_performance"),
                         ("Fundamentals", "fundamentals"), ("Valuation", "valuation"), ("News flow", "news"))
        if take.get(k)
    )
    cases = "".join(
        f'<div class="mb-story"><h3>{title}</h3><p>{esc(take.get(k, ""))}</p></div>'
        for title, k in (("Bear case", "bear_case"), ("Base case", "base_case"), ("Bull case", "bull_case"))
    )
    risks = "".join(f"<li>{esc(r)}</li>" for r in take.get("risks", []))
    cats = "".join(f"<li>{esc(c)}</li>" for c in take.get("catalysts", []))
    st.html(
        f'<div class="mb-story top" style="margin-top:.6rem">{body}</div>'
        f'<div class="mb-grid3">{cases}</div>'
        f'<div class="mb-grid2"><div class="mb-story"><h3>Main risks</h3><ul>{risks}</ul></div>'
        f'<div class="mb-story"><h3>Coming catalysts</h3><ul>{cats}</ul></div></div>'
        f'<div class="mb-callout"><b>Conclusion.</b> {esc(take.get("conclusion", ""))}</div>'
        f'<p class="mb-note">Written {take["generated_at"]:%b %d, %-I:%M %p} ET.</p>'
    )


# =========================================================================== Methodology
def page_methodology() -> None:
    st.html('<div class="mb-mast"><div><h1 class="mb-date">How this works</h1>'
            '<div class="mb-dek">Where every number comes from and how it is calculated.</div></div></div>')
    st.html(f'<p class="mb-foot" style="font-size:.9rem">Every figure in the app is tagged: {src("mkt")} prices and rates from data '
            f'providers, {src("rep")} numbers companies filed with the SEC, {src("calc")} figures computed here from those inputs, '
            f'and {src("ai")} text written by the AI from the data shown.</p>')
    st.markdown("""
A personal markets dashboard: a daily AI-written note, a five-stock watchlist, and a one-page analysis per stock with
risk metrics and a discounted cash flow valuation.

#### Data sources (all free tiers)

| What | Source | Freshness |
|---|---|---|
| Stock and ETF quotes, day range | Finnhub | Latest available, refreshed every minute |
| Daily price history and volume | Twelve Data | Daily closes, refreshed every 6 hours |
| Financial statements | SEC EDGAR (XBRL company facts) | As reported in 10-K and 10-Q filings |
| 10-year Treasury yield | FRED (St. Louis Fed) | Daily, previous business day |
| Bitcoin and USD/MXN | CoinGecko and Twelve Data | Every 10 to 15 minutes |
| Argentine dollar rates (official, MEP, blue) | DolarApi | Every 15 minutes |
| Headlines | CNBC, MarketWatch, WSJ Markets, Federal Reserve (RSS) and Finnhub | Every 30 minutes |

Indices are shown through their ETFs (SPY, QQQ, DIA, IWM, EWW for Mexico, ARGT for Argentina) and gold and oil through
GLD and USO, because index and futures levels aren't on free data plans. Mexican and Argentine companies with US
listings (for example AMX, YPF, GGAL, MELI) can be analyzed or added to the watchlist.

#### Risk metrics
Returns use daily closes. Volatility is the annualized standard deviation of daily log returns over the last year.
Beta is the slope of the stock's weekly returns on SPY's over two years. Sharpe is the 1-year return minus the
10-year Treasury yield, divided by volatility. Max drawdown is the worst peak-to-trough fall in the last year.
The trend line compares the price with its 50- and 200-day moving averages.

#### Statistical ranges
price × exp(±zσ√t) from the last year's volatility, with z = 1 (about two in three outcomes) and z = 1.96 (about
nineteen in twenty) under a normal model of log returns with no drift. It describes how much a stock moves, not
where it is going, and real crashes are larger than the model implies.

#### DCF
Free cash flow is operating cash flow minus capital expenditures, from SEC filings. It grows at the chosen rate for
five years, fades in a straight line to terminal growth over the next five, and a Gordon growth terminal value is
added in year 10. Everything is discounted at WACC: cost of equity from CAPM (10-year Treasury + beta × equity risk
premium), after-tax cost of debt, and market-value weights. Equity value is enterprise value minus net debt, divided
by shares outstanding. The reverse DCF solves for the growth rate that makes intrinsic value equal the market price.
The watchlist's value column runs the same model with default assumptions.

#### Valuation ranges
The football field puts the DCF bear-to-bull range, the DCF sensitivity range, the 52-week trading range and the
3-month statistical range on one axis with the market price, so you can see where the price sits.

#### AI
Google Gemini writes the morning note and the stock view. It gets only the headlines and numbers shown in the app
and is told not to add facts, recommend trades or set price targets. Each story links to its sources.

#### Limits
Free data can be delayed or briefly unavailable. SEC tag coverage varies by company, so check the 10-K when a number
looks off. Nothing here is investment advice.
""")


# =========================================================================== main
if "page" not in st.session_state:
    st.session_state.page = "Today"
watchlist = get_watchlist()
render_sidebar(watchlist)

page = st.session_state.page
if page == "Today":
    page_today(watchlist)
elif page == "Watchlist":
    page_watchlist(watchlist)
elif page == "Stock analysis":
    page_stock(watchlist)
else:
    page_methodology()
