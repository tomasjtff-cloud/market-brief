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


def test_peer_implied_and_parse():
    own = {"peTTM": 30, "psTTM": 8, "evEbitdaTTM": -5}
    peers = [{"peTTM": 20, "psTTM": 4, "evEbitdaTTM": 12}, {"peTTM": 25, "psTTM": 6, "evEbitdaTTM": 14},
             {"peTTM": 22, "psTTM": 5, "evEbitdaTTM": 13}, {"peTTM": -3}]
    out = analysis.peer_implied(own, peers, 300)
    assert out["P/E"]["median"] == 22 and abs(out["P/E"]["implied"] - 300 * 22 / 30) < 1e-9
    assert out["EV/EBITDA"]["implied"] is None  # own multiple negative: not meaningful


def _facts():
    def flow(tag, vals):  # vals: list of (frame, start, end, val)
        return {tag: {"units": {"USD": [{"frame": f, "start": s, "end": e, "val": v, "form": "10-K", "filed": "2026-01-01"} for f, s, e, v in vals]}}}
    def inst(tag, vals):
        return {tag: {"units": {"USD": [{"end": e, "val": v, "form": "10-K", "filed": "2026-01-01"} for e, v in vals]}}}
    g = {}
    # fiscal year ends in September, like Apple: annual frame CY2025 = Oct 2024 - Sep 2025
    g.update(flow("Revenues", [("CY2024", "2023-10-01", "2024-09-30", 400.0), ("CY2025", "2024-10-01", "2025-09-30", 440.0),
                               ("CY2024Q4", "2024-10-01", "2024-12-31", 120.0), ("CY2025Q1", "2025-01-01", "2025-03-31", 100.0),
                               ("CY2025Q2", "2025-04-01", "2025-06-30", 105.0)]))
    g.update(flow("NetIncomeLoss", [("CY2024", "2023-10-01", "2024-09-30", 40.0), ("CY2025", "2024-10-01", "2025-09-30", 50.0)]))
    g.update(flow("OperatingIncomeLoss", [("CY2024", "2023-10-01", "2024-09-30", 60.0), ("CY2025", "2024-10-01", "2025-09-30", 70.0)]))
    g.update(flow("GrossProfit", [("CY2024", "2023-10-01", "2024-09-30", 160.0), ("CY2025", "2024-10-01", "2025-09-30", 180.0)]))
    g.update(flow("NetCashProvidedByUsedInOperatingActivities", [("CY2024", "2023-10-01", "2024-09-30", 55.0), ("CY2025", "2024-10-01", "2025-09-30", 45.0)]))
    g.update(flow("InterestExpense", [("CY2025", "2024-10-01", "2025-09-30", 7.0)]))
    g.update(inst("Assets", [("2024-09-30", 500.0), ("2025-09-30", 540.0), ("2023-12-31", 1.0)]))
    g.update(inst("StockholdersEquity", [("2024-09-30", 200.0), ("2025-09-30", 220.0)]))
    g.update(inst("AssetsCurrent", [("2025-09-30", 150.0)]))
    g.update(inst("LiabilitiesCurrent", [("2025-09-30", 100.0)]))
    g.update(inst("LongTermDebt", [("2024-09-30", 80.0), ("2025-09-30", 60.0)]))
    return {"entityName": "Test", "facts": {"us-gaap": g, "dei": {}}}


def test_fundamentals_balance_and_quarters():
    import fundamentals
    f = fundamentals.build(_facts())
    assert f["balance"]["assets"].to_dict() == {2024: 500.0, 2025: 540.0}
    q = f["quarters"]["revenue"]
    assert list(q["end"]) == ["2024-12-31", "2025-03-31", "2025-06-30", "2025-09-30"]
    last = q.iloc[-1]
    assert last["derived"] and last["value"] == 440 - 120 - 100 - 105
    r = analysis.statement_analysis(f)
    assert r.loc["revenue_growth", 2025] == pytest.approx(0.1)
    assert r.loc["roe", 2025] == pytest.approx(50 / 210)
    assert r.loc["current_ratio", 2025] == pytest.approx(1.5)
    assert r.loc["interest_coverage", 2025] == pytest.approx(10.0)
    assert r.loc["roe", 2025] == pytest.approx(r.loc["net_margin", 2025] * r.loc["asset_turnover", 2025] * r.loc["equity_multiplier", 2025])
    e = analysis.eva(f, 0.09, tax=0.2)
    assert e.loc[2025, "nopat"] == pytest.approx(56.0) and e.loc[2025, "capital"] == pytest.approx((280 + 280) / 2)
    assert e.loc[2025, "eva"] == pytest.approx(56 - 0.09 * 280)
    checks = analysis.health_checks(r)
    assert any("cash flow" in m for _, m, _ in checks)


def test_capture_tails_and_reaction():
    idx = pd.bdate_range("2024-01-01", periods=520)
    rng = np.random.default_rng(3)
    b = pd.Series(100 * np.cumprod(1 + rng.normal(0.0004, 0.01, len(idx))), index=idx)
    s = b ** 1.0  # identical to the benchmark
    ca = analysis.capture_alpha(s, b, 0.04)
    assert ca["up_capture"] == pytest.approx(1.0) and ca["down_capture"] == pytest.approx(1.0) and abs(ca["alpha"]) < 1e-9
    t = analysis.tail_stats(b)
    assert t["es95"] >= t["var95"] > 0 and t["var99"] >= t["var95"]
    px = pd.Series([10.0, 11.0, 12.0], index=pd.to_datetime(["2026-01-05", "2026-01-06", "2026-01-07"]))
    assert analysis.earnings_reaction(px, "2026-01-06", "bmo") == pytest.approx(0.1)
    assert analysis.earnings_reaction(px, "2026-01-06", "amc") == pytest.approx(12 / 11 - 1)
