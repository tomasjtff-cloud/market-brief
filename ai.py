"""AI writing layer (Google Gemini, free tier).

The model never fetches anything itself: it only rewrites the headlines and
numbers it is handed, and the prompts forbid adding facts that aren't there.
Results are cached so the free quota is barely touched.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import time

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


MODEL_PATTERN = re.compile(r"^gemini-(\d+(?:\.\d+)?)-(flash-lite|flash|pro)(.*)$")
SKIP_VARIANTS = ("image", "tts", "audio", "live", "embedding", "vision", "thinking", "native")


def _model_score(name: str) -> float | None:
    """Prefer the newest stable Flash-Lite/Flash model: fast, and on the free tier. Pro usually isn't."""
    m = MODEL_PATTERN.match(name)
    if not m or any(v in m.group(3) for v in SKIP_VARIANTS):
        return None
    # Kind first (Flash-Lite is the fastest and most available on the free tier), then the newest version.
    score = {"flash-lite": 200, "flash": 100, "pro": 0}[m.group(2)] + float(m.group(1))
    if "preview" in m.group(3) or "exp" in m.group(3):
        score -= 50
    return score


@st.cache_data(ttl=86400, show_spinner=False)
def model_ranking(_key: str) -> list[str]:
    """Ask Google which models this key can use, best first."""
    resp = requests.get(
        "https://generativelanguage.googleapis.com/v1beta/models",
        headers={"x-goog-api-key": _key}, params={"pageSize": 200}, timeout=20,
    )
    resp.raise_for_status()
    names = [
        m["name"].split("/", 1)[-1]
        for m in resp.json().get("models", [])
        if "generateContent" in m.get("supportedGenerationMethods", [])
    ]
    scored = [(s, n) for n in names if (s := _model_score(n)) is not None]
    return [n for _, n in sorted(scored, reverse=True)]


@st.cache_resource
def _working_model() -> dict:
    return {"name": None, "pause_until": 0.0}


def _thinking_config(model: str) -> dict:
    """Keep 'thinking' to a minimum: these are summaries, and thinking makes Flash models very slow."""
    m = MODEL_PATTERN.match(model)
    version = float(m.group(1)) if m else 0
    return {"thinkingBudget": 0} if version < 3 else {"thinkingLevel": "low"}


def _post(key: str, model: str, prompt: str, thinking: bool, timeout: int = 25):
    config = {"temperature": 0.2, "responseMimeType": "application/json"}
    if thinking:
        config["thinkingConfig"] = _thinking_config(model)
    return requests.post(
        GEMINI_URL.format(model=model),
        headers={"x-goog-api-key": key, "Content-Type": "application/json"},
        json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": config},
        timeout=timeout,
    )


def _google_message(resp) -> str:
    try:
        return resp.json()["error"]["message"][:200]
    except Exception:
        return f"HTTP {resp.status_code}"


def _call(prompt: str, timeout: int = 25) -> dict:
    key = secret("GEMINI_API_KEY")
    if not key:
        raise AIError("GEMINI_API_KEY is missing from the app secrets.")
    remembered = _working_model()
    if time.time() < remembered["pause_until"]:
        wait = int((remembered["pause_until"] - time.time()) / 60) + 1
        raise AIError(f"Gemini was unavailable a moment ago; the app will try again in about {wait} min")
    _spend_budget()

    candidates = [m for m in (remembered["name"], secret("GEMINI_MODEL")) if m]
    try:
        candidates += model_ranking(key)
    except Exception:
        candidates += ["gemini-flash-latest", "gemini-2.5-flash"]
    candidates = list(dict.fromkeys(candidates))[:5]

    last_error = "no model available"
    print(f"[ai] candidates: {candidates}", flush=True)
    for model in candidates:
        started = time.time()
        try:
            resp = _post(key, model, prompt, thinking=True, timeout=timeout)
            if resp.status_code == 400 and "thinking" in _google_message(resp).lower():
                resp = _post(key, model, prompt, thinking=False, timeout=timeout)  # this model doesn't take the thinking setting
        except requests.Timeout:
            last_error = f"{model}: timed out"
            print(f"[ai] {model} timed out", flush=True)
            if remembered["name"] == model:
                remembered["name"] = None
            continue
        print(f"[ai] {model} -> {resp.status_code} in {time.time() - started:.1f}s", flush=True)
        if resp.status_code in (400, 403, 404, 429) or resp.status_code >= 500:  # missing, not allowed, over quota or overloaded
            last_error = f"{model}: {_google_message(resp)}"
            if remembered["name"] == model:
                remembered["name"] = None
            continue
        remembered["name"] = model
        try:
            parts = resp.json()["candidates"][0]["content"]["parts"]
            text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
            text = re.sub(r"^```(?:json)?|```$", "", text.strip()).strip()
            return json.loads(text)
        except Exception as exc:
            raise AIError("The AI answer couldn't be read. Try again in a moment.") from exc
    remembered["pause_until"] = time.time() + 600  # don't make every visitor wait on a failing service
    raise AIError(f"Gemini didn't accept the request ({last_error}).")


def language_rule(lang: str) -> str:
    if lang == "ES":
        return ("- Write every text value in professional, neutral Latin American Spanish (finance vocabulary as used in Mexico and "
                "Argentina). Keep JSON keys and fixed values such as Buy/Hold/Sell, Low/Medium/High and Positive/Mixed/Negative in English.")
    return "- Write in English."


RULES = """STRICT RULES
- Use ONLY the facts in the data below. Do not add facts, numbers, quotes, dates or events that are not there.
- If something is unclear, say so briefly or leave it out.
- No buy/sell/hold recommendations and no price targets of your own.
- Plain, precise English for a finance graduate: explain any jargon in a few words.
- Never present old information as new; respect the timestamps given."""


# --------------------------------------------------------------------------- daily brief
BRIEF_PROMPT = """You are a buy-side market analyst writing today's short morning note.

{rules}
{language}
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
def daily_brief(slot: str, lang: str, _snapshot: str, _headlines: list[dict]) -> dict:
    """Cached per 6-hour slot (the leading underscore keeps the inputs out of the cache key)."""
    used = _headlines[:40]
    lines = [
        f"[{i}] {h['source']} | {h['time']:%a %b %d %H:%M} ET | {h['title']}"
        + (f" — {h['summary'][:300]}" if h.get("summary") else "")
        for i, h in enumerate(used, 1)
    ]
    now = dt.datetime.now(ET)
    prompt = BRIEF_PROMPT.format(rules=RULES, language=language_rule(lang), now=f"{now:%Y-%m-%d %H:%M} ET", snapshot=_snapshot, headlines="\n".join(lines))
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
STOCK_RULES = """STRICT RULES
- Use ONLY the facts in the data below. Do not add facts, numbers, quotes, dates or events that are not there.
- If something is unclear, say so briefly or leave it out.
- You must give a lean of Buy, Hold or Sell. It is a model opinion based only on this data, weighing valuation
  (DCF and reverse DCF), growth, risk, momentum and news. Do not just copy the Wall Street consensus: form your own
  view from the data, then compare it with the consensus. No price targets of your own.
- Plain, precise English for a finance graduate: explain any jargon in a few words.
- Never present old information as new; respect the timestamps given."""

STOCK_PROMPT = """You are an equity analyst at an asset manager writing a one-page view on {ticker} ({name}).

{rules}
{language}
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
  "lean": "Buy" or "Hold" or "Sell",
  "conviction": "Low" or "Medium" or "High",
  "lean_reason": "2-3 sentences: the main reasons for the lean, citing the data",
  "vs_consensus": "1-2 sentences comparing your lean with the Wall Street consensus in the data and why they differ or agree",
  "conclusion": "2-3 sentences, balanced"}}

DATA (as of {now})
{data}

RECENT NEWS
{news}
"""


@st.cache_data(ttl=12 * 3600, show_spinner=False)
def stock_take(ticker: str, name: str, day: str, assumptions: str, lang: str, _data_text: str, _news: list[dict]) -> dict:
    news_lines = [
        f"- {n['time']:%b %d} | {n['source']} | {n['title']}" + (f" — {n['summary'][:250]}" if n.get("summary") else "")
        for n in _news[:12] if n.get("time")
    ] or ["- No company news in the last 7 days."]
    now = dt.datetime.now(ET)
    prompt = STOCK_PROMPT.format(
        ticker=ticker, name=name, rules=STOCK_RULES, language=language_rule(lang), now=f"{now:%Y-%m-%d %H:%M} ET",
        data=_data_text, news="\n".join(news_lines),
    )
    out = _call(prompt)
    lean = str(out.get("lean", "")).strip().title()
    out["lean"] = lean if lean in ("Buy", "Hold", "Sell") else None
    conv = str(out.get("conviction", "")).strip().title()
    out["conviction"] = conv if conv in ("Low", "Medium", "High") else None
    out["generated_at"] = now
    return out


# --------------------------------------------------------------------------- news desk
DESK_PROMPT = """You are the head of a buy-side news desk writing today's read of the news for a portfolio manager
who invests in the US, Mexico and Argentina. Headlines may be in English or Spanish.

{rules}
{language}
- Each view must be built from the headlines of that section (and the FX and rates data where relevant).
- If a section has few or no relevant headlines, say so in one sentence instead of guessing.
- "tone" is the overall market tone the headlines suggest for that area: "Positive", "Mixed" or "Negative".

Return JSON exactly in this shape:
{{"overview": "3-4 sentences: the big picture across regions today",
  "regions": {{
    "USA": {{"tone": "...", "view": "3-4 sentences", "key_points": ["3-4 short points"], "watch": "1 sentence"}},
    "Mexico": {{...same keys...}}, "Argentina": {{...same keys...}}, "World": {{...same keys...}}}},
  "sectors": {{{sector_keys}}},
  "fx_rates": {{"view": "4-5 sentences on the dollar, the Mexican peso, Argentina's exchange rates and gap, and interest rates, using the FX AND RATES data and the headlines",
               "key_points": ["3-4 short points"]}}}}
For "sectors" use exactly these keys, each with {{"tone": "...", "view": "2-3 sentences"}}.

FX AND RATES (as of {now})
{fx}

{sections}
"""


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def news_view(slot: str, lang: str, _fx_text: str, _buckets: dict) -> dict:
    """AI read of the news desk, cached per 3-hour slot."""
    blocks = []
    for name, items in _buckets.items():
        lines = [f"- {h['source']} | {h['time']:%a %b %d %H:%M} ET | {h['title']}"
                 + (f" — {h['summary'][:160]}" if h.get("summary") else "") for h in items[:10]]
        blocks.append(f"HEADLINES: {name}\n" + ("\n".join(lines) if lines else "- (none)"))
    sector_names = [k for k in _buckets if k not in ("USA", "Mexico", "Argentina", "World")]
    now = dt.datetime.now(ET)
    prompt = DESK_PROMPT.format(rules=RULES, language=language_rule(lang), now=f"{now:%Y-%m-%d %H:%M} ET", fx=_fx_text,
                                sector_keys=", ".join(f'"{s}": {{...}}' for s in sector_names), sections="\n\n".join(blocks))
    out = _call(prompt, timeout=50)
    out["generated_at"] = now
    return out
