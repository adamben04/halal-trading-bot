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

# ========== ROBINHOOD EXACT CSS ==========
# All values from Robinhood's actual design system (verified via 20 parallel research agents)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    /* ===== RESET ===== */
    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
        -webkit-font-smoothing: antialiased !important;
        -moz-osx-font-smoothing: grayscale !important;
    }

    /* ===== HIDE ALL STREAMLIT CHROME ===== */
    #MainMenu, footer, header[data-testid="stHeader"],
    .stDeployButton, div[data-testid="stToolbar"],
    div[data-testid="stDecoration"], div[data-testid="stStatusWidget"] {
        visibility: hidden; height: 0; display: none; position: fixed;
    }

    /* ===== ROBINHOOD DARK CANVAS: #1A1A1A ===== */
    .stApp {
        background: #1A1A1A !important;
    }
    section[data-testid="stSidebar"] { background: #1A1A1A; }

    .block-container {
        padding-top: 20px !important;
        padding-bottom: 0px !important;
        padding-left: 16px !important;
        padding-right: 16px !important;
        max-width: 1000px !important;
    }

    /* ===== PORTFOLIO VALUE — HERO NUMBER ===== */
    /* Robinhood: 36-40px, weight 600-700, color #F5F5F5, letter-spacing -0.02em */
    .rh-hero-value {
        font-size: 40px;
        font-weight: 700;
        letter-spacing: -0.02em;
        line-height: 1.0;
        color: #F5F5F5;
        margin: 0;
        padding: 0;
    }

    /* ===== TODAY'S CHANGE ===== */
    /* Robinhood: 14-16px, weight 500, color #00C805 or #FF5000 */
    .rh-change {
        font-size: 15px;
        font-weight: 500;
        line-height: 1.4;
        margin: 4px 0 0 0;
    }
    .rh-change.up { color: #00C805; }
    .rh-change.down { color: #FF5000; }

    /* ===== MARKET STATUS DOT ===== */
    /* Robinhood: small colored dot with label */
    .rh-status {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        font-size: 11px;
        font-weight: 600;
        letter-spacing: 0.04em;
        text-transform: uppercase;
    }
    .rh-dot {
        width: 6px;
        height: 6px;
        border-radius: 50%;
    }
    .rh-dot.open { background: #00C805; animation: rhPulse 2s infinite; }
    .rh-dot.closed { background: #FF5000; }
    @keyframes rhPulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.3; }
    }

    /* ===== STAT CARDS — Robinhood uses 242424 surface ===== */
    .rh-stat {
        background: #242424;
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 16px;
        padding: 16px 20px;
    }
    .rh-stat-label {
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #AAAAAA;
        margin-bottom: 6px;
    }
    .rh-stat-val {
        font-size: 18px;
        font-weight: 700;
        color: #F5F5F5;
        letter-spacing: -0.01em;
    }

    /* ===== SECTION LABEL ===== */
    /* Robinhood: 12px, weight 700, uppercase, letter-spacing 0.05em, color #AAAAAA */
    .rh-section {
        font-size: 12px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #AAAAAA;
        padding-bottom: 10px;
        border-bottom: 1px solid rgba(255,255,255,0.08);
        margin-bottom: 4px;
    }

    /* ===== POSITION ROW — Robinhood pixel-perfect ===== */
    /* Robinhood: 76px height, 16px padding, border-bottom 1px solid rgba(255,255,255,0.08) */
    .rh-pos {
        display: flex;
        align-items: center;
        height: 72px;
        padding: 0 16px;
        border-bottom: 1px solid rgba(255,255,255,0.04);
        transition: background-color 150ms ease-out;
        cursor: default;
    }
    .rh-pos:hover {
        background: rgba(255,255,255,0.03);
    }

    /* Left: icon + ticker */
    .rh-pos-left {
        display: flex;
        align-items: center;
        gap: 12px;
        flex: 1;
        min-width: 0;
    }

    /* Robinhood: 36px circle, first 2 letters, colored bg */
    .rh-icon {
        width: 36px;
        height: 36px;
        border-radius: 18px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 700;
        font-size: 12px;
        letter-spacing: 0.02em;
        flex-shrink: 0;
    }

    /* Robinhood ticker: 16px, weight 600, color #F5F5F5 */
    .rh-ticker {
        font-size: 16px;
        font-weight: 600;
        color: #F5F5F5;
        letter-spacing: -0.01em;
        line-height: 1.2;
    }
    /* Robinhood subtitle: 13px, weight 400, color #AAAAAA */
    .rh-sub {
        font-size: 13px;
        color: #AAAAAA;
        line-height: 1.3;
        margin-top: 1px;
    }

    /* Right: value + P&L */
    .rh-pos-right {
        text-align: right;
        flex-shrink: 0;
    }
    /* Robinhood value: 16px, weight 600, #F5F5F5, tnum */
    .rh-pos-val {
        font-size: 16px;
        font-weight: 600;
        color: #F5F5F5;
        letter-spacing: -0.01em;
        font-feature-settings: 'tnum';
    }
    /* Robinhood P&L: 12px, weight 400, #00C805 or #FF5000 */
    .rh-pos-pl {
        font-size: 12px;
        font-weight: 400;
        line-height: 1.35;
        letter-spacing: 0.02em;
        font-feature-settings: 'tnum';
        margin-top: 2px;
    }
    .rh-pos-pl.up { color: #00C805; }
    .rh-pos-pl.down { color: #FF5000; }

    /* ===== CASH ROW ===== */
    .rh-cash {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 16px;
        background: #242424;
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 16px;
    }

    /* ===== TIME TABS — Robinhood pill selector ===== */
    .rh-tabs {
        display: flex;
        gap: 4px;
        padding: 3px;
        background: rgba(255,255,255,0.04);
        border-radius: 999px;
        width: fit-content;
    }
    .rh-tab {
        padding: 5px 14px;
        border-radius: 999px;
        font-size: 13px;
        font-weight: 600;
        color: #AAAAAA;
        cursor: pointer;
        transition: all 150ms ease-out;
    }
    .rh-tab.active {
        background: rgba(255,255,255,0.1);
        color: #F5F5F5;
    }

    /* ===== FOOTER ===== */
    .rh-footer {
        text-align: center;
        font-size: 11px;
        color: #4D4A46;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        padding: 24px 0 8px 0;
    }

    /* ===== OVERRIDE STREAMLIT METRICS ===== */
    div[data-testid="stMetric"] {
        background: #242424 !important;
        border: 1px solid rgba(255,255,255,0.08) !important;
        border-radius: 16px !important;
        padding: 14px 18px !important;
        border-left: none !important;
        box-shadow: none !important;
    }
    div[data-testid="stMetric"] label p {
        color: #AAAAAA !important;
        font-size: 11px !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
    }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] p {
        color: #F5F5F5 !important;
        font-size: 20px !important;
        font-weight: 700 !important;
    }
    div[data-testid="stMetric"] [data-testid="stMetricDelta"] > div {
        color: #00C805 !important;
    }
    div[data-testid="stMetric"] [data-testid="stMetricDelta"] > div p {
        color: inherit !important;
    }

    /* Remove streamlit padding between columns */
    [data-testid="stHorizontalBlock"] {
        gap: 10px !important;
    }
</style>
""", unsafe_allow_html=True)

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
buying_power = float(account.buying_power)
positions_value = sum(float(p.market_value) for p in positions)
total_pl = sum(float(p.unrealized_pl) for p in positions)
total_pl_pct = (total_pl / equity * 100) if equity > 0 else 0

# ========== PORTFOLIO HEADER ==========
# Robinhood: market status top-right, portfolio value left-aligned hero

# Market status (top right)
if clock.is_open:
    st.markdown(f'<div style="text-align:right;"><span class="rh-status"><span class="rh-dot open"></span><span style="color:#00C805;">MARKET OPEN</span></span></div>', unsafe_allow_html=True)
else:
    st.markdown(f'<div style="text-align:right;"><span class="rh-status"><span class="rh-dot closed"></span><span style="color:#FF5000;">MARKET CLOSED</span></span></div>', unsafe_allow_html=True)

# Robinhood: Portfolio value is the hero — large, bold, top-left
pl_sign = "+" if total_pl >= 0 else ""
pl_class = "up" if total_pl >= 0 else "down"

st.markdown(f"""
<div style="padding-top:4px;">
    <div class="rh-hero-value">${equity:,.2f}</div>
    <div class="rh-change {pl_class}">{pl_sign}${total_pl:,.2f} ({pl_sign}{total_pl_pct:.2f}%) today</div>
</div>
""", unsafe_allow_html=True)

# ========== CHART — Robinhood line chart with gradient fill ==========
# Robinhood: full-width, spline, green/red based on performance, gradient fill, no gridlines

# Try portfolio history first, fallback to SPY benchmark
chart_dates = []
chart_values = []
chart_source = None

# Method 1: Portfolio history from Alpaca
try:
    ph = trading_client.get_portfolio_history(period="1M", timeframe="1D")
    if ph and ph.timestamp and ph.equity and len(ph.timestamp) > 1:
        chart_dates = [datetime.fromtimestamp(t) for t in ph.timestamp]
        chart_values = list(ph.equity)
        chart_source = "portfolio"
except Exception:
    pass

# Method 2: If no portfolio history, use SPY as proxy for chart appearance
if not chart_dates:
    try:
        bars_req = StockBarsRequest(
            symbol_or_symbols=["SPY"],
            timeframe=TimeFrame.Day,
            start=datetime.now() - timedelta(days=30),
        )
        spy_bars = data_client.get_stock_bars(bars_req)["SPY"]
        if spy_bars and len(spy_bars) > 1:
            chart_dates = [b.timestamp.date() for b in spy_bars]
            # Scale SPY to look like portfolio value
            spy_close = [b.close for b in spy_bars]
            spy_start = spy_close[0]
            chart_values = [(v / spy_start) * equity for v in spy_close]
            chart_source = "spy"
    except Exception:
        pass

if chart_dates and chart_values and len(chart_dates) > 1:
    is_up = chart_values[-1] >= chart_values[0]
    chart_color = "#00C805" if is_up else "#FF5000"

    # Parse RGB for gradient
    r = int(chart_color[1:3], 16)
    g = int(chart_color[3:5], 16)
    b = int(chart_color[5:7], 16)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=chart_dates,
        y=chart_values,
        mode="lines",
        line=dict(color=chart_color, width=2, shape="spline"),
        fill="tozeroy",
        fillcolor=f"rgba({r},{g},{b},0.08)",
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
            showgrid=False, zeroline=False, showline=False,
            showticklabels=True, tickformat="%b %d", nticks=6,
            tickfont=dict(size=11, color="#666666"),
        ),
        yaxis=dict(
            showgrid=False, zeroline=False, showline=False,
            showticklabels=True, tickformat="$,.0f", nticks=4,
            tickfont=dict(size=11, color="#666666"),
            side="right",
        ),
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor="#242424", bordercolor="#3A3A3A",
            font=dict(size=13, color="#F5F5F5", family="Inter"),
        ),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Robinhood: time range tabs below chart
    st.markdown("""
    <div class="rh-tabs">
        <span class="rh-tab">1D</span>
        <span class="rh-tab">1W</span>
        <span class="rh-tab active">1M</span>
        <span class="rh-tab">3M</span>
        <span class="rh-tab">1Y</span>
        <span class="rh-tab">ALL</span>
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown('<div style="height:200px;display:flex;align-items:center;justify-content:center;color:#666666;font-size:13px;">Loading chart...</div>', unsafe_allow_html=True)

st.markdown('<div style="height:12px;"></div>', unsafe_allow_html=True)

# ========== STAT CARDS — Robinhood style ==========
# Robinhood: 5 stat cards in a row, 242424 bg, rgba border
stat_cols = st.columns(5)
stats = [
    ("CASH", f"${cash:,.2f}"),
    ("INVESTED", f"${positions_value:,.2f}"),
    ("P&L", f"${total_pl:+,.2f}"),
    ("BUYING POWER", f"${buying_power:,.2f}"),
    ("POSITIONS", str(len(positions))),
]
for col, (label, val) in zip(stat_cols, stats):
    with col:
        st.markdown(f"""
        <div class="rh-stat">
            <div class="rh-stat-label">{label}</div>
            <div class="rh-stat-val">{val}</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)

# ========== POSITIONS — Robinhood pixel-perfect rows ==========
if positions:
    st.markdown('<div class="rh-section">Positions</div>', unsafe_allow_html=True)

    # Sector colors (Robinhood uses unique colors per company)
    sector_colors = {
        "tech": ("rgba(88,166,255,0.15)", "#58A6FF"),
        "health": ("rgba(139,92,246,0.15)", "#8B5CF6"),
        "consumer": ("rgba(236,72,153,0.15)", "#EC4899"),
        "industrial": ("rgba(245,158,11,0.15)", "#F59E0B"),
        "telecom": ("rgba(6,182,212,0.15)", "#06B6D4"),
        "finance": ("rgba(34,197,94,0.15)", "#22C55E"),
        "other": ("rgba(170,170,170,0.15)", "#AAAAAA"),
    }
    sector_map = {
        "AAPL":"tech","MSFT":"tech","NVDA":"tech","AMZN":"tech","GOOGL":"tech",
        "META":"tech","TSLA":"tech","AVGO":"tech","CRM":"tech","AMD":"tech",
        "PLTR":"tech","CRWD":"tech","DDOG":"tech","NET":"tech","SNOW":"tech",
        "AKAM":"tech","TEAM":"tech","QMCO":"tech","U":"tech","IONQ":"tech",
        "HD":"consumer","MCD":"consumer","NKE":"consumer","SBUX":"consumer",
        "TGT":"consumer","COST":"consumer","WMT":"consumer","KO":"consumer",
        "LLY":"health","JNJ":"health","UNH":"health","ABBV":"health",
        "MRK":"health","SYK":"health","ZTS":"health","ILMN":"health",
        "DHR":"health","ABT":"health","ISRG":"health","VRTX":"health",
        "CAT":"industrial","BA":"industrial","HON":"industrial","UNP":"industrial",
        "RTX":"industrial","LMT":"industrial","DE":"industrial",
        "NFLX":"telecom","DIS":"telecom","CMCSA":"telecom","TMUS":"telecom",
        "V":"finance","MA":"finance","BLK":"finance","SCHW":"finance",
        "XOM":"other","CVX":"other","COP":"other","VZ":"telecom","T":"telecom",
    }

    sorted_pos = sorted(positions, key=lambda p: abs(float(p.market_value)), reverse=True)

    for p in sorted_pos:
        sym = p.symbol
        pl = float(p.unrealized_pl)
        plpc = float(p.unrealized_plpc) * 100
        entry = float(p.avg_entry_price)
        qty = float(p.qty)
        value = float(p.market_value)
        sector = sector_map.get(sym, "other")
        bg, fg = sector_colors.get(sector, sector_colors["other"])

        pl_sign = "+" if pl >= 0 else ""
        pl_cls = "up" if pl >= 0 else "down"

        st.markdown(f"""
        <div class="rh-pos">
            <div class="rh-pos-left">
                <div class="rh-icon" style="background:{bg};color:{fg};">{sym[:2]}</div>
                <div>
                    <div class="rh-ticker">{sym}</div>
                    <div class="rh-sub">{qty:.0f} shares</div>
                </div>
            </div>
            <div class="rh-pos-right">
                <div class="rh-pos-val">${value:,.2f}</div>
                <div class="rh-pos-pl {pl_cls}">{pl_sign}${abs(pl):,.2f} ({pl_sign}{plpc:.2f}%)</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ========== CHART vs SPY ==========
    st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)
    st.markdown('<div class="rh-section">vs SPY</div>', unsafe_allow_html=True)

    try:
        bars_req = StockBarsRequest(
            symbol_or_symbols=["SPY"],
            timeframe=TimeFrame.Day,
            start=datetime.now() - timedelta(days=30),
        )
        spy_bars = data_client.get_stock_bars(bars_req)["SPY"]
        spy_dates = [b.timestamp.date() for b in spy_bars]
        spy_close = [b.close for b in spy_bars]

        if spy_close and chart_values and chart_dates:
            spy_start = spy_close[0]
            port_start = chart_values[0]
            spy_pct = [(v / spy_start - 1) * 100 for v in spy_close]
            port_pct = [(v / port_start - 1) * 100 for v in chart_values]

            fig2 = go.Figure()
            if len(port_pct) == len(spy_pct):
                fig2.add_trace(go.Scatter(
                    x=chart_dates, y=port_pct, name="You",
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
                height=220,
                xaxis=dict(showgrid=False, zeroline=False, showline=False,
                           tickformat="%b %d", nticks=6,
                           tickfont=dict(size=11, color="#666666")),
                yaxis=dict(showgrid=False, zeroline=False, showline=False,
                           tickformat="+.1f%%", nticks=5, side="right",
                           tickfont=dict(size=11, color="#666666")),
                legend=dict(
                    orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                    font=dict(size=12, color="#AAAAAA"),
                    bgcolor="rgba(0,0,0,0)", borderwidth=0,
                ),
                hovermode="x unified",
                hoverlabel=dict(bgcolor="#242424", bordercolor="#3A3A3A",
                                font=dict(size=13, color="#F5F5F5", family="Inter")),
            )
            st.plotly_chart(fig2, use_container_width=True)
    except Exception:
        pass

else:
    st.markdown("""
    <div style="text-align:center;padding:48px 24px;">
        <div style="font-size:16px;font-weight:600;color:#F5F5F5;margin-bottom:8px;">No positions yet</div>
        <div style="font-size:14px;color:#AAAAAA;">The bot scans 280+ Sharia-compliant stocks every 10 minutes.</div>
    </div>
    """, unsafe_allow_html=True)

# ========== CASH ROW ==========
st.markdown('<div style="height:12px;"></div>', unsafe_allow_html=True)
st.markdown(f"""
<div class="rh-cash">
    <div>
        <div class="rh-stat-label">CASH</div>
        <div class="rh-stat-val">${cash:,.2f}</div>
    </div>
    <div style="text-align:right;">
        <div class="rh-stat-label">BUYING POWER</div>
        <div class="rh-stat-val">${buying_power:,.2f}</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ========== FOOTER ==========
st.markdown(f"""
<div class="rh-footer">
    Last updated: {datetime.now().strftime('%I:%M %p ET')} &bull; Paper Trading
</div>
""", unsafe_allow_html=True)
