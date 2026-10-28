"""Pure finance functions: returns, risk metrics, statistical ranges, DCF.

No API calls here, so everything is unit-tested in tests/test_analysis.py.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

TRADING_DAYS = 252


# --------------------------------------------------------------------------- performance & risk
def period_return(close: pd.Series, days: int) -> float | None:
    if len(close) <= days:
        return None
    return close.iloc[-1] / close.iloc[-1 - days] - 1


def ytd_return(close: pd.Series) -> float | None:
    last_year = close.index[-1].year
    before = close[close.index.year < last_year]
    if before.empty:
        return None
    return close.iloc[-1] / before.iloc[-1] - 1


def annual_volatility(close: pd.Series, window: int = TRADING_DAYS) -> float | None:
    r = np.log(close).diff().dropna().iloc[-window:]
    if len(r) < 20:
        return None
    return float(r.std() * math.sqrt(TRADING_DAYS))


def max_drawdown(close: pd.Series, window: int = TRADING_DAYS) -> float | None:
    c = close.iloc[-window:]
    if len(c) < 2:
        return None
    return float((c / c.cummax() - 1).min())


def beta(close: pd.Series, bench_close: pd.Series, weeks: int = 104) -> float | None:
    """Two-year beta on weekly (Friday) returns, the usual convention for cost of capital."""
    weekly = pd.concat([close, bench_close], axis=1, join="inner").resample("W-FRI").last()
    df = weekly.pct_change().dropna().iloc[-weeks:]
    if len(df) < 40:
        return None
    var = df.iloc[:, 1].var()
    return float(df.iloc[:, 0].cov(df.iloc[:, 1]) / var) if var > 0 else None


def sharpe(close: pd.Series, rf: float) -> float | None:
    r1y = period_return(close, TRADING_DAYS)
    vol = annual_volatility(close)
    if r1y is None or not vol:
        return None
    return (r1y - rf) / vol


def risk_metrics(close: pd.Series, bench_close: pd.Series | None, rf: float) -> dict:
    return {
        "ret_1m": period_return(close, 21),
        "ret_3m": period_return(close, 63),
        "ret_ytd": ytd_return(close),
        "ret_1y": period_return(close, TRADING_DAYS),
        "volatility": annual_volatility(close),
        "max_drawdown": max_drawdown(close),
        "beta": beta(close, bench_close) if bench_close is not None else None,
        "sharpe": sharpe(close, rf),
    }


def statistical_range(price: float, vol: float, trading_days: int) -> tuple[float, float]:
    """One-standard-deviation band for log returns with zero drift.

    If daily returns keep the same volatility and are roughly normal in logs,
    about 68% of outcomes land inside this band. It is a description of past
    volatility, not a forecast of direction.
    """
    s = vol * math.sqrt(trading_days / TRADING_DAYS)
    return price * math.exp(-s), price * math.exp(s)


# --------------------------------------------------------------------------- cost of capital
def wacc(rf: float, beta_: float, erp: float, pre_tax_kd: float, tax: float, market_cap: float, debt: float) -> dict:
    ke = rf + beta_ * erp
    debt = max(debt, 0.0)
    total = market_cap + debt
    we = market_cap / total if total > 0 else 1.0
    wd = 1 - we
    return {"cost_of_equity": ke, "after_tax_kd": pre_tax_kd * (1 - tax), "we": we, "wd": wd,
            "wacc": we * ke + wd * pre_tax_kd * (1 - tax)}


# --------------------------------------------------------------------------- DCF
@dataclass
class DCFResult:
    projections: pd.DataFrame
    pv_fcf: float
    terminal_value: float
    pv_terminal: float
    enterprise_value: float
    equity_value: float
    per_share: float

    @property
    def terminal_share(self) -> float:
        return self.pv_terminal / self.enterprise_value if self.enterprise_value else float("nan")


def dcf(base_fcf: float, growth: float, terminal_growth: float, discount_rate: float,
        net_debt: float, shares: float, high_growth_years: int = 5, fade_years: int = 5) -> DCFResult:
    """Two-stage free-cash-flow DCF.

    Years 1..high_growth_years grow at `growth`; the next `fade_years` move in a
    straight line from `growth` down to `terminal_growth`; after that a Gordon
    growth terminal value. Equity value = enterprise value - net debt.
    """
    if discount_rate <= terminal_growth + 0.005:
        raise ValueError("The discount rate must be at least 0.5 points above terminal growth.")
    if shares is None or shares <= 0:
        raise ValueError("Shares outstanding must be positive.")

    rows, fcf = [], base_fcf
    total_years = high_growth_years + fade_years
    for year in range(1, total_years + 1):
        if year <= high_growth_years:
            g = growth
        else:
            k = year - high_growth_years
            g = growth + (terminal_growth - growth) * k / fade_years
        fcf *= 1 + g
        factor = (1 + discount_rate) ** -year
        rows.append({"Year": year, "Growth": g, "FCF": fcf, "Discount factor": factor, "PV of FCF": fcf * factor})

    proj = pd.DataFrame(rows)
    pv_fcf = float(proj["PV of FCF"].sum())
    tv = float(proj["FCF"].iloc[-1] * (1 + terminal_growth) / (discount_rate - terminal_growth))
    pv_tv = tv * float(proj["Discount factor"].iloc[-1])
    ev = pv_fcf + pv_tv
    equity = ev - net_debt
    return DCFResult(proj, pv_fcf, tv, pv_tv, ev, equity, equity / shares)


def sensitivity(base_fcf: float, growth: float, net_debt: float, shares: float,
                discount_rates: list[float], terminal_growths: list[float]) -> pd.DataFrame:
    table = {}
    for g_t in terminal_growths:
        col = {}
        for r in discount_rates:
            try:
                col[r] = dcf(base_fcf, growth, g_t, r, net_debt, shares).per_share
            except ValueError:
                col[r] = float("nan")
        table[g_t] = col
    df = pd.DataFrame(table)
    df.index.name = "Discount rate"
    df.columns.name = "Terminal growth"
    return df


def implied_growth(price: float, base_fcf: float, terminal_growth: float, discount_rate: float,
                   net_debt: float, shares: float, low: float = -0.30, high: float = 0.80) -> float | None:
    """Reverse DCF: the 5-year growth rate the current price is pricing in."""
    if base_fcf <= 0:
        return None

    def gap(g: float) -> float:
        return dcf(base_fcf, g, terminal_growth, discount_rate, net_debt, shares).per_share - price

    try:
        f_low, f_high = gap(low), gap(high)
    except ValueError:
        return None
    if f_low * f_high > 0:
        return None
    for _ in range(80):
        mid = (low + high) / 2
        f_mid = gap(mid)
        if abs(f_mid) < 1e-6:
            break
        if f_low * f_mid < 0:
            high = mid
        else:
            low, f_low = mid, f_mid
    return (low + high) / 2


def verdict(intrinsic: float, price: float, band: float = 0.15) -> tuple[str, float]:
    gap = intrinsic / price - 1
    if gap > band:
        return "Looks undervalued", gap
    if gap < -band:
        return "Looks overvalued", gap
    return "Roughly fairly valued", gap


def drawdown_series(close: pd.Series, window: int = TRADING_DAYS) -> pd.Series:
    c = close.iloc[-window:]
    return c / c.cummax() - 1


def default_valuation(f: dict, price: float, beta_: float | None, rf: float,
                      erp: float = 0.05, tax: float = 0.21, terminal_growth: float = 0.025) -> dict | None:
    """Base-case DCF with the app's default assumptions, used for the watchlist at a glance.

    Growth = last five years' revenue CAGR capped at 0-20%; WACC from CAPM with beta clipped to 0.5-2.5,
    cost of debt = risk-free + 1.5 points. Returns None when free cash flow is negative or data is missing.
    """
    import fundamentals  # local import keeps this module free of Streamlit

    if f["fcf"].empty or not f["shares"]:
        return None
    base_fcf = float(f["fcf"].iloc[-1])
    if base_fcf <= 0:
        return None
    hist_g = fundamentals.revenue_cagr(f["revenue"])
    growth = float(np.clip(hist_g if hist_g is not None else 0.05, 0.0, 0.20))
    b = float(np.clip(beta_, 0.5, 2.5)) if beta_ else 1.0
    w = wacc(rf, b, erp, rf + 0.015, tax, price * f["shares"], f["debt"])
    try:
        r = dcf(base_fcf, growth, terminal_growth, w["wacc"], f["net_debt"], f["shares"])
    except ValueError:
        return None
    label, gap = verdict(r.per_share, price)
    return {"per_share": r.per_share, "gap": gap, "label": label, "growth": growth, "wacc": w["wacc"]}


# --------------------------------------------------------------------------- outlook (bootstrap simulation)
DRIFT_CHOICES = {
    "neutral": "No trend: past moves with their average removed",
    "market": "Market average: about +8% a year",
    "trend": "Recent trend: last two years' average, capped at ±30% a year",
}
OUTLOOK_PERCENTILES = (5, 25, 50, 75, 95)
OUTLOOK_LABELS = ("Bad", "Weak", "Middle", "Good", "Very good")


def bootstrap_paths(close: pd.Series, days: int = 126, n: int = 4000, drift: str = "neutral",
                    lookback: int = 504, seed: int = 7) -> np.ndarray | None:
    """Simulated price paths (n × days). Each simulated day replays a real daily move from the last
    `lookback` trading days, so fat tails and crash days are kept; only the average drift is set."""
    r = np.log(close).diff().dropna().iloc[-lookback:].to_numpy()
    if len(r) < 120:
        return None
    mean = r.mean()
    if drift == "market":
        target = np.log(1.08) / TRADING_DAYS
    elif drift == "trend":
        target = float(np.clip(mean, np.log(0.70) / TRADING_DAYS, np.log(1.30) / TRADING_DAYS))
    else:
        target = 0.0
    shocks = r - mean + target
    rng = np.random.default_rng(seed)
    picks = shocks[rng.integers(0, len(shocks), size=(n, days))]
    return float(close.iloc[-1]) * np.exp(np.cumsum(picks, axis=1))


def outlook_summary(paths: np.ndarray, price: float, high_52w: float | None = None,
                    target: float | None = None) -> dict:
    horizons = {"1 month": 21, "3 months": 63, "6 months": min(126, paths.shape[1])}
    table = {h: np.percentile(paths[:, d - 1], OUTLOOK_PERCENTILES) for h, d in horizons.items()}
    final, low, high = paths[:, -1], paths.min(axis=1), paths.max(axis=1)
    probs = {
        "finish_up": float((final > price).mean()),
        "drop_20": float((low <= price * 0.8).mean()),
        "touch_high": None if not high_52w else (1.0 if high_52w <= price else float((high >= high_52w).mean())),
        "touch_target": None if not target else float(((high >= target) if target > price else (low <= target)).mean()),
    }
    fan = np.percentile(paths, OUTLOOK_PERCENTILES, axis=0)
    return {"table": table, "probs": probs, "fan": fan}


# --------------------------------------------------------------------------- comparison
def aligned_returns(closes: dict[str, pd.Series], days: int = TRADING_DAYS) -> pd.DataFrame:
    df = pd.DataFrame(closes).dropna(how="any").iloc[-(days + 1):]
    return df.pct_change().dropna()


def equal_weight_index(closes: dict[str, pd.Series], days: int) -> pd.Series:
    """Equal-weight, daily-rebalanced portfolio, rebased to 1."""
    rets = aligned_returns(closes, days)
    return (1 + rets.mean(axis=1)).cumprod()


# --------------------------------------------------------------------------- analyst consensus
RATING_KEYS = (("strongBuy", 5), ("buy", 4), ("hold", 3), ("sell", 2), ("strongSell", 1))


def consensus(row: dict | None) -> dict | None:
    """Average analyst rating on a 1 (strong sell) to 5 (strong buy) scale, with the usual labels."""
    if not row:
        return None
    n = sum(int(row.get(k, 0) or 0) for k, _ in RATING_KEYS)
    if n == 0:
        return None
    score = sum(int(row.get(k, 0) or 0) * w for k, w in RATING_KEYS) / n
    label = ("Strong Buy" if score >= 4.5 else "Buy" if score >= 3.5 else "Hold" if score >= 2.5
             else "Sell" if score >= 1.5 else "Strong Sell")
    return {"score": score, "label": label, "n": n, "period": str(row.get("period", ""))[:7],
            "counts": {k: int(row.get(k, 0) or 0) for k, _ in RATING_KEYS}}



# --------------------------------------------------------------------------- comparable companies
COMP_MULTIPLES = {  # label: Finnhub "basic financials" keys, first available wins
    "P/E": ("peTTM", "peBasicExclExtraTTM", "peExclExtraTTM"),
    "EV/EBITDA": ("evEbitdaTTM", "enterpriseValueEbitdaTTM", "currentEv/ebitdaTTM"),
    "P/S": ("psTTM", "priceToSalesTTM"),
    "P/FCF": ("pfcfShareTTM", "currentEv/freeCashFlowTTM"),
    "P/B": ("pbQuarterly", "pbAnnual"),
}
COMP_QUALITY = {  # Finnhub reports these in percent
    "Gross margin": ("grossMarginTTM",), "Operating margin": ("operatingMarginTTM",), "Net margin": ("netProfitMarginTTM",),
    "Revenue growth": ("revenueGrowthTTMYoy",), "ROE": ("roeTTM",),
}


def metric_value(met: dict, keys: tuple[str, ...], positive: bool = False) -> float | None:
    for k in keys:
        v = met.get(k)
        if isinstance(v, (int, float)) and not (isinstance(v, float) and math.isnan(v)):
            if positive and v <= 0:
                return None  # a negative multiple is not meaningful (losses)
            return float(v)
    return None


def peer_implied(own: dict, peer_mets: list[dict], price: float) -> dict[str, dict]:
    """Peer median of each multiple and the price it implies: price x (peer median / own multiple)."""
    out = {}
    for label, keys in COMP_MULTIPLES.items():
        vals = [v for v in (metric_value(m, keys, positive=True) for m in peer_mets) if v is not None and v < 500]
        mine = metric_value(own, keys, positive=True)
        if len(vals) >= 3:  # a median of one or two peers says little
            med = float(np.median(vals))
            out[label] = {"median": med, "own": mine, "n": len(vals),
                          "implied": price * med / mine if mine else None}
    return out
