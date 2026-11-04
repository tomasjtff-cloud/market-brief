"""Turn SEC XBRL "company facts" into the handful of numbers a DCF needs.

Companies don't all use the same XBRL tags, and some switched tags over the
years, so each line item has a list of candidate tags. Annual values are taken
from the SEC's calendar "frames" (CY2023, CY2024, ...), which removes the
duplicate values that appear when the same year is repeated in later filings.
"""
from __future__ import annotations

import re

import pandas as pd

ANNUAL_FRAME = re.compile(r"^CY(\d{4})$")
PERIODIC_FORMS = {"10-K", "10-Q", "10-K/A", "10-Q/A"}

REVENUE = [
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "Revenues",
    "SalesRevenueNet",
    "RevenueFromContractWithCustomerIncludingAssessedTax",
]
NET_INCOME = ["NetIncomeLoss", "ProfitLoss"]
GROSS_PROFIT = ["GrossProfit"]
COST_OF_REVENUE = ["CostOfRevenue", "CostOfGoodsAndServicesSold", "CostOfGoodsSold"]
OPERATING_INCOME = ["OperatingIncomeLoss"]
OPERATING_CF = [
    "NetCashProvidedByUsedInOperatingActivities",
    "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
]
CAPEX = [
    "PaymentsToAcquirePropertyPlantAndEquipment",
    "PaymentsToAcquireProductiveAssets",
    "PaymentsForCapitalImprovements",
]
EPS_DILUTED = ["EarningsPerShareDiluted", "EarningsPerShareBasicAndDiluted"]
CASH = ["CashAndCashEquivalentsAtCarryingValue", "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"]
SHORT_INVESTMENTS = ["MarketableSecuritiesCurrent", "ShortTermInvestments", "AvailableForSaleSecuritiesDebtSecuritiesCurrent"]
DEBT_TOTAL = ["LongTermDebt"]
DEBT_NONCURRENT = ["LongTermDebtNoncurrent", "LongTermDebtAndCapitalLeaseObligations"]
DEBT_CURRENT = ["LongTermDebtCurrent", "LongTermDebtAndCapitalLeaseObligationsCurrent"]
SHORT_BORROWINGS = ["CommercialPaper", "ShortTermBorrowings"]

# Statement-analysis lines (balance sheet at each fiscal year end, plus a few income and cash-flow items).
ASSETS = ["Assets"]
ASSETS_CURRENT = ["AssetsCurrent"]
LIABILITIES_CURRENT = ["LiabilitiesCurrent"]
INVENTORY = ["InventoryNet"]
RECEIVABLES = ["AccountsReceivableNetCurrent", "ReceivablesNetCurrent"]
EQUITY = ["StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"]
INTEREST = ["InterestExpense", "InterestExpenseNonoperating", "InterestExpenseDebt"]
DEPRECIATION = ["DepreciationDepletionAndAmortization", "DepreciationAndAmortization", "DepreciationAmortizationAndAccretionNet",
                "Depreciation"]
STOCK_COMP = ["ShareBasedCompensation", "AllocatedShareBasedCompensationExpense"]
INCOME_TAX = ["IncomeTaxExpenseBenefit"]
PRETAX_INCOME = ["IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
                 "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments"]
QUARTER_FRAME = re.compile(r"^CY(\d{4})Q([1-4])$")


def annual_series(facts: dict, tags: list[str], unit: str = "USD") -> pd.Series:
    """Yearly values (index = year). The most up-to-date tag wins; older tags fill gaps."""
    gaap = facts.get("facts", {}).get("us-gaap", {})
    found = []
    for tag in tags:
        vals = {}
        for row in gaap.get(tag, {}).get("units", {}).get(unit, []):
            m = ANNUAL_FRAME.match(row.get("frame") or "")
            if m:
                vals[int(m.group(1))] = float(row["val"])
        if vals:
            found.append(pd.Series(vals, dtype=float).sort_index())
    if not found:
        return pd.Series(dtype=float)
    found.sort(key=lambda s: s.index.max(), reverse=True)
    combined = found[0]
    for s in found[1:]:
        combined = combined.combine_first(s)
    return combined.sort_index()


def annual_ends(facts: dict, tags: list[str]) -> dict[int, str]:
    """Fiscal year-end date behind each calendar-aligned annual value, so balance sheets line up with the income statement."""
    gaap = facts.get("facts", {}).get("us-gaap", {})
    ends: dict[int, str] = {}
    for tag in tags:
        for row in gaap.get(tag, {}).get("units", {}).get("USD", []):
            m = ANNUAL_FRAME.match(row.get("frame") or "")
            if m and int(m.group(1)) not in ends and row.get("end"):
                ends[int(m.group(1))] = row["end"]
    return ends


def instant_series(facts: dict, tags: list[str], ends: dict[int, str], unit: str = "USD") -> pd.Series:
    """Balance-sheet value at each fiscal year end (index = the same year as the annual flows)."""
    gaap = facts.get("facts", {}).get("us-gaap", {})
    out: dict[int, float] = {}
    for tag in tags:
        by_end: dict[str, tuple[str, float]] = {}
        for row in gaap.get(tag, {}).get("units", {}).get(unit, []):
            e = row.get("end")
            if e and ("start" not in row) and (e not in by_end or (row.get("filed") or "") > by_end[e][0]):
                by_end[e] = (row.get("filed") or "", float(row["val"]))
        for year, end in ends.items():
            if year not in out and end in by_end:
                out[year] = by_end[end][1]
    return pd.Series(out, dtype=float).sort_index()


def quarterly_series(facts: dict, tags: list[str], unit: str = "USD", derive_q4: bool = True) -> pd.DataFrame:
    """Quarterly values (three-month periods) with their period end, from the SEC's quarterly frames.
    There is no 10-Q for a company's fourth fiscal quarter, so for flows it is derived as the fiscal year minus the
    three quarters inside it, whichever calendar quarter that falls in."""
    gaap = facts.get("facts", {}).get("us-gaap", {})
    quarters: dict[str, dict] = {}
    annual: list[dict] = []
    for tag in tags:
        for row in gaap.get(tag, {}).get("units", {}).get(unit, []):
            fr = row.get("frame") or ""
            if QUARTER_FRAME.match(fr) and row.get("end") and row["end"] not in quarters:
                quarters[row["end"]] = {"start": row.get("start", ""), "end": row["end"], "value": float(row["val"]), "derived": False}
            elif ANNUAL_FRAME.match(fr) and row.get("start") and row.get("end"):
                annual.append({"start": row["start"], "end": row["end"], "value": float(row["val"])})
    if derive_q4:
        seen = set()
        for a in sorted(annual, key=lambda r: r["end"], reverse=True):
            if a["end"] in seen or a["end"] in quarters:
                continue
            seen.add(a["end"])
            inside = [q for q in quarters.values() if not q["derived"] and q["start"] >= a["start"] and q["end"] <= a["end"]]
            if len(inside) == 3:
                quarters[a["end"]] = {"start": max(q["end"] for q in inside), "end": a["end"],
                                      "value": a["value"] - sum(q["value"] for q in inside), "derived": True}
    df = pd.DataFrame(sorted(quarters.values(), key=lambda r: r["end"]), columns=["start", "end", "value", "derived"])
    return df.reset_index(drop=True)


def latest_instant(facts: dict, tags: list[str], unit: str = "USD") -> dict | None:
    """Most recent balance-sheet value reported in a 10-K or 10-Q."""
    gaap = facts.get("facts", {}).get("us-gaap", {})
    best = None
    for tag in tags:
        rows = [r for r in gaap.get(tag, {}).get("units", {}).get(unit, []) if r.get("form") in PERIODIC_FORMS]
        if not rows:
            continue
        r = max(rows, key=lambda r: (r.get("end", ""), r.get("filed", "")))
        if best is None or r["end"] > best["end"]:
            best = {"val": float(r["val"]), "end": r["end"], "tag": tag}
    return best


def shares_outstanding(facts: dict) -> dict | None:
    rows = facts.get("facts", {}).get("dei", {}).get("EntityCommonStockSharesOutstanding", {}).get("units", {}).get("shares", [])
    if rows:
        latest = max(rows, key=lambda r: (r.get("filed", ""), r.get("end", "")))
        # Companies with several share classes (e.g. Alphabet) report one row per class.
        same = [r for r in rows if r.get("accn") == latest.get("accn") and r.get("end") == latest.get("end")]
        return {"val": float(sum(r["val"] for r in same)), "end": latest["end"], "source": "cover page of latest filing"}
    diluted = annual_series(facts, ["WeightedAverageNumberOfDilutedSharesOutstanding"], unit="shares")
    if not diluted.empty:
        return {"val": float(diluted.iloc[-1]), "end": str(diluted.index[-1]), "source": "diluted weighted average"}
    return None


def _fresh(item: dict | None, reference_end: str | None, max_days: int = 400) -> dict | None:
    """Ignore tags the company stopped reporting long ago."""
    if not item or not reference_end:
        return item
    gap = (pd.Timestamp(reference_end) - pd.Timestamp(item["end"])).days
    return item if gap <= max_days else None


def build(facts: dict) -> dict:
    notes: list[str] = []

    revenue = annual_series(facts, REVENUE)
    net_income = annual_series(facts, NET_INCOME)
    operating_income = annual_series(facts, OPERATING_INCOME)
    gross_profit = annual_series(facts, GROSS_PROFIT)
    if gross_profit.empty and not revenue.empty:
        cost = annual_series(facts, COST_OF_REVENUE)
        if not cost.empty:
            gross_profit = (revenue - cost.reindex(revenue.index)).dropna()
    ocf = annual_series(facts, OPERATING_CF)
    capex = annual_series(facts, CAPEX)
    eps = annual_series(facts, EPS_DILUTED, unit="USD/shares")

    if ocf.empty:
        fcf = pd.Series(dtype=float)
        notes.append("Operating cash flow not found in SEC filings, so free cash flow can't be computed.")
    else:
        if capex.empty:
            notes.append("Capital expenditures not found; free cash flow shown equals operating cash flow.")
        fcf = (ocf - capex.reindex(ocf.index).fillna(0.0)).dropna()

    cash = latest_instant(facts, CASH)
    reference_end = cash["end"] if cash else None
    st_inv = _fresh(latest_instant(facts, SHORT_INVESTMENTS), reference_end)

    total_debt = _fresh(latest_instant(facts, DEBT_TOTAL), reference_end)
    if total_debt:
        debt_parts = [total_debt]
    else:
        debt_parts = [
            d for d in (
                _fresh(latest_instant(facts, DEBT_NONCURRENT), reference_end),
                _fresh(latest_instant(facts, DEBT_CURRENT), reference_end),
            ) if d
        ]
    short_borrow = _fresh(latest_instant(facts, SHORT_BORROWINGS), reference_end)
    if short_borrow:
        debt_parts.append(short_borrow)

    cash_total = (cash["val"] if cash else 0.0) + (st_inv["val"] if st_inv else 0.0)
    debt_total = sum(d["val"] for d in debt_parts)
    if not cash:
        notes.append("Cash not found in SEC filings; assumed zero.")
    if not debt_parts:
        notes.append("No debt found in SEC filings; assumed zero (check the 10-K if this looks wrong).")

    shares = shares_outstanding(facts)
    if not shares:
        notes.append("Shares outstanding not found.")

    ends = annual_ends(facts, REVENUE + NET_INCOME)
    debt_hist = instant_series(facts, DEBT_TOTAL, ends)
    if debt_hist.empty:
        debt_hist = instant_series(facts, DEBT_NONCURRENT, ends).add(instant_series(facts, DEBT_CURRENT, ends), fill_value=0.0)
    debt_hist = debt_hist.add(instant_series(facts, SHORT_BORROWINGS, ends), fill_value=0.0)
    balance = {
        "assets": instant_series(facts, ASSETS, ends), "assets_current": instant_series(facts, ASSETS_CURRENT, ends),
        "liabilities_current": instant_series(facts, LIABILITIES_CURRENT, ends), "inventory": instant_series(facts, INVENTORY, ends),
        "receivables": instant_series(facts, RECEIVABLES, ends), "equity": instant_series(facts, EQUITY, ends),
        "cash": instant_series(facts, CASH, ends).add(instant_series(facts, SHORT_INVESTMENTS, ends), fill_value=0.0),
        "debt": debt_hist,
    }
    extra = {"interest": annual_series(facts, INTEREST), "depreciation": annual_series(facts, DEPRECIATION),
             "stock_comp": annual_series(facts, STOCK_COMP), "income_tax": annual_series(facts, INCOME_TAX),
             "pretax_income": annual_series(facts, PRETAX_INCOME)}
    quarters = {"revenue": quarterly_series(facts, REVENUE), "net_income": quarterly_series(facts, NET_INCOME),
                "operating_income": quarterly_series(facts, OPERATING_INCOME), "gross_profit": quarterly_series(facts, GROSS_PROFIT),
                "eps": quarterly_series(facts, EPS_DILUTED, unit="USD/shares", derive_q4=False)}

    keep = lambda s: s[s.index >= (s.index.max() - 9)] if not s.empty else s  # noqa: E731
    return {
        "balance": {k: keep(v) for k, v in balance.items()},
        **{k: keep(v) for k, v in extra.items()},
        "year_ends": ends,
        "quarters": {k: v.tail(12).reset_index(drop=True) for k, v in quarters.items()},
        "name": facts.get("entityName", ""),
        "revenue": keep(revenue),
        "net_income": keep(net_income),
        "gross_profit": keep(gross_profit),
        "operating_income": keep(operating_income),
        "ocf": keep(ocf),
        "capex": keep(capex),
        "fcf": keep(fcf),
        "eps": keep(eps),
        "cash": cash_total,
        "debt": debt_total,
        "net_debt": debt_total - cash_total,
        "balance_sheet_date": reference_end,
        "shares": shares["val"] if shares else None,
        "shares_source": shares["source"] if shares else None,
        "notes": notes,
    }


def revenue_cagr(revenue: pd.Series, years: int = 5) -> float | None:
    s = revenue.dropna()
    s = s[s > 0]
    if len(s) < 3:
        return None
    s = s.iloc[-(years + 1):]
    n = s.index[-1] - s.index[0]
    if n <= 0:
        return None
    return (s.iloc[-1] / s.iloc[0]) ** (1 / n) - 1
