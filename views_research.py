"""Research page: stock pitches kept as Markdown files in research/, each with a live track record since publication,
and a helper that turns a filled-in form into a pitch file ready to upload to the repository."""
from __future__ import annotations

import datetime as dt
import re
from pathlib import Path

import pandas as pd
import streamlit as st

import analysis
import charts
import data
from common import money, num, pct, safe
from i18n import D, T, choice, lang
from ui import esc, link, signed_class, src
from views_market import page_header, quick_value

RESEARCH_DIR = Path(__file__).parent / "research"
UPLOAD_URL = "https://github.com/tomasjtff-cloud/market-brief/upload/main/research"
CALL_CLASS = {"Long": "up", "Short": "down", "Neutral": "hold"}


# =========================================================================== files
def parse(text: str) -> tuple[dict, str]:
    """Front matter between --- lines (key: value), then the Markdown body."""
    meta, body = {}, text
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.S)
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip().lower()] = v.strip().strip('"').strip("'")
        body = m.group(2)
    return meta, body


def load_pitches() -> list[dict]:
    out = []
    if not RESEARCH_DIR.exists():
        return out
    for p in sorted(RESEARCH_DIR.glob("*.md")):
        if p.name.startswith("_") or p.name.lower() == "readme.md":
            continue
        try:
            meta, body = parse(p.read_text(encoding="utf-8"))
            day = dt.date.fromisoformat(meta.get("date", "")[:10])
        except (ValueError, OSError):
            continue
        ticker = (meta.get("ticker") or "").upper().strip()
        if not ticker:
            continue
        call = (meta.get("call") or "Long").strip().title()
        out.append({"file": p.name, "title": meta.get("title") or ticker, "ticker": ticker, "date": day,
                    "call": call if call in CALL_CLASS else "Long", "price": _num(meta.get("price")),
                    "target": _num(meta.get("target")), "horizon": meta.get("horizon", ""), "author": meta.get("author", ""),
                    "body": body})
    return sorted(out, key=lambda x: x["date"], reverse=True)


def _num(v) -> float | None:
    try:
        return float(str(v).replace(",", "").replace("$", "")) if v not in (None, "") else None
    except ValueError:
        return None


def _close_on(close: pd.Series, day: dt.date) -> float | None:
    after = close[close.index >= pd.Timestamp(day)]
    return float(after.iloc[0]) if len(after) else None


def track(p: dict) -> dict:
    """Return since publication for the stock and the S&P 500, adjusted for the direction of the call."""
    hist = safe(data.history, p["ticker"])
    spy = safe(data.history, "SPY")
    q = safe(data.quote, p["ticker"])
    now = q["price"] if q else (float(hist["close"].iloc[-1]) if hist is not None else None)
    start = p["price"] or (_close_on(hist["close"], p["date"]) if hist is not None else None)
    ret = now / start - 1 if now and start else None
    spy_ret = None
    if spy is not None:
        s0 = _close_on(spy["close"], p["date"])
        spy_ret = float(spy["close"].iloc[-1]) / s0 - 1 if s0 else None
    sign = {"Long": 1, "Short": -1}.get(p["call"])
    call_ret = ret * sign if ret is not None and sign else None
    excess = (ret - spy_ret) * sign if ret is not None and spy_ret is not None and sign else None
    return {"start": start, "now": now, "ret": ret, "spy": spy_ret, "call_ret": call_ret, "excess": excess,
            "hit": excess > 0 if excess is not None else None,
            "to_target": (p["target"] / now - 1) if p["target"] and now else None, "hist": hist, "spy_hist": spy}


# =========================================================================== page
def page_research() -> None:
    page_header(T("Research"), T("Investment pitches with a live track record: each call is measured against the S&P 500 from the day it was published."))
    mode = choice(st.segmented_control, "Research mode", ["Published pitches", "Write a pitch"], key="rs_mode",
                  default="Published pitches", label_visibility="collapsed") or "Published pitches"
    if mode == "Write a pitch":
        writer()
    else:
        published()


def published() -> None:
    pitches = load_pitches()
    if not pitches:
        st.html('<div class="mb-callout"><b>' + T("No pitches published yet.") + "</b> " + T(
            "Use “Write a pitch” to build one from your own analysis; it produces a file that you upload to the research folder of "
            "the repository, and it appears here with its track record.") + "</div>")
        return
    with st.spinner(T("Measuring each call since publication…")):
        rows = [(p, track(p)) for p in pitches]
    scored = [tr for _, tr in rows if tr["excess"] is not None]
    hits = [tr["hit"] for tr in scored]
    st.html('<div class="mb-stats" style="--cols:4">' + "".join(
        f'<div class="mb-stat"><div class="k">{k}</div><div class="v num {c}">{v}</div></div>' for k, v, c in [
            (T("Pitches"), str(len(pitches)), ""),
            (T("Beat the S&P 500"), f"{sum(hits)}/{len(hits)}" if hits else "–", ""),
            (T("Average return of the calls"), pct(sum(t["call_ret"] for t in scored) / len(scored)) if scored else "–",
             signed_class(sum(t["call_ret"] for t in scored) / len(scored)) if scored else ""),
            (T("Average excess vs S&P 500"), pct(sum(t["excess"] for t in scored) / len(scored)) if scored else "–",
             signed_class(sum(t["excess"] for t in scored) / len(scored)) if scored else ""),
        ]) + "</div>")
    body = ""
    for p, tr in rows:
        body += (f'<tr><td class="l">{D(p["date"], "%b %-d, %Y")}</td>'
                 f'<td class="l"><a href="{link({"p": "stock", "t": p["ticker"]})}" target="_self">{esc(p["ticker"])}</a>'
                 f'<span class="co">{esc(p["title"])}</span></td>'
                 f'<td><span class="mb-lean {CALL_CLASS[p["call"]]}">{T(p["call"])}</span></td>'
                 f'<td class="num">{money(tr["start"], 2)}</td><td class="num">{money(tr["now"], 2)}</td>'
                 f'<td class="num {signed_class(tr["ret"])}">{pct(tr["ret"])}</td><td class="num {signed_class(tr["spy"])}">{pct(tr["spy"])}</td>'
                 f'<td class="num {signed_class(tr["excess"])}">{pct(tr["excess"])}</td>'
                 f'<td class="num">{money(p["target"], 2) if p["target"] else "–"}</td>'
                 f'<td class="num {signed_class(tr["to_target"])}">{pct(tr["to_target"]) if tr["to_target"] is not None else "–"}</td></tr>')
    head = "".join(f"<th>{T(h)}</th>" for h in ("Call", "Price then", "Price now", "Stock return", "S&P 500", "Call vs S&P 500",
                                                "Target", "To target"))
    st.html(f'<div class="mb-sec">{T("Track record")} {src("mkt")} {src("calc")}</div><div class="mb-scroll"><table class="mb-tbl">'
            f'<tr><th class="l">{T("Date")}</th><th class="l">{T("Pitch")}</th>{head}</tr>{body}</table></div>'
            '<p class="mb-foot">' + T("Call vs S&P 500 = the stock's return minus the index's since the publication date, with the sign flipped for short calls. Prices are not adjusted for dividends.") + "</p>")

    names = {f'{p["date"]} · {p["ticker"]} · {p["title"]}': i for i, p in enumerate(pitches)}
    pick = st.selectbox(T("Read a pitch"), list(names), key="rs_pick")
    p, tr = rows[names[pick]]
    a, b = st.columns([1.9, 1], gap="medium")
    with b:
        st.html('<div class="mb-panel">' + "".join(
            f'<div class="mb-check"><span class="mb-lean flat">{esc(k)}</span><p class="mb-p">{v}</p></div>' for k, v in [
                (T("Call"), f'<b>{T(p["call"])}</b>' + (f' · {esc(p["horizon"])}' if p["horizon"] else "")),
                (T("Published"), D(p["date"], "%b %-d, %Y") + (f' · {esc(p["author"])}' if p["author"] else "")),
                (T("Price then → now"), f'{money(tr["start"], 2)} → {money(tr["now"], 2)} (<span class="{signed_class(tr["ret"])}">{pct(tr["ret"])}</span>)'),
                (T("Call vs S&P 500"), f'<span class="{signed_class(tr["excess"])}">{pct(tr["excess"])}</span>'),
                (T("Target"), f'{money(p["target"], 2)} · {pct(tr["to_target"])} {T("to go")}' if p["target"] else "–"),
            ]) + "</div>")
        if tr["hist"] is not None and tr["spy_hist"] is not None:
            since = pd.Timestamp(p["date"])
            s1 = tr["hist"]["close"][tr["hist"]["close"].index >= since]
            s2 = tr["spy_hist"]["close"].reindex(s1.index).ffill()
            if len(s1) > 1:
                st.plotly_chart(charts.compare_lines({p["ticker"]: s1, "SPY": s2}, highlight=p["ticker"], height=280),
                                config=charts.CONFIG, key=f"rs_chart_{p['file']}_{lang()}")
    with a:
        with st.container(key="panel_rs_body"):
            st.html(f'<div class="mb-kicker">{T("Pitch")}</div><h2 style="margin:.1rem 0 .6rem;font-size:1.35rem">{esc(p["title"])}</h2>')
            st.markdown(p["body"])


# =========================================================================== writer
def snapshot(t: str) -> str:
    """Facts from the app, as of today, to append to the pitch (no opinions)."""
    q = safe(data.quote, t)
    hist = safe(data.history, t)
    met = safe(data.basic_metrics, t, default={}) or {}
    lines = []
    if q:
        lines.append(f"- Price: ${q['price']:,.2f} ({dt.date.today().isoformat()})")
    if met.get("marketCapitalization"):
        lines.append(f"- Market cap: {money(met['marketCapitalization'] * 1e6, 1)}")
    pe = analysis.metric_value(met, analysis.COMP_MULTIPLES["P/E"], positive=True)
    if pe:
        lines.append(f"- P/E (TTM): {pe:,.1f}x")
    if hist is not None:
        c = hist["close"]
        lines.append(f"- 1-year return: {pct(analysis.period_return(c, 252))}; volatility: {pct(analysis.annual_volatility(c), 1, False)}")
    if q:
        v = safe(quick_value, t, round(q["price"], 2))
        if v:
            lines.append(f"- DCF with Market Brief default assumptions: ${v['per_share']:,.2f} ({pct(v['gap'], 0)} vs price)")
    recs = safe(data.recommendations, t, default=[]) or []
    cs = analysis.consensus(recs[0]) if recs else None
    if cs:
        lines.append(f"- Analyst consensus: {cs['label']} ({cs['score']:.2f}/5, {cs['n']} analysts, {cs['period']})")
    return "\n".join(lines)


def writer() -> None:
    st.html('<div class="mb-callout">' + T("Write the pitch in your own words. The app fills in the date and today's price, can add a snapshot of the data, and gives you a file to upload to the research folder of the repository. Once uploaded, the pitch is published here and its track record starts.") + "</div>")
    with st.form("rs_form"):
        c1, c2, c3, c4 = st.columns([1, 1, 1, 1.2])
        ticker = c1.text_input(T("Ticker"), placeholder="AAPL")
        call = c2.selectbox(T("Call"), ["Long", "Short", "Neutral"], format_func=T)
        target = c3.number_input(T("Price target (optional)"), min_value=0.0, value=0.0, step=1.0)
        horizon = c4.text_input(T("Horizon"), value="12 months")
        title = st.text_input(T("Title: your thesis in one line"))
        author = st.text_input(T("Author"))
        parts = {}
        for key, label in (("Thesis", "Thesis"), ("Business and fundamentals", "Business and fundamentals"),
                           ("Valuation", "Valuation"), ("Catalysts", "Catalysts"), ("Risks", "Risks")):
            parts[key] = st.text_area(T(label), height=110, key=f"rs_{key}")
        add_snap = st.checkbox(T("Add a data snapshot from the app"), value=True)
        go = st.form_submit_button(T("Build the pitch file"), type="primary")
    if not go:
        return
    t = ticker.strip().upper()
    q = safe(data.quote, t) if t else None
    if not q:
        st.error(T("{t} wasn't found as a US-listed stock or ETF. Check the ticker.", t=t or "?"))
        return
    if not title.strip() or not parts["Thesis"].strip():
        st.error(T("Add at least a title and the thesis."))
        return
    today = dt.date.today().isoformat()
    head = ["---", f"title: {title.strip()}", f"ticker: {t}", f"date: {today}", f"call: {call}", f"price: {q['price']:.2f}"]
    if target > 0:
        head.append(f"target: {target:.2f}")
    if horizon.strip():
        head.append(f"horizon: {horizon.strip()}")
    if author.strip():
        head.append(f"author: {author.strip()}")
    head.append("---")
    body = "\n\n".join(f"## {k}\n{v.strip()}" for k, v in parts.items() if v.strip())
    if add_snap:
        snap = snapshot(t)
        if snap:
            body += f"\n\n## Data snapshot (Market Brief, {today})\n{snap}"
    text = "\n".join(head) + "\n\n" + body + "\n"
    fname = f"{today}-{t.lower()}.md"
    st.html(f'<div class="mb-sec">{T("Preview")}</div>')
    with st.container(key="panel_rs_preview"):
        st.markdown(parse(text)[1])
    a, b = st.columns(2)
    a.download_button(T("Download {f}", f=fname), text.encode("utf-8"), file_name=fname, mime="text/markdown", type="primary",
                      width="stretch")
    b.link_button(T("Open the research folder on GitHub to upload it"), UPLOAD_URL, width="stretch")
    st.caption(T("On GitHub: drag the file, then “Commit changes”. The app redeploys in about a minute and the pitch appears under Published pitches."))
