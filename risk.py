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
                                 current_positions: list) -> dict:
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

        # Cash reserve check
        cash_needed = account_equity * CASH_RESERVE_PCT
        available = account_equity - cash_needed
        if available <= 0:
            result["reason"] = "Cash reserve insufficient"
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

        # Sector cap check
        sector_value = sum(p.get("market_value", 0) for p in current_positions if p.get("sector") == sector)
        sector_limit = account_equity * MAX_SECTOR_PCT
        sector_available = sector_limit - sector_value
        max_by_sector = sector_available / entry_price if sector_available > 0 else 0
        shares = min(shares, max_by_sector)

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
