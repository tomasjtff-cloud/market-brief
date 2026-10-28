"""Market-wide pages: Markets (home), Map, Watchlist, Compare and Methodology."""
from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import streamlit as st

import ai
import analysis
import charts
import data
from common import (BENCHMARK, INDEX_ETFS, MAX_WATCHLIST, add_to_watchlist, big, get_watchlist, isnum, money, num,
                    pct, remove_from_watchlist, safe, status_line, when)
from i18n import D, T, es, lang
from ui import chip, esc, link, pill, range_bar, sgn, signed_class, spark_svg, src

CLOCKS = [("New York", "America/New_York"), ("Mexico City", "America/Mexico_City"),
          ("Buenos Aires", "America/Argentina/Buenos_Aires"), ("London", "Europe/London")]


def page_header(title: str, sub: str, clocks: bool = False) -> None:
    right = ""
    if clocks:
        right = '<div class="mb-clocks">' + "".join(
            f'<div class="mb-clock"><div class="c">{T(c)}</div><div class="t num">{D(dt.datetime.now(ZoneInfo(tz)), "%-I:%M %p")}</div></div>'
            for c, tz in CLOCKS) + "</div>"
    st.html(f'<div class="mb-ph"><div><h1>{esc(title)}</h1><div class="sub">{sub}</div></div>{right}</div>')


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def quick_value(ticker: str, price: float) -> dict | None:
    """Base-case DCF with default assumptions, for at-a-glance columns."""
    f = data.company_fundamentals(ticker)
    rf, _ = data.risk_free_rate()
    close = data.history(ticker)["close"]
    bench = data.history(BENCHMARK)["close"]
    return analysis.default_valuation(f, price, analysis.beta(close, bench), rf)


# =========================================================================== Markets


def index_cards() -> list[str]:
    cards, snapshot = [], []
    status = safe(data.market_status, default={}) or {}
    low_high = T("Today's low → high")
    for name, sym in INDEX_ETFS:
        q = safe(data.quote, sym)
        head = f'<div class="hd"><span class="n">{T(name)}</span><span class="via">{T("via")} {sym}</span></div>'
        if not q:
            cards.append(f'<div class="mb-card">{head}<div class="p">n/a</div></div>')
            continue
        state = (T("Live") + f" · {D(q['time'], '%-I:%M %p')} ET") if status.get("isOpen") else (T("Close") + f" · {D(q['time'], '%b %-d')}")
        cards.append(
            f'<a class="mb-card" href="{link({"p": "stock", "t": sym})}" target="_self">{head}'
            f'<div class="p">${q["price"]:,.2f}</div>'
            f'<div class="c">{pill(q["pct"])}<span class="abs">{sgn(q["change"] or 0, 2, "")}</span></div>'
            f'{range_bar(q["low"], q["high"], q["price"], left="$", right="$", label=low_high)}'
            f'<div class="a">{state}</div></a>')
        snapshot.append(f"{name} ({sym}): ${q['price']:,.2f} ({q['pct']:+.2f}% today)")
    st.html(f'<div class="mb-cards" style="--cols:6">{"".join(cards)}</div>')
    return snapshot


def latam_board() -> tuple[str, list[str]]:
    cells, text = [], []

    def cell(name, px, ch, asof):
        return (f'<div class="mb-cell"><div class="name">{esc(name)}</div><div class="row"><span class="px num">{esc(px)}</span>{ch}</div>'
                f'<div class="asof">{esc(asof)}</div></div>')

    for name, sym in (("Mexico stocks (EWW)", "EWW"), ("Argentina stocks (ARGT)", "ARGT")):
        q = safe(data.quote, sym)
        cells.append(cell(T(name), f"${q['price']:,.2f}", chip(q["pct"]), when(q["time"])) if q else cell(T(name), "n/a", "", T("Unavailable")))
        if q:
            text.append(f"{name}: ${q['price']:,.2f} ({q['pct']:+.2f}%)")
    fx = safe(data.fx_quote, "USD/MXN")
    cells.append(cell(T("Dollar in Mexican pesos"), f"{fx['price']:,.4f}", chip(fx["pct"]), T("As of {d}", d=fx['time'])) if fx
                 else cell(T("Dollar in Mexican pesos"), "n/a", "", T("Unavailable")))
    if fx:
        text.append(f"USD/MXN {fx['price']:.4f} ({fx['pct']:+.2f}%)")
    ar = safe(data.dolares_ar) or {}
    official = ar.get("oficial", {}).get("sell")
    for casa, name in (("oficial", "Argentina official dollar"), ("bolsa", "Argentina MEP dollar"), ("blue", "Argentina blue dollar")):
        r = ar.get(casa)
        if not r:
            cells.append(cell(T(name), "n/a", "", T("Unavailable")))
            continue
        gap = (r["sell"] / official - 1) * 100 if official and casa != "oficial" else None
        ch = f'<span class="mb-chip flat">{gap:+.1f}% {T("vs official")}</span>' if gap is not None else ""
        cells.append(cell(T(name), f"ARS {r['sell']:,.0f}", ch, f"{T('Sell')}, {when(r['time'])}" if r["time"] else T("Sell")))
        text.append(f"{name}: ARS {r['sell']:,.0f}")
    return f'<div class="mb-board" style="--cols:3">{"".join(cells)}</div>', text


def watch_rail(wl: list[str]) -> None:
    rows, upcoming = [], []
    for t in wl:
        q = safe(data.quote, t)
        p = safe(data.profile, t, default={"name": t})
        h = safe(data.history, t)
        spark = spark_svg(h["close"].iloc[-63:].tolist()) if h is not None else ""
        price = f'${q["price"]:,.2f}' if q else "n/a"
        rows.append(f'<a class="mb-wrow" href="{link({"p": "stock", "t": t})}" target="_self"><div><div class="tk">{esc(t)}</div>'
                    f'<div class="co">{esc(p["name"])}</div></div><div>{spark}</div>'
                    f'<div><div class="px num">{price}</div><div style="text-align:right;margin-top:.15rem">{chip(q["pct"]) if q else ""}</div></div></a>')
        e = safe(data.next_earnings, t)
        if e:
            upcoming.append((e["date"], t, e["timing"]))
    html_ = f'<div class="mb-panel"><div class="mb-h"><b>{T("My watchlist")}</b><span>{T("3 months")}</span></div>{"".join(rows)}</div>'
    if upcoming:
        html_ += (f'<div class="mb-panel" style="margin-top:.7rem"><div class="mb-h"><b>{T("Earnings coming up")}</b>'
                  f'<span>{src("mkt")}</span></div><div class="mb-cal">' + "".join(
                      f'<div><span><b>{esc(t)}</b></span><span>{D(dt.date.fromisoformat(d), "%a %b %-d")}'
                      f'{(T(", before open") if "before" in timing else T(", after close")) if timing else ""}</span></div>'
                      for d, t, timing in sorted(upcoming)) + "</div></div>")
    st.html(html_)


def story_html(s: dict, top: bool = False) -> str:
    sources = "".join(
        f'<a class="mb-src" href="{esc(h["url"])}" target="_blank" rel="noopener">{esc(h["source"])}, {D(h["time"], "%b %d %-I:%M %p")}</a>'
        for h in s["sources"])
    return (f'<div class="mb-story{" top" if top else ""}"><h3>{esc(s["headline"])}</h3>'
            f'<p><b>{T("What happened.")}</b> {esc(s["what_happened"])}</p><p><b>{T("Why it matters.")}</b> {esc(s["why_it_matters"])}</p>'
            f'<p class="watch"><b>{T("Next to watch.")}</b> {esc(s["what_to_watch"])}</p><div class="mb-sources">{sources}</div></div>')


def page_markets(wl: list[str]) -> None:
    now = dt.datetime.now(data.ET)
    page_header(T("Markets") + " · " + (D(now, "%A %-d de %B") if es() else D(now, "%A, %B %-d")), status_line(), clocks=True)
    snapshot = index_cards()

    left, right = st.columns([2.3, 1], gap="medium")
    with right:
        watch_rail(wl)
    with left:
        a, b = st.columns(2, gap="small")
        with a:
            with st.container(key="panel_sectors"):
                st.html(f'<div class="mb-h"><b>{T("Sector performance today")}</b><span>{T("SPDR sector ETFs")} {src("mkt")}</span></div>')
                rows = [(T(name), q["pct"]) for name, sym in data.SECTOR_ETFS if (q := safe(data.quote, sym)) and q["pct"] is not None]
                if rows:
                    st.plotly_chart(charts.sector_bars(rows), config=charts.CONFIG, key="sectors")
                    best, worst = max(rows, key=lambda r: r[1]), min(rows, key=lambda r: r[1])
                    snapshot.append(f"Best sector {best[0]} {best[1]:+.2f}%, worst {worst[0]} {worst[1]:+.2f}%")
                else:
                    st.caption(T("Sector data unavailable right now."))
        with b:
            with st.container(key="panel_rates"):
                st.html(f'<div class="mb-h"><b>{T("US Treasury yield curve")}</b><span>FRED {src("mkt")}</span></div>')
                curve = safe(data.yield_curve)
                if curve is not None and len(curve) > 2:
                    st.plotly_chart(charts.yield_curve(curve), config=charts.CONFIG, key="curve")
                    get = lambda t: curve.loc[curve["tenor"] == t, "now"]  # noqa: E731
                    y2, y10, m3 = get("2Y"), get("10Y"), get("3M")
                    stats = []
                    if len(y2) and len(y10):
                        spread = (float(y10.iloc[0]) - float(y2.iloc[0])) * 100
                        stats.append(f"10Y − 2Y <b>{spread:+.0f} bps</b>")
                        snapshot.append(f"US 2Y {float(y2.iloc[0]):.2f}%, 10Y {float(y10.iloc[0]):.2f}%, 10Y-2Y {spread:+.0f} bps")
                    if len(m3) and len(y10):
                        stats.append(f"10Y − 3M <b>{(float(y10.iloc[0]) - float(m3.iloc[0])) * 100:+.0f} bps</b>")
                    st.html(f'<p class="mb-foot" style="font-size:.8rem">{" &nbsp;·&nbsp; ".join(stats)}. '
                            + T("A negative spread (inverted curve) has often come before recessions.") + "</p>")
                else:
                    st.caption(T("Treasury yields unavailable right now."))
        board, latam_text = latam_board()
        snapshot += latam_text
        st.html(f'<div class="mb-sec">{T("Mexico and Argentina")} {src("mkt")}</div>{board}'
                f'<p class="mb-foot">{T("Country stock markets through the US-listed ETFs that track them (EWW, ARGT). Argentine dollar rates from DolarApi.")}</p>')

    headlines, failed = data.todays_headlines()
    st.html(f'<div class="mb-sec">{T("The morning note")} {src("ai")}</div>')
    note = st.empty()
    n1, n2 = st.columns([2.3, 1], gap="medium")
    with n2:
        st.html(f'<div class="mb-panel"><div class="mb-h"><b>{T("Latest headlines")}</b><span>{src("mkt")}</span></div><div class="mb-news">' + "".join(
            f'<div><a class="t" href="{esc(h["url"])}" target="_blank" rel="noopener">{esc(h["title"])}</a>'
            f'<div class="m">{esc(h["source"])} · {D(h["time"], "%b %d, %-I:%M %p")}</div></div>' for h in headlines[:14]) + "</div></div>")
        if failed:
            st.caption(T("No answer this time from: ") + ", ".join(failed))
    with n1:
        slot = st.empty()
    if not headlines:
        note.info(T("No headlines from the last day could be loaded. Try again in a few minutes."))
        return
    slot.html('<div class="mb-story"><div class="mb-skel" style="width:94%"></div><div class="mb-skel" style="width:86%"></div>'
              f'<div class="mb-skel" style="width:60%"></div><p class="mb-note">' + T("Writing today's note from {n} headlines…", n=min(len(headlines), 40)) + '</p></div>')
    try:
        brief = ai.daily_brief(f"{now:%Y-%m-%d}-{now.hour // 6}", lang(), "\n".join(snapshot), headlines)
        stories = brief["stories"]
        out = f'<p class="mb-lead">{esc(brief["market_summary"])}</p>'
        if stories:
            out += story_html(stories[0], top=True)
        if len(stories) > 1:
            out += '<div class="mb-grid2">' + "".join(story_html(s) for s in stories[1:]) + "</div>"
        out += ('<p class="mb-note">' + T("Written by AI at {t} ET from {n} headlines and the market data on this page, and nothing else. Follow the source links before relying on it.",
                                           t=D(brief["generated_at"], "%-I:%M %p"), n=brief["n_headlines"]) + "</p>")
        slot.html(out)
    except Exception as exc:
        slot.warning(T("The AI note couldn't be written this time ({e}). The latest headlines are on the right.", e=exc))


# =========================================================================== Map
@st.cache_data(ttl=120, show_spinner=False)
def map_rows(language: str = "EN") -> list[dict]:
    rows = []
    for t, sector in data.MEGA_CAPS:
        q = safe(data.quote, t)
        p = safe(data.profile, t)
        if not q or q["pct"] is None:
            continue
        cap = (p or {}).get("market_cap") or ((p or {}).get("shares") or 0) * q["price"]
        rows.append({"ticker": t, "sector": T(sector), "name": (p or {}).get("name", t), "price": q["price"],
                     "pct": q["pct"], "cap": cap or 1e11})
    return rows


def movers_table(rows: list[dict], title: str) -> str:
    body = "".join(
        f'<tr><td class="l"><a href="{link({"p": "stock", "t": r["ticker"]})}" target="_self">{esc(r["ticker"])}</a>'
        f'<span class="co">{esc(r["name"])}</span></td><td class="num">${r["price"]:,.2f}</td>'
        f'<td class="num {signed_class(r["pct"])}">{sgn(r["pct"])}</td><td class="num">{money(r["cap"], 1)}</td></tr>'
        for r in rows)
    return (f'<div class="mb-panel" style="padding:.7rem .8rem"><div class="mb-h"><b>{title}</b></div>'
            f'<table class="mb-tbl"><tr><th class="l">{T("Company")}</th><th>{T("Price")}</th><th>{T("Change")}</th><th>{T("Market cap")}</th></tr>{body}</table></div>')


def page_map() -> None:
    page_header(T("Market map"), T("The 25 largest US companies, sized by market value and colored by today's move") + f" {src('mkt')}")
    with st.spinner(T("Loading quotes for the map…")):
        rows = map_rows(lang())
    if not rows:
        st.info(T("Quotes are unavailable right now. Try again in a minute."))
        return
    with st.container(key="bare_map"):
        st.plotly_chart(charts.treemap(rows), config=charts.CONFIG, key="treemap")
    st.html(f'<p class="mb-foot">{T("Green is up and red is down, capped at ±3% for color. Click a ticker in the tables to open it.")}</p>')
    ranked = sorted(rows, key=lambda r: r["pct"], reverse=True)
    c1, c2, c3 = st.columns(3, gap="small")
    c1.html(movers_table(ranked[:8], T("Top gainers")))
    c2.html(movers_table(list(reversed(ranked[-8:])), T("Top decliners")))
    sec = [(name, sym, safe(data.quote, sym)) for name, sym in data.SECTOR_ETFS]
    sec_rows = "".join(
        f'<tr><td class="l"><a href="{link({"p": "stock", "t": sym})}" target="_self">{sym}</a><span class="co">{T(name)}</span></td>'
        f'<td class="num">${q["price"]:,.2f}</td><td class="num {signed_class(q["pct"])}">{sgn(q["pct"] or 0)}</td></tr>'
        for name, sym, q in sec if q)
    c3.html(f'<div class="mb-panel" style="padding:.7rem .8rem"><div class="mb-h"><b>{T("Sectors")}</b></div>'
            f'<table class="mb-tbl"><tr><th class="l">{T("Sector ETF")}</th><th>{T("Price")}</th><th>{T("Change")}</th></tr>{sec_rows}</table></div>')


# =========================================================================== Watchlist
def page_watchlist(wl: list[str]) -> None:
    page_header(T("Watchlist"), T("Price, performance, risk and value side by side. Click a ticker to open it.") + f" {src('mkt')} {src('calc')}")
    rf, _ = data.risk_free_rate()
    bench = safe(lambda: data.history(BENCHMARK)["close"])
    rows = []
    for t in wl:
        q = safe(data.quote, t)
        p = safe(data.profile, t, default={"name": t, "industry": ""})
        h = safe(data.history, t)
        met = safe(data.basic_metrics, t, default={}) or {}
        e = safe(data.next_earnings, t)
        cells = [f'<td class="l"><a href="{link({"p": "stock", "t": t})}" target="_self">{esc(t)}</a><span class="co">{esc(p["name"])}</span></td>']
        if q:
            cells += [f'<td class="num">${q["price"]:,.2f}</td>', f'<td class="num {signed_class(q["pct"])}">{sgn(q["pct"] or 0)}</td>']
        else:
            cells += ["<td>n/a</td>", "<td></td>"]
        if h is not None:
            c = h["close"]
            m = analysis.risk_metrics(c, bench, rf)
            for k in ("ret_1m", "ret_3m", "ret_ytd", "ret_1y"):
                cells.append(f'<td class="num {signed_class(m[k])}">{pct(m[k])}</td>')
            cells += [f'<td class="num">{pct(m["volatility"], signed=False)}</td>', f'<td class="num">{num(m["beta"])}</td>',
                      f'<td class="num neg">{pct(m["max_drawdown"])}</td>']
            yr = c.iloc[-252:]
            cells.append(f'<td style="min-width:8rem">{range_bar(float(yr.min()), float(yr.max()), float(c.iloc[-1]), "{:,.0f}")}</td>')
            cells.append(f'<td style="width:7rem">{spark_svg(c.iloc[-126:].tolist())}</td>')
        else:
            cells += ["<td>n/a</td>"] * 9
        pe = met.get("peTTM") or met.get("peBasicExclExtraTTM")
        cells.append(f'<td class="num">{num(pe, 1, "x") if pe and pe > 0 else "n/m"}</td>')
        cells.append(f'<td class="num">{money((p.get("market_cap") or 0) or None, 1)}</td>')
        v = safe(quick_value, t, round(q["price"], 2)) if q else None
        if v:
            cls = "pos" if v["label"] == "Looks undervalued" else "neg" if v["label"] == "Looks overvalued" else ""
            cells += [f'<td class="num">${v["per_share"]:,.0f}</td>', f'<td class="num {cls}">{pct(v["gap"], 0)}</td>']
        else:
            cells += [f'<td title="{T("DCF needs positive free cash flow and SEC filings")}">n/m</td>', "<td></td>"]
        cells.append(f'<td>{D(dt.date.fromisoformat(e["date"]), "%b %-d")}</td>' if e else "<td></td>")
        rows.append("<tr>" + "".join(cells) + "</tr>")
    head = "<tr><th class='l'>Ticker</th>" + "".join(f"<th>{T(h)}</th>" for h in (
        "Price", "Today", "1M", "3M", "YTD", "1Y", "Volatility", "Beta", "Max DD", "52-week range", "6 months", "P/E",
        "Market cap", "DCF value", "Upside", "Earnings")) + "</tr>"
    st.html(f'<div class="mb-scroll"><table class="mb-tbl">{head}{"".join(rows)}</table></div>'
            f'<p class="mb-foot">{T("Volatility, beta (2 years of weekly returns vs SPY) and max drawdown are calculated here. DCF value is the base case with default assumptions (5-year revenue CAGR capped at 0 to 20%, CAPM cost of equity, 2.5% terminal growth); open a stock to change them. P/E is trailing twelve months from Finnhub.")}</p>')

    st.html(f'<div class="mb-sec">{T("Manage the list")}</div>')
    c1, c2 = st.columns([3, 2], gap="medium")
    with c1:
        cols = st.columns(min(len(wl), 4))
        for i, t in enumerate(wl):
            cols[i % len(cols)].button(T("Remove {t}", t=t), key=f"rm_{t}", on_click=remove_from_watchlist, args=(t,),
                                       disabled=len(wl) == 1, width="stretch")
    with c2:
        if len(wl) < MAX_WATCHLIST:
            qq = st.text_input(T("Add a stock"), key="wl_add", placeholder=T("Company or ticker"))
            if qq.strip():
                res = safe(data.search_symbols, qq.strip(), default=[])
                if res:
                    ch = st.selectbox(T("Match"), res, key="wl_pick", format_func=lambda r: f"{r['symbol']}  {r['description']}")
                    st.button(T("Add {s}", s=ch['symbol']), type="primary", on_click=add_to_watchlist, args=(ch["symbol"],))
        else:
            st.caption(T("The list holds {n} stocks.", n=MAX_WATCHLIST))
        st.caption(T("The list is saved in this page's address. Bookmark it to keep it."))


# =========================================================================== Compare
COMPARE_PERIODS = {"1M": 21, "3M": 63, "6M": 126, "YTD": None, "1Y": 252, "3Y": 756, "5Y": 1260}


def page_compare(wl: list[str]) -> None:
    page_header(T("Compare"), T("Performance, risk and correlation of any stocks against the market") + f" {src('calc')}")
    options = list(dict.fromkeys(wl + [BENCHMARK, "QQQ", "EWW", "ARGT"] + [t for t, _ in data.MEGA_CAPS]))
    c1, c2 = st.columns([3, 1.3], vertical_alignment="bottom")
    picked = c1.multiselect(T("Tickers (up to 6)"), options, default=list(dict.fromkeys(wl[:5] + [BENCHMARK])), max_selections=6,
                            key="cmp_pick")
    period = c2.segmented_control(T("Period"), list(COMPARE_PERIODS), default="1Y", key="cmp_period") or "1Y"
    if not picked:
        st.info(T("Pick at least one ticker."))
        return
    closes = {}
    for t in picked:
        h = safe(data.history, t)
        if h is not None:
            closes[t] = h["close"]
    missing = [t for t in picked if t not in closes]
    if missing:
        st.caption(T("No price history right now for: ") + ", ".join(missing))
    if not closes:
        return
    df = pd.DataFrame(closes).dropna()
    if period == "YTD":
        df = df[df.index >= pd.Timestamp(dt.date(df.index[-1].year, 1, 1))]
        days = len(df) - 1
    else:
        days = COMPARE_PERIODS[period]
        df = df.iloc[-(days + 1):]
    stocks = [t for t in df.columns if t != BENCHMARK]
    series = {t: df[t] for t in df.columns}
    if len(stocks) >= 2:
        series[T("Equal-weight portfolio")] = analysis.equal_weight_index({t: closes[t] for t in stocks}, len(df) - 1).reindex(df.index).fillna(1.0)
    st.plotly_chart(charts.compare_lines(series), config=charts.CONFIG, key="cmp_chart")

    rf, _ = data.risk_free_rate()
    bench = closes.get(BENCHMARK) if BENCHMARK in closes else safe(lambda: data.history(BENCHMARK)["close"])
    rows = []
    for name, s in series.items():
        r = s.pct_change().dropna()
        total = s.iloc[-1] / s.iloc[0] - 1
        years = max(len(r) / 252, 1 / 252)
        vol = r.std() * np.sqrt(252) if len(r) > 5 else None
        ann = (1 + total) ** (1 / years) - 1 if years >= 1 else None
        sharpe = ((total / years if years < 1 else ann) - rf) / vol if vol else None
        dd = float((s / s.cummax() - 1).min())
        b = None
        if bench is not None and name != BENCHMARK and name in closes:
            b = analysis.beta(closes[name], bench)
        q = safe(data.quote, name) if name in closes else None
        price_txt = f"${q['price']:,.2f}" if q else ""
        rows.append(f'<tr><td class="l"><b>{esc(name)}</b></td><td class="num">{price_txt}</td>'
                    f'<td class="num {signed_class(total)}">{pct(total)}</td><td class="num">{pct(ann) if ann is not None else "n/a"}</td>'
                    f'<td class="num">{pct(vol, signed=False) if vol else "n/a"}</td><td class="num">{num(sharpe)}</td>'
                    f'<td class="num neg">{pct(dd)}</td><td class="num">{num(b)}</td></tr>')
    head = "".join(f"<th>{T(h)}</th>" for h in ("Price", "Return", "Annualized", "Volatility", "Sharpe", "Max drawdown", "Beta vs SPY"))
    st.html(f'<div class="mb-scroll"><table class="mb-tbl"><tr><th class="l">{T("Series")}</th>{head}</tr>{"".join(rows)}</table></div>'
            f'<p class="mb-foot">{T("Over the selected period. Sharpe uses the 10-year Treasury as the risk-free rate; beta uses two years of weekly returns. The equal-weight portfolio holds the chosen stocks (not SPY) in equal parts, rebalanced daily.")}</p>')

    if len(df.columns) >= 2:
        a, b = st.columns([1.2, 1], gap="medium")
        with a:
            st.html(f'<div class="mb-sec">{T("Correlation of daily returns")} {src("calc")}</div>')
            st.plotly_chart(charts.correlation(df.pct_change().dropna()), config=charts.CONFIG, key="cmp_corr")
        with b:
            st.html(f'<div class="mb-sec">{T("How to read it")}</div>')
            st.html('<div class="mb-callout">' + T("Correlation runs from −1 to +1. Stocks near +1 move together, so holding both adds little diversification; values near 0 or negative smooth a portfolio's ride. Compare the equal-weight portfolio's volatility with the average of the single stocks to see how much diversification is helping.") + '</div>')


# =========================================================================== Methodology
def page_method() -> None:
    page_header(T("Methodology"), T("Where every number comes from and how it is calculated"))
    st.html('<div class="mb-callout">' + T("Every figure is tagged: {mkt} prices and rates from data providers, {rep} numbers companies filed with the SEC, {calc} figures computed here, {ana} sell-side analyst ratings and {ai} text written by the AI from the data shown.",
            mkt=src("mkt"), rep=src("rep"), calc=src("calc"), ana=src("ana"), ai=src("ai")) + "</div>")
    if es():
        from i18n_es import METHOD_ES
        st.markdown(METHOD_ES)
    else:
        st.markdown(METHOD_EN)


METHOD_EN = """
#### Data sources (all free tiers)
| What | Source | Freshness |
|---|---|---|
| Quotes, day range, symbol search, company profile, key metrics, analyst ratings, news, earnings dates | Finnhub | Quotes every minute; others hourly to daily |
| Daily and intraday price history, volume, USD/MXN | Twelve Data | Daily bars every 6 hours, intraday every 5 minutes |
| Financial statements | SEC EDGAR (XBRL company facts) | As filed in 10-K and 10-Q reports |
| Treasury yields (1 month to 30 years) | FRED, St. Louis Fed | Daily, previous business day |
| Bitcoin | CoinGecko | About every 10 minutes |
| Argentine dollar rates | DolarApi | About every 15 minutes |
| Headlines, USA | CNBC, MarketWatch, WSJ Markets, Federal Reserve (RSS) and Finnhub | Every 30 minutes |
| Headlines, Mexico | El Financiero (economy, markets and business sections), Expansión, El Economista (RSS) | Every 30 minutes |
| Headlines, Argentina | Ámbito (economy and finance), Infobae economy (RSS) | Every 30 minutes |
| Headlines, World and sectors | BBC Business, CNBC World, DW Business, Mining.com, TechCrunch AI, OilPrice, CoinDesk (RSS), Finnhub forex, M&A and crypto news | Every 30 minutes |
| Exchange rates vs the dollar | ECB reference rates via Frankfurter | Daily |
| Argentina country risk (EMBI) | ArgentinaDatos | Daily |
| Fed funds rate | FRED, St. Louis Fed | Daily |

Indices are shown through the ETFs that track them (SPY, QQQ, DIA, IWM; EWW for Mexico, ARGT for Argentina), because index
levels aren't on free data plans. A shared rate limiter keeps the app within each provider's free per-minute limits.

#### News desk
Headlines are grouped by region according to the feed they come from, and by sector with an English and Spanish keyword
list (a headline can be in more than one sector). The AI read is written from those headlines and the exchange-rate and
interest-rate data on the page, every 3 hours, and gives each region and sector a tone: positive, mixed or negative.

#### Risk and performance
Volatility is the annualized standard deviation of daily log returns over a year. Beta is the slope of weekly returns on SPY
over two years. Sharpe is return minus the 10-year Treasury yield, divided by volatility. Max drawdown is the worst fall from a
peak. RSI is the 14-day relative strength index; Bollinger bands are the 20-day average ± two standard deviations.

#### Outlook (scenario simulation)
4,000 six-month paths. Each simulated day replays one real daily move of the stock from the last two years (a bootstrap), so
crash days and rallies are kept in their real proportions. The average daily move is replaced by the trend you choose: none,
the market's long-run average (about 8% a year), or the stock's own recent trend capped at ±30% a year. Percentiles of the
paths give the scenario table; the share of paths that cross a level gives each probability. These are model probabilities
that assume the next six months look like a reshuffled version of the last two years. They are not forecasts.

#### DCF and valuation
Free cash flow (operating cash flow minus capital expenditures) from SEC filings grows at the chosen rate for five years, fades
to terminal growth over the next five, then a Gordon growth terminal value. Discount rate is WACC: CAPM cost of equity
(10-year Treasury + beta × equity risk premium), after-tax cost of debt and market-value weights. Equity value is enterprise
value minus net debt, per share. The reverse DCF solves for the growth the current price implies. The football field compares
DCF scenarios, DCF sensitivity, the 52-week range and the statistical range against the price.

#### AI
Google Gemini writes the morning note, the news desk read and the stock analysis from the data shown in the app only, with
instructions not to add facts or set price targets. The stock take gives a Buy / Hold / Sell lean, labeled as a model opinion. The app picks a fast available Gemini model and switches if one is overloaded.

#### Portfolio and risk management
Your transactions (buys, sells, dividends, deposits and withdrawals) are stored only in your browser's local storage, with a
JSON backup to download and restore; nothing personal is asked for and nothing is kept on the server. Positions use average
cost; purchases larger than the recorded cash count as new money. The time-weighted return removes the effect of deposits
and withdrawals. Risk uses today's weights over the last two years of daily prices: volatility, Sharpe, beta (weekly, vs
SPY), maximum drawdown, historical VaR and CVaR at 95% (one day) and a parametric one-month VaR, correlations, risk
contributions and concentration (largest positions, effective number of positions, sectors). A six-question profile scores
willingness and capacity separately (the lower one sets the profile) and gives guide rails for volatility, drawdown,
single-company weight and cash plus bonds. The optimiser is long-only Markowitz with CAPM expected returns and Ledoit-Wolf
shrinkage of the covariance: minimum variance, maximum Sharpe and the highest-return portfolio within the profile's
volatility. Recommendation signals come from these numbers; the AI only explains them, and the app never trades.

#### Comparable companies and research
Peers are the companies Finnhub groups in the same industry. For each multiple (P/E, EV/EBITDA, P/S, P/FCF, P/B, trailing
twelve months) the app takes the peer median and the value it implies: today's price × peer median ÷ the company's own
multiple; negative multiples are left out. The Research page publishes pitches kept as files in the repository and measures
each call from its publication date against the S&P 500 (sign flipped for short calls).

#### Limits
Free data can be delayed or briefly unavailable; every number shows its time. SEC tag coverage varies by company. Nothing here
is investment advice.
"""
