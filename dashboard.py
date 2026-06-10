import streamlit as st
import os
from datetime import datetime, timedelta
from alpaca.trading.client import TradingClient
from alpaca.data.historical.stock import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
import plotly.graph_objects as go
import pandas as pd

st.set_page_config(page_title="Halal Trading Bot", layout="wide")

ALPACA_API_KEY = os.environ.get("ALPACA_API_KEY", "")
ALPACA_SECRET_KEY = os.environ.get("ALPACA_SECRET_KEY", "")

if not ALPACA_API_KEY or not ALPACA_SECRET_KEY:
    st.error("Missing ALPACA_API_KEY or ALPACA_SECRET_KEY secrets")
    st.stop()

trading_client = TradingClient(ALPACA_API_KEY, ALPACA_SECRET_KEY, paper=True)
data_client = StockHistoricalDataClient(ALPACA_API_KEY, ALPACA_SECRET_KEY)

st.title("Halal Trading Bot")

try:
    account = trading_client.get_account()
    clock = trading_client.get_clock()
    positions = trading_client.get_all_positions()
except Exception as e:
    st.error(f"Alpaca connection failed: {e}")
    st.stop()

market_status = "OPEN" if clock.is_open else "CLOSED"
next_open = clock.next_open.strftime("%I:%M %p ET") if clock.next_open else "N/A"

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Equity", f"${float(account.equity):,.2f}")
col2.metric("Cash", f"${float(account.cash):,.2f}")
col3.metric("Buying Power", f"${float(account.buying_power):,.2f}")
col4.metric("Market", market_status)
col5.metric("Next Open", next_open)

st.divider()

if positions:
    st.subheader(f"Open Positions ({len(positions)})")
    rows = []
    for p in positions:
        rows.append({
            "Symbol": p.symbol,
            "Qty": float(p.qty),
            "Entry": f"${float(p.avg_entry_price):.2f}",
            "Current": f"${float(p.current_price):.2f}",
            "Mkt Value": f"${float(p.market_value):,.2f}",
            "P&L": f"${float(p.unrealized_pl):+,.2f}",
            "P&L %": f"{float(p.unrealized_plpc)*100:+.2f}%",
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True)

    st.subheader("Equity Chart (30d)")
    try:
        bars_req = StockBarsRequest(
            symbol_or_symbols=["SPY"],
            timeframe=TimeFrame.Day,
            start=datetime.now() - timedelta(days=30),
        )
        spy_bars = data_client.get_stock_bars(bars_req)["SPY"]
        spy_dates = [b.timestamp.date() for b in spy_bars]
        spy_close = [b.close for b in spy_bars]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=spy_dates, y=spy_close, name="SPY"))
        fig.update_layout(height=300, margin=dict(t=10))
        st.plotly_chart(fig, use_container_width=True)
    except Exception:
        st.info("Could not load SPY chart")
else:
    st.info("No open positions yet. Bot will trade when market opens at 9:30 AM ET.")

st.divider()
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Paper Trading")
