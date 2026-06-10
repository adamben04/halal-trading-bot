import os
from dotenv import load_dotenv

load_dotenv()

# Alpaca API
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY", "")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY", "")
PAPER_TRADING = os.getenv("PAPER_TRADING", "true").lower() == "true"

# Sharia Screening (AAOIFI thresholds)
DEBT_THRESHOLD = 0.33
CASH_THRESHOLD = 0.33
RECEIVABLES_THRESHOLD = 0.49
IMPURE_INCOME_THRESHOLD = 0.05
PROHIBITED_SECTORS = {"Financial Services", "Insurance"}
PROHIBITED_KEYWORDS = ["alcohol", "gambling", "casino", "tobacco", "pork", "adult", "pornography", "weapon of mass destruction"]

# Risk Management
RISK_PER_TRADE = 0.01  # 1% of account per trade
MAX_POSITIONS = 8
MAX_SINGLE_POSITION_PCT = 0.20
MAX_SECTOR_PCT = 0.30
DAILY_LOSS_LIMIT = 0.03
MAX_DRAWDOWN = 0.15
CONSECUTIVE_LOSS_LIMIT = 5
CASH_RESERVE_PCT = 0.25
ATR_STOP_MULTIPLIER = 2.0
MAX_STOP_PCT = 0.07

# Strategy
RSI_OVERBOUGHT = 75
RSI_OVERSOLD = 30
RSI_NEUTRAL = 70
VOLUME_SURGE_PCT = 1.20
FAST_MA = 20
SLOW_MA = 50
TREND_MA = 200

# Universe
TICKER_CACHE_FILE = "data/halal_stocks.json"
TRADING_UNIVERSE = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA",
    "AVGO", "LLY", "JNJ", "UNH", "XOM", "PG", "MA", "V",
    "JPM", "COST", "HD", "ABBV", "CRM", "NFLX", "MRK", "BAC",
    "AMD", "PEP", "KO", "TMO", "ACN", "LIN", "WMT", "MCD",
    "CSCO", "ABT", "DHR", "NEE", "PM", "TXN", "UNP", "LOW",
    "HON", "AMGN", "IBM", "CAT", "BA", "GS", "BLK", "AXP",
    "SYK", "MDT", "GILD", "ISRG", "ADP", "VRTX", "REGN", "ADI",
    "LRCX", "KLAC", "SNPS", "CDNS", "FTNT", "PANW", "NOW",
    "PLTR", "CRWD", "DDOG", "ZS", "NET", "TEAM", "ABNB",
    "COIN", "SQ", "SHOP", "SE", "MELI", "CPNG", "WDAY"
]
