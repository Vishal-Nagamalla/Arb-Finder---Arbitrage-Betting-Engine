"""
Profit Tracker Service
Supports both SQLite (local dev) and Neon Postgres (cloud deployment).

If DATABASE_URL is set -> uses Postgres (persistent across deploys)
Otherwise -> falls back to SQLite (local file, wiped on redeploy)
"""

import os
import uuid
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

SQLITE_PATH = Path(__file__).parent.parent.parent / "arb_history.db"


class ProfitTracker:
    """Track arb bets placed and their outcomes."""

    def __init__(self):
        self.database_url = os.environ.get("DATABASE_URL", "")
        self.use_postgres = bool(self.database_url)

        if self.use_postgres:
            logger.info("Profit tracker: using Neon Postgres (persistent)")
        else:
            logger.info(f"Profit tracker: using SQLite ({SQLITE_PATH})")

        self._init_db()

    # ─── Connection Helpers ───────────────────────────────────────────────

    def _get_conn(self):
        """Get a database connection."""
        if self.use_postgres:
            import psycopg2
            return psycopg2.connect(self.database_url, sslmode="require")
        else:
            import sqlite3
            conn = sqlite3.connect(str(SQLITE_PATH))
            conn.row_factory = sqlite3.Row
            return conn

    def _placeholder(self) -> str:
        """Get the parameter placeholder for the current DB."""
        return "%s" if self.use_postgres else "?"

    def _execute(self, query: str, params: tuple | list = ()) -> list[dict]:
        """Execute a query and return results as list of dicts."""
        # Convert ? placeholders to %s for Postgres
        if self.use_postgres:
            query = query.replace("?", "%s")

        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)

            if cursor.description:
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(columns, row)) for row in rows]

            conn.commit()
            return []
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def _execute_one(self, query: str, params: tuple | list = ()) -> dict | None:
        """Execute a query and return a single result."""
        results = self._execute(query, params)
        return results[0] if results else None

    def _execute_write(self, query: str, params: tuple | list = ()):
        """Execute an insert/update/delete."""
        if self.use_postgres:
            query = query.replace("?", "%s")

        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    # ─── Init ─────────────────────────────────────────────────────────────

    def _init_db(self):
        """Create tables if they don't exist."""
        # Use TEXT for compatibility between SQLite and Postgres
        create_sql = """
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
        """

        if self.use_postgres:
            # Postgres uses DOUBLE PRECISION instead of REAL
            create_sql = create_sql.replace(" REAL ", " DOUBLE PRECISION ")

        try:
            self._execute_write(create_sql)
            # Settings table for persistent configuration
            settings_sql = """
                CREATE TABLE IF NOT EXISTS app_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """
            self._execute_write(settings_sql)
            logger.info("Profit tracker initialized")
        except Exception as e:
            logger.error(f"Failed to init profit tracker: {e}")

    # ─── Settings Persistence ─────────────────────────────────────────────

    def save_setting(self, key: str, value: str):
        """Save a setting to the database."""
        try:
            existing = self._execute_one("SELECT key FROM app_settings WHERE key = ?", (key,))
            if existing:
                self._execute_write("UPDATE app_settings SET value = ? WHERE key = ?", (value, key))
            else:
                self._execute_write("INSERT INTO app_settings (key, value) VALUES (?, ?)", (key, value))
        except Exception as e:
            logger.error(f"Failed to save setting {key}: {e}")

    def load_setting(self, key: str, default: str = "") -> str:
        """Load a setting from the database."""
        try:
            row = self._execute_one("SELECT value FROM app_settings WHERE key = ?", (key,))
            return row["value"] if row else default
        except Exception as e:
            logger.error(f"Failed to load setting {key}: {e}")
            return default

    def save_all_settings(self, settings: dict):
        """Save multiple settings at once."""
        import json
        for key, value in settings.items():
            self.save_setting(key, json.dumps(value) if not isinstance(value, str) else value)

    def load_all_settings(self) -> dict:
        """Load all settings from the database."""
        import json
        try:
            rows = self._execute("SELECT key, value FROM app_settings")
            result = {}
            for row in rows:
                try:
                    result[row["key"]] = json.loads(row["value"])
                except (json.JSONDecodeError, TypeError):
                    result[row["key"]] = row["value"]
            return result
        except Exception as e:
            logger.error(f"Failed to load settings: {e}")
            return {}

    # ─── CRUD Operations ──────────────────────────────────────────────────

    def add_bet(self, arb_data: dict) -> dict:
        """Record a new arb bet from scanner data."""
        bet_id = str(uuid.uuid4())[:8]
        now = datetime.now(timezone.utc).isoformat()

        self._execute_write("""
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

        logger.info(f"Bet recorded: {bet_id} - {arb_data['event_name']}")
        return self.get_bet(bet_id)

    def resolve_bet(self, bet_id: str, winning_outcome: str,
                    actual_profit: float | None = None, notes: str | None = None) -> dict | None:
        """Resolve a bet with the actual outcome."""
        bet = self.get_bet(bet_id)
        if not bet:
            return None

        if actual_profit is None:
            actual_profit = bet["expected_profit"]

        now = datetime.now(timezone.utc).isoformat()
        self._execute_write("""
            UPDATE bets SET status = 'resolved', winning_outcome = ?,
                actual_profit = ?, resolved_at = ?, notes = ?
            WHERE id = ?
        """, (winning_outcome, actual_profit, now, notes, bet_id))

        return self.get_bet(bet_id)

    def cancel_bet(self, bet_id: str, notes: str | None = None) -> dict | None:
        """Cancel a bet."""
        now = datetime.now(timezone.utc).isoformat()
        self._execute_write("""
            UPDATE bets SET status = 'cancelled', actual_profit = 0,
                resolved_at = ?, notes = ?
            WHERE id = ?
        """, (now, notes, bet_id))
        return self.get_bet(bet_id)

    def delete_bet(self, bet_id: str) -> bool:
        """Permanently delete a bet record."""
        count = self._execute_write("DELETE FROM bets WHERE id = ?", (bet_id,))
        return count > 0

    def get_bet(self, bet_id: str) -> dict | None:
        """Get a single bet by ID."""
        return self._execute_one("SELECT * FROM bets WHERE id = ?", (bet_id,))

    def get_all_bets(self, status: str | None = None, sport: str | None = None,
                     limit: int = 100, offset: int = 0) -> list[dict]:
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

        return self._execute(query, params)

    # ─── Statistics ───────────────────────────────────────────────────────

    def get_stats(self) -> dict:
        """Get aggregate profit/loss statistics."""
        total = self._execute_one("SELECT COUNT(*) as count FROM bets")["count"]
        pending = self._execute_one(
            "SELECT COUNT(*) as count FROM bets WHERE status = 'pending'"
        )["count"]
        resolved = self._execute_one(
            "SELECT COUNT(*) as count FROM bets WHERE status = 'resolved'"
        )["count"]
        cancelled = self._execute_one(
            "SELECT COUNT(*) as count FROM bets WHERE status = 'cancelled'"
        )["count"]

        financials = self._execute_one("""
            SELECT
                COALESCE(SUM(actual_profit), 0) as total_profit,
                COALESCE(SUM(total_stake), 0) as total_invested,
                COALESCE(AVG(profit_percentage), 0) as avg_roi,
                COALESCE(MAX(actual_profit), 0) as best_profit,
                COALESCE(MIN(actual_profit), 0) as worst_profit
            FROM bets WHERE status = 'resolved'
        """)

        pending_stats = self._execute_one("""
            SELECT
                COALESCE(SUM(expected_profit), 0) as pending_profit,
                COALESCE(SUM(total_stake), 0) as pending_stake
            FROM bets WHERE status = 'pending'
        """)

        by_sport = self._execute("""
            SELECT sport, COUNT(*) as count,
                COALESCE(SUM(actual_profit), 0) as profit
            FROM bets WHERE status = 'resolved'
            GROUP BY sport ORDER BY profit DESC
        """)

        book_a_stats = self._execute("""
            SELECT book_a as book, COUNT(*) as count, SUM(actual_profit) as profit
            FROM bets WHERE status = 'resolved' GROUP BY book_a
        """)
        book_b_stats = self._execute("""
            SELECT book_b as book, COUNT(*) as count, SUM(actual_profit) as profit
            FROM bets WHERE status = 'resolved' GROUP BY book_b
        """)

        book_map: dict[str, dict] = {}
        for row in book_a_stats + book_b_stats:
            book = row["book"]
            if book not in book_map:
                book_map[book] = {"count": 0, "profit": 0}
            book_map[book]["count"] += row["count"]
            book_map[book]["profit"] += row["profit"] or 0

        recent = self._execute("""
            SELECT id, event_name, sport, total_stake, expected_profit,
                   actual_profit, status, created_at
            FROM bets ORDER BY created_at DESC LIMIT 10
        """)

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
            "by_sport": by_sport,
            "by_book": [
                {"book": k, "count": v["count"], "profit": round(v["profit"], 2)}
                for k, v in sorted(book_map.items(), key=lambda x: x[1]["profit"], reverse=True)
            ],
            "recent": recent,
        }

    # ─── Settings Persistence ─────────────────────────────────────────────

    def save_setting(self, key: str, value: str):
        """Save a setting to the database."""
        try:
            if self.use_postgres:
                self._execute_write(
                    "INSERT INTO app_settings (key, value) VALUES (?, ?) "
                    "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
                    (key, value),
                )
            else:
                self._execute_write(
                    "INSERT OR REPLACE INTO app_settings (key, value) VALUES (?, ?)",
                    (key, value),
                )
        except Exception as e:
            logger.error(f"Failed to save setting {key}: {e}")

    def get_setting(self, key: str, default: str | None = None) -> str | None:
        """Get a setting from the database."""
        try:
            row = self._execute_one("SELECT value FROM app_settings WHERE key = ?", (key,))
            return row["value"] if row else default
        except Exception as e:
            logger.error(f"Failed to get setting {key}: {e}")
            return default

    def save_all_settings(self, settings: dict):
        """Save multiple settings at once."""
        import json
        for key, value in settings.items():
            self.save_setting(key, json.dumps(value) if not isinstance(value, str) else value)

    def load_all_settings(self) -> dict:
        """Load all saved settings."""
        import json
        try:
            rows = self._execute("SELECT key, value FROM app_settings")
            result = {}
            for row in rows:
                try:
                    result[row["key"]] = json.loads(row["value"])
                except (json.JSONDecodeError, TypeError):
                    result[row["key"]] = row["value"]
            return result
        except Exception as e:
            logger.error(f"Failed to load settings: {e}")
            return {}