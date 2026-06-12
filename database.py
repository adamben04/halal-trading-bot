import sqlite3
import json
import os
from datetime import datetime

DB_PATH = "data/portfolio.db"


def get_db():
    os.makedirs("data", exist_ok=True)
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
    try:
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
        return position_id
    finally:
        conn.close()


def log_close_position(position_id, exit_price, exit_reason, pnl):
    conn = get_db()
    try:
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
    finally:
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
    try:
        c = conn.cursor()
        c.execute("SELECT * FROM positions WHERE closed_at IS NOT NULL")
        closed = [dict(r) for r in c.fetchall()]
    finally:
        conn.close()

    if not closed:
        return {"total_trades": 0, "win_rate": 0, "avg_pnl": 0, "profit_factor": 0}

    wins = [t for t in closed if (t.get("pnl") or 0) > 0]
    losses = [t for t in closed if (t.get("pnl") or 0) <= 0]
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


def get_recent_closed_trades(limit=5):
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "SELECT symbol, qty, avg_entry_price, exit_price, pnl, exit_reason, opened_at, closed_at "
        "FROM positions WHERE closed_at IS NOT NULL ORDER BY closed_at DESC LIMIT ?",
        (limit,)
    )
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def get_trade_count_today():
    conn = get_db()
    c = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    c.execute("SELECT COUNT(*) as cnt FROM trades WHERE DATE(timestamp) = ?", (today,))
    row = c.fetchone()
    conn.close()
    return row["cnt"] if row else 0


def get_streak():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT DISTINCT DATE(timestamp) as day FROM trades ORDER BY day DESC")
    days = [r["day"] for r in c.fetchall()]
    conn.close()

    if not days:
        return 0

    from datetime import date, timedelta
    streak = 0
    today = date.today()

    for d in days:
        trade_date = date.fromisoformat(d)
        if trade_date == today - timedelta(days=streak):
            streak += 1
        elif trade_date == today - timedelta(days=streak - 1) and streak > 0:
            continue
        else:
            break

    return streak


def get_best_worst_trade():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT symbol, pnl FROM positions WHERE closed_at IS NOT NULL ORDER BY pnl DESC")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()

    if not rows:
        return None, None
    return rows[0], rows[-1]


def log_journal(position_id, ticker, action, price, indicators, reasons, strategy=None, sharia=None, risk_info=None):
    conn = get_db()
    try:
        c = conn.cursor()
        c.execute(
            "INSERT INTO journal (trade_id, pre_analysis, market_conditions, lessons) VALUES (?, ?, ?, ?)",
            (
                position_id,
                json.dumps({
                    "ticker": ticker,
                    "action": action,
                    "price": price,
                    "strategy": strategy,
                    "indicators": indicators,
                    "reasons": reasons,
                    "sharia": sharia,
                    "risk": risk_info,
                }),
                json.dumps({"timestamp": datetime.now().isoformat()}),
                None,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def get_journal_entries(limit=20):
    conn = get_db()
    try:
        c = conn.cursor()
        c.execute(
            "SELECT j.id, j.pre_analysis, j.market_conditions, j.created_at, "
            "p.symbol, p.avg_entry_price, p.exit_price, p.pnl, p.exit_reason "
            "FROM journal j LEFT JOIN positions p ON j.trade_id = p.id "
            "ORDER BY j.created_at DESC LIMIT ?",
            (limit,),
        )
        rows = [dict(r) for r in c.fetchall()]
    finally:
        conn.close()

    for row in rows:
        try:
            row["analysis"] = json.loads(row["pre_analysis"]) if row["pre_analysis"] else {}
        except Exception:
            row["analysis"] = {}
        try:
            row["conditions"] = json.loads(row["market_conditions"]) if row["market_conditions"] else {}
        except Exception:
            row["conditions"] = {}
    return rows


def get_full_trade_history(limit=50):
    conn = get_db()
    try:
        c = conn.cursor()
        c.execute("""
            SELECT 
                p.id, p.symbol, p.qty, p.avg_entry_price, p.exit_price, 
                p.pnl, p.exit_reason, p.opened_at, p.closed_at, p.sector,
                j.pre_analysis, j.market_conditions
            FROM positions p
            LEFT JOIN journal j ON j.trade_id = p.id
            WHERE p.closed_at IS NOT NULL
            ORDER BY p.closed_at DESC
            LIMIT ?
        """, (limit,))
        rows = [dict(r) for r in c.fetchall()]
    finally:
        conn.close()

    for row in rows:
        try:
            row["journal"] = json.loads(row["pre_analysis"]) if row["pre_analysis"] else {}
        except Exception:
            row["journal"] = {}
        try:
            row["market"] = json.loads(row["market_conditions"]) if row["market_conditions"] else {}
        except Exception:
            row["market"] = {}
        if row["opened_at"] and row["closed_at"]:
            try:
                opened = datetime.fromisoformat(row["opened_at"])
                closed = datetime.fromisoformat(row["closed_at"])
                row["hold_hours"] = round((closed - opened).total_seconds() / 3600, 1)
            except Exception:
                row["hold_hours"] = 0
        else:
            row["hold_hours"] = 0
    return rows


def get_calendar_pnl():
    conn = get_db()
    try:
        c = conn.cursor()
        c.execute("""
            SELECT DATE(closed_at) as day, SUM(pnl) as daily_pnl, COUNT(*) as trades
            FROM positions WHERE closed_at IS NOT NULL
            GROUP BY DATE(closed_at) ORDER BY day
        """)
        rows = [dict(r) for r in c.fetchall()]
    finally:
        conn.close()
    return rows


def get_stats_by_strategy():
    conn = get_db()
    try:
        c = conn.cursor()
        c.execute("""
            SELECT j.pre_analysis, p.pnl
            FROM positions p
            LEFT JOIN journal j ON j.trade_id = p.id
            WHERE p.closed_at IS NOT NULL AND j.pre_analysis IS NOT NULL
        """)
        rows = [dict(r) for r in c.fetchall()]
    finally:
        conn.close()

    strategies = {}
    for row in rows:
        try:
            analysis = json.loads(row["pre_analysis"])
            strategy = analysis.get("strategy", "Unknown")
        except Exception:
            strategy = "Unknown"
        if strategy not in strategies:
            strategies[strategy] = {"wins": 0, "losses": 0, "total_pnl": 0, "trades": []}
        pnl = row.get("pnl") or 0
        strategies[strategy]["trades"].append(pnl)
        strategies[strategy]["total_pnl"] += pnl
        if pnl > 0:
            strategies[strategy]["wins"] += 1
        else:
            strategies[strategy]["losses"] += 1

    result = []
    for strategy, data in strategies.items():
        total = data["wins"] + data["losses"]
        result.append({
            "strategy": strategy,
            "trades": total,
            "wins": data["wins"],
            "losses": data["losses"],
            "win_rate": round(data["wins"] / total * 100, 1) if total > 0 else 0,
            "total_pnl": round(data["total_pnl"], 2),
            "avg_pnl": round(data["total_pnl"] / total, 2) if total > 0 else 0,
        })
    return sorted(result, key=lambda x: x["trades"], reverse=True)


if __name__ == "__main__":
    init_db()
    print("Database initialized")
