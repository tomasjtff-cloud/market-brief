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
import threading
import time
from collections import deque
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


# --------------------------------------------------------------------------- rate limiting
@st.cache_resource
def _limiter(name: str) -> dict:
    return {"lock": threading.Lock(), "calls": deque()}


def _throttle(name: str, per_minute: int, max_wait: float) -> None:
    """Shared sliding-window limiter so the whole app stays inside each free plan's per-minute cap."""
    lim = _limiter(name)
    deadline = time.time() + max_wait
    while True:
        with lim["lock"]:
            now = time.time()
            while lim["calls"] and now - lim["calls"][0] > 60:
                lim["calls"].popleft()
            if len(lim["calls"]) < per_minute:
                lim["calls"].append(now)
                return
            wait = 60.5 - (now - lim["calls"][0])
        if time.time() + wait > deadline:
            raise DataError(f"{name} is busy (free plan limit per minute). Refresh in a minute.")
        time.sleep(min(wait, 2.0))


# --------------------------------------------------------------------------- Finnhub
FINNHUB = "https://finnhub.io/api/v1"


def _finnhub(path: str, **params):
    key = secret("FINNHUB_API_KEY")
    if not key:
        raise DataError("FINNHUB_API_KEY is missing from the app secrets.")
    _throttle("Finnhub", 55, max_wait=40)
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
        "country": p.get("country") or "",
        "exchange": p.get("exchange") or "",
        "ipo": p.get("ipo") or "",
        "market_cap": (p.get("marketCapitalization") or 0) * 1e6 or None,
        "shares": (p.get("shareOutstanding") or 0) * 1e6 or None,
    }


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def basic_metrics(symbol: str) -> dict:
    """Finnhub 'basic financials': 52-week range, P/E, EPS, dividend yield, average volume..."""
    return (_finnhub("/stock/metric", symbol=symbol, metric="all") or {}).get("metric") or {}


@st.cache_data(ttl=12 * 3600, show_spinner=False)
def recommendations(symbol: str) -> list[dict]:
    """Monthly counts of sell-side analyst ratings (strong buy ... strong sell), newest first."""
    rows = _finnhub("/stock/recommendation", symbol=symbol) or []
    return sorted(rows, key=lambda r: r.get("period", ""), reverse=True)[:6]


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
    _throttle("Twelve Data", 8, max_wait=25)
    params["apikey"] = key
    data = _get_json(f"{TWELVE}{path}", params=params)
    if isinstance(data, dict) and data.get("status") == "error":
        if data.get("code") == 429:
            raise DataError("Twelve Data free limit reached (8 requests per minute). Wait a minute and refresh.")
        raise DataError(data.get("message") or "Twelve Data error.")
    return data


def _frame(values: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(values)
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.set_index("datetime").sort_index()
    for col in ("open", "high", "low", "close", "volume"):
        if col in df:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.dropna(subset=["close"])


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def history(symbol: str, outputsize: int = 1300) -> pd.DataFrame:
    """Daily OHLCV, oldest first. 1,300 trading days is about five years."""
    data = _twelve("/time_series", symbol=symbol, interval="1day", outputsize=outputsize)
    values = data.get("values") or []
    if not values:
        raise DataError(f"No price history for {symbol}.")
    return _frame(values)


@st.cache_data(ttl=300, show_spinner=False)
def intraday(symbol: str, interval: str = "5min", outputsize: int = 80) -> pd.DataFrame:
    """Intraday bars (exchange time) for the 1D and 5D charts."""
    data = _twelve("/time_series", symbol=symbol, interval=interval, outputsize=outputsize)
    values = data.get("values") or []
    if not values:
        raise DataError(f"No intraday data for {symbol}.")
    return _frame(values)


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
def fred_series(series_id: str, limit: int = 40) -> list[tuple[str, float]]:
    """Most recent observations, newest first, skipping missing days."""
    key = secret("FRED_API_KEY")
    if not key:
        raise DataError("FRED_API_KEY is missing from the app secrets.")
    d = _get_json(
        "https://api.stlouisfed.org/fred/series/observations",
        params={"series_id": series_id, "api_key": key, "file_type": "json", "sort_order": "desc", "limit": limit},
    )
    obs = [(o["date"], float(o["value"])) for o in d.get("observations", []) if o.get("value") not in (".", "", None)]
    if len(obs) < 2:
        raise DataError(f"No recent data for {series_id}.")
    return obs


def fred_latest(series_id: str = "DGS10") -> dict:
    obs = fred_series(series_id)
    return {"value": obs[0][1], "prev": obs[1][1], "date": obs[0][0]}


CURVE = [("1M", "DGS1MO", 1 / 12), ("3M", "DGS3MO", 0.25), ("6M", "DGS6MO", 0.5), ("1Y", "DGS1", 1),
         ("2Y", "DGS2", 2), ("3Y", "DGS3", 3), ("5Y", "DGS5", 5), ("7Y", "DGS7", 7), ("10Y", "DGS10", 10),
         ("20Y", "DGS20", 20), ("30Y", "DGS30", 30)]


def yield_curve() -> pd.DataFrame:
    """US Treasury curve today and about one month earlier."""
    rows = []
    for label, sid, years in CURVE:
        try:
            obs = fred_series(sid)
        except Exception:
            continue
        latest_date = dt.date.fromisoformat(obs[0][0])
        month_ago = next((v for d, v in obs if dt.date.fromisoformat(d) <= latest_date - dt.timedelta(days=28)), None)
        rows.append({"tenor": label, "years": years, "now": obs[0][1], "month_ago": month_ago, "date": obs[0][0]})
    if not rows:
        raise DataError("Treasury yields unavailable.")
    return pd.DataFrame(rows)


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


def _similar(a: str, b: str, threshold: float) -> bool:
    sm = SequenceMatcher(None, a, b)
    return sm.real_quick_ratio() >= threshold and sm.quick_ratio() >= threshold and sm.ratio() >= threshold


def dedupe(items: list[dict], threshold: float = 0.8) -> list[dict]:
    """Newest first, dropping headlines that are near-copies of one already kept."""
    floor = dt.datetime.min.replace(tzinfo=ET)
    kept, kept_norm = [], []
    for it in sorted(items, key=lambda x: x["time"] or floor, reverse=True):
        n = _norm(it["title"])
        if not n or any(_similar(n, k, threshold) for k in kept_norm):
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


# --------------------------------------------------------------------------- news desk
def _fetch_feed(region: str, source: str, spec) -> tuple[list[dict], str | None]:
    import news

    url, filters = (spec if isinstance(spec, tuple) else (spec, None))
    try:
        parsed = feedparser.parse(_get_bytes(url, headers={"User-Agent": "Mozilla/5.0 (personal market dashboard)"}))
        out = []
        for e in parsed.entries[:40]:
            t = e.get("published_parsed") or e.get("updated_parsed")
            when = dt.datetime(*t[:6], tzinfo=dt.timezone.utc).astimezone(ET) if t else None
            title, link = _clean(e.get("title")), e.get("link")
            if not title or not link or not news.keep(link, filters):
                continue
            item = _news_item(source, title, _clean(e.get("summary"))[:400], link, when)
            item["region"] = region if region in news.REGIONS else None
            out.append(item)
        return out, (None if out else source)
    except Exception:
        return [], source


@st.cache_data(ttl=1800, show_spinner=False)
def finnhub_news(category: str = "general") -> list[dict]:
    raw = _finnhub("/news", category=category) or []
    return [
        _news_item(n.get("source") or "Finnhub", _clean(n.get("headline")), _clean(n.get("summary"))[:400], n.get("url"),
                   dt.datetime.fromtimestamp(n["datetime"], tz=ET) if n.get("datetime") else None)
        for n in raw if n.get("headline") and n.get("url")
    ]


@st.cache_data(ttl=1800, show_spinner=False)
def news_desk() -> tuple[list[dict], list[str]]:
    """Every news-desk headline, tagged with a region (from its feed) and sectors (from keywords), newest first."""
    import news
    from concurrent.futures import ThreadPoolExecutor

    jobs = [(region, source, spec) for region, feeds in news.FEEDS.items() for source, spec in feeds.items()]
    items, failed = [], []
    with ThreadPoolExecutor(max_workers=8) as pool:
        for got, bad in pool.map(lambda j: _fetch_feed(*j), jobs):
            items += got
            if bad:
                failed.append(bad)
    for category, region in (("general", "USA"), ("forex", "World"), ("merger", None), ("crypto", None)):
        try:
            for it in finnhub_news(category):
                it = dict(it, region=region)
                items.append(it)
        except Exception:
            failed.append(f"Finnhub {category}")
    for it in items:
        it["sectors"] = news.classify(it["title"], it.get("summary", ""))
    return dedupe(items), failed


# --------------------------------------------------------------------------- FX and rates for the news desk
ECB_PAIRS = [("USD/MXN", "MXN", False), ("EUR/USD", "EUR", True), ("USD/JPY", "JPY", False), ("GBP/USD", "GBP", True),
             ("USD/BRL", "BRL", False), ("USD/CNY", "CNY", False), ("USD/CAD", "CAD", False)]


@st.cache_data(ttl=3 * 3600, show_spinner=False)
def fx_reference() -> dict:
    """ECB reference rates via the free Frankfurter API: latest, previous day and about a week earlier."""
    start = (dt.date.today() - dt.timedelta(days=14)).isoformat()
    d = _get_json(f"https://api.frankfurter.dev/v1/{start}..",
                  params={"base": "USD", "symbols": ",".join(c for _, c, _ in ECB_PAIRS)})
    days = sorted(d.get("rates", {}))
    if len(days) < 2:
        raise DataError("No ECB reference rates available.")
    out = {}
    for pair, code, invert in ECB_PAIRS:
        series = [d["rates"][x].get(code) for x in days]
        series = [(1 / v if invert else v) if v else None for v in series]
        if series[-1] is None:
            continue
        out[pair] = {"rate": series[-1], "prev": series[-2], "week": series[-6] if len(series) >= 6 else series[0],
                     "date": days[-1]}
    return out


@st.cache_data(ttl=3600, show_spinner=False)
def riesgo_pais() -> dict:
    """Argentina's country-risk spread (EMBI, basis points) from the free ArgentinaDatos API."""
    d = _get_json("https://api.argentinadatos.com/v1/finanzas/indices/riesgo-pais/ultimo")
    return {"value": float(d["valor"]), "date": d.get("fecha")}


# --------------------------------------------------------------------------- SEC EDGAR
def _sec_headers() -> dict:
    # The SEC asks automated users to identify themselves with a name and email.
    return {"User-Agent": secret("SEC_USER_AGENT", "Market Brief personal app admin@example.com")}


@st.cache_data(ttl=7 * 86400, show_spinner=False)
def sec_cik_map() -> dict:
    d = _get_json("https://www.sec.gov/files/company_tickers.json", headers=_sec_headers())
    return {v["ticker"].upper(): int(v["cik_str"]) for v in d.values()}


def sec_facts(ticker: str) -> dict:
    cik = sec_cik_map().get(ticker.upper().replace(".", "-"))
    if not cik:
        raise DataError(
            f"{ticker} is not in the SEC database. Valuation works for US-listed companies that file 10-Ks."
        )
    return _get_json(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json", headers=_sec_headers())


@st.cache_data(ttl=86400, show_spinner=False, max_entries=60)
def company_fundamentals(ticker: str) -> dict:
    """Parsed SEC financials (small), cached instead of the multi-megabyte raw filing data."""
    import fundamentals

    return fundamentals.build(sec_facts(ticker))


# --------------------------------------------------------------------------- universes
SECTOR_ETFS = [("Technology", "XLK"), ("Financials", "XLF"), ("Health care", "XLV"), ("Consumer discretionary", "XLY"),
               ("Communication services", "XLC"), ("Industrials", "XLI"), ("Consumer staples", "XLP"),
               ("Energy", "XLE"), ("Utilities", "XLU"), ("Real estate", "XLRE"), ("Materials", "XLB")]

MEGA_CAPS = [
    ("AAPL", "Technology"), ("MSFT", "Technology"), ("NVDA", "Technology"), ("AVGO", "Technology"),
    ("ORCL", "Technology"), ("AMD", "Technology"), ("GOOGL", "Communication services"),
    ("META", "Communication services"), ("NFLX", "Communication services"), ("AMZN", "Consumer discretionary"),
    ("TSLA", "Consumer discretionary"), ("HD", "Consumer discretionary"), ("JPM", "Financials"),
    ("V", "Financials"), ("MA", "Financials"), ("BAC", "Financials"), ("LLY", "Health care"),
    ("UNH", "Health care"), ("JNJ", "Health care"), ("ABBV", "Health care"), ("WMT", "Consumer staples"),
    ("COST", "Consumer staples"), ("PG", "Consumer staples"), ("XOM", "Energy"), ("CVX", "Energy"),
]
