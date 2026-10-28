"""Market Brief: a free markets terminal for US stocks, with Mexico and Argentina on the side.

Run locally with:  streamlit run app.py
"""
from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="Market Brief", page_icon="📈", layout="wide", initial_sidebar_state="collapsed")

from common import current_page, get_watchlist, init_state, ticker_tape, top_bar  # noqa: E402
from ui import inject_css  # noqa: E402
import views_market as vm  # noqa: E402
import views_stock as vs  # noqa: E402

inject_css()
init_state()
top_bar()
wl = get_watchlist()
ticker_tape(wl)

page = current_page()
if page == "Markets":
    vm.page_markets(wl)
elif page == "Map":
    vm.page_map()
elif page == "Watchlist":
    vm.page_watchlist(wl)
elif page == "Compare":
    vm.page_compare(wl)
elif page == "Stock":
    vs.page_stock(wl)
else:
    vm.page_method()

st.html('<p class="mb-foot" style="text-align:center;margin:2rem 0 .5rem">Market Brief · data from Finnhub, Twelve Data, FRED, '
        'SEC EDGAR, CoinGecko and DolarApi · AI text by Google Gemini · for information and learning, not investment advice. '
        '<a href="https://github.com/tomasjtff-cloud/market-brief" target="_blank" rel="noopener">Source code</a></p>')
