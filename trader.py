import os
from datetime import datetime
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest, StopLossRequest, TakeProfitRequest
from alpaca.trading.enums import OrderSide, TimeInForce, OrderClass
from alpaca.data.historical.stock import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from config import ALPACA_API_KEY, ALPACA_SECRET_KEY, PAPER_TRADING


class Trader:
    def __init__(self):
        self.trading_client = TradingClient(
            ALPACA_API_KEY, ALPACA_SECRET_KEY, paper=PAPER_TRADING
        )
        self.data_client = StockHistoricalDataClient(
            ALPACA_API_KEY, ALPACA_SECRET_KEY
        )

    def get_account(self) -> dict:
        account = self.trading_client.get_account()
        return {
            "equity": float(account.equity),
            "cash": float(account.cash),
            "buying_power": float(account.buying_power),
            "portfolio_value": float(account.portfolio_value),
        }

    def get_positions(self) -> list:
        positions = self.trading_client.get_all_positions()
        return [
            {
                "symbol": p.symbol,
                "qty": float(p.qty),
                "avg_entry_price": float(p.avg_entry_price),
                "current_price": float(p.current_price),
                "market_value": float(p.market_value),
                "unrealized_pl": float(p.unrealized_pl),
                "unrealized_plpc": float(p.unrealized_plpc),
                "side": p.side.value if hasattr(p.side, "value") else str(p.side),
            }
            for p in positions
        ]

    def get_position(self, symbol: str):
        try:
            return self.trading_client.get_position(symbol)
        except Exception:
            return None

    def buy(self, symbol: str, qty: int, order_type: str = "market",
            limit_price: float = None) -> dict:
        if order_type == "market":
            order = MarketOrderRequest(
                symbol=symbol, qty=qty, side=OrderSide.BUY,
                time_in_force=TimeInForce.DAY
            )
        elif order_type == "limit":
            order = LimitOrderRequest(
                symbol=symbol, qty=qty, side=OrderSide.BUY,
                time_in_force=TimeInForce.DAY, limit_price=limit_price
            )
        else:
            return {"error": f"Unknown order type: {order_type}"}

        try:
            result = self.trading_client.submit_order(order_data=order)
            return {
                "order_id": str(result.id),
                "symbol": result.symbol,
                "side": result.side.value,
                "qty": result.qty,
                "type": order_type,
                "status": result.status.value,
                "submitted_at": result.submitted_at.isoformat() if result.submitted_at else None,
            }
        except Exception as e:
            return {"error": str(e)}

    def sell(self, symbol: str, qty: int = None) -> dict:
        try:
            if qty is None:
                result = self.trading_client.close_position(symbol)
            else:
                result = self.trading_client.close_position(symbol, close_options={"qty": str(qty)})
            return {"status": "closed", "symbol": symbol}
        except Exception as e:
            return {"error": str(e)}

    def buy_bracket(self, symbol: str, qty: int, stop_price: float,
                    take_profit_price: float) -> dict:
        order = MarketOrderRequest(
            symbol=symbol, qty=qty, side=OrderSide.BUY,
            time_in_force=TimeInForce.DAY,
            order_class=OrderClass.BRACKET,
            take_profit=TakeProfitRequest(limit_price=take_profit_price),
            stop_loss=StopLossRequest(stop_price=stop_price),
        )
        try:
            result = self.trading_client.submit_order(order_data=order)
            return {
                "order_id": str(result.id),
                "symbol": result.symbol,
                "side": result.side.value,
                "qty": result.qty,
                "type": "bracket",
                "status": result.status.value,
                "stop_price": stop_price,
                "take_profit": take_profit_price,
            }
        except Exception as e:
            return {"error": str(e)}

    def get_bars(self, symbol: str, timeframe: str = "1Day",
                 start: datetime = None, limit: int = 200) -> list:
        tf_map = {"1Day": TimeFrame.Day, "1Hour": TimeFrame.Hour, "1Min": TimeFrame.Minute}
        tf = tf_map.get(timeframe, TimeFrame.Day)

        if start is None:
            start = datetime(2024, 1, 1)

        request = StockBarsRequest(
            symbol_or_symbols=[symbol], timeframe=tf,
            start=start, limit=limit
        )
        bars = self.data_client.get_stock_bars(request)
        return [
            {
                "timestamp": bar.timestamp.isoformat(),
                "open": bar.open, "high": bar.high,
                "low": bar.low, "close": bar.close,
                "volume": bar.volume,
            }
            for bar in bars[symbol]
        ]

    def is_market_open(self) -> bool:
        clock = self.trading_client.get_clock()
        return clock.is_open


if __name__ == "__main__":
    trader = Trader()
    print(f"Account: {trader.get_account()}")
    print(f"Positions: {trader.get_positions()}")
    print(f"Market open: {trader.is_market_open()}")
