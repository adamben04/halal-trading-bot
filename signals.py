import os
import json
import time
import pandas as pd
import numpy as np
import yfinance as yf
from config import ATR_STOP_MULTIPLIER

CACHE_DIR = "data/signal_cache"
CACHE_TTL = 1800  # 30 minutes


def _cache_path(ticker):
    os.makedirs(CACHE_DIR, exist_ok=True)
    return os.path.join(CACHE_DIR, f"{ticker}.json")


def _read_cache(ticker):
    path = _cache_path(ticker)
    if not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            data = json.load(f)
        if time.time() - data.get("ts", 0) < CACHE_TTL:
            return data["result"]
    except Exception:
        pass
    return None


def _write_cache(ticker, result):
    try:
        path = _cache_path(ticker)
        with open(path, "w") as f:
            json.dump({"ts": time.time(), "result": result}, f)
    except Exception:
        pass


def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def compute_atr(high, low, close, period=14):
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()


def compute_adx(high, low, close, period=14):
    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)
    atr = compute_atr(high, low, close, period)
    plus_di = 100 * (plus_dm.rolling(period).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(period).mean() / atr)
    dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan))
    adx = dx.rolling(period).mean()
    return adx, plus_di, minus_di


def get_signals(ticker: str) -> dict:
    cached = _read_cache(ticker)
    if cached:
        return cached

    stock = yf.Ticker(ticker)
    df = stock.history(period="60d", interval="1h")

    if df.empty or len(df) < 30:
        return {"ticker": ticker, "error": "Insufficient data", "signal": "HOLD"}

    close = df["Close"]
    high = df["High"]
    low = df["Low"]

    rsi_2 = compute_rsi(close, 2)
    rsi_14 = compute_rsi(close, 14)
    atr = compute_atr(high, low, close)
    adx, plus_di, minus_di = compute_adx(high, low, close)

    donchian_high_20 = high.rolling(20).max()
    donchian_low_20 = low.rolling(20).min()

    sma_50 = close.rolling(50).mean()
    sma_200 = close.rolling(200).mean()

    latest = {
        "price": round(close.iloc[-1], 2),
        "rsi_2": round(rsi_2.iloc[-1], 2),
        "rsi_14": round(rsi_14.iloc[-1], 2),
        "atr": round(atr.iloc[-1], 2),
        "adx": round(adx.iloc[-1], 2),
        "donchian_high_20": round(donchian_high_20.iloc[-1], 2),
        "donchian_low_20": round(donchian_low_20.iloc[-1], 2),
        "sma_50": round(sma_50.iloc[-1], 2),
        "sma_200": round(sma_200.iloc[-1], 2),
    }

    prev_price = round(close.iloc[-2], 2)

    signal = "HOLD"
    reasons = []
    stop_price = None
    take_profit = None
    strategy = None

    # Strategy 1: RSI(2) Mean Reversion
    if rsi_2.iloc[-1] < 10 and latest["adx"] > 20:
        signal = "BUY"
        strategy = "RSI(2) Mean Reversion"
        reasons.append(f"RSI(2) = {latest['rsi_2']} (< 10, deeply oversold)")
        reasons.append(f"ADX = {latest['adx']} (> 20, trend exists)")
        stop_price = latest["price"] - (latest["atr"] * ATR_STOP_MULTIPLIER)
        take_profit = latest["price"] * 1.03

    # Strategy 2: Donchian Breakout
    elif (prev_price < donchian_high_20.iloc[-2] and
          latest["price"] >= latest["donchian_high_20"] and
          latest["adx"] > 25):
        signal = "BUY"
        strategy = "Donchian Breakout"
        reasons.append(f"Price {latest['price']} broke 20-period high {latest['donchian_high_20']}")
        reasons.append(f"ADX = {latest['adx']} (> 25, strong trend)")
        stop_price = latest["donchian_low_20"]
        take_profit = latest["price"] + (latest["atr"] * 3)

    # Sell signals
    elif rsi_14.iloc[-1] > 80:
        signal = "SELL"
        reasons.append(f"RSI(14) = {latest['rsi_14']} (> 80, overbought)")

    elif (prev_price > donchian_low_20.iloc[-2] and
          latest["price"] <= latest["donchian_low_20"] and
          latest["adx"] > 25):
        signal = "SELL"
        reasons.append("Price broke below 20-period low with strong trend")

    if stop_price is not None:
        stop_price = round(stop_price, 2)
    if take_profit is not None:
        take_profit = round(take_profit, 2)

    result = {
        "ticker": ticker,
        "signal": signal,
        "strategy": strategy,
        "reasons": reasons,
        "indicators": latest,
        "stop_price": stop_price,
        "take_profit": take_profit,
    }
    if stop_price and latest["price"] > 0:
        result["stop_pct"] = round((latest["price"] - stop_price) / latest["price"] * 100, 2)
    _write_cache(ticker, result)
    return result


def scan_universe(tickers: list) -> list:
    signals = []
    for ticker in tickers:
        try:
            result = get_signals(ticker)
            signals.append(result)
        except Exception as e:
            signals.append({"ticker": ticker, "error": str(e), "signal": "HOLD"})
    return signals


if __name__ == "__main__":
    signals = scan_universe(["AAPL", "MSFT", "NVDA", "TSLA", "GOOGL", "AMZN"])
    for s in signals:
        strat = s.get("strategy", "N/A")
        print(f"{s['ticker']}: {s['signal']} [{strat}] | {s.get('reasons', [])}")
