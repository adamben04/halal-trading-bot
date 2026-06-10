import json
import os
import yfinance as yf
from datetime import datetime
from config import (
    DEBT_THRESHOLD, CASH_THRESHOLD, RECEIVABLES_THRESHOLD,
    IMPURE_INCOME_THRESHOLD, PROHIBITED_SECTORS, PROHIBITED_KEYWORDS
)

TICKER_CACHE_FILE = "data/halal_stocks.json"


class ShariaScreener:
    def __init__(self):
        self.cache = self._load_cache()

    def _load_cache(self):
        if os.path.exists(TICKER_CACHE_FILE):
            with open(TICKER_CACHE_FILE, "r") as f:
                return json.load(f)
        return {}

    def _save_cache(self):
        with open(TICKER_CACHE_FILE, "w") as f:
            json.dump(self.cache, f, indent=2)

    def screen(self, ticker: str, use_cache: bool = True) -> dict:
        if use_cache and ticker in self.cache:
            cached = self.cache[ticker]
            cache_date = datetime.fromisoformat(cached["screened_at"])
            if (datetime.now() - cache_date).days < 90:
                return cached

        stock = yf.Ticker(ticker)
        info = stock.info

        result = {
            "ticker": ticker,
            "name": info.get("longName", ticker),
            "sector": info.get("sector", "Unknown"),
            "passes_business": False,
            "passes_financial": False,
            "compliant": False,
            "ratios": {},
            "screened_at": datetime.now().isoformat(),
            "error": None,
        }

        # Business Activity Screen
        sector = info.get("sector", "")
        industry = info.get("industry", "")
        description = info.get("longBusinessSummary", "").lower()

        if sector in PROHIBITED_SECTORS:
            result["error"] = f"Prohibited sector: {sector}"
            return result

        for keyword in PROHIBITED_KEYWORDS:
            if keyword in description:
                result["error"] = f"Prohibited keyword: {keyword}"
                return result

        result["passes_business"] = True

        # Financial Ratio Screen
        market_cap = info.get("marketCap", 0)
        if not market_cap:
            result["error"] = "No market cap data"
            return result

        bs = stock.balance_sheet
        if bs.empty:
            result["error"] = "No balance sheet data"
            return result

        latest = bs.iloc[0]

        # Debt ratio
        short_debt = latest.get("Current Debt", 0) or 0
        long_debt = latest.get("Long Term Debt", 0) or 0
        total_debt = short_debt + long_debt
        debt_ratio = total_debt / market_cap

        # Cash + interest-bearing securities
        cash = latest.get("Cash And Cash Equivalents", 0) or 0
        short_investments = latest.get("Other Short Term Investments", 0) or 0
        cash_ratio = (cash + short_investments) / market_cap

        # Receivables
        receivables = latest.get("Net Receivables", 0) or 0
        total_assets = latest.get("Total Assets", 1) or 1
        receivables_ratio = receivables / total_assets

        result["ratios"] = {
            "debt_pct": round(debt_ratio * 100, 2),
            "cash_pct": round(cash_ratio * 100, 2),
            "receivables_pct": round(receivables_ratio * 100, 2),
            "market_cap": market_cap,
        }

        debt_pass = debt_ratio < DEBT_THRESHOLD
        cash_pass = cash_ratio < CASH_THRESHOLD
        recv_pass = receivables_ratio < RECEIVABLES_THRESHOLD
        result["passes_financial"] = debt_pass and cash_pass and recv_pass

        # Impermissible income estimate
        total_revenue = info.get("totalRevenue", 1) or 1
        try:
            income = stock.income_stmt
            if not income.empty:
                inc_latest = income.iloc[0]
                interest_income = inc_latest.get("Interest Income", 0) or 0
                other_income = inc_latest.get("Other Income", 0) or 0
                impure_estimate = interest_income + (other_income * 0.5)
            else:
                impure_estimate = 0
        except Exception:
            impure_estimate = 0

        impure_pct = impure_estimate / total_revenue if total_revenue else 0
        result["ratios"]["impure_income_pct"] = round(impure_pct * 100, 2)

        impure_pass = impure_pct < IMPURE_INCOME_THRESHOLD
        result["compliant"] = result["passes_business"] and result["passes_financial"] and impure_pass

        self.cache[ticker] = result
        self._save_cache()
        return result

    def screen_batch(self, tickers: list, use_cache: bool = True) -> list:
        results = []
        for ticker in tickers:
            try:
                result = self.screen(ticker, use_cache=use_cache)
                results.append(result)
            except Exception as e:
                results.append({"ticker": ticker, "error": str(e), "compliant": False})
        return results

    def get_halal_universe(self, tickers: list) -> list:
        halal = []
        for ticker in tickers:
            result = self.screen(ticker)
            if result.get("compliant"):
                halal.append(ticker)
        return halal


if __name__ == "__main__":
    screener = ShariaScreener()
    test_tickers = ["AAPL", "MSFT", "NVDA", "JPM", "BAC"]
    for ticker in test_tickers:
        result = screener.screen(ticker, use_cache=False)
        status = "HALAL" if result["compliant"] else "NOT HALAL"
        print(f"{ticker}: {status} | {result.get('error', '')}")
        if result["ratios"]:
            print(f"  Debt: {result['ratios']['debt_pct']}% | Cash: {result['ratios']['cash_pct']}%")
