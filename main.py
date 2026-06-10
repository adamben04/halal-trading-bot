import os
import time
import json
import logging
from datetime import datetime
from config import TRADING_UNIVERSE, RISK_PER_TRADE, PAPER_TRADING
from sharia import ShariaScreener
from signals import get_signals
from risk import RiskManager
from trader import Trader
from database import (
    init_db, log_open_position, log_close_position,
    save_daily_snapshot, get_open_positions
)

os.makedirs("logs", exist_ok=True)
os.makedirs("data", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler("logs/bot.log"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("bot")


class HalalTradingBot:
    def __init__(self):
        log.info("Initializing Halal Trading Bot...")
        self.screener = ShariaScreener()
        self.trader = Trader()
        self.risk_mgr = None
        self.halal_universe = []
        init_db()

    def run(self):
        log.info(f"Paper trading: {PAPER_TRADING}")

        # 1. Get account info
        account = self.trader.get_account()
        log.info(f"Account equity: ${account['equity']:,.2f} | Cash: ${account['cash']:,.2f}")

        # HALAL: Block trading if cash is negative (margin usage = haram)
        if account["cash"] < 0:
            log.warning(f"CASH NEGATIVE (${account['cash']:,.2f}) — margin detected. Closing positions to fix.")
            positions = self.trader.get_positions()
            for pos in positions:
                log.info(f"FORCE SELL {pos['symbol']}: removing margin position")
                self.trader.sell(pos["symbol"])
            return
        self.risk_mgr = RiskManager(account["equity"])

        # 2. Check market
        if not self.trader.is_market_open():
            log.info("Market is closed. Skipping.")
            return

        # 3. Screen for halal stocks
        log.info("Screening universe for Sharia compliance...")
        self.halal_universe = self.screener.get_halal_universe(TRADING_UNIVERSE)
        log.info(f"Halal universe: {len(self.halal_universe)}/{len(TRADING_UNIVERSE)} stocks")

        # 4. Get current positions
        current_positions = self.trader.get_positions()
        local_positions = get_open_positions()
        current_symbols = {p["symbol"] for p in current_positions}

        # 5. Check exits first
        for pos in current_positions:
            self._check_exit(pos)

        # 6. Scan for buy signals
        log.info("Scanning for buy signals...")
        for ticker in self.halal_universe:
            if ticker in current_symbols:
                continue  # Already holding

            signal = get_signals(ticker)
            if signal.get("signal") == "BUY":
                self._execute_buy(signal, account, current_positions)

        # 7. Save daily snapshot
        positions_value = sum(p["market_value"] for p in current_positions)
        save_daily_snapshot(
            account["equity"], account["cash"], positions_value,
            0, 0  # Daily P&L calculated at end of day
        )

        log.info("Bot run complete")

    def _execute_buy(self, signal, account, current_positions):
        ticker = signal["ticker"]
        price = signal["indicators"]["price"]
        stop_price = signal["stop_price"]

        # Get sector from cache
        cached = self.screener.cache.get(ticker, {})
        sector = cached.get("sector", "Unknown")

        # Calculate position size — cash only, no margin (halal)
        sizing = self.risk_mgr.calculate_position_size(
            account["equity"], price, stop_price, sector,
            [{"sector": p.get("sector", ""), "market_value": p.get("market_value", 0)}
             for p in current_positions],
            account_cash=account["cash"]
        )

        if sizing["size"] == 0:
            log.info(f"Skipping {ticker}: {sizing['reason']}")
            return

        qty = sizing["size"]
        log.info(f"BUY {qty} {ticker} @ ${price} | Stop: ${stop_price} ({sizing['stop_pct']}%) | Risk: ${sizing['risk_amount']}")

        result = self.trader.buy(ticker, qty)
        if "error" in result:
            log.error(f"Buy failed for {ticker}: {result['error']}")
        else:
            log.info(f"Order placed: {result['order_id']}")
            log_open_position(ticker, qty, price, sector, json.dumps(signal["reasons"]))

    def _check_exit(self, position):
        symbol = position["symbol"]
        entry_price = position["avg_entry_price"]
        current_price = position["current_price"]

        signal = get_signals(symbol)
        exit_reason = None

        if signal.get("signal") == "SELL":
            exit_reason = signal.get("reasons", ["Signal sell"])[0]

        # Trailing stop
        atr = signal.get("indicators", {}).get("atr", 0)
        if atr > 0:
            stop_price = entry_price - (atr * 2)
            if current_price <= stop_price:
                exit_reason = f"ATR stop hit: ${stop_price:.2f}"

        # Take profit
        take_profit = signal.get("take_profit") or (entry_price * 1.10)
        if current_price >= take_profit:
            exit_reason = f"Take profit hit: ${take_profit:.2f}"

        if exit_reason:
            log.info(f"SELL {symbol}: {exit_reason}")
            result = self.trader.sell(symbol)
            if "error" not in result:
                pnl = (current_price - entry_price) * position["qty"]
                self.risk_mgr.record_trade_result(pnl)

                # Find local position ID
                local = get_open_positions()
                for p in local:
                    if p["symbol"] == symbol:
                        log_close_position(p["id"], current_price, exit_reason, pnl)
                        break

                log.info(f"Closed {symbol}: P&L ${pnl:.2f}")


if __name__ == "__main__":
    bot = HalalTradingBot()
    bot.run()
