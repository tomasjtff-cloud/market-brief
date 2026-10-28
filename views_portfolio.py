"""Portfolio page: positions and transactions saved in the browser, risk, investor profile, news impact,
Markowitz optimisation, recommendations and a what-if simulator. Numbers come from portfolio.py; the AI only explains."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import time

import numpy as np
import pandas as pd
import streamlit as st

import ai
import analysis
import charts
import data
import news
import portfolio as pf
import store
from common import money, num, pct, safe
from i18n import D, T, choice, lang
from ui import P, chip, esc, link, signed_class, src
from views_market import page_header, quick_value

SECTIONS = ["Overview", "Transactions", "Risk", "Investor profile", "News impact", "Optimization", "Recommendations", "Simulator"]
ACTION_CLASS = {"Buy more": "up", "Add new": "up", "Hold": "hold", "Keep as is": "hold", "Fine-tune": "hold",
                "Reduce": "down", "Sell": "down", "Rebalance": "flat"}
EFFECT_CLASS = {"Positive": "up", "Negative": "down", "Mixed": "hold", "Uncertain": "flat"}
NEWS_SECTOR_FOR_ETF = {"QQQ": "Tech & AI", "SMH": "Tech & AI", "SOXX": "Tech & AI", "XLK": "Tech & AI", "ARKK": "Tech & AI",
                       "XLE": "Energy", "USO": "Energy", "GLD": "Mining & metals", "IAU": "Mining & metals", "SLV": "Mining & metals",
                       "XLB": "Mining & metals", "XLF": "Banks & finance", "XLV": "Health care", "XLY": "Consumer & retail",
                       "XLP": "Consumer & retail", "XLI": "Industrials & autos", "XLRE": "Real estate", "VNQ": "Real estate"}


# =========================================================================== data helpers
def load_closes(tickers: list[str]) -> tuple[dict[str, pd.Series], list[str]]:
    """Daily closes, waiting politely when the free Twelve Data plan's per-minute limit is hit."""
    out, missing = {}, []
    for t in dict.fromkeys(tickers):
        for attempt in range(7):
            try:
                out[t] = data.history(t)["close"]
                break
            except data.DataError as exc:
                msg = str(exc).lower()
                if ("busy" in msg or "limit" in msg) and attempt < 6:
                    time.sleep(9)
                    continue
                missing.append(t)
                break
            except Exception:
                missing.append(t)
                break
    return out, missing


def ticker_meta(t: str) -> dict:
    p = safe(data.profile, t, default={}) or {}
    industry = (p.get("industry") or "").strip()
    etf = pf.is_etf(t, industry if p else None)
    sector = pf.ETF_SECTOR.get(t) if etf else (industry or "Other")
    return {"name": p.get("name") or t, "industry": industry, "etf": etf, "sector": sector or "Other"}


def state() -> dict:
    """Everything the sections share, computed from the saved transactions."""
    b = store.book()
    txs = b["transactions"]
    pos = pf.positions(txs)
    tickers = sorted(pos["holdings"])
    prices, day_pct = {}, {}
    for t in tickers:
        q = safe(data.quote, t)
        if q:
            prices[t], day_pct[t] = q["price"], q["pct"]
    meta = {t: ticker_meta(t) for t in tickers}
    table = pf.valuation_table(pos, prices, meta)
    total = float(table["value"].fillna(0).sum())
    weights = {r.ticker: float(r.weight) for r in table.itertuples() if r.weight > 0}
    prof = pf.investor_profile(b["profile"]["answers"]) if b.get("profile") and b["profile"].get("answers") else None
    return {"book": b, "txs": txs, "pos": pos, "tickers": tickers, "prices": prices, "day_pct": day_pct, "meta": meta,
            "table": table, "total": total, "weights": weights, "profile": prof}


def signature(s: dict, extra: str = "") -> str:
    raw = json.dumps([sorted((k, round(v, 4)) for k, v in s["weights"].items()), extra, dt.date.today().isoformat()])
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def stat_grid(items: list[tuple[str, str, str]], cols: int | None = None) -> str:
    return (f'<div class="mb-stats" style="--cols:{cols or len(items)}">' + "".join(
        f'<div class="mb-stat"><div class="k">{esc(k)}</div><div class="v num {c}">{v}</div></div>' for k, v, c in items) + "</div>")


def badge(text: str, cls: str) -> str:
    return f'<span class="mb-lean {cls}">{esc(T(text))}</span>'


# =========================================================================== page
def page_portfolio() -> None:
    page_header(T("Portfolio"), T("Your real positions, their risk, how today's news touches them and what could improve them. "
                                  "Saved only in this browser: download a backup to keep it safe or move it to another device."))
    if not store.sync():
        st.html('<div class="mb-panel"><div class="mb-skel" style="width:60%"></div><p class="mb-note">'
                + T("Opening your saved portfolio…") + "</p></div>")
        if st.button(T("Taking too long? Continue without saved data")):
            st.session_state.pf_force_fallback = True
            st.rerun()
        return
    if st.session_state.get("pf_problems"):
        st.warning(T("Some saved rows could not be read and were skipped: {p}", p="; ".join(st.session_state.pf_problems[:5])))
        st.session_state.pf_problems = []
    if not st.session_state.get("pf_storage_ok", True):
        st.info(T("This browser didn't allow saving, so the portfolio lives only while this tab is open. Use the backup file to keep it."))
    s = state()
    if not s["txs"]:
        onboarding()
        return
    section = choice(st.segmented_control, "Portfolio section", SECTIONS, key="pf_section", default="Overview",
                     label_visibility="collapsed") or "Overview"
    st.html('<div style="height:.2rem"></div>')
    {"Overview": overview, "Transactions": transactions, "Risk": risk_section, "Investor profile": profile_section,
     "News impact": news_impact, "Optimization": optimization, "Recommendations": recommendations,
     "Simulator": simulator}[section](s)


def onboarding() -> None:
    st.html('<div class="mb-callout"><b>' + T("Start your portfolio.") + "</b> " + T(
        "Add your purchases below (ticker, shares, price and date), or restore a backup file. Nothing personal is asked "
        "for: the data stays in this browser. You can also load an example to explore the tools first.") + "</div>")
    a, b = st.columns([1.6, 1], gap="medium")
    with a:
        transaction_form()
    with b:
        st.html(f'<div class="mb-sec">{T("Restore a backup")}</div>')
        restore_box()
        st.html(f'<div class="mb-sec">{T("Just looking?")}</div>')
        if st.button(T("Load an example portfolio"), width="stretch"):
            with st.spinner(T("Building the example from real prices…")):
                ex = example_book()
            if ex:
                store.save(ex)
                st.rerun()
            else:
                st.warning(T("Prices for the example aren't available right now. Try again in a minute."))


def example_book() -> dict | None:
    closes, missing = load_closes(["SPY", "AAPL", "MSFT", "NVDA", "BND", "GLD"])
    if missing:
        return None
    idx = closes["SPY"].index
    d1, d2 = idx[-480], idx[-240]
    px = lambda t, d: round(float(closes[t].loc[d]), 2)  # noqa: E731
    txs = [{"type": "deposit", "date": d1.date().isoformat(), "amount": 20000},
           {"type": "buy", "date": d1.date().isoformat(), "ticker": "SPY", "shares": 12, "price": px("SPY", d1)},
           {"type": "buy", "date": d1.date().isoformat(), "ticker": "AAPL", "shares": 15, "price": px("AAPL", d1)},
           {"type": "buy", "date": d1.date().isoformat(), "ticker": "NVDA", "shares": 30, "price": px("NVDA", d1)},
           {"type": "buy", "date": d2.date().isoformat(), "ticker": "MSFT", "shares": 6, "price": px("MSFT", d2)},
           {"type": "buy", "date": d2.date().isoformat(), "ticker": "BND", "shares": 20, "price": px("BND", d2)},
           {"type": "sell", "date": idx[-60].date().isoformat(), "ticker": "NVDA", "shares": 10, "price": px("NVDA", idx[-60])},
           {"type": "dividend", "date": idx[-30].date().isoformat(), "ticker": "AAPL", "amount": 3.9}]
    book, _ = pf.clean_book({"transactions": txs})
    return book


# =========================================================================== Overview
def overview(s: dict) -> None:
    table, pos, total = s["table"], s["pos"], s["total"]
    inv = table[table["ticker"] != pf.CASH]
    unreal = float(inv["unrealized"].fillna(0).sum())
    cost = float(inv["cost"].sum())
    hist_closes, missing = load_closes(sorted({t["ticker"] for t in s["txs"] if t.get("ticker")}) + ["SPY"])
    vh = pf.value_history(s["txs"], {k: v for k, v in hist_closes.items() if k != "SPY"})
    twr = float(vh["twr_index"].iloc[-1] - 1) if len(vh) else None
    spy_ret = None
    if len(vh) and "SPY" in hist_closes:
        spy = hist_closes["SPY"]
        spy = spy[spy.index >= vh.index[0]]
        spy_ret = float(spy.iloc[-1] / spy.iloc[0] - 1) if len(spy) > 1 else None
    st.html(stat_grid([
        (T("Total value"), money(total, 2), ""),
        (T("Invested in positions"), money(float(inv["value"].fillna(0).sum()), 2), ""),
        (T("Cash"), money(pos["cash"], 2), ""),
        (T("Unrealized P&L"), f"{money(unreal, 2)} ({pct(unreal / cost if cost else None)})", signed_class(unreal)),
        (T("Realized P&L"), money(pos["realized"], 2), signed_class(pos["realized"])),
        (T("Dividends"), money(pos["dividends"], 2), ""),
        (T("Time-weighted return"), pct(twr), signed_class(twr)),
        (T("S&P 500 same period"), pct(spy_ret), signed_class(spy_ret)),
    ], cols=8))
    if pos["problems"]:
        st.warning(T("Check these transactions: {p}", p="; ".join(pos["problems"][:4])))
    missing_px = [t for t in s["tickers"] if t not in s["prices"]]
    if missing_px:
        st.caption(T("No live price right now for: {t}. Their value is left out until the quote returns.", t=", ".join(missing_px)))

    rows = ""
    for r in inv.sort_values("value", ascending=False).itertuples():
        dp = s["day_pct"].get(r.ticker)
        rows += (f'<tr><td class="l"><a href="{link({"p": "stock", "t": r.ticker})}" target="_self">{esc(r.ticker)}</a>'
                 f'<span class="co">{esc(r.name)}</span></td><td class="num">{r.shares:,.4g}</td><td class="num">${r.avg_cost:,.2f}</td>'
                 f'<td class="num">{"$" + format(r.price, ",.2f") if r.price else "n/a"}</td>'
                 f'<td class="num {signed_class(dp)}">{pct(dp / 100 if dp is not None else None, 2)}</td>'
                 f'<td class="num">{money(r.value, 2) if r.value is not None else "n/a"}</td><td class="num">{pct(r.weight, 1, False)}</td>'
                 f'<td class="num {signed_class(r.unrealized)}">{money(r.unrealized, 2) if r.unrealized is not None else "n/a"}</td>'
                 f'<td class="num {signed_class(r.unrealized_pct)}">{pct(r.unrealized_pct)}</td></tr>')
    rows += (f'<tr><td class="l"><b>{T("Cash")}</b></td><td></td><td></td><td></td><td></td><td class="num">{money(pos["cash"], 2)}</td>'
             f'<td class="num">{pct(s["weights"].get(pf.CASH, 0), 1, False)}</td><td></td><td></td></tr>')
    head = "".join(f"<th>{T(h)}</th>" for h in ("Shares", "Avg. cost", "Price", "Today", "Value", "Weight", "Unrealized P&L", "Return"))
    st.html(f'<div class="mb-sec">{T("Positions")} {src("mkt")} {src("calc")}</div><div class="mb-scroll"><table class="mb-tbl">'
            f'<tr><th class="l">{T("Ticker")}</th>{head}</tr>{rows}</table></div>')

    a, b = st.columns(2, gap="medium")
    with a:
        with st.container(key="panel_pf_alloc"):
            st.html(f'<div class="mb-h"><b>{T("Allocation by position")}</b><span>{src("calc")}</span></div>')
            w = table[table["value"].fillna(0) > 0]
            st.plotly_chart(charts.donut([T("Cash") if t == pf.CASH else t for t in w["ticker"]], w["value"].tolist(),
                                         center=money(total, 1)), config=charts.CONFIG, key=f"pf_donut_{lang()}")
    with b:
        with st.container(key="panel_pf_sector"):
            st.html(f'<div class="mb-h"><b>{T("Allocation by sector")}</b><span>{src("calc")}</span></div>')
            sec = table.groupby("sector")["value"].sum()
            sec = sec[sec > 0].sort_values(ascending=False)
            st.plotly_chart(charts.donut([T(x) for x in sec.index], sec.tolist()), config=charts.CONFIG, key=f"pf_sector_{lang()}")
    conc = pf.concentration(table, {t: m["etf"] for t, m in s["meta"].items()})
    st.html(stat_grid([
        (T("Largest position"), f'{conc["top_ticker"] or "–"} · {pct(conc["top_weight"], 1, False)}', ""),
        (T("Top 3 positions"), pct(conc["top3_weight"], 1, False), ""),
        (T("Effective number of positions"), num(conc["effective_n"], 1), ""),
        (T("Cash share"), pct(conc["cash_weight"], 1, False), ""),
    ]))
    st.html('<p class="mb-foot">' + T("Effective number of positions = 1 / sum of squared weights: 10 equal positions give 10; one dominant position pulls it towards 1.") + "</p>")
    if len(vh) > 2:
        st.html(f'<div class="mb-sec">{T("Value over time")} {src("calc")}</div>')
        st.plotly_chart(charts.value_history(vh), config=charts.CONFIG, key=f"pf_hist_{lang()}")
        series = {T("Portfolio (time-weighted)"): vh["twr_index"]}
        if "SPY" in hist_closes:
            spy = hist_closes["SPY"].reindex(vh.index).ffill()
            series["SPY"] = spy
        st.plotly_chart(charts.compare_lines(series, height=300), config=charts.CONFIG, key=f"pf_twr_{lang()}")
        st.html('<p class="mb-foot">' + T("The time-weighted return removes the effect of money put in or taken out, so it can be compared with the S&P 500. Values use daily closes; purchases funded beyond your recorded cash count as new money.") + "</p>")
    if missing:
        st.caption(T("Price history unavailable right now for: {t}.", t=", ".join(missing)))


# =========================================================================== Transactions
def transaction_form() -> None:
    st.html(f'<div class="mb-sec">{T("Add a transaction")}</div>')
    kinds = ["buy", "sell", "dividend", "deposit", "withdraw"]
    typ = choice(st.segmented_control, T("Type"), [k.title() for k in kinds], key="pf_tx_type", default="Buy") or "Buy"
    typ = typ.lower()
    with st.form("pf_tx_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        day = c1.date_input(T("Date"), value=dt.date.today(), max_value=dt.date.today(), format="YYYY-MM-DD")
        ticker = shares = price = fee = amount = None
        if typ in ("buy", "sell", "dividend"):
            ticker = c2.text_input(T("Ticker (US-listed stock or ETF)"), placeholder="AAPL")
        if typ in ("buy", "sell"):
            shares = c3.number_input(T("Shares"), min_value=0.0, value=0.0, step=1.0, format="%.4f")
            d1, d2 = st.columns(2)
            price = d1.number_input(T("Price per share (USD)"), min_value=0.0, value=0.0, step=0.01, format="%.4f")
            fee = d2.number_input(T("Fees (USD)"), min_value=0.0, value=0.0, step=0.5)
        else:
            amount = c3.number_input(T("Amount (USD)"), min_value=0.0, value=0.0, step=10.0)
        note = st.text_input(T("Note (optional)"), max_chars=120)
        ok = st.form_submit_button(T("Save transaction"), type="primary")
    if ok:
        raw = {"type": typ, "date": day.isoformat(), "ticker": (ticker or "").strip().upper(), "shares": shares, "price": price,
               "fee": fee, "amount": amount, "note": note}
        try:
            tx = pf.clean_transaction(raw)
        except ValueError:
            st.error(T("Please complete the fields: ticker, shares and price for trades; ticker and amount for dividends; amount for cash."))
            return
        if tx.get("ticker") and not safe(data.quote, tx["ticker"]):
            st.error(T("{t} wasn't found as a US-listed stock or ETF. Check the ticker.", t=tx["ticker"]))
            return
        b = store.book()
        if typ == "sell":
            held = pf.positions(b["transactions"])["holdings"].get(tx["ticker"], {}).get("shares", 0)
            if tx["shares"] > held + 1e-9:
                st.error(T("You hold {h} shares of {t}; you can't sell {n}.", h=f"{held:g}", t=tx["ticker"], n=f"{tx['shares']:g}"))
                return
        b = dict(b, transactions=b["transactions"] + [tx])
        store.save(pf.clean_book(b)[0])
        st.toast(T("Saved"))
        st.rerun()


def restore_box() -> None:
    up = st.file_uploader(T("Backup file (.json)"), type=["json"], key="pf_restore")
    if up is not None and st.button(T("Restore this backup"), key="pf_restore_btn"):
        try:
            problems = store.restore(up.getvalue())
            if problems:
                st.warning(T("Restored, skipping rows that were not valid: {p}", p="; ".join(problems[:5])))
            st.rerun()
        except (ValueError, UnicodeDecodeError):
            st.error(T("That file isn't a Market Brief backup."))


def transactions(s: dict) -> None:
    a, b = st.columns([1.6, 1], gap="medium")
    with a:
        transaction_form()
    with b:
        st.html(f'<div class="mb-sec">{T("Cash balance")}</div>')
        cur = s["pos"]["cash"]
        with st.form("pf_cash_form"):
            target = st.number_input(T("Cash I have available now (USD)"), min_value=0.0, value=float(round(cur, 2)), step=50.0)
            if st.form_submit_button(T("Update cash")):
                diff = round(target - cur, 2)
                if abs(diff) >= 0.01:
                    tx = pf.clean_transaction({"type": "cash_adjust", "date": dt.date.today().isoformat(), "amount": diff,
                                               "note": "cash balance update"})
                    bk = store.book()
                    store.save(pf.clean_book(dict(bk, transactions=bk["transactions"] + [tx]))[0])
                    st.rerun()
        st.html('<p class="mb-foot">' + T("Sets the cash you report; the difference is recorded as a cash adjustment.") + "</p>")
        st.html(f'<div class="mb-sec">{T("Backup")}</div>')
        st.download_button(T("Download backup (.json)"), store.backup_bytes(), file_name=f"market-brief-portfolio-{dt.date.today()}.json",
                           mime="application/json", width="stretch")
        restore_box()

    st.html(f'<div class="mb-sec">{T("History")}</div>')
    txs = list(reversed(s["txs"]))
    df = pd.DataFrame([{T("Delete"): False, T("Date"): t["date"], T("Type"): T(t["type"].replace("_", " ").title()),
                        T("Ticker"): t.get("ticker", ""), T("Shares"): t.get("shares"), T("Price"): t.get("price"),
                        T("Amount"): t.get("amount", (t.get("shares") or 0) * (t.get("price") or 0) or None),
                        T("Note"): t.get("note", ""), "id": t["id"]} for t in txs])
    edited = st.data_editor(df, hide_index=True, disabled=[c for c in df.columns if c != T("Delete")], column_config={"id": None},
                            key=f"pf_tx_editor_{len(txs)}_{lang()}", width="stretch")
    picked = edited.loc[edited[T("Delete")], "id"].tolist() if len(edited) else []
    c1, c2 = st.columns([1, 3])
    if c1.button(T("Delete selected ({n})", n=len(picked)), disabled=not picked):
        bk = store.book()
        store.save(pf.clean_book(dict(bk, transactions=[t for t in bk["transactions"] if t["id"] not in picked]))[0])
        st.rerun()
    with c2.expander(T("Erase all portfolio data from this browser")):
        st.caption(T("This removes every transaction and your investor profile from this browser. Download a backup first if you may need it."))
        if st.checkbox(T("I understand"), key="pf_erase_ok") and st.button(T("Erase everything"), type="primary"):
            store.clear()
            st.rerun()


# =========================================================================== Risk
@st.cache_data(ttl=3600, show_spinner=False)
def _risk_cached(weights_key: str, weights: dict[str, float], value: float, rf: float) -> dict:
    closes, _ = load_closes([t for t in weights if t != pf.CASH] + ["SPY"])
    rets = pf.returns_matrix({t: closes[t] for t in weights if t in closes})
    out = pf.risk_report(rets, weights, value, rf, closes.get("SPY"))
    out["corr"] = rets.corr() if rets.shape[1] > 1 else None
    out["missing"] = [t for t in weights if t != pf.CASH and t not in closes]
    return out


def risk_of(s: dict) -> dict:
    rf, _ = data.risk_free_rate()
    key = json.dumps(sorted((k, round(v, 4)) for k, v in s["weights"].items()))
    with st.spinner(T("Measuring risk on two years of daily prices…")):
        return _risk_cached(key, s["weights"], s["total"], rf)


METRIC_HELP = {
    "Volatility": "How much the portfolio's value swings in a typical year (standard deviation of returns). Higher = bumpier ride.",
    "Sharpe ratio": "Return earned above the 10-year Treasury per unit of volatility. Above 1 is good, below 0 means cash would have done better.",
    "Beta vs S&P 500": "How strongly the portfolio follows the market: 1 moves with it, 1.3 moves about 30% more, 0.7 about 30% less.",
    "Max drawdown": "The worst fall from a peak to a low in the period. It shows the pain you would have had to sit through.",
    "VaR 95%, 1 day": "On 19 days out of 20 the daily loss was smaller than this (historical). On the 20th day it was larger.",
    "CVaR 95%, 1 day": "The average loss on those worst 1-in-20 days: what a bad day tends to look like.",
    "VaR 95%, 1 month": "The same idea over a month, estimated from volatility (normal model). A rough guide, not a limit.",
}


def risk_section(s: dict) -> None:
    r = risk_of(s)
    if not r or not r.get("vol"):
        st.info(T("Not enough price history to measure risk yet (it needs about three months of prices for each position)."))
        return
    st.html(stat_grid([
        (T("Volatility"), pct(r["vol"], 1, False), ""), (T("Sharpe ratio"), num(r["sharpe"]), ""),
        (T("Beta vs S&P 500"), num(r["beta"]), ""), (T("Max drawdown"), pct(r["max_drawdown"]), "neg"),
        (T("VaR 95%, 1 day"), f'{money(r["var95_1d_usd"], 0)} · {pct(r["var95_1d"], 1, False)}', ""),
        (T("CVaR 95%, 1 day"), f'{money(r["cvar95_1d_usd"], 0)} · {pct(r["cvar95_1d"], 1, False)}', ""),
        (T("VaR 95%, 1 month"), f'{money(r["var95_1m_param_usd"], 0)} · {pct(r["var95_1m_param"], 1, False)}', ""),
    ], cols=7))
    st.html('<p class="mb-foot">' + T("Measured with today's weights over the last {d} trading days of real prices (cash counted as riskless). Past behaviour, not a forecast.", d=r["days"]) + "</p>")
    if r.get("missing"):
        st.caption(T("Left out for lack of price history: {t}.", t=", ".join(r["missing"])))

    a, b = st.columns([1.2, 1], gap="medium")
    with a:
        st.html(f'<div class="mb-sec">{T("What drives the risk")} {src("calc")}</div>')
        rc = r["risk_contrib"]
        cats = [t for t in sorted(rc, key=rc.get, reverse=True) if t != pf.CASH]
        if cats:
            st.plotly_chart(charts.grouped_bars(cats, [(T("Share of value"), [s["weights"].get(t, 0) for t in cats], "accent"),
                                                       (T("Share of risk"), [rc[t] for t in cats], "orange")]),
                            config=charts.CONFIG, key=f"pf_rc_{lang()}")
            st.html('<p class="mb-foot">' + T("When a position's share of risk is much bigger than its share of value, it is the one making the portfolio bumpy.") + "</p>")
    with b:
        st.html(f'<div class="mb-sec">{T("What each number means")}</div>')
        st.html('<div class="mb-panel">' + "".join(f'<p class="mb-p"><b>{T(k)}.</b> {T(v)}</p>' for k, v in METRIC_HELP.items()) + "</div>")

    if r.get("corr") is not None:
        c1, c2 = st.columns([1.2, 1], gap="medium")
        with c1:
            st.html(f'<div class="mb-sec">{T("Correlation between positions")} {src("calc")}</div>')
            st.plotly_chart(charts.correlation(r["corr"].rename_axis(None)), config=charts.CONFIG, key=f"pf_corr_{lang()}")
        with c2:
            st.html(f'<div class="mb-sec">{T("Drawdown with today’s mix")}</div>')
            st.plotly_chart(charts.drawdown(r["index"]), config=charts.CONFIG, key=f"pf_dd_{lang()}")
    st.html(f'<div class="mb-sec">{T("Main risks")}</div>')
    st.html('<div class="mb-panel"><ul class="mb-ul">' + "".join(f"<li>{x}</li>" for x in main_risks(s, r)) + "</ul></div>")


def main_risks(s: dict, r: dict) -> list[str]:
    out = []
    rc = {k: v for k, v in r.get("risk_contrib", {}).items() if k != pf.CASH}
    if rc:
        top = max(rc, key=rc.get)
        out.append(T("{t} carries {r} of the portfolio's risk with {w} of its value.", t=f"<b>{esc(top)}</b>", r=pct(rc[top], 0, False),
                     w=pct(s["weights"].get(top, 0), 0, False)))
    corr = r.get("corr")
    if corr is not None:
        pairs = [(a, b, corr.loc[a, b]) for i, a in enumerate(corr.columns) for b in corr.columns[i + 1:] if corr.loc[a, b] > 0.75]
        for a, b, c in sorted(pairs, key=lambda x: -x[2])[:3]:
            out.append(T("{a} and {b} move closely together (correlation {c}), so they diversify each other little.",
                         a=f"<b>{esc(a)}</b>", b=f"<b>{esc(b)}</b>", c=f"{c:.2f}"))
    conc = pf.concentration(s["table"], {t: m["etf"] for t, m in s["meta"].items()})
    if conc["largest_stock"] and conc["largest_stock_weight"] > 0.2:
        out.append(T("A single company, {t}, is {w} of the portfolio: company-specific news can move your whole result.",
                     t=f"<b>{esc(conc['largest_stock'])}</b>", w=pct(conc["largest_stock_weight"], 0, False)))
    if r.get("beta") is not None and r["beta"] > 1.15:
        out.append(T("Beta of {b}: in a market fall the portfolio has tended to drop more than the S&P 500.", b=f"{r['beta']:.2f}"))
    if r.get("max_drawdown") is not None and r["max_drawdown"] < -0.25:
        out.append(T("With today's mix the portfolio would have fallen {d} from a peak in the last two years.", d=pct(-r["max_drawdown"], 0, False)))
    return out or [T("No single risk stands out: positions are spread and none dominates the risk.")]


# =========================================================================== Investor profile
def profile_section(s: dict) -> None:
    saved = (s["book"].get("profile") or {}).get("answers") or {}
    st.html('<div class="mb-callout">' + T("Six questions. Your answers set a risk profile, and the app checks your real portfolio against it. Willingness (what you want) and capacity (what you can afford) are scored apart: if they disagree, the lower one wins.") + "</div>")
    qtext = {"goal": "What is the main goal of this money?", "horizon": "When will you need most of it?",
             "drop": "Your portfolio falls 20% in a few weeks. What do you do?",
             "loss": "What is the largest one-year loss you could take without it changing your plans?",
             "liquidity": "How much of this money might you need to withdraw soon?",
             "style": "What kind of investments do you prefer?"}
    with st.form("pf_profile_form"):
        answers = {}
        for k, opts in pf.QUESTIONS.items():
            labels = [T(o) for o in opts]
            idx = int(saved.get(k, 3)) - 1
            pick = st.radio(T(qtext[k]), labels, index=idx, key=f"pf_q_{k}_{lang()}")
            answers[k] = labels.index(pick) + 1
        if st.form_submit_button(T("Save my profile"), type="primary"):
            bk = store.book()
            store.save(dict(bk, profile={"answers": answers, "saved": dt.date.today().isoformat()}))
            st.rerun()
    prof = s["profile"]
    if not prof:
        return
    lim = {"capacity": T("limited by your capacity to take losses"), "willingness": T("limited by your willingness to take risk")}.get(prof["limited_by"] or "", "")
    st.html(f'<div class="mb-verdict"><div><div class="k">{T("Your profile")}</div><div class="label">{esc(T(prof["name"]))}</div>'
            f'<div class="k">{T("Score")} {prof["score"]:.1f} / 5 {("· " + lim) if lim else ""}</div></div>'
            f'<div><div class="k">{T("Willingness / capacity")}</div><div class="v num">{prof["willingness"]:.1f} / {prof["capacity"]:.1f}</div></div>'
            f'<div><div class="k">{T("Guide rails for this profile")}</div><div class="k">'
            + T("Volatility up to {v} · drawdown up to {d} · one company up to {c} · cash and bonds at least {m}",
                v=pct(prof["target_vol"], 0, False), d=pct(prof["max_drawdown"], 0, False), c=pct(prof["single_cap"], 0, False),
                m=pct(prof["min_safe"], 0, False)) + "</div></div></div>")
    r = risk_of(s)
    conc = pf.concentration(s["table"], {t: m["etf"] for t, m in s["meta"].items()})
    safe_w = conc["cash_weight"] + sum(w for t, w in s["weights"].items() if pf.ETF_SECTOR.get(t) == "Bonds")
    checks = pf.profile_checks(prof, r or {}, conc, safe_w)
    st.html(f'<div class="mb-sec">{T("Your portfolio against your profile")} {src("calc")}</div>')
    st.html('<div class="mb-panel">' + "".join(check_html(c) for c in checks) + "</div>")


def check_html(c: dict) -> str:
    cls = {"high": "down", "medium": "hold", "ok": "up"}[c["level"]]
    word = {"high": "Mismatch", "medium": "Watch", "ok": "In line"}[c["level"]]
    v, lim = pct(c["value"], 1, False), pct(c["limit"], 0, False)
    msgs = {
        "vol_high": T("Volatility is {v}, above the {l} that fits your profile. Expect bigger swings than you said you are comfortable with.", v=v, l=lim),
        "vol_low": T("Volatility is {v}, well below the {l} your profile allows. That is safe, but you may be giving up long-term growth.", v=v, l=lim),
        "vol_ok": T("Volatility is {v}, within the {l} that fits your profile.", v=v, l=lim),
        "dd_high": T("With today's mix the worst fall in two years was {v}, deeper than the {l} you said you could take.", v=v, l=lim),
        "dd_ok": T("The worst fall in two years with today's mix was {v}, within your {l} tolerance.", v=v, l=lim),
        "single_high": T("{t} alone is {v} of the portfolio, above the {l} limit for one company in your profile.", t=esc(c.get("ticker", "")), v=v, l=lim),
        "safe_low": T("Cash and bonds are {v} of the portfolio; with your liquidity needs and profile at least {l} is advisable.", v=v, l=lim),
        "sector_high": T("{s} is {v} of the portfolio: a sector-specific shock would hit a large part of it.", s=esc(T(c.get("sector", ""))), v=v),
    }
    return f'<div class="mb-check">{badge(word, cls)}<p class="mb-p">{msgs[c["code"]]}</p></div>'


# =========================================================================== News impact
def related_headlines(s: dict) -> tuple[list[dict], dict[str, list[dict]]]:
    items, _ = safe(data.news_desk, default=([], [])) or ([], [])
    now = dt.datetime.now(data.ET)
    recent = [i for i in items if i.get("time") and i["time"] >= now - dt.timedelta(hours=news.window_hours(now))]
    per: dict[str, list[dict]] = {t: [] for t in s["tickers"]}
    picked: dict[str, dict] = {}

    def add(item, t):
        key = item["url"]
        if key not in picked:
            picked[key] = dict(item, matched=[])
        if t and t not in picked[key]["matched"]:
            picked[key]["matched"].append(t)
        if t and item not in per[t]:
            per[t].append(item)

    for t in s["tickers"]:
        m = s["meta"][t]
        for n in (safe(data.company_news, t, default=[]) or [])[:4]:
            add(n, t)
        short = re.split(r"[ ,.]", m["name"])[0] if m["name"] and m["name"] != t else ""
        pat = re.compile(r"\b(" + re.escape(t) + (("|" + re.escape(short)) if len(short) > 3 else "") + r")\b")
        sectors = {NEWS_SECTOR_FOR_ETF[t]} if t in NEWS_SECTOR_FOR_ETF else set(news.classify(m["industry"] + " " + m["name"]))
        for it in recent:
            if pat.search(it["title"]):
                add(it, t)
        for it in [i for i in recent if sectors & set(i.get("sectors", []))][:3]:
            add(it, t)
    for region, k in (("USA", 6), ("World", 4)):
        for it in [i for i in recent if i.get("region") == region][:k]:
            add(it, None)
    allh = sorted(picked.values(), key=lambda x: x["time"] or now, reverse=True)[:45]
    return allh, per


def news_impact(s: dict) -> None:
    allh, per = related_headlines(s)
    st.html('<div class="mb-callout">' + T("Connects the headlines the app already collects (company news, the news desk and macro) with your positions. The AI explains the possible direction and why; it gives no numbers and a negative headline is not a sell signal by itself.") + "</div>")
    sig = signature(s, "news" + lang() + str(dt.datetime.now(data.ET).hour // 3))
    run_key = f"pf_news_run_{sig}"
    if st.button(T("Analyze today's news for my portfolio"), type="primary", key="pf_news_btn"):
        st.session_state[run_key] = True
    view = None
    if st.session_state.get(run_key):
        with st.spinner(T("Reading the news against your positions… (20 to 40 seconds)")):
            try:
                from views_news import fx_and_rates
                _, fx_text = fx_and_rates()
                pos_text = "\n".join(f"- {t} ({s['meta'][t]['name']}, {s['meta'][t]['sector']}): {pct(s['weights'].get(t, 0), 1, False)}"
                                     for t in s["tickers"]) + f"\n- Cash: {pct(s['weights'].get(pf.CASH, 0), 1, False)}"
                view = ai.portfolio_news(sig, lang(), pos_text, fx_text, allh)
                st.session_state["pf_news_view"] = view
            except Exception as exc:
                st.warning(T("The AI read couldn't be written this time ({e}). The matched headlines are below.", e=exc))
    if view:
        st.html(f'<div class="mb-story top"><div class="mb-kicker">{T("AI read")} {src("ai")}</div><p class="mb-lead" style="margin:.3rem 0 0">'
                f'{esc(view.get("summary", ""))}</p></div>')
        macro = view.get("macro") or []
        if macro:
            st.html(f'<div class="mb-sec">{T("Macro factors")}</div><div class="mb-grid3">' + "".join(
                f'<div class="mb-story"><h3>{esc(m.get("factor", ""))} {badge(m.get("effect", "Uncertain"), EFFECT_CLASS.get(m.get("effect"), "flat"))}</h3>'
                f'<p>{esc(m.get("why", ""))}</p><p class="watch">{T("Affects")}: {esc(", ".join(m.get("affected", []) or ["–"]))}</p></div>'
                for m in macro) + "</div>")
    st.html(f'<div class="mb-sec">{T("By position")}</div>')
    pv = {p.get("ticker"): p for p in (view or {}).get("positions", [])}
    cards = []
    for t in s["tickers"]:
        p = pv.get(t)
        heads = (p or {}).get("sources") or per.get(t, [])[:4]
        links = "".join(f'<a class="mb-src" href="{esc(h["url"])}" target="_blank" rel="noopener">{esc(h["source"])}: {esc(h["title"][:70])}</a>'
                        for h in heads[:4])
        if p:
            review = f'<span class="mb-chip down">{T("Review this position")}</span>' if p.get("review") else ""
            body = (f'<p>{esc(p.get("why", ""))}</p>' + (f'<p class="watch"><b>{T("What to check.")}</b> {esc(p.get("what_to_check", ""))}</p>'
                                                         if p.get("what_to_check") else ""))
            head = f'{badge(p.get("effect", "Uncertain"), EFFECT_CLASS.get(p.get("effect"), "flat"))} {review}'
        else:
            body = f'<p>{T("{n} related headlines found.", n=len(per.get(t, [])))}</p>' if per.get(t) else f'<p>{T("No related headlines today.")}</p>'
            head = ""
        cards.append(f'<div class="mb-story"><h3>{esc(t)} <span style="font-weight:400;color:var(--muted);font-size:.8rem">'
                     f'{esc(s["meta"][t]["name"])}</span></h3><div class="mb-take-row" style="margin:.2rem 0 .4rem">{head}</div>{body}'
                     f'<div class="mb-sources">{links}</div></div>')
    st.html('<div class="mb-grid2">' + "".join(cards) + "</div>")
    if view:
        st.html('<p class="mb-note">' + T("Written {d} ET from {n} headlines. Model interpretation, not investment advice.",
                                            d=D(view["generated_at"], "%b %d, %-I:%M %p"), n=len(allh)) + "</p>")


# =========================================================================== Optimization
def caps_for(tickers: list[str], meta: dict, prof: dict) -> dict[str, float]:
    caps = {}
    for t in tickers:
        if t == "GLD" or pf.ETF_SECTOR.get(t) == "Gold & commodities":
            caps[t] = 0.15
        elif (meta.get(t) or {}).get("etf", t in pf.KNOWN_ETFS):
            caps[t] = 0.60
        else:
            caps[t] = prof["single_cap"]
    return caps


@st.cache_data(ttl=3 * 3600, show_spinner=False)
def _opt_cached(key: str, tickers: tuple, caps: dict, target_vol: float, rf: float) -> dict | None:
    closes, missing = load_closes(list(tickers) + ["SPY"])
    use = [t for t in tickers if t in closes]
    if len(use) < 2:
        return None
    rets = pf.returns_matrix({t: closes[t] for t in use})
    cov = pf.ledoit_wolf(rets)
    mu = pf.capm_returns(rets, closes["SPY"], rf)
    out = pf.optimise(mu, cov, rf, {t: caps[t] for t in use}, target_vol=target_vol)
    out.update(mu=mu, cov=cov, rets=rets, missing=missing, universe=use)
    return out


def optimise_for(s: dict, include_div: bool) -> tuple[dict | None, dict]:
    prof = s["profile"] or pf.investor_profile({k: 3 for k in pf.QUESTIONS})
    universe = list(dict.fromkeys(s["tickers"] + (pf.DIVERSIFIERS if include_div else [])))
    meta = dict(s["meta"])
    for t in universe:
        meta.setdefault(t, {"etf": t in pf.KNOWN_ETFS, "name": t, "sector": pf.ETF_SECTOR.get(t, "Other")})
    caps = caps_for(universe, meta, prof)
    rf, _ = data.risk_free_rate()
    key = json.dumps([universe, prof["name"], dt.date.today().isoformat()])
    with st.spinner(T("Optimising on two years of prices (the first run can take up to a minute on the free data plan)…")):
        opt = _opt_cached(key, tuple(universe), caps, prof["target_vol"], rf)
    return opt, prof


def current_point(s: dict, opt: dict) -> dict:
    rf, _ = data.risk_free_rate()
    mu2, cov2 = pf.with_cash(opt["mu"], opt["cov"], rf)
    w = {k: v for k, v in s["weights"].items() if k in mu2.index}
    return pf.mix_stats(w, mu2, cov2, rf)


def backtest_stats(opt: dict, weights: dict[str, float], value: float) -> dict:
    rf, _ = data.risk_free_rate()
    r = pf.risk_report(opt["rets"], {k: v for k, v in weights.items() if k in opt["rets"].columns or k == pf.CASH}, value, rf)
    return r or {}


def optimization(s: dict) -> None:
    include = st.toggle(T("Also consider diversifiers I don't own (S&P 500, bonds, gold, international and emerging markets ETFs)"),
                        value=True, key="pf_opt_div")
    opt, prof = optimise_for(s, include)
    if not opt:
        st.info(T("The optimiser needs price history for at least two assets. Add positions or turn on the diversifiers."))
        return
    if not s["profile"]:
        st.caption(T("No investor profile saved yet, so a Moderate profile is assumed. Fill in the Investor profile section."))
    cur = current_point(s, opt)
    labels = {"current": T("Your portfolio"), "gmv": T("Minimum variance"), "max_sharpe": T("Maximum Sharpe"),
              "profile": T("Best for your profile ({p})", p=T(prof["name"]))}
    pts = {"current": (labels["current"], cur), "gmv": (labels["gmv"], opt["gmv"]), "max_sharpe": (labels["max_sharpe"], opt["max_sharpe"]),
           "profile": (labels["profile"], opt.get("profile"))}
    st.plotly_chart(charts.frontier(opt, pts, prof["target_vol"]), config=charts.CONFIG, key=f"pf_frontier_{lang()}")
    st.html('<p class="mb-foot">' + T("Expected returns come from CAPM (10-year Treasury + beta × 5% equity premium) rather than past returns, which are too noisy to optimise on. Risk uses two years of daily returns with Ledoit-Wolf shrinkage. Long-only; one company is capped at your profile's limit, funds at 60%, gold at 15%. Your portfolio's point includes its cash.") + "</p>")
    if opt.get("missing"):
        st.caption(T("Left out for lack of price history: {t}.", t=", ".join(opt["missing"])))

    names = list(dict.fromkeys([t for t in s["tickers"]] + [t for k in ("gmv", "max_sharpe", "profile") for t in (opt.get(k) or {}).get("weights", {})]))
    cols = [("current", labels["current"]), ("gmv", labels["gmv"]), ("max_sharpe", labels["max_sharpe"]), ("profile", labels["profile"])]
    wmap = {"current": s["weights"], **{k: (opt.get(k) or {}).get("weights", {}) for k in ("gmv", "max_sharpe", "profile")}}
    body = ""
    for t in names + [pf.CASH]:
        vals = [wmap[k].get(t, 0.0) for k, _ in cols]
        if max(vals) < 0.0005:
            continue
        body += f'<tr><td class="l">{esc(T("Cash") if t == pf.CASH else t)}</td>' + "".join(f'<td class="num">{pct(v, 1, False)}</td>' for v in vals) + "</tr>"
    stats = {"current": cur, **{k: opt.get(k) for k in ("gmv", "max_sharpe", "profile")}}
    bts = {k: backtest_stats(opt, wmap[k], s["total"]) for k, _ in cols}
    for label, f in ((T("Expected return"), lambda k: pct((stats[k] or {}).get("ret"), 1, False)),
                     (T("Expected volatility"), lambda k: pct((stats[k] or {}).get("vol"), 1, False)),
                     (T("Expected Sharpe"), lambda k: num((stats[k] or {}).get("sharpe"))),
                     (T("Max drawdown, last 2 years"), lambda k: pct(bts[k].get("max_drawdown"))),
                     (T("VaR 95%, 1 day"), lambda k: pct(bts[k].get("var95_1d"), 1, False))):
        body += f'<tr><td class="l"><b>{label}</b></td>' + "".join(f'<td class="num">{f(k)}</td>' for k, _ in cols) + "</tr>"
    head = "".join(f"<th>{esc(lbl)}</th>" for _, lbl in cols)
    st.html(f'<div class="mb-sec">{T("Weights and statistics")} {src("calc")}</div><div class="mb-scroll"><table class="mb-tbl">'
            f'<tr><th class="l">{T("Asset")}</th>{head}</tr>{body}</table></div>')
    st.html(f'<div class="mb-sec">{T("Which one fits you")}</div><div class="mb-callout">{why_profile(opt, prof, cur)}</div>')


def why_profile(opt: dict, prof: dict, cur: dict) -> str:
    p, ms, g = opt.get("profile") or {}, opt["max_sharpe"], opt["gmv"]
    tv = pct(prof["target_vol"], 0, False)
    parts = []
    if p and not p.get("feasible", True):
        parts.append(T("Even the minimum-variance mix of these assets is riskier than your profile's {tv} volatility guide, so the suggestion is the minimum-variance portfolio. To get closer, hold more cash or bonds.", tv=tv))
    elif p:
        parts.append(T("The suggested portfolio is the one with the highest expected return whose volatility stays within the {tv} that fits a {name} profile: it uses your full risk budget and no more.", tv=tv, name=T(prof["name"])))
    if ms.get("vol") and ms["vol"] > prof["target_vol"] * 1.05:
        parts.append(T("Maximum Sharpe has the best return per unit of risk on paper, but its {v} volatility is above your guide, so it is not the default here.", v=pct(ms["vol"], 1, False)))
    elif ms.get("vol"):
        parts.append(T("Maximum Sharpe ({v} volatility) also fits your profile; it is the most efficient mix but leans on the return estimates, which are uncertain.", v=pct(ms["vol"], 1, False)))
    parts.append(T("Minimum variance ({v}) is the calmest mix, at the cost of a lower expected return.", v=pct(g["vol"], 1, False)))
    if cur.get("vol") is not None:
        parts.append(T("Your portfolio today: {v} volatility and {r} expected return.", v=pct(cur["vol"], 1, False), r=pct(cur["ret"], 1, False)))
    parts.append(T("Optimisers amplify estimation errors, so treat these weights as a direction, not an exact recipe."))
    return " ".join(parts)


# =========================================================================== Recommendations
def signals(s: dict, opt: dict, prof: dict) -> tuple[list[dict], list[dict], dict]:
    rf, _ = data.risk_free_rate()
    mu2, cov2 = pf.with_cash(opt["mu"], opt["cov"], rf)
    w_now = {k: v for k, v in s["weights"].items() if k in mu2.index}
    now_stats = pf.mix_stats(w_now, mu2, cov2, rf)
    target = (opt.get("profile") or opt["gmv"])["weights"]
    invested = 1 - s["weights"].get(pf.CASH, 0.0)
    rows = []
    risk = risk_of(s)
    rc = risk.get("risk_contrib", {}) if risk else {}
    recs_cache = {}
    for t in s["tickers"]:
        m = s["meta"][t]
        w = s["weights"].get(t, 0.0)
        w_inv = w / invested if invested > 0 else 0.0
        opt_w = target.get(t, 0.0)
        target_total = opt_w * invested
        recs = safe(data.recommendations, t, default=[]) or []
        cs = analysis.consensus(recs[0]) if recs else None
        recs_cache[t] = cs
        val = None
        if not m["etf"] and s["prices"].get(t):
            val = safe(quick_value, t, round(s["prices"][t], 2))
        news_eff = ((st.session_state.get("pf_news_view") or {}).get("positions") or [])
        news_eff = next((p.get("effect") for p in news_eff if p.get("ticker") == t), None)
        sig = "Hold"
        if not m["etf"] and w > prof["single_cap"] * 1.1:
            sig = "Reduce"
        elif opt_w < 0.01 and w_inv > 0.02:
            weak = sum([bool(val and val["label"] == "Looks overvalued"), bool(cs and cs["label"] in ("Sell", "Strong Sell")),
                        news_eff == "Negative"])
            sig = "Sell" if weak >= 2 else "Reduce"
        elif opt_w - w_inv > 0.05:
            sig = "Buy more"
        elif opt_w - w_inv < -0.05:
            sig = "Reduce"
        new_w = pf.shift_weights(w_now, t, target_total if sig != "Hold" else w) if t in mu2.index else w_now
        after = pf.mix_stats(new_w, mu2, cov2, rf)
        q = safe(lambda: data.history(t)["close"])
        rows.append({"ticker": t, "name": m["name"], "weight": w, "opt_weight_total": target_total, "risk_share": rc.get(t),
                     "ret_1y": analysis.period_return(q, 252) if q is not None else None,
                     "vol": analysis.annual_volatility(q) if q is not None else None,
                     "dcf_gap": val["gap"] if val else None, "dcf_label": val["label"] if val else None,
                     "consensus": f'{cs["label"]} ({cs["score"]:.2f}/5)' if cs else None, "news": news_eff, "signal": sig,
                     "vol_after": after["vol"], "ret_after": after["ret"], "pnl_pct": float(s["table"].set_index("ticker").at[t, "unrealized_pct"] or 0)})
    ideas = []
    for t, wt in sorted(target.items(), key=lambda x: -x[1]):
        if t in s["tickers"] or wt < 0.03:
            continue
        add = min(wt * invested, 0.10)
        new_w = pf.shift_weights(w_now, t, add, funding="pro rata")
        after = pf.mix_stats(new_w, mu2, cov2, rf)
        corr = None
        if t in opt["rets"].columns:
            pr = pf.portfolio_returns(opt["rets"], {k: v for k, v in w_now.items() if k in opt["rets"].columns})
            corr = float(opt["rets"][t].corr(pr))
        ideas.append({"ticker": t, "what": T(pf.ETF_SECTOR.get(t, "")) or t, "weight": add, "corr": corr,
                      "vol_after": after["vol"], "ret_after": after["ret"], "sharpe_after": after["sharpe"]})
    reb = pf.mix_stats({**{k: v * invested for k, v in target.items()}, pf.CASH: s["weights"].get(pf.CASH, 0.0)}, mu2, cov2, rf)
    turnover = 0.5 * sum(abs(target.get(k, 0) * invested - s["weights"].get(k, 0)) for k in set(target) | set(s["tickers"]))
    return rows, ideas[:4], {"now": now_stats, "rebalanced": reb, "turnover": turnover}


def recommendations(s: dict) -> None:
    include = st.session_state.get("pf_opt_div", True)
    opt, prof = optimise_for(s, include)
    if not opt:
        st.info(T("The optimiser needs price history for at least two assets. Add positions or turn on the diversifiers."))
        return
    with st.spinner(T("Collecting valuation, analyst and risk data for each position…")):
        rows, ideas, port = signals(s, opt, prof)
    st.html('<div class="mb-callout">' + T("Signals are computed by the app from your profile, the optimiser, risk, valuation, analyst ratings and (if you ran it) the news read. The AI then explains them. Nothing is executed: you decide.") + "</div>")
    now, reb = port["now"], port["rebalanced"]
    st.html(stat_grid([
        (T("Volatility now"), pct(now["vol"], 1, False), ""), (T("After a profile rebalance"), pct(reb["vol"], 1, False), ""),
        (T("Expected return now"), pct(now["ret"], 1, False), ""), (T("After a profile rebalance"), pct(reb["ret"], 1, False), ""),
        (T("Share of the portfolio that would trade"), pct(port["turnover"], 0, False), ""),
    ]))
    body = ""
    for r in rows:
        body += (f'<tr><td class="l"><b>{esc(r["ticker"])}</b></td><td class="num">{pct(r["weight"], 1, False)}</td>'
                 f'<td class="num">{pct(r["opt_weight_total"], 1, False)}</td><td class="num">{pct(r["risk_share"], 0, False)}</td>'
                 f'<td class="num {signed_class(r["ret_1y"])}">{pct(r["ret_1y"])}</td>'
                 f'<td class="num {signed_class(r["dcf_gap"])}">{pct(r["dcf_gap"], 0) if r["dcf_gap"] is not None else "–"}</td>'
                 f'<td>{esc(T(r["consensus"].split(" (")[0]) + " (" + r["consensus"].split(" (")[1]) if r["consensus"] else "–"}</td>'
                 f'<td>{esc(T(r["news"])) if r["news"] else "–"}</td><td>{badge(r["signal"], ACTION_CLASS.get(r["signal"], "flat"))}</td>'
                 f'<td class="num">{pct(r["vol_after"], 1, False)}</td></tr>')
    head = "".join(f"<th>{T(h)}</th>" for h in ("Weight", "Profile target", "Share of risk", "1 year", "DCF upside", "Analysts",
                                                "News", "Model signal", "Volatility after"))
    st.html(f'<div class="mb-sec">{T("Signals by position")} {src("calc")} {src("ana")}</div><div class="mb-scroll"><table class="mb-tbl">'
            f'<tr><th class="l">{T("Ticker")}</th>{head}</tr>{body}</table></div>'
            '<p class="mb-foot">' + T("Volatility after = the whole portfolio's expected volatility if only that position moved to its target (cash absorbs the difference). DCF upside uses default assumptions; funds have none.") + "</p>")
    if ideas:
        ib = "".join(f'<tr><td class="l"><b>{esc(i["ticker"])}</b> <span class="co">{esc(i["what"])}</span></td><td class="num">{pct(i["weight"], 0, False)}</td>'
                     f'<td class="num">{num(i["corr"])}</td><td class="num">{pct(i["vol_after"], 1, False)}</td><td class="num">{pct(i["ret_after"], 1, False)}</td>'
                     f'<td class="num">{num(i["sharpe_after"])}</td></tr>' for i in ideas)
        ih = "".join(f"<th>{T(h)}</th>" for h in ("Suggested weight", "Correlation with your portfolio", "Volatility after", "Expected return after", "Sharpe after"))
        st.html(f'<div class="mb-sec">{T("New ideas from the optimiser")} {src("calc")}</div><div class="mb-scroll"><table class="mb-tbl">'
                f'<tr><th class="l">{T("Ticker")}</th>{ih}</tr>{ib}</table></div>'
                '<p class="mb-foot">' + T("Assets you don't own that the profile-optimal portfolio uses, added at up to 10% and funded pro rata from today's positions.") + "</p>")

    sig = signature(s, "advice" + lang() + prof["name"] + str(include) + str(bool(st.session_state.get("pf_news_view"))))
    run_key = f"pf_adv_run_{sig}"
    if st.button(T("Write the recommendations"), type="primary", key="pf_adv_btn"):
        st.session_state[run_key] = True
    if not st.session_state.get(run_key):
        return
    rf, _ = data.risk_free_rate()
    prof_text = (f"{prof['name']} (score {prof['score']:.1f}/5; volatility guide {pct(prof['target_vol'], 0, False)}, "
                 f"drawdown tolerance {pct(prof['max_drawdown'], 0, False)}, one company up to {pct(prof['single_cap'], 0, False)}, "
                 f"cash and bonds at least {pct(prof['min_safe'], 0, False)})" + ("" if s["profile"] else " — assumed, the client has not filled in the questionnaire"))
    r = risk_of(s) or {}
    risk_text = (f"Now: expected volatility {pct(now['vol'], 1, False)}, expected return (CAPM) {pct(now['ret'], 1, False)}, "
                 f"historical 2-year max drawdown {pct(r.get('max_drawdown'))}, beta {num(r.get('beta'))}, VaR 95% 1-day {pct(r.get('var95_1d'), 1, False)}. "
                 f"After rebalancing to the profile portfolio: expected volatility {pct(reb['vol'], 1, False)}, expected return {pct(reb['ret'], 1, False)}; "
                 f"{pct(port['turnover'], 0, False)} of the portfolio would trade. Risk-free rate {pct(rf, 2, False)}.")
    pos_text = "\n".join(
        f"- {x['ticker']} ({x['name']}): weight {pct(x['weight'], 1, False)}, profile target {pct(x['opt_weight_total'], 1, False)}, "
        f"share of risk {pct(x['risk_share'], 0, False)}, 1-year return {pct(x['ret_1y'])}, volatility {pct(x['vol'], 0, False)}, "
        f"unrealized return {pct(x['pnl_pct'])}, DCF {('upside ' + pct(x['dcf_gap'], 0) + ' (' + x['dcf_label'] + ')') if x['dcf_gap'] is not None else 'n/a'}, "
        f"analyst consensus {x['consensus'] or 'n/a'}, news read {x['news'] or 'not run'}; "
        f"above the one-company cap: {'yes' if (not s['meta'][x['ticker']]['etf'] and x['weight'] > prof['single_cap']) else 'no'}; MODEL SIGNAL {x['signal']}; "
        f"portfolio volatility if moved to target {pct(x['vol_after'], 1, False)} (expected return {pct(x['ret_after'], 1, False)})"
        for x in rows) + f"\n- Cash: {pct(s['weights'].get(pf.CASH, 0), 1, False)}"
    ideas_text = "\n".join(f"- {i['ticker']} ({pf.ETF_SECTOR.get(i['ticker'], '')}): add {pct(i['weight'], 0, False)}; correlation with portfolio {num(i['corr'])}; "
                           f"portfolio volatility after {pct(i['vol_after'], 1, False)} (now {pct(now['vol'], 1, False)}), expected return after "
                           f"{pct(i['ret_after'], 1, False)} (now {pct(now['ret'], 1, False)})" for i in ideas) or "(none)"
    nv = st.session_state.get("pf_news_view") or {}
    news_text = "\n".join(f"- {p.get('ticker')}: {p.get('effect')} — {p.get('why', '')}" for p in nv.get("positions", []))
    with st.spinner(T("Writing the recommendations… (20 to 40 seconds)")):
        try:
            adv = ai.portfolio_advice(sig, lang(), prof_text, risk_text, pos_text, ideas_text, news_text)
        except Exception as exc:
            st.warning(T("The recommendations couldn't be written this time ({e}). The computed signals above still apply.", e=exc))
            return
    ov = adv.get("overall") or {}
    st.html(f'<div class="mb-story top"><div class="mb-kicker">{T("Overall")} {src("ai")}</div>'
            f'<div class="mb-take-row" style="margin:.3rem 0 .5rem">{badge(ov.get("stance", "Keep as is"), ACTION_CLASS.get(ov.get("stance"), "hold"))}</div>'
            f'<p class="mb-lead" style="margin:0">{esc(ov.get("summary", ""))}</p></div>')
    cards = "".join(
        f'<div class="mb-story"><h3>{esc(i.get("ticker", ""))} {badge(i.get("action", "Hold"), ACTION_CLASS.get(i.get("action"), "flat"))}</h3>'
        f'<p><b>{T("What.")}</b> {esc(i.get("what", ""))}</p><p><b>{T("Why.")}</b> {esc(i.get("why", ""))}</p>'
        f'<p><b>{T("Data.")}</b> {esc(i.get("data", ""))}</p><p><b>{T("Risk change.")}</b> {esc(i.get("risk_change", ""))}</p>'
        f'<p class="watch"><b>{T("Downsides.")}</b> {esc(i.get("downsides", ""))}</p></div>' for i in adv.get("items", []))
    st.html(f'<div class="mb-grid2">{cards}</div><p class="mb-note">'
            + T("Written {d} ET. Model opinion built only from the numbers above; not investment advice. Nothing is bought or sold by the app.",
                d=D(adv["generated_at"], "%b %d, %-I:%M %p")) + "</p>")


# =========================================================================== Simulator
def simulator(s: dict) -> None:
    st.html('<div class="mb-callout">' + T("Try changes before making them. Edit the target shares (or add a row with a new ticker) and compare risk and expected return before and after. Your saved portfolio is never changed here.") + "</div>")
    base_rows = [{"Ticker": t, "Price": s["prices"].get(t), "Shares now": s["pos"]["holdings"][t]["shares"],
                  "Target shares": s["pos"]["holdings"][t]["shares"]} for t in s["tickers"]]
    if st.button(T("Fill in the profile-optimal weights")):
        opt, _ = optimise_for(s, st.session_state.get("pf_opt_div", True))
        if opt:
            target = (opt.get("profile") or opt["gmv"])["weights"]
            invested = s["total"] * (1 - s["weights"].get(pf.CASH, 0))
            rows = {r["Ticker"]: r for r in base_rows}
            for t, w in target.items():
                px = s["prices"].get(t) or safe(lambda: data.quote(t)["price"])
                if not px:
                    continue
                rows.setdefault(t, {"Ticker": t, "Price": px, "Shares now": 0.0, "Target shares": 0.0})
                rows[t]["Target shares"] = round(w * invested / px, 2)
            for t in rows:
                if t not in target:
                    rows[t]["Target shares"] = 0.0
            st.session_state["pf_sim_rows"] = list(rows.values())
    seed = st.session_state.get("pf_sim_rows") or base_rows
    df = pd.DataFrame(seed)[["Ticker", "Price", "Shares now", "Target shares"]]
    df.columns = [T(c) for c in df.columns]
    edited = st.data_editor(df, num_rows="dynamic", hide_index=True, width="stretch", key=f"pf_sim_{lang()}_{hash(str(seed)) % 10**6}",
                            disabled=[T("Price"), T("Shares now")],
                            column_config={T("Target shares"): st.column_config.NumberColumn(min_value=0.0, step=1.0, format="%.4f")})
    if not st.button(T("Compare before and after"), type="primary"):
        return
    target_shares, prices = {}, dict(s["prices"])
    for _, r in edited.iterrows():
        t = str(r[T("Ticker")] or "").strip().upper()
        if not t:
            continue
        n = float(r[T("Target shares")] or 0)
        if t not in prices:
            q = safe(data.quote, t)
            if not q:
                st.warning(T("{t} wasn't found as a US-listed stock or ETF. Check the ticker.", t=t))
                return
            prices[t] = q["price"]
        target_shares[t] = n
    now_val = {t: s["pos"]["holdings"][t]["shares"] * prices[t] for t in s["tickers"] if t in prices}
    new_val = {t: n * prices[t] for t, n in target_shares.items() if n > 0}
    cash_now = s["pos"]["cash"]
    spend = sum(new_val.values()) - sum(now_val.values())
    cash_after = cash_now - spend
    new_money = max(-cash_after, 0.0)
    cash_after = max(cash_after, 0.0)
    tot_before = sum(now_val.values()) + cash_now
    tot_after = sum(new_val.values()) + cash_after
    w_before = {**{t: v / tot_before for t, v in now_val.items()}, pf.CASH: cash_now / tot_before}
    w_after = {**{t: v / tot_after for t, v in new_val.items()}, pf.CASH: cash_after / tot_after}
    tickers = sorted(set(now_val) | set(new_val))
    with st.spinner(T("Loading prices for the comparison…")):
        closes, missing = load_closes(tickers + ["SPY"])
    if missing:
        st.caption(T("Left out for lack of price history: {t}.", t=", ".join(missing)))
    use = [t for t in tickers if t in closes]
    if not use:
        return
    rf, _ = data.risk_free_rate()
    rets = pf.returns_matrix({t: closes[t] for t in use})
    mu, cov = pf.capm_returns(rets, closes["SPY"], rf), pf.ledoit_wolf(rets)
    mu2, cov2 = pf.with_cash(mu, cov, rf)
    res = {}
    for name, w, tot in (("before", w_before, tot_before), ("after", w_after, tot_after)):
        ww = {k: v for k, v in w.items() if k in mu2.index}
        ex = pf.mix_stats(ww, mu2, cov2, rf)
        hist = pf.risk_report(rets, ww, tot, rf, closes.get("SPY")) or {}
        conc_w = pd.Series({k: v for k, v in w.items()})
        res[name] = {"Value": money(tot, 0), "Positions": str(len([k for k in w if k != pf.CASH and w[k] > 0])),
                     "Cash": money(tot * w.get(pf.CASH, 0), 0),
                     "Largest position": pct(max([v for k, v in w.items() if k != pf.CASH] or [0]), 1, False),
                     "Effective number of positions": num(1 / float((conc_w ** 2).sum()), 1),
                     "Expected return (CAPM)": pct(ex["ret"], 1, False), "Expected volatility": pct(ex["vol"], 1, False),
                     "Expected Sharpe": num(ex["sharpe"]), "Beta vs S&P 500": num(hist.get("beta")),
                     "Max drawdown, last 2 years": pct(hist.get("max_drawdown")), "VaR 95%, 1 day": money(hist.get("var95_1d_usd"), 0),
                     "CVaR 95%, 1 day": money(hist.get("cvar95_1d_usd"), 0)}
    body = "".join(f'<tr><td class="l">{T(k)}</td><td class="num">{res["before"][k]}</td><td class="num">{res["after"][k]}</td></tr>'
                   for k in res["before"])
    st.html(f'<div class="mb-sec">{T("Before and after")} {src("calc")}</div><div class="mb-scroll"><table class="mb-tbl">'
            f'<tr><th class="l"></th><th>{T("Now")}</th><th>{T("Simulated")}</th></tr>{body}</table></div>'
            + ('<p class="mb-foot">' + T("The changes need {m} of new money beyond your cash.", m=money(new_money, 0)) + "</p>" if new_money > 0.5 else ""))
    cats = [t for t in sorted(set(w_before) | set(w_after)) if max(w_before.get(t, 0), w_after.get(t, 0)) > 0.001]
    st.plotly_chart(charts.grouped_bars([T("Cash") if c == pf.CASH else c for c in cats],
                                        [(T("Now"), [w_before.get(c, 0) for c in cats], "faint"), (T("Simulated"), [w_after.get(c, 0) for c in cats], "accent")]),
                    config=charts.CONFIG, key=f"pf_sim_bars_{lang()}")
