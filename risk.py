from config import (
    RISK_PER_TRADE, MAX_POSITIONS, MAX_SINGLE_POSITION_PCT,
    MAX_SECTOR_PCT, DAILY_LOSS_LIMIT, MAX_DRAWDOWN,
    CONSECUTIVE_LOSS_LIMIT, CASH_RESERVE_PCT, ATR_STOP_MULTIPLIER,
    MAX_STOP_PCT
)


class RiskManager:
    def __init__(self, initial_capital: float):
        self.initial_capital = initial_capital
        self.peak_equity = initial_capital
        self.daily_start_equity = initial_capital
        self.consecutive_losses = 0
        self.daily_pnl = 0
        self.halted = False

    def calculate_position_size(self, account_equity: float, entry_price: float,
                                 stop_price: float, sector: str,
                                 current_positions: list,
                                 account_cash: float = None) -> dict:
        result = {"size": 0, "reason": ""}

        if self.halted:
            result["reason"] = "Trading halted"
            return result

        # Daily loss check
        if self.daily_start_equity > 0:
            daily_loss = (self.daily_start_equity - account_equity) / self.daily_start_equity
            if daily_loss >= DAILY_LOSS_LIMIT:
                self.halted = True
                result["reason"] = f"Daily loss limit hit: {daily_loss:.2%}"
                return result

        # Drawdown check
        self.peak_equity = max(self.peak_equity, account_equity)
        drawdown = (self.peak_equity - account_equity) / self.peak_equity
        if drawdown >= MAX_DRAWDOWN:
            self.halted = True
            result["reason"] = f"Max drawdown hit: {drawdown:.2%}"
            return result

        # Consecutive losses check
        if self.consecutive_losses >= CONSECUTIVE_LOSS_LIMIT:
            result["reason"] = f"Consecutive losses: {self.consecutive_losses}"
            return result

        # Max positions check
        if len(current_positions) >= MAX_POSITIONS:
            result["reason"] = f"Max positions reached: {len(current_positions)}"
            return result

        # HALAL: Cash-only — no margin, no leverage
        # Available cash = actual cash in account (NOT buying_power which includes margin)
        if account_cash is None:
            account_cash = account_equity  # fallback
        cash_reserve = account_equity * CASH_RESERVE_PCT
        available_cash = account_cash - cash_reserve
        if available_cash <= 0:
            result["reason"] = f"Cash too low: ${account_cash:,.0f} (need ${cash_reserve:,.0f} reserve)"
            return result

        # HALAL: Total positions must never exceed equity (no margin)
        total_exposure = sum(abs(p.get("market_value", 0)) for p in current_positions)
        if total_exposure >= account_equity:
            result["reason"] = f"Fully invested: ${total_exposure:,.0f} / ${account_equity:,.0f}"
            return result

        # Position size calculation
        stop_distance = abs(entry_price - stop_price)
        if stop_distance == 0:
            result["reason"] = "Stop distance is zero"
            return result

        risk_amount = account_equity * RISK_PER_TRADE
        shares = risk_amount / stop_distance

        # Max position cap
        max_shares = (account_equity * MAX_SINGLE_POSITION_PCT) / entry_price
        shares = min(shares, max_shares)

        # Cash cap — can only spend what we have
        max_by_cash = int(available_cash / entry_price) if entry_price > 0 else 0
        shares = min(shares, max_by_cash)

        # Sector cap check
        sector_value = sum(p.get("market_value", 0) for p in current_positions if p.get("sector") == sector)
        sector_limit = account_equity * MAX_SECTOR_PCT
        sector_available = sector_limit - sector_value
        max_by_sector = sector_available / entry_price if sector_available > 0 else 0
        shares = min(shares, max_by_sector)

        # Exposure cap — new position + existing must stay under equity
        max_new_value = account_equity - total_exposure
        max_by_exposure = int(max_new_value / entry_price) if entry_price > 0 else 0
        shares = min(shares, max_by_exposure)

        # Stop loss width cap
        stop_pct = stop_distance / entry_price
        if stop_pct > MAX_STOP_PCT:
            shares = min(shares, risk_amount / (entry_price * MAX_STOP_PCT))

        shares = max(int(shares), 0)

        if shares == 0:
            result["reason"] = "Calculated size is zero"
            return result

        result["size"] = shares
        result["risk_amount"] = round(risk_amount, 2)
        result["stop_distance"] = round(stop_distance, 2)
        result["stop_pct"] = round(stop_pct * 100, 2)
        return result

    def record_trade_result(self, pnl: float):
        if pnl < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0

    def reset_daily(self, current_equity: float):
        self.daily_start_equity = current_equity
        self.halted = False

    def get_status(self) -> dict:
        return {
            "peak_equity": round(self.peak_equity, 2),
            "consecutive_losses": self.consecutive_losses,
            "daily_start": round(self.daily_start_equity, 2),
            "halted": self.halted,
        }


if __name__ == "__main__":
    rm = RiskManager(10000)
    positions = [{"sector": "Technology", "market_value": 1500}]
    result = rm.calculate_position_size(10000, 150, 147, "Technology", positions)
    print(f"Position size: {result}")
