import streamlit as st
import os
from datetime import datetime, timedelta
from alpaca.trading.client import TradingClient
from alpaca.data.historical.stock import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
import plotly.graph_objects as go

st.set_page_config(page_title="Trading Bot", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    /* ===== RESET ===== */
    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
        -webkit-font-smoothing: antialiased !important;
        -moz-osx-font-smoothing: grayscale !important;
    }

    /* ===== HIDE STREAMLIT CHROME ===== */
    #MainMenu, footer, header[data-testid="stHeader"],
    .stDeployButton, div[data-testid="stToolbar"],
    div[data-testid="stDecoration"], div[data-testid="stStatusWidget"] {
        visibility: hidden; height: 0; display: none; position: fixed;
    }

    /* ===== ROBINHOOD CANVAS: #110e08 (warm black) ===== */
    .stApp {
        background: #110e08 !important;
    }
    section[data-testid="stSidebar"] { background: #110e08; }

    .block-container {
        padding-top: 16px !important;
        padding-bottom: 0px !important;
        padding-left: 16px !important;
        padding-right: 16px !important;
        max-width: 960px !important;
    }

    /* ===== SCROLLBAR ===== */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: #110e08; }
    ::-webkit-scrollbar-thumb { background: #35322d; border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: #4d4a46; }

    /* ===== PORTFOLIO HERO ===== */
    .rh-hero {
        padding: 4px 0 0 0;
    }
    .rh-hero-value {
        font-size: 36px;
        font-weight: 700;
        letter-spacing: -0.025em;
        line-height: 1.0;
        color: #FFFFFF;
        margin: 0;
        padding: 0;
    }
    .rh-change {
        font-size: 14px;
        font-weight: 500;
        line-height: 1.4;
        margin: 6px 0 0 0;
    }
    .rh-change.up { color: #00C805; }
    .rh-change.down { color: #FF5000; }

    /* ===== MARKET STATUS ===== */
    .rh-status {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        font-size: 10px;
        font-weight: 700;
        letter-spacing: 0.06em;
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

    /* ===== STAT CARDS ===== */
    .rh-stats {
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: 8px;
        margin: 12px 0;
    }
    .rh-stat {
        background: #1c180d;
        border: 1px solid #35322d;
        border-radius: 0px;
        padding: 14px 16px;
    }
    .rh-stat-label {
        font-size: 10px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #4d4a46;
        margin-bottom: 6px;
    }
    .rh-stat-val {
        font-size: 16px;
        font-weight: 700;
        color: #FFFFFF;
        letter-spacing: -0.01em;
        font-feature-settings: 'tnum';
    }

    /* ===== SECTION HEADER ===== */
    .rh-section {
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #4d4a46;
        padding-bottom: 8px;
        border-bottom: 1px solid #35322d;
        margin-bottom: 0;
    }

    /* ===== POSITION ROW ===== */
    .rh-pos {
        display: flex;
        align-items: center;
        height: 64px;
        padding: 0 12px;
        border-bottom: 1px solid #1c180d;
        transition: background-color 120ms ease-out;
        cursor: default;
    }
    .rh-pos:hover {
        background: rgba(255,255,255,0.02);
    }
    .rh-pos-left {
        display: flex;
        align-items: center;
        gap: 12px;
        flex: 1;
        min-width: 0;
    }
    .rh-icon {
        width: 32px;
        height: 32px;
        border-radius: 16px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 700;
        font-size: 11px;
        letter-spacing: 0.02em;
        flex-shrink: 0;
    }
    .rh-ticker {
        font-size: 15px;
        font-weight: 600;
        color: #FFFFFF;
        letter-spacing: -0.01em;
        line-height: 1.2;
    }
    .rh-sub {
        font-size: 12px;
        color: #4d4a46;
        line-height: 1.3;
        margin-top: 1px;
    }
    .rh-pos-right {
        text-align: right;
        flex-shrink: 0;
    }
    .rh-pos-val {
        font-size: 15px;
        font-weight: 600;
        color: #FFFFFF;
        letter-spacing: -0.01em;
        font-feature-settings: 'tnum';
    }
    .rh-pos-pl {
        font-size: 12px;
        font-weight: 400;
        line-height: 1.35;
        letter-spacing: 0.01em;
        font-feature-settings: 'tnum';
        margin-top: 2px;
    }
    .rh-pos-pl.up { color: #00C805; }
    .rh-pos-pl.down { color: #FF5000; }

    /* ===== TIME TABS ===== */
    .rh-tabs {
        display: flex;
        gap: 2px;
        padding: 3px;
        background: #1c180d;
        border-radius: 0px;
        width: fit-content;
        margin: 8px 0;
    }
    .rh-tab {
        padding: 5px 14px;
        border-radius: 0px;
        font-size: 12px;
        font-weight: 600;
        color: #4d4a46;
        cursor: pointer;
        transition: all 120ms ease-out;
    }
    .rh-tab:hover { color: #AAAAAA; }
    .rh-tab.active {
        background: #35322d;
        color: #FFFFFF;
    }

    /* ===== CASH ROW ===== */
    .rh-cash {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 14px 16px;
        background: #1c180d;
        border: 1px solid #35322d;
        border-radius: 0px;
        margin: 12px 0;
    }

    /* ===== FOOTER ===== */
    .rh-footer {
        text-align: center;
        font-size: 10px;
        color: #35322d;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        padding: 20px 0 8px 0;
    }

    /* ===== OVERRIDE STREAMLIT METRICS ===== */
    div[data-testid="stMetric"] {
        background: #1c180d !important;
        border: 1px solid #35322d !important;
        border-radius: 0px !important;
        padding: 12px 14px !important;
        border-left: none !important;
        box-shadow: none !important;
    }
    div[data-testid="stMetric"] label p {
        color: #4d4a46 !important;
        font-size: 10px !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.06em !important;
    }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] p {
        color: #FFFFFF !important;
        font-size: 18px !important;
        font-weight: 700 !important;
    }
    div[data-testid="stMetric"] [data-testid="stMetricDelta"] > div {
        color: #00C805 !important;
    }
    div[data-testid="stMetric"] [data-testid="stMetricDelta"] > div p {
        color: inherit !important;
    }

    [data-testid="stHorizontalBlock"] {
        gap: 8px !important;
    }

    /* ===== CHART CONTAINER ===== */
    .rh-chart {
        margin: 4px 0;
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

# ========== HEADER: Market status + Portfolio value ==========
if clock.is_open:
    st.markdown(f'<div style="text-align:right;"><span class="rh-status"><span class="rh-dot open"></span><span style="color:#00C805;">MARKET OPEN</span></span></div>', unsafe_allow_html=True)
else:
    st.markdown(f'<div style="text-align:right;"><span class="rh-status"><span class="rh-dot closed"></span><span style="color:#FF5000;">MARKET CLOSED</span></span></div>', unsafe_allow_html=True)

pl_sign = "+" if total_pl >= 0 else ""
pl_class = "up" if total_pl >= 0 else "down"

st.markdown(f"""
<div class="rh-hero">
    <div class="rh-hero-value">${equity:,.2f}</div>
    <div class="rh-change {pl_class}">{pl_sign}${total_pl:,.2f} ({pl_sign}{total_pl_pct:.2f}%) today</div>
</div>
""", unsafe_allow_html=True)

# ========== CHART ==========
chart_dates = []
chart_values = []
chart_source = None

try:
    ph = trading_client.get_portfolio_history(period="1M", timeframe="1D")
    if ph and ph.timestamp and ph.equity and len(ph.timestamp) > 1:
        chart_dates = [datetime.fromtimestamp(t) for t in ph.timestamp]
        chart_values = list(ph.equity)
        chart_source = "portfolio"
except Exception:
    pass

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
            spy_close = [b.close for b in spy_bars]
            spy_start = spy_close[0]
            chart_values = [(v / spy_start) * equity for v in spy_close]
            chart_source = "spy"
    except Exception:
        pass

if chart_dates and chart_values and len(chart_dates) > 1:
    is_up = chart_values[-1] >= chart_values[0]
    chart_color = "#00C805" if is_up else "#FF5000"
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
        fillcolor=f"rgba({r},{g},{b},0.06)",
        hovertemplate="%{x|%b %d}<br>$%{y:,.2f}<extra></extra>",
        showlegend=False,
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#4d4a46", size=11, family="Inter"),
        margin=dict(l=0, r=0, t=4, b=0),
        height=180,
        xaxis=dict(
            showgrid=False, zeroline=False, showline=False,
            showticklabels=True, tickformat="%b %d", nticks=5,
            tickfont=dict(size=10, color="#35322d"),
        ),
        yaxis=dict(
            showgrid=False, zeroline=False, showline=False,
            showticklabels=True, tickformat="$,.0f", nticks=4,
            tickfont=dict(size=10, color="#35322d"),
            side="right",
        ),
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor="#1c180d", bordercolor="#35322d",
            font=dict(size=12, color="#FFFFFF", family="Inter"),
        ),
    )
    st.plotly_chart(fig, use_container_width=True)

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
    st.markdown('<div style="height:180px;display:flex;align-items:center;justify-content:center;color:#35322d;font-size:12px;">Loading chart...</div>', unsafe_allow_html=True)

# ========== STAT CARDS ==========
stat_labels = ["CASH", "INVESTED", "P&L", "BUYING POWER", "POSITIONS"]
stat_vals = [
    f"${cash:,.2f}",
    f"${positions_value:,.2f}",
    f"${total_pl:+,.2f}",
    f"${buying_power:,.2f}",
    str(len(positions)),
]
stat_html = '<div class="rh-stats">'
for label, val in zip(stat_labels, stat_vals):
    stat_html += f'<div class="rh-stat"><div class="rh-stat-label">{label}</div><div class="rh-stat-val">{val}</div></div>'
stat_html += '</div>'
st.markdown(stat_html, unsafe_allow_html=True)

# ========== POSITIONS ==========
if positions:
    st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)
    st.markdown('<div class="rh-section">Positions</div>', unsafe_allow_html=True)

    sector_colors = {
        "tech": ("rgba(88,166,255,0.15)", "#58A6FF"),
        "health": ("rgba(139,92,246,0.15)", "#8B5CF6"),
        "consumer": ("rgba(236,72,153,0.15)", "#EC4899"),
        "industrial": ("rgba(245,158,11,0.15)", "#F59E0B"),
        "telecom": ("rgba(6,182,212,0.15)", "#06B6D4"),
        "finance": ("rgba(34,197,94,0.15)", "#22C55E"),
        "other": ("rgba(77,74,70,0.25)", "#4d4a46"),
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

    pos_html = ""
    for p in sorted_pos:
        sym = p.symbol
        pl = float(p.unrealized_pl)
        plpc = float(p.unrealized_plpc) * 100
        qty = float(p.qty)
        value = float(p.market_value)
        sector = sector_map.get(sym, "other")
        bg, fg = sector_colors.get(sector, sector_colors["other"])

        pl_sign = "+" if pl >= 0 else ""
        pl_cls = "up" if pl >= 0 else "down"

        pos_html += f"""
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
        """
    st.markdown(pos_html, unsafe_allow_html=True)

    # ========== VS SPY CHART ==========
    st.markdown('<div style="height:12px;"></div>', unsafe_allow_html=True)
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
                line=dict(color="#58A6FF", width=1.5, shape="spline", dash="dot"),
                hovertemplate="%{y:+.2f}%<extra>SPY</extra>",
            ))
            fig2.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#4d4a46", size=11, family="Inter"),
                margin=dict(l=0, r=0, t=8, b=0),
                height=200,
                xaxis=dict(showgrid=False, zeroline=False, showline=False,
                           tickformat="%b %d", nticks=5,
                           tickfont=dict(size=10, color="#35322d")),
                yaxis=dict(showgrid=False, zeroline=False, showline=False,
                           tickformat="+.1f%%", nticks=5, side="right",
                           tickfont=dict(size=10, color="#35322d")),
                legend=dict(
                    orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                    font=dict(size=11, color="#4d4a46"),
                    bgcolor="rgba(0,0,0,0)", borderwidth=0,
                ),
                hovermode="x unified",
                hoverlabel=dict(bgcolor="#1c180d", bordercolor="#35322d",
                                font=dict(size=12, color="#FFFFFF", family="Inter")),
            )
            st.plotly_chart(fig2, use_container_width=True)
    except Exception:
        pass

else:
    st.markdown("""
    <div style="text-align:center;padding:40px 24px;">
        <div style="font-size:15px;font-weight:600;color:#FFFFFF;margin-bottom:6px;">No positions yet</div>
        <div style="font-size:13px;color:#4d4a46;">The bot scans 280+ Sharia-compliant stocks every 10 minutes.</div>
    </div>
    """, unsafe_allow_html=True)

# ========== CASH ROW ==========
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
""")
