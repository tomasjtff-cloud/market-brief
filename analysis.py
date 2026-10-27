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


def beta(close: pd.Series, bench_close: pd.Series, window: int = TRADING_DAYS) -> float | None:
    df = pd.concat([close.pct_change(), bench_close.pct_change()], axis=1, join="inner").dropna().iloc[-window:]
    if len(df) < 60:
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
