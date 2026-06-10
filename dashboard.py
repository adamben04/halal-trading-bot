import streamlit as st
import os
from datetime import datetime, timedelta
from alpaca.trading.client import TradingClient
from alpaca.data.historical.stock import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
import plotly.graph_objects as go
import pandas as pd

st.set_page_config(page_title="Trading Bot", layout="wide", initial_sidebar_state="collapsed")

ROBINHOOD_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
        -webkit-font-smoothing: antialiased;
    }

    /* Robinhood dark canvas */
    .stApp {
        background: #1A1A1A !important;
        color: #F5F5F5 !important;
    }
    section[data-testid="stSidebar"] { background: #1A1A1A; }

    header[data-testid="stHeader"] { background: transparent; height: 0; }

    /* Reset Streamlit defaults */
    .stDeployButton { display: none; }
    #MainMenu { display: none; }
    footer { display: none; }
    header { display: none !important; }

    /* ========== TYPOGRAPHY ========== */

    /* Portfolio value — the hero number */
    .portfolio-value {
        font-size: 40px;
        font-weight: 700;
        letter-spacing: -0.02em;
        line-height: 1.0;
        color: #FFFFFF;
        margin-bottom: 4px;
    }

    /* Today's change */
    .portfolio-change {
        font-size: 14px;
        font-weight: 500;
        letter-spacing: 0;
        line-height: 1.4;
    }
    .portfolio-change.positive { color: #00C805; }
    .portfolio-change.negative { color: #FF5000; }

    /* Section labels */
    .section-label {
        font-size: 12px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #AAAAAA;
        padding: 0 0 12px 0;
        border-bottom: 1px solid rgba(255,255,255,0.08);
        margin-bottom: 8px;
    }

    /* ========== CARDS ========== */

    .rh-card {
        background: #242424;
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 20px;
        padding: 24px;
        margin-bottom: 12px;
    }

    /* ========== STAT CARDS (top row) ========== */

    .stat-card {
        background: #242424;
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 20px;
        padding: 20px 24px;
        min-height: 90px;
    }
    .stat-label {
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #AAAAAA;
        margin-bottom: 8px;
    }
    .stat-value {
        font-size: 22px;
        font-weight: 700;
        letter-spacing: -0.01em;
        color: #F5F5F5;
    }
    .stat-value.green { color: #00C805; }
    .stat-value.red { color: #FF5000; }

    /* ========== POSITION ROWS ========== */

    .pos-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 16px 20px;
        border-bottom: 1px solid rgba(255,255,255,0.04);
        transition: background 0.15s ease;
        border-radius: 16px;
        margin-bottom: 2px;
    }
    .pos-row:hover {
        background: rgba(255,255,255,0.03);
    }
    .pos-row:last-child {
        border-bottom: none;
    }

    .pos-left {
        display: flex;
        align-items: center;
        gap: 14px;
        flex: 1;
    }
    .pos-icon {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 800;
        font-size: 13px;
        letter-spacing: 0.02em;
        flex-shrink: 0;
    }
    .pos-icon.tech { background: rgba(88,166,255,0.15); color: #58A6FF; }
    .pos-icon.health { background: rgba(139,92,246,0.15); color: #8B5CF6; }
    .pos-icon.consumer { background: rgba(236,72,153,0.15); color: #EC4899; }
    .pos-icon.industrial { background: rgba(245,158,11,0.15); color: #F59E0B; }
    .pos-icon.telecom { background: rgba(6,182,212,0.15); color: #06B6D4; }
    .pos-icon.finance { background: rgba(34,197,94,0.15); color: #22C55E; }
    .pos-icon.other { background: rgba(170,170,170,0.15); color: #AAAAAA; }

    .pos-ticker {
        font-size: 15px;
        font-weight: 700;
        color: #F5F5F5;
        letter-spacing: -0.01em;
    }
    .pos-name {
        font-size: 12px;
        color: #AAAAAA;
        margin-top: 1px;
    }

    .pos-center {
        flex: 1;
        display: flex;
        justify-content: center;
        padding: 0 16px;
    }

    .pos-right {
        text-align: right;
        flex-shrink: 0;
    }
    .pos-value {
        font-size: 15px;
        font-weight: 600;
        color: #F5F5F5;
        letter-spacing: -0.01em;
    }
    .pos-pl {
        font-size: 13px;
        font-weight: 500;
        margin-top: 2px;
    }
    .pos-pl.positive { color: #00C805; }
    .pos-pl.negative { color: #FF5000; }

    /* ========== MARKET STATUS ========== */

    .market-status {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        font-size: 12px;
        font-weight: 600;
        letter-spacing: 0.03em;
    }
    .market-dot {
        width: 7px;
        height: 7px;
        border-radius: 50%;
    }
    .market-dot.open { background: #00C805; animation: rh-pulse 2s infinite; }
    .market-dot.closed { background: #FF5000; }
    @keyframes rh-pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.4; }
    }

    /* ========== TIME RANGE TABS ========== */

    .time-tabs {
        display: flex;
        gap: 4px;
        margin-top: 16px;
        margin-bottom: 8px;
    }
    .time-tab {
        padding: 6px 16px;
        border-radius: 999px;
        font-size: 13px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.15s ease;
        border: none;
        background: transparent;
        color: #AAAAAA;
    }
    .time-tab:hover { background: rgba(255,255,255,0.06); }
    .time-tab.active {
        background: rgba(255,255,255,0.1);
        color: #F5F5F5;
    }

    /* ========== STRATEGY BADGE ========== */

    .strategy-badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 999px;
        font-size: 11px;
        font-weight: 600;
        letter-spacing: 0.03em;
        background: rgba(204,255,0,0.12);
        color: #CCFF00;
        border: 1px solid rgba(204,255,0,0.2);
    }

    /* ========== CASH ROW ========== */

    .cash-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 16px 20px;
        background: #242424;
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 16px;
    }

    /* ========== PILL BUTTON ========== */

    .rh-btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 6px;
        padding: 10px 24px;
        border-radius: 999px;
        font-size: 14px;
        font-weight: 700;
        letter-spacing: 0.01em;
        border: none;
        cursor: pointer;
        transition: all 0.15s ease;
    }
    .rh-btn-primary {
        background: #00C805;
        color: #0A0A0A;
    }
    .rh-btn-primary:hover { background: #00B504; }

    /* ========== LAST UPDATED ========== */

    .last-updated {
        text-align: center;
        font-size: 11px;
        color: #666666;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        padding: 20px 0;
    }

    /* Remove Streamlit default padding */
    .block-container { padding-top: 24px !important; }

    /* Hide Streamlit chrome */
    .stDeployButton { display: none !important; }
    #MainMenu { display: none !important; }
    footer { display: none !important; }
    div[data-testid="stDecoration"] { display: none !important; }
</style>
"""

st.markdown(ROBINHOOD_CSS, unsafe_allow_html=True)

# ========== API KEYS ==========
ALPACA_API_KEY = ""
ALPACA_SECRET_KEY = ""

if "ALPACA_API_KEY" in st.secrets:
    ALPACA_API_KEY = st.secrets["ALPACA_API_KEY"]
    ALPACA_SECRET_KEY = st.secrets["ALPACA_SECRET_KEY"]
elif os.environ.get("ALPACA_API_KEY"):
    ALPACA_API_KEY = os.environ["ALPACA_API_KEY"]
    ALPACA_SECRET_KEY = os.environ["ALPACA_SECRET_KEY"]

if not ALPACA_API_KEY or not ALPACA_SECRET_KEY:
    st.error("Missing API keys.")
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

# ========== DATA ==========
equity = float(account.equity)
cash = float(account.cash)
positions_value = sum(float(p.market_value) for p in positions)
total_pl = sum(float(p.unrealized_pl) for p in positions)
total_pl_pct = (total_pl / equity * 100) if equity > 0 else 0

# ========== PORTFOLIO HEADER ==========
col_status = st.columns([4, 1])
with col_status[1]:
    if clock.is_open:
        st.markdown('<div class="market-status" style="justify-content:flex-end;"><span class="market-dot open"></span><span style="color:#00C805;">MARKET OPEN</span></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="market-status" style="justify-content:flex-end;"><span class="market-dot closed"></span><span style="color:#FF5000;">MARKET CLOSED</span></div>', unsafe_allow_html=True)

# Portfolio value — hero
pl_sign = "+" if total_pl >= 0 else ""
pl_class = "positive" if total_pl >= 0 else "negative"

st.markdown(f"""
<div style="padding: 8px 0 0 0;">
    <div class="portfolio-value">${equity:,.2f}</div>
    <div class="portfolio-change {pl_class}">{pl_sign}${total_pl:,.2f} ({pl_sign}{total_pl_pct:.2f}%) today</div>
</div>
""", unsafe_allow_html=True)

# ========== CHART ==========
# Fetch portfolio history for the chart
try:
    portfolio_history = trading_client.get_portfolio_history(
        period="1M", timeframe="1D"
    )
    timestamps = portfolio_history.timestamp
    equity_values = portfolio_history.equity
    chart_dates = [datetime.fromtimestamp(t) for t in timestamps]
    chart_values = equity_values
except Exception:
    chart_dates = []
    chart_values = []

if chart_dates:
    chart_color = "#00C805" if chart_values[-1] >= chart_values[0] else "#FF5000"
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=chart_dates, y=chart_values,
        mode="lines",
        line=dict(color=chart_color, width=2, shape="spline"),
        fill="tozeroy",
        fillcolor=f"rgba({','.join(str(int(chart_color.lstrip('#')[i:i+2], 16)) for i in (0,2,4))},0.05)",
        hovertemplate="%{x|%b %d}<br>$%{y:,.2f}<extra></extra>",
        showlegend=False,
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#AAAAAA", size=11),
        margin=dict(l=0, r=0, t=4, b=0),
        height=200,
        xaxis=dict(
            showgrid=False, zeroline=False, showticklabels=True,
            tickformat="%b %d", nticks=6,
            tickfont=dict(size=11, color="#666666"),
        ),
        yaxis=dict(
            showgrid=False, zeroline=False, showticklabels=True,
            tickformat="$,.0f", nticks=4,
            tickfont=dict(size=11, color="#666666"),
        ),
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor="#2E2E2E", bordercolor="#3A3A3A",
            font=dict(size=13, color="#F5F5F5", family="Inter"),
        ),
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.markdown('<div style="height:200px;display:flex;align-items:center;justify-content:center;color:#666666;font-size:13px;">Chart data unavailable</div>', unsafe_allow_html=True)

# ========== TIME RANGE TABS (visual only) ==========
st.markdown("""
<div class="time-tabs">
    <span class="time-tab">1D</span>
    <span class="time-tab">1W</span>
    <span class="time-tab active">1M</span>
    <span class="time-tab">3M</span>
    <span class="time-tab">1Y</span>
    <span class="time-tab">ALL</span>
</div>
""", unsafe_allow_html=True)

st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)

# ========== STAT CARDS ==========
stat_cols = st.columns(5)
stat_data = [
    ("CASH", f"${cash:,.2f}", ""),
    ("INVESTED", f"${positions_value:,.2f}", ""),
    ("P&L", f"${total_pl:+,.2f}", f"{total_pl_pct:+.2f}%"),
    ("BUYING POWER", f"${float(account.buying_power):,.2f}", ""),
    ("POSITIONS", str(len(positions)), "active"),
]
for col, (label, value, sub) in zip(stat_cols, stat_data):
    sub_class = ""
    if "+" in sub or "positive" in sub.lower():
        sub_class = "color:#00C805;"
    elif "-" in sub and sub != "":
        sub_class = "color:#FF5000;"

    with col:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-label">{label}</div>
            <div class="stat-value">{value}</div>
            {"<div style='font-size:12px;font-weight:500;margin-top:4px;" + sub_class + "'>" + sub + "</div>" if sub else ""}
        </div>
        """, unsafe_allow_html=True)

st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)

# ========== POSITIONS ==========
if positions:
    st.markdown('<div class="section-label">Positions</div>', unsafe_allow_html=True)

    # Sector classification
    sector_map = {
        "AAPL": "tech", "MSFT": "tech", "NVDA": "tech", "AMZN": "tech", "GOOGL": "tech",
        "META": "tech", "TSLA": "tech", "AVGO": "tech", "CRM": "tech", "AMD": "tech",
        "PLTR": "tech", "CRWD": "tech", "DDOG": "tech", "NET": "tech", "SNOW": "tech",
        "AKAM": "tech", "TEAM": "tech", "QMCO": "tech", "U": "tech", "IONQ": "tech",
        "HD": "consumer", "MCD": "consumer", "NKE": "consumer", "SBUX": "consumer",
        "TGT": "consumer", "COST": "consumer", "WMT": "consumer", "KO": "consumer",
        "LLY": "health", "JNJ": "health", "UNH": "health", "ABBV": "health",
        "MRK": "health", "SYK": "health", "ZTS": "health", "ILMN": "health",
        "DHR": "health", "ABT": "health", "ISRG": "health", "VRTX": "health",
        "CAT": "industrial", "BA": "industrial", "HON": "industrial", "UNP": "industrial",
        "RTX": "industrial", "LMT": "industrial", "DE": "industrial",
        "NFLX": "telecom", "DIS": "telecom", "CMCSA": "telecom", "TMUS": "telecom",
        "V": "finance", "MA": "finance", "BLK": "finance", "SCHW": "finance",
        "XOM": "other", "CVX": "other", "COP": "other",
        "VZ": "telecom", "T": "telecom",
    }

    # Sort by market value descending
    sorted_positions = sorted(positions, key=lambda p: abs(float(p.market_value)), reverse=True)

    for p in sorted_positions:
        sym = p.symbol
        pl = float(p.unrealized_pl)
        plpc = float(p.unrealized_plpc) * 100
        entry = float(p.avg_entry_price)
        current = float(p.current_price)
        value = float(p.market_value)
        qty = float(p.qty)
        pl_sign = "+" if pl >= 0 else ""
        pl_class = "positive" if pl >= 0 else "negative"
        sector = sector_map.get(sym, "other")

        # Generate icon color class
        icon_class = sector

        st.markdown(f"""
        <div class="pos-row">
            <div class="pos-left">
                <div class="pos-icon {icon_class}">{sym[:2]}</div>
                <div>
                    <div class="pos-ticker">{sym}</div>
                    <div class="pos-name">{qty:.0f} shares</div>
                </div>
            </div>
            <div class="pos-right">
                <div class="pos-value">${value:,.2f}</div>
                <div class="pos-pl {pl_class}">{pl_sign}${pl:,.2f} ({pl_sign}{plpc:.2f}%)</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ========== PORTFOLIO CHART vs SPY ==========
    st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)
    st.markdown('<div class="section-label">vs SPY</div>', unsafe_allow_html=True)

    try:
        bars_req = StockBarsRequest(
            symbol_or_symbols=["SPY"],
            timeframe=TimeFrame.Day,
            start=datetime.now() - timedelta(days=30),
        )
        spy_bars = data_client.get_stock_bars(bars_req)["SPY"]
        spy_dates = [b.timestamp.date() for b in spy_bars]
        spy_close = [b.close for b in spy_bars]

        # Normalize SPY to % change from start
        spy_start = spy_close[0] if spy_close else 1
        spy_pct = [(v / spy_start - 1) * 100 for v in spy_close]

        # Portfolio % change
        if chart_dates and chart_values:
            port_start = chart_values[0] if chart_values else equity
            port_pct = [(v / port_start - 1) * 100 for v in chart_values]
            port_dates = chart_dates
        else:
            port_pct = []
            port_dates = []

        fig2 = go.Figure()

        if port_pct:
            fig2.add_trace(go.Scatter(
                x=port_dates, y=port_pct, name="Portfolio",
                line=dict(color="#00C805", width=2, shape="spline"),
                hovertemplate="%{y:+.2f}%<extra>You</extra>",
            ))

        fig2.add_trace(go.Scatter(
            x=spy_dates, y=spy_pct, name="SPY",
            line=dict(color="#58A6FF", width=2, shape="spline", dash="dot"),
            hovertemplate="%{y:+.2f}%<extra>SPY</extra>",
        ))

        fig2.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#AAAAAA", size=11),
            margin=dict(l=0, r=0, t=10, b=0),
            height=240,
            xaxis=dict(showgrid=False, zeroline=False, tickformat="%b %d", nticks=6,
                       tickfont=dict(size=11, color="#666666")),
            yaxis=dict(showgrid=False, zeroline=False, tickformat="+.1f%%", nticks=5,
                       tickfont=dict(size=11, color="#666666")),
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                font=dict(size=12, color="#AAAAAA"),
                bgcolor="rgba(0,0,0,0)", borderwidth=0,
            ),
            hovermode="x unified",
            hoverlabel=dict(
                bgcolor="#2E2E2E", bordercolor="#3A3A3A",
                font=dict(size=13, color="#F5F5F5", family="Inter"),
            ),
        )
        st.plotly_chart(fig2, use_container_width=True)
    except Exception:
        st.info("SPY comparison unavailable")

else:
    st.markdown("""
    <div class="rh-card" style="text-align:center;padding:48px 24px;">
        <div style="font-size:16px;font-weight:600;color:#F5F5F5;margin-bottom:8px;">No positions yet</div>
        <div style="font-size:14px;color:#AAAAAA;line-height:1.6;">
            The bot scans 280+ Sharia-compliant stocks every 10 minutes.<br>
            Trades are cash-only — no margin, no leverage.
        </div>
    </div>
    """, unsafe_allow_html=True)

# ========== CASH ROW ==========
st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)
st.markdown(f"""
<div class="cash-row">
    <div>
        <div class="stat-label">CASH</div>
        <div class="stat-value">${cash:,.2f}</div>
    </div>
    <div style="text-align:right;">
        <div class="stat-label">BUYING POWER</div>
        <div class="stat-value">${float(account.buying_power):,.2f}</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ========== FOOTER ==========
st.markdown(f"""
<div class="last-updated">
    Last updated: {datetime.now().strftime('%I:%M %p ET')} &bull; Paper Trading
</div>
""", unsafe_allow_html=True)
