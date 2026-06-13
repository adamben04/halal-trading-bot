import streamlit as st
import os
from datetime import datetime, timedelta

try:
    from alpaca.trading.client import TradingClient
    from alpaca.data.historical.stock import StockHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
except ImportError as e:
    st.error(f"Failed to import Alpaca packages: {e}. Check requirements.txt")
    st.stop()

try:
    import plotly.graph_objects as go
except ImportError as e:
    st.error(f"Failed to import plotly: {e}. Check requirements.txt")
    st.stop()

try:
    from database import init_db, get_performance_stats, get_streak, get_best_worst_trade, get_trade_count_today, get_journal_entries, get_full_trade_history, get_calendar_pnl, get_stats_by_strategy
except ImportError as e:
    st.error(f"Failed to import database module: {e}")
    st.stop()

init_db()

st.set_page_config(page_title="Trading Bot", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
        -webkit-font-smoothing: antialiased !important;
    }

    #MainMenu, footer, header[data-testid="stHeader"],
    .stDeployButton, div[data-testid="stToolbar"],
    div[data-testid="stDecoration"], div[data-testid="stStatusWidget"] {
        visibility: hidden; height: 0; display: none; position: fixed;
    }

    .stApp { background: #000000 !important; }
    section[data-testid="stSidebar"] { background: #000000; }

    .block-container {
        padding-top: 12px !important;
        padding-bottom: 0px !important;
        padding-left: 16px !important;
        padding-right: 16px !important;
        max-width: 480px !important;
    }

    ::-webkit-scrollbar { width: 0; height: 0; }

    .rh-hero-value {
        font-size: 34px; font-weight: 700; letter-spacing: -0.03em;
        line-height: 1.0; color: #FFF; margin: 0;
    }
    .rh-change { font-size: 15px; font-weight: 500; margin: 4px 0 0 0; }
    .rh-change.up { color: #00D64F; }
    .rh-change.down { color: #FF5000; }

    .rh-status {
        display: inline-flex; align-items: center; gap: 6px;
        font-size: 10px; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase;
    }
    .rh-dot { width: 6px; height: 6px; border-radius: 50%; }
    .rh-dot.open { background: #00D64F; animation: rhPulse 2s infinite; }
    .rh-dot.closed { background: #FF5000; }
    @keyframes rhPulse { 0%,100%{opacity:1} 50%{opacity:0.3} }

    .rh-section {
        font-size: 11px; font-weight: 700; text-transform: uppercase;
        letter-spacing: 0.06em; color: #555; padding: 14px 0 8px 0;
        border-bottom: 1px solid #1A1A1A;
    }

    /* ===== STAT PILLS ===== */
    .rh-pills {
        display: grid; grid-template-columns: repeat(5, 1fr);
        gap: 1px; background: #1A1A1A; border: 1px solid #1A1A1A;
        margin: 16px 0 8px 0;
    }
    .rh-pill { background: #0A0A0A; padding: 12px 6px; text-align: center; }
    .rh-pill-label {
        font-size: 9px; font-weight: 700; text-transform: uppercase;
        letter-spacing: 0.08em; color: #555; margin-bottom: 4px;
    }
    .rh-pill-val {
        font-size: 13px; font-weight: 700; color: #FFF;
        font-feature-settings: 'tnum';
    }

    /* ===== POSITION ROW ===== */
    .rh-pos {
        display: flex; align-items: center; height: 68px;
        padding: 0 4px; border-bottom: 1px solid #111;
        transition: background 100ms;
    }
    .rh-pos:active { background: rgba(255,255,255,0.03); }
    .rh-pos-left { display: flex; align-items: center; gap: 12px; flex: 1; min-width: 0; }
    .rh-icon {
        width: 36px; height: 36px; border-radius: 18px;
        display: flex; align-items: center; justify-content: center;
        font-weight: 700; font-size: 12px; flex-shrink: 0;
    }
    .rh-ticker { font-size: 16px; font-weight: 600; color: #FFF; letter-spacing: -0.01em; }
    .rh-sub { font-size: 13px; color: #555; margin-top: 1px; }
    .rh-pos-right { text-align: right; flex-shrink: 0; }
    .rh-pos-val { font-size: 16px; font-weight: 600; color: #FFF; font-feature-settings: 'tnum'; }
    .rh-pos-pl { font-size: 13px; font-feature-settings: 'tnum'; margin-top: 1px; }
    .rh-pos-pl.up { color: #00D64F; }
    .rh-pos-pl.down { color: #FF5000; }

    /* ===== TRADE CARD ===== */
    .rh-trade {
        display: flex; align-items: center; height: 56px;
        padding: 0 4px; border-bottom: 1px solid #111;
    }
    .rh-trade-icon {
        width: 32px; height: 32px; border-radius: 16px;
        display: flex; align-items: center; justify-content: center;
        font-weight: 700; font-size: 10px; flex-shrink: 0; margin-right: 12px;
    }
    .rh-trade-left { flex: 1; }
    .rh-trade-ticker { font-size: 14px; font-weight: 600; color: #FFF; }
    .rh-trade-sub { font-size: 11px; color: #555; }
    .rh-trade-right { text-align: right; }
    .rh-trade-pnl { font-size: 14px; font-weight: 600; font-feature-settings: 'tnum'; }
    .rh-trade-pnl.up { color: #00D64F; }
    .rh-trade-pnl.down { color: #FF5000; }
    .rh-trade-date { font-size: 10px; color: #555; }

    /* ===== GOAL BAR ===== */
    .rh-goal { margin: 12px 0; }
    .rh-goal-header { display: flex; justify-content: space-between; margin-bottom: 6px; }
    .rh-goal-label { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: #555; }
    .rh-goal-pct { font-size: 11px; font-weight: 700; color: #00D64F; }
    .rh-goal-track { height: 4px; background: #1A1A1A; border-radius: 2px; overflow: hidden; }
    .rh-goal-fill { height: 100%; background: #00D64F; border-radius: 2px; transition: width 0.5s; }

    /* ===== STREAK ===== */
    .rh-streak {
        display: flex; align-items: center; gap: 8px;
        padding: 10px 12px; background: #0A0A0A; border: 1px solid #1A1A1A;
        margin: 8px 0;
    }
    .rh-streak-num { font-size: 24px; font-weight: 800; color: #FF6B00; }
    .rh-streak-text { font-size: 12px; color: #555; line-height: 1.3; }
    .rh-streak-text b { color: #FFF; }

    /* ===== CASH BAR ===== */
    .rh-cash {
        display: flex; justify-content: space-between; align-items: center;
        padding: 14px 12px; background: #0A0A0A; border: 1px solid #1A1A1A; margin: 12px 0;
    }

    .rh-footer {
        text-align: center; font-size: 10px; color: #333;
        letter-spacing: 0.05em; text-transform: uppercase; padding: 24px 0 12px 0;
    }

    .modebar { display: none !important; }

    /* ===== TRADE HISTORY CARD ===== */
    .rh-th-card {
        background: #0A0A0A; border: 1px solid #1A1A1A; margin: 8px 0;
        overflow: hidden;
    }
    .rh-th-header {
        display: flex; align-items: center; padding: 12px 14px;
        border-bottom: 1px solid #1A1A1A;
    }
    .rh-th-badge {
        width: 36px; height: 36px; border-radius: 18px;
        display: flex; align-items: center; justify-content: center;
        font-weight: 700; font-size: 12px; flex-shrink: 0; margin-right: 10px;
    }
    .rh-th-badge.buy { background: rgba(0,214,79,0.15); color: #00D64F; }
    .rh-th-badge.sell { background: rgba(255,80,0,0.15); color: #FF5000; }
    .rh-th-title { font-size: 15px; font-weight: 600; color: #FFF; }
    .rh-th-subtitle { font-size: 11px; color: #555; margin-top: 1px; }
    .rh-th-pnl-col { margin-left: auto; text-align: right; }
    .rh-th-pnl { font-size: 15px; font-weight: 700; font-feature-settings: 'tnum'; }
    .rh-th-pnl.up { color: #00D64F; }
    .rh-th-pnl.down { color: #FF5000; }
    .rh-th-pnl-pct { font-size: 11px; color: #555; }

    .rh-th-body { padding: 0; }
    .rh-th-row {
        display: flex; justify-content: space-between; align-items: center;
        padding: 8px 14px; border-bottom: 1px solid #111;
    }
    .rh-th-row:last-child { border-bottom: none; }
    .rh-th-label { font-size: 11px; color: #555; text-transform: uppercase; letter-spacing: 0.04em; }
    .rh-th-val { font-size: 13px; color: #FFF; font-weight: 500; text-align: right; max-width: 60%; }

    .rh-th-section {
        padding: 10px 14px; border-top: 1px solid #1A1A1A;
    }
    .rh-th-section-title {
        font-size: 10px; font-weight: 700; text-transform: uppercase;
        letter-spacing: 0.06em; color: #555; margin-bottom: 6px;
    }
    .rh-th-reason {
        font-size: 12px; color: #888; line-height: 1.4; margin: 3px 0;
    }
    .rh-th-reason strong { color: #FFF; }

    /* ===== CALENDAR HEATMAP ===== */
    .rh-cal {
        display: grid; grid-template-columns: repeat(7, 1fr);
        gap: 2px; margin: 8px 0;
    }
    .rh-cal-head {
        font-size: 9px; font-weight: 700; color: #555;
        text-align: center; padding: 4px 0; text-transform: uppercase;
    }
    .rh-cal-day {
        aspect-ratio: 1; display: flex; align-items: center; justify-content: center;
        font-size: 10px; font-weight: 600; color: #555; border-radius: 3px;
    }
    .rh-cal-day.win { background: rgba(0,214,79,0.2); color: #00D64F; }
    .rh-cal-day.loss { background: rgba(255,80,0,0.2); color: #FF5000; }
    .rh-cal-day.neutral { background: #1A1A1A; color: #555; }
    .rh-cal-day.empty { background: transparent; }

    /* ===== STRATEGY STATS ===== */
    .rh-strat {
        display: flex; align-items: center; padding: 10px 0;
        border-bottom: 1px solid #111;
    }
    .rh-strat:last-child { border-bottom: none; }
    .rh-strat-name { font-size: 13px; font-weight: 600; color: #FFF; flex: 1; }
    .rh-strat-stat { text-align: center; padding: 0 8px; }
    .rh-strat-stat-val { font-size: 13px; font-weight: 600; color: #FFF; }
    .rh-strat-stat-label { font-size: 9px; color: #555; text-transform: uppercase; }

    @media (max-width: 480px) {
        .block-container { padding-left: 12px !important; padding-right: 12px !important; }
        .rh-hero-value { font-size: 32px; }
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
    st.error(f"Alpaca connection failed: {type(e).__name__}")
    st.stop()

equity = float(account.equity)
cash = float(account.cash)
buying_power = float(account.buying_power)
positions_value = sum(float(p.market_value) for p in positions)
total_pl = sum(float(p.unrealized_pl) for p in positions)
total_pl_pct = (total_pl / equity * 100) if equity > 0 else 0

# ========== HEADER ==========
if clock.is_open:
    st.markdown(f'<div style="text-align:right;"><span class="rh-status"><span class="rh-dot open"></span><span style="color:#00D64F;">OPEN</span></span></div>', unsafe_allow_html=True)
else:
    st.markdown(f'<div style="text-align:right;"><span class="rh-status"><span class="rh-dot closed"></span><span style="color:#FF5000;">CLOSED</span></span></div>', unsafe_allow_html=True)

pl_sign = "+" if total_pl >= 0 else ""
pl_cls = "up" if total_pl >= 0 else "down"

st.markdown(f"""
<div style="padding-top:2px;">
    <div class="rh-hero-value">${equity:,.2f}</div>
    <div class="rh-change {pl_cls}">{pl_sign}${total_pl:,.2f} ({pl_sign}{total_pl_pct:.2f}%) today</div>
</div>
""", unsafe_allow_html=True)

# ========== CHART ==========
chart_dates = []
chart_values = []

try:
    ph = trading_client.get_portfolio_history(period="1M", timeframe="1D")
    if ph and ph.timestamp and ph.equity and len(ph.timestamp) > 1:
        chart_dates = [datetime.fromtimestamp(t) for t in ph.timestamp]
        chart_values = list(ph.equity)
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
    except Exception:
        pass

if chart_dates and chart_values and len(chart_dates) > 1:
    is_up = chart_values[-1] >= chart_values[0]
    line_color = "#00D64F" if is_up else "#FF5000"
    r = int(line_color[1:3], 16)
    g = int(line_color[3:5], 16)
    b = int(line_color[5:7], 16)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=chart_dates, y=chart_values, mode="lines",
        line=dict(color=line_color, width=2.5, shape="spline"),
        fill="tozeroy", fillcolor=f"rgba({r},{g},{b},0.08)",
        hoverinfo="x+y", showlegend=False,
    ))
    fig.update_layout(
        height=220, margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False, fixedrange=True),
        yaxis=dict(visible=False, fixedrange=False),
        hovermode="x unified",
        hoverlabel=dict(bgcolor="#1A1A1A", bordercolor="#333",
                        font=dict(size=13, color="#FFF", family="Inter")),
        dragmode=False,
    )
    st.plotly_chart(fig, use_container_width=True, config={
        "responsive": True, "displayModeBar": False, "displaylogo": False,
        "scrollZoom": False, "staticPlot": False,
    })
else:
    st.markdown('<div style="height:220px;"></div>', unsafe_allow_html=True)

# ========== STAT PILLS ==========
perf = get_performance_stats()
streak = get_streak()
trades_today = get_trade_count_today()

stat_html = '<div class="rh-pills">'
for label, val in [
    ("CASH", f"${cash:,.0f}"),
    ("INVESTED", f"${positions_value:,.0f}"),
    ("P&L", f"${total_pl:+,.0f}"),
    ("WIN RATE", f"{perf['win_rate']}%" if perf['total_trades'] > 0 else "--"),
    ("TRADES", str(perf['total_trades'])),
]:
    stat_html += f'<div class="rh-pill"><div class="rh-pill-label">{label}</div><div class="rh-pill-val">{val}</div></div>'
stat_html += '</div>'
st.markdown(stat_html, unsafe_allow_html=True)

# ========== STREAK + GOAL ==========
col1, col2 = st.columns([1, 2])

with col1:
    if streak > 0:
        st.markdown(f"""
        <div class="rh-streak">
            <div class="rh-streak-num">{streak}</div>
            <div class="rh-streak-text"><b>day streak</b><br>{trades_today} trades today</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="rh-streak">
            <div class="rh-streak-num" style="color:#555;">0</div>
            <div class="rh-streak-text"><b>no streak yet</b><br>{trades_today} trades today</div>
        </div>
        """, unsafe_allow_html=True)

with col2:
    goal_target = 15000
    goal_pct = min((equity / goal_target) * 100, 100)
    st.markdown(f"""
    <div class="rh-goal" style="margin-top:10px;">
        <div class="rh-goal-header">
            <span class="rh-goal-label">Goal: $15,000</span>
            <span class="rh-goal-pct">{goal_pct:.1f}%</span>
        </div>
        <div class="rh-goal-track">
            <div class="rh-goal-fill" style="width:{goal_pct}%;"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ========== POSITIONS ==========
if positions:
    st.markdown('<div class="rh-section">Positions</div>', unsafe_allow_html=True)

    sector_colors = {
        "tech": ("rgba(88,166,255,0.15)", "#58A6FF"),
        "health": ("rgba(139,92,246,0.15)", "#8B5CF6"),
        "consumer": ("rgba(236,72,153,0.15)", "#EC4899"),
        "industrial": ("rgba(245,158,11,0.15)", "#F59E0B"),
        "telecom": ("rgba(6,182,212,0.15)", "#06B6D4"),
        "finance": ("rgba(34,197,94,0.15)", "#22C55E"),
        "other": ("rgba(85,85,85,0.2)", "#555"),
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

    # ========== VS SPY ==========
    st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)
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
                    line=dict(color="#00D64F", width=2.5, shape="spline"),
                    hoverinfo="name+y",
                ))
            fig2.add_trace(go.Scatter(
                x=spy_dates, y=spy_pct, name="SPY",
                line=dict(color="#555", width=1.5, shape="spline", dash="dot"),
                hoverinfo="name+y",
            ))
            fig2.update_layout(
                height=180, margin=dict(l=0, r=0, t=0, b=0),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(visible=False, fixedrange=True),
                yaxis=dict(visible=False, fixedrange=True),
                hovermode="x unified",
                hoverlabel=dict(bgcolor="#1A1A1A", bordercolor="#333",
                                font=dict(size=12, color="#FFF", family="Inter")),
                showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                            font=dict(size=11, color="#555"), bgcolor="rgba(0,0,0,0)", borderwidth=0),
                dragmode=False,
            )
            st.plotly_chart(fig2, use_container_width=True, config={
                "responsive": True, "displayModeBar": False, "displaylogo": False,
            })
    except Exception:
        pass

else:
    st.markdown("""
    <div style="text-align:center;padding:48px 24px;">
        <div style="font-size:16px;font-weight:600;color:#FFF;margin-bottom:6px;">No positions</div>
        <div style="font-size:13px;color:#555;">Bot scans 280+ stocks every 10 min.</div>
    </div>
    """, unsafe_allow_html=True)

# ========== PERFORMANCE ==========
if perf["total_trades"] > 0:
    st.markdown('<div class="rh-section">Performance</div>', unsafe_allow_html=True)

    best, worst = get_best_worst_trade()
    best_text = f"{best['symbol']} +${best['pnl']:,.2f}" if best else "--"
    worst_text = f"{worst['symbol']} ${worst['pnl']:,.2f}" if worst else "--"

    perf_html = f"""
    <div class="rh-pills" style="grid-template-columns: repeat(3, 1fr);">
        <div class="rh-pill">
            <div class="rh-pill-label">PROFIT FACTOR</div>
            <div class="rh-pill-val">{perf['profit_factor']}</div>
        </div>
        <div class="rh-pill">
            <div class="rh-pill-label">BEST TRADE</div>
            <div class="rh-pill-val" style="color:#00D64F;font-size:11px;">{best_text}</div>
        </div>
        <div class="rh-pill">
            <div class="rh-pill-label">WORST TRADE</div>
            <div class="rh-pill-val" style="color:#FF5000;font-size:11px;">{worst_text}</div>
        </div>
    </div>
    """
    st.markdown(perf_html, unsafe_allow_html=True)

# ========== TRADE HISTORY ==========
full_history = get_full_trade_history(20)
if full_history:
    st.markdown('<div class="rh-section">Trade History</div>', unsafe_allow_html=True)

    for trade in full_history:
        symbol = trade["symbol"]
        entry = trade["avg_entry_price"] or 0
        exit_p = trade["exit_price"] or 0
        pnl = trade["pnl"] or 0
        qty = trade["qty"] or 0
        reason = trade["exit_reason"] or ""
        sector = trade["sector"] or "Other"
        opened = trade["opened_at"] or ""
        closed = trade["closed_at"] or ""
        hold_hours = trade.get("hold_hours", 0)
        journal = trade.get("journal", {})

        pnl_pct = ((exit_p / entry - 1) * 100) if entry > 0 else 0
        pl_sign = "+" if pnl >= 0 else ""
        pl_cls = "up" if pnl >= 0 else "down"
        badge_cls = "buy" if pnl >= 0 else "sell"

        try:
            opened_dt = datetime.fromisoformat(opened)
            opened_str = opened_dt.strftime("%b %d, %I:%M %p")
        except:
            opened_str = opened[:10] if opened else "--"
        try:
            closed_dt = datetime.fromisoformat(closed)
            closed_str = closed_dt.strftime("%b %d, %I:%M %p")
        except:
            closed_str = closed[:10] if closed else "--"

        if hold_hours >= 24:
            hold_str = f"{hold_hours/24:.1f}d"
        elif hold_hours >= 1:
            hold_str = f"{hold_hours:.0f}h"
        else:
            hold_str = f"{hold_hours*60:.0f}m"

        reasons = journal.get("reasons", [])
        strategy = journal.get("strategy", "")
        indicators = journal.get("indicators", {})
        sharia = journal.get("sharia", {})

        card_html = f"""
        <div class="rh-th-card">
            <div class="rh-th-header">
                <div class="rh-th-badge {badge_cls}">{symbol[:2]}</div>
                <div>
                    <div class="rh-th-title">{symbol}</div>
                    <div class="rh-th-subtitle">{sector} &bull; {opened_str}</div>
                </div>
                <div class="rh-th-pnl-col">
                    <div class="rh-th-pnl {pl_cls}">{pl_sign}${pnl:,.2f}</div>
                    <div class="rh-th-pnl-pct">{pl_sign}{pnl_pct:.1f}%</div>
                </div>
            </div>
            <div class="rh-th-body">
                <div class="rh-th-row">
                    <span class="rh-th-label">Entry</span>
                    <span class="rh-th-val">${entry:.2f} &times; {qty:.0f} shares</span>
                </div>
                <div class="rh-th-row">
                    <span class="rh-th-label">Exit</span>
                    <span class="rh-th-val">${exit_p:.2f}</span>
                </div>
                <div class="rh-th-row">
                    <span class="rh-th-label">Hold</span>
                    <span class="rh-th-val">{hold_str}</span>
                </div>
                <div class="rh-th-row">
                    <span class="rh-th-label">Exit Reason</span>
                    <span class="rh-th-val">{reason[:60]}</span>
                </div>
        """
        if strategy:
            card_html += f"""
                <div class="rh-th-row">
                    <span class="rh-th-label">Strategy</span>
                    <span class="rh-th-val">{strategy}</span>
                </div>
            """
        if sharia and sharia.get("debt") is not None:
            card_html += f"""
                <div class="rh-th-row">
                    <span class="rh-th-label">Sharia Debt</span>
                    <span class="rh-th-val">{sharia['debt']}%</span>
                </div>
            """
        card_html += "</div>"

        if reasons:
            card_html += '<div class="rh-th-section"><div class="rh-th-section-title">Why I Bought</div>'
            for r in reasons[:3]:
                card_html += f'<div class="rh-th-reason">&bull; <strong>{r}</strong></div>'
            card_html += "</div>"

        if indicators:
            rsi = indicators.get("rsi")
            adx = indicators.get("adx")
            atr = indicators.get("atr")
            if rsi or adx:
                card_html += '<div class="rh-th-section"><div class="rh-th-section-title">Indicators at Entry</div><div style="display:flex;gap:16px;">'
                if rsi:
                    card_html += f'<div class="rh-th-reason">RSI(14): <strong>{rsi:.1f}</strong></div>'
                if adx:
                    card_html += f'<div class="rh-th-reason">ADX: <strong>{adx:.1f}</strong></div>'
                if atr:
                    card_html += f'<div class="rh-th-reason">ATR: <strong>${atr:.2f}</strong></div>'
                card_html += "</div></div>"

        card_html += "</div>"
        st.markdown(card_html, unsafe_allow_html=True)

# ========== CALENDAR HEATMAP ==========
calendar_data = get_calendar_pnl()
if calendar_data:
    st.markdown('<div class="rh-section">Monthly P&L</div>', unsafe_allow_html=True)

    from datetime import date
    today = date.today()
    year = today.year
    month = today.month

    cal_html = '<div class="rh-cal">'
    for head in ["S", "M", "T", "W", "T", "F", "S"]:
        cal_html += f'<div class="rh-cal-head">{head}</div>'

    import calendar as cal_mod
    cal = cal_mod.monthcalendar(year, month)
    pnl_map = {r["day"]: r["daily_pnl"] for r in calendar_data if r["day"]}

    for week in cal:
        for day in week:
            if day == 0:
                cal_html += '<div class="rh-cal-day empty"></div>'
            else:
                day_str = f"{year}-{month:02d}-{day:02d}"
                if day_str in pnl_map:
                    pnl = pnl_map[day_str]
                    cls = "win" if pnl > 0 else "loss" if pnl < 0 else "neutral"
                    cal_html += f'<div class="rh-cal-day {cls}">{day}</div>'
                elif day <= today.day:
                    cal_html += f'<div class="rh-cal-day neutral">{day}</div>'
                else:
                    cal_html += f'<div class="rh-cal-day empty">{day}</div>'
    cal_html += "</div>"

    month_pnl = sum(r["daily_pnl"] for r in calendar_data
                    if r["day"] and r["day"][:7] == f"{year}-{month:02d}")
    mp_sign = "+" if month_pnl >= 0 else ""
    mp_cls = "up" if month_pnl >= 0 else "down"
    cal_html += f'<div style="text-align:center;margin-top:8px;"><span class="rh-th-pnl {mp_cls}" style="font-size:14px;">{mp_sign}${month_pnl:,.2f}</span> <span style="font-size:11px;color:#555;">this month</span></div>'
    st.markdown(cal_html, unsafe_allow_html=True)

# ========== STRATEGY STATS ==========
strat_stats = get_stats_by_strategy()
if strat_stats:
    st.markdown('<div class="rh-section">By Strategy</div>', unsafe_allow_html=True)

    strat_html = ""
    for s in strat_stats:
        wr_cls = "up" if s["win_rate"] >= 50 else "down"
        pnl_cls = "up" if s["total_pnl"] >= 0 else "down"
        pnl_sign = "+" if s["total_pnl"] >= 0 else ""
        strat_html += f"""
        <div class="rh-strat">
            <div class="rh-strat-name">{s['strategy']}</div>
            <div class="rh-strat-stat">
                <div class="rh-strat-stat-val {wr_cls}">{s['win_rate']}%</div>
                <div class="rh-strat-stat-label">Win Rate</div>
            </div>
            <div class="rh-strat-stat">
                <div class="rh-strat-stat-val">{s['trades']}</div>
                <div class="rh-strat-stat-label">Trades</div>
            </div>
            <div class="rh-strat-stat">
                <div class="rh-strat-stat-val {pnl_cls}">{pnl_sign}${s['total_pnl']:,.0f}</div>
                <div class="rh-strat-stat-label">P&L</div>
            </div>
        </div>
        """
    st.markdown(strat_html, unsafe_allow_html=True)

# ========== CASH ==========
st.markdown(f"""
<div class="rh-cash">
    <div>
        <div class="rh-pill-label">CASH</div>
        <div class="rh-pill-val" style="font-size:15px;">${cash:,.2f}</div>
    </div>
    <div style="text-align:right;">
        <div class="rh-pill-label">BUYING POWER</div>
        <div class="rh-pill-val" style="font-size:15px;">${buying_power:,.2f}</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ========== FOOTER ==========
st.markdown(f"""
<div class="rh-footer">
    {datetime.now().strftime('%I:%M %p')} &bull; Paper
</div>
""")
