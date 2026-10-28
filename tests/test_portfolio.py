import numpy as np
import pandas as pd
import pytest

import portfolio as pf


def tx(**k):
    return pf.clean_transaction({"date": "2025-01-02", **k})


def test_positions_average_cost_and_cash():
    txs = [tx(type="deposit", amount=1000), tx(type="buy", ticker="aapl", shares=5, price=100, fee=1),
           tx(type="buy", ticker="AAPL", shares=5, price=120, date="2025-02-01"),
           tx(type="sell", ticker="AAPL", shares=4, price=150, date="2025-03-01"),
           tx(type="dividend", ticker="AAPL", amount=10, date="2025-03-05")]
    p = pf.positions(txs)
    h = p["holdings"]["AAPL"]
    assert h["shares"] == 6
    avg = (501 + 600) / 10
    assert h["avg_cost"] == pytest.approx(avg)
    assert p["realized"] == pytest.approx(4 * 150 - 4 * avg)
    # 1000 deposit, 501 spent, then 600 more: 499 from cash + 101 new money
    assert p["contributed"] == pytest.approx(1101)
    assert p["cash"] == pytest.approx(600 + 10)


def test_oversell_is_capped_and_flagged():
    p = pf.positions([tx(type="buy", ticker="X", shares=1, price=10), tx(type="sell", ticker="X", shares=3, price=10)])
    assert "X" not in p["holdings"] and p["problems"]


def test_clean_book_drops_bad_rows():
    book, problems = pf.clean_book({"transactions": [{"type": "buy", "date": "2025-01-01", "ticker": "", "shares": 1, "price": 1},
                                                     {"type": "deposit", "date": "2025-01-01", "amount": 5}]})
    assert len(book["transactions"]) == 1 and len(problems) == 1


def _prices(n=600, seed=1):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2023-01-02", periods=n)
    a = 100 * np.exp(np.cumsum(rng.normal(0.0005, 0.02, n)))
    b = 50 * np.exp(np.cumsum(rng.normal(0.0002, 0.01, n)))
    m = 400 * np.exp(np.cumsum(rng.normal(0.0003, 0.011, n)))
    return {"A": pd.Series(a, idx), "B": pd.Series(b, idx), "SPY": pd.Series(m, idx)}


def test_value_history_twr_ignores_deposits():
    c = _prices()
    d0 = c["A"].index[10].date().isoformat()
    d1 = c["A"].index[300].date().isoformat()
    txs = [tx(type="buy", ticker="A", shares=10, price=float(c["A"].iloc[10]), date=d0),
           tx(type="deposit", amount=5000, date=d1)]
    h = pf.value_history(txs, {"A": c["A"]})
    # before the deposit the time-weighted index follows A's price exactly
    assert h["twr_index"].iloc[289] == pytest.approx(c["A"].iloc[299] / c["A"].iloc[10], rel=1e-6)
    # the deposit itself is not a return: on that day the index moves only with A's holding
    day = h.index.get_loc(c["A"].index[300])
    r = h["twr_index"].iloc[day] / h["twr_index"].iloc[day - 1] - 1
    hold_r = h["holdings"].iloc[day] / h["holdings"].iloc[day - 1] - 1
    assert r == pytest.approx(hold_r, rel=1e-9)


def test_risk_report_and_contributions_sum_to_one():
    c = _prices()
    rets = pf.returns_matrix({k: c[k] for k in ("A", "B")})
    r = pf.risk_report(rets, {"A": 0.6, "B": 0.3, pf.CASH: 0.1}, 10000, 0.04, bench=c["SPY"])
    assert r["vol"] > 0 and r["var95_1d"] > 0 and r["cvar95_1d"] >= r["var95_1d"]
    assert sum(r["risk_contrib"].values()) == pytest.approx(1.0)
    assert r["beta"] is not None


def test_profile_lower_of_willingness_and_capacity():
    p = pf.investor_profile({"goal": 5, "drop": 5, "style": 5, "horizon": 1, "loss": 1, "liquidity": 1})
    assert p["name"] == "Conservative" and p["limited_by"] == "capacity"
    q = pf.investor_profile({k: 4 for k in pf.QUESTIONS})
    assert q["name"] == "Growth"


def test_optimiser_respects_caps_and_target_vol():
    c = _prices()
    rets = pf.returns_matrix({k: c[k] for k in ("A", "B")})
    cov = pf.ledoit_wolf(rets)
    mu = pf.capm_returns(rets, c["SPY"], 0.04)
    mu2, cov2 = pf.with_cash(mu, cov, 0.04)
    out = pf.optimise(mu2, cov2, 0.04, {"A": 0.5, "B": 0.5, pf.CASH: 1.0}, target_vol=0.08)
    for key in ("gmv", "max_sharpe", "profile"):
        w = out[key]["weights"]
        assert sum(w.values()) == pytest.approx(1.0, abs=1e-6)
        assert w.get("A", 0) <= 0.5 + 1e-6
    assert out["profile"]["vol"] <= 0.08 + 1e-4
    assert out["gmv"]["vol"] <= out["max_sharpe"]["vol"] + 1e-9
    assert len(out["frontier"]) > 5


def test_shift_weights():
    w = pf.shift_weights({"A": 0.5, "B": 0.5}, "A", 0.3)
    assert w["A"] == pytest.approx(0.3) and w[pf.CASH] == pytest.approx(0.2)
