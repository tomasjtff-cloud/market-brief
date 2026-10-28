"""The stock page, laid out like a quote page: header, then sections for summary, chart, financials,
valuation, outlook, comparison, news and the AI analysis."""
from __future__ import annotations

import datetime as dt
import hashlib

import numpy as np
import pandas as pd
import streamlit as st

import ai
import analysis
import charts
import data
import fundamentals
from common import (BENCHMARK, MAX_WATCHLIST, add_to_watchlist, big, get_watchlist, isnum, money, num, pct,
                    remove_from_watchlist, safe, when)
from ui import P, chip, esc, link, sgn, signed_class, src

SECTIONS = ["Summary", "Chart", "Financials", "Valuation", "Outlook", "Compare", "News", "Analysts & AI take"]
RANGES = ["1D", "5D", "1M", "6M", "YTD", "1Y", "5Y"]


# =========================================================================== helpers
def window(hist: pd.DataFrame, rng: str) -> pd.DataFrame:
    if rng == "YTD":
        return hist[hist.index >= pd.Timestamp(dt.date(hist.index[-1].year, 1, 1))]
    n = {"1M": 21, "6M": 126, "1Y": 252, "5Y": len(hist)}[rng]
    return hist.iloc[-(n + 1):]


def chart_block(t: str, hist: pd.DataFrame, q: dict, key: str, height: int, indicators: tuple = (), cone: float | None = None,
                default_range: str = "1Y") -> None:
    c1, c2 = st.columns([3, 1.2], vertical_alignment="center")
    rng = c1.segmented_control("Range", RANGES, default=default_range, key=f"{key}_rng_{t}", label_visibility="collapsed") or default_range
    kind = c2.segmented_control("Type", ["Area", "Candles"], default="Area", key=f"{key}_kind_{t}", label_visibility="collapsed") or "Area"
    intraday = rng in ("1D", "5D")
    if intraday:
        interval, size, days = ("5min", 80, 1) if rng == "1D" else ("30min", 70, 5)
        df = safe(data.intraday, t, interval, size)
        if df is None or df.empty:
            st.caption("Intraday bars aren't available right now; showing one month instead.")
            intraday, df = False, window(hist, "1M")
        else:
            dates = sorted(set(df.index.date))[-days:]
            df = df[np.isin(df.index.date, dates)]
    else:
        df = window(hist, rng)
    mas = tuple(n for n in (50, 200) if f"{n}-day" in indicators) if not intraday else ()
    fig = charts.price_chart(df, kind="candles" if kind == "Candles" else "area", intraday=intraday,
                             prev_close=q.get("prev_close") if rng == "1D" else None, mas=mas,
                             bollinger="Bollinger" in indicators and not intraday, show_rsi="RSI" in indicators,
                             full=None if intraday else hist, height=height, cone_vol=cone if not intraday else None)
    st.plotly_chart(fig, config=charts.CONFIG, key=f"{key}_fig_{t}")
    if len(df) > 1:
        ref = q.get("prev_close") if rng == "1D" and q.get("prev_close") else float(df["close"].iloc[0])
        ch = float(df["close"].iloc[-1]) / ref - 1
        st.html(f'<p class="mb-foot">{rng} change <b class="{signed_class(ch)}">{pct(ch, 2)}</b> · '
                f'{"5-minute" if rng == "1D" else "30-minute" if rng == "5D" else "daily"} bars from Twelve Data {src("mkt")}</p>')


def kv(rows: list[tuple[str, str]]) -> str:
    return '<div class="mb-kv">' + "".join(f"<div><span>{esc(k)}</span><span>{v}</span></div>" for k, v in rows) + "</div>"


@st.cache_data(ttl=3600, show_spinner=False)
def outlook_for(ticker: str, drift: str, last_close: float, high52: float | None, target: float | None) -> dict | None:
    close = data.history(ticker)["close"]
    seed = int(hashlib.md5(f"{ticker}{drift}{close.index[-1]:%Y%m%d}".encode()).hexdigest()[:8], 16)
    paths = analysis.bootstrap_paths(close, days=126, n=4000, drift=drift, seed=seed)
    if paths is None:
        return None
    out = analysis.outlook_summary(paths, float(close.iloc[-1]), high52, target)
    out["start"] = float(close.iloc[-1])
    return out


def dcf_defaults(f: dict, m: dict, rf: float, price: float) -> dict:
    hist_g = fundamentals.revenue_cagr(f["revenue"])
    return {"growth": float(np.clip(hist_g if hist_g is not None else 0.05, 0.0, 0.20)), "hist_g": hist_g,
            "beta": float(np.clip(m["beta"], 0.5, 2.5)) if m["beta"] else 1.0}


# =========================================================================== page
def page_stock(wl: list[str]) -> None:
    t = st.session_state.ticker
    q = safe(data.quote, t)
    if not q:
        st.error(f"No quote found for {t}. Check the ticker or search for the company in the top bar.")
        return
    p = safe(data.profile, t, default={"name": t, "industry": "", "logo": "", "exchange": ""}) or {"name": t}
    hist = safe(data.history, t)
    if hist is None or len(hist) < 30:
        st.error(f"Price history for {t} isn't available right now. Try again in a minute.")
        return
    bench = safe(lambda: data.history(BENCHMARK)["close"])
    rf, rf_label = data.risk_free_rate()
    m = analysis.risk_metrics(hist["close"], bench, rf)
    met = safe(data.basic_metrics, t, default={}) or {}
    status = safe(data.market_status, default={}) or {}

    # ---- header
    logo = f'<img class="logo" src="{esc(p.get("logo"))}" alt="">' if p.get("logo") else ""
    cls = signed_class(q["pct"])
    state = "Market open" if status.get("isOpen") else "At close"
    head_l, head_r = st.columns([5, 1.3], vertical_alignment="bottom")
    head_l.html(
        f'<div class="mb-quote"><div class="idt">{logo}<div><div class="co">{esc(p.get("name") or t)}</div>'
        f'<div class="meta"><span class="mb-tag">{esc(t)}</span><span>{esc(p.get("exchange", "")).replace("NASDAQ NMS - GLOBAL MARKET", "Nasdaq")}</span>'
        f'<span>{esc(p.get("industry", ""))}</span><span>USD</span></div></div></div>'
        f'<div><span class="px num">{q["price"]:,.2f}</span><span class="chg num {cls}">{sgn(q["change"] or 0, 2, "")} ({sgn(q["pct"] or 0)})</span>'
        f'<div class="asof">{state} · {when(q["time"])} {src("mkt")}</div></div></div>')
    with head_r:
        if t in wl:
            st.button("✓ In watchlist", key=f"wl_rm_{t}", on_click=remove_from_watchlist, args=(t,), width="stretch",
                      help="Click to remove from the watchlist", disabled=len(wl) == 1)
        elif len(wl) < MAX_WATCHLIST:
            st.button("+ Add to watchlist", key=f"wl_add_{t}", on_click=add_to_watchlist, args=(t,), type="primary", width="stretch")

    high52 = met.get("52WeekHigh") or float(hist["close"].iloc[-252:].max())
    low52 = met.get("52WeekLow") or float(hist["close"].iloc[-252:].min())
    st.html(f'<div class="mb-stats" style="--cols:8">' + "".join(
        f'<div class="mb-stat"><div class="k">{k}</div><div class="v num {c}">{v}</div></div>' for k, v, c in [
            ("Market cap", money(p.get("market_cap"), 2), ""),
            ("P/E (TTM)", num(met.get("peTTM"), 1, "x") if (met.get("peTTM") or 0) > 0 else "n/m", ""),
            ("EPS (TTM)", f'${met["epsTTM"]:,.2f}' if isnum(met.get("epsTTM")) else "n/a", ""),
            ("YTD", pct(m["ret_ytd"]), signed_class(m["ret_ytd"])),
            ("1 year", pct(m["ret_1y"]), signed_class(m["ret_1y"])),
            ("Volatility", pct(m["volatility"], signed=False), ""),
            ("Beta", num(m["beta"]), ""),
            ("52-week range", f"{low52:,.0f} – {high52:,.0f}", ""),
        ]) + "</div>")

    section = st.segmented_control("Section", SECTIONS, default="Summary", key=f"sec_{t}", label_visibility="collapsed") or "Summary"
    st.html('<div style="height:.2rem"></div>')
    ctx = {"t": t, "q": q, "p": p, "hist": hist, "bench": bench, "rf": rf, "rf_label": rf_label, "m": m, "met": met,
           "high52": high52, "low52": low52, "wl": wl}
    {"Summary": summary, "Chart": chart_section, "Financials": financials, "Valuation": valuation, "Outlook": outlook,
     "Compare": compare, "News": news, "Analysts & AI take": analysts_section}[section](ctx)


# =========================================================================== Summary
def summary(c: dict) -> None:
    t, q, hist, met, m = c["t"], c["q"], c["hist"], c["met"], c["m"]
    left, right = st.columns([2.2, 1], gap="medium")
    with left:
        chart_block(t, hist, q, "sum", 400, indicators=("50-day", "200-day"), default_range="1Y")
    with right:
        last_vol = hist["volume"].iloc[-1] if "volume" in hist else None
        avg_vol = hist["volume"].iloc[-63:].mean() if "volume" in hist else None
        e = safe(data.next_earnings, t)
        dy = met.get("currentDividendYieldTTM") or met.get("dividendYieldIndicatedAnnual")
        rows = [
            ("Previous close", f'{q["prev_close"]:,.2f}' if q.get("prev_close") else "n/a"),
            ("Day's range", f'{q["low"]:,.2f} – {q["high"]:,.2f}' if q.get("low") and q.get("high") else "n/a"),
            ("52-week range", f'{c["low52"]:,.2f} – {c["high52"]:,.2f}'),
            ("Volume (last day)", big(last_vol)),
            ("Avg. volume (3M)", big(avg_vol)),
            ("Market cap", money(c["p"].get("market_cap"), 2)),
            ("Beta (2Y weekly)", num(m["beta"])),
            ("P/E (TTM)", num(met.get("peTTM"), 2) if (met.get("peTTM") or 0) > 0 else "n/m"),
            ("EPS (TTM)", f'{met["epsTTM"]:,.2f}' if isnum(met.get("epsTTM")) else "n/a"),
            ("Dividend yield", f"{dy:.2f}%" if isnum(dy) and dy else "None"),
            ("Next earnings", f'{dt.date.fromisoformat(e["date"]):%b %-d, %Y}' if e else "n/a"),
            ("Sharpe (1Y)", num(m["sharpe"])),
        ]
        st.html(f'<div class="mb-panel"><div class="mb-h"><b>Key statistics</b><span>{src("mkt")} {src("calc")}</span></div>'
                + kv(rows).replace('class="mb-kv"', 'class="mb-kv" style="grid-template-columns:1fr"') + "</div>")

    a, b, c3 = st.columns([1.15, 1.15, 1], gap="small")
    with a:
        close = hist["close"]
        bclose = c["bench"]
        rows = ""
        for label, n in (("1 month", 21), ("3 months", 63), ("YTD", None), ("1 year", 252), ("3 years", 756), ("5 years", 1250)):
            if n is None:
                r1, r2 = analysis.ytd_return(close), analysis.ytd_return(bclose) if bclose is not None else None
            else:
                r1 = analysis.period_return(close, n)
                r2 = analysis.period_return(bclose, n) if bclose is not None else None
            if r1 is None:
                continue
            rel = (r1 - r2) if r2 is not None else None
            rows += (f'<tr><td class="l">{label}</td><td class="num {signed_class(r1)}">{pct(r1)}</td>'
                     f'<td class="num {signed_class(r2)}">{pct(r2)}</td><td class="num {signed_class(rel)}">{pct(rel)}</td></tr>')
        st.html(f'<div class="mb-panel"><div class="mb-h"><b>Performance vs S&amp;P 500</b><span>{src("calc")}</span></div>'
                f'<table class="mb-tbl"><tr><th class="l">Period</th><th>{esc(t)}</th><th>SPY</th><th>Difference</th></tr>{rows}</table></div>')
    with b:
        with st.container(key="panel_recs"):
            st.html(f'<div class="mb-h"><b>Analyst ratings</b><span>{src("ana")}</span></div>')
            recs = safe(data.recommendations, t, default=[])
            if recs:
                st.plotly_chart(charts.recommendations(recs), config=charts.CONFIG, key=f"recs_{t}")
                cs = analysis.consensus(recs[0])
                if cs:
                    bulls = (cs["counts"]["strongBuy"] + cs["counts"]["buy"]) / cs["n"]
                    st.html(f'<p class="mb-foot">Consensus <b>{cs["label"]}</b> ({cs["score"]:.2f} / 5) from {cs["n"]} analysts, '
                            f'{bulls:.0%} buy or strong buy ({cs["period"]}). Sell-side ratings lean positive in general.</p>')
            else:
                st.caption("No analyst ratings available.")
    with c3:
        ma50, ma200 = hist["close"].rolling(50).mean().iloc[-1], hist["close"].rolling(200).mean().iloc[-1]
        price = q["price"]
        lv = [("52-week high", c["high52"]), ("50-day average", ma50), ("200-day average", ma200), ("52-week low", c["low52"])]
        rows = "".join(f'<tr><td class="l">{n}</td><td class="num">{v:,.2f}</td><td class="num {signed_class(price / v - 1)}">{pct(price / v - 1)}</td></tr>'
                       for n, v in lv if isnum(v))
        prof = c["p"]
        st.html(f'<div class="mb-panel"><div class="mb-h"><b>Key levels</b><span>{src("calc")}</span></div>'
                f'<table class="mb-tbl"><tr><th class="l">Level</th><th>Price</th><th>Price vs level</th></tr>{rows}</table></div>'
                f'<div class="mb-panel" style="margin-top:.6rem"><div class="mb-h"><b>Profile</b></div>' + kv([
                    ("Industry", esc(prof.get("industry") or "n/a")), ("Country", esc(prof.get("country") or "n/a")),
                    ("Listed since", esc(prof.get("ipo") or "n/a")),
                    ("Website", f'<a href="{esc(prof.get("web"))}" target="_blank" rel="noopener">{esc((prof.get("web") or "").replace("https://", "").replace("http://", "").strip("/"))}</a>' if prof.get("web") else "n/a"),
                ]).replace('class="mb-kv"', 'class="mb-kv" style="grid-template-columns:1fr"') + "</div>")


# =========================================================================== Chart
def chart_section(c: dict) -> None:
    t, hist, q, m = c["t"], c["hist"], c["q"], c["m"]
    ind = st.pills("Indicators", ["50-day", "200-day", "Bollinger", "RSI", "±1σ range ahead"], selection_mode="multi",
                   default=["50-day", "200-day"], key=f"ind_{t}", label_visibility="collapsed") or []
    chart_block(t, hist, q, "big", 600, indicators=tuple(ind), cone=m["volatility"] if "±1σ range ahead" in ind else None)
    a, b = st.columns([1, 1.1], gap="medium")
    with a:
        st.html(f'<div class="mb-sec">How far it usually moves {src("calc")}</div>')
        if m["volatility"]:
            rows = ""
            for label, days in (("1 month", 21), ("3 months", 63), ("6 months", 126)):
                lo1, hi1 = analysis.statistical_range(q["price"], m["volatility"], days)
                s = m["volatility"] * np.sqrt(days / analysis.TRADING_DAYS) * 1.96
                rows += (f'<tr><td class="l">{label}</td><td class="num">{lo1:,.2f} – {hi1:,.2f}</td>'
                         f'<td class="num">{q["price"] * np.exp(-s):,.2f} – {q["price"] * np.exp(s):,.2f}</td></tr>')
            st.html(f'<div class="mb-panel"><table class="mb-tbl"><tr><th class="l">Horizon</th><th>2 in 3 outcomes</th>'
                    f'<th>19 in 20 outcomes</th></tr>{rows}</table></div><p class="mb-foot">Normal model on last year\'s volatility '
                    f'({pct(m["volatility"], signed=False)} a year), no drift. The Outlook section uses real past moves instead.</p>')
        st.html(stats_row([("Max drawdown, 1Y", pct(m["max_drawdown"]), "neg"), ("Sharpe, 1Y", num(m["sharpe"]), ""),
                           ("Beta vs SPY", num(m["beta"]), ""), ("RSI (14)", num(charts.rsi(hist["close"]).iloc[-1], 0), "")]))
    with b:
        st.html(f'<div class="mb-sec">Drawdown, last year {src("calc")}</div>')
        st.plotly_chart(charts.drawdown(hist["close"]), config=charts.CONFIG, key=f"dd_{t}")


def stats_row(items: list[tuple[str, str, str]]) -> str:
    return (f'<div class="mb-stats" style="--cols:{len(items)};margin-top:.6rem">' + "".join(
        f'<div class="mb-stat"><div class="k">{k}</div><div class="v num {cl}">{v}</div></div>' for k, v, cl in items) + "</div>")


# =========================================================================== Financials
def financials(c: dict) -> None:
    t = c["t"]
    with st.spinner("Reading SEC filings…"):
        f = safe(data.company_fundamentals, t)
    if not f or f["revenue"].empty:
        st.info(f"Reported financials aren't available for {t} (non-US filers, ETFs and funds don't file 10-Ks).")
        return
    years = sorted(set(f["revenue"].index) | set(f["fcf"].index))[-6:]
    g = lambda s, y: float(s[y]) if y in s.index else None  # noqa: E731
    def row(label, s, kind="money"):
        cells = []
        for y in years:
            v = g(s, y)
            if kind == "money":
                cells.append(f'<td class="num">{money(v, 1) if v is not None else "n/a"}</td>')
            elif kind == "eps":
                cells.append(f'<td class="num">{f"${v:,.2f}" if v is not None else "n/a"}</td>')
            else:
                cells.append(f'<td class="num {signed_class(v) if kind == "growth" else ""}">{pct(v, 1, kind == "growth") if v is not None else "n/a"}</td>')
        return f'<tr><td class="l">{label}</td>{"".join(cells)}</tr>'

    rev = f["revenue"]
    ratio = lambda a: (a / rev).dropna() if not a.empty else pd.Series(dtype=float)  # noqa: E731
    body = "".join([
        row("Revenue", rev), row("Revenue growth", rev.pct_change(fill_method=None), "growth"),
        row("Gross profit", f["gross_profit"]), row("Operating income", f["operating_income"]), row("Net income", f["net_income"]),
        row("Diluted EPS", f["eps"], "eps"), row("Operating cash flow", f["ocf"]), row("Capital expenditures", f["capex"]),
        row("Free cash flow", f["fcf"]), row("Gross margin", ratio(f["gross_profit"]), "ratio"),
        row("Operating margin", ratio(f["operating_income"]), "ratio"), row("Net margin", ratio(f["net_income"]), "ratio"),
        row("FCF margin", ratio(f["fcf"]), "ratio"),
    ])
    st.html(f'<div class="mb-sec">Annual financials {src("rep")}</div><div class="mb-scroll"><table class="mb-tbl">'
            f'<tr><th class="l">Fiscal year</th>{"".join(f"<th>{y}</th>" for y in years)}</tr>{body}</table></div>'
            f'<p class="mb-foot">From 10-K filings (XBRL), calendar-aligned fiscal years. Balance sheet as of {f["balance_sheet_date"]}: '
            f'cash and short-term investments {money(f["cash"], 1)}, debt {money(f["debt"], 1)}, net debt {money(f["net_debt"], 1)}.</p>')
    for note in f["notes"]:
        st.caption(f"Note: {note}")
    b = lambda s: [g(s, y) / 1e9 if g(s, y) is not None else None for y in years]  # noqa: E731
    a1, a2 = st.columns(2, gap="medium")
    with a1:
        st.html('<div class="mb-sec">Revenue, profit and cash</div>')
        st.plotly_chart(charts.financial_bars(years, [("Revenue", b(rev), "accent"), ("Net income", b(f["net_income"]), "teal"),
                                                      ("Free cash flow", b(f["fcf"]), "orange")]), config=charts.CONFIG, key=f"fin_{t}")
    with a2:
        st.html('<div class="mb-sec">Margins</div>')
        mg = lambda s: [(g(ratio(s), y) or np.nan) * 100 if g(ratio(s), y) is not None else None for y in years]  # noqa: E731
        st.plotly_chart(charts.margin_lines(years, [("Gross", mg(f["gross_profit"]), "accent"), ("Operating", mg(f["operating_income"]), "violet"),
                                                    ("Net", mg(f["net_income"]), "teal"), ("FCF", mg(f["fcf"]), "orange")]),
                        config=charts.CONFIG, key=f"mg_{t}")


# =========================================================================== Valuation
def valuation(c: dict) -> dict | None:
    t, q, m, rf, rf_label, hist = c["t"], c["q"], c["m"], c["rf"], c["rf_label"], c["hist"]
    price = q["price"]
    with st.spinner("Reading SEC filings…"):
        f = safe(data.company_fundamentals, t)
    if not f or f["fcf"].empty or not f["shares"]:
        st.info(f"A DCF isn't available for {t}: it needs SEC filings with free cash flow and a share count "
                "(non-US companies, ETFs and funds aren't covered).")
        return None
    shares, mcap = f["shares"], price * f["shares"]
    last_year, last_fcf = int(f["fcf"].index[-1]), float(f["fcf"].iloc[-1])
    eps = float(f["eps"].iloc[-1]) if not f["eps"].empty else None
    d = dcf_defaults(f, m, rf, price)

    with st.expander("DCF assumptions — change them and everything below updates", expanded=False):
        a1, a2, a3 = st.columns(3)
        base_choice = a1.radio("Starting free cash flow", ["Latest year", "3-year average"], key=f"base_{t}", horizontal=True)
        growth = a2.slider("FCF growth, years 1 to 5 (%)", -10.0, 40.0, round(d["growth"] * 100, 1), 0.5, key=f"g_{t}") / 100
        g_term = a3.slider("Terminal growth (%)", 0.0, 4.0, 2.5, 0.1, key=f"gt_{t}") / 100
        b1, b2, b3, b4 = st.columns(4)
        erp = b1.number_input("Equity risk premium (%)", 3.0, 8.0, 5.0, 0.25, key=f"erp_{t}") / 100
        beta_in = b2.number_input("Beta", 0.3, 3.0, round(d["beta"], 2), 0.05, key=f"beta_{t}")
        kd = b3.number_input("Pre-tax cost of debt (%)", 1.0, 12.0, round((rf + 0.015) * 100, 2), 0.25, key=f"kd_{t}") / 100
        tax = b4.number_input("Tax rate (%)", 0.0, 35.0, 21.0, 1.0, key=f"tax_{t}") / 100
        w = analysis.wacc(rf, beta_in, erp, kd, tax, mcap, f["debt"])
        discount = st.slider("Discount rate used (WACC, %)", 4.0, 16.0, round(w["wacc"] * 100, 1), 0.1,
                             key=f"wacc_{t}_{round(w['wacc'] * 100, 1)}") / 100
        base_fcf = last_fcf if base_choice == "Latest year" else float(f["fcf"].iloc[-3:].mean())
        st.caption(f"Starting FCF {money(base_fcf)}. Default growth = last five years' revenue CAGR "
                   f"({pct(d['hist_g']) if d['hist_g'] is not None else 'n/a'}) capped at 0 to 20%; years 6 to 10 fade to terminal growth. "
                   f"Cost of equity {pct(rf, 2, False)} + {beta_in:.2f} × {pct(erp, 2, False)} = {pct(w['cost_of_equity'], 2, False)}; "
                   f"weights {pct(w['we'], 0, False)} equity / {pct(w['wd'], 0, False)} debt; WACC {pct(w['wacc'], 2, False)}. {rf_label}.")

    result = {"fundamentals": f, "mcap": mcap, "eps": eps, "last_year": last_year}
    if base_fcf <= 0:
        st.info("Free cash flow is negative, so a cash-flow DCF doesn't apply. Revenue growth and the path to profitability are the better lens.")
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
        st.html(f'<div class="mb-verdict"><div><div class="k">Intrinsic value per share {src("calc")}</div><div class="v num">${base.per_share:,.2f}</div>'
                f'<div class="k">Bear ${bear.per_share:,.0f} · Bull ${bull.per_share:,.0f}</div></div>'
                f'<div><div class="k">Market price {src("mkt")}</div><div class="v num">${price:,.2f}</div>'
                f'<div class="k">Upside to intrinsic value <b style="color:{color}">{pct(gap)}</b></div></div>'
                f'<div><div class="k">Verdict under these assumptions</div><div class="label" style="color:{color}">{label}</div>'
                f'<div class="k">Within ±15% counts as fairly valued</div></div></div>')
        if implied is not None:
            st.html(f'<div class="mb-callout"><b>What the price implies.</b> To be worth ${price:,.2f}, free cash flow would need to grow about '
                    f'<b>{pct(implied)} a year for five years</b>, then fade to {pct(g_term, 1, False)}, at a {pct(discount, 1, False)} '
                    f'discount rate. Revenue grew {pct(d["hist_g"]) if d["hist_g"] is not None else "n/a"} a year over the last five years.</div>')
        rates = [round(discount + x, 4) for x in (-0.02, -0.01, 0.0, 0.01, 0.02)]
        terms = [round(g_term + x, 4) for x in (-0.01, -0.005, 0.0, 0.005, 0.01)]
        sens = analysis.sensitivity(base_fcf, growth, f["net_debt"], shares, rates, terms)
        inner = sens.loc[rates[1:4], terms[1:4]].to_numpy()
        lo3, hi3 = analysis.statistical_range(price, m["volatility"], 63) if m["volatility"] else (None, None)
        st.html(f'<div class="mb-sec">Valuation ranges (football field) {src("calc")}</div>')
        st.plotly_chart(charts.football_field([
            ("DCF scenarios, bear to bull", bear.per_share, bull.per_share),
            ("DCF sensitivity (WACC ±1, g ±0.5)", float(np.nanmin(inner)), float(np.nanmax(inner))),
            ("52-week trading range", c["low52"], c["high52"]),
            ("3-month statistical range", lo3, hi3),
        ], price), config=charts.CONFIG, key=f"ff_{t}")
        st.caption("Bear: growth 5 points lower, discount rate 1 point higher. Bull: the opposite.")
        with st.expander("Sensitivity table and DCF detail"):
            show = sens.copy()
            show.index = [pct(r, 1, False) for r in show.index]
            show.columns = [pct(gg, 1, False) for gg in show.columns]
            st.markdown("**Intrinsic value per share** — rows: discount rate, columns: terminal growth")
            st.dataframe(show.style.format("${:,.0f}", na_rep="n/m"))
            proj = base.projections.copy()
            proj["Growth"] = proj["Growth"].map(pct)
            for col in ("FCF", "PV of FCF"):
                proj[col] = proj[col].map(money)
            proj["Discount factor"] = proj["Discount factor"].map(lambda x: f"{x:.3f}")
            st.dataframe(proj, hide_index=True)
            st.caption(f"Discounted FCF {money(base.pv_fcf)} + discounted terminal value {money(base.pv_terminal)} = EV {money(base.enterprise_value)}; "
                       f"− net debt {money(f['net_debt'])} = equity {money(base.equity_value)}; ÷ {shares / 1e9:,.2f}B shares = ${base.per_share:,.2f}. "
                       f"Terminal value is {pct(base.terminal_share, 0, False)} of EV.")
        result.update({"base": base.per_share, "bear": bear.per_share, "bull": bull.per_share, "growth": growth,
                       "g_term": g_term, "discount": discount, "implied": implied, "label": label, "gap": gap, "source": "your"})
        st.session_state[f"val_{t}"] = result
    st.html(f'<div class="mb-sec">Multiples {src("rep")} {src("calc")}</div>' + stats_row([
        ("Market cap", money(mcap), ""), (f"P/E, FY{last_year}", f"{price / eps:,.1f}x" if eps and eps > 0 else "n/m", ""),
        (f"Price / FCF, FY{last_year}", f"{mcap / last_fcf:,.1f}x" if last_fcf > 0 else "n/m", ""),
        ("FCF yield", pct(last_fcf / mcap, signed=False) if last_fcf > 0 else "n/m", ""),
        ("EV / FCF", f"{(mcap + f['net_debt']) / last_fcf:,.1f}x" if last_fcf > 0 else "n/m", "")]))
    return result


# =========================================================================== Outlook
def outlook(c: dict) -> None:
    t, hist, q = c["t"], c["hist"], c["q"]
    labels = {"neutral": "No trend", "market": "Market average (+8%/yr)", "trend": "Recent trend (capped ±30%/yr)"}
    choice = st.segmented_control("Trend assumption", list(labels.values()), default=labels["neutral"], key=f"drift_{t}") or labels["neutral"]
    drift = next(k for k, v in labels.items() if v == choice)
    dcf_val = None
    f = safe(data.company_fundamentals, t)
    if f:
        v = analysis.default_valuation(f, q["price"], c["m"]["beta"], c["rf"])
        dcf_val = v["per_share"] if v else None
    with st.spinner("Simulating 4,000 scenarios…"):
        out = outlook_for(t, drift, float(hist["close"].iloc[-1]), c["high52"], dcf_val)
    if not out:
        st.info("Not enough price history to simulate scenarios.")
        return
    start = out["start"]
    pr = out["probs"]
    cards = [(pr["finish_up"], "end the 6 months above today's close"), (pr["drop_20"], "fall 20% or more at some point"),
             (pr["touch_high"], f"reach the 52-week high (${c['high52']:,.2f})")]
    if pr["touch_target"] is not None:
        cards.append((pr["touch_target"], f"touch the DCF value (${dcf_val:,.2f})"))
    st.html(f'<div class="mb-sec">Model probabilities over 6 months {src("calc")}</div><div class="mb-prob">' + "".join(
        f'<div><div class="v num">{v:.0%}</div><div class="k">of scenarios {esc(k)}</div><div class="bar"><i style="width:{v * 100:.0f}%"></i></div></div>'
        for v, k in cards if v is not None) + "</div>")
    st.plotly_chart(charts.fan_chart(hist["close"], out["fan"], [("52-week high", c["high52"], "up"), ("DCF value", dcf_val, "violet"),
                                                                 ("52-week low", c["low52"], "down")]),
                    config=charts.CONFIG, key=f"fan_{t}_{drift}")
    a, b = st.columns([1.4, 1], gap="medium")
    with a:
        head = "".join(f"<th>{lab}<br><span style='font-weight:400;color:var(--faint)'>{pc}th pct</span></th>"
                       for lab, pc in zip(analysis.OUTLOOK_LABELS, analysis.OUTLOOK_PERCENTILES))
        rows = ""
        for h, vals in out["table"].items():
            rows += f'<tr><td class="l">{h}</td>' + "".join(
                f'<td class="num">${v:,.2f}<br><span class="{signed_class(v / start - 1)}" style="font-size:.74rem">{pct(v / start - 1)}</span></td>'
                for v in vals) + "</tr>"
        st.html(f'<div class="mb-sec">Scenario table</div><div class="mb-scroll"><table class="mb-tbl"><tr><th class="l">Horizon</th>{head}</tr>{rows}</table></div>')
    with b:
        st.html('<div class="mb-sec">How this works</div><div class="mb-callout">4,000 six-month paths. Each simulated day replays a real '
                f'daily move of {esc(t)} from the last two years, so crash days and rallies keep their real frequency. The trend '
                "assumption replaces the average move. These are <b>model probabilities, not forecasts</b>: they assume the next six "
                "months look like a reshuffled version of the past two years.</div>")


# =========================================================================== Compare
def compare(c: dict) -> None:
    t = c["t"]
    peers = [x for x in c["wl"] if x != t][:3]
    picks = st.multiselect("Compare with", list(dict.fromkeys([BENCHMARK, "QQQ"] + c["wl"] + [x for x, _ in data.MEGA_CAPS])),
                           default=[BENCHMARK] + peers, key=f"cmp_{t}", max_selections=5)
    rng = st.segmented_control("Period", ["3M", "6M", "1Y", "3Y", "5Y"], default="1Y", key=f"cmprng_{t}") or "1Y"
    n = {"3M": 63, "6M": 126, "1Y": 252, "3Y": 756, "5Y": 1260}[rng]
    closes = {t: c["hist"]["close"]}
    for x in picks:
        h = safe(data.history, x)
        if h is not None:
            closes[x] = h["close"]
    df = pd.DataFrame(closes).dropna().iloc[-(n + 1):]
    st.plotly_chart(charts.compare_lines({k: df[k] for k in df.columns}, highlight=t), config=charts.CONFIG, key=f"cmpfig_{t}")
    rows = []
    for k in df.columns:
        s = df[k]
        r = s.pct_change().dropna()
        tot = s.iloc[-1] / s.iloc[0] - 1
        vol = r.std() * np.sqrt(252)
        rows.append(f'<tr><td class="l"><a href="{link({"p": "stock", "t": k})}" target="_self">{esc(k)}</a></td>'
                    f'<td class="num {signed_class(tot)}">{pct(tot)}</td><td class="num">{pct(vol, signed=False)}</td>'
                    f'<td class="num neg">{pct(float((s / s.cummax() - 1).min()))}</td>'
                    f'<td class="num">{num(r.corr(df[t].pct_change().dropna()) if k != t else 1.0)}</td></tr>')
    st.html(f'<div class="mb-scroll"><table class="mb-tbl"><tr><th class="l">Ticker</th><th>Return</th><th>Volatility</th>'
            f'<th>Max drawdown</th><th>Correlation with {esc(t)}</th></tr>{"".join(rows)}</table></div>'
            f'<p class="mb-foot">More options on the <a href="{link({"p": "compare"})}" target="_self">Compare</a> page, including an equal-weight portfolio.</p>')


# =========================================================================== News
def news(c: dict) -> list[dict]:
    items = safe(data.company_news, c["t"], default=[]) or []
    if not items:
        st.info("No company news in the last 7 days.")
        return []
    st.html(f'<div class="mb-panel"><div class="mb-h"><b>Latest news on {esc(c["t"])}</b><span>Finnhub {src("mkt")}</span></div><div class="mb-news">' + "".join(
        f'<div><a class="t" href="{esc(n["url"])}" target="_blank" rel="noopener">{esc(n["title"])}</a>'
        f'<div class="m">{esc(n["source"])} · {n["time"]:%b %d, %-I:%M %p}</div>'
        + (f'<div class="s">{esc(n["summary"])}</div>' if n["summary"] else "") + "</div>" for n in items if n.get("time")) + "</div></div>")
    return items


# =========================================================================== AI
def ai_data_text(c: dict, val: dict | None, out: dict | None) -> str:
    q, m, met = c["q"], c["m"], c["met"]
    lines = [
        f"Price ${q['price']:,.2f} ({(q['pct'] or 0):+.2f}% today), quote time {q['time']:%Y-%m-%d %H:%M} ET",
        f"Returns: 1M {pct(m['ret_1m'])}, 3M {pct(m['ret_3m'])}, YTD {pct(m['ret_ytd'])}, 1Y {pct(m['ret_1y'])}",
        f"Risk: 1Y volatility {pct(m['volatility'], signed=False)}, 1Y max drawdown {pct(m['max_drawdown'])}, "
        f"2Y weekly beta vs SPY {num(m['beta'])}, 1Y Sharpe {num(m['sharpe'])}",
        f"52-week range {c['low52']:,.2f} to {c['high52']:,.2f}; price-to-earnings ratio (P/E, trailing 12 months) {num(met.get('peTTM'), 1)}; market cap {money(c['p'].get('market_cap'))}",
    ]
    if val:
        f = val["fundamentals"]
        lines += ["Revenue: " + "; ".join(f"FY{y}: {money(v)}" for y, v in f["revenue"].iloc[-5:].items()),
                  "Free cash flow: " + "; ".join(f"FY{y}: {money(v)}" for y, v in f["fcf"].iloc[-5:].items()),
                  f"Net debt {money(f['net_debt'])}"]
        if val.get("base"):
            lines.append(f"Base-case DCF ({'assumptions set in the Valuation tab' if val.get('source') == 'your' else 'default assumptions'}: "
                         f"growth {pct(val['growth'])} for 5 years, terminal growth {pct(val.get('g_term', 0.025), 1, False)}, "
                         f"WACC {pct(val['discount'], 1, False)}): "
                         f"${val['base']:,.2f} per share, {val['label'].lower()} ({pct(val['gap'])} vs price); bear ${val['bear']:,.2f}, bull ${val['bull']:,.2f}")
            if val.get("implied") is not None:
                lines.append(f"Reverse DCF: the price implies about {pct(val['implied'])} annual FCF growth for 5 years")
    if out:
        pr = out["probs"]
        lines.append(f"Scenario model (bootstrap of 2 years of daily moves, no trend), 6 months: median ${out['table']['6 months'][2]:,.2f}, "
                     f"5th-95th percentile ${out['table']['6 months'][0]:,.2f} to ${out['table']['6 months'][4]:,.2f}; "
                     f"{pr['finish_up']:.0%} of paths end higher, {pr['drop_20']:.0%} fall 20% at some point")
    recs = safe(data.recommendations, c["t"], default=[])
    cs = analysis.consensus(recs[0]) if recs else None
    if cs:
        k = cs["counts"]
        lines.append(f"Wall Street consensus ({cs['period']}, {cs['n']} analysts): {cs['label']}, average {cs['score']:.2f} on a 1-5 scale "
                     f"(strong buy {k['strongBuy']}, buy {k['buy']}, hold {k['hold']}, sell {k['sell']}, strong sell {k['strongSell']})")
    e = safe(data.next_earnings, c["t"])
    if e:
        lines.append(f"Next earnings date: {e['date']} {e['timing']}")
    return "\n".join(lines)


def lean_badge(lean: str | None, big_text: bool = True) -> str:
    cls = {"Buy": "up", "Strong Buy": "up", "Hold": "hold", "Sell": "down", "Strong Sell": "down"}.get(lean or "", "flat")
    return f'<span class="mb-lean {cls}{" big" if big_text else ""}">{esc(lean or "n/a")}</span>'


def default_val(c: dict) -> dict | None:
    f = safe(data.company_fundamentals, c["t"])
    if not f:
        return None
    if f["fcf"].empty or not f["shares"]:
        return {"fundamentals": f}
    v = analysis.default_valuation(f, c["q"]["price"], c["m"]["beta"], c["rf"])
    if not v:
        return {"fundamentals": f}
    base_fcf = float(f["fcf"].iloc[-1])
    implied = analysis.implied_growth(c["q"]["price"], base_fcf, 0.025, v["wacc"], f["net_debt"], f["shares"])
    bear = analysis.dcf(base_fcf, max(v["growth"] - 0.05, -0.1), 0.025, v["wacc"] + 0.01, f["net_debt"], f["shares"]).per_share
    bull = analysis.dcf(base_fcf, v["growth"] + 0.05, 0.025, max(v["wacc"] - 0.01, 0.031), f["net_debt"], f["shares"]).per_share
    return {"fundamentals": f, "base": v["per_share"], "bear": bear, "bull": bull, "growth": v["growth"], "g_term": 0.025,
            "discount": v["wacc"], "label": v["label"], "gap": v["gap"], "implied": implied, "source": "default"}


def consensus_card(t: str) -> tuple[str, dict | None]:
    recs = safe(data.recommendations, t, default=[]) or []
    cs = analysis.consensus(recs[0]) if recs else None
    head = (f'<div class="mb-kicker">What the experts say</div><div class="mb-h"><b>Wall Street consensus</b>'
            f'<span>Finnhub recommendation trends {src("ana")}</span></div>')
    if not cs:
        return f'<div class="mb-panel mb-take">{head}<p class="mb-foot">No analyst ratings available for {esc(t)}.</p></div>', None
    trend = ""
    old = analysis.consensus(recs[3]) if len(recs) > 3 else (analysis.consensus(recs[-1]) if len(recs) > 1 else None)
    if old:
        d = cs["score"] - old["score"]
        word = "more bullish" if d > 0.02 else "more bearish" if d < -0.02 else "unchanged"
        trend = f' · {word} vs {old["period"]}'
    k, n, pal = cs["counts"], cs["n"], P()
    colors = {"strongBuy": pal["up"], "buy": pal["up"] + "99", "hold": pal["faint"], "sell": pal["down"] + "99", "strongSell": pal["down"]}
    names = {"strongBuy": "Strong Buy", "buy": "Buy", "hold": "Hold", "sell": "Sell", "strongSell": "Strong Sell"}
    bar = "".join(f'<i style="width:{k[x] / n * 100:.2f}%;background:{colors[x]}" title="{names[x]} {k[x]}"></i>' for x in names if k[x])
    legend = " · ".join(f'<span><b style="background:{colors[x]}"></b>{names[x]} {k[x]}</span>' for x in names)
    html_ = (f'<div class="mb-panel mb-take">{head}<div class="mb-take-row">{lean_badge(cs["label"])}'
             f'<div><div class="mb-score num">{cs["score"]:.2f} <small>/ 5</small></div>'
             f'<div class="mb-foot" style="margin:0">{n} analysts · {cs["period"]}{trend}</div></div></div>'
             f'<div class="mb-stack">{bar}</div><div class="mb-legend">{legend}</div>'
             f'<p class="mb-foot">Ratings from the brokerage analysts that cover the stock, aggregated monthly by Finnhub '
             f'(5 = strong buy, 1 = strong sell). Price targets are not in the free plan.</p></div>')
    return html_, cs


def analysts_section(c: dict) -> None:
    t = c["t"]
    key = f"take_{t}"
    val = st.session_state.get(f"val_{t}")
    using_yours = bool(val and val.get("base"))
    card, cs = consensus_card(t)
    left, right = st.columns(2, gap="medium")
    left.html(card)
    with right:
        take = st.session_state.get(key)
        head = (f'<div class="mb-kicker">Model view</div><div class="mb-h"><b>AI take</b>'
                f'<span>Gemini reads the data on this page {src("ai")}</span></div>')
        if take and take.get("lean"):
            agree = ""
            if cs:
                same = (take["lean"] == "Buy" and cs["label"] in ("Buy", "Strong Buy")) or (take["lean"] == "Sell" and cs["label"] in ("Sell", "Strong Sell")) \
                    or (take["lean"] == "Hold" and cs["label"] == "Hold")
                agree = f'<span class="mb-chip {"up" if same else "flat"}">{"Agrees with" if same else "Differs from"} Wall Street</span>'
            conv = f'<div class="mb-foot" style="margin:0">Conviction: {esc(take.get("conviction") or "n/a")}</div>'
            st.html(f'<div class="mb-panel mb-take">{head}<div class="mb-take-row">{lean_badge(take["lean"])}<div>{agree}{conv}</div></div>'
                    f'<p class="mb-p">{esc(take.get("lean_reason", ""))}</p>'
                    f'<p class="mb-p"><b>Vs the consensus.</b> {esc(take.get("vs_consensus", ""))}</p>'
                    f'<p class="mb-foot">Model opinion from the data in this app, written {take["generated_at"]:%b %d, %-I:%M %p} ET. '
                    "Not investment advice.</p></div>")
        else:
            st.html(f'<div class="mb-panel mb-take">{head}<p class="mb-p">Click the button for a written take with a <b>Buy / Hold / Sell</b> lean, '
                    "compared against the Wall Street consensus, plus bull, base and bear cases, risks and catalysts. "
                    + ("It uses the <b>DCF assumptions set in the Valuation tab</b>." if using_yours else
                       "It uses the default DCF assumptions; open the Valuation tab and adjust them first to use yours.")
                    + '</p><p class="mb-foot">Data: fetched from the sources · Calc: computed by the app · AI: model opinion.</p></div>')
        label = "Refresh AI take" if take else "Generate AI take"
        clicked = st.button(label, type="primary", key=f"btn_{key}", width="stretch")
    if clicked:
        with st.spinner("Collecting the data and writing the take… (10 to 30 seconds)"):
            v = val if using_yours else default_val(c)
            out = safe(outlook_for, t, "neutral", float(c["hist"]["close"].iloc[-1]), c["high52"], None)
            news_items = safe(data.company_news, t, default=[]) or []
            assumptions = (f"{v.get('growth', 0):.4f}|{v.get('g_term', 0):.4f}|{v.get('discount', 0):.4f}|{v.get('source')}"
                           if v and v.get("base") else "none")
            try:
                st.session_state[key] = ai.stock_take(t, c["p"].get("name") or t, dt.date.today().isoformat(), assumptions,
                                                      ai_data_text(c, v, out), news_items)
                st.rerun()
            except Exception as exc:
                st.warning(f"The AI take couldn't be written this time: {exc}")
    take = st.session_state.get(key)
    if not take:
        return
    body = "".join(f'<p><b>{title}.</b> {esc(take[k])}</p>' for title, k in (
        ("Where it stands", "situation"), ("Recent performance", "recent_performance"), ("Fundamentals", "fundamentals"),
        ("Valuation", "valuation"), ("News flow", "news")) if take.get(k))
    cases = "".join(f'<div class="mb-story"><h3>{title}</h3><p>{esc(take.get(k, ""))}</p></div>'
                    for title, k in (("Bear case", "bear_case"), ("Base case", "base_case"), ("Bull case", "bull_case")))
    risks = "".join(f"<li>{esc(r)}</li>" for r in take.get("risks", []))
    cats = "".join(f"<li>{esc(x)}</li>" for x in take.get("catalysts", []))
    st.html(f'<div class="mb-sec">Full AI analysis {src("ai")}</div><div class="mb-story top">{body}</div><div class="mb-grid3">{cases}</div>'
            f'<div class="mb-grid2"><div class="mb-story"><h3>Main risks</h3><ul>{risks}</ul></div>'
            f'<div class="mb-story"><h3>Coming catalysts</h3><ul>{cats}</ul></div></div>'
            f'<div class="mb-callout"><b>Conclusion.</b> {esc(take.get("conclusion", ""))}</div>'
            '<p class="mb-note">Not investment advice · statistics describe the past, they don\'t predict the future.</p>')
