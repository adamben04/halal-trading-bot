import sqlite3
import json
from datetime import datetime

DB_PATH = "data/portfolio.db"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            qty REAL NOT NULL,
            avg_entry_price REAL NOT NULL,
            sector TEXT,
            opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            closed_at TIMESTAMP,
            exit_price REAL,
            exit_reason TEXT,
            pnl REAL
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            position_id INTEGER,
            symbol TEXT NOT NULL,
            side TEXT NOT NULL,
            qty REAL NOT NULL,
            price REAL NOT NULL,
            reason TEXT,
            strategy TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS daily_snapshot (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL UNIQUE,
            equity REAL NOT NULL,
            cash REAL NOT NULL,
            positions_value REAL NOT NULL,
            daily_pnl REAL,
            total_return_pct REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS journal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trade_id INTEGER,
            pre_analysis TEXT,
            market_conditions TEXT,
            lessons TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


def log_open_position(symbol, qty, price, sector, reason):
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "INSERT INTO positions (symbol, qty, avg_entry_price, sector) VALUES (?, ?, ?, ?)",
        (symbol, qty, price, sector)
    )
    position_id = c.lastrowid
    c.execute(
        "INSERT INTO trades (position_id, symbol, side, qty, price, reason) VALUES (?, ?, 'buy', ?, ?, ?)",
        (position_id, symbol, qty, price, reason)
    )
    conn.commit()
    conn.close()
    return position_id


def log_close_position(position_id, exit_price, exit_reason, pnl):
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "UPDATE positions SET closed_at=?, exit_price=?, exit_reason=?, pnl=? WHERE id=?",
        (datetime.now().isoformat(), exit_price, exit_reason, pnl, position_id)
    )
    c.execute(
        "INSERT INTO trades (position_id, symbol, side, qty, price, reason) "
        "SELECT id, symbol, 'sell', qty, ?, ? FROM positions WHERE id=?",
        (exit_price, exit_reason, position_id)
    )
    conn.commit()
    conn.close()


def save_daily_snapshot(equity, cash, positions_value, daily_pnl, total_return_pct):
    conn = get_db()
    c = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    c.execute(
        "INSERT OR REPLACE INTO daily_snapshot (date, equity, cash, positions_value, daily_pnl, total_return_pct) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (today, equity, cash, positions_value, daily_pnl, total_return_pct)
    )
    conn.commit()
    conn.close()


def get_open_positions():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM positions WHERE closed_at IS NULL")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def get_all_trades():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM trades ORDER BY timestamp DESC LIMIT 100")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def get_daily_snapshots():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM daily_snapshot ORDER BY date")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def get_performance_stats():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM positions WHERE closed_at IS NOT NULL")
    closed = [dict(r) for r in c.fetchall()]
    conn.close()

    if not closed:
        return {"total_trades": 0, "win_rate": 0, "avg_pnl": 0, "profit_factor": 0}

    wins = [t for t in closed if t.get("pnl", 0) > 0]
    losses = [t for t in closed if t.get("pnl", 0) <= 0]
    total_win = sum(t["pnl"] for t in wins)
    total_loss = abs(sum(t["pnl"] for t in losses))

    return {
        "total_trades": len(closed),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(len(wins) / len(closed) * 100, 1),
        "avg_pnl": round(sum(t.get("pnl", 0) for t in closed) / len(closed), 2),
        "total_pnl": round(sum(t.get("pnl", 0) for t in closed), 2),
        "profit_factor": round(total_win / total_loss, 2) if total_loss > 0 else float("inf"),
    }


if __name__ == "__main__":
    init_db()
    print("Database initialized")
