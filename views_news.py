"""News desk page: headlines by region (USA, Mexico, Argentina, World) and by sector, FX and rates,
and an AI read of what it all means for markets."""
from __future__ import annotations

import datetime as dt

import streamlit as st

import ai
import data
import news
from common import safe, when
from ui import chip, esc, src
from views_market import page_header

TONE_CLASS = {"Positive": "up", "Mixed": "hold", "Negative": "down"}
REGION_SUB = {
    "USA": "CNBC, MarketWatch, WSJ, Federal Reserve, Finnhub",
    "Mexico": "El Financiero, Expansión, El Economista",
    "Argentina": "Ámbito, Infobae",
    "World": "BBC, CNBC World, DW, Finnhub forex",
}


def tone_chip(tone: str | None) -> str:
    t = (tone or "").strip().title()
    return f'<span class="mb-lean {TONE_CLASS.get(t, "flat")}">{esc(t or "n/a")}</span>'


def headline_list(items: list[dict], show_sectors: bool = True, limit: int = 14) -> str:
    if not items:
        return '<p class="mb-foot">No recent headlines in this section.</p>'
    rows = []
    for n in items[:limit]:
        tags = "".join(f'<span class="mb-tagx">{esc(s)}</span>' for s in n.get("sectors", [])[:3]) if show_sectors else ""
        rows.append(f'<div><a class="t" href="{esc(n["url"])}" target="_blank" rel="noopener">{esc(n["title"])}</a>'
                    f'<div class="m">{esc(n["source"])} · {n["time"]:%a %b %d, %-I:%M %p} ET {tags}</div>'
                    + (f'<div class="s">{esc(n["summary"][:240])}</div>' if n.get("summary") else "") + "</div>")
    return f'<div class="mb-news">{"".join(rows)}</div>'


def cell(name: str, value: str, change: str = "", sub: str = "") -> str:
    return (f'<div class="mb-cell"><div class="name">{esc(name)}</div><div class="row"><span class="px num">{esc(value)}</span>{change}</div>'
            f'<div class="asof">{esc(sub)}</div></div>')


def bps_chip(bps: float | None) -> str:
    if bps is None:
        return ""
    cls = "up" if bps > 0 else "down" if bps < 0 else "flat"
    return f'<span class="mb-chip {cls}">{bps:+.0f} bps</span>'


# =========================================================================== FX & rates
def fx_and_rates() -> tuple[str, str]:
    """HTML for the three boards and a plain-text version for the AI."""
    text = []
    # --- the dollar vs other currencies
    fx_cells = []
    live = safe(data.fx_quote, "USD/MXN")
    if live:
        fx_cells.append(cell("USD/MXN (live)", f"{live['price']:,.4f}", chip(live["pct"]), f"Twelve Data · {live['time']}"))
        text.append(f"USD/MXN live {live['price']:.4f} ({live['pct']:+.2f}% today)")
    ecb = safe(data.fx_reference, default={}) or {}
    for pair, r in ecb.items():
        if pair == "USD/MXN" and live:
            continue
        d1 = (r["rate"] / r["prev"] - 1) * 100 if r.get("prev") else None
        w1 = (r["rate"] / r["week"] - 1) * 100 if r.get("week") else None
        fx_cells.append(cell(pair, f"{r['rate']:,.4f}", chip(d1), f"ECB {r['date']} · 1 week {w1:+.2f}%" if w1 is not None else f"ECB {r['date']}"))
        text.append(f"{pair} {r['rate']:.4f} ({d1:+.2f}% on the day, {w1:+.2f}% on the week, ECB reference {r['date']})")
    uup = safe(data.quote, "UUP")
    if uup:
        fx_cells.append(cell("US dollar index (UUP)", f"${uup['price']:,.2f}", chip(uup["pct"]), f"ETF proxy · {when(uup['time'])}"))
        text.append(f"US dollar index ETF (UUP) {uup['pct']:+.2f}% today")

    # --- Argentina
    ar_cells = []
    ar = safe(data.dolares_ar, default={}) or {}
    official = ar.get("oficial", {}).get("sell")
    for casa, name in (("oficial", "Official"), ("mayorista", "Wholesale"), ("bolsa", "MEP"), ("contadoconliqui", "CCL"),
                       ("blue", "Blue"), ("cripto", "Crypto")):
        r = ar.get(casa)
        if not r:
            continue
        gap = (r["sell"] / official - 1) * 100 if official and casa not in ("oficial", "mayorista") else None
        ch = f'<span class="mb-chip flat">{gap:+.1f}% gap</span>' if gap is not None else ""
        ar_cells.append(cell(f"Dollar {name}", f"ARS {r['sell']:,.0f}", ch, f"Sell · {r['time']:%b %d, %-I:%M %p}" if r.get("time") else "Sell"))
        text.append(f"Argentina dollar {name}: ARS {r['sell']:,.1f}" + (f" ({gap:+.1f}% vs official)" if gap is not None else ""))
    rp = safe(data.riesgo_pais)
    if rp:
        ar_cells.append(cell("Country risk (EMBI)", f"{rp['value']:,.0f} bps", "", f"ArgentinaDatos · {rp['date']}"))
        text.append(f"Argentina country risk {rp['value']:,.0f} bps ({rp['date']})")

    # --- rates
    rate_cells = []
    latest = {}
    for sid, name in (("DFF", "Fed funds (effective)"), ("DGS2", "US 2-year"), ("DGS10", "US 10-year"), ("DGS30", "US 30-year")):
        obs = safe(data.fred_series, sid, 15, default=[]) or []
        if not obs:
            continue
        (d0, v0) = obs[0]
        wk = obs[5][1] if len(obs) > 5 else None
        latest[sid] = v0
        rate_cells.append(cell(name, f"{v0:.2f}%", bps_chip((v0 - wk) * 100 if wk is not None else None), f"FRED · {d0} · change vs 1 week"))
        text.append(f"{name} {v0:.2f}% ({(v0 - wk) * 100:+.0f} bps vs a week earlier, {d0})" if wk is not None else f"{name} {v0:.2f}%")
    if "DGS10" in latest and "DGS2" in latest:
        spread = (latest["DGS10"] - latest["DGS2"]) * 100
        rate_cells.append(cell("10Y − 2Y spread", f"{spread:+.0f} bps", "", "Negative = inverted curve"))
        text.append(f"US 10Y-2Y spread {spread:+.0f} bps")

    def board(title: str, cells: list[str], cols: int, tag: str) -> str:
        if not cells:
            return ""
        return (f'<div class="mb-sub">{title} {tag}</div>'
                f'<div class="mb-board" style="--cols:{cols}">{"".join(cells)}</div>')

    html_ = (board("The dollar", fx_cells, 4, src("mkt")) + board("Argentina", ar_cells, 4, src("mkt"))
             + board("Interest rates", rate_cells, 5, src("mkt")))
    return html_, "\n".join(text)


# =========================================================================== page
def ai_panel(view: dict | None, extra: str = "") -> str:
    if not view:
        return '<div class="mb-panel mb-take"><p class="mb-foot">AI read unavailable right now; the headlines are below.</p></div>'
    pts = "".join(f"<li>{esc(p)}</li>" for p in view.get("key_points", []) or [])
    watch = f'<p class="mb-p"><b>What to watch.</b> {esc(view["watch"])}</p>' if view.get("watch") else ""
    return (f'<div class="mb-panel mb-take"><div class="mb-kicker">AI read {src("ai")}</div>'
            f'<div class="mb-take-row" style="margin:.35rem 0 .6rem">{tone_chip(view.get("tone"))}{extra}</div>'
            f'<p class="mb-p">{esc(view.get("view", ""))}</p>' + (f'<ul class="mb-ul">{pts}</ul>' if pts else "") + watch + "</div>")


def page_news() -> None:
    now = dt.datetime.now(data.ET)
    page_header("News desk", "Headlines by region and by sector from official publisher feeds, exchange rates and interest "
                             "rates, and an AI read of what it means for markets.")
    with st.spinner("Collecting headlines from about 20 sources…"):
        items, failed = data.news_desk()
    groups = news.buckets(items, now)
    n_recent = len({id(i) for g in groups.values() for i in g})
    fx_html, fx_text = fx_and_rates()

    slot = f"{now:%Y-%m-%d}-{now.hour // 3}"
    view, ai_error = None, None
    with st.spinner("Writing the AI read of today's news… (20 to 40 seconds the first time)"):
        try:
            view = ai.news_view(slot, fx_text, {k: v for k, v in groups.items()})
        except Exception as exc:
            ai_error = str(exc)

    if view and view.get("overview"):
        st.html(f'<div class="mb-story top"><div class="mb-kicker">Today\'s read {src("ai")}</div>'
                f'<p class="mb-lead" style="margin:.3rem 0 0">{esc(view["overview"])}</p>'
                f'<p class="mb-note">Written {view["generated_at"]:%b %d, %-I:%M %p} ET from {n_recent} headlines; '
                "refreshed every 3 hours.</p></div>")
    elif ai_error:
        st.warning(f"The AI read couldn't be written this time ({ai_error}). Headlines and data are below.")

    # ---- FX & rates
    st.html(f'<div class="mb-sec">Exchange rates and interest rates</div>')
    left, right = st.columns([2.2, 1], gap="medium")
    left.html(fx_html)
    fxv = (view or {}).get("fx_rates") or {}
    pts = "".join(f"<li>{esc(p)}</li>" for p in fxv.get("key_points", []) or [])
    right.html(f'<div class="mb-panel mb-take"><div class="mb-kicker">AI read {src("ai")}</div><div class="mb-h"><b>FX and rates</b></div>'
               f'<p class="mb-p">{esc(fxv.get("view", "AI read unavailable right now."))}</p>'
               + (f'<ul class="mb-ul">{pts}</ul>' if pts else "") + "</div>")

    # ---- regions
    st.html('<div class="mb-sec">By region</div>')
    regions = (view or {}).get("regions") or {}
    tabs = st.tabs([f"{r}  ({len(groups[r])})" for r in news.REGIONS])
    for tab, r in zip(tabs, news.REGIONS):
        with tab:
            a, b = st.columns([1, 1.7], gap="medium")
            a.html(ai_panel(regions.get(r)))
            b.html(f'<div class="mb-panel"><div class="mb-h"><b>Latest headlines</b><span>{esc(REGION_SUB[r])}</span></div>'
                   f'{headline_list(groups[r])}</div>')

    # ---- sectors
    st.html('<div class="mb-sec">By sector</div>')
    sectors = (view or {}).get("sectors") or {}
    strip = "".join(f'<div class="mb-tone {TONE_CLASS.get(str((sectors.get(s) or {}).get("tone", "")).title(), "flat")}">'
                    f'<b>{esc(s)}</b><span>{esc(str((sectors.get(s) or {}).get("tone") or "No read").title())} · {len(groups[s])} headline{"" if len(groups[s]) == 1 else "s"}</span></div>'
                    for s in news.SECTORS)
    st.html(f'<div class="mb-tones">{strip}</div>')
    tabs = st.tabs(list(news.SECTORS))
    for tab, s in zip(tabs, news.SECTORS):
        with tab:
            a, b = st.columns([1, 1.7], gap="medium")
            a.html(ai_panel(sectors.get(s)))
            b.html(f'<div class="mb-panel"><div class="mb-h"><b>Latest headlines</b><span>Tagged by keywords, all regions</span></div>'
                   f'{headline_list(groups[s], show_sectors=False)}</div>')

    note = f" Unavailable right now: {', '.join(failed)}." if failed else ""
    st.html(f'<p class="mb-foot" style="margin-top:1rem">Headlines from the publishers\' official RSS feeds and Finnhub, refreshed every '
            f'30 minutes, last {news.window_hours(now)} hours, duplicates removed. Sectors are assigned by keywords (English and '
            f'Spanish), so a headline can appear in more than one. ECB reference rates via Frankfurter; Argentina rates via DolarApi '
            f'and ArgentinaDatos; US rates via FRED.{esc(note)}</p>')
