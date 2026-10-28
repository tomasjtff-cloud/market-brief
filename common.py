"""Shared helpers: formatting, navigation state, the top bar and the ticker tape."""
from __future__ import annotations

import datetime as dt

import numpy as np
import streamlit as st

import data
from i18n import LANGS, D, T, choice
from ui import esc, link, sgn

DEFAULT_WATCHLIST = ["AAPL", "NVDA", "MSFT", "GOOGL", "TSLA"]
MAX_WATCHLIST = 8
BENCHMARK = "SPY"
PAGES = {"Markets": "markets", "News": "news", "Portfolio": "portfolio", "Map": "map", "Watchlist": "watchlist", "Compare": "compare",
         "Stock": "stock", "Methodology": "method"}
INDEX_ETFS = [("S&P 500", "SPY"), ("Nasdaq 100", "QQQ"), ("Dow Jones", "DIA"), ("Russell 2000", "IWM"),
              ("Gold", "GLD"), ("Crude oil", "USO")]


# =========================================================================== formatting
def isnum(x) -> bool:
    return x is not None and not (isinstance(x, float) and np.isnan(x))


def money(x, decimals: int = 2) -> str:
    if not isnum(x):
        return "n/a"
    sign, a = ("−" if x < 0 else ""), abs(x)
    for div, suffix in ((1e12, "T"), (1e9, "B"), (1e6, "M")):
        if a >= div:
            return f"{sign}${a / div:,.{decimals}f}{suffix}"
    return f"{sign}${a:,.{decimals}f}"


def big(x, decimals: int = 2) -> str:
    """Large counts without a currency sign (volume, shares)."""
    if not isnum(x):
        return "n/a"
    for div, suffix in ((1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "K")):
        if abs(x) >= div:
            return f"{x / div:,.{decimals}f}{suffix}"
    return f"{x:,.0f}"


def pct(x, decimals: int = 1, signed: bool = True) -> str:
    if not isnum(x):
        return "n/a"
    return sgn(x * 100, decimals) if signed else f"{x * 100:.{decimals}f}%"


def num(x, decimals: int = 2, suffix: str = "") -> str:
    return f"{x:,.{decimals}f}{suffix}" if isnum(x) else "n/a"


def when(t: dt.datetime | None) -> str:
    return f"{D(t, '%b %d, %-I:%M %p')} ET" if t else ""


def safe(fn, *args, default=None, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception:
        return default


# =========================================================================== state
def get_watchlist() -> list[str]:
    raw = st.query_params.get("w")
    if raw:
        wl = list(dict.fromkeys(t.strip().upper() for t in raw.split(",") if t.strip()))[:MAX_WATCHLIST]
        if wl:
            return wl
    return DEFAULT_WATCHLIST.copy()


def save_watchlist(wl: list[str]) -> None:
    st.query_params["w"] = ",".join(wl)


def add_to_watchlist(ticker: str) -> None:
    wl = get_watchlist()
    if ticker not in wl and len(wl) < MAX_WATCHLIST:
        save_watchlist(wl + [ticker])


def remove_from_watchlist(ticker: str) -> None:
    wl = [t for t in get_watchlist() if t != ticker]
    if wl:
        save_watchlist(wl)


def go_stock(ticker: str) -> None:
    st.session_state.ticker = ticker.upper()
    st.session_state.page = "Stock"
    st.session_state.q = ""


def init_state() -> None:
    if "page" not in st.session_state:
        qp = st.query_params.get("p", "markets")
        st.session_state.page = next((k for k, v in PAGES.items() if v == qp), "Markets")
    if "lang_sel" not in st.session_state:
        st.session_state.lang_sel = "ES" if st.query_params.get("lang", "").lower() == "es" else "EN"
    if "ticker" not in st.session_state:
        st.session_state.ticker = (st.query_params.get("t") or get_watchlist()[0]).upper()
    if st.session_state.page:
        st.session_state.last_page = st.session_state.page


def current_page() -> str:
    page = st.session_state.get("page") or st.session_state.get("last_page") or "Markets"
    st.query_params["p"] = PAGES[page]
    if st.session_state.get("lang_sel") == "ES":
        st.query_params["lang"] = "es"
    elif "lang" in st.query_params:
        del st.query_params["lang"]
    if page == "Stock":
        st.query_params["t"] = st.session_state.ticker
    elif "t" in st.query_params:
        del st.query_params["t"]
    return page


# =========================================================================== top bar & tape
def top_bar() -> None:
    with st.container(key="topbar"):
        c1, c2, c4, c3 = st.columns([1.15, 5.5, 0.8, 1.55], vertical_alignment="center")
        c1.html('<div class="mb-logo"><span class="mark">MB</span><span>Market Brief'
                f'<small>{T("Free markets terminal")}</small></span></div>')
        with c2:
            choice(st.segmented_control, "Navigate", list(PAGES), key="page", default="Markets", label_visibility="collapsed")
        with c4:
            st.segmented_control("Language", list(LANGS), key="lang_sel", label_visibility="collapsed",
                                 help="English / Español")
        with c3:
            q = st.text_input("Search", key="q", placeholder=T("Search a company or ticker"), label_visibility="collapsed")
            if q and q.strip():
                results = safe(data.search_symbols, q.strip(), default=[])
                if results:
                    pick = st.selectbox("Results", results, label_visibility="collapsed", key="q_pick",
                                          format_func=lambda r: f"{r['symbol']}  {r['description']}")
                    st.button(T("Open {s}", s=pick['symbol']), on_click=go_stock, args=(pick["symbol"],), type="primary",
                              width="stretch")
                else:
                    st.caption(T("No US-listed stock matches that search."))


def tape_items(watchlist: list[str]) -> list[dict]:
    items = []
    for label, sym in INDEX_ETFS + [("Mexico", "EWW"), ("Argentina", "ARGT")]:
        q = safe(data.quote, sym)
        if q:
            items.append({"label": T(label), "sym": sym, "price": f"{q['price']:,.2f}", "pct": q["pct"], "href": link({"p": "stock", "t": sym})})
    for sym in watchlist:
        q = safe(data.quote, sym)
        if q:
            items.append({"label": sym, "sym": sym, "price": f"{q['price']:,.2f}", "pct": q["pct"], "href": link({"p": "stock", "t": sym})})
    b = safe(data.bitcoin)
    if b:
        items.append({"label": "Bitcoin", "sym": "", "price": f"{b['price']:,.0f}", "pct": b["pct"], "href": link({"p": "markets"})})
    fx = safe(data.fx_quote, "USD/MXN")
    if fx:
        items.append({"label": "USD/MXN", "sym": "", "price": f"{fx['price']:,.4f}", "pct": fx["pct"], "href": link({"p": "markets"})})
    t10 = safe(data.fred_latest, "DGS10")
    if t10:
        items.append({"label": T("US 10Y"), "sym": "", "price": f"{t10['value']:.2f}%", "pct": None,
                      "bps": round((t10["value"] - t10["prev"]) * 100), "href": link({"p": "markets"})})
    return items


def ticker_tape(watchlist: list[str]) -> None:
    items = tape_items(watchlist)
    if not items:
        return

    def one(i: dict) -> str:
        if i.get("pct") is not None:
            cls = "u" if i["pct"] > 0 else "d" if i["pct"] < 0 else "f"
            ch = sgn(i["pct"])
        else:
            cls, ch = "f", f"{sgn(i.get('bps', 0), 0, '')} bps"
        return f'<a href="{i["href"]}" target="_self"><b>{esc(i["label"])}</b><span>{esc(i["price"])}</span><span class="{cls}">{esc(ch)}</span></a>'

    row = "".join(one(i) for i in items)
    st.html(f'<div class="mb-tape" aria-label="Ticker tape"><div class="track">{row}{row}</div></div>')


def status_line() -> str:
    s = safe(data.market_status)
    if not s:
        return T("Market status unavailable")
    if s.get("isOpen"):
        return '<span class="mb-dot open"></span>' + T("US market open")
    session = {"pre-market": T("pre-market"), "post-market": T("after hours")}.get(s.get("session") or "")
    holiday = f" ({esc(s['holiday'])})" if s.get("holiday") else ""
    state = T("in {s}", s=session) if session else T("closed") + holiday
    return '<span class="mb-dot closed"></span>' + T("US market {state}, prices are the latest close", state=state)
