# Market Brief

A free markets terminal built in Python, styled after Yahoo Finance and Finviz. It covers the US market with Mexico and Argentina on the side: a scrolling ticker tape, a Finviz-style market map, a screener-style watchlist, stock comparison, and a full quote page per stock with financials, a DCF valuation, a 4,000-scenario outlook and an AI-written analysis.

Everything runs on free data sources and free hosting, works on a phone, and the whole interface and the AI text switch between English and Spanish (`?lang=es`).

## What it does

| Page | Content |
|---|---|
| **Markets** | Index cards with day ranges, sector performance (SPDR ETFs), the US Treasury yield curve vs a month ago with 10Y−2Y and 10Y−3M spreads, Mexico and Argentina (EWW, ARGT, USD/MXN, official, MEP and blue dollar), watchlist rail with sparklines, upcoming earnings, an AI morning note with sources and the latest headlines |
| **News** | A news desk: headlines by region (USA, Mexico, Argentina, World) and by sector (tech & AI, energy, mining & metals, banks, health care, consumer, industrials & autos, real estate, crypto) from official publisher RSS feeds, exchange rates (ECB reference rates, Argentina's official, MEP, CCL and blue dollars and country risk) and interest rates, with an AI read and a tone for each region and sector |
| **Map** | The 25 largest US companies as a treemap sized by market value and colored by today's move, plus top gainers, decliners and sectors |
| **Watchlist** | Up to eight stocks in one table: price, returns (1D to 1Y), volatility, beta, max drawdown, 52-week range, 6-month sparkline, P/E, market cap, DCF value, upside and next earnings |
| **Compare** | Up to six stocks rebased to 100 against SPY and an equal-weight portfolio, with return, volatility, Sharpe, drawdown, beta and a correlation heatmap |
| **Stock** | Quote header and key stats; **Summary** (chart 1D to 5Y, key statistics, performance vs S&P 500, analyst ratings, key levels, profile); **Chart** (area or candles, 50/200-day averages, Bollinger bands, RSI, ±1σ range ahead, drawdown); **Financials** (six years from 10-K filings, margins); **Valuation** (interactive DCF, bear/bull, reverse DCF, football field, sensitivity, multiples); **Outlook** (4,000 bootstrap scenarios over 6 months, fan chart, scenario table at 1/3/6 months, probabilities, trend assumption); **Compare**; **News**; **Analysts & AI take** (Wall Street consensus from analyst ratings next to an AI Buy / Hold / Sell lean that uses your DCF assumptions, plus a full written analysis) |
| **Methodology** | How every number is calculated and where it comes from |

## Methodology

**Risk metrics.** Daily closes. Volatility is the annualized standard deviation of daily log returns over one year; beta is the slope of the stock's weekly returns on SPY over two years; Sharpe = (1-year return − 10-year Treasury yield) / volatility; max drawdown is the worst peak-to-trough fall in the last year.

**Statistical range.** price × exp(±σ√t), a one-standard-deviation band from trailing volatility. It describes how much a stock tends to move, not its direction, and is labeled as such in the app.

**DCF.** Free cash flow (operating cash flow − capex) is taken from SEC XBRL filings. It grows at a chosen rate for five years, fades linearly to terminal growth over the next five, and a Gordon growth terminal value is added in year 10. The discount rate is WACC: cost of equity from CAPM (10-year Treasury + beta × equity risk premium), after-tax cost of debt, and market-value weights. Equity value = enterprise value − net debt, divided by shares outstanding. Defaults come from the data (historical revenue CAGR, measured beta, live Treasury yield) and every assumption can be changed.

**Scenarios, sensitivity and football field.** Bear and bull cases move growth by ±5 points and the discount rate by ±1 point. A sensitivity table shows value per share across discount rates and terminal growth rates. A football-field chart puts the DCF scenario range, the sensitivity range, the 52-week trading range and the 3-month statistical range on one axis against the market price.

**Outlook.** 4,000 six-month paths built by resampling the stock's real daily moves from the last two years (bootstrap), so fat tails and crash days keep their real frequency. The average move is replaced by the chosen trend: none, the market average (+8% a year) or the recent trend capped at ±30% a year. The app reports percentiles at 1, 3 and 6 months and the share of paths that end higher, fall 20% at some point, reach the 52-week high or touch the DCF value. These are model probabilities, not forecasts.

**Reverse DCF.** Solves (by bisection) for the five-year growth rate that makes intrinsic value equal the current price, which shows what the market is already pricing in.

**Analyst consensus.** Finnhub's monthly recommendation trends, averaged on a 1 (strong sell) to 5 (strong buy) scale: 4.5+ Strong Buy, 3.5+ Buy, 2.5+ Hold, 1.5+ Sell, below that Strong Sell, with the change versus three months earlier.

**AI guardrails.** Google Gemini writes the brief and the per-stock take. It only receives the headlines and numbers shown in the app and is instructed not to add facts or set price targets. The stock take gives a Buy / Hold / Sell lean with a conviction level, labeled as a model opinion and compared with the Wall Street consensus. Every story links back to its sources, and output is cached to stay within the free quota.

## Data sources

| Data | Source |
|---|---|
| Quotes, company profile, key metrics, analyst ratings, company news, earnings dates, symbol search | Finnhub (free tier) |
| Daily and intraday price history, USD/MXN | Twelve Data (free tier) |
| Financial statements | SEC EDGAR XBRL company facts |
| Treasury yield curve | FRED, Federal Reserve Bank of St. Louis |
| Bitcoin | CoinGecko |
| Argentine dollar rates (official, MEP, blue) | DolarApi |
| Headlines | RSS feeds from CNBC, MarketWatch, WSJ, the Federal Reserve, El Financiero, Expansión, El Economista, Ámbito, Infobae, BBC, DW, Mining.com, TechCrunch, OilPrice and CoinDesk, plus Finnhub news |
| Exchange rates vs the dollar | ECB reference rates via Frankfurter |
| Argentina country risk | ArgentinaDatos |

## Tech stack

Python, Streamlit, pandas, NumPy, Plotly, feedparser, Google Gemini API. Hosted on Streamlit Community Cloud. Finance math is unit-tested (`tests/test_analysis.py`).

```
app.py            router: top bar, ticker tape, pages
common.py         navigation, watchlist state, formatting, top bar and ticker tape
views_market.py   Markets, Map, Watchlist, Compare and Methodology pages
views_stock.py    the stock quote page and its sections
views_news.py     the news desk page
news.py           news feeds by region and the sector keyword classifier
charts.py         Plotly charts (price, fan, treemap, yield curve, football field…)
data.py           all external data sources, with caching and rate limiting
fundamentals.py   SEC XBRL parsing into revenue, FCF, cash, debt, shares
analysis.py       risk metrics, WACC, DCF, reverse DCF, bootstrap outlook, portfolio math
ai.py             daily brief and stock take (Gemini, picks an available model automatically)
ui.py             styles and HTML building blocks
i18n.py           English / Spanish switch (i18n_es.py holds the Spanish strings)
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
