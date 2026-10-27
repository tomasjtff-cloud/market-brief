"""AI writing layer (Google Gemini, free tier).

The model never fetches anything itself: it only rewrites the headlines and
numbers it is handed, and the prompts forbid adding facts that aren't there.
Results are cached so the free quota is barely touched.
"""
from __future__ import annotations

import datetime as dt
import json
import re

import requests
import streamlit as st

from data import ET, secret

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


class AIError(Exception):
    pass


@st.cache_resource
def _usage() -> dict:
    return {"date": None, "count": 0}


def _spend_budget() -> None:
    """Simple daily cap so a public app can't burn through the free quota."""
    u = _usage()
    today = dt.date.today().isoformat()
    if u["date"] != today:
        u["date"], u["count"] = today, 0
    limit = int(secret("AI_DAILY_LIMIT", 100))
    if u["count"] >= limit:
        raise AIError("Daily AI limit for this app reached. It resets tomorrow.")
    u["count"] += 1


def _call(prompt: str) -> dict:
    key = secret("GEMINI_API_KEY")
    if not key:
        raise AIError("GEMINI_API_KEY is missing from the app secrets.")
    _spend_budget()
    model = secret("GEMINI_MODEL", "gemini-2.5-flash")
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"},
    }
    resp = requests.post(
        GEMINI_URL.format(model=model),
        headers={"x-goog-api-key": key, "Content-Type": "application/json"},
        json=body,
        timeout=90,
    )
    if resp.status_code == 429:
        raise AIError("Gemini free-tier limit reached. Try again later.")
    if resp.status_code >= 400:
        raise AIError(f"Gemini returned an error ({resp.status_code}).")
    try:
        parts = resp.json()["candidates"][0]["content"]["parts"]
        text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
        text = re.sub(r"^```(?:json)?|```$", "", text.strip()).strip()
        return json.loads(text)
    except Exception as exc:
        raise AIError("The AI answer couldn't be read. Try again in a moment.") from exc


RULES = """STRICT RULES
- Use ONLY the facts in the data below. Do not add facts, numbers, quotes, dates or events that are not there.
- If something is unclear, say so briefly or leave it out.
- No buy/sell/hold recommendations and no price targets of your own.
- Plain, precise English for a finance graduate: explain any jargon in a few words.
- Never present old information as new; respect the timestamps given."""


# --------------------------------------------------------------------------- daily brief
BRIEF_PROMPT = """You are a buy-side market analyst writing today's short morning note.

{rules}
- Prefer market-moving news: central banks, rates, inflation, jobs, earnings of large companies, major geopolitics, big index moves.
- Merge headlines about the same event into one story.

Return JSON exactly in this shape:
{{"market_summary": "3-5 sentences: what markets are doing and the main reasons, based on the data",
  "stories": [{{"headline": "short headline in your own words",
               "what_happened": "1-2 sentences",
               "why_it_matters": "1-2 sentences on the market impact",
               "what_to_watch": "1 sentence",
               "source_ids": [1, 4]}}]}}
Give 5 to 8 stories, most important first. source_ids are the numbers of the HEADLINES used.

MARKET DATA (as of {now})
{snapshot}

HEADLINES
{headlines}
"""


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def daily_brief(slot: str, _snapshot: str, _headlines: list[dict]) -> dict:
    """Cached per 6-hour slot (the leading underscore keeps the inputs out of the cache key)."""
    used = _headlines[:60]
    lines = [
        f"[{i}] {h['source']} | {h['time']:%a %b %d %H:%M} ET | {h['title']}"
        + (f" — {h['summary'][:300]}" if h.get("summary") else "")
        for i, h in enumerate(used, 1)
    ]
    now = dt.datetime.now(ET)
    prompt = BRIEF_PROMPT.format(rules=RULES, now=f"{now:%Y-%m-%d %H:%M} ET", snapshot=_snapshot, headlines="\n".join(lines))
    out = _call(prompt)

    stories = []
    for s in out.get("stories", [])[:8]:
        ids = [i for i in s.get("source_ids", []) if isinstance(i, int) and 1 <= i <= len(used)]
        stories.append({
            "headline": s.get("headline", ""),
            "what_happened": s.get("what_happened", ""),
            "why_it_matters": s.get("why_it_matters", ""),
            "what_to_watch": s.get("what_to_watch", ""),
            "sources": [used[i - 1] for i in ids],
        })
    return {
        "market_summary": out.get("market_summary", ""),
        "stories": stories,
        "generated_at": now,
        "n_headlines": len(used),
    }


# --------------------------------------------------------------------------- stock take
STOCK_PROMPT = """You are an equity analyst at an asset manager writing a one-page view on {ticker} ({name}).

{rules}
- The valuation numbers come from a simple DCF with the stated assumptions: present them as model outputs that
  depend on those assumptions, not as facts.
- Scenarios must be qualitative and tied to the data (growth, margins, valuation, news). Do not invent probabilities.

Return JSON exactly in this shape:
{{"situation": "2-3 sentences",
  "recent_performance": "2-3 sentences using the returns and risk metrics",
  "fundamentals": "2-3 sentences using the reported financials and multiples",
  "valuation": "2-3 sentences on the DCF and reverse DCF",
  "news": "2-3 sentences on what recent news suggests",
  "bull_case": "1-2 sentences", "base_case": "1-2 sentences", "bear_case": "1-2 sentences",
  "risks": ["3-5 short items"],
  "catalysts": ["2-4 short items"],
  "conclusion": "2-3 sentences, balanced, no recommendation"}}

DATA (as of {now})
{data}

RECENT NEWS
{news}
"""


@st.cache_data(ttl=12 * 3600, show_spinner=False)
def stock_take(ticker: str, name: str, day: str, _data_text: str, _news: list[dict]) -> dict:
    news_lines = [
        f"- {n['time']:%b %d} | {n['source']} | {n['title']}" + (f" — {n['summary'][:250]}" if n.get("summary") else "")
        for n in _news[:12] if n.get("time")
    ] or ["- No company news in the last 7 days."]
    now = dt.datetime.now(ET)
    prompt = STOCK_PROMPT.format(
        ticker=ticker, name=name, rules=RULES, now=f"{now:%Y-%m-%d %H:%M} ET",
        data=_data_text, news="\n".join(news_lines),
    )
    out = _call(prompt)
    out["generated_at"] = now
    return out
