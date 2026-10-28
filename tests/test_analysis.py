"""Unit tests for the finance math. Run with:  python -m pytest -q"""
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import analysis  # noqa: E402
import fundamentals  # noqa: E402


def test_dcf_matches_hand_calculation():
    # No growth anywhere: value = FCF/r for the perpetuity, built up from 10 years + terminal value.
    r = analysis.dcf(base_fcf=100, growth=0.0, terminal_growth=0.0, discount_rate=0.10, net_debt=0, shares=10)
    assert r.enterprise_value == pytest.approx(1000, rel=1e-9)
    assert r.per_share == pytest.approx(100, rel=1e-9)


def test_dcf_terminal_value_and_net_debt():
    r = analysis.dcf(100, 0.05, 0.02, 0.09, net_debt=200, shares=4)
    last = r.projections["FCF"].iloc[-1]
    assert r.terminal_value == pytest.approx(last * 1.02 / 0.07)
    assert r.equity_value == pytest.approx(r.enterprise_value - 200)
    assert r.per_share == pytest.approx(r.equity_value / 4)
    # growth fades linearly to terminal growth in year 10
    assert r.projections["Growth"].iloc[4] == pytest.approx(0.05)
    assert r.projections["Growth"].iloc[-1] == pytest.approx(0.02)


def test_dcf_rejects_bad_inputs():
    with pytest.raises(ValueError):
        analysis.dcf(100, 0.05, 0.03, 0.032, 0, 10)
    with pytest.raises(ValueError):
        analysis.dcf(100, 0.05, 0.02, 0.09, 0, 0)


def test_reverse_dcf_recovers_growth():
    true_g = 0.12
    price = analysis.dcf(500, true_g, 0.025, 0.09, 1000, 50).per_share
    g = analysis.implied_growth(price, 500, 0.025, 0.09, 1000, 50)
    assert g == pytest.approx(true_g, abs=1e-6)


def test_sensitivity_shape_and_monotonic():
    t = analysis.sensitivity(100, 0.05, 0, 10, [0.08, 0.09, 0.10], [0.02, 0.025])
    assert t.shape == (3, 2)
    assert (t[0.02].diff().dropna() < 0).all()  # higher discount rate -> lower value


def test_wacc_weights():
    w = analysis.wacc(rf=0.04, beta_=1.2, erp=0.05, pre_tax_kd=0.05, tax=0.21, market_cap=800, debt=200)
    assert w["cost_of_equity"] == pytest.approx(0.10)
    assert w["wacc"] == pytest.approx(0.8 * 0.10 + 0.2 * 0.05 * 0.79)


def _prices(n=300, seed=1, drift=0.0005, vol=0.02):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2025-01-02", periods=n)
    return pd.Series(100 * np.exp(np.cumsum(rng.normal(drift, vol, n))), index=idx)


def test_risk_metrics():
    bench = _prices(seed=2)
    stock = bench * 1.0  # identical series -> beta 1
    m = analysis.risk_metrics(stock, bench, rf=0.04)
    assert m["beta"] == pytest.approx(1.0)
    assert 0.2 < m["volatility"] < 0.45  # 2% daily ~ 32% annual
    assert m["max_drawdown"] <= 0


def test_statistical_range_symmetric_in_logs():
    lo, hi = analysis.statistical_range(100, 0.30, 252)
    assert math.log(hi / 100) == pytest.approx(0.30)
    assert math.log(100 / lo) == pytest.approx(0.30)


def test_fundamentals_from_sec_facts():
    def flow(vals, tag_unit="USD"):
        return {"units": {tag_unit: [{"val": v, "frame": f"CY{y}", "form": "10-K", "end": f"{y}-12-31"} for y, v in vals.items()]}}

    facts = {
        "entityName": "Test Co",
        "facts": {
            "dei": {"EntityCommonStockSharesOutstanding": {"units": {"shares": [
                {"val": 600, "end": "2025-01-20", "accn": "a1", "filed": "2025-02-01"},
                {"val": 400, "end": "2025-01-20", "accn": "a1", "filed": "2025-02-01"},
                {"val": 900, "end": "2024-01-20", "accn": "a0", "filed": "2024-02-01"},
            ]}}},
            "us-gaap": {
                "Revenues": flow({2015: 50, 2016: 60}),  # old tag, stopped being used
                "RevenueFromContractWithCustomerExcludingAssessedTax": flow({2022: 100, 2023: 110, 2024: 121}),
                "NetCashProvidedByUsedInOperatingActivities": flow({2023: 30, 2024: 40}),
                "PaymentsToAcquirePropertyPlantAndEquipment": flow({2023: 10, 2024: 15}),
                "CashAndCashEquivalentsAtCarryingValue": {"units": {"USD": [
                    {"val": 20, "end": "2024-12-31", "form": "10-K", "filed": "2025-02-01"}]}},
                "LongTermDebt": {"units": {"USD": [
                    {"val": 50, "end": "2024-12-31", "form": "10-K", "filed": "2025-02-01"}]}},
                "CommercialPaper": {"units": {"USD": [  # stale: last reported long ago -> ignored
                    {"val": 99, "end": "2019-12-31", "form": "10-K", "filed": "2020-02-01"}]}},
            },
        },
    }
    f = fundamentals.build(facts)
    assert f["revenue"].loc[2024] == 121 and f["revenue"].loc[2016] == 60
    assert f["fcf"].loc[2024] == 25
    assert f["shares"] == 1000  # two share classes summed from the latest filing
    assert f["debt"] == 50 and f["cash"] == 20 and f["net_debt"] == 30
    assert fundamentals.revenue_cagr(f["revenue"].loc[2022:]) == pytest.approx(0.10)


def test_bootstrap_outlook():
    close = _prices(n=600, seed=3)
    paths = analysis.bootstrap_paths(close, days=126, n=2000, drift="neutral", seed=1)
    assert paths.shape == (2000, 126)
    again = analysis.bootstrap_paths(close, days=126, n=2000, drift="neutral", seed=1)
    assert np.allclose(paths, again)  # reproducible
    price = float(close.iloc[-1])
    out = analysis.outlook_summary(paths, price, high_52w=price * 1.2, target=price * 0.9)
    lo, med, hi = out["table"]["6 months"][[0, 2, 4]]
    assert lo < med < hi
    assert abs(np.log(np.median(paths[:, -1]) / price)) < 0.05  # no drift: median near today
    for v in out["probs"].values():
        assert 0 <= v <= 1
    up = analysis.bootstrap_paths(close, days=126, n=2000, drift="market", seed=1)
    assert np.median(up[:, -1]) > np.median(paths[:, -1])


def test_equal_weight_index():
    a, b = _prices(seed=4), _prices(seed=5)
    idx = analysis.equal_weight_index({"A": a, "B": b}, 100)
    assert len(idx) == 100 and idx.iloc[0] > 0


def test_consensus():
    c = analysis.consensus({"period": "2026-10-01", "strongBuy": 11, "buy": 20, "hold": 14, "sell": 3, "strongSell": 1})
    assert c["n"] == 49 and c["label"] == "Buy" and abs(c["score"] - 184 / 49) < 1e-9
    assert analysis.consensus({"hold": 0}) is None
    assert analysis.consensus({"strongSell": 3})["label"] == "Strong Sell"


def test_news_classify():
    import news
    assert "Tech & AI" in news.classify("Nvidia unveils new AI chips")
    assert "Energy" in news.classify("Precio del petróleo sube por tensiones en Medio Oriente")
    assert "Mining & metals" in news.classify("Codelco, BHP launch $40M copper hunt in northern Chile")
    assert "Crypto" in news.classify("Bitcoin falls below $80,000")
    assert news.classify("Said the chair in a speech") == []
    assert "Tech & AI" not in news.classify("Paid leave plan advances")  # 'AI' must be the acronym, not part of a word
