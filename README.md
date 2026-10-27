# Market Brief

A personal markets dashboard built in Python. It gives a daily AI-written market brief, a five-stock watchlist, and a one-page analysis for each stock with risk metrics and a discounted cash flow (DCF) valuation that compares intrinsic value with the market price.

Everything runs on free data sources and free hosting.

## What it does

| Page | Content |
|---|---|
| **Today** | Market snapshot (S&P 500, Nasdaq 100, Dow, Russell 2000 via ETFs, gold, oil, Bitcoin, USD/MXN, 10-year Treasury), an AI-written brief of the day's most important stories with links to the sources, and the latest headlines |
| **Watchlist** | Up to five stocks chosen from a search box, with price, daily change, a 6-month chart, returns, volatility and the next earnings date |
| **Stock analysis** | Price chart with a volatility-based range, returns and risk metrics (volatility, max drawdown, beta, Sharpe), reported fundamentals, an interactive DCF with scenarios, a sensitivity table and a reverse DCF, company news, and an AI-written take |
| **Methodology** | How every number is calculated and where it comes from |

## Methodology

**Risk metrics.** Daily closes. Volatility is the annualized standard deviation of daily log returns over one year; beta is the slope of the stock's daily returns on SPY; Sharpe = (1-year return − 10-year Treasury yield) / volatility; max drawdown is the worst peak-to-trough fall in the last year.

**Statistical range.** price × exp(±σ√t), a one-standard-deviation band from trailing volatility. It describes how much a stock tends to move, not its direction, and is labeled as such in the app.

**DCF.** Free cash flow (operating cash flow − capex) is taken from SEC XBRL filings. It grows at a chosen rate for five years, fades linearly to terminal growth over the next five, and a Gordon growth terminal value is added in year 10. The discount rate is WACC: cost of equity from CAPM (10-year Treasury + beta × equity risk premium), after-tax cost of debt, and market-value weights. Equity value = enterprise value − net debt, divided by shares outstanding. Defaults come from the data (historical revenue CAGR, measured beta, live Treasury yield) and every assumption can be changed.

**Scenarios and sensitivity.** Bear and bull cases move growth by ±5 points and the discount rate by ±1 point. A sensitivity table shows value per share across discount rates and terminal growth rates.

**Reverse DCF.** Solves (by bisection) for the five-year growth rate that makes intrinsic value equal the current price, which shows what the market is already pricing in.

**AI guardrails.** Google Gemini writes the brief and the per-stock take. It only receives the headlines and numbers shown in the app and is instructed not to add facts, give recommendations or set price targets. Every story links back to its sources, and output is cached to stay within the free quota.

## Data sources

| Data | Source |
|---|---|
| Quotes, company news, earnings dates, symbol search | Finnhub (free tier) |
| Daily price history, USD/MXN | Twelve Data (free tier) |
| Financial statements | SEC EDGAR XBRL company facts |
| 10-year Treasury yield | FRED, Federal Reserve Bank of St. Louis |
| Bitcoin | CoinGecko |
| Headlines | CNBC, MarketWatch, WSJ Markets and Federal Reserve RSS feeds |

## Tech stack

Python, Streamlit, pandas, NumPy, Plotly, feedparser, Google Gemini API. Hosted on Streamlit Community Cloud. Finance math is unit-tested (`tests/test_analysis.py`).

```
app.py            pages and charts
data.py           all external data sources, with caching
fundamentals.py   SEC XBRL parsing into revenue, FCF, cash, debt, shares
analysis.py       risk metrics, statistical range, WACC, DCF, reverse DCF
ai.py             daily brief and stock take (Gemini)
```

## Run it locally

```bash
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # then add your free API keys
streamlit run app.py
python -m pytest -q                                          # tests
```

## Limitations

Free data plans don't include index or futures levels, so ETFs are used as proxies. SEC tag coverage varies by company; banks, insurers and companies with negative free cash flow aren't suited to this DCF. Nothing in this app is investment advice.
