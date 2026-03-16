"""
Book Rotation / Anti-Detection Service
Tracks how often each sportsbook is used for arb bets and provides
a scoring system to spread bets evenly, reducing the risk of any
single book flagging your account for consistent arb patterns.

Strategy:
- Track bet count and volume per book from profit_tracker history
- Score each arb opportunity: prefer book pairs you've used LESS
- Penalize books with high arb detection risk (DraftKings, bet365)
- Factor in time since last bet on each book
"""

import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

# Risk multipliers - higher = more penalty for using this book
ARB_RISK_WEIGHTS = {
    "low": 1.0,     # Minimal detection, safe to use frequently
    "medium": 1.5,  # Some detection, spread usage out
    "high": 2.5,    # Aggressive detection, use sparingly
    "unknown": 2.0,
}


class BookRotationService:
    """Tracks book usage and scores arb opportunities to spread risk."""

    def __init__(self):
        self._usage_cache: dict[str, dict] = {}  # book_key -> {count, volume, last_used}

    def load_from_tracker(self, tracker) -> None:
        """Load historical usage data from the ProfitTracker."""
        self._usage_cache.clear()
        try:
            stats = tracker.get_stats()
            for book_entry in stats.get("by_book", []):
                book = book_entry["book"]
                self._usage_cache[book] = {
                    "count": book_entry["count"],
                    "volume": book_entry.get("profit", 0),
                    "last_used": None,
                }

            # Get last-used timestamps from recent bets
            bets = tracker.get_all_bets(limit=200)
            for bet in bets:
                for book_field in ["book_a", "book_b"]:
                    book = bet.get(book_field, "")
                    if book and book in self._usage_cache:
                        if self._usage_cache[book]["last_used"] is None:
                            self._usage_cache[book]["last_used"] = bet["created_at"]
        except Exception as e:
            logger.error(f"Failed to load tracker history: {e}")

    def get_book_usage_score(self, book_key: str, arb_risk: str = "unknown") -> float:
        """
        Get a usage penalty score for a book. Higher = used more = less preferred.
        
        Returns a multiplier (1.0 = neutral, 2.0+ = heavily used, avoid).
        """
        usage = self._usage_cache.get(book_key, {"count": 0, "volume": 0, "last_used": None})
        count = usage["count"]

        # Base penalty from usage count
        if count == 0:
            count_penalty = 0.0
        elif count < 5:
            count_penalty = 0.2
        elif count < 15:
            count_penalty = 0.5
        elif count < 30:
            count_penalty = 1.0
        else:
            count_penalty = 1.5

        # Recency penalty - more penalty if used recently
        recency_penalty = 0.0
        last_used = usage.get("last_used")
        if last_used:
            try:
                last_dt = datetime.fromisoformat(last_used.replace("Z", "+00:00"))
                hours_ago = (datetime.now(timezone.utc) - last_dt).total_seconds() / 3600
                if hours_ago < 2:
                    recency_penalty = 1.0
                elif hours_ago < 12:
                    recency_penalty = 0.5
                elif hours_ago < 48:
                    recency_penalty = 0.2
            except (ValueError, TypeError):
                pass

        # Arb risk weight
        risk_weight = ARB_RISK_WEIGHTS.get(arb_risk, 2.0)

        total = (1.0 + count_penalty + recency_penalty) * risk_weight
        return round(total, 2)

    def score_arb_opportunity(self, arb: dict, book_risks: dict[str, str]) -> float:
        """
        Score an arb opportunity considering book rotation.
        
        Higher score = BETTER (more desirable to bet on).
        Combines profit with inverse of book usage penalty.
        
        Returns: composite score (profit weighted by book safety)
        """
        profit = arb.get("guaranteed_profit", 0)
        profit_pct = arb.get("profit_percentage", 0)

        book_a = arb.get("book_a", "")
        book_b = arb.get("book_b", "")
        risk_a = book_risks.get(book_a, "unknown")
        risk_b = book_risks.get(book_b, "unknown")

        penalty_a = self.get_book_usage_score(book_a, risk_a)
        penalty_b = self.get_book_usage_score(book_b, risk_b)

        # Average penalty of the two books
        avg_penalty = (penalty_a + penalty_b) / 2

        # Score: profit percentage divided by usage penalty
        # This naturally prefers: high profit + low usage books
        if avg_penalty <= 0:
            avg_penalty = 1.0

        score = profit_pct / avg_penalty
        return round(score, 4)

    def rank_opportunities(self, arbs: list[dict], book_risks: dict[str, str]) -> list[dict]:
        """
        Re-rank arb opportunities factoring in book rotation.
        
        Returns arbs sorted by composite score (profit + book safety).
        Each arb gets additional fields: rotation_score, book_a_penalty, book_b_penalty
        """
        scored = []
        for arb in arbs:
            book_a = arb.get("book_a", "")
            book_b = arb.get("book_b", "")
            risk_a = book_risks.get(book_a, "unknown")
            risk_b = book_risks.get(book_b, "unknown")

            arb_copy = dict(arb)
            arb_copy["rotation_score"] = self.score_arb_opportunity(arb, book_risks)
            arb_copy["book_a_usage_penalty"] = self.get_book_usage_score(book_a, risk_a)
            arb_copy["book_b_usage_penalty"] = self.get_book_usage_score(book_b, risk_b)
            scored.append(arb_copy)

        scored.sort(key=lambda x: x["rotation_score"], reverse=True)
        return scored

    def get_usage_summary(self) -> dict:
        """Get summary of book usage for the UI."""
        summary = {}
        for book, usage in self._usage_cache.items():
            summary[book] = {
                "bet_count": usage["count"],
                "total_profit": usage["volume"],
                "last_used": usage["last_used"],
            }
        return summary
