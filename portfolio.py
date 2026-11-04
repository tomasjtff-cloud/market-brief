"""Portfolio and risk management maths. Pure Python (pandas, numpy, scipy): no Streamlit, so it is unit-tested.

Conventions
- Transactions are dicts: {"id", "date" (YYYY-MM-DD), "type", "ticker", "shares", "price", "fee", "amount", "note"}.
  Types: buy, sell (ticker, shares, price, fee), dividend (ticker, amount), deposit, withdraw (amount),
  cash_adjust (amount, signed: sets the cash balance the user reports).
- Cash never goes below zero: a purchase larger than the cash on hand is treated as new money put in that day.
- Holdings use the average-cost method. "CASH" is a zero-risk asset in the risk and optimisation maths.
"""
from __future__ import annotations

import datetime as dt
import math
import uuid

import numpy as np
import pandas as pd

TRADING_DAYS = 252
CASH = "CASH"
TYPES = ("buy", "sell", "dividend", "deposit", "withdraw", "cash_adjust")

# Funds (not single companies): broader caps in the optimiser and their own sector buckets.
KNOWN_ETFS = {
    "SPY", "VOO", "IVV", "VTI", "QQQ", "DIA", "IWM", "EFA", "VEA", "IEFA", "VWO", "EEM", "IEMG", "ACWI", "VT",
    "BND", "AGG", "TLT", "IEF", "SHY", "SHV", "BIL", "SGOV", "TIP", "LQD", "HYG", "EMB", "GLD", "IAU", "SLV",
    "EWW", "ARGT", "EWZ", "FXI", "EWJ", "VNQ", "SCHD", "VYM", "DGRO", "SMH", "SOXX", "ARKK", "UUP", "USO",
    "XLK", "XLF", "XLV", "XLY", "XLC", "XLI", "XLP", "XLE", "XLU", "XLRE", "XLB", "VUG", "VTV", "IJH", "IJR",
}
ETF_SECTOR = {
    "SPY": "Broad US equity", "VOO": "Broad US equity", "IVV": "Broad US equity", "VTI": "Broad US equity",
    "DIA": "Broad US equity", "IWM": "Broad US equity", "QQQ": "Technology", "SMH": "Technology", "SOXX": "Technology",
    "ARKK": "Technology", "XLK": "Technology", "XLF": "Financials", "XLV": "Health care", "XLY": "Consumer discretionary",
    "XLC": "Communication services", "XLI": "Industrials", "XLP": "Consumer staples", "XLE": "Energy", "USO": "Energy",
    "XLU": "Utilities", "XLRE": "Real estate", "VNQ": "Real estate", "XLB": "Materials",
    "EFA": "International equity", "VEA": "International equity", "IEFA": "International equity", "ACWI": "International equity",
    "VT": "International equity", "EWJ": "International equity", "VWO": "Emerging markets", "EEM": "Emerging markets",
    "IEMG": "Emerging markets", "EWW": "Emerging markets", "ARGT": "Emerging markets", "EWZ": "Emerging markets",
    "FXI": "Emerging markets", "BND": "Bonds", "AGG": "Bonds", "TLT": "Bonds", "IEF": "Bonds", "SHY": "Bonds",
    "SHV": "Bonds", "BIL": "Bonds", "SGOV": "Bonds", "TIP": "Bonds", "LQD": "Bonds", "HYG": "Bonds", "EMB": "Bonds",
    "GLD": "Gold & commodities", "IAU": "Gold & commodities", "SLV": "Gold & commodities", "UUP": "Currency",
    "SCHD": "Broad US equity", "VYM": "Broad US equity", "DGRO": "Broad US equity", "VUG": "Broad US equity",
    "VTV": "Broad US equity", "IJH": "Broad US equity", "IJR": "Broad US equity",
}
# Diversifiers the optimiser and the idea generator may consider in addition to the holdings.
DIVERSIFIERS = ["SPY", "BND", "GLD", "VEA", "VWO"]


def is_etf(ticker: str, industry: str | None = None) -> bool:
    return ticker in KNOWN_ETFS or (industry is not None and industry.strip() == "")


def _order(t: dict) -> tuple:
    """Date order; on the same day cash comes in first, then trades in the order they were entered (stable sort)."""
    return (t["date"], 0 if t["type"] in ("deposit", "cash_adjust") else 1)


def new_id() -> str:
    return uuid.uuid4().hex[:10]


def empty_book() -> dict:
    return {"version": 1, "transactions": [], "profile": None, "updated": None}


# =========================================================================== validation
def clean_transaction(t: dict) -> dict:
    """Normalise one transaction; raises ValueError with a short reason when it is not usable."""
    typ = str(t.get("type", "")).lower()
    if typ not in TYPES:
        raise ValueError(f"unknown type {typ!r}")
    try:
        day = dt.date.fromisoformat(str(t.get("date"))[:10])
    except ValueError:
        raise ValueError("bad date") from None
    out = {"id": str(t.get("id") or new_id()), "date": day.isoformat(), "type": typ, "note": str(t.get("note") or "")[:120]}
    if typ in ("buy", "sell"):
        ticker = str(t.get("ticker") or "").strip().upper()
        shares, price = float(t.get("shares") or 0), float(t.get("price") or 0)
        if not ticker or shares <= 0 or price <= 0:
            raise ValueError("buy/sell needs a ticker, shares > 0 and price > 0")
        out.update(ticker=ticker, shares=shares, price=price, fee=max(float(t.get("fee") or 0), 0.0))
    elif typ == "dividend":
        ticker = str(t.get("ticker") or "").strip().upper()
        amount = float(t.get("amount") or 0)
        if not ticker or amount <= 0:
            raise ValueError("dividend needs a ticker and amount > 0")
        out.update(ticker=ticker, amount=amount)
    else:
        amount = float(t.get("amount") or 0)
        if typ in ("deposit", "withdraw") and amount <= 0:
            raise ValueError("amount must be > 0")
        out.update(amount=amount)
    return out


def clean_book(book: dict) -> tuple[dict, list[str]]:
    """Validate a stored or uploaded book. Returns the clean book and the problems found (bad rows are dropped)."""
    problems, txs = [], []
    for i, t in enumerate((book or {}).get("transactions", []) or []):
        try:
            txs.append(clean_transaction(t))
        except (ValueError, TypeError) as exc:
            problems.append(f"row {i + 1}: {exc}")
    profile = (book or {}).get("profile")
    return {"version": 1, "transactions": sorted(txs, key=_order), "profile": profile,
            "updated": (book or {}).get("updated")}, problems


# =========================================================================== positions
def positions(txs: list[dict]) -> dict:
    """Average-cost positions, realised P&L, dividends, cash and money put in."""
    hold: dict[str, dict] = {}
    cash, contributed, withdrawn, realized, dividends, fees = 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
    problems = []
    for t in sorted(txs, key=_order):
        typ = t["type"]
        if typ == "deposit":
            cash += t["amount"]
            contributed += t["amount"]
        elif typ == "withdraw":
            take = min(t["amount"], cash)
            cash -= take
            withdrawn += take
        elif typ == "cash_adjust":
            cash += t["amount"]
            if cash < 0:
                cash = 0.0
            contributed += t["amount"]
        elif typ == "dividend":
            cash += t["amount"]
            dividends += t["amount"]
            hold.setdefault(t["ticker"], {"shares": 0.0, "cost": 0.0, "realized": 0.0, "dividends": 0.0})["dividends"] += t["amount"]
        elif typ == "buy":
            h = hold.setdefault(t["ticker"], {"shares": 0.0, "cost": 0.0, "realized": 0.0, "dividends": 0.0})
            spend = t["shares"] * t["price"] + t["fee"]
            if spend > cash:  # bought with new money
                contributed += spend - cash
                cash = 0.0
            else:
                cash -= spend
            h["shares"] += t["shares"]
            h["cost"] += spend
            fees += t["fee"]
        elif typ == "sell":
            h = hold.get(t["ticker"])
            if not h or h["shares"] <= 1e-9:
                problems.append(f"{t['date']}: sell of {t['ticker']} with no shares held")
                continue
            qty = min(t["shares"], h["shares"])
            if t["shares"] > h["shares"] + 1e-9:
                problems.append(f"{t['date']}: sold more {t['ticker']} than held; capped at {h['shares']:g}")
            avg = h["cost"] / h["shares"]
            proceeds = qty * t["price"] - t["fee"]
            pnl = proceeds - avg * qty
            h["realized"] += pnl
            realized += pnl
            h["cost"] -= avg * qty
            h["shares"] -= qty
            cash += proceeds
            fees += t["fee"]
    open_pos = {k: v for k, v in hold.items() if v["shares"] > 1e-9}
    for v in open_pos.values():
        v["avg_cost"] = v["cost"] / v["shares"]
    return {"holdings": open_pos, "all": hold, "cash": cash, "contributed": contributed, "withdrawn": withdrawn,
            "realized": realized, "dividends": dividends, "fees": fees, "problems": problems}


def valuation_table(pos: dict, prices: dict[str, float], meta: dict[str, dict] | None = None) -> pd.DataFrame:
    """One row per open position plus cash: value, weight, cost, unrealised P&L."""
    meta = meta or {}
    rows = []
    for tk, h in pos["holdings"].items():
        px = prices.get(tk)
        value = h["shares"] * px if px else None
        rows.append({"ticker": tk, "name": (meta.get(tk) or {}).get("name", tk), "sector": (meta.get(tk) or {}).get("sector", "Other"),
                     "shares": h["shares"], "avg_cost": h["avg_cost"], "price": px, "value": value, "cost": h["cost"],
                     "unrealized": (value - h["cost"]) if value is not None else None,
                     "unrealized_pct": (value / h["cost"] - 1) if value is not None and h["cost"] else None,
                     "realized": h["realized"], "dividends": h["dividends"]})
    rows.append({"ticker": CASH, "name": "Cash", "sector": "Cash", "shares": None, "avg_cost": None, "price": 1.0,
                 "value": pos["cash"], "cost": pos["cash"], "unrealized": 0.0, "unrealized_pct": 0.0, "realized": 0.0, "dividends": 0.0})
    df = pd.DataFrame(rows)
    total = df["value"].fillna(0).sum()
    df["weight"] = df["value"].fillna(0) / total if total > 0 else 0.0
    return df


# =========================================================================== history
def value_history(txs: list[dict], closes: dict[str, pd.Series]) -> pd.DataFrame:
    """Daily market value, cash and external flows since the first transaction, plus a time-weighted return index."""
    if not txs:
        return pd.DataFrame()
    txs = sorted(txs, key=_order)
    start = pd.Timestamp(txs[0]["date"])
    px = pd.DataFrame({k: v for k, v in closes.items() if v is not None and len(v)}).sort_index()
    px = px[px.index >= start - pd.Timedelta(days=7)].ffill()
    days = px.index[px.index >= start]
    if len(days) < 2:
        return pd.DataFrame()
    by_day: dict[pd.Timestamp, list[dict]] = {}
    for t in txs:
        d = pd.Timestamp(t["date"])
        nxt = days[days >= d]
        if len(nxt):
            by_day.setdefault(nxt[0], []).append(t)
    shares: dict[str, float] = {}
    cash = 0.0
    out = []
    for d in days:
        flow = 0.0
        for t in by_day.get(d, []):
            typ = t["type"]
            if typ in ("deposit", "cash_adjust"):
                cash += t["amount"]
                flow += t["amount"]
                if cash < 0:
                    flow -= cash
                    cash = 0.0
            elif typ == "withdraw":
                take = min(t["amount"], cash)
                cash -= take
                flow -= take
            elif typ == "dividend":
                cash += t["amount"]
            elif typ == "buy":
                spend = t["shares"] * t["price"] + t["fee"]
                if spend > cash:
                    flow += spend - cash
                    cash = 0.0
                else:
                    cash -= spend
                shares[t["ticker"]] = shares.get(t["ticker"], 0.0) + t["shares"]
            elif typ == "sell":
                held = shares.get(t["ticker"], 0.0)
                qty = min(t["shares"], held)
                shares[t["ticker"]] = held - qty
                cash += qty * t["price"] - t["fee"]
        mv = 0.0
        for tk, n in shares.items():
            if n > 1e-9 and tk in px.columns and not math.isnan(px.at[d, tk]):
                mv += n * float(px.at[d, tk])
        out.append({"date": d, "holdings": mv, "cash": cash, "value": mv + cash, "flow": flow})
    df = pd.DataFrame(out).set_index("date")
    prev = df["value"].shift(1)
    r = (df["value"] - df["flow"]) / prev - 1
    r = r.where(prev > 0, 0.0).fillna(0.0)
    df["twr_index"] = (1 + r).cumprod()
    df["invested"] = df["flow"].cumsum()
    return df


# =========================================================================== risk
def returns_matrix(closes: dict[str, pd.Series], days: int = 2 * TRADING_DAYS) -> pd.DataFrame:
    df = pd.DataFrame({k: v for k, v in closes.items() if v is not None}).sort_index().ffill()
    df = df.dropna(how="any").iloc[-(days + 1):]
    return df.pct_change().dropna(how="any")


def portfolio_returns(rets: pd.DataFrame, weights: dict[str, float]) -> pd.Series:
    """Daily returns of a constant-weight portfolio (cash earns nothing in the backtest)."""
    cols = [c for c in weights if c in rets.columns]
    w = np.array([weights[c] for c in cols])
    return pd.Series(rets[cols].to_numpy() @ w, index=rets.index) if cols else pd.Series(0.0, index=rets.index)


def risk_report(rets: pd.DataFrame, weights: dict[str, float], value: float, rf: float,
                bench: pd.Series | None = None) -> dict:
    """Risk of the current mix, measured on the last two years of daily returns (constant weights)."""
    pr = portfolio_returns(rets, weights)
    if len(pr) < 60:
        return {}
    vol = float(pr.std() * math.sqrt(TRADING_DAYS))
    idx = (1 + pr).cumprod()
    years = len(pr) / TRADING_DAYS
    ann = float(idx.iloc[-1] ** (1 / years) - 1)
    mdd = float((idx / idx.cummax() - 1).min())
    q = float(np.percentile(pr, 5))
    var1 = -q
    cvar1 = -float(pr[pr <= q].mean())
    z = 1.6449
    beta = None
    if bench is not None:
        b = bench.pct_change().reindex(pr.index).dropna()
        common = pr.reindex(b.index)
        wk = pd.concat([(1 + common).cumprod(), (1 + b).cumprod()], axis=1).resample("W-FRI").last().pct_change().dropna()
        if len(wk) > 30 and wk.iloc[:, 1].var() > 0:
            beta = float(wk.iloc[:, 0].cov(wk.iloc[:, 1]) / wk.iloc[:, 1].var())
    cov = rets.cov() * TRADING_DAYS
    cols = [c for c in weights if c in cov.columns]
    w = np.array([weights[c] for c in cols])
    contrib = {}
    if cols and vol > 0:
        sw = cov.loc[cols, cols].to_numpy() @ w
        port_var = float(w @ sw)
        if port_var > 0:
            contrib = {c: float(w[i] * sw[i] / port_var) for i, c in enumerate(cols)}
    return {
        "vol": vol, "ann_return": ann, "sharpe": (ann - rf) / vol if vol else None, "max_drawdown": mdd, "beta": beta,
        "var95_1d": var1, "cvar95_1d": cvar1, "var95_1d_usd": var1 * value, "cvar95_1d_usd": cvar1 * value,
        "var95_1m_param": z * vol * math.sqrt(21 / TRADING_DAYS), "var95_1m_param_usd": z * vol * math.sqrt(21 / TRADING_DAYS) * value,
        "risk_contrib": contrib, "index": idx, "days": len(pr),
    }


def concentration(table: pd.DataFrame, etf_flags: dict[str, bool]) -> dict:
    inv = table[table["ticker"] != CASH]
    w = table.set_index("ticker")["weight"]
    stock_w = {t: float(w[t]) for t in inv["ticker"] if not etf_flags.get(t)}
    sectors = table.groupby("sector")["weight"].sum().sort_values(ascending=False)
    hhi = float((w ** 2).sum())
    return {
        "top_ticker": inv.sort_values("weight", ascending=False)["ticker"].iloc[0] if len(inv) else None,
        "top_weight": float(inv["weight"].max()) if len(inv) else 0.0,
        "top3_weight": float(inv["weight"].nlargest(3).sum()) if len(inv) else 0.0,
        "largest_stock": max(stock_w, key=stock_w.get) if stock_w else None,
        "largest_stock_weight": max(stock_w.values()) if stock_w else 0.0,
        "hhi": hhi, "effective_n": 1 / hhi if hhi > 0 else 0.0, "sectors": sectors.to_dict(),
        "cash_weight": float(w.get(CASH, 0.0)),
    }


# =========================================================================== investor profile
QUESTIONS = {
    "goal": ["Protect what I have", "Steady income", "Balance growth and safety", "Grow my money", "Maximise long-term growth"],
    "horizon": ["Less than 1 year", "1 to 3 years", "3 to 5 years", "5 to 10 years", "More than 10 years"],
    "drop": ["Sell everything", "Sell part", "Do nothing", "Buy a little more", "Buy a lot more"],
    "loss": ["Up to 5%", "Up to 10%", "Up to 20%", "Up to 30%", "40% or more"],
    "liquidity": ["Most of it within a year", "Part of it within 1–2 years", "Some of it within 3 years",
                  "Probably none for 5 years", "None: this is long-term money"],
    "style": ["Only diversified funds (ETFs)", "Mostly funds, a few stocks", "Half funds, half stocks",
              "Mostly individual stocks", "Concentrated bets on individual stocks"],
}
PROFILES = [  # name, max score, target volatility, drawdown tolerance, single-stock cap, minimum cash + bonds
    ("Conservative", 1.8, 0.07, 0.10, 0.10, 0.40),
    ("Moderately conservative", 2.6, 0.10, 0.15, 0.15, 0.25),
    ("Moderate", 3.4, 0.14, 0.25, 0.20, 0.10),
    ("Growth", 4.2, 0.18, 0.35, 0.25, 0.05),
    ("Aggressive", 5.1, 0.24, 0.50, 0.35, 0.0),
]


def investor_profile(answers: dict[str, int]) -> dict:
    """Answers are 1-5. Willingness (goal, reaction, style) and capacity (horizon, affordable loss, liquidity) are scored
    separately; when they disagree by more than a point, the lower one sets the profile, as risk-profiling practice does."""
    a = {k: int(answers.get(k, 3)) for k in QUESTIONS}
    will = (a["goal"] + a["drop"] + a["style"]) / 3
    cap = (a["horizon"] + a["loss"] + a["liquidity"]) / 3
    score = min(will, cap) if abs(will - cap) > 1 else (will + cap) / 2
    for name, top, vol, dd, single, safe in PROFILES:
        if score <= top:
            break
    if a["liquidity"] <= 2:
        safe = max(safe, 0.20 if a["liquidity"] == 2 else 0.40)
    return {"name": name, "score": score, "willingness": will, "capacity": cap, "target_vol": vol, "max_drawdown": dd,
            "single_cap": single, "min_safe": safe, "answers": a, "limited_by": "capacity" if cap < will - 1 else
            "willingness" if will < cap - 1 else None}


def profile_checks(profile: dict, risk: dict, conc: dict, safe_weight: float) -> list[dict]:
    """Rule-based mismatches between the profile and the portfolio. Each item: level (high/medium/ok), code, numbers."""
    out = []
    if risk.get("vol") is not None:
        if risk["vol"] > profile["target_vol"] * 1.15:
            out.append({"level": "high", "code": "vol_high", "value": risk["vol"], "limit": profile["target_vol"]})
        elif risk["vol"] < profile["target_vol"] * 0.5:
            out.append({"level": "medium", "code": "vol_low", "value": risk["vol"], "limit": profile["target_vol"]})
        else:
            out.append({"level": "ok", "code": "vol_ok", "value": risk["vol"], "limit": profile["target_vol"]})
    if risk.get("max_drawdown") is not None:
        if -risk["max_drawdown"] > profile["max_drawdown"]:
            out.append({"level": "high", "code": "dd_high", "value": -risk["max_drawdown"], "limit": profile["max_drawdown"]})
        else:
            out.append({"level": "ok", "code": "dd_ok", "value": -risk["max_drawdown"], "limit": profile["max_drawdown"]})
    if conc.get("largest_stock") and conc["largest_stock_weight"] > profile["single_cap"]:
        out.append({"level": "high", "code": "single_high", "value": conc["largest_stock_weight"], "limit": profile["single_cap"],
                    "ticker": conc["largest_stock"]})
    if safe_weight < profile["min_safe"] - 0.02:
        out.append({"level": "high" if profile["min_safe"] >= 0.2 else "medium", "code": "safe_low", "value": safe_weight,
                    "limit": profile["min_safe"]})
    top_sector = next(((s, w) for s, w in conc.get("sectors", {}).items() if s not in ("Cash", "Bonds", "Broad US equity",
                                                                                         "International equity")), None)
    if top_sector and top_sector[1] > 0.40:
        out.append({"level": "medium", "code": "sector_high", "value": top_sector[1], "limit": 0.40, "sector": top_sector[0]})
    return out


# =========================================================================== optimisation
def ledoit_wolf(rets: pd.DataFrame) -> pd.DataFrame:
    """Ledoit-Wolf (2004) shrinkage of the sample covariance towards a scaled identity, annualised."""
    x = rets.to_numpy()
    t, n = x.shape
    x = x - x.mean(axis=0)
    s = x.T @ x / t
    mu = np.trace(s) / n
    f = mu * np.eye(n)
    d2 = np.sum((s - f) ** 2)
    b2 = sum(np.sum((np.outer(row, row) - s) ** 2) for row in x) / t ** 2
    b2 = min(b2, d2)
    delta = b2 / d2 if d2 > 0 else 1.0
    shrunk = delta * f + (1 - delta) * s
    return pd.DataFrame(shrunk * TRADING_DAYS, index=rets.columns, columns=rets.columns)


def capm_returns(rets: pd.DataFrame, market: pd.Series, rf: float, erp: float = 0.05) -> pd.Series:
    """Expected annual returns implied by CAPM (rf + beta x equity risk premium), steadier than past averages."""
    m = market.pct_change().reindex(rets.index)
    mask = m.notna()
    var = m[mask].var()
    betas = {c: (rets.loc[mask, c].cov(m[mask]) / var) if var > 0 else 1.0 for c in rets.columns}
    return pd.Series({c: rf + b * erp for c, b in betas.items()})


def _stats(w: np.ndarray, mu: np.ndarray, cov: np.ndarray, rf: float) -> dict:
    r = float(w @ mu)
    v = float(math.sqrt(max(w @ cov @ w, 0.0)))
    return {"ret": r, "vol": v, "sharpe": (r - rf) / v if v > 1e-9 else None}


def optimise(mu: pd.Series, cov: pd.DataFrame, rf: float, caps: dict[str, float], target_vol: float | None = None,
             frontier_points: int = 30) -> dict:
    """Long-only Markowitz with per-asset caps. CASH (if present) is a zero-variance asset earning rf.

    Returns the global minimum variance, maximum Sharpe (tangency) and the profile portfolio (highest expected return
    whose volatility stays within target_vol), plus the efficient frontier.
    """
    from scipy.optimize import minimize

    names = list(mu.index)
    m, c = mu.to_numpy(float), cov.loc[names, names].to_numpy(float)
    n = len(names)
    ub = np.array([min(max(caps.get(k, 1.0), 0.0), 1.0) for k in names])
    if ub.sum() < 1:  # caps too tight to be fully invested: scale them up proportionally
        ub = np.minimum(ub / ub.sum(), 1.0)
    bounds = list(zip(np.zeros(n), ub))
    x0 = ub / ub.sum()
    budget = {"type": "eq", "fun": lambda w: w.sum() - 1}
    opts = {"maxiter": 500, "ftol": 1e-10}

    def solve(obj, extra=()):
        res = minimize(obj, x0, method="SLSQP", bounds=bounds, constraints=[budget, *extra], options=opts)
        w = np.clip(res.x, 0, None)
        return w / w.sum() if w.sum() > 0 else x0, bool(res.success)

    gmv, _ = solve(lambda w: w @ c @ w)

    def neg_sharpe(w):
        v = math.sqrt(max(w @ c @ w, 1e-12))
        return -(w @ m - rf) / v
    ms, _ = solve(neg_sharpe)

    as_dict = lambda w: {k: float(x) for k, x in zip(names, w) if x > 0.0005}  # noqa: E731
    lo, hi = float(gmv @ m), float(max(m[ub > 0]))
    frontier = [{**_stats(gmv, m, c, rf), "weights": as_dict(gmv)}]
    for target in np.linspace(lo, hi, frontier_points)[1:]:
        w, ok = solve(lambda w: w @ c @ w, ({"type": "ineq", "fun": lambda w, t=target: w @ m - t},))
        if ok:
            frontier.append({**_stats(w, m, c, rf), "weights": as_dict(w)})
    frontier.sort(key=lambda r: r["vol"])
    clean = []
    for r in frontier:  # keep only points that add return as risk rises (the efficient part), drop near-duplicates
        if not clean or (r["ret"] > clean[-1]["ret"] + 1e-5 and r["vol"] > clean[-1]["vol"] + 1e-5):
            clean.append(r)
    frontier = clean
    prof = None
    if target_vol is not None:
        if _stats(gmv, m, c, rf)["vol"] > target_vol:
            prof, feasible = gmv, False
        else:
            prof, feasible = solve(lambda w: -(w @ m),
                                   ({"type": "ineq", "fun": lambda w: target_vol ** 2 - w @ c @ w},))
            feasible = True
    out = {"gmv": {"weights": as_dict(gmv), **_stats(gmv, m, c, rf)},
           "max_sharpe": {"weights": as_dict(ms), **_stats(ms, m, c, rf)},
           "frontier": frontier,
           "assets": {k: {"ret": float(m[i]), "vol": float(math.sqrt(c[i, i]))} for i, k in enumerate(names)}}
    if prof is not None:
        out["profile"] = {"weights": as_dict(prof), **_stats(prof, m, c, rf), "feasible": feasible}
    return out


def mix_stats(weights: dict[str, float], mu: pd.Series, cov: pd.DataFrame, rf: float) -> dict:
    names = [k for k in weights if k in mu.index]
    w = np.array([weights[k] for k in names])
    if not len(names) or w.sum() <= 0:
        return {"ret": None, "vol": None, "sharpe": None}
    w = w / w.sum()
    return _stats(w, mu[names].to_numpy(float), cov.loc[names, names].to_numpy(float), rf)


def with_cash(mu: pd.Series, cov: pd.DataFrame, rf: float) -> tuple[pd.Series, pd.DataFrame]:
    mu2 = pd.concat([mu, pd.Series({CASH: rf})])
    cov2 = cov.reindex(index=mu2.index, columns=mu2.index).fillna(0.0)
    return mu2, cov2


def shift_weights(weights: dict[str, float], ticker: str, new_weight: float, funding: str = CASH) -> dict[str, float]:
    """Move one asset to new_weight, taking or giving the difference from `funding` (cash by default, or 'pro rata')."""
    w = dict(weights)
    old = w.get(ticker, 0.0)
    diff = new_weight - old
    w[ticker] = new_weight
    if funding == "pro rata":
        others = {k: v for k, v in w.items() if k != ticker and v > 0}
        tot = sum(others.values())
        for k in others:
            w[k] = others[k] - diff * others[k] / tot if tot > 0 else others[k]
    else:
        w[funding] = w.get(funding, 0.0) - diff
    w = {k: max(v, 0.0) for k, v in w.items()}
    s = sum(w.values())
    return {k: v / s for k, v in w.items() if v > 1e-6} if s > 0 else w


# =========================================================================== performance attribution
SECTOR_ETF = {"Technology": "XLK", "Financials": "XLF", "Health care": "XLV", "Consumer discretionary": "XLY",
              "Communication services": "XLC", "Industrials": "XLI", "Consumer staples": "XLP", "Energy": "XLE",
              "Utilities": "XLU", "Real estate": "XLRE", "Materials": "XLB"}
# Finnhub industry names -> S&P 500 (GICS) sectors. First keyword found wins.
_INDUSTRY_KEYS = [
    ("Communication services", ("media", "telecommunication", "communications", "entertainment", "interactive")),
    ("Technology", ("semiconductor", "technology", "software", "electronic", "it services", "computers")),
    ("Financials", ("bank", "financial", "insurance", "capital markets", "diversified financ", "consumer finance")),
    ("Health care", ("health", "pharma", "biotech", "life sciences", "medical")),
    ("Consumer staples", ("beverages", "food", "tobacco", "household", "personal products", "staples")),
    ("Consumer discretionary", ("retail", "automobile", "auto components", "hotels", "restaurants", "leisure", "textiles",
                                "apparel", "luxury", "distributors", "diversified consumer", "consumer products", "homebuilding")),
    ("Energy", ("energy", "oil", "gas")),
    ("Utilities", ("utilities",)),
    ("Real estate", ("real estate", "reit")),
    ("Materials", ("chemicals", "metals", "mining", "packaging", "paper", "forest", "construction materials")),
    ("Industrials", ("aerospace", "defense", "airlines", "building", "construction", "electrical", "machinery", "industrial",
                     "logistics", "transportation", "road & rail", "marine", "commercial services", "professional services",
                     "trading companies")),
]


def sector_of(ticker: str, industry: str | None, etf: bool) -> tuple[str, str]:
    """(sector name, benchmark ETF used for it). An ETF is its own benchmark, so its whole excess return is allocation."""
    if etf:
        return ETF_SECTOR.get(ticker, "Funds"), ticker
    low = (industry or "").lower()
    for sector, keys in _INDUSTRY_KEYS:
        if any(k in low for k in keys):
            return sector, SECTOR_ETF[sector]
    return "Other", "SPY"


def _link(daily: pd.Series, port: pd.Series, bench: pd.Series | None = None) -> float:
    """Carino linking: scale daily effects so they add up exactly to the multi-period (active) return."""
    lg = lambda x: np.log1p(x)  # noqa: E731
    if bench is None:
        R = float((1 + port).prod() - 1)
        K = lg(R) / R if abs(R) > 1e-12 else 1.0
        k = pd.Series(np.where(port.abs() > 1e-12, lg(port) / port.where(port.abs() > 1e-12, 1), 1.0), index=port.index)
        return float((daily * k).sum() / K)
    R, B = float((1 + port).prod() - 1), float((1 + bench).prod() - 1)
    K = (lg(R) - lg(B)) / (R - B) if abs(R - B) > 1e-12 else 1 / (1 + R)
    diff = port - bench
    k = pd.Series(np.where(diff.abs() > 1e-12, (lg(port) - lg(bench)) / diff.where(diff.abs() > 1e-12, 1), 1 / (1 + port)),
                  index=port.index)
    return float((daily * k).sum() / K)


def attribution(txs: list[dict], closes: dict[str, pd.Series], sectors: dict[str, tuple[str, str]],
                bench: pd.Series, start: pd.Timestamp | None = None) -> dict | None:
    """Where the return came from, day by day with the previous close's holdings, linked over the period (Carino).

    Contribution of each position = its weight × its price return, plus dividends. Versus the S&P 500 (SPY, price only):
      active return = sector bets  Σ w·(sector ETF − SPY)
                    + cash         −w_cash·SPY
                    + selection    Σ w·(stock − its sector ETF)   (dividends count here)
                    + trading      buys/sells done at a price other than that day's close, and fees.
    """
    if not txs:
        return None
    txs = sorted(txs, key=_order)
    first = pd.Timestamp(txs[0]["date"])
    names = [t for t in {t.get("ticker") for t in txs if t.get("ticker")} if t in closes]
    etfs = {s[1] for s in sectors.values()}
    px = pd.DataFrame({**{k: closes[k] for k in names}, **{e: closes[e] for e in etfs if e in closes}, "__SPY": bench}).sort_index()
    px = px[px.index >= first - pd.Timedelta(days=7)].ffill()
    days = px.index[px.index >= first]
    if len(days) < 3:
        return None
    by_day: dict[pd.Timestamp, list[dict]] = {}
    for t in txs:
        nxt = days[days >= pd.Timestamp(t["date"])]
        if len(nxt):
            by_day.setdefault(nxt[0], []).append(t)
    shares: dict[str, float] = {}
    cash = 0.0
    prev_val = None
    recs, contrib = [], []
    for i, d in enumerate(days):
        c_day: dict[str, float] = {}
        trading, flow = 0.0, 0.0
        w_prev: dict[str, float] = {}
        if i > 0 and prev_val and prev_val > 0:
            pd_ = days[i - 1]
            for tk, n in shares.items():
                if n > 1e-9 and tk in px.columns and pd.notna(px.at[pd_, tk]) and pd.notna(px.at[d, tk]):
                    w_prev[tk] = n * float(px.at[pd_, tk]) / prev_val
                    c_day[tk] = n * (float(px.at[d, tk]) - float(px.at[pd_, tk])) / prev_val
        for t in by_day.get(d, []):
            typ = t["type"]
            if typ in ("deposit", "cash_adjust"):
                cash += t["amount"]
                flow += t["amount"]
                if cash < 0:
                    flow -= cash
                    cash = 0.0
            elif typ == "withdraw":
                take = min(t["amount"], cash)
                cash -= take
                flow -= take
            elif typ == "dividend":
                cash += t["amount"]
                if prev_val:
                    c_day[t["ticker"]] = c_day.get(t["ticker"], 0.0) + t["amount"] / prev_val
            elif typ == "buy":
                spend = t["shares"] * t["price"] + t["fee"]
                if spend > cash:
                    flow += spend - cash
                    cash = 0.0
                else:
                    cash -= spend
                shares[t["ticker"]] = shares.get(t["ticker"], 0.0) + t["shares"]
                if prev_val and t["ticker"] in px.columns and pd.notna(px.at[d, t["ticker"]]):
                    trading += (t["shares"] * (float(px.at[d, t["ticker"]]) - t["price"]) - t["fee"]) / prev_val
            elif typ == "sell":
                held = shares.get(t["ticker"], 0.0)
                qty = min(t["shares"], held)
                shares[t["ticker"]] = held - qty
                cash += qty * t["price"] - t["fee"]
                if prev_val and t["ticker"] in px.columns and pd.notna(px.at[d, t["ticker"]]):
                    trading += (qty * (t["price"] - float(px.at[d, t["ticker"]])) - t["fee"]) / prev_val
        mv = sum(n * float(px.at[d, tk]) for tk, n in shares.items() if n > 1e-9 and tk in px.columns and pd.notna(px.at[d, tk]))
        val = mv + cash
        if i > 0 and prev_val and prev_val > 0:
            r = (val - flow) / prev_val - 1
            rb = float(px.at[d, "__SPY"] / px.at[days[i - 1], "__SPY"] - 1)
            w_cash = 1 - sum(w_prev.values())
            sec_eff, sel_eff = 0.0, 0.0
            for tk, w in w_prev.items():
                etf = sectors.get(tk, ("Other", "SPY"))[1]
                col = "__SPY" if etf == "SPY" or etf not in px.columns else etf
                rs = float(px.at[d, col] / px.at[days[i - 1], col] - 1)
                sec_eff += w * (rs - rb)
                sel_eff += c_day.get(tk, 0.0) - w * rs
            for tk in c_day:  # dividends from positions sold before the previous close
                if tk not in w_prev:
                    sel_eff += c_day[tk]
            resid = r - sum(c_day.values()) - trading
            recs.append({"date": d, "r": r, "rb": rb, "sector": sec_eff, "cash": -w_cash * rb, "selection": sel_eff,
                         "trading": trading + resid, "w_cash": w_cash})
            contrib.append({"date": d, **c_day, "__trading": trading + resid, **{f"w:{k}": v for k, v in w_prev.items()}})
        prev_val = val
    if not recs:
        return None
    daily = pd.DataFrame(recs).set_index("date")
    cdf = pd.DataFrame(contrib).set_index("date").fillna(0.0)
    if start is not None:
        daily, cdf = daily[daily.index > start], cdf[cdf.index > start]
    if len(daily) < 2:
        return None
    port, benchr = daily["r"], daily["rb"]
    R, B = float((1 + port).prod() - 1), float((1 + benchr).prod() - 1)
    rows = []
    for tk in [c for c in cdf.columns if not c.startswith("w:") and c != "__trading"]:
        w = cdf.get(f"w:{tk}", pd.Series(0.0, index=cdf.index))
        held = w > 0
        sec, etf = sectors.get(tk, ("Other", "SPY"))
        rows.append({"ticker": tk, "sector": sec, "benchmark": etf, "avg_weight": float(w[held].mean()) if held.any() else 0.0,
                     "days": int(held.sum()), "contribution": _link(cdf[tk], port)})
    by_ticker = pd.DataFrame(rows, columns=["ticker", "sector", "benchmark", "avg_weight", "days", "contribution"])
    by_ticker = by_ticker.sort_values("contribution", ascending=False).reset_index(drop=True)
    effects = {k: _link(daily[k], port, benchr) for k in ("sector", "cash", "selection", "trading")}
    # sector table: contribution, allocation and selection per sector (linked with the same factors)
    sec_rows = []
    for sec, grp in by_ticker.groupby("sector"):
        tks = list(grp["ticker"])
        w = sum(cdf.get(f"w:{t}", 0.0) for t in tks)
        alloc_d, sel_d = pd.Series(0.0, index=cdf.index), pd.Series(0.0, index=cdf.index)
        for t in tks:
            wt = cdf.get(f"w:{t}", pd.Series(0.0, index=cdf.index))
            etf = sectors.get(t, ("Other", "SPY"))[1]
            src = bench if etf == "SPY" or etf not in closes else closes[etf]
            rs = src.reindex(px.index).ffill().pct_change().reindex(cdf.index).fillna(0.0)
            alloc_d += wt * (rs - daily["rb"])
            sel_d += cdf[t] - wt * rs
        sec_rows.append({"sector": sec, "avg_weight": float(w.mean()) if hasattr(w, "mean") else 0.0,
                         "contribution": float(grp["contribution"].sum()),
                         "allocation": _link(alloc_d, port, benchr), "selection": _link(sel_d, port, benchr)})
    by_sector = pd.DataFrame(sec_rows, columns=["sector", "avg_weight", "contribution", "allocation", "selection"])
    by_sector = by_sector.sort_values("contribution", ascending=False).reset_index(drop=True)
    cum = pd.DataFrame({"portfolio": (1 + port).cumprod() - 1, "benchmark": (1 + benchr).cumprod() - 1})
    return {"start": daily.index[0], "end": daily.index[-1], "days": len(daily), "port": R, "bench": B, "active": R - B,
            "effects": effects, "trading_total": _link(cdf["__trading"], port), "by_ticker": by_ticker, "by_sector": by_sector,
            "cum": cum, "avg_cash": float(daily["w_cash"].mean())}
