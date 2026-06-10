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
TRADING_UNIVERSE = [
    # Tech mega-cap
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA",
    "AVGO", "ORCL", "ADBE", "CRM", "AMD", "INTC", "QCOM", "TXN",
    # Cloud / SaaS
    "NOW", "PLTR", "CRWD", "DDOG", "ZS", "NET", "TEAM", "SNPS", "CDNS", "PANW", "FTNT",
    "WDAY", "VEEV", "PCTY", "PAYC", "BILL", "HUBS", "MDB", "GTLB", "CFLT",
    # Semis
    "LRCX", "KLAC", "AMAT", "MRVL", "ON", "MCHP", "QRVO", "SWKS",
    # AI / Data
    "AI", "BBAI", "SOUN", "UPST",
    # E-commerce / Fintech
    "SHOP", "SQ", "COIN", "ABNB", "SE", "MELI", "CPNG", "PYPL", "AFRM", "SOFI",
    # Healthcare
    "LLY", "JNJ", "UNH", "ABBV", "MRK", "TMO", "ABT", "DHR", "AMGN",
    "GILD", "ISRG", "SYK", "MDT", "VRTX", "REGN", "BMY", "PFE", "ZTS", "ILMN",
    # Consumer
    "PG", "KO", "PEP", "COST", "HD", "MCD", "WMT", "LOW", "NKE", "SBUX",
    "TGT", "CL", "EL", "GIS", "KMB", "SYY",
    # Industrials
    "CAT", "BA", "HON", "UNP", "RTX", "LMT", "DE", "GD", "WM",
    "ETN", "EMR", "ITW", "ROK", "PH", "CMI",
    # Financials (non-bank)
    "V", "MA", "BLK", "SCHW", "CME", "ICE", "MSCI", "SPGI",
    # Energy
    "XOM", "CVX", "COP", "SLB", "EOG", "MPC", "PSX",
    # Telecom / Media
    "NFLX", "DIS", "CMCSA", "TMUS", "VZ", "T",
    # Cloud infra
    "SNOW", "FSLY", "AKAM",
    # Other growth
    "TOST", "ARM", "APP", "DASH", "UBER", "LYFT",
    "RBLX", "U", "TTD", "ROKU", "SPOT",
    # --- Mid-cap liquid additions ---
    # Tech mid-cap
    "WDC", "STX", "HPE", "DELL", "HPQ", "ERIC", "NOK",
    "CGNX", "ANSS", "KEYS", "AZTA", "NOVT", "ICLR", "CRL", "DOCS",
    "IONQ", "RGTI", "QMCO", "ARQQ",
    # Cloud / Software mid-cap
    "ZI", "COUR", "DOCU", "SPT", "VRNS", "TENB", "CYBR", "QLYS",
    "VRNT", "PAMT", "CALX", "INFN", "CIEN", "LITE", "AAOI",
    "ALRM", "LOV", "BR", "PFGC", "POOL",
    # Healthcare mid-cap
    "HOLX", "INCY", "ALNY", "EXAS", "NTRA", "CRSP", "BEAM",
    "RARE", "HALO", "PTCT", "IONS", "SRPT", "NBIX", "UTHR",
    "BMRN", "OGIV", "TVTX", "ARWR", "NKTX",
    # Consumer mid-cap
    "CAG", "SJM", "HSY", "MNST", "STZ", "KDP", "KHC", "CPB",
    "CHD", "CPT", "TPR", "PVH", "RL", "VFC", "HBI", "LEVI",
    "YUM", "DRI", "TXRH", "WING", "CAKE", "DPZ", "QSR",
    # Industrials mid-cap
    "FAST", "ODFL", "XPO", "JBHT", "CHRW", "EXPD", "UPS",
    "DAL", "UAL", "LUV", "AAL", "ALK", "SKYW",
    "JCI", "OTIS", "CTAS", "GWW", "SWK", "TT", "MASI",
    # Energy mid-cap
    "FANG", "DVN", "MRO", "OVV", "CTRA", "RRC", "AR",
    "NOG", "SM", "MTDR", "PR", "PEDev",
    # Financials mid-cap
    "COF", "DFS", "SYF", "AXP", "MTB", "HBAN", "KEY", "CFG",
    "PACW", "WAL", "FFIN", "SF", "WAFD",
    # Materials / Other
    "NEM", "FCX", "SCCO", "ALB", "LTHM", "SQM", "CF",
    "DD", "SHW", "CE", "VMC", "MLM",
]
