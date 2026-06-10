import pandas as pd
import numpy as np
import yfinance as yf
import warnings
warnings.filterwarnings("ignore")

INITIAL_CAPITAL = 100000
RISK_PER_TRADE = 0.01

def compute_rsi(s, p=14):
    d = s.diff()
    g = d.where(d > 0, 0).rolling(p).mean()
    l = (-d.where(d < 0, 0)).rolling(p).mean()
    return 100 - (100 / (1 + g / l))

def compute_macd(s):
    ef = s.ewm(span=12, adjust=False).mean()
    es = s.ewm(span=26, adjust=False).mean()
    ml = ef - es
    sl = ml.ewm(span=9, adjust=False).mean()
    return ml, sl, ml - sl

def compute_atr(h, l, c, p=14):
    tr = pd.concat([h - l, (h - c.shift(1)).abs(), (l - c.shift(1)).abs()], axis=1).max(axis=1)
    return tr.rolling(p).mean()

def backtest(ticker, strategy="momentum"):
    stock = yf.Ticker(ticker)
    df = stock.history(period="2y", interval="1d")
    if df.empty or len(df) < 250:
        return None

    c, h, lo, v = df["Close"], df["High"], df["Low"], df["Volume"]
    rsi = compute_rsi(c)
    macd_l, macd_s, macd_h = compute_macd(c)
    atr = compute_atr(h, lo, c)
    sma50 = c.rolling(50).mean()
    sma200 = c.rolling(200).mean()
    vol_sma = v.rolling(20).mean()

    capital = INITIAL_CAPITAL
    position = 0
    entry_price = 0
    stop_price = 0
    best_price = 0
    trades = []
    equity = []

    start = 200
    for i in range(start, len(df)):
        price = c.iloc[i]
        rsi_val = rsi.iloc[i]
        m_val, ms_val = macd_l.iloc[i], macd_s.iloc[i]
        pm_val, pms_val = macd_l.iloc[i-1], macd_s.iloc[i-1]
        a_val = atr.iloc[i]
        s50_val = sma50.iloc[i]
        s200_val = sma200.iloc[i]
        vol_val = v.iloc[i]
        vs_val = vol_sma.iloc[i]

        if pd.isna(s200_val) or pd.isna(a_val) or pd.isna(vs_val) or pd.isna(s50_val):
            equity.append(capital + position * price)
            continue

        # Position management
        if position > 0:
            best_price = max(best_price, price)
            trailing_stop = best_price - (a_val * 2.5)

            exit_reason = None
            if price <= stop_price:
                exit_reason = "initial_stop"
            elif price <= trailing_stop:
                exit_reason = "trailing_stop"
            elif rsi_val > 80:
                exit_reason = "rsi_overbought"
            elif m_val < ms_val and pm_val >= pms_val and price < s50_val:
                exit_reason = "macd_bearish"

            if exit_reason:
                pnl = (price - entry_price) * position
                capital += position * price
                trades.append({"entry": entry_price, "exit": price, "pnl": pnl, "reason": exit_reason})
                position = 0

        # Entry logic
        if position == 0:
            bullish = price > s200_val and s50_val > s200_val
            pullback = rsi_val < 55 and rsi_val > 30
            macd_turning = m_val > ms_val and (m_val - ms_val) > (pm_val - pms_val)
            volume_ok = vol_val > vs_val * 0.8

            high_20 = h.iloc[i-20:i].max()

            if strategy == "momentum" and bullish and pullback and macd_turning and volume_ok:
                risk_amount = capital * RISK_PER_TRADE
                risk_per = a_val * 2.5
                if risk_per > 0:
                    qty = int(risk_amount / risk_per)
                    cost = qty * price
                    if qty > 0 and cost <= capital * 0.95:
                        entry_price = price
                        stop_price = price - (a_val * 2.5)
                        best_price = price
                        position = qty
                        capital -= cost

            elif strategy == "breakout" and price > high_20 and price > s200_val and vol_val > vs_val * 1.5:
                risk_amount = capital * RISK_PER_TRADE
                risk_per = a_val * 2
                if risk_per > 0:
                    qty = int(risk_amount / risk_per)
                    cost = qty * price
                    if qty > 0 and cost <= capital * 0.95:
                        entry_price = price
                        stop_price = price - (a_val * 2)
                        best_price = price
                        position = qty
                        capital -= cost

        equity.append(capital + position * price)

    # Close remaining position
    if position > 0:
        price = c.iloc[-1]
        pnl = (price - entry_price) * position
        capital += position * price
        trades.append({"entry": entry_price, "exit": price, "pnl": pnl, "reason": "end"})
        position = 0

    final = capital
    total_ret = (final - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100

    wins = [t for t in trades if t["pnl"] > 0]
    losses = [t for t in trades if t["pnl"] <= 0]
    wr = len(wins) / len(trades) * 100 if trades else 0
    pf = sum(t["pnl"] for t in wins) / abs(sum(t["pnl"] for t in losses)) if losses and sum(t["pnl"] for t in losses) != 0 else 999

    eq = pd.Series(equity)
    dr = eq.pct_change(fill_method=None).dropna()
    sharpe = (dr.mean() / dr.std() * np.sqrt(252)) if dr.std() > 0 else 0
    peak = eq.cummax()
    dd = ((eq - peak) / peak).min() * 100

    return {
        "ticker": ticker, "return": round(total_ret, 2), "trades": len(trades),
        "win_rate": round(wr, 1), "profit_factor": round(min(pf, 999), 2),
        "sharpe": round(sharpe, 2), "max_dd": round(dd, 2),
    }


if __name__ == "__main__":
    spy_df = yf.Ticker("SPY").history(period="2y", interval="1d")
    spy_start = spy_df["Close"].iloc[200] if len(spy_df) > 200 else spy_df["Close"].iloc[0]
    spy_ret = (spy_df["Close"].iloc[-1] / spy_start - 1) * 100

    tickers = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA",
               "AVGO", "ORCL", "ADBE", "CRM", "AMD", "QCOM", "TXN",
               "NOW", "PLTR", "CRWD", "DDOG", "ZS", "NET", "SNOW",
               "LRCX", "KLAC", "AMAT", "MRVL", "UBER", "COIN"]

    for strat in ["momentum", "breakout"]:
        print(f"\n{'='*65}")
        print(f"  STRATEGY: {strat.upper()} | 2yr Daily | ${INITIAL_CAPITAL:,.0f}")
        print(f"  SPY Buy & Hold (same period): {spy_ret:+.1f}%")
        print(f"{'='*65}")
        print(f"{'Ticker':<8} {'Return':>8} {'Trades':>7} {'Win%':>6} {'PF':>6} {'Sharpe':>7} {'MaxDD':>8}")
        print(f"{'-'*55}")

        results = []
        for t in tickers:
            r = backtest(t, strat)
            if r:
                results.append(r)

        results.sort(key=lambda x: x["return"], reverse=True)
        for r in results:
            print(f"{r['ticker']:<8} {r['return']:>+7.1f}% {r['trades']:>6} {r['win_rate']:>5.0f}% {r['profit_factor']:>5.1f} {r['sharpe']:>7.2f} {r['max_dd']:>+7.1f}%")

        avg_ret = np.mean([r["return"] for r in results]) if results else 0
        total_trades = sum(r["trades"] for r in results)
        profitable = sum(1 for r in results if r["return"] > 0)
        beat_spy = sum(1 for r in results if r["return"] > spy_ret)

        print(f"\n  Avg Return:   {avg_ret:+.1f}%")
        print(f"  Total Trades: {total_trades}")
        print(f"  Profitable:   {profitable}/{len(results)}")
        print(f"  Beat SPY:     {beat_spy}/{len(results)}")
        print(f"{'='*65}")
