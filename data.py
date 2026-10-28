"""Data access layer.

Every external source the app uses lives in this file, each wrapped in a
Streamlit cache so the free API limits are respected:

- Finnhub ......... stock/ETF quotes, company news, market news, earnings dates, symbol search
- Twelve Data ..... daily price history (charts, volatility, beta) and USD/MXN
- FRED ............ 10-year US Treasury yield (risk-free rate)
- SEC EDGAR ....... reported financial statements (XBRL company facts) for the DCF
- CoinGecko ....... Bitcoin price
- RSS feeds ....... CNBC, MarketWatch, WSJ Markets and the Federal Reserve
"""
from __future__ import annotations

import datetime as dt
import html
import re
from difflib import SequenceMatcher
from zoneinfo import ZoneInfo

import feedparser
import pandas as pd
import requests
import streamlit as st

TIMEOUT = 15
ET = ZoneInfo("America/New_York")


class DataError(Exception):
    """A source answered, but without usable data (or a key is missing)."""


def secret(name: str, default=None):
    try:
        return st.secrets[name]
    except Exception:
        return default


def _get_json(url: str, params: dict | None = None, headers: dict | None = None):
    resp = requests.get(url, params=params, headers=headers, timeout=TIMEOUT)
    if resp.status_code == 429:
        raise DataError("Rate limit reached for this data source. Try again in a minute.")
    resp.raise_for_status()
    return resp.json()


def _get_bytes(url: str, headers: dict | None = None) -> bytes:
    resp = requests.get(url, headers=headers, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.content


# --------------------------------------------------------------------------- Finnhub
FINNHUB = "https://finnhub.io/api/v1"


def _finnhub(path: str, **params):
    key = secret("FINNHUB_API_KEY")
    if not key:
        raise DataError("FINNHUB_API_KEY is missing from the app secrets.")
    params["token"] = key
    return _get_json(f"{FINNHUB}{path}", params=params)


@st.cache_data(ttl=60, show_spinner=False)
def quote(symbol: str) -> dict:
    q = _finnhub("/quote", symbol=symbol)
    if not q or not q.get("t") or not q.get("c"):
        raise DataError(f"No quote available for {symbol}.")
    return {
        "price": float(q["c"]),
        "change": q.get("d"),
        "pct": q.get("dp"),  # already in percent, e.g. 1.25 = +1.25%
        "prev_close": q.get("pc"),
        "high": q.get("h") or None,
        "low": q.get("l") or None,
        "time": dt.datetime.fromtimestamp(q["t"], tz=ET),
    }


@st.cache_data(ttl=300, show_spinner=False)
def market_status() -> dict:
    return _finnhub("/stock/market-status", exchange="US")


@st.cache_data(ttl=86400, show_spinner=False)
def profile(symbol: str) -> dict:
    p = _finnhub("/stock/profile2", symbol=symbol) or {}
    return {
        "name": p.get("name") or symbol,
        "industry": p.get("finnhubIndustry") or "",
        "logo": p.get("logo") or "",
        "web": p.get("weburl") or "",
    }


US_SYMBOL = re.compile(r"^[A-Z]{1,5}(\.[A-Z])?$")


@st.cache_data(ttl=86400, show_spinner=False)
def search_symbols(query: str) -> list[dict]:
    res = _finnhub("/search", q=query).get("result", [])
    out, seen = [], set()
    for r in res:
        sym = (r.get("symbol") or "").upper()
        if r.get("type") in ("Common Stock", "ADR") and US_SYMBOL.match(sym) and sym not in seen:
            seen.add(sym)
            out.append({"symbol": sym, "description": (r.get("description") or "").title()})
    return out[:10]


def _news_item(source: str, title: str, summary: str, url: str, when: dt.datetime | None) -> dict:
    return {"source": source, "title": title, "summary": summary, "url": url, "time": when}


@st.cache_data(ttl=3600, show_spinner=False)
def company_news(symbol: str, days: int = 7) -> list[dict]:
    today = dt.date.today()
    raw = _finnhub(
        "/company-news",
        symbol=symbol,
        **{"from": (today - dt.timedelta(days=days)).isoformat(), "to": today.isoformat()},
    ) or []
    items = [
        _news_item(
            n.get("source") or "Finnhub",
            _clean(n.get("headline")),
            _clean(n.get("summary"))[:400],
            n.get("url"),
            dt.datetime.fromtimestamp(n["datetime"], tz=ET) if n.get("datetime") else None,
        )
        for n in raw
        if n.get("headline") and n.get("url")
    ]
    return dedupe(items)[:15]


@st.cache_data(ttl=1800, show_spinner=False)
def market_news() -> list[dict]:
    raw = _finnhub("/news", category="general") or []
    return [
        _news_item(
            n.get("source") or "Finnhub",
            _clean(n.get("headline")),
            _clean(n.get("summary"))[:400],
            n.get("url"),
            dt.datetime.fromtimestamp(n["datetime"], tz=ET) if n.get("datetime") else None,
        )
        for n in raw
        if n.get("headline") and n.get("url")
    ]


@st.cache_data(ttl=43200, show_spinner=False)
def next_earnings(symbol: str) -> dict | None:
    today = dt.date.today()
    data = _finnhub(
        "/calendar/earnings",
        symbol=symbol,
        **{"from": today.isoformat(), "to": (today + dt.timedelta(days=120)).isoformat()},
    ) or {}
    cal = [c for c in data.get("earningsCalendar", []) if c.get("date")]
    if not cal:
        return None
    nxt = min(cal, key=lambda c: c["date"])
    timing = {"bmo": "before market open", "amc": "after market close"}.get(nxt.get("hour") or "", "")
    return {"date": nxt["date"], "eps_estimate": nxt.get("epsEstimate"), "timing": timing}


# --------------------------------------------------------------------------- Twelve Data
TWELVE = "https://api.twelvedata.com"


def _twelve(path: str, **params):
    key = secret("TWELVE_DATA_API_KEY")
    if not key:
        raise DataError("TWELVE_DATA_API_KEY is missing from the app secrets.")
    params["apikey"] = key
    data = _get_json(f"{TWELVE}{path}", params=params)
    if isinstance(data, dict) and data.get("status") == "error":
        if data.get("code") == 429:
            raise DataError("Twelve Data free limit reached (8 requests per minute). Wait a minute and refresh.")
        raise DataError(data.get("message") or "Twelve Data error.")
    return data


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def history(symbol: str, outputsize: int = 520) -> pd.DataFrame:
    """Daily OHLCV, oldest first. 520 trading days is a bit over two years."""
    data = _twelve("/time_series", symbol=symbol, interval="1day", outputsize=outputsize)
    values = data.get("values") or []
    if not values:
        raise DataError(f"No price history for {symbol}.")
    df = pd.DataFrame(values)
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.set_index("datetime").sort_index()
    for col in ("open", "high", "low", "close", "volume"):
        if col in df:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.dropna(subset=["close"])


@st.cache_data(ttl=900, show_spinner=False)
def fx_quote(pair: str = "USD/MXN") -> dict:
    d = _twelve("/quote", symbol=pair)
    return {
        "price": float(d["close"]),
        "pct": float(d.get("percent_change") or 0),
        "time": d.get("datetime"),
    }


# --------------------------------------------------------------------------- CoinGecko
@st.cache_data(ttl=600, show_spinner=False)
def bitcoin() -> dict:
    headers = {}
    if secret("COINGECKO_API_KEY"):
        headers["x-cg-demo-api-key"] = secret("COINGECKO_API_KEY")
    d = _get_json(
        "https://api.coingecko.com/api/v3/simple/price",
        params={
            "ids": "bitcoin",
            "vs_currencies": "usd",
            "include_24hr_change": "true",
            "include_last_updated_at": "true",
        },
        headers=headers,
    )
    b = d["bitcoin"]
    return {
        "price": float(b["usd"]),
        "pct": b.get("usd_24h_change"),
        "time": dt.datetime.fromtimestamp(b["last_updated_at"], tz=ET) if b.get("last_updated_at") else None,
    }


# --------------------------------------------------------------------------- Argentina (DolarApi)
@st.cache_data(ttl=900, show_spinner=False)
def dolares_ar() -> dict:
    """Argentine dollar rates (official, MEP, blue...) from the free public DolarApi."""
    rows = _get_json("https://dolarapi.com/v1/dolares") or []
    out = {}
    for r in rows:
        if r.get("casa") and r.get("venta"):
            ts = r.get("fechaActualizacion")
            try:
                when = dt.datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(ET) if ts else None
            except ValueError:
                when = None
            out[r["casa"]] = {"name": r.get("nombre") or r["casa"], "buy": r.get("compra"),
                              "sell": float(r["venta"]), "time": when}
    if not out:
        raise DataError("No Argentine dollar rates available.")
    return out


# --------------------------------------------------------------------------- FRED
@st.cache_data(ttl=6 * 3600, show_spinner=False)
def fred_latest(series_id: str = "DGS10") -> dict:
    key = secret("FRED_API_KEY")
    if not key:
        raise DataError("FRED_API_KEY is missing from the app secrets.")
    d = _get_json(
        "https://api.stlouisfed.org/fred/series/observations",
        params={"series_id": series_id, "api_key": key, "file_type": "json", "sort_order": "desc", "limit": 15},
    )
    obs = [o for o in d.get("observations", []) if o.get("value") not in (".", "", None)]
    if len(obs) < 2:
        raise DataError(f"No recent data for {series_id}.")
    return {"value": float(obs[0]["value"]), "prev": float(obs[1]["value"]), "date": obs[0]["date"]}


def risk_free_rate() -> tuple[float, str]:
    """10-year Treasury yield as a decimal, plus a label saying where it came from."""
    try:
        t = fred_latest("DGS10")
        return t["value"] / 100, f"10Y Treasury {t['value']:.2f}% (FRED, {t['date']})"
    except Exception:
        return 0.042, "10Y Treasury unavailable, using 4.20% placeholder"


# --------------------------------------------------------------------------- RSS
FEEDS = {
    "CNBC": "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    "CNBC Markets": "https://www.cnbc.com/id/20409666/device/rss/rss.html",
    "MarketWatch": "https://feeds.marketwatch.com/marketwatch/topstories",
    "WSJ Markets": "https://feeds.content.dowjones.io/public/rss/RSSMarketsMain",
    "Federal Reserve": "https://www.federalreserve.gov/feeds/press_all.xml",
}
_TAG = re.compile(r"<[^>]+>")


def _clean(text: str | None) -> str:
    return re.sub(r"\s+", " ", html.unescape(_TAG.sub(" ", text or ""))).strip()


@st.cache_data(ttl=1800, show_spinner=False)
def rss_headlines() -> tuple[list[dict], list[str]]:
    items, failed = [], []
    for source, url in FEEDS.items():
        try:
            parsed = feedparser.parse(_get_bytes(url, headers={"User-Agent": "Mozilla/5.0 (personal market dashboard)"}))
            if not parsed.entries:
                failed.append(source)
                continue
            for e in parsed.entries[:30]:
                t = e.get("published_parsed") or e.get("updated_parsed")
                when = dt.datetime(*t[:6], tzinfo=dt.timezone.utc).astimezone(ET) if t else None
                title = _clean(e.get("title"))
                if title and e.get("link"):
                    items.append(_news_item(source, title, _clean(e.get("summary"))[:400], e.get("link"), when))
        except Exception:
            failed.append(source)
    return items, failed


def _norm(title: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", title.lower())


def dedupe(items: list[dict], threshold: float = 0.8) -> list[dict]:
    """Newest first, dropping headlines that are near-copies of one already kept."""
    floor = dt.datetime.min.replace(tzinfo=ET)
    kept, kept_norm = [], []
    for it in sorted(items, key=lambda x: x["time"] or floor, reverse=True):
        n = _norm(it["title"])
        if not n or any(SequenceMatcher(None, n, k).ratio() >= threshold for k in kept_norm):
            continue
        kept.append(it)
        kept_norm.append(n)
    return kept


def todays_headlines() -> tuple[list[dict], list[str]]:
    """Headlines from the last trading day (longer window on Mondays and weekends)."""
    now = dt.datetime.now(ET)
    hours = 72 if now.weekday() in (0, 5, 6) else 30
    rss, failed = rss_headlines()
    failed = list(failed)
    try:
        fh = market_news()
    except Exception:
        fh = []
        failed.append("Finnhub")
    cutoff = now - dt.timedelta(hours=hours)
    recent = [i for i in rss + fh if i["time"] and i["time"] >= cutoff]
    return dedupe(recent), failed


# --------------------------------------------------------------------------- SEC EDGAR
def _sec_headers() -> dict:
    # The SEC asks automated users to identify themselves with a name and email.
    return {"User-Agent": secret("SEC_USER_AGENT", "Market Brief personal app admin@example.com")}


@st.cache_data(ttl=7 * 86400, show_spinner=False)
def sec_cik_map() -> dict:
    d = _get_json("https://www.sec.gov/files/company_tickers.json", headers=_sec_headers())
    return {v["ticker"].upper(): int(v["cik_str"]) for v in d.values()}


@st.cache_data(ttl=86400, show_spinner=False, max_entries=20)
def sec_facts(ticker: str) -> dict:
    cik = sec_cik_map().get(ticker.upper().replace(".", "-"))
    if not cik:
        raise DataError(
            f"{ticker} is not in the SEC database. Valuation works for US-listed companies that file 10-Ks."
        )
    return _get_json(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json", headers=_sec_headers())
