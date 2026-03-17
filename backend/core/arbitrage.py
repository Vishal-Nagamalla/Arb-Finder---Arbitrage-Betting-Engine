"""
Arbitrage Scanner Module
Detects arbitrage opportunities across sportsbook odds.

Core principle:
    For a 2-outcome event (Team A vs Team B), if the sum of implied
    probabilities across two different sportsbooks is less than 1.0,
    an arbitrage opportunity exists.

    Example:
        Book 1: Team A at +150 (decimal 2.50, implied 40%)
        Book 2: Team B at +120 (decimal 2.20, implied 45.5%)
        Combined implied: 40% + 45.5% = 85.5% < 100%
        Arbitrage margin: 14.5% guaranteed profit on total stake

    In practice, arb margins are usually 1-5%. Anything above that is rare.
"""

from dataclasses import dataclass
from typing import Optional
from .odds_converter import OddsConverter


@dataclass
class ArbOpportunity:
    """Represents a detected arbitrage opportunity."""

    event_name: str
    sport: str
    
    # Outcome A details
    outcome_a: str
    book_a: str
    odds_a_decimal: float
    odds_a_american: float
    implied_prob_a: float
    stake_a: float
    
    # Outcome B details
    outcome_b: str
    book_b: str
    odds_b_decimal: float
    odds_b_american: float
    implied_prob_b: float
    stake_b: float
    
    # Profit details
    total_stake: float
    guaranteed_return: float
    guaranteed_profit: float
    profit_percentage: float  # ROI as a percentage
    arb_margin: float  # The raw margin (1 - sum of implied probs)

    # Optional: for 3-way markets (soccer draw)
    outcome_c: Optional[str] = None
    book_c: Optional[str] = None
    odds_c_decimal: Optional[float] = None
    odds_c_american: Optional[float] = None
    implied_prob_c: Optional[float] = None
    stake_c: Optional[float] = None


class ArbitrageScanner:
    """Scans odds data to find arbitrage opportunities."""

    def __init__(self, min_profit_pct: float = 0.5, max_profit_pct: float = 20.0):
        """
        Args:
            min_profit_pct: Minimum profit % to flag an arb (filter noise)
            max_profit_pct: Maximum profit % to flag (extremely high margins 
                           are usually data errors, not real arbs)
        """
        self.min_profit_pct = min_profit_pct
        self.max_profit_pct = max_profit_pct
        self.converter = OddsConverter()

    def check_two_way_arb(
        self,
        odds_a: float,
        odds_b: float,
        fmt: str = "decimal"
    ) -> dict:
        """
        Check if a 2-outcome market has an arb opportunity.
        
        Args:
            odds_a: Odds for outcome A (best available across all books)
            odds_b: Odds for outcome B (best available across all books)
            fmt: Odds format ("decimal", "american", "probability")
        
        Returns:
            dict with is_arb, margin, implied_probs, etc.
        """
        dec_a = self.converter.normalize_to_decimal(odds_a, fmt)
        dec_b = self.converter.normalize_to_decimal(odds_b, fmt)
        
        prob_a = 1 / dec_a
        prob_b = 1 / dec_b
        combined = prob_a + prob_b
        
        is_arb = combined < 1.0
        margin = 1 - combined if is_arb else 0
        profit_pct = (margin / combined) * 100 if is_arb else 0
        
        return {
            "is_arb": is_arb,
            "combined_implied_probability": round(combined, 6),
            "arb_margin": round(margin, 6),
            "profit_percentage": round(profit_pct, 4),
            "odds_a_decimal": round(dec_a, 4),
            "odds_b_decimal": round(dec_b, 4),
            "implied_prob_a": round(prob_a, 6),
            "implied_prob_b": round(prob_b, 6),
        }

    def check_three_way_arb(
        self,
        odds_a: float,
        odds_b: float,
        odds_c: float,
        fmt: str = "decimal"
    ) -> dict:
        """
        Check if a 3-outcome market (e.g., soccer: win/draw/loss) has an arb.
        
        Same math, just extended to three outcomes.
        """
        dec_a = self.converter.normalize_to_decimal(odds_a, fmt)
        dec_b = self.converter.normalize_to_decimal(odds_b, fmt)
        dec_c = self.converter.normalize_to_decimal(odds_c, fmt)
        
        prob_a = 1 / dec_a
        prob_b = 1 / dec_b
        prob_c = 1 / dec_c
        combined = prob_a + prob_b + prob_c
        
        is_arb = combined < 1.0
        margin = 1 - combined if is_arb else 0
        profit_pct = (margin / combined) * 100 if is_arb else 0
        
        return {
            "is_arb": is_arb,
            "combined_implied_probability": round(combined, 6),
            "arb_margin": round(margin, 6),
            "profit_percentage": round(profit_pct, 4),
            "odds_a_decimal": round(dec_a, 4),
            "odds_b_decimal": round(dec_b, 4),
            "odds_c_decimal": round(dec_c, 4),
            "implied_prob_a": round(prob_a, 6),
            "implied_prob_b": round(prob_b, 6),
            "implied_prob_c": round(prob_c, 6),
        }

    def scan_event(self, event: dict) -> list[ArbOpportunity]:
        """
        Scan a single event's odds across all books and find arb opportunities.
        
        Args:
            event: Dict with structure:
                {
                    "id": "event_id",
                    "sport": "basketball_nba",
                    "home_team": "Lakers",
                    "away_team": "Celtics", 
                    "commence_time": "2026-03-20T00:00:00Z",
                    "bookmakers": [
                        {
                            "key": "fanduel",
                            "title": "FanDuel",
                            "markets": [
                                {
                                    "key": "h2h",
                                    "outcomes": [
                                        {"name": "Lakers", "price": 2.10},
                                        {"name": "Celtics", "price": 1.80}
                                    ]
                                }
                            ]
                        },
                        ...
                    ]
                }
        
        Returns:
            List of ArbOpportunity objects found for this event
        """
        arbs = []
        bookmakers = event.get("bookmakers", [])
        
        if len(bookmakers) < 2:
            return arbs

        sport = event.get("sport_key", event.get("sport", "unknown"))
        home = event.get("home_team", "Home")
        away = event.get("away_team", "Away")
        event_name = f"{away} @ {home}"
        
        # Extract best odds per outcome across all books
        # Structure: {outcome_name: [(odds_decimal, book_key, book_title), ...]}
        outcome_odds: dict[str, list[tuple[float, str, str]]] = {}
        
        for book in bookmakers:
            book_key = book.get("key", "unknown")
            book_title = book.get("title", book_key)
            
            for market in book.get("markets", []):
                if market.get("key") != "h2h":
                    continue
                for outcome in market.get("outcomes", []):
                    name = outcome["name"]
                    price = outcome["price"]
                    if name not in outcome_odds:
                        outcome_odds[name] = []
                    outcome_odds[name].append((price, book_key, book_title))
        
        outcomes = list(outcome_odds.keys())
        
        # 2-way market
        if len(outcomes) == 2:
            arbs.extend(
                self._find_two_way_arbs(
                    event_name, sport, outcomes, outcome_odds
                )
            )
        
        # 3-way market (soccer)
        elif len(outcomes) == 3:
            arbs.extend(
                self._find_three_way_arbs(
                    event_name, sport, outcomes, outcome_odds
                )
            )
        
        return arbs

    def _find_two_way_arbs(
        self,
        event_name: str,
        sport: str,
        outcomes: list[str],
        outcome_odds: dict
    ) -> list[ArbOpportunity]:
        """Find arbs in a 2-way market by checking every cross-book combination."""
        arbs = []
        name_a, name_b = outcomes[0], outcomes[1]
        
        for odds_a, key_a, title_a in outcome_odds[name_a]:
            for odds_b, key_b, title_b in outcome_odds[name_b]:
                # Skip same book (no arb possible within one book)
                if key_a == key_b:
                    continue
                
                result = self.check_two_way_arb(odds_a, odds_b)
                
                if (
                    result["is_arb"]
                    and result["profit_percentage"] >= self.min_profit_pct
                    and result["profit_percentage"] <= self.max_profit_pct
                ):
                    # We'll calculate stakes for a default $100 bankroll
                    # The actual stake amounts get calculated by StakeCalculator
                    arb = ArbOpportunity(
                        event_name=event_name,
                        sport=sport,
                        outcome_a=name_a,
                        book_a=title_a,
                        odds_a_decimal=odds_a,
                        odds_a_american=self.converter.decimal_to_american(odds_a),
                        implied_prob_a=result["implied_prob_a"],
                        stake_a=0,  # Calculated later by StakeCalculator
                        outcome_b=name_b,
                        book_b=title_b,
                        odds_b_decimal=odds_b,
                        odds_b_american=self.converter.decimal_to_american(odds_b),
                        implied_prob_b=result["implied_prob_b"],
                        stake_b=0,
                        total_stake=0,
                        guaranteed_return=0,
                        guaranteed_profit=0,
                        profit_percentage=result["profit_percentage"],
                        arb_margin=result["arb_margin"],
                    )
                    arbs.append(arb)
        
        return arbs

    def _find_three_way_arbs(
        self,
        event_name: str,
        sport: str,
        outcomes: list[str],
        outcome_odds: dict
    ) -> list[ArbOpportunity]:
        """Find arbs in a 3-way market (home/draw/away)."""
        arbs = []
        name_a, name_b, name_c = outcomes[0], outcomes[1], outcomes[2]
        
        for odds_a, key_a, title_a in outcome_odds[name_a]:
            for odds_b, key_b, title_b in outcome_odds[name_b]:
                for odds_c, key_c, title_c in outcome_odds[name_c]:
                    # ALL three outcomes must be on DIFFERENT books
                    # You cannot bet opposing sides on the same sportsbook
                    if key_a == key_b or key_a == key_c or key_b == key_c:
                        continue
                    
                    result = self.check_three_way_arb(odds_a, odds_b, odds_c)
                    
                    if (
                        result["is_arb"]
                        and result["profit_percentage"] >= self.min_profit_pct
                        and result["profit_percentage"] <= self.max_profit_pct
                    ):
                        arb = ArbOpportunity(
                            event_name=event_name,
                            sport=sport,
                            outcome_a=name_a,
                            book_a=title_a,
                            odds_a_decimal=odds_a,
                            odds_a_american=self.converter.decimal_to_american(odds_a),
                            implied_prob_a=result["implied_prob_a"],
                            stake_a=0,
                            outcome_b=name_b,
                            book_b=title_b,
                            odds_b_decimal=odds_b,
                            odds_b_american=self.converter.decimal_to_american(odds_b),
                            implied_prob_b=result["implied_prob_b"],
                            stake_b=0,
                            outcome_c=name_c,
                            book_c=title_c,
                            odds_c_decimal=odds_c,
                            odds_c_american=self.converter.decimal_to_american(odds_c),
                            implied_prob_c=result["implied_prob_c"],
                            stake_c=0,
                            total_stake=0,
                            guaranteed_return=0,
                            guaranteed_profit=0,
                            profit_percentage=result["profit_percentage"],
                            arb_margin=result["arb_margin"],
                        )
                        arbs.append(arb)
        
        return arbs