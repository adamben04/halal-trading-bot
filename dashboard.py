import streamlit as st
import os
from datetime import datetime, timedelta
from alpaca.trading.client import TradingClient
from alpaca.data.historical.stock import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
import plotly.graph_objects as go
import plotly.io as pio
import pandas as pd

st.set_page_config(page_title="Trading Bot", layout="wide", initial_sidebar_state="collapsed")

DARK_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    * { font-family: 'Inter', sans-serif !important; }

    .stApp {
        background: linear-gradient(135deg, #0a0a0f 0%, #0d1117 50%, #0a0f1a 100%);
        color: #e6edf3;
    }

    header[data-testid="stHeader"] { background: transparent; }

    .stMetric {
        background: rgba(22, 27, 34, 0.8);
        border: 1px solid rgba(48, 54, 61, 0.6);
        border-radius: 16px;
        padding: 20px 24px;
        backdrop-filter: blur(10px);
        transition: all 0.2s ease;
    }
    .stMetric:hover {
        border-color: rgba(48, 54, 61, 1);
        box-shadow: 0 4px 24px rgba(0, 0, 0, 0.3);
    }
    .stMetric [data-testid="stMetricValue"] {
        font-size: 1.8rem !important;
        font-weight: 700 !important;
        letter-spacing: -0.02em;
    }
    .stMetric [data-testid="stMetricLabel"] {
        font-size: 0.75rem !important;
        font-weight: 500 !important;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #8b949e !important;
    }

    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        letter-spacing: 0.05em;
        text-transform: uppercase;
    }
    .status-open {
        background: rgba(46, 204, 113, 0.15);
        color: #2ecc71;
        border: 1px solid rgba(46, 204, 113, 0.3);
    }
    .status-closed {
        background: rgba(231, 76, 60, 0.15);
        color: #e74c3c;
        border: 1px solid rgba(231, 76, 60, 0.3);
    }
    .status-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        animation: pulse 2s infinite;
    }
    .status-open .status-dot { background: #2ecc71; }
    .status-closed .status-dot { background: #e74c3c; }
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.4; }
    }

    .card {
        background: rgba(22, 27, 34, 0.6);
        border: 1px solid rgba(48, 54, 61, 0.5);
        border-radius: 16px;
        padding: 24px;
        backdrop-filter: blur(10px);
    }

    .section-header {
        font-size: 0.7rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: #8b949e;
        margin-bottom: 16px;
        padding-bottom: 8px;
        border-bottom: 1px solid rgba(48, 54, 61, 0.4);
    }

    .position-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 16px 20px;
        border-radius: 12px;
        background: rgba(22, 27, 34, 0.4);
        border: 1px solid rgba(48, 54, 61, 0.3);
        margin-bottom: 8px;
        transition: all 0.15s ease;
    }
    .position-row:hover {
        background: rgba(22, 27, 34, 0.7);
        border-color: rgba(48, 54, 61, 0.6);
    }

    .pnl-positive { color: #2ecc71 !important; }
    .pnl-negative { color: #e74c3c !important; }

    .logo-text {
        font-size: 1.4rem;
        font-weight: 700;
        letter-spacing: -0.03em;
        background: linear-gradient(135deg, #58a6ff, #2ecc71);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 2px;
    }
    .logo-sub {
        font-size: 0.65rem;
        color: #8b949e;
        text-transform: uppercase;
        letter-spacing: 0.15em;
        font-weight: 500;
    }

    .trade-time {
        font-size: 0.7rem;
        color: #484f58;
    }

    hr { border: none; border-top: 1px solid rgba(48, 54, 61, 0.4); margin: 16px 0; }

    .stDataFrame {
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid rgba(48, 54, 61, 0.4);
    }

    .js-plotly-plot .plotly .modebar { display: none !important; }
</style>
"""

st.markdown(DARK_CSS, unsafe_allow_html=True)

ALPACA_API_KEY = ""
ALPACA_SECRET_KEY = ""

if "ALPACA_API_KEY" in st.secrets:
    ALPACA_API_KEY = st.secrets["ALPACA_API_KEY"]
    ALPACA_SECRET_KEY = st.secrets["ALPACA_SECRET_KEY"]
elif os.environ.get("ALPACA_API_KEY"):
    ALPACA_API_KEY = os.environ["ALPACA_API_KEY"]
    ALPACA_SECRET_KEY = os.environ["ALPACA_SECRET_KEY"]

if not ALPACA_API_KEY or not ALPACA_SECRET_KEY:
    st.error(f"Missing API keys. Secrets found: {list(st.secrets.keys())}")
    st.stop()

trading_client = TradingClient(ALPACA_API_KEY, ALPACA_SECRET_KEY, paper=True)
data_client = StockHistoricalDataClient(ALPACA_API_KEY, ALPACA_SECRET_KEY)

try:
    account = trading_client.get_account()
    clock = trading_client.get_clock()
    positions = trading_client.get_all_positions()
except Exception as e:
    st.error(f"Connection failed: {e}")
    st.stop()

equity = float(account.equity)
cash = float(account.cash)
buying_power = float(account.buying_power)
positions_value = sum(float(p.market_value) for p in positions)
total_pl = sum(float(p.unrealized_pl) for p in positions)
total_pl_pct = (total_pl / positions_value * 100) if positions_value > 0 else 0

col_logo, col_status = st.columns([3, 1])
with col_logo:
    st.markdown('<div class="logo-text">Trading Bot</div>', unsafe_allow_html=True)
    st.markdown('<div class="logo-sub">Paper Trading</div>', unsafe_allow_html=True)
with col_status:
    if clock.is_open:
        st.markdown('<div class="status-badge status-open"><span class="status-dot"></span>Market Open</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="status-badge status-closed"><span class="status-dot"></span>Market Closed</div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Equity", f"${equity:,.2f}", delta=None)
c2.metric("Cash", f"${cash:,.2f}", delta=None)
c3.metric("Positions", f"${positions_value:,.2f}", delta=None)
c4.metric("Unrealized P&L", f"${total_pl:+,.2f}", delta=f"{total_pl_pct:+.1f}%" if positions else None,
          delta_color="normal" if total_pl >= 0 else "inverse")
c5.metric("Buying Power", f"${buying_power:,.2f}", delta=None)

st.markdown("<br>", unsafe_allow_html=True)

if positions:
    st.markdown('<div class="section-header">Open Positions</div>', unsafe_allow_html=True)

    pos_data = []
    for p in positions:
        pl = float(p.unrealized_pl)
        pos_data.append({
            "Symbol": p.symbol,
            "Shares": float(p.qty),
            "Entry": float(p.avg_entry_price),
            "Price": float(p.current_price),
            "Value": float(p.market_value),
            "P&L": pl,
            "P&L %": float(p.unrealized_plpc) * 100,
        })

    df = pd.DataFrame(pos_data)

    for _, row in df.iterrows():
        pl_class = "pnl-positive" if row["P&L"] >= 0 else "pnl-negative"
        arrow = "+" if row["P&L"] >= 0 else ""
        st.markdown(f"""
        <div class="position-row">
            <div style="display:flex;align-items:center;gap:16px;">
                <div style="width:40px;height:40px;border-radius:12px;background:linear-gradient(135deg,rgba(88,166,255,0.15),rgba(46,204,113,0.15));display:flex;align-items:center;justify-content:center;font-weight:700;font-size:0.85rem;color:#58a6ff;">{row["Symbol"][:2]}</div>
                <div>
                    <div style="font-weight:600;font-size:0.95rem;">{row["Symbol"]}</div>
                    <div style="font-size:0.75rem;color:#8b949e;">{row["Shares"]:.0f} shares @ ${row["Entry"]:.2f}</div>
                </div>
            </div>
            <div style="text-align:right;">
                <div style="font-weight:600;font-size:0.95rem;">${row["Value"]:,.2f}</div>
                <div class="{pl_class}" style="font-size:0.8rem;font-weight:600;">{arrow}{row["P&L"]:,.2f} ({arrow}{row["P&L %"]:.1f}%)</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown('<div class="section-header">Portfolio vs SPY (30 Days)</div>', unsafe_allow_html=True)
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
        fig.add_trace(go.Scatter(
            x=spy_dates, y=spy_close, name="SPY",
            line=dict(color="#58a6ff", width=2),
            fill="tozeroy", fillcolor="rgba(88,166,255,0.05)"
        ))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#8b949e", size=11),
            margin=dict(l=0, r=0, t=10, b=0),
            height=280,
            xaxis=dict(gridcolor="rgba(48,54,61,0.3)", showgrid=True, zeroline=False),
            yaxis=dict(gridcolor="rgba(48,54,61,0.3)", showgrid=True, zeroline=False, tickformat="$,.0f"),
            showlegend=False,
            hovermode="x unified",
        )
        st.plotly_chart(fig, use_container_width=True)
    except Exception:
        st.info("Chart unavailable")
else:
    st.markdown('<div class="section-header">Getting Started</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="card">
        <div style="font-size:0.95rem;font-weight:500;color:#e6edf3;margin-bottom:8px;">No open positions yet</div>
        <div style="font-size:0.8rem;color:#8b949e;line-height:1.6;">
            The bot scans 76 Sharia-compliant stocks every 10 minutes during market hours.<br>
            Trades execute when MACD + RSI + Volume + 200SMA align.<br>
            Market opens at <span style="color:#58a6ff;">9:30 AM ET</span>.
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
st.markdown(f"""
<div style="text-align:center;padding:20px 0;">
    <span style="font-size:0.65rem;color:#484f58;letter-spacing:0.1em;text-transform:uppercase;">
        Last updated: {datetime.now().strftime('%I:%M %p ET')} &bull; Paper Trading
    </span>
</div>
""", unsafe_allow_html=True)
