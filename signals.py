import pandas as pd
import numpy as np
import yfinance as yf
from config import (
    RSI_OVERBOUGHT, RSI_OVERSOLD, RSI_NEUTRAL,
    VOLUME_SURGE_PCT, FAST_MA, SLOW_MA, TREND_MA
)


def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def compute_macd(series, fast=12, slow=26, signal=9):
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def compute_atr(high, low, close, period=14):
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()


def get_signals(ticker: str, timeframe: str = "daily") -> dict:
    stock = yf.Ticker(ticker)

    if timeframe == "daily":
        df = stock.history(period="1y", interval="1d")
    elif timeframe == "4h":
        df = stock.history(period="60d", interval="1h")
        # Resample to 4h
        df = df.resample("4h").agg({
            "Open": "first", "High": "max", "Low": "min",
            "Close": "last", "Volume": "sum"
        }).dropna()
    else:
        df = stock.history(period="6mo", interval="1d")

    if df.empty or len(df) < TREND_MA:
        return {"ticker": ticker, "error": "Insufficient data", "signal": "HOLD"}

    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    volume = df["Volume"]

    # Indicators
    rsi = compute_rsi(close)
    macd_line, signal_line, histogram = compute_macd(close)
    atr = compute_atr(high, low, close)
    sma_200 = close.rolling(TREND_MA).mean()
    sma_fast = close.rolling(FAST_MA).mean()
    sma_slow = close.rolling(SLOW_MA).mean()
    volume_sma = volume.rolling(20).mean()

    latest = {
        "price": round(close.iloc[-1], 2),
        "rsi": round(rsi.iloc[-1], 2),
        "macd": round(macd_line.iloc[-1], 4),
        "macd_signal": round(signal_line.iloc[-1], 4),
        "macd_hist": round(histogram.iloc[-1], 4),
        "atr": round(atr.iloc[-1], 2),
        "sma_200": round(sma_200.iloc[-1], 2),
        "sma_fast": round(sma_fast.iloc[-1], 2),
        "sma_slow": round(sma_slow.iloc[-1], 2),
        "volume": int(volume.iloc[-1]),
        "volume_sma": int(volume_sma.iloc[-1]),
    }

    # Previous values for crossover detection
    prev = {
        "macd": round(macd_line.iloc[-2], 4),
        "macd_signal": round(signal_line.iloc[-2], 4),
        "macd_hist": round(histogram.iloc[-2], 4),
    }

    # Signal logic
    signal = "HOLD"
    reasons = []

    above_200sma = latest["price"] > latest["sma_200"]
    rsi_ok = latest["rsi"] < RSI_NEUTRAL
    macd_cross_up = prev["macd"] <= prev["macd_signal"] and latest["macd"] > latest["macd_signal"]
    macd_cross_down = prev["macd"] >= prev["macd_signal"] and latest["macd"] < latest["macd_signal"]
    volume_surge = latest["volume"] > latest["volume_sma"] * VOLUME_SURGE_PCT

    # Buy signal
    if above_200sma and rsi_ok and macd_cross_up and volume_surge:
        signal = "BUY"
        reasons.append("Above 200 SMA")
        reasons.append(f"RSI {latest['rsi']} < {RSI_NEUTRAL}")
        reasons.append("MACD crossed above signal")
        reasons.append(f"Volume surge {latest['volume']}/{latest['volume_sma']}")

    # Sell signal
    elif latest["rsi"] > RSI_OVERBOUGHT:
        signal = "SELL"
        reasons.append(f"RSI overbought {latest['rsi']}")
    elif macd_cross_down and latest["price"] < latest["sma_200"]:
        signal = "SELL"
        reasons.append("MACD bearish cross below 200 SMA")

    # Trailing stop check
    stop_price = latest["price"] - (latest["atr"] * 2)

    return {
        "ticker": ticker,
        "signal": signal,
        "reasons": reasons,
        "indicators": latest,
        "stop_price": round(stop_price, 2),
        "stop_pct": round((latest["price"] - stop_price) / latest["price"] * 100, 2),
    }


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
    signals = scan_universe(["AAPL", "MSFT", "NVDA", "TSLA"])
    for s in signals:
        print(f"{s['ticker']}: {s['signal']} | {s.get('reasons', [])}")
