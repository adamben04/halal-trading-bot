import pandas as pd
import numpy as np
import yfinance as yf
import warnings
warnings.filterwarnings("ignore")

INITIAL_CAPITAL = 100000
RISK_PER_TRADE = 0.01
ATR_STOP_MULT = 2.0

def compute_rsi(s, p=14):
    d = s.diff()
    g = d.where(d > 0, 0).rolling(p).mean()
    l = (-d.where(d < 0, 0)).rolling(p).mean()
    return 100 - (100 / (1 + g / l))

def compute_atr(h, l, c, p=14):
    tr = pd.concat([h - l, (h - c.shift(1)).abs(), (l - c.shift(1)).abs()], axis=1).max(axis=1)
    return tr.rolling(p).mean()

def compute_adx(h, l, c, p=14):
    plus_dm = h.diff()
    minus_dm = -l.diff()
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)
    atr = compute_atr(h, l, c, p)
    plus_di = 100 * (plus_dm.rolling(p).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(p).mean() / atr)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    return dx.rolling(p).mean()


def backtest_hybrid(ticker, capital=INITIAL_CAPITAL):
    stock = yf.Ticker(ticker)
    df = stock.history(period="2y", interval="1d")
    if df.empty or len(df) < 250:
        return None

    c, h, lo, v = df["Close"], df["High"], df["Low"], df["Volume"]
    rsi2 = compute_rsi(c, 2)
    rsi14 = compute_rsi(c, 14)
    atr = compute_atr(h, lo, c, 14)
    adx = compute_adx(h, lo, c, 14)
    sma200 = c.rolling(200).mean()
    sma5 = c.rolling(5).mean()
    donchian_high = h.rolling(20).max()
    donchian_low = lo.rolling(10).min()

    cash = capital
    position = 0
    entry_price = 0
    stop_price = 0
    strategy_used = ""
    trades = []
    equity = []
    entry_bar = 0

    for i in range(200, len(df)):
        price = c.iloc[i]
        r2 = rsi2.iloc[i]
        a = atr.iloc[i]
        adx_val = adx.iloc[i]
        s200 = sma200.iloc[i]
        s5 = sma5.iloc[i]
        d_high = donchian_high.iloc[i-1]  # prior bar's 20-day high
        d_low = donchian_low.iloc[i-1]

        if pd.isna(s200) or pd.isna(a) or pd.isna(adx_val):
            equity.append(cash + position * price)
            continue

        # EXIT LOGIC
        if position > 0:
            exit_reason = None

            if strategy_used == "mean_reversion":
                if price > s5:
                    exit_reason = "rsi2_exit"
                elif price <= stop_price:
                    exit_reason = "stop_loss"
            elif strategy_used == "donchian":
                if price < d_low:
                    exit_reason = "donchian_exit"
                elif price <= stop_price:
                    exit_reason = "stop_loss"

            if exit_reason:
                pnl = (price - entry_price) * position
                cash += position * price
                trades.append({
                    "entry": entry_price, "exit": price, "pnl": pnl,
                    "reason": exit_reason, "strategy": strategy_used,
                    "hold_bars": i - entry_bar
                })
                position = 0

        # ENTRY LOGIC
        if position == 0:
            # Strategy 1: RSI(2) Mean Reversion
            if price > s200 and r2 < 5:
                risk_amount = cash * RISK_PER_TRADE
                risk_per = a * ATR_STOP_MULT
                if risk_per > 0:
                    qty = int(risk_amount / risk_per)
                    cost = qty * price
                    if qty > 0 and cost <= cash * 0.95:
                        entry_price = price
                        stop_price = price - (a * ATR_STOP_MULT)
                        strategy_used = "mean_reversion"
                        entry_bar = i
                        position = qty
                        cash -= cost

            # Strategy 2: Donchian Breakout + ADX
            elif price > d_high and adx_val > 25:
                risk_amount = cash * RISK_PER_TRADE
                risk_per = a * ATR_STOP_MULT
                if risk_per > 0:
                    qty = int(risk_amount / risk_per)
                    cost = qty * price
                    if qty > 0 and cost <= cash * 0.95:
                        entry_price = price
                        stop_price = price - (a * ATR_STOP_MULT)
                        strategy_used = "donchian"
                        entry_bar = i
                        position = qty
                        cash -= cost

        equity.append(cash + position * price)

    # Close remaining
    if position > 0:
        price = c.iloc[-1]
        pnl = (price - entry_price) * position
        cash += position * price
        trades.append({
            "entry": entry_price, "exit": price, "pnl": pnl,
            "reason": "end", "strategy": strategy_used,
            "hold_bars": len(df) - 1 - entry_bar
        })
        position = 0

    final = cash
    total_ret = round((final - capital) / capital * 100, 2) if final and capital else 0
    if np.isnan(total_ret) or np.isinf(total_ret):
        total_ret = 0

    mr_trades = [t for t in trades if t["strategy"] == "mean_reversion"]
    dc_trades = [t for t in trades if t["strategy"] == "donchian"]
    wins = [t for t in trades if t["pnl"] > 0]
    losses = [t for t in trades if t["pnl"] <= 0]

    wr = len(wins) / len(trades) * 100 if trades else 0
    avg_win = np.mean([t["pnl"] for t in wins]) if wins else 0
    avg_loss = abs(np.mean([t["pnl"] for t in losses])) if losses else 0
    pf = sum(t["pnl"] for t in wins) / abs(sum(t["pnl"] for t in losses)) if losses and sum(t["pnl"] for t in losses) != 0 else 999

    eq = pd.Series(equity).dropna()
    if len(eq) < 2:
        return None
    dr = eq.pct_change(fill_method=None).dropna()
    sharpe = (dr.mean() / dr.std() * np.sqrt(252)) if dr.std() > 0 else 0
    peak = eq.cummax()
    dd = ((eq - peak) / peak).min() * 100
    avg_hold = np.mean([t["hold_bars"] for t in trades]) if trades else 0

    return {
        "ticker": ticker,
        "return": round(total_ret, 2),
        "trades": len(trades),
        "mr_trades": len(mr_trades),
        "dc_trades": len(dc_trades),
        "win_rate": round(wr, 1),
        "profit_factor": round(min(pf, 999), 2),
        "sharpe": round(sharpe, 2),
        "max_dd": round(dd, 2),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "avg_hold": round(avg_hold, 1),
        "final": round(final, 2),
    }


if __name__ == "__main__":
    spy_df = yf.Ticker("SPY").history(period="2y", interval="1d")
    spy_ret = (float(spy_df["Close"].iloc[-1]) / float(spy_df["Close"].iloc[min(200, len(spy_df)-1)]) - 1) * 100

    qqq_df = yf.Ticker("QQQ").history(period="2y", interval="1d")
    qqq_ret = (float(qqq_df["Close"].iloc[-1]) / float(qqq_df["Close"].iloc[min(200, len(qqq_df)-1)]) - 1) * 100

    tickers = [
        "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA",
        "AVGO", "ORCL", "ADBE", "CRM", "AMD", "QCOM", "TXN",
        "NOW", "PLTR", "CRWD", "DDOG", "ZS", "NET", "SNOW",
        "LRCX", "KLAC", "AMAT", "MRVL", "UBER", "COIN"
    ]

    print(f"\n{'='*80}")
    print(f"  HYBRID ALGO BACKTEST — RSI(2) Mean Reversion + Donchian Breakout")
    print(f"  2yr Daily | ${INITIAL_CAPITAL:,.0f} | 1% risk/trade | 2x ATR stop")
    print(f"  SPY: {spy_ret:+.1f}% | QQQ: {qqq_ret:+.1f}%")
    print(f"{'='*80}")
    print(f"{'Ticker':<8} {'Return':>8} {'Trades':>7} {'MR':>4} {'DC':>4} {'Win%':>6} {'PF':>6} {'Sharpe':>7} {'MaxDD':>8} {'AvgHold':>8}")
    print(f"{'-'*75}")

    results = []
    for t in tickers:
        r = backtest_hybrid(t)
        if r:
            results.append(r)

    results.sort(key=lambda x: x["return"], reverse=True)
    for r in results:
        ret_str = f"{r['return']:>+7.1f}%" if not np.isnan(r['return']) else "    N/A"
        print(f"{r['ticker']:<8} {ret_str} {r['trades']:>6} {r['mr_trades']:>4} {r['dc_trades']:>4} {r['win_rate']:>5.0f}% {r['profit_factor']:>5.1f} {r['sharpe']:>7.2f} {r['max_dd']:>+7.1f}% {r['avg_hold']:>6.1f}d")

    avg_ret = np.nanmean([r["return"] for r in results])
    avg_wr = np.nanmean([r["win_rate"] for r in results if r["trades"] > 0])
    avg_sharpe = np.nanmean([r["sharpe"] for r in results if r["trades"] > 0])
    total_trades = sum(r["trades"] for r in results)
    total_mr = sum(r["mr_trades"] for r in results)
    total_dc = sum(r["dc_trades"] for r in results)
    profitable = sum(1 for r in results if r["return"] > 0)
    beat_spy = sum(1 for r in results if r["return"] > spy_ret)
    beat_qqq = sum(1 for r in results if r["return"] > qqq_ret)
    avg_dd = np.mean([r["max_dd"] for r in results])

    print(f"\n{'='*75}")
    print(f"  SUMMARY")
    print(f"{'='*75}")
    print(f"  Avg Return:       {avg_ret:+.1f}%")
    print(f"  Avg Win Rate:     {avg_wr:.0f}%")
    print(f"  Avg Sharpe:       {avg_sharpe:.2f}")
    print(f"  Avg Max DD:       {avg_dd:.1f}%")
    print(f"  Total Trades:     {total_trades} ({total_mr} MR + {total_dc} DC)")
    print(f"  Profitable:       {profitable}/{len(results)} stocks")
    print(f"  Beat SPY ({spy_ret:+.1f}%):  {beat_spy}/{len(results)}")
    print(f"  Beat QQQ ({qqq_ret:+.1f}%):  {beat_qqq}/{len(results)}")
    print(f"{'='*75}")

    # Strategy breakdown
    all_mr = [t for r in results for t in []]  # placeholder
    print(f"\n  STRATEGY BREAKDOWN")
    print(f"  Mean Reversion trades: {total_mr}")
    print(f"  Donchian Breakout trades: {total_dc}")
    print(f"{'='*75}\n")
