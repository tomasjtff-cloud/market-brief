"""Market Brief: a personal markets dashboard.

Run locally with:  streamlit run app.py
"""
from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import ai
import analysis
import data
import fundamentals

st.set_page_config(page_title="Market Brief", page_icon="📈", layout="wide")

DEFAULT_WATCHLIST = ["AAPL", "NVDA", "MSFT", "GOOGL", "TSLA"]
MAX_WATCHLIST = 5
BENCHMARK = "SPY"
PAGES = ["Today", "Watchlist", "Stock analysis", "Methodology"]

BLUE, ORANGE = "#2a78d6", "#eb6834"
UP, DOWN = "#0ca30c", "#d03b3b"
GRID = "rgba(128,128,128,0.18)"


# =========================================================================== helpers
def md(text) -> str:
    """Make text safe for st.markdown ($ would otherwise start LaTeX)."""
    return str(text or "").replace("$", "\\$").replace("[", "(").replace("]", ")")


def money(x, decimals: int = 2) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "—"
    sign, a = ("-" if x < 0 else ""), abs(x)
    for div, suffix in ((1e12, "T"), (1e9, "B"), (1e6, "M")):
        if a >= div:
            return f"{sign}${a / div:,.{decimals}f}{suffix}"
    return f"{sign}${a:,.{decimals}f}"


def pct(x, decimals: int = 1, signed: bool = True) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "—"
    return f"{x * 100:+.{decimals}f}%" if signed else f"{x * 100:.{decimals}f}%"


def num(x, decimals: int = 2) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "—"
    return f"{x:,.{decimals}f}"


def base_layout(fig: go.Figure, height: int = 360) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=8, t=30, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        font=dict(size=13),
    )
    fig.update_xaxes(showgrid=False, linecolor=GRID)
    fig.update_yaxes(gridcolor=GRID, zeroline=False)
    return fig


def quote_note(q: dict) -> str:
    return f"As of {q['time']:%b %d, %I:%M %p} ET"


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


def add_stock(ticker: str) -> None:
    wl = get_watchlist()
    if ticker not in wl and len(wl) < MAX_WATCHLIST:
        save_watchlist(wl + [ticker])
    st.session_state.search_box = ""


def render_sidebar(wl: list[str]) -> None:
    with st.sidebar:
        st.title("📈 Market Brief")
        st.radio("Navigate", PAGES, key="page", label_visibility="collapsed")
        st.divider()
        st.subheader("My watchlist")
        for t in wl:
            c1, c2 = st.columns([4, 1])
            c1.button(t, key=f"open_{t}", on_click=open_stock, args=(t,))
            c2.button("✕", key=f"rm_{t}", on_click=remove_stock, args=(t,), help=f"Remove {t}",
                      disabled=len(wl) == 1)

        if len(wl) < MAX_WATCHLIST:
            q = st.text_input("Add a stock", key="search_box", placeholder="Search by name or ticker")
            if q.strip():
                try:
                    results = data.search_symbols(q.strip())
                except Exception as exc:
                    results = []
                    st.caption(f"Search unavailable: {exc}")
                if results:
                    choice = st.selectbox(
                        "Results", results, format_func=lambda r: f"{r['symbol']} — {r['description']}"
                    )
                    st.button("Add to watchlist", type="primary", on_click=add_stock, args=(choice["symbol"],))
                else:
                    st.caption("No US-listed stocks found for that search.")
        else:
            st.caption(f"Up to {MAX_WATCHLIST} stocks. Remove one to add another.")
        st.caption("Your list lives in this page's link. Bookmark it to keep it.")
        st.divider()
        st.caption("For education only. Not investment advice.")


# =========================================================================== Today
STRIP = [
    ("S&P 500 · SPY", "SPY"),
    ("Nasdaq 100 · QQQ", "QQQ"),
    ("Dow Jones · DIA", "DIA"),
    ("Russell 2000 · IWM", "IWM"),
    ("Gold · GLD", "GLD"),
    ("Oil · USO", "USO"),
]


def market_tiles() -> list[dict]:
    tiles = []
    for label, sym in STRIP:
        try:
            q = data.quote(sym)
            delta = f"{q['pct']:+.2f}%" if q["pct"] is not None else None
            tiles.append({"label": label, "value": f"${q['price']:,.2f}", "delta": delta, "note": quote_note(q),
                          "text": f"{label}: ${q['price']:,.2f}" + (f" ({delta} today)" if delta else "")})
        except Exception:
            tiles.append({"label": label, "value": "—", "delta": None, "note": "Unavailable", "text": ""})
    try:
        b = data.bitcoin()
        tiles.append({"label": "Bitcoin", "value": f"${b['price']:,.0f}",
                      "delta": f"{b['pct']:+.2f}% 24h" if b["pct"] is not None else None,
                      "note": f"As of {b['time']:%b %d, %I:%M %p} ET" if b["time"] else "",
                      "text": f"Bitcoin: ${b['price']:,.0f} ({b['pct']:+.2f}% in 24h)"})
    except Exception:
        tiles.append({"label": "Bitcoin", "value": "—", "delta": None, "note": "Unavailable", "text": ""})
    try:
        fx = data.fx_quote("USD/MXN")
        tiles.append({"label": "USD / MXN", "value": f"{fx['price']:,.4f}", "delta": f"{fx['pct']:+.2f}%",
                      "note": f"As of {fx['time']}", "text": f"USD/MXN: {fx['price']:.4f} ({fx['pct']:+.2f}%)"})
    except Exception:
        tiles.append({"label": "USD / MXN", "value": "—", "delta": None, "note": "Unavailable", "text": ""})
    try:
        t = data.fred_latest("DGS10")
        bps = (t["value"] - t["prev"]) * 100
        tiles.append({"label": "US 10Y Treasury", "value": f"{t['value']:.2f}%", "delta": f"{bps:+.0f} bps",
                      "delta_color": "inverse", "note": f"Daily close, {t['date']} (FRED)",
                      "text": f"US 10-year Treasury yield: {t['value']:.2f}% ({bps:+.0f} bps vs prior day, {t['date']})"})
    except Exception:
        tiles.append({"label": "US 10Y Treasury", "value": "—", "delta": None, "note": "Unavailable", "text": ""})
    return tiles


def render_market_status() -> None:
    try:
        s = data.market_status()
        if s.get("isOpen"):
            st.success("US market is open. Stock and ETF quotes refresh every minute.", icon="🟢")
        else:
            session = s.get("session")
            label = {"pre-market": "in pre-market", "post-market": "in after-hours"}.get(session or "", "closed")
            holiday = f" for {s['holiday']}" if s.get("holiday") else ""
            st.info(f"US market is {label}{holiday}. Prices are the latest available, usually the last close.", icon="🌙")
    except Exception:
        st.caption("Market status unavailable right now.")


def page_today() -> None:
    now = dt.datetime.now(data.ET)
    st.title("Today in the markets")
    st.caption(f"{now:%A, %B %d, %Y · %I:%M %p} ET")
    render_market_status()

    st.subheader("Market snapshot")
    tiles = market_tiles()
    for row in range(0, len(tiles), 3):
        cols = st.columns(3)
        for col, t in zip(cols, tiles[row:row + 3]):
            with col:
                st.metric(t["label"], t["value"], t["delta"], delta_color=t.get("delta_color", "normal"), border=True)
                st.caption(t["note"])
    st.caption("Index levels are shown through the ETFs that track them (SPY, QQQ, DIA, IWM); gold and oil through GLD and USO.")

    st.divider()
    headlines, failed = data.todays_headlines()
    st.subheader("Daily brief")
    if not headlines:
        st.warning("No recent headlines could be loaded. Check the data sources below and try again later.")
    else:
        snapshot = "\n".join(t["text"] for t in tiles if t["text"])
        slot = f"{now:%Y-%m-%d}-{now.hour // 6}"
        try:
            with st.spinner("Writing today's brief…"):
                brief = ai.daily_brief(slot, snapshot, headlines)
            st.markdown(md(brief["market_summary"]))
            for i, s in enumerate(brief["stories"], 1):
                with st.container(border=True):
                    st.markdown(f"#### {i}. {md(s['headline'])}")
                    st.markdown(f"**What happened.** {md(s['what_happened'])}")
                    st.markdown(f"**Why it matters.** {md(s['why_it_matters'])}")
                    st.markdown(f"**What to watch.** {md(s['what_to_watch'])}")
                    if s["sources"]:
                        st.caption(" · ".join(
                            f"[{md(h['source'])}]({h['url']}) {h['time']:%b %d %I:%M %p}" for h in s["sources"]
                        ))
            st.caption(
                f"AI summary written at {brief['generated_at']:%I:%M %p} ET from {brief['n_headlines']} headlines, "
                "using only those headlines and the snapshot above. Check the linked sources before relying on it."
            )
        except Exception as exc:
            st.warning(f"The AI brief isn't available right now ({exc}). The latest headlines are below.")

    st.subheader("Latest headlines")
    for h in headlines[:25]:
        st.markdown(f"- [{md(h['title'])}]({h['url']})  \n  <small>{md(h['source'])} · {h['time']:%b %d, %I:%M %p} ET</small>",
                    unsafe_allow_html=True)
    if failed:
        st.caption("Sources that didn't respond this time: " + ", ".join(failed))


# =========================================================================== Watchlist
def sparkline(close: pd.Series) -> go.Figure:
    color = UP if close.iloc[-1] >= close.iloc[0] else DOWN
    fig = go.Figure(go.Scatter(x=close.index, y=close.values, mode="lines", line=dict(color=color, width=2),
                               hovertemplate="%{x|%b %d}: $%{y:,.2f}<extra></extra>"))
    fig.update_layout(height=80, margin=dict(l=0, r=0, t=4, b=4), showlegend=False,
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      xaxis=dict(visible=False), yaxis=dict(visible=False))
    return fig


def page_watchlist(wl: list[str]) -> None:
    st.title("My watchlist")
    st.caption("Quotes refresh every minute while the market is open. Charts use daily closes (6 months).")
    for t in wl:
        with st.container(border=True):
            c1, c2, c3, c4 = st.columns([2.2, 1.6, 3, 1.4], vertical_alignment="center")
            try:
                p = data.profile(t)
            except Exception:
                p = {"name": t, "industry": ""}
            c1.markdown(f"**{t}**  \n{md(p['name'])}  \n<small>{md(p['industry'])}</small>", unsafe_allow_html=True)

            try:
                q = data.quote(t)
                c2.metric("Price", f"${q['price']:,.2f}", f"{q['pct']:+.2f}%" if q["pct"] is not None else None)
                c2.caption(quote_note(q))
            except Exception:
                c2.metric("Price", "—")
                c2.caption("Quote unavailable")

            try:
                hist = data.history(t)
                close = hist["close"]
                c3.plotly_chart(sparkline(close.iloc[-126:]), config={"displayModeBar": False}, key=f"spark_{t}")
                c3.caption(f"6M {pct(analysis.period_return(close, 126))} · 1Y {pct(analysis.period_return(close, 252))} · "
                           f"Volatility {pct(analysis.annual_volatility(close), signed=False)}")
            except Exception as exc:
                c3.caption(f"Chart unavailable: {exc}")

            c4.button("Analyze →", key=f"analyze_{t}", on_click=open_stock, args=(t,), type="primary")
            try:
                e = data.next_earnings(t)
                if e:
                    c4.caption(f"Earnings {e['date']}")
            except Exception:
                pass


# =========================================================================== Stock analysis
def price_chart(close: pd.Series, vol: float | None, lookback: int) -> go.Figure:
    c = close.iloc[-lookback:]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=c.index, y=c.values, mode="lines", name="Price", line=dict(color=BLUE, width=2),
                             hovertemplate="$%{y:,.2f}<extra>Price</extra>"))
    if vol:
        last_date, last = c.index[-1], c.iloc[-1]
        future = pd.bdate_range(last_date, periods=64)
        days = np.arange(len(future))
        sig = vol * np.sqrt(days / analysis.TRADING_DAYS)
        upper, lower = last * np.exp(sig), last * np.exp(-sig)
        fig.add_trace(go.Scatter(x=future, y=upper, mode="lines", line=dict(color=BLUE, width=1, dash="dot"),
                                 name="Statistical range (±1σ)", hovertemplate="$%{y:,.2f}<extra>Upper</extra>"))
        fig.add_trace(go.Scatter(x=future, y=lower, mode="lines", line=dict(color=BLUE, width=1, dash="dot"),
                                 fill="tonexty", fillcolor="rgba(42,120,214,0.12)", showlegend=False,
                                 hovertemplate="$%{y:,.2f}<extra>Lower</extra>"))
    fig.update_yaxes(tickprefix="$")
    return base_layout(fig, 400)


def fundamentals_chart(f: dict) -> go.Figure:
    rev, fcf = f["revenue"], f["fcf"]
    years = sorted(set(rev.index) | set(fcf.index))[-8:]
    fig = go.Figure()
    to_b = lambda s: [s.get(y) / 1e9 if s.get(y) is not None else None for y in years]  # noqa: E731
    fig.add_trace(go.Bar(x=[str(y) for y in years], y=to_b(rev), name="Revenue", marker_color=BLUE,
                         hovertemplate="$%{y:,.1f}B<extra>Revenue</extra>"))
    fig.add_trace(go.Bar(x=[str(y) for y in years], y=to_b(fcf), name="Free cash flow",
                         marker_color=ORANGE, hovertemplate="$%{y:,.1f}B<extra>Free cash flow</extra>"))
    fig.update_layout(barmode="group", bargap=0.3, bargroupgap=0.08)
    fig.update_yaxes(tickprefix="$", ticksuffix="B")
    fig.update_traces(marker_cornerradius=4)
    return base_layout(fig, 320)


def scenario_chart(values: dict, price: float) -> go.Figure:
    names = list(values)
    colors = [DOWN, BLUE, UP]
    fig = go.Figure(go.Bar(x=names, y=[values[n] for n in names], marker_color=colors, marker_cornerradius=4,
                           text=[f"${values[n]:,.0f}" for n in names], textposition="outside",
                           hovertemplate="%{x}: $%{y:,.2f}<extra></extra>"))
    fig.add_hline(y=price, line_dash="dash", line_color="gray",
                  annotation_text=f"Market price ${price:,.2f}", annotation_position="top left")
    fig.update_yaxes(tickprefix="$", rangemode="tozero")
    fig.update_layout(bargap=0.45, hovermode="closest", showlegend=False)
    return base_layout(fig, 340)


def page_stock(wl: list[str]) -> None:
    current = st.session_state.get("ticker")
    options = wl + ([current] if current and current not in wl else [])
    ticker = st.selectbox("Stock", options, index=options.index(current) if current in options else 0)
    st.session_state.ticker = ticker

    try:
        p = data.profile(ticker)
    except Exception:
        p = {"name": ticker, "industry": ""}
    try:
        q = data.quote(ticker)
    except Exception as exc:
        st.error(f"Couldn't load a quote for {ticker}: {exc}")
        return

    h1, h2 = st.columns([3, 1.4], vertical_alignment="bottom")
    h1.title(f"{p['name']} ({ticker})")
    h1.caption(p["industry"])
    h2.metric("Last price", f"${q['price']:,.2f}", f"{q['pct']:+.2f}%" if q["pct"] is not None else None)
    h2.caption(quote_note(q))

    rf, rf_label = data.risk_free_rate()
    try:
        close = data.history(ticker)["close"]
    except Exception as exc:
        st.error(f"Price history unavailable: {exc}")
        return
    try:
        bench = data.history(BENCHMARK)["close"]
    except Exception:
        bench = None
    m = analysis.risk_metrics(close, bench, rf)

    tab_overview, tab_val, tab_news, tab_ai = st.tabs(["Overview", "Valuation (DCF)", "News", "AI take"])

    with tab_overview:
        render_overview(ticker, q, close, m, rf_label)
    with tab_val:
        val = render_valuation(ticker, q["price"], m, rf, rf_label)
    with tab_news:
        news = render_news(ticker)
    with tab_ai:
        render_ai_take(ticker, p["name"], q, m, val, news)


def render_overview(ticker: str, q: dict, close: pd.Series, m: dict, rf_label: str) -> None:
    span = st.segmented_control("Period", ["3M", "6M", "1Y", "2Y"], default="1Y", key=f"span_{ticker}") or "1Y"
    lookback = {"3M": 63, "6M": 126, "1Y": 252, "2Y": 520}[span]
    st.plotly_chart(price_chart(close, m["volatility"], lookback), key=f"price_{ticker}")

    cols = st.columns(4)
    cols[0].metric("1 month", pct(m["ret_1m"]))
    cols[1].metric("3 months", pct(m["ret_3m"]))
    cols[2].metric("Year to date", pct(m["ret_ytd"]))
    cols[3].metric("1 year", pct(m["ret_1y"]))
    cols = st.columns(4)
    cols[0].metric("Volatility (1Y, annualized)", pct(m["volatility"], signed=False))
    cols[1].metric("Max drawdown (1Y)", pct(m["max_drawdown"]))
    cols[2].metric(f"Beta vs {BENCHMARK} (1Y)", num(m["beta"]))
    cols[3].metric("Sharpe ratio (1Y)", num(m["sharpe"]))
    st.caption(f"Risk-free rate: {rf_label}. Based on daily closes from Twelve Data.")

    if m["volatility"]:
        lo1, hi1 = analysis.statistical_range(q["price"], m["volatility"], 21)
        lo3, hi3 = analysis.statistical_range(q["price"], m["volatility"], 63)
        with st.container(border=True):
            st.markdown("**Statistical range, not a forecast**")
            st.markdown(md(
                f"If {ticker} keeps moving with the same volatility as the last year ({pct(m['volatility'], signed=False)} "
                f"a year), about 2 in 3 outcomes would land between **${lo1:,.2f} and ${hi1:,.2f} in one month**, and "
                f"between **${lo3:,.2f} and ${hi3:,.2f} in three months**. It says how much the stock tends to move, "
                "not which way. It assumes normally distributed log returns, which understates big shocks."
            ))
    try:
        e = data.next_earnings(ticker)
        if e:
            est = f", consensus EPS estimate ${e['eps_estimate']:.2f}" if e.get("eps_estimate") is not None else ""
            st.info(f"Next earnings report: {e['date']} {e['timing']}{est}.", icon="🗓️")
    except Exception:
        pass


def render_valuation(ticker: str, price: float, m: dict, rf: float, rf_label: str) -> dict | None:
    try:
        with st.spinner("Reading SEC filings…"):
            f = fundamentals.build(data.sec_facts(ticker))
    except Exception as exc:
        st.warning(f"Valuation isn't available for {ticker}: {exc}")
        return None
    if f["fcf"].empty or not f["shares"]:
        st.warning("Not enough reported data (free cash flow or share count) to run a DCF for this company.")
        return None

    shares = f["shares"]
    mcap = price * shares
    last_year = int(f["fcf"].index[-1])
    last_fcf = float(f["fcf"].iloc[-1])
    eps = float(f["eps"].iloc[-1]) if not f["eps"].empty else None

    st.subheader("Reported fundamentals")
    st.caption(f"From SEC 10-K filings (XBRL), calendar-aligned fiscal years. Balance sheet as of {f['balance_sheet_date']}.")
    st.plotly_chart(fundamentals_chart(f), key=f"fund_{ticker}")
    cols = st.columns(5)
    cols[0].metric("Market cap", money(mcap))
    cols[1].metric(f"P/E (FY{last_year})", num(price / eps, 1) + "x" if eps and eps > 0 else "n/m")
    cols[2].metric(f"P/FCF (FY{last_year})", num(mcap / last_fcf, 1) + "x" if last_fcf > 0 else "n/m")
    cols[3].metric("FCF yield", pct(last_fcf / mcap, signed=False) if last_fcf > 0 else "n/m")
    cols[4].metric("Net debt", money(f["net_debt"]))
    for note in f["notes"]:
        st.caption(f"⚠️ {note}")

    st.divider()
    st.subheader("Discounted cash flow")
    st.caption("Move the assumptions and the intrinsic value updates. Defaults come from the data; they are a starting point, not a view.")

    hist_g = fundamentals.revenue_cagr(f["revenue"])
    default_g = float(np.clip(hist_g if hist_g is not None else 0.05, 0.0, 0.20))
    beta_used = float(np.clip(m["beta"], 0.5, 2.5)) if m["beta"] else 1.0

    with st.expander("Assumptions", expanded=True):
        a1, a2, a3 = st.columns(3)
        base_choice = a1.radio("Starting free cash flow", ["Latest year", "3-year average"], key=f"base_{ticker}",
                               horizontal=True)
        base_fcf = last_fcf if base_choice == "Latest year" else float(f["fcf"].iloc[-3:].mean())
        a1.caption(f"Starting FCF: {money(base_fcf)}")
        growth = a2.slider("FCF growth, years 1-5 (%)", -10.0, 40.0, round(default_g * 100, 1), 0.5,
                           key=f"g_{ticker}") / 100
        a2.caption(f"Default = revenue CAGR {pct(hist_g) if hist_g is not None else 'n/a'}, capped at 0-20%. "
                   "Years 6-10 fade to terminal growth.")
        g_term = a3.slider("Terminal growth (%)", 0.0, 4.0, 2.5, 0.1, key=f"gt_{ticker}") / 100
        a3.caption("Long-run growth after year 10. Should stay near long-run GDP/inflation.")

        b1, b2, b3, b4 = st.columns(4)
        erp = b1.number_input("Equity risk premium (%)", 3.0, 8.0, 5.0, 0.25, key=f"erp_{ticker}") / 100
        beta_in = b2.number_input("Beta", 0.3, 3.0, round(beta_used, 2), 0.05, key=f"beta_{ticker}")
        kd = b3.number_input("Pre-tax cost of debt (%)", 1.0, 12.0, round((rf + 0.015) * 100, 2), 0.25,
                             key=f"kd_{ticker}") / 100
        tax = b4.number_input("Tax rate (%)", 0.0, 35.0, 21.0, 1.0, key=f"tax_{ticker}") / 100
        w = analysis.wacc(rf, beta_in, erp, kd, tax, mcap, f["debt"])
        st.caption(
            f"Cost of equity (CAPM) = {pct(rf, 2, False)} + {beta_in:.2f} × {pct(erp, 2, False)} = "
            f"{pct(w['cost_of_equity'], 2, False)} · Weights: equity {pct(w['we'], 0, False)}, debt {pct(w['wd'], 0, False)} "
            f"· WACC = {pct(w['wacc'], 2, False)}. {rf_label}."
        )
        discount = st.slider("Discount rate used (WACC, %)", 4.0, 16.0, round(w["wacc"] * 100, 1), 0.1,
                             key=f"wacc_{ticker}_{round(w['wacc'] * 100, 1)}") / 100

    if base_fcf <= 0:
        st.warning("Starting free cash flow is negative, so a cash-flow DCF isn't meaningful for this company. "
                   "Look at revenue growth and the path to profitability instead.")
        return {"fundamentals": f, "mcap": mcap, "eps": eps, "last_fcf": last_fcf, "last_year": last_year}

    try:
        base = analysis.dcf(base_fcf, growth, g_term, discount, f["net_debt"], shares)
        bear = analysis.dcf(base_fcf, max(growth - 0.05, -0.10), g_term, discount + 0.01, f["net_debt"], shares)
        bull = analysis.dcf(base_fcf, growth + 0.05, g_term, max(discount - 0.01, g_term + 0.006), f["net_debt"], shares)
    except ValueError as exc:
        st.error(str(exc))
        return None

    label, gap = analysis.verdict(base.per_share, price)
    implied = analysis.implied_growth(price, base_fcf, g_term, discount, f["net_debt"], shares)

    r1, r2, r3 = st.columns(3)
    r1.metric("Intrinsic value per share (base)", f"${base.per_share:,.2f}")
    r2.metric("Market price", f"${price:,.2f}")
    r3.metric("Upside / downside", pct(gap), label, delta_color="off")
    if label == "Looks undervalued":
        st.success(f"Under these assumptions the stock trades {pct(gap / (1 + gap), 0, False)} below its estimated value.", icon="📉")
    elif label == "Looks overvalued":
        st.error(f"Under these assumptions the market price is {pct(1 / (1 + gap) - 1, 0, False)} above the estimated value.", icon="📈")
    else:
        st.info("Under these assumptions the price is within ±15% of the estimated value.", icon="⚖️")

    if implied is not None:
        st.markdown(md(
            f"**Reverse DCF.** To justify today's ${price:,.2f}, free cash flow would need to grow about "
            f"**{pct(implied)} a year for five years** (then fade to {pct(g_term, 1, False)}), with a "
            f"{pct(discount, 1, False)} discount rate. Compare that with the {pct(hist_g) if hist_g is not None else 'n/a'} "
            "revenue growth of the last five years."
        ))

    st.plotly_chart(scenario_chart({"Bear": bear.per_share, "Base": base.per_share, "Bull": bull.per_share}, price),
                    key=f"scen_{ticker}")
    st.caption("Bear: growth −5 pts and discount rate +1 pt. Bull: growth +5 pts and discount rate −1 pt.")

    st.markdown("**Sensitivity: intrinsic value per share**")
    rates = [round(discount + d, 4) for d in (-0.02, -0.01, 0.0, 0.01, 0.02)]
    terms = [round(g_term + d, 4) for d in (-0.01, -0.005, 0.0, 0.005, 0.01)]
    sens = analysis.sensitivity(base_fcf, growth, f["net_debt"], shares, rates, terms)
    sens.index = [pct(r, 1, False) for r in sens.index]
    sens.columns = [pct(g, 1, False) for g in sens.columns]
    st.dataframe(sens.style.format("${:,.0f}", na_rep="n/m"))
    st.caption("Rows: discount rate. Columns: terminal growth.")

    with st.expander("DCF detail"):
        proj = base.projections.copy()
        proj["Growth"] = proj["Growth"].map(lambda x: pct(x))
        for c in ("FCF", "PV of FCF"):
            proj[c] = proj[c].map(money)
        proj["Discount factor"] = proj["Discount factor"].map(lambda x: f"{x:.3f}")
        st.dataframe(proj, hide_index=True)
        st.markdown(md(
            f"Sum of discounted FCF {money(base.pv_fcf)} + discounted terminal value {money(base.pv_terminal)} "
            f"= enterprise value {money(base.enterprise_value)}. Minus net debt {money(f['net_debt'])} = equity value "
            f"{money(base.equity_value)}, divided by {shares / 1e9:,.2f}B shares ({f['shares_source']}) = "
            f"${base.per_share:,.2f} per share. The terminal value is {pct(base.terminal_share, 0, False)} of enterprise value."
        ))
    st.caption("A DCF is only as good as its assumptions. It doesn't fit banks, insurers or companies with negative cash flow.")

    return {"fundamentals": f, "mcap": mcap, "eps": eps, "last_fcf": last_fcf, "last_year": last_year,
            "base": base.per_share, "bear": bear.per_share, "bull": bull.per_share, "growth": growth,
            "g_term": g_term, "discount": discount, "implied": implied, "label": label, "gap": gap}


def render_news(ticker: str) -> list[dict]:
    try:
        news = data.company_news(ticker)
    except Exception as exc:
        st.warning(f"Company news unavailable: {exc}")
        return []
    if not news:
        st.info("No company news in the last 7 days.")
    for n in news:
        with st.container(border=True):
            st.markdown(f"**[{md(n['title'])}]({n['url']})**")
            if n["summary"]:
                st.markdown(md(n["summary"]))
            st.caption(f"{n['source']} · {n['time']:%b %d, %I:%M %p} ET" if n["time"] else n["source"])
    return news


def ai_data_text(ticker: str, q: dict, m: dict, val: dict | None) -> str:
    lines = [
        f"Price ${q['price']:,.2f} ({q['pct']:+.2f}% today), quote time {q['time']:%Y-%m-%d %H:%M} ET",
        f"Returns: 1M {pct(m['ret_1m'])}, 3M {pct(m['ret_3m'])}, YTD {pct(m['ret_ytd'])}, 1Y {pct(m['ret_1y'])}",
        f"Risk (1Y): volatility {pct(m['volatility'], signed=False)}, max drawdown {pct(m['max_drawdown'])}, "
        f"beta vs SPY {num(m['beta'])}, Sharpe {num(m['sharpe'])}",
    ]
    if val:
        f = val["fundamentals"]
        rev = "; ".join(f"FY{y}: {money(v)}" for y, v in f["revenue"].iloc[-5:].items())
        fcf = "; ".join(f"FY{y}: {money(v)}" for y, v in f["fcf"].iloc[-5:].items())
        lines += [f"Revenue: {rev}", f"Free cash flow: {fcf}",
                  f"Market cap {money(val['mcap'])}, net debt {money(f['net_debt'])}"]
        if val.get("eps") and val["eps"] > 0:
            lines.append(f"P/E on FY{val['last_year']} EPS: {q['price'] / val['eps']:.1f}x")
        if val.get("base"):
            lines.append(
                f"DCF (FCF growth {pct(val['growth'])} for 5 years, terminal {pct(val['g_term'])}, discount rate "
                f"{pct(val['discount'], 1, False)}): base ${val['base']:,.2f}, bear ${val['bear']:,.2f}, bull "
                f"${val['bull']:,.2f} per share -> {val['label']} ({pct(val['gap'])} vs price)"
            )
            if val.get("implied") is not None:
                lines.append(f"Reverse DCF: price implies ~{pct(val['implied'])} annual FCF growth for 5 years")
    try:
        e = data.next_earnings(ticker)
        if e:
            lines.append(f"Next earnings date: {e['date']} {e['timing']}")
    except Exception:
        pass
    return "\n".join(lines)


def render_ai_take(ticker: str, name: str, q: dict, m: dict, val: dict | None, news: list[dict]) -> None:
    st.caption("An AI-written read of the numbers and news on the other tabs. It may only use that data. "
               "It is an interpretation, not investment advice.")
    key = f"take_{ticker}"
    if st.button("Generate AI take", type="primary", key=f"btn_{key}"):
        try:
            with st.spinner("Writing the analysis…"):
                st.session_state[key] = ai.stock_take(ticker, name, dt.date.today().isoformat(),
                                                      ai_data_text(ticker, q, m, val), news)
        except Exception as exc:
            st.warning(f"AI take unavailable right now: {exc}")
    take = st.session_state.get(key)
    if not take:
        return
    sections = [("Current situation", "situation"), ("Recent performance", "recent_performance"),
                ("Fundamentals", "fundamentals"), ("Valuation", "valuation"), ("Recent news", "news")]
    for title, k in sections:
        if take.get(k):
            st.markdown(f"**{title}.** {md(take[k])}")
    c1, c2, c3 = st.columns(3)
    for col, title, k in ((c1, "🐻 Bear case", "bear_case"), (c2, "⚖️ Base case", "base_case"), (c3, "🐂 Bull case", "bull_case")):
        with col.container(border=True):
            st.markdown(f"**{title}**")
            st.markdown(md(take.get(k, "")))
    c1, c2 = st.columns(2)
    c1.markdown("**Main risks**\n" + "\n".join(f"- {md(r)}" for r in take.get("risks", [])))
    c2.markdown("**Upcoming catalysts**\n" + "\n".join(f"- {md(c)}" for c in take.get("catalysts", [])))
    st.markdown(f"**Conclusion.** {md(take.get('conclusion', ''))}")
    st.caption(f"Written {take['generated_at']:%b %d, %I:%M %p} ET.")


# =========================================================================== Methodology
def page_methodology() -> None:
    st.title("How this works")
    st.markdown(md("""
**What it is.** A personal markets dashboard: a daily AI-written brief, a 5-stock watchlist, and a one-page
analysis per stock with risk metrics and a discounted cash flow valuation.

**Data sources (all free tiers)**

| What | Source | Freshness |
|---|---|---|
| Stock and ETF quotes | Finnhub | Latest available, refreshed every minute |
| Daily price history | Twelve Data | Daily closes, refreshed every 6 hours |
| Financial statements | SEC EDGAR (XBRL company facts) | As reported in 10-K / 10-Q filings |
| 10-year Treasury yield | FRED (St. Louis Fed) | Daily, previous business day |
| Bitcoin / USD-MXN | CoinGecko / Twelve Data | About every 10-15 minutes |
| Headlines | CNBC, MarketWatch, WSJ Markets, Federal Reserve (RSS), Finnhub | Every 30 minutes |

Indices are shown through their ETFs (SPY, QQQ, DIA, IWM), and gold and oil through GLD and USO, because
index and futures levels aren't available on free data plans. Every number shows when it was last updated.

**Risk metrics.** Returns use daily closes. Volatility is the annualized standard deviation of daily log returns
over the last year. Beta is the slope of the stock's daily returns on SPY's. Sharpe = (1-year return − 10-year
Treasury yield) / volatility. Max drawdown is the worst peak-to-trough fall in the last year.

**Statistical range.** A one-standard-deviation band, price × exp(±σ√t), from the last year's volatility.
Under a normal model of log returns about two thirds of outcomes fall inside it. It describes how much a stock
moves, not where it is going, and it understates big shocks.

**DCF.** Free cash flow = operating cash flow − capital expenditures, from SEC filings. Cash flow grows at the
chosen rate for five years, fades in a straight line to terminal growth over the next five, and a Gordon growth
terminal value is added in year 10. Everything is discounted at WACC, where the cost of equity comes from CAPM
(10-year Treasury + beta × equity risk premium) and the weights from market cap and reported debt. Equity value =
enterprise value − net debt; dividing by shares outstanding gives intrinsic value per share. The **reverse DCF**
solves for the growth rate that makes intrinsic value equal the market price, which shows what the market is
pricing in.

**AI.** Google Gemini writes the daily brief and the per-stock take. It receives only the headlines and numbers
shown in the app and is told not to add facts, make recommendations or set price targets. Each brief links
back to its source articles.

**Limits.** Free data can be delayed or briefly unavailable. SEC tag coverage varies by company, so check the
10-K when a number looks off. Nothing here is investment advice.
"""))


# =========================================================================== main
if "page" not in st.session_state:
    st.session_state.page = "Today"
watchlist = get_watchlist()
render_sidebar(watchlist)

page = st.session_state.page
if page == "Today":
    page_today()
elif page == "Watchlist":
    page_watchlist(watchlist)
elif page == "Stock analysis":
    page_stock(watchlist)
else:
    page_methodology()
