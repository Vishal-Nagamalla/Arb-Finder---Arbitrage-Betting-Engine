"""
Profit Tracker Service
SQLite-backed storage for tracking placed arb bets, outcomes, and cumulative P&L.
"""

import sqlite3
import json
import uuid
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent.parent / "arb_history.db"


class ProfitTracker:
    """Track arb bets placed and their outcomes."""

    def __init__(self, db_path: str | Path = DB_PATH):
        self.db_path = str(db_path)
        self._init_db()

    def _init_db(self):
        """Create tables if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS bets (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    event_name TEXT NOT NULL,
                    sport TEXT NOT NULL,
                    commence_time TEXT,

                    outcome_a TEXT NOT NULL,
                    book_a TEXT NOT NULL,
                    odds_a_decimal REAL NOT NULL,
                    odds_a_american REAL NOT NULL,
                    stake_a REAL NOT NULL,

                    outcome_b TEXT NOT NULL,
                    book_b TEXT NOT NULL,
                    odds_b_decimal REAL NOT NULL,
                    odds_b_american REAL NOT NULL,
                    stake_b REAL NOT NULL,

                    outcome_c TEXT,
                    book_c TEXT,
                    odds_c_decimal REAL,
                    odds_c_american REAL,
                    stake_c REAL,

                    total_stake REAL NOT NULL,
                    guaranteed_return REAL NOT NULL,
                    expected_profit REAL NOT NULL,
                    profit_percentage REAL NOT NULL,
                    arb_margin REAL NOT NULL,

                    status TEXT NOT NULL DEFAULT 'pending',
                    actual_profit REAL,
                    winning_outcome TEXT,
                    resolved_at TEXT,
                    notes TEXT
                )
            """)
            conn.commit()
        logger.info(f"Profit tracker initialized (db: {self.db_path})")

    def add_bet(self, arb_data: dict) -> dict:
        """
        Record a new arb bet from scanner data.
        
        Args:
            arb_data: Dict matching ArbOpportunityResponse fields
            
        Returns:
            The created bet record with id
        """
        bet_id = str(uuid.uuid4())[:8]
        now = datetime.now(timezone.utc).isoformat()

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO bets (
                    id, created_at, event_name, sport, commence_time,
                    outcome_a, book_a, odds_a_decimal, odds_a_american, stake_a,
                    outcome_b, book_b, odds_b_decimal, odds_b_american, stake_b,
                    outcome_c, book_c, odds_c_decimal, odds_c_american, stake_c,
                    total_stake, guaranteed_return, expected_profit,
                    profit_percentage, arb_margin, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                bet_id, now,
                arb_data["event_name"], arb_data["sport"], arb_data.get("commence_time"),
                arb_data["outcome_a"], arb_data["book_a"],
                arb_data["odds_a_decimal"], arb_data["odds_a_american"], arb_data["stake_a"],
                arb_data["outcome_b"], arb_data["book_b"],
                arb_data["odds_b_decimal"], arb_data["odds_b_american"], arb_data["stake_b"],
                arb_data.get("outcome_c"), arb_data.get("book_c"),
                arb_data.get("odds_c_decimal"), arb_data.get("odds_c_american"),
                arb_data.get("stake_c"),
                arb_data["total_stake"], arb_data["guaranteed_return"],
                arb_data["guaranteed_profit"], arb_data["profit_percentage"],
                arb_data["arb_margin"], "pending",
            ))
            conn.commit()

        logger.info(f"Bet recorded: {bet_id} - {arb_data['event_name']}")
        return self.get_bet(bet_id)

    def resolve_bet(
        self,
        bet_id: str,
        winning_outcome: str,
        actual_profit: float | None = None,
        notes: str | None = None,
    ) -> dict | None:
        """
        Resolve a bet with the actual outcome.
        
        For arbs, actual_profit should be the expected_profit since both
        sides are covered. But this lets you track if something went wrong
        (e.g., a bet didn't go through, odds changed).
        """
        now = datetime.now(timezone.utc).isoformat()
        bet = self.get_bet(bet_id)
        if not bet:
            return None

        # If actual_profit not provided, use expected (arb guarantee)
        if actual_profit is None:
            actual_profit = bet["expected_profit"]

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE bets SET
                    status = 'resolved',
                    winning_outcome = ?,
                    actual_profit = ?,
                    resolved_at = ?,
                    notes = ?
                WHERE id = ?
            """, (winning_outcome, actual_profit, now, notes, bet_id))
            conn.commit()

        return self.get_bet(bet_id)

    def cancel_bet(self, bet_id: str, notes: str | None = None) -> dict | None:
        """Cancel a bet (e.g., couldn't place it in time)."""
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE bets SET
                    status = 'cancelled',
                    actual_profit = 0,
                    resolved_at = ?,
                    notes = ?
                WHERE id = ?
            """, (now, notes, bet_id))
            conn.commit()
        return self.get_bet(bet_id)

    def delete_bet(self, bet_id: str) -> bool:
        """Permanently delete a bet record."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM bets WHERE id = ?", (bet_id,))
            conn.commit()
            return cursor.rowcount > 0

    def get_bet(self, bet_id: str) -> dict | None:
        """Get a single bet by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM bets WHERE id = ?", (bet_id,)).fetchone()
            return dict(row) if row else None

    def get_all_bets(
        self,
        status: str | None = None,
        sport: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        """Get all bets with optional filtering."""
        query = "SELECT * FROM bets"
        params: list = []
        conditions = []

        if status:
            conditions.append("status = ?")
            params.append(status)
        if sport:
            conditions.append("sport = ?")
            params.append(sport)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]

    def get_stats(self) -> dict:
        """Get aggregate profit/loss statistics."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            total = conn.execute("SELECT COUNT(*) as count FROM bets").fetchone()["count"]
            pending = conn.execute(
                "SELECT COUNT(*) as count FROM bets WHERE status = 'pending'"
            ).fetchone()["count"]
            resolved = conn.execute(
                "SELECT COUNT(*) as count FROM bets WHERE status = 'resolved'"
            ).fetchone()["count"]
            cancelled = conn.execute(
                "SELECT COUNT(*) as count FROM bets WHERE status = 'cancelled'"
            ).fetchone()["count"]

            # Financial stats from resolved bets
            financials = conn.execute("""
                SELECT
                    COALESCE(SUM(actual_profit), 0) as total_profit,
                    COALESCE(SUM(total_stake), 0) as total_invested,
                    COALESCE(AVG(profit_percentage), 0) as avg_roi,
                    COALESCE(MAX(actual_profit), 0) as best_profit,
                    COALESCE(MIN(actual_profit), 0) as worst_profit
                FROM bets WHERE status = 'resolved'
            """).fetchone()

            # Expected from pending
            pending_stats = conn.execute("""
                SELECT
                    COALESCE(SUM(expected_profit), 0) as pending_profit,
                    COALESCE(SUM(total_stake), 0) as pending_stake
                FROM bets WHERE status = 'pending'
            """).fetchone()

            # Per-sport breakdown
            by_sport = conn.execute("""
                SELECT
                    sport,
                    COUNT(*) as count,
                    COALESCE(SUM(actual_profit), 0) as profit
                FROM bets WHERE status = 'resolved'
                GROUP BY sport ORDER BY profit DESC
            """).fetchall()

            # Per-book breakdown
            book_a_stats = conn.execute("""
                SELECT book_a as book, COUNT(*) as count, SUM(actual_profit) as profit
                FROM bets WHERE status = 'resolved' GROUP BY book_a
            """).fetchall()
            book_b_stats = conn.execute("""
                SELECT book_b as book, COUNT(*) as count, SUM(actual_profit) as profit
                FROM bets WHERE status = 'resolved' GROUP BY book_b
            """).fetchall()

            # Merge book stats
            book_map: dict[str, dict] = {}
            for row in list(book_a_stats) + list(book_b_stats):
                book = row["book"]
                if book not in book_map:
                    book_map[book] = {"count": 0, "profit": 0}
                book_map[book]["count"] += row["count"]
                book_map[book]["profit"] += row["profit"] or 0

            # Recent history (last 10)
            recent = conn.execute("""
                SELECT id, event_name, sport, total_stake, expected_profit,
                       actual_profit, status, created_at
                FROM bets ORDER BY created_at DESC LIMIT 10
            """).fetchall()

        return {
            "total_bets": total,
            "pending": pending,
            "resolved": resolved,
            "cancelled": cancelled,
            "total_profit": round(financials["total_profit"], 2),
            "total_invested": round(financials["total_invested"], 2),
            "avg_roi": round(financials["avg_roi"], 2),
            "best_profit": round(financials["best_profit"], 2),
            "worst_profit": round(financials["worst_profit"], 2),
            "pending_profit": round(pending_stats["pending_profit"], 2),
            "pending_stake": round(pending_stats["pending_stake"], 2),
            "by_sport": [dict(row) for row in by_sport],
            "by_book": [
                {"book": k, "count": v["count"], "profit": round(v["profit"], 2)}
                for k, v in sorted(book_map.items(), key=lambda x: x[1]["profit"], reverse=True)
            ],
            "recent": [dict(row) for row in recent],
        }
