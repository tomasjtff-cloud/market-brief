"""The stock page, laid out like a quote page: header, then sections for summary, chart, financials,
valuation, outlook, comparison, news and the AI analysis."""
from __future__ import annotations

import datetime as dt
import hashlib

import numpy as np
import pandas as pd
import streamlit as st

import helpbox as hp

import ai
import analysis
import charts
import data
import fundamentals
from common import (BENCHMARK, MAX_WATCHLIST, add_to_watchlist, big, get_watchlist, isnum, money, num, pct,
                    remove_from_watchlist, safe, when)
from i18n import D, T, choice, lang
from ui import P, chip, esc, link, sgn, signed_class, src

from reportlab.lib.colors import HexColor as _Hex  # noqa: E402

UP_C, DOWN_C, AMBER_C = _Hex("#0E9F6E"), _Hex("#D64545"), _Hex("#C98A00")


def tone(x):
    """Report colour for a signed number (None keeps the default ink)."""
    if x is None or not isnum(x):
        return None
    return UP_C if x > 0 else DOWN_C if x < 0 else None

SECTIONS = ["Summary", "Chart", "Financials", "Earnings", "Valuation", "Outlook", "Compare", "News", "Analysts & AI take"]
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
    with c2:
        kind = choice(st.segmented_control, "Type", ["Area", "Candles"], key=f"{key}_kind_{t}", default="Area",
                      label_visibility="collapsed") or "Area"
    intraday = rng in ("1D", "5D")
    if intraday:
        interval, size, days = ("5min", 80, 1) if rng == "1D" else ("30min", 70, 5)
        df = safe(data.intraday, t, interval, size)
        if df is None or df.empty:
            st.caption(T("Intraday bars aren't available right now; showing one month instead."))
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
        bars = T("5-minute bars") if rng == "1D" else T("30-minute bars") if rng == "5D" else T("daily bars")
        st.html(f'<p class="mb-foot">{T("{r} change", r=rng)} <b class="{signed_class(ch)}">{pct(ch, 2)}</b> · '
                f'{bars} {T("from Twelve Data")} {src("mkt")}</p>')


def kv(rows: list[tuple[str, str]]) -> str:
    return '<div class="mb-kv">' + "".join(f"<div><span>{esc(T(k))}</span><span>{v}</span></div>" for k, v in rows) + "</div>"


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
        st.error(T("No quote found for {t}. Check the ticker or search for the company in the top bar.", t=t))
        return
    p = safe(data.profile, t, default={"name": t, "industry": "", "logo": "", "exchange": ""}) or {"name": t}
    hist = safe(data.history, t)
    if hist is None or len(hist) < 30:
        st.error(T("Price history for {t} isn't available right now. Try again in a minute.", t=t))
        return
    bench = safe(lambda: data.history(BENCHMARK)["close"])
    rf, rf_label = data.risk_free_rate()
    m = analysis.risk_metrics(hist["close"], bench, rf)
    met = safe(data.basic_metrics, t, default={}) or {}
    status = safe(data.market_status, default={}) or {}

    # ---- header
    logo = f'<img class="logo" src="{esc(p.get("logo"))}" alt="">' if p.get("logo") else ""
    cls = signed_class(q["pct"])
    state = T("Market open") if status.get("isOpen") else T("At close")
    head_l, head_r = st.columns([5, 1.3], vertical_alignment="bottom")
    head_l.html(
        f'<div class="mb-quote"><div class="idt">{logo}<div><div class="co">{esc(p.get("name") or t)}</div>'
        f'<div class="meta"><span class="mb-tag">{esc(t)}</span><span>{esc(p.get("exchange", "")).replace("NASDAQ NMS - GLOBAL MARKET", "Nasdaq")}</span>'
        f'<span>{esc(T(p.get("industry") or ""))}</span><span>USD</span></div></div></div>'
        f'<div><span class="px num">{q["price"]:,.2f}</span><span class="chg num {cls}">{sgn(q["change"] or 0, 2, "")} ({sgn(q["pct"] or 0)})</span>'
        f'<div class="asof">{state} · {when(q["time"])} {src("mkt")}</div></div></div>')
    with head_r:
        pdf_slot = st.container()
        if t in wl:
            st.button(T("✓ In watchlist"), key=f"wl_rm_{t}", on_click=remove_from_watchlist, args=(t,), width="stretch",
                      help=T("Click to remove from the watchlist"), disabled=len(wl) == 1)
        elif len(wl) < MAX_WATCHLIST:
            st.button(T("+ Add to watchlist"), key=f"wl_add_{t}", on_click=add_to_watchlist, args=(t,), type="primary", width="stretch")

    high52 = met.get("52WeekHigh") or float(hist["close"].iloc[-252:].max())
    low52 = met.get("52WeekLow") or float(hist["close"].iloc[-252:].min())
    st.html(f'<div class="mb-stats" style="--cols:8">' + "".join(
        f'<div class="mb-stat"><div class="k">{T(k)}</div><div class="v num {c}">{v}</div></div>' for k, v, c in [
            ("Market cap", money(p.get("market_cap"), 2), ""),
            ("P/E (TTM)", num(met.get("peTTM"), 1, "x") if (met.get("peTTM") or 0) > 0 else "n/m", ""),
            ("EPS (TTM)", f'${met["epsTTM"]:,.2f}' if isnum(met.get("epsTTM")) else "n/a", ""),
            ("YTD", pct(m["ret_ytd"]), signed_class(m["ret_ytd"])),
            ("1 year", pct(m["ret_1y"]), signed_class(m["ret_1y"])),
            ("Volatility", pct(m["volatility"], signed=False), ""),
            ("Beta", num(m["beta"]), ""),
            ("52-week range", f"{low52:,.0f} – {high52:,.0f}", ""),
        ]) + "</div>")

    section = choice(st.segmented_control, "Section", SECTIONS, key=f"sec_{t}", default="Summary",
                     label_visibility="collapsed") or "Summary"
    st.html('<div style="height:.2rem"></div>')
    hp.show({"Summary": "stock_summary", "Chart": "stock_chart", "Financials": "stock_financials", "Earnings": "stock_earnings", "Valuation": "stock_valuation",
             "Outlook": "stock_outlook", "Compare": "stock_compare", "News": "stock_news",
             "Analysts & AI take": "stock_analysts"}.get(section, ""))
    ctx = {"t": t, "q": q, "p": p, "hist": hist, "bench": bench, "rf": rf, "rf_label": rf_label, "m": m, "met": met,
           "high52": high52, "low52": low52, "wl": wl}
    with pdf_slot:
        pdf_controls(ctx)
    {"Summary": summary, "Chart": chart_section, "Financials": financials, "Earnings": earnings, "Valuation": valuation, "Outlook": outlook,
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
            ("Dividend yield", f"{dy:.2f}%" if isnum(dy) and dy else T("None")),
            ("Next earnings", D(dt.date.fromisoformat(e["date"]), "%b %-d, %Y") if e else "n/a"),
            ("Sharpe (1Y)", num(m["sharpe"])),
        ]
        st.html(f'<div class="mb-panel"><div class="mb-h"><b>{T("Key statistics")}</b><span>{src("mkt")} {src("calc")}</span></div>'
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
            rows += (f'<tr><td class="l">{T(label)}</td><td class="num {signed_class(r1)}">{pct(r1)}</td>'
                     f'<td class="num {signed_class(r2)}">{pct(r2)}</td><td class="num {signed_class(rel)}">{pct(rel)}</td></tr>')
        st.html(f'<div class="mb-panel"><div class="mb-h"><b>{T("Performance vs S&amp;P 500")}</b><span>{src("calc")}</span></div>'
                f'<table class="mb-tbl"><tr><th class="l">{T("Period")}</th><th>{esc(t)}</th><th>SPY</th><th>{T("Difference")}</th></tr>{rows}</table></div>')
    with b:
        with st.container(key="panel_recs"):
            st.html(f'<div class="mb-h"><b>{T("Analyst ratings")}</b><span>{src("ana")}</span></div>')
            recs = safe(data.recommendations, t, default=[])
            if recs:
                st.plotly_chart(charts.recommendations(recs), config=charts.CONFIG, key=f"recs_{t}")
                cs = analysis.consensus(recs[0])
                if cs:
                    bulls = (cs["counts"]["strongBuy"] + cs["counts"]["buy"]) / cs["n"]
                    st.html('<p class="mb-foot">' + T("Consensus <b>{l}</b> ({s} / 5) from {n} analysts, {b} buy or strong buy ({p}). Sell-side ratings lean positive in general.",
                                                      l=T(cs["label"]), s=f'{cs["score"]:.2f}', n=cs["n"], b=f"{bulls:.0%}", p=cs["period"]) + "</p>")
            else:
                st.caption(T("No analyst ratings available."))
    with c3:
        ma50, ma200 = hist["close"].rolling(50).mean().iloc[-1], hist["close"].rolling(200).mean().iloc[-1]
        price = q["price"]
        lv = [("52-week high", c["high52"]), ("50-day average", ma50), ("200-day average", ma200), ("52-week low", c["low52"])]
        rows = "".join(f'<tr><td class="l">{T(n)}</td><td class="num">{v:,.2f}</td><td class="num {signed_class(price / v - 1)}">{pct(price / v - 1)}</td></tr>'
                       for n, v in lv if isnum(v))
        prof = c["p"]
        st.html(f'<div class="mb-panel"><div class="mb-h"><b>{T("Key levels")}</b><span>{src("calc")}</span></div>'
                f'<table class="mb-tbl"><tr><th class="l">{T("Level")}</th><th>{T("Price")}</th><th>{T("Price vs level")}</th></tr>{rows}</table></div>'
                f'<div class="mb-panel" style="margin-top:.6rem"><div class="mb-h"><b>{T("Profile")}</b></div>' + kv([
                    ("Industry", esc(prof.get("industry") or "n/a")), ("Country", esc(prof.get("country") or "n/a")),
                    ("Listed since", esc(prof.get("ipo") or "n/a")),
                    ("Website", f'<a href="{esc(prof.get("web"))}" target="_blank" rel="noopener">{esc((prof.get("web") or "").replace("https://", "").replace("http://", "").strip("/"))}</a>' if prof.get("web") else "n/a"),
                ]).replace('class="mb-kv"', 'class="mb-kv" style="grid-template-columns:1fr"') + "</div>")


# =========================================================================== Chart
def chart_section(c: dict) -> None:
    t, hist, q, m = c["t"], c["hist"], c["q"], c["m"]
    ind = choice(st.pills, "Indicators", ["50-day", "200-day", "Bollinger", "RSI", "±1σ range ahead"], key=f"ind_{t}",
                 default=["50-day", "200-day"], multi=True, label_visibility="collapsed") or []
    chart_block(t, hist, q, "big", 600, indicators=tuple(ind), cone=m["volatility"] if "±1σ range ahead" in ind else None)
    a, b = st.columns([1, 1.1], gap="medium")
    with a:
        st.html(f'<div class="mb-sec">{T("How far it usually moves")} {src("calc")}</div>')
        if m["volatility"]:
            rows = ""
            for label, days in (("1 month", 21), ("3 months", 63), ("6 months", 126)):
                lo1, hi1 = analysis.statistical_range(q["price"], m["volatility"], days)
                s = m["volatility"] * np.sqrt(days / analysis.TRADING_DAYS) * 1.96
                rows += (f'<tr><td class="l">{T(label)}</td><td class="num">{lo1:,.2f} – {hi1:,.2f}</td>'
                         f'<td class="num">{q["price"] * np.exp(-s):,.2f} – {q["price"] * np.exp(s):,.2f}</td></tr>')
            st.html(f'<div class="mb-panel"><table class="mb-tbl"><tr><th class="l">{T("Horizon")}</th><th>{T("2 in 3 outcomes")}</th>'
                    f'<th>{T("19 in 20 outcomes")}</th></tr>{rows}</table></div><p class="mb-foot">'
                    + T("Normal model on last year's volatility ({v} a year), no drift. The Outlook section uses real past moves instead.",
                        v=pct(m["volatility"], signed=False)) + "</p>")
        st.html(stats_row([("Max drawdown, 1Y", pct(m["max_drawdown"]), "neg"), ("Sharpe, 1Y", num(m["sharpe"]), ""),
                           ("Beta vs SPY", num(m["beta"]), ""), ("RSI (14)", num(charts.rsi(hist["close"]).iloc[-1], 0), "")]))
    with b:
        st.html(f'<div class="mb-sec">{T("Drawdown, last year")} {src("calc")}</div>')
        st.plotly_chart(charts.drawdown(hist["close"]), config=charts.CONFIG, key=f"dd_{t}")
    tail = analysis.tail_stats(hist["close"])
    if tail:
        st.html(f'<div class="mb-sec">{T("Tail risk: bad days")} {src("calc")}</div>')
        rows = "".join(
            f'<tr><td class="l">{T(lbl)}</td><td class="num neg">{pct(-tail[f"var{lv}"], 2)}</td><td class="num neg">{pct(-tail[f"es{lv}"], 2)}</td>'
            f'<td class="num">{pct(-tail[f"var{lv}_normal"], 2)}</td></tr>' for lv, lbl in ((95, "1 day in 20"), (99, "1 day in 100")))
        fat = tail[f"var99"] > tail["var99_normal"] * 1.1
        st.html(f'<div class="mb-scroll"><table class="mb-tbl"><tr><th class="l">{T("How often")}</th><th>{T("Loss at least (VaR)")}</th>'
                f'<th>{T("Average loss on those days (expected shortfall)")}</th><th>{T("A normal bell curve would say")}</th></tr>{rows}</table></div>'
                '<p class="mb-foot">' + T("From {d} real daily returns. Skewness {sk}, excess kurtosis {ku}. {fat}", d=tail["days"],
                                           sk=f'{tail["skew"]:.2f}', ku=f'{tail["kurt"]:.1f}',
                                           fat=T("Bad days are worse than the bell curve suggests (fat tails).") if fat
                                           else T("Bad days are close to what the bell curve suggests.")) + "</p>")


def stats_row(items: list[tuple[str, str, str]]) -> str:
    return (f'<div class="mb-stats" style="--cols:{len(items)};margin-top:.6rem">' + "".join(
        f'<div class="mb-stat"><div class="k">{T(k)}</div><div class="v num {cl}">{v}</div></div>' for k, v, cl in items) + "</div>")


# =========================================================================== Financials
def financials(c: dict) -> None:
    t = c["t"]
    with st.spinner(T("Reading SEC filings…")):
        f = safe(data.company_fundamentals, t)
    if not f or f["revenue"].empty:
        st.info(T("Reported financials aren't available for {t} (non-US filers, ETFs and funds don't file 10-Ks).", t=t))
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
        return f'<tr><td class="l">{T(label)}</td>{"".join(cells)}</tr>'

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
    st.html(f'<div class="mb-sec">{T("Annual financials")} {src("rep")}</div><div class="mb-scroll"><table class="mb-tbl">'
            f'<tr><th class="l">{T("Fiscal year")}</th>{"".join(f"<th>{y}</th>" for y in years)}</tr>{body}</table></div><p class="mb-foot">'
            + T("From 10-K filings (XBRL), calendar-aligned fiscal years. Balance sheet as of {d}: cash and short-term investments {c}, debt {debt}, net debt {nd}.",
                d=f["balance_sheet_date"], c=money(f["cash"], 1), debt=money(f["debt"], 1), nd=money(f["net_debt"], 1)) + "</p>")
    for note in f["notes"]:
        st.caption(T("Note: ") + note)
    b = lambda s: [g(s, y) / 1e9 if g(s, y) is not None else None for y in years]  # noqa: E731
    a1, a2 = st.columns(2, gap="medium")
    with a1:
        st.html(f'<div class="mb-sec">{T("Revenue, profit and cash")}</div>')
        st.plotly_chart(charts.financial_bars(years, [(T("Revenue"), b(rev), "accent"), (T("Net income"), b(f["net_income"]), "teal"),
                                                      (T("Free cash flow"), b(f["fcf"]), "orange")]), config=charts.CONFIG, key=f"fin_{t}_{lang()}")
    with a2:
        st.html(f'<div class="mb-sec">{T("Margins")}</div>')
        mg = lambda s: [(g(ratio(s), y) or np.nan) * 100 if g(ratio(s), y) is not None else None for y in years]  # noqa: E731
        st.plotly_chart(charts.margin_lines(years, [(T("Gross"), mg(f["gross_profit"]), "accent"), (T("Operating"), mg(f["operating_income"]), "violet"),
                                                    (T("Net"), mg(f["net_income"]), "teal"), ("FCF", mg(f["fcf"]), "orange")]),
                        config=charts.CONFIG, key=f"mg_{t}_{lang()}")
    statement_block(c, f)


def wacc_for(c: dict, f: dict) -> tuple[float, str]:
    """The WACC set in the Valuation tab, or the same default it starts from."""
    val = st.session_state.get(f"val_{c['t']}") or {}
    if val.get("discount"):
        return float(val["discount"]), T("from your Valuation assumptions")
    beta_ = float(np.clip(c["m"]["beta"], 0.5, 2.5)) if c["m"].get("beta") else 1.0
    mcap = c["q"]["price"] * (f.get("shares") or 0)
    w = analysis.wacc(c["rf"], beta_, 0.05, c["rf"] + 0.015, analysis.tax_rate(f), mcap, f.get("debt") or 0.0)
    return float(w["wacc"]), T("default: CAPM with a 5% equity premium, as in Valuation")


RATIO_ROWS = [  # (group, key, label, kind) — kind: pct, x, days, growth
    ("Growth (horizontal analysis)", "revenue_growth", "Revenue growth", "growth"),
    ("Growth (horizontal analysis)", "net_income_growth", "Net income growth", "growth"),
    ("Margins (vertical analysis, % of revenue)", "gross_margin", "Gross margin", "pct"),
    ("Margins (vertical analysis, % of revenue)", "ebitda_margin", "EBITDA margin", "pct"),
    ("Margins (vertical analysis, % of revenue)", "operating_margin", "Operating margin", "pct"),
    ("Margins (vertical analysis, % of revenue)", "net_margin", "Net margin", "pct"),
    ("Margins (vertical analysis, % of revenue)", "fcf_margin", "FCF margin", "pct"),
    ("Margins (vertical analysis, % of revenue)", "sbc_revenue", "Stock compensation, % of revenue", "pct"),
    ("Liquidity", "current_ratio", "Current ratio", "x"),
    ("Liquidity", "quick_ratio", "Quick ratio", "x"),
    ("Leverage", "debt_equity", "Debt / equity", "x"),
    ("Leverage", "net_debt_ebitda", "Net debt / EBITDA", "x"),
    ("Leverage", "interest_coverage", "Interest coverage (EBIT / interest)", "x"),
    ("Activity", "asset_turnover", "Asset turnover", "x"),
    ("Activity", "dso", "Days sales outstanding", "days"),
    ("Activity", "dio", "Days inventory", "days"),
    ("Profitability and DuPont", "roa", "Return on assets (ROA)", "pct"),
    ("Profitability and DuPont", "roe", "Return on equity (ROE)", "pct"),
    ("Profitability and DuPont", "net_margin", "× Net margin", "pct"),
    ("Profitability and DuPont", "asset_turnover", "× Asset turnover", "x"),
    ("Profitability and DuPont", "equity_multiplier", "× Equity multiplier", "x"),
    ("Earnings quality", "cash_conversion", "Cash conversion (operating cash flow / net income)", "x"),
    ("Earnings quality", "accruals", "Accruals ratio ((net income − operating cash flow) / assets)", "growth"),
    ("Earnings quality", "receivables_vs_sales", "Receivables growth − revenue growth", "growth"),
]


def fmt_ratio(v, kind: str) -> str:
    if not isnum(v) or np.isinf(v):
        return "n/a"
    if kind == "x":
        return f"{v:,.2f}x"
    if kind == "days":
        return f"{v:,.0f}"
    return pct(v, 1, kind == "growth")


def statement_block(c: dict, f: dict) -> None:
    t = c["t"]
    ratios = analysis.statement_analysis(f)
    if ratios.empty or not (f.get("balance") or {}).get("assets") is not None:
        return
    years = list(ratios.columns)[-5:]
    wacc_v, wacc_src = wacc_for(c, f)
    left, right = st.columns([1, 1.25], gap="medium")
    with left:
        st.html(f'<div class="mb-sec">{T("Health checks")} <span class="mb-tagx">{T("latest fiscal year")}</span> {src("calc")}</div>')
        checks = analysis.health_checks(ratios[years])
        icon = {"good": ("up", "✓"), "watch": ("hold", "!"), "bad": ("down", "✕")}
        st.html('<div class="mb-panel">' + ("".join(
            f'<div class="mb-check"><span class="mb-lean {icon[lv][0]}">{icon[lv][1]}</span><div class="mb-p" style="margin:0">{esc(T(msg, **kw))}</div></div>'
            for lv, msg, kw in checks) or f'<p class="mb-p">{T("Not enough balance-sheet data for the checks.")}</p>') + "</div>")
    with right:
        e = analysis.eva(f, wacc_v)
        st.html(f'<div class="mb-sec">{T("Economic value added")} {src("calc")}</div>')
        if e.empty or e["eva"].dropna().empty:
            st.caption(T("EVA needs equity and operating profit from the 10-K; not available here."))
        else:
            last = e.dropna(subset=["eva"]).iloc[-1]
            yr = e.dropna(subset=["eva"]).index[-1]
            st.html(stats_row([("NOPAT", money(last["nopat"], 1), ""), ("Capital employed", money(last["capital"], 1), ""),
                               ("ROIC", pct(last["roic"], 1, False), ""), ("WACC", pct(wacc_v, 1, False), ""),
                               ("EVA", money(last["eva"], 1), signed_class(last["eva"]))]))
            st.html('<p class="mb-foot">' + T("FY{y}. NOPAT = operating income × (1 − {tax} tax); capital employed = debt + equity, average of the year; WACC {w}, {src}. {verdict}",
                                               y=yr, tax=pct(analysis.tax_rate(f), 0, False), w=pct(wacc_v, 1, False), src=wacc_src,
                                               verdict=T("Return on capital beats its cost: the company creates value.") if last["eva"] > 0
                                               else T("Return on capital is below its cost: the company destroys value at this WACC.")) + "</p>")
            ey = [y for y in e.index if pd.notna(e.at[y, "eva"])][-6:]
            st.plotly_chart(charts.financial_bars(ey, [(T("EVA"), [e.at[y, "eva"] / 1e9 for y in ey], "teal")], height=220),
                            config=charts.CONFIG, key=f"eva_{t}_{lang()}")
    body, group = "", None
    for grp, key, label, kind in RATIO_ROWS:
        if key not in ratios.index or ratios.loc[key, years].isna().all():
            continue
        if grp != group:
            body += f'<tr class="grp"><td class="l" colspan="{len(years) + 1}">{T(grp)}</td></tr>'
            group = grp
        body += f'<tr><td class="l">{T(label)}</td>' + "".join(
            f'<td class="num {signed_class(ratios.at[key, y]) if kind == "growth" and isnum(ratios.at[key, y]) else ""}">{fmt_ratio(ratios.at[key, y], kind)}</td>'
            for y in years) + "</tr>"
    st.html(f'<div class="mb-sec">{T("Statement analysis")} <span class="mb-tagx">{T("fiscal years · SEC 10-K")}</span> {src("calc")}</div>'
            f'<div class="mb-scroll"><table class="mb-tbl mb-ratios"><tr><th class="l"></th>{"".join(f"<th>FY{y}</th>" for y in years)}</tr>{body}</table></div>'
            '<p class="mb-foot">' + T("Balance-sheet ratios use the average of the opening and closing balance. DuPont splits ROE into net margin × asset turnover × equity multiplier, so you can see whether returns come from pricing power, efficiency or debt. n/a = the company doesn't report that line in a comparable way.") + "</p>")


# =========================================================================== Earnings
def _q_label(end: str) -> str:
    try:
        return D(dt.date.fromisoformat(end[:10]), "%b %Y")
    except Exception:
        return end


def earnings(c: dict) -> None:
    t, hist = c["t"], c["hist"]
    with st.spinner(T("Loading earnings…")):
        surprises = safe(data.earnings_surprises, t, default=[]) or []
        cal = safe(data.earnings_history, t, default=[]) or []
        f = safe(data.company_fundamentals, t)
    today = dt.date.today().isoformat()
    past = [r for r in cal if r["date"] <= today and (r.get("eps_actual") is not None or r.get("rev_actual") is not None)]
    nxt = next((r for r in cal if r["date"] >= today and r.get("eps_actual") is None), None)
    # merge EPS surprises (by fiscal year and quarter) with report dates and revenue
    rows: dict[tuple, dict] = {}
    for r in surprises:
        rows[(r.get("year"), r.get("quarter"))] = {"period": r["period"], "eps_actual": r["actual"], "eps_estimate": r.get("estimate"),
                                                    "surprise_pct": r.get("surprise_pct")}
    for r in past:
        k = (r.get("year"), r.get("quarter"))
        row = rows.setdefault(k, {"period": None, "eps_actual": r.get("eps_actual"), "eps_estimate": r.get("eps_estimate"), "surprise_pct": None})
        row.update({"date": r["date"], "hour": r.get("hour"), "rev_actual": r.get("rev_actual"), "rev_estimate": r.get("rev_estimate")})
        if row.get("eps_actual") is None:
            row["eps_actual"], row["eps_estimate"] = r.get("eps_actual"), r.get("eps_estimate")
    items = sorted(rows.items(), key=lambda kv: (kv[0][0] or 0, kv[0][1] or 0))[-8:]
    for _, r in items:
        if r.get("surprise_pct") is None and isnum(r.get("eps_actual")) and isnum(r.get("eps_estimate")) and r["eps_estimate"]:
            r["surprise_pct"] = (r["eps_actual"] - r["eps_estimate"]) / abs(r["eps_estimate"]) * 100
        r["reaction"] = analysis.earnings_reaction(hist["close"], r["date"], r.get("hour") or "") if r.get("date") else None
    if not items and not nxt:
        st.info(T("No earnings data for {t} (ETFs and funds don't report earnings).", t=t))
    else:
        beats = [r for _, r in items if isnum(r.get("eps_actual")) and isnum(r.get("eps_estimate"))]
        n_beat = sum(1 for r in beats if r["eps_actual"] > r["eps_estimate"])
        sur = [r["surprise_pct"] for r in beats if isnum(r.get("surprise_pct"))]
        moves = [r["reaction"] for _, r in items if r.get("reaction") is not None]
        nxt_txt = "n/a"
        if nxt:
            timing = {"bmo": T("before the open"), "amc": T("after the close")}.get(nxt.get("hour") or "", "")
            nxt_txt = D(dt.date.fromisoformat(nxt["date"]), "%b %-d") + (f" · {timing}" if timing else "")
        st.html(stats_row([
            ("Next report", nxt_txt, ""),
            ("EPS estimate", f'${nxt["eps_estimate"]:,.2f}' if nxt and isnum(nxt.get("eps_estimate")) else "n/a", ""),
            ("Revenue estimate", money(nxt.get("rev_estimate"), 2) if nxt else "n/a", ""),
            ("Beat EPS estimates", T("{a} of {b}", a=n_beat, b=len(beats)) if beats else "n/a", ""),
            ("Average EPS surprise", sgn(float(np.mean(sur)), 1) if sur else "n/a", signed_class(float(np.mean(sur))) if sur else ""),
            ("Average move on results", sgn(float(np.mean(np.abs(moves))) * 100, 1).replace("+", "±") if moves else "n/a", ""),
        ]))
        a, b = st.columns([1.15, 1], gap="medium")
        with a:
            st.html(f'<div class="mb-sec">{T("EPS: reported vs expected")} {src("rep")} {src("ana")}</div>')
            pts = [(r.get("period") or r.get("date") or "", r.get("eps_estimate"), r.get("eps_actual")) for _, r in items if isnum(r.get("eps_actual"))]
            if pts:
                labels = [_q_label(x[0]) for x in pts]
                if nxt and isnum(nxt.get("eps_estimate")):
                    labels.append(T("Next") + " · " + D(dt.date.fromisoformat(nxt["date"]), "%b %-d"))
                    pts.append(("", nxt["eps_estimate"], None))
                st.plotly_chart(charts.earnings_dots(labels, [x[1] for x in pts], [x[2] for x in pts],
                                                     names=(T("Expected"), T("Beat"), T("Missed"))),
                                config=charts.CONFIG, key=f"eps_{t}_{lang()}")
            else:
                st.caption(T("No reported EPS available."))
        with b:
            st.html(f'<div class="mb-sec">{T("Each report")} {src("rep")} {src("mkt")}</div>')
            body = ""
            for _, r in reversed(items):
                ea, ee = r.get("eps_actual"), r.get("eps_estimate")
                ra, re_ = r.get("rev_actual"), r.get("rev_estimate")
                verdict = ""
                if isnum(ea) and isnum(ee):
                    verdict = f'<span class="mb-lean {"up" if ea > ee else "down" if ea < ee else "hold"}">{T("Beat") if ea > ee else T("Missed") if ea < ee else T("In line")}</span>'
                rev = (f'{money(ra, 1)}' + (f' <span class="co">{T("vs")} {money(re_, 1)}</span>' if isnum(re_) else "")) if isnum(ra) else "n/a"
                body += (f'<tr><td class="l">{esc(_q_label(r.get("period") or r.get("date") or ""))}'
                         f'<span class="co">{D(dt.date.fromisoformat(r["date"]), "%b %-d, %Y") if r.get("date") else ""}</span></td>'
                         f'<td class="num">{f"${ea:,.2f}" if isnum(ea) else "n/a"}<span class="co">{T("vs")} {f"${ee:,.2f}" if isnum(ee) else "n/a"}</span></td>'
                         f'<td>{verdict}</td><td class="num">{rev}</td>'
                         f'<td class="num {signed_class(r.get("reaction"))}">{pct(r.get("reaction"), 1) if r.get("reaction") is not None else "n/a"}</td></tr>')
            st.html(f'<div class="mb-scroll"><table class="mb-tbl"><tr><th class="l">{T("Quarter")}</th><th>EPS</th><th></th>'
                    f'<th>{T("Revenue")}</th><th>{T("Stock move")}</th></tr>{body}</table></div>'
                    '<p class="mb-foot">' + T("Quarter = fiscal period end. Stock move = close-to-close on the first session after the report (the report day if it came before the open). Estimates are the analysts' consensus from Finnhub.") + "</p>")
    # quarterly trend from the 10-Q filings
    qs = (f or {}).get("quarters") or {}
    rev = qs.get("revenue")
    if rev is not None and len(rev) >= 4:
        df = rev.set_index("end")[["value", "derived"]].rename(columns={"value": "revenue"})
        for k in ("net_income", "operating_income", "gross_profit"):
            s = qs.get(k)
            if s is not None and len(s):
                df[k] = s.set_index("end")["value"].reindex(df.index)
        df = df.tail(9)
        df["yoy"] = df["revenue"] / df["revenue"].shift(4) - 1
        show = df.tail(8 if len(df) >= 8 else len(df))
        labels = [_q_label(e) for e in show.index]
        st.html(f'<div class="mb-sec">{T("Quarterly results")} <span class="mb-tagx">{T("SEC 10-Q and 10-K")}</span> {src("rep")}</div>')
        q1, q2 = st.columns([1.15, 1], gap="medium")
        with q1:
            st.plotly_chart(charts.financial_bars(labels, [(T("Revenue"), list(show["revenue"] / 1e9), "accent")] + (
                [(T("Net income"), list(show["net_income"] / 1e9), "teal")] if "net_income" in show else []), height=280),
                config=charts.CONFIG, key=f"qrev_{t}_{lang()}")
        with q2:
            body = ""
            for e_, r in show.iloc[::-1].iterrows():
                om = r.get("operating_income") / r["revenue"] if isnum(r.get("operating_income")) and r["revenue"] else None
                nm = r.get("net_income") / r["revenue"] if isnum(r.get("net_income")) and r["revenue"] else None
                body += (f'<tr><td class="l">{esc(_q_label(e_))}{" *" if r["derived"] else ""}</td><td class="num">{money(r["revenue"], 1)}</td>'
                         f'<td class="num {signed_class(r["yoy"]) if isnum(r["yoy"]) else ""}">{pct(r["yoy"], 1) if isnum(r["yoy"]) else "n/a"}</td>'
                         f'<td class="num">{pct(om, 1, False) if om is not None else "n/a"}</td><td class="num">{pct(nm, 1, False) if nm is not None else "n/a"}</td></tr>')
            st.html(f'<div class="mb-scroll"><table class="mb-tbl"><tr><th class="l">{T("Quarter ending")}</th><th>{T("Revenue")}</th>'
                    f'<th>{T("vs a year ago")}</th><th>{T("Operating margin")}</th><th>{T("Net margin")}</th></tr>{body}</table></div>'
                    '<p class="mb-foot">' + T("* Fourth fiscal quarter: there is no 10-Q for it, so it is the fiscal year from the 10-K minus the first three quarters.") + "</p>")


# =========================================================================== Valuation
def valuation(c: dict) -> dict | None:
    t, q, m, rf, rf_label, hist = c["t"], c["q"], c["m"], c["rf"], c["rf_label"], c["hist"]
    price = q["price"]
    with st.spinner(T("Reading SEC filings…")):
        f = safe(data.company_fundamentals, t)
    with st.spinner(T("Loading comparable companies…")):
        comps, implied_peers = peer_comps(t, price, c["met"])
    if not f or f["fcf"].empty or not f["shares"]:
        st.info(T("A DCF isn't available for {t}: it needs SEC filings with free cash flow and a share count (non-US companies, ETFs and funds aren't covered).", t=t))
        comps_block(c, comps, implied_peers)
        return None
    shares, mcap = f["shares"], price * f["shares"]
    last_year, last_fcf = int(f["fcf"].index[-1]), float(f["fcf"].iloc[-1])
    eps = float(f["eps"].iloc[-1]) if not f["eps"].empty else None
    d = dcf_defaults(f, m, rf, price)

    with st.expander(T("DCF assumptions — change them and everything below updates"), expanded=False):
        a1, a2, a3 = st.columns(3)
        base_choice = choice(a1.radio, T("Starting free cash flow"), ["Latest year", "3-year average"], key=f"base_{t}", default="Latest year", horizontal=True)
        growth = a2.slider(T("FCF growth, years 1 to 5 (%)"), -10.0, 40.0, round(d["growth"] * 100, 1), 0.5, key=f"g_{t}") / 100
        g_term = a3.slider(T("Terminal growth (%)"), 0.0, 4.0, 2.5, 0.1, key=f"gt_{t}") / 100
        b1, b2, b3, b4 = st.columns(4)
        erp = b1.number_input(T("Equity risk premium (%)"), 3.0, 8.0, 5.0, 0.25, key=f"erp_{t}") / 100
        beta_in = b2.number_input("Beta", 0.3, 3.0, round(d["beta"], 2), 0.05, key=f"beta_{t}")
        kd = b3.number_input(T("Pre-tax cost of debt (%)"), 1.0, 12.0, round((rf + 0.015) * 100, 2), 0.25, key=f"kd_{t}") / 100
        tax = b4.number_input(T("Tax rate (%)"), 0.0, 35.0, 21.0, 1.0, key=f"tax_{t}") / 100
        w = analysis.wacc(rf, beta_in, erp, kd, tax, mcap, f["debt"])
        discount = st.slider(T("Discount rate used (WACC, %)"), 4.0, 16.0, round(w["wacc"] * 100, 1), 0.1,
                             key=f"wacc_{t}_{round(w['wacc'] * 100, 1)}") / 100
        base_fcf = last_fcf if base_choice == "Latest year" else float(f["fcf"].iloc[-3:].mean())
        st.caption(T("Starting FCF {fcf}. Default growth = last five years' revenue CAGR ({g}) capped at 0 to 20%; years 6 to 10 fade to terminal growth. Cost of equity {rf} + {b} × {erp} = {ke}; weights {we} equity / {wd} debt; WACC {w}. {rfl}.",
                       fcf=money(base_fcf), g=pct(d['hist_g']) if d['hist_g'] is not None else 'n/a', rf=pct(rf, 2, False), b=f"{beta_in:.2f}",
                       erp=pct(erp, 2, False), ke=pct(w['cost_of_equity'], 2, False), we=pct(w['we'], 0, False), wd=pct(w['wd'], 0, False),
                       w=pct(w['wacc'], 2, False), rfl=rf_label))

    result = {"fundamentals": f, "mcap": mcap, "eps": eps, "last_year": last_year}
    if base_fcf <= 0:
        st.info(T("Free cash flow is negative, so a cash-flow DCF doesn't apply. Revenue growth and the path to profitability are the better lens."))
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
        st.html(f'<div class="mb-verdict"><div><div class="k">{T("Intrinsic value per share")} {src("calc")}</div><div class="v num">${base.per_share:,.2f}</div>'
                f'<div class="k">{T("Bear")} ${bear.per_share:,.0f} · {T("Bull")} ${bull.per_share:,.0f}</div></div>'
                f'<div><div class="k">{T("Market price")} {src("mkt")}</div><div class="v num">${price:,.2f}</div>'
                f'<div class="k">{T("Upside to intrinsic value")} <b style="color:{color}">{pct(gap)}</b></div></div>'
                f'<div><div class="k">{T("Verdict under these assumptions")}</div><div class="label" style="color:{color}">{T(label)}</div>'
                f'<div class="k">{T("Within ±15% counts as fairly valued")}</div></div></div>')
        if implied is not None:
            st.html('<div class="mb-callout">' + T("<b>What the price implies.</b> To be worth ${p}, free cash flow would need to grow about <b>{g} a year for five years</b>, then fade to {gt}, at a {d} discount rate. Revenue grew {h} a year over the last five years.",
                    p=f"{price:,.2f}", g=pct(implied), gt=pct(g_term, 1, False), d=pct(discount, 1, False),
                    h=pct(d["hist_g"]) if d["hist_g"] is not None else "n/a") + "</div>")
        rates = [round(discount + x, 4) for x in (-0.02, -0.01, 0.0, 0.01, 0.02)]
        terms = [round(g_term + x, 4) for x in (-0.01, -0.005, 0.0, 0.005, 0.01)]
        sens = analysis.sensitivity(base_fcf, growth, f["net_debt"], shares, rates, terms)
        inner = sens.loc[rates[1:4], terms[1:4]].to_numpy()
        lo3, hi3 = analysis.statistical_range(price, m["volatility"], 63) if m["volatility"] else (None, None)
        st.html(f'<div class="mb-sec">{T("Valuation ranges (football field)")} {src("calc")}</div>')
        st.plotly_chart(charts.football_field([
            (T("DCF scenarios, bear to bull"), bear.per_share, bull.per_share),
            (T("DCF sensitivity (WACC ±1, g ±0.5)"), float(np.nanmin(inner)), float(np.nanmax(inner))),
            (T("52-week trading range"), c["low52"], c["high52"]),
            (T("3-month statistical range"), lo3, hi3),
        ] + peer_ff_row(implied_peers), price), config=charts.CONFIG, key=f"ff_{t}_{lang()}")
        st.caption(T("Bear: growth 5 points lower, discount rate 1 point higher. Bull: the opposite."))
        with st.expander(T("Sensitivity table and DCF detail")):
            show = sens.copy()
            show.index = [pct(r, 1, False) for r in show.index]
            show.columns = [pct(gg, 1, False) for gg in show.columns]
            st.markdown(T("**Intrinsic value per share** — rows: discount rate, columns: terminal growth"))
            st.dataframe(show.style.format("${:,.0f}", na_rep="n/m"))
            proj = base.projections.copy()
            proj["Growth"] = proj["Growth"].map(pct)
            for col in ("FCF", "PV of FCF"):
                proj[col] = proj[col].map(money)
            proj["Discount factor"] = proj["Discount factor"].map(lambda x: f"{x:.3f}")
            st.dataframe(proj.rename(columns=lambda col: T(str(col))), hide_index=True)
            st.caption(T("Discounted FCF {a} + discounted terminal value {b} = EV {ev}; − net debt {nd} = equity {eq}; ÷ {sh}B shares = ${ps}. Terminal value is {ts} of EV.",
                         a=money(base.pv_fcf), b=money(base.pv_terminal), ev=money(base.enterprise_value), nd=money(f['net_debt']),
                         eq=money(base.equity_value), sh=f"{shares / 1e9:,.2f}", ps=f"{base.per_share:,.2f}", ts=pct(base.terminal_share, 0, False)))
        result.update({"base": base.per_share, "bear": bear.per_share, "bull": bull.per_share, "growth": growth,
                       "g_term": g_term, "discount": discount, "implied": implied, "label": label, "gap": gap, "source": "your"})
        st.session_state[f"val_{t}"] = result
    st.html(f'<div class="mb-sec">{T("Multiples")} {src("rep")} {src("calc")}</div>' + stats_row([
        ("Market cap", money(mcap), ""), (f"P/E, FY{last_year}", f"{price / eps:,.1f}x" if eps and eps > 0 else "n/m", ""),
        (f"Price / FCF, FY{last_year}", f"{mcap / last_fcf:,.1f}x" if last_fcf > 0 else "n/m", ""),
        ("FCF yield", pct(last_fcf / mcap, signed=False) if last_fcf > 0 else "n/m", ""),
        ("EV / FCF", f"{(mcap + f['net_debt']) / last_fcf:,.1f}x" if last_fcf > 0 else "n/m", "")]))
    comps_block(c, comps, implied_peers)
    return result


# =========================================================================== comparable companies
def peer_list(t: str) -> list[str]:
    key = f"peers_{t}"
    if key not in st.session_state:
        st.session_state[key] = (safe(data.peers, t, default=[]) or [])[:7]
    return [x for x in st.session_state[key] if x != t]


def peer_comps(t: str, price: float, own: dict) -> tuple[list[dict], dict]:
    rows = []
    for x in peer_list(t)[:10]:
        met = safe(data.basic_metrics, x, default={}) or {}
        if not met:
            continue
        p = safe(data.profile, x, default={}) or {}
        cap = (met.get("marketCapitalization") or 0) * 1e6 or p.get("market_cap")
        rows.append({"ticker": x, "name": p.get("name") or x, "met": met, "cap": cap})
    return rows, analysis.peer_implied(own or {}, [r["met"] for r in rows], price)


def peer_ff_row(implied: dict) -> list[tuple[str, float, float]]:
    vals = [v["implied"] for k, v in implied.items() if k in ("P/E", "EV/EBITDA", "P/S") and v.get("implied")]
    return [(T("Peer multiples (P/E, EV/EBITDA, P/S)"), min(vals), max(vals))] if len(vals) >= 2 else []


def comps_block(c: dict, comps: list[dict], implied: dict) -> None:
    t, price = c["t"], c["q"]["price"]
    st.html(f'<div class="mb-sec">{T("Comparable companies")} {src("mkt")} {src("calc")}</div>')
    suggested = (safe(data.peers, t, default=[]) or [])[:12]
    options = list(dict.fromkeys(suggested + st.session_state.get(f"peers_{t}", []) + [x for x, _ in data.MEGA_CAPS if x != t]))
    st.multiselect(T("Peer group (Finnhub's suggestion; add or remove tickers as an analyst would)"), options, key=f"peers_{t}",
                   max_selections=10, accept_new_options=True)
    if not comps:
        st.caption(T("No comparable companies available for {t}.", t=t))
        return
    own_cap = (c["met"].get("marketCapitalization") or 0) * 1e6 or c["p"].get("market_cap")
    mult_keys, qual_keys = list(analysis.COMP_MULTIPLES), list(analysis.COMP_QUALITY)

    def cells(met: dict) -> str:
        out = ""
        for k in mult_keys:
            v = analysis.metric_value(met, analysis.COMP_MULTIPLES[k], positive=True)
            out += f'<td class="num">{f"{v:,.1f}x" if v is not None and v < 500 else "n/m"}</td>'
        for k in qual_keys:
            v = analysis.metric_value(met, analysis.COMP_QUALITY[k])
            out += f'<td class="num {signed_class(v) if k in ("Revenue growth", "ROE") else ""}">{f"{v:,.1f}%" if v is not None else "n/a"}</td>'
        return out

    rows = (f'<tr class="hl"><td class="l"><b>{esc(t)}</b><span class="co">{esc(c["p"].get("name") or t)}</span></td>'
            f'<td class="num">{money(own_cap, 1)}</td>{cells(c["met"])}</tr>')
    for r in comps:
        rows += (f'<tr><td class="l"><a href="{link({"p": "stock", "t": r["ticker"]})}" target="_self">{esc(r["ticker"])}</a>'
                 f'<span class="co">{esc(r["name"])}</span></td><td class="num">{money(r["cap"], 1)}</td>{cells(r["met"])}</tr>')
    med = ""
    for k in mult_keys:
        v = implied.get(k, {}).get("median")
        med += f'<td class="num"><b>{f"{v:,.1f}x" if v else "–"}</b></td>'
    for k in qual_keys:
        vals = [x for x in (analysis.metric_value(r["met"], analysis.COMP_QUALITY[k]) for r in comps) if x is not None]
        med += f'<td class="num"><b>{f"{float(np.median(vals)):,.1f}%" if len(vals) >= 2 else "–"}</b></td>'
    rows += f'<tr><td class="l"><b>{T("Peer median")}</b></td><td></td>{med}</tr>'
    head = "".join(f"<th>{T(h)}</th>" for h in ["Market cap"] + mult_keys + qual_keys)
    st.html(f'<div class="mb-scroll"><table class="mb-tbl"><tr><th class="l">{T("Company")}</th>{head}</tr>{rows}</table></div>')
    imp = [(k, v) for k, v in implied.items() if v.get("implied")]
    if imp:
        st.html(stat_grid_imp(imp, price))
    st.html('<p class="mb-foot">' + T("Peers are the companies Finnhub groups in the same industry; multiples are trailing twelve months. Implied value = today's price × peer median ÷ this company's multiple: what the stock would be worth on its peers' valuation. Peers are rarely perfect matches, so read it next to the DCF, not instead of it.") + "</p>")


def stat_grid_imp(imp: list[tuple[str, dict]], price: float) -> str:
    cells = "".join(
        f'<div class="mb-stat"><div class="k">{T("Value at peer median {m}", m=k)}</div><div class="v num">${v["implied"]:,.2f}</div>'
        f'<div class="s {signed_class(v["implied"] / price - 1)}">{pct(v["implied"] / price - 1)} {T("vs price")} · '
        f'{T("{n} peers", n=v["n"])}</div></div>' for k, v in imp)
    return f'<div class="mb-stats" style="--cols:{len(imp)};margin-top:.6rem">{cells}</div>'


# =========================================================================== Outlook
def outlook(c: dict) -> None:
    t, hist, q = c["t"], c["hist"], c["q"]
    labels = {"neutral": "No trend", "market": "Market average (+8%/yr)", "trend": "Recent trend (capped ±30%/yr)"}
    picked = choice(st.segmented_control, T("Trend assumption"), list(labels.values()), key=f"drift_{t}",
                    default=labels["neutral"]) or labels["neutral"]
    drift = next(k for k, v in labels.items() if v == picked)
    dcf_val = None
    f = safe(data.company_fundamentals, t)
    if f:
        v = analysis.default_valuation(f, q["price"], c["m"]["beta"], c["rf"])
        dcf_val = v["per_share"] if v else None
    with st.spinner(T("Simulating 4,000 scenarios…")):
        out = outlook_for(t, drift, float(hist["close"].iloc[-1]), c["high52"], dcf_val)
    if not out:
        st.info(T("Not enough price history to simulate scenarios."))
        return
    start = out["start"]
    pr = out["probs"]
    cards = [(pr["finish_up"], T("of scenarios end the 6 months above today's close")), (pr["drop_20"], T("of scenarios fall 20% or more at some point")),
             (pr["touch_high"], T("of scenarios reach the 52-week high (${v})", v=f"{c['high52']:,.2f}"))]
    if pr["touch_target"] is not None:
        cards.append((pr["touch_target"], T("of scenarios touch the DCF value (${v})", v=f"{dcf_val:,.2f}")))
    st.html(f'<div class="mb-sec">{T("Model probabilities over 6 months")} {src("calc")}</div><div class="mb-prob">' + "".join(
        f'<div><div class="v num">{v:.0%}</div><div class="k">{esc(k)}</div><div class="bar"><i style="width:{v * 100:.0f}%"></i></div></div>'
        for v, k in cards if v is not None) + "</div>")
    st.plotly_chart(charts.fan_chart(hist["close"], out["fan"], [(T("52-week high"), c["high52"], "up"), (T("DCF value"), dcf_val, "violet"),
                                                                 (T("52-week low"), c["low52"], "down")]),
                    config=charts.CONFIG, key=f"fan_{t}_{drift}_{lang()}")
    a, b = st.columns([1.4, 1], gap="medium")
    with a:
        head = "".join(f"<th>{T(lab)}<br><span style='font-weight:400;color:var(--faint)'>{T('{p}th pct', p=pc)}</span></th>"
                       for lab, pc in zip(analysis.OUTLOOK_LABELS, analysis.OUTLOOK_PERCENTILES))
        rows = ""
        for h, vals in out["table"].items():
            rows += f'<tr><td class="l">{T(h)}</td>' + "".join(
                f'<td class="num">${v:,.2f}<br><span class="{signed_class(v / start - 1)}" style="font-size:.74rem">{pct(v / start - 1)}</span></td>'
                for v in vals) + "</tr>"
        st.html(f'<div class="mb-sec">{T("Scenario table")}</div><div class="mb-scroll"><table class="mb-tbl"><tr><th class="l">{T("Horizon")}</th>{head}</tr>{rows}</table></div>')
    with b:
        st.html(f'<div class="mb-sec">{T("How this works")}</div><div class="mb-callout">' + T("4,000 six-month paths. Each simulated day replays a real daily move of {t} from the last two years, so crash days and rallies keep their real frequency. The trend assumption replaces the average move. These are <b>model probabilities, not forecasts</b>: they assume the next six months look like a reshuffled version of the past two years.", t=esc(t)) + "</div>")


# =========================================================================== Compare
def compare(c: dict) -> None:
    t = c["t"]
    peers = [x for x in c["wl"] if x != t][:3]
    picks = st.multiselect(T("Compare with"), list(dict.fromkeys([BENCHMARK, "QQQ"] + c["wl"] + [x for x, _ in data.MEGA_CAPS])),
                           default=[BENCHMARK] + peers, key=f"cmp_{t}", max_selections=5)
    rng = st.segmented_control(T("Period"), ["3M", "6M", "1Y", "3Y", "5Y"], default="1Y", key=f"cmprng_{t}") or "1Y"
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
    st.html(f'<div class="mb-scroll"><table class="mb-tbl"><tr><th class="l">Ticker</th><th>{T("Return")}</th><th>{T("Volatility")}</th>'
            f'<th>{T("Max drawdown")}</th><th>{T("Correlation with {t}", t=esc(t))}</th></tr>{"".join(rows)}</table></div><p class="mb-foot">'
            + T("More options on the <a href=\"{u}\" target=\"_self\">Compare</a> page, including an equal-weight portfolio.", u=link({"p": "compare"})) + "</p>")


# =========================================================================== News
def news(c: dict) -> list[dict]:
    items = safe(data.company_news, c["t"], default=[]) or []
    if not items:
        st.info(T("No company news in the last 7 days."))
        return []
    st.html(f'<div class="mb-panel"><div class="mb-h"><b>{T("Latest news on {t}", t=esc(c["t"]))}</b><span>Finnhub {src("mkt")}</span></div><div class="mb-news">' + "".join(
        f'<div><a class="t" href="{esc(n["url"])}" target="_blank" rel="noopener">{esc(n["title"])}</a>'
        f'<div class="m">{esc(n["source"])} · {D(n["time"], "%b %d, %-I:%M %p")}</div>'
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
    return f'<span class="mb-lean {cls}{" big" if big_text else ""}">{esc(T(lean) if lean else "n/a")}</span>'


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
    head = (f'<div class="mb-kicker">{T("What the experts say")}</div><div class="mb-h"><b>{T("Wall Street consensus")}</b>'
            f'<span>{T("Finnhub recommendation trends")} {src("ana")}</span></div>')
    if not cs:
        return f'<div class="mb-panel mb-take">{head}<p class="mb-foot">{T("No analyst ratings available for {t}.", t=esc(t))}</p></div>', None
    trend = ""
    old = analysis.consensus(recs[3]) if len(recs) > 3 else (analysis.consensus(recs[-1]) if len(recs) > 1 else None)
    if old:
        d = cs["score"] - old["score"]
        word = T("more bullish") if d > 0.02 else T("more bearish") if d < -0.02 else T("unchanged")
        trend = f' · {word} {T("vs")} {old["period"]}'
    k, n, pal = cs["counts"], cs["n"], P()
    colors = {"strongBuy": pal["up"], "buy": pal["up"] + "99", "hold": pal["faint"], "sell": pal["down"] + "99", "strongSell": pal["down"]}
    names = {"strongBuy": T("Strong Buy"), "buy": T("Buy"), "hold": T("Hold"), "sell": T("Sell"), "strongSell": T("Strong Sell")}
    bar = "".join(f'<i style="width:{k[x] / n * 100:.2f}%;background:{colors[x]}" title="{names[x]} {k[x]}"></i>' for x in names if k[x])
    legend = " · ".join(f'<span><b style="background:{colors[x]}"></b>{names[x]} {k[x]}</span>' for x in names)
    html_ = (f'<div class="mb-panel mb-take">{head}<div class="mb-take-row">{lean_badge(cs["label"])}'
             f'<div><div class="mb-score num">{cs["score"]:.2f} <small>/ 5</small></div>'
             f'<div class="mb-foot" style="margin:0">{n} {T("analysts")} · {cs["period"]}{trend}</div></div></div>'
             f'<div class="mb-stack">{bar}</div><div class="mb-legend">{legend}</div>'
             f'<p class="mb-foot">{T("Ratings from the brokerage analysts that cover the stock, aggregated monthly by Finnhub (5 = strong buy, 1 = strong sell). Price targets are not in the free plan.")}</p></div>')
    return html_, cs


def analysts_section(c: dict) -> None:
    t = c["t"]
    key = f"take_{t}_{lang()}"
    val = st.session_state.get(f"val_{t}")
    using_yours = bool(val and val.get("base"))
    card, cs = consensus_card(t)
    left, right = st.columns(2, gap="medium")
    left.html(card)
    with right:
        take = st.session_state.get(key)
        head = (f'<div class="mb-kicker">{T("Model view")}</div><div class="mb-h"><b>{T("AI take")}</b>'
                f'<span>{T("Gemini reads the data on this page")} {src("ai")}</span></div>')
        if take and take.get("lean"):
            agree = ""
            if cs:
                same = (take["lean"] == "Buy" and cs["label"] in ("Buy", "Strong Buy")) or (take["lean"] == "Sell" and cs["label"] in ("Sell", "Strong Sell")) \
                    or (take["lean"] == "Hold" and cs["label"] == "Hold")
                agree = f'<span class="mb-chip {"up" if same else "flat"}">{T("Agrees with Wall Street") if same else T("Differs from Wall Street")}</span>'
            conv = f'<div class="mb-foot" style="margin:0">{T("Conviction")}: {esc(T(take.get("conviction") or "n/a"))}</div>'
            written = T("Model opinion from the data in this app, written {d} ET. Not investment advice.", d=D(take["generated_at"], "%b %d, %-I:%M %p"))
            st.html(f'<div class="mb-panel mb-take">{head}<div class="mb-take-row">{lean_badge(take["lean"])}<div>{agree}{conv}</div></div>'
                    f'<p class="mb-p">{esc(take.get("lean_reason", ""))}</p>'
                    f'<p class="mb-p"><b>{T("Vs the consensus.")}</b> {esc(take.get("vs_consensus", ""))}</p>'
                    f'<p class="mb-foot">{written}</p></div>')
        else:
            st.html(f'<div class="mb-panel mb-take">{head}<p class="mb-p">'
                    + T("Click the button for a written take with a <b>Buy / Hold / Sell</b> lean, compared against the Wall Street consensus, plus bull, base and bear cases, risks and catalysts.") + " "
                    + (T("It uses the <b>DCF assumptions set in the Valuation tab</b>.") if using_yours else
                       T("It uses the default DCF assumptions; open the Valuation tab and adjust them first to use yours."))
                    + '</p><p class="mb-foot">' + T("Data: fetched from the sources · Calc: computed by the app · AI: model opinion.") + "</p></div>")
        label = T("Refresh AI take") if take else T("Generate AI take")
        clicked = st.button(label, type="primary", key=f"btn_{key}", width="stretch")
    if clicked:
        with st.spinner(T("Collecting the data and writing the take… (10 to 30 seconds)")):
            v = val if using_yours else default_val(c)
            out = safe(outlook_for, t, "neutral", float(c["hist"]["close"].iloc[-1]), c["high52"], None)
            news_items = safe(data.company_news, t, default=[]) or []
            assumptions = (f"{v.get('growth', 0):.4f}|{v.get('g_term', 0):.4f}|{v.get('discount', 0):.4f}|{v.get('source')}"
                           if v and v.get("base") else "none")
            try:
                st.session_state[key] = ai.stock_take(t, c["p"].get("name") or t, dt.date.today().isoformat(), assumptions, lang(),
                                                      ai_data_text(c, v, out), news_items)
                st.rerun()
            except Exception as exc:
                st.warning(T("The AI take couldn't be written this time: {e}", e=exc))
    take = st.session_state.get(key)
    if not take:
        return
    body = "".join(f'<p><b>{T(title)}.</b> {esc(take[k])}</p>' for title, k in (
        ("Where it stands", "situation"), ("Recent performance", "recent_performance"), ("Fundamentals", "fundamentals"),
        ("Valuation", "valuation"), ("News flow", "news")) if take.get(k))
    cases = "".join(f'<div class="mb-story"><h3>{T(title)}</h3><p>{esc(take.get(k, ""))}</p></div>'
                    for title, k in (("Bear case", "bear_case"), ("Base case", "base_case"), ("Bull case", "bull_case")))
    risks = "".join(f"<li>{esc(r)}</li>" for r in take.get("risks", []))
    cats = "".join(f"<li>{esc(x)}</li>" for x in take.get("catalysts", []))
    st.html(f'<div class="mb-sec">{T("Full AI analysis")} {src("ai")}</div><div class="mb-story top">{body}</div><div class="mb-grid3">{cases}</div>'
            f'<div class="mb-grid2"><div class="mb-story"><h3>{T("Main risks")}</h3><ul>{risks}</ul></div>'
            f'<div class="mb-story"><h3>{T("Coming catalysts")}</h3><ul>{cats}</ul></div></div>'
            f'<div class="mb-callout"><b>{T("Conclusion.")}</b> {esc(take.get("conclusion", ""))}</div><p class="mb-note">'
            + T("Not investment advice · statistics describe the past, they don't predict the future.") + "</p>")


# =========================================================================== PDF report
def _pdf_labels() -> dict:
    return {
        "kicker": T("EQUITY REPORT"), "band": T("Equity report") + " · " + D(dt.date.today(), "%b %-d, %Y"),
        "footer": T("Market Brief · tomas-market-brief.streamlit.app · For information and learning, not investment advice"),
        "page": T("Page {n}"), "perf": T("Price vs the S&P 500, last year"), "period": T("Period"), "diff": T("Difference"),
        "key_stats": T("Key statistics"), "financials": T("Financials and ratios"), "checks": T("Health checks"),
        "eva": T("Economic value added"), "valuation": T("Valuation"), "comps": T("Comparable companies"),
        "earnings": T("Earnings record"), "eps_chart": T("EPS: reported vs expected"), "risk": T("Risk"),
        "street": T("Wall Street consensus"), "ai": T("AI take"), "price": T("Price"),
        "src_mkt": T("Source: Twelve Data, Finnhub"), "src_mkt_calc": T("Source: market data · calculated"),
        "src_rep": T("Source: SEC 10-K filings · calculated"), "src_calc": T("Calculated by the app"),
        "src_comps": T("Source: Finnhub peers and multiples (TTM)"), "src_earn": T("Source: Finnhub, SEC"),
        "src_ana": T("Source: Finnhub recommendation trends"), "src_ai": T("AI-written from the app's data (Google Gemini)"),
        "disclaimer": T("Every figure comes from the sources named in each section or is calculated from them; AI text is labeled. Statistics describe the past and don't predict the future. This report is for information and learning and is not investment advice."),
    }


def report_data(c: dict) -> dict:
    t, q, hist, m, met, prof = c["t"], c["q"], c["hist"], c["m"], c["met"], c["p"]
    price = float(q["price"])
    close, bench = hist["close"], c["bench"]
    val = st.session_state.get(f"val_{t}") or safe(default_val, c) or {}
    f = val.get("fundamentals") or safe(data.company_fundamentals, t)
    recs = safe(data.recommendations, t, default=[]) or []
    cs = analysis.consensus(recs[0]) if recs else None
    r: dict = {"labels": _pdf_labels(), "ticker": t, "name": prof.get("name") or t, "price": price, "change_pct": q.get("pct"),
               "change_txt": f'{sgn(q.get("change") or 0, 2, "")} ({sgn(q.get("pct") or 0)})',
               "asof": T("As of {d}", d=when(q.get("time"))),
               "meta_line": " · ".join(x for x in (t, (prof.get("exchange") or "").replace("NASDAQ NMS - GLOBAL MARKET", "Nasdaq"),
                                                   T(prof.get("industry") or ""), prof.get("country") or "") if x)}
    # KPIs
    k = [(T("Market cap"), money(prof.get("market_cap"), 1), "", None)]
    if val.get("base"):
        k.append((T("DCF value"), f'${val["base"]:,.0f}', T("{g} vs price", g=pct(val["gap"], 0)), tone(val["gap"])))
        k.append((T("Bear – bull"), f'${val["bear"]:,.0f}–{val["bull"]:,.0f}', T("DCF scenarios"), None))
    k.append((T("1-year return"), pct(m["ret_1y"], 1), T("S&P 500 {x}", x=pct(analysis.period_return(bench, 252), 1)) if bench is not None else "",
              tone(m["ret_1y"])))
    if cs:
        k.append((T("Wall Street"), T(cs["label"]), T("{s} / 5 · {n} analysts", s=f'{cs["score"]:.2f}', n=cs["n"]), None))
    take = st.session_state.get(f"take_{t}_{lang()}")
    if take and take.get("lean"):
        k.append((T("AI lean"), T(take["lean"]), T("Conviction") + ": " + T(take.get("conviction") or "n/a"), None))
    r["kpis"] = k[:6]
    # one-line summary from the numbers (no AI)
    bits = []
    if val.get("base"):
        bits.append(T("At ${p} the stock trades {g} its DCF value of ${v} (base case, {src}).", p=f"{price:,.2f}",
                      g=T("{x} below", x=pct(abs(val['gap']), 0, False)) if val["gap"] > 0 else T("{x} above", x=pct(abs(val['gap']), 0, False)),
                      v=f'{val["base"]:,.0f}', src=T("your assumptions") if val.get("source") == "your" else T("default assumptions")))
        if val.get("implied") is not None:
            bits.append(T("The price implies about {g} a year of free-cash-flow growth for five years.", g=pct(val["implied"], 1, False)))
    if cs:
        bits.append(T("Wall Street's consensus is {l} ({s} / 5).", l=T(cs["label"]), s=f'{cs["score"]:.2f}'))
    r["summary"] = " ".join(bits)
    # chart: 1 year rebased
    df = pd.DataFrame({"s": close, "b": bench}).dropna().iloc[-253:] if bench is not None else pd.DataFrame({"s": close}).iloc[-253:]
    r["chart"] = {"stock": list((df["s"] / df["s"].iloc[0] - 1) * 100),
                  "bench": list((df["b"] / df["b"].iloc[0] - 1) * 100) if "b" in df else [],
                  "dates": [D(d, "%b %Y") for d in df.index]}
    perf = []
    for label, n in (("1 month", 21), ("3 months", 63), ("YTD", None), ("1 year", 252), ("3 years", 756)):
        r1 = analysis.ytd_return(close) if n is None else analysis.period_return(close, n)
        r2 = (analysis.ytd_return(bench) if n is None else analysis.period_return(bench, n)) if bench is not None else None
        if r1 is None:
            continue
        rel = r1 - r2 if r2 is not None else None
        perf.append([T(label), (pct(r1), tone(r1)), (pct(r2), tone(r2)), (pct(rel), tone(rel))])
    r["perf_rows"] = perf
    dy = met.get("currentDividendYieldTTM") or met.get("dividendYieldIndicatedAnnual")
    r["key_stats"] = [[T(a), b] for a, b in (
        ("P/E (TTM)", num(met.get("peTTM"), 1, "x") if (met.get("peTTM") or 0) > 0 else "n/m"),
        ("EPS (TTM)", f'${met["epsTTM"]:,.2f}' if isnum(met.get("epsTTM")) else "n/a"),
        ("Dividend yield", f"{dy:.2f}%" if isnum(dy) and dy else T("None")),
        ("52-week range", f'{c["low52"]:,.2f} – {c["high52"]:,.2f}'),
        ("Volatility", pct(m["volatility"], 1, False)), ("Beta vs SPY", num(m["beta"])),
        ("Sharpe, 1Y", num(m["sharpe"])), ("Max drawdown, 1Y", pct(m["max_drawdown"], 1)))]
    # financials and ratios
    if f and not f["revenue"].empty:
        ratios = analysis.statement_analysis(f)
        years = list(ratios.columns)[-5:]
        g = lambda s_, y: float(s_[y]) if s_ is not None and y in s_.index and isnum(s_[y]) else None  # noqa: E731
        rows, groups = [], set()
        def add_group(name):
            groups.add(len(rows))
            rows.append([name] + [""] * len(years))
        add_group(T("Income and cash flow"))
        for lbl, s_ in (("Revenue", f["revenue"]), ("Operating income", f["operating_income"]), ("Net income", f["net_income"]),
                        ("Free cash flow", f["fcf"])):
            rows.append([T(lbl)] + [money(g(s_, y), 1) if g(s_, y) is not None else "n/a" for y in years])
        for grp, keys in ((T("Growth and margins"), ("revenue_growth", "gross_margin", "operating_margin", "net_margin", "fcf_margin")),
                          (T("Returns, DuPont and balance sheet"), ("roe", "roa", "asset_turnover", "equity_multiplier", "current_ratio",
                                                                   "net_debt_ebitda", "interest_coverage", "cash_conversion"))):
            add_group(grp)
            for key in keys:
                lbl = next((x[2] for x in RATIO_ROWS if x[1] == key), key)
                kind = next((x[3] for x in RATIO_ROWS if x[1] == key), "pct")
                if key not in ratios.index or ratios.loc[key, years].isna().all():
                    continue
                rows.append([T(lbl).lstrip("× ")] + [(fmt_ratio(ratios.at[key, y], kind), tone(ratios.at[key, y]) if kind == "growth" else None) for y in years])
        r["fin_years"], r["fin_rows"], r["fin_groups"] = years, rows, groups
        cols = {"good": UP_C, "watch": AMBER_C, "bad": DOWN_C}
        r["checks"] = [(T(msg, **kw), cols[lv]) for lv, msg, kw in analysis.health_checks(ratios[years])]
        wacc_v, wacc_src = wacc_for(c, f)
        e = analysis.eva(f, wacc_v)
        if not e.empty and not e["eva"].dropna().empty:
            last, yr = e.dropna(subset=["eva"]).iloc[-1], e.dropna(subset=["eva"]).index[-1]
            r["eva"] = {"kpis": [("ROIC", pct(last["roic"], 1, False), f"FY{yr}", None), ("WACC", pct(wacc_v, 1, False), "", None),
                                 ("EVA", money(last["eva"], 1), T("creates value") if last["eva"] > 0 else T("destroys value"), tone(last["eva"])),
                                 (T("Capital employed"), money(last["capital"], 1), T("debt + equity"), None)],
                        "note": T("NOPAT − WACC × capital employed. WACC {w}, {src}.", w=pct(wacc_v, 1, False), src=wacc_src)}
    # valuation
    if val.get("base"):
        _, implied_peers = peer_comps(t, price, met)
        ranges = [(T("DCF scenarios, bear to bull"), val["bear"], val["bull"]), (T("52-week trading range"), c["low52"], c["high52"])]
        if m["volatility"]:
            lo3, hi3 = analysis.statistical_range(price, m["volatility"], 63)
            ranges.append((T("3-month statistical range"), lo3, hi3))
        ranges += peer_ff_row(implied_peers)
        r["valuation"] = {
            "kpis": [(T("DCF value (base)"), f'${val["base"]:,.2f}', T("{g} vs price", g=pct(val["gap"], 0)), tone(val["gap"])),
                     (T("Growth, years 1–5"), pct(val["growth"], 1, False), T("free cash flow"), None),
                     (T("Discount rate"), pct(val["discount"], 1, False), "WACC", None),
                     (T("Terminal growth"), pct(val["g_term"], 1, False), "", None),
                     (T("Price implies"), pct(val["implied"], 1, False) if val.get("implied") is not None else "n/a", T("FCF growth, 5 years"), None)],
            "text": T("Verdict under these assumptions: {l}. Bear case ${b} (growth −5 points, discount rate +1), bull case ${u} (the opposite). {src}",
                      l=T(val["label"]), b=f'{val["bear"]:,.0f}', u=f'{val["bull"]:,.0f}',
                      src=T("Assumptions set in the app's Valuation tab.") if val.get("source") == "your" else T("Default assumptions: revenue CAGR capped at 0–20%, CAPM cost of equity with a 5% premium.")),
            "ranges": ranges, "ranges_note": T("Each bar is a range of values per share; the dashed line is today's price."),
        }
        comps, implied = peer_comps(t, price, met)
        if comps:
            mult = list(analysis.COMP_MULTIPLES)[:4]
            def mrow(name, mm):
                vals = [analysis.metric_value(mm, analysis.COMP_MULTIPLES[k], positive=True) for k in mult]
                gm = analysis.metric_value(mm, analysis.COMP_QUALITY["Revenue growth"])
                return [name] + [f"{v:,.1f}x" if v is not None and v < 500 else "n/m" for v in vals] + [f"{gm:,.1f}%" if gm is not None else "n/a"]
            rows = [mrow(t, met)] + [mrow(x["ticker"], x["met"]) for x in comps[:7]]
            rows.append([T("Peer median")] + [f'{implied[k]["median"]:,.1f}x' if implied.get(k) else "–" for k in mult] + [""])
            imp = [f'{k} ${v["implied"]:,.0f}' for k, v in implied.items() if v.get("implied")]
            r["comps_header"] = [T("Company")] + mult + [T("Revenue growth")]
            r["comps_rows"] = rows
            r["comps_note"] = (T("Value per share at the peer median: {v}.", v=", ".join(imp)) + " " if imp else "") + T("Trailing twelve months; negative multiples are not meaningful (n/m).")
    # earnings
    surprises = safe(data.earnings_surprises, t, default=[]) or []
    cal = safe(data.earnings_history, t, default=[]) or []
    by_q = {(x.get("year"), x.get("quarter")): x for x in cal}
    erows, labels, exp_, act_ = [], [], [], []
    for x in surprises[-4:]:
        h_ = by_q.get((x.get("year"), x.get("quarter")), {})
        react = analysis.earnings_reaction(close, h_["date"], h_.get("hour") or "") if h_.get("date") else None
        sp = x.get("surprise_pct")
        erows.append([_q_label(x["period"]), f'${x["actual"]:,.2f}', f'${x["estimate"]:,.2f}' if isnum(x.get("estimate")) else "n/a",
                      (sgn(sp, 1) if isnum(sp) else "n/a", tone(sp) if isnum(sp) else None),
                      (pct(react, 1) if react is not None else "n/a", tone(react))])
        labels.append(_q_label(x["period"]))
        exp_.append(x.get("estimate"))
        act_.append(x["actual"])
    if erows:
        nxt = next((x for x in cal if x["date"] >= dt.date.today().isoformat() and x.get("eps_actual") is None), None)
        r["earn_header"] = [T("Quarter"), T("EPS"), T("Expected"), T("Surprise"), T("Stock move")]
        r["earn_rows"] = list(reversed(erows))
        r["eps_chart"] = {"labels": labels, "expected": exp_, "actual": act_}
        r["earn_note"] = T("Hollow circle: analysts' estimate; filled: reported (green beat, red miss).") + (
            " " + T("Next report: {d}, EPS estimate {e}.", d=D(dt.date.fromisoformat(nxt["date"]), "%b %-d"),
                    e=f'${nxt["eps_estimate"]:,.2f}' if isnum(nxt.get("eps_estimate")) else "n/a") if nxt else "")
    tail = analysis.tail_stats(close)
    capa = analysis.capture_alpha(close, bench, c["rf"]) if bench is not None else {}
    rr = [[T("Volatility, 1 year"), pct(m["volatility"], 1, False)], [T("Beta vs S&P 500"), num(m["beta"])],
          [T("Max drawdown, 1 year"), (pct(m["max_drawdown"], 1), DOWN_C)]]
    if tail:
        rr += [[T("1 day in 20, loss at least (VaR 95%)"), pct(-tail["var95"], 2)], [T("Average loss on those days (ES 95%)"), pct(-tail["es95"], 2)]]
    if capa.get("up_capture") is not None:
        rr += [[T("Up / down capture vs S&P 500"), f'{capa["up_capture"] * 100:.0f}% / {capa["down_capture"] * 100:.0f}%']]
    if capa.get("alpha") is not None:
        rr += [[T("Alpha, 1 year (Jensen)"), (pct(capa["alpha"], 1), tone(capa["alpha"]))]]
    r["risk_rows"] = rr
    if cs:
        k_ = cs["counts"]
        r["consensus"] = {"kpis": [(T("Consensus"), T(cs["label"]), f'{cs["score"]:.2f} / 5', None),
                                   (T("Analysts"), str(cs["n"]), cs["period"], None)],
                          "note": T("Strong buy {a} · buy {b} · hold {c} · sell {d} · strong sell {e}. Sell-side ratings lean positive in general.",
                                    a=k_["strongBuy"], b=k_["buy"], c=k_["hold"], d=k_["sell"], e=k_["strongSell"])}
    if take and take.get("lean"):
        paras = [take.get(x) for x in ("lean_reason", "situation", "fundamentals", "valuation", "conclusion") if take.get(x)]
        if take.get("risks"):
            paras.append(T("Main risks") + ": " + "; ".join(take["risks"]))
        if take.get("catalysts"):
            paras.append(T("Coming catalysts") + ": " + "; ".join(take["catalysts"]))
        r["ai"] = {"lean": T(take["lean"]), "conviction": T("Conviction") + ": " + T(take.get("conviction") or "n/a"),
                   "color": UP_C if take["lean"] == "Buy" else DOWN_C if take["lean"] == "Sell" else AMBER_C, "paragraphs": paras}
    return r


def pdf_controls(c: dict) -> None:
    t = c["t"]
    val = st.session_state.get(f"val_{t}") or {}
    take = st.session_state.get(f"take_{t}_{lang()}") or {}
    sig = hashlib.md5(repr((round(val.get("base") or 0, 2), val.get("discount"), str(take.get("generated_at")), lang(),
                            dt.date.today().isoformat())).encode()).hexdigest()[:10]
    key = f"pdf_{t}_{sig}"
    if key in st.session_state:
        st.download_button(T("⤓ Download PDF"), data=st.session_state[key], file_name=f"{t}_Market_Brief_{dt.date.today():%Y-%m-%d}.pdf",
                           mime="application/pdf", width="stretch", key=f"dl_{key}")
    elif st.button(T("PDF report"), key=f"mk_{key}", width="stretch",
                   help=T("A printable report with everything on this page: price, financials and ratios, valuation, peers, earnings, risk, Wall Street and the AI take if you generated it.")):
        with st.spinner(T("Building the report…")):
            import reports
            st.session_state[key] = reports.stock_pdf(report_data(c))
        st.rerun()
