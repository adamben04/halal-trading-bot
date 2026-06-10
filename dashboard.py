import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from database import get_db, get_open_positions, get_all_trades, get_daily_snapshots, get_performance_stats

st.set_page_config(page_title="Halal Trading Bot", layout="wide")
st.title("Halal Trading Bot Dashboard")

# Sidebar
page = st.sidebar.selectbox("Navigate", ["Overview", "Positions", "Trades", "Performance", "Journal"])

# Overview
if page == "Overview":
    snapshots = get_daily_snapshots()
    positions = get_open_positions()

    col1, col2, col3, col4 = st.columns(4)

    if snapshots:
        latest = snapshots[-1]
        prev = snapshots[-2] if len(snapshots) > 1 else latest
        daily_pnl = latest.get("daily_pnl", 0)
        total_return = latest.get("total_return_pct", 0)

        col1.metric("Equity", f"${latest['equity']:,.2f}", f"{total_return:+.2f}%")
        col2.metric("Cash", f"${latest['cash']:,.2f}")
        col3.metric("Positions", f"${latest['positions_value']:,.2f}")
        col4.metric("Daily P&L", f"${daily_pnl:,.2f}")

        # Equity curve
        dates = [s["date"] for s in snapshots]
        equities = [s["equity"] for s in snapshots]

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=dates, y=equities, mode="lines", name="Portfolio"))
        fig.update_layout(title="Equity Curve", xaxis_title="Date", yaxis_title="Equity ($)")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No data yet. Bot hasn't run.")

    # Open positions table
    st.subheader("Open Positions")
    if positions:
        df = pd.DataFrame(positions)
        st.dataframe(df[["symbol", "qty", "avg_entry_price", "current_price",
                         "unrealized_pl", "unrealized_plpc"]], use_container_width=True)
    else:
        st.info("No open positions")

# Positions
elif page == "Positions":
    positions = get_open_positions()
    st.subheader(f"Open Positions ({len(positions)})")

    if positions:
        for pos in positions:
            with st.expander(f"{pos['symbol']} — {pos['qty']} shares"):
                st.write(f"Entry Price: ${pos['avg_entry_price']}")
                st.write(f"Opened: {pos['opened_at']}")
                st.write(f"Sector: {pos.get('sector', 'Unknown')}")
                if st.button(f"Close {pos['symbol']}", key=f"close_{pos['id']}"):
                    st.warning("Manual close not implemented yet")
    else:
        st.info("No open positions")

# Trades
elif page == "Trades":
    trades = get_all_trades()
    st.subheader(f"Recent Trades ({len(trades)})")

    if trades:
        df = pd.DataFrame(trades)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No trades yet")

# Performance
elif page == "Performance":
    stats = get_performance_stats()
    st.subheader("Performance Stats")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Trades", stats["total_trades"])
    col2.metric("Win Rate", f"{stats['win_rate']}%")
    col3.metric("Avg P&L", f"${stats['avg_pnl']}")
    col4.metric("Profit Factor", f"{stats['profit_factor']}")

    st.write(f"Total P&L: ${stats['total_pnl']}")
    st.write(f"Wins: {stats['wins']} | Losses: {stats['losses']}")

    # Trade distribution
    trades = get_all_trades()
    if trades:
        df = pd.DataFrame(trades)
        if "price" in df.columns:
            st.bar_chart(df["price"].value_counts().head(20))

# Journal
elif page == "Journal":
    st.subheader("Trade Journal")
    st.info("Journal entries will appear here after trades are logged")

    with st.form("new_entry"):
        pre = st.text_area("Pre-Trade Analysis")
        market = st.selectbox("Market Conditions", ["Bull", "Bear", "Sideways", "Volatile"])
        lessons = st.text_area("Lessons Learned")
        if st.form_submit_button("Save"):
            st.success("Entry saved (not implemented yet)")
