"""News desk: which feeds cover which region, and a keyword classifier that tags headlines by sector.

Pure Python (no Streamlit) so it can be unit-tested.
"""
from __future__ import annotations

import datetime as dt
import re

REGIONS = ["USA", "Mexico", "Argentina", "World"]

# Official publisher RSS feeds. A tuple adds URL path filters for general-interest feeds.
FEEDS: dict[str, dict[str, str | tuple[str, tuple[str, ...]]]] = {
    "USA": {
        "CNBC": "https://www.cnbc.com/id/100003114/device/rss/rss.html",
        "CNBC Markets": "https://www.cnbc.com/id/20409666/device/rss/rss.html",
        "MarketWatch": "https://feeds.marketwatch.com/marketwatch/topstories",
        "WSJ Markets": "https://feeds.content.dowjones.io/public/rss/RSSMarketsMain",
        "Federal Reserve": "https://www.federalreserve.gov/feeds/press_all.xml",
    },
    "Mexico": {
        "El Financiero": ("https://www.elfinanciero.com.mx/arc/outboundfeeds/rss/?outputType=xml",
                          ("/economia/", "/mercados/", "/empresas/", "/finanzas-personales/", "/tech/")),
        "Expansión": "https://expansion.mx/rss/economia",
        "El Economista": "https://www.eleconomista.com.mx/rss/economia",
    },
    "Argentina": {
        "Ámbito Economía": "https://www.ambito.com/rss/pages/economia.xml",
        "Ámbito Finanzas": "https://www.ambito.com/rss/pages/finanzas.xml",
        "Infobae Economía": "https://www.infobae.com/arc/outboundfeeds/rss/category/economia/",
    },
    "World": {
        "BBC Business": "https://feeds.bbci.co.uk/news/business/rss.xml",
        "CNBC World": "https://www.cnbc.com/id/100727362/device/rss/rss.html",
        "DW Business": "https://rss.dw.com/rdf/rss-en-bus",
    },
    # Specialist feeds: no region of their own, they feed the sector view.
    "Sector": {
        "Mining.com": "https://www.mining.com/feed/",
        "TechCrunch AI": "https://techcrunch.com/category/artificial-intelligence/feed/",
        "OilPrice": "https://oilprice.com/rss/main",
        "CoinDesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    },
}

# Sector keywords in English and Spanish. Short acronyms are matched case-sensitively.
SECTORS: dict[str, dict] = {
    "Tech & AI": {
        "words": ["artificial intelligence", "inteligencia artificial", "chip", "chips", "semiconductor", "semiconductores",
                  "nvidia", "openai", "anthropic", "microsoft", "apple", "alphabet", "google", "meta platforms", "amazon web services",
                  "software", "cloud", "nube", "data center", "data centers", "centro de datos", "tsmc", "broadcom", "amd", "intel",
                  "chatgpt", "gemini", "tecnológica", "tecnológicas", "big tech", "cybersecurity", "ciberseguridad"],
        "acronyms": ["AI", "IA", "GPU", "GPUs"],
    },
    "Energy": {
        "words": ["oil", "crude", "brent", "wti", "opec", "natural gas", "lng", "gasoline", "refinery", "refiner", "exxon",
                  "chevron", "shell", "bp", "petróleo", "petroleo", "crudo", "gas natural", "pemex", "ypf", "vaca muerta",
                  "gasolina", "energía", "energy", "power grid", "electricity", "electricidad", "cfe", "solar", "renewable",
                  "nuclear", "uranium"],
        "acronyms": ["OPEC+"],
    },
    "Mining & metals": {
        "words": ["gold", "silver", "copper", "lithium", "nickel", "iron ore", "zinc", "aluminum", "aluminium", "platinum",
                  "mining", "miner", "miners", "mines", "rare earth", "rare earths", "freeport", "bhp", "rio tinto", "glencore",
                  "newmont", "barrick", "codelco", "oro", "plata", "cobre", "litio", "minería", "mineria", "minera", "mineras",
                  "metales", "acero", "steel"],
        "acronyms": [],
    },
    "Banks & finance": {
        "words": ["bank", "banks", "banking", "jpmorgan", "goldman", "morgan stanley", "citigroup", "wells fargo",
                  "bank of america", "lender", "lenders", "credit", "loan", "loans", "private equity", "private credit",
                  "hedge fund", "asset manager", "blackrock", "insurer", "bond", "bonds", "treasury", "treasuries", "yield",
                  "yields", "banco", "bancos", "bancario", "crédito", "credito", "bonos", "deuda", "tasa", "tasas", "morosidad",
                  "fintech", "afore", "afores"],
        "acronyms": ["IPO", "M&A", "SEC"],
    },
    "Health care": {
        "words": ["pharma", "pharmaceutical", "drug", "drugs", "drugmaker", "biotech", "vaccine", "fda", "pfizer",
                  "eli lilly", "lilly", "novo nordisk", "merck", "johnson & johnson", "unitedhealth", "health insurer",
                  "obesity", "glp-1", "medicare", "hospital", "farmacéutica", "farmaceutica", "salud", "medicamentos"],
        "acronyms": [],
    },
    "Consumer & retail": {
        "words": ["retail", "retailer", "retailers", "consumer", "consumers", "shoppers", "walmart", "costco",
                  "home depot", "nike", "starbucks", "mcdonald", "restaurant", "restaurants", "spending", "holiday sales",
                  "e-commerce", "ecommerce", "consumo", "ventas minoristas", "minoristas", "supermercado", "supermercados",
                  "consumidores", "walmex", "femsa", "mercadolibre", "mercado libre"],
        "acronyms": [],
    },
    "Industrials & autos": {
        "words": ["tesla", "automaker", "automakers", "auto", "autos", "car sales", "electric vehicle", "electric vehicles",
                  "boeing", "airbus", "airline", "airlines", "general motors", "ford", "stellantis", "toyota", "factory",
                  "manufacturing", "tariff", "tariffs", "aranceles", "arancel", "automotriz", "automotrices", "nearshoring",
                  "manufactura", "industria", "industrial", "logistics", "shipping", "railroad", "defense", "construcción"],
        "acronyms": ["EV", "EVs", "PMI", "T-MEC", "USMCA"],
    },
    "Real estate": {
        "words": ["real estate", "housing", "home sales", "mortgage", "mortgages", "homebuilder", "homebuilders",
                  "commercial property", "office space", "reit", "reits", "vivienda", "inmobiliario", "inmobiliaria",
                  "hipotecario", "hipotecas", "fibra", "fibras", "alquiler", "alquileres"],
        "acronyms": [],
    },
    "Crypto": {
        "words": ["bitcoin", "crypto", "cryptocurrency", "ether", "ethereum", "stablecoin", "stablecoins", "coinbase",
                  "binance", "solana", "blockchain", "cripto", "criptomonedas"],
        "acronyms": ["BTC", "ETH"],
    },
}


def _compile(spec: dict) -> tuple[re.Pattern, re.Pattern | None]:
    words = sorted(spec["words"], key=len, reverse=True)
    w = re.compile(r"(?<![\w-])(?:" + "|".join(re.escape(x) for x in words) + r")(?![\w-])", re.IGNORECASE)
    a = (re.compile(r"(?<![\w-])(?:" + "|".join(re.escape(x) for x in spec["acronyms"]) + r")(?![\w-])")
         if spec["acronyms"] else None)
    return w, a


_PATTERNS = {name: _compile(spec) for name, spec in SECTORS.items()}


def classify(title: str, summary: str = "") -> list[str]:
    """Sectors a headline belongs to. The title counts double: a match only in the summary needs two hits."""
    out = []
    for name, (w, a) in _PATTERNS.items():
        t_hits = len(w.findall(title)) + (len(a.findall(title)) if a else 0)
        s_hits = len(w.findall(summary)) + (len(a.findall(summary)) if a else 0)
        if t_hits or s_hits >= 2:
            out.append(name)
    return out


def keep(url: str, filters: tuple[str, ...] | None) -> bool:
    return not filters or any(f in (url or "") for f in filters)


def window_hours(now: dt.datetime) -> int:
    """Look back further over weekends and on Mondays."""
    return 72 if now.weekday() in (0, 5, 6) else 36


def buckets(items: list[dict], now: dt.datetime, per_bucket: int = 14) -> dict[str, list[dict]]:
    """Group recent items (newest first, already de-duplicated) by region and by sector."""
    cutoff = now - dt.timedelta(hours=window_hours(now))
    recent = [i for i in items if i.get("time") and i["time"] >= cutoff]
    out: dict[str, list[dict]] = {r: [] for r in REGIONS}
    out.update({s: [] for s in SECTORS})
    for it in recent:
        if it.get("region") in REGIONS and len(out[it["region"]]) < per_bucket:
            out[it["region"]].append(it)
        for s in it.get("sectors", []):
            if len(out[s]) < per_bucket:
                out[s].append(it)
    return out
