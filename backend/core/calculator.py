"""
Stake Calculator Module
Computes optimal stake distribution across outcomes to guarantee profit.

The Math:
    For a 2-outcome arb with decimal odds d1 and d2:
    
    We want the same guaranteed return R regardless of which outcome wins.
        If outcome 1 wins: stake1 * d1 = R
        If outcome 2 wins: stake2 * d2 = R
    
    So:
        stake1 = R / d1
        stake2 = R / d2
        total_stake = stake1 + stake2 = R * (1/d1 + 1/d2)
    
    Given a bankroll B (total_stake = B):
        R = B / (1/d1 + 1/d2)
        stake1 = B * (1/d1) / (1/d1 + 1/d2)
        stake2 = B * (1/d2) / (1/d1 + 1/d2)
        profit = R - B
"""

from dataclasses import dataclass
from .arbitrage import ArbOpportunity


@dataclass
class StakeBreakdown:
    """Complete breakdown of an arb bet."""

    # Per-outcome stakes
    stakes: dict[str, dict]  # {outcome_name: {book, stake, odds_decimal, odds_american, potential_return}}
    
    # Totals
    total_stake: float
    guaranteed_return: float
    guaranteed_profit: float
    profit_percentage: float  # ROI
    
    # If outcome A wins vs B wins (shows both scenarios)
    scenario_outcomes: list[dict]  # [{outcome, return, profit}, ...]
    
    # After fees estimate
    profit_after_fees: float | None = None

    def display(self) -> str:
        """Pretty print the breakdown."""
        lines = []
        lines.append("=" * 60)
        lines.append("  ARBITRAGE BET BREAKDOWN")
        lines.append("=" * 60)
        
        for outcome_name, info in self.stakes.items():
            lines.append(f"\n  >> {outcome_name} on {info['book']}")
            lines.append(f"     Odds: {info['odds_decimal']:.2f} (American: {info['odds_american']:+.0f})")
            lines.append(f"     Stake: ${info['stake']:.2f}")
            lines.append(f"     Potential Return: ${info['potential_return']:.2f}")
        
        lines.append(f"\n{'─' * 60}")
        lines.append(f"  Total Investment:    ${self.total_stake:.2f}")
        lines.append(f"  Guaranteed Return:   ${self.guaranteed_return:.2f}")
        lines.append(f"  Guaranteed Profit:   ${self.guaranteed_profit:.2f}")
        lines.append(f"  ROI:                 {self.profit_percentage:.2f}%")
        
        lines.append(f"\n{'─' * 60}")
        lines.append("  SCENARIO ANALYSIS:")
        for scenario in self.scenario_outcomes:
            lines.append(
                f"    If {scenario['outcome']}: "
                f"Return ${scenario['return']:.2f}, "
                f"Profit ${scenario['profit']:.2f}"
            )
        
        if self.profit_after_fees is not None:
            lines.append(f"\n  Est. Profit After Fees: ${self.profit_after_fees:.2f}")
        
        lines.append("=" * 60)
        return "\n".join(lines)


class StakeCalculator:
    """Calculate optimal stakes for arbitrage betting."""

    def __init__(self, default_fee_pct: float = 0.0):
        """
        Args:
            default_fee_pct: Default withdrawal/platform fee as a percentage
                             (e.g., 2.0 for 2% fee). Applied to winnings estimate.
        """
        self.default_fee_pct = default_fee_pct

    def calculate_two_way(
        self,
        odds_a: float,
        odds_b: float,
        bankroll: float,
        outcome_a_name: str = "Outcome A",
        outcome_b_name: str = "Outcome B",
        book_a: str = "Book A",
        book_b: str = "Book B",
        fee_pct: float | None = None,
    ) -> StakeBreakdown:
        """
        Calculate exact stakes for a 2-outcome arb bet.
        
        Args:
            odds_a: Decimal odds for outcome A
            odds_b: Decimal odds for outcome B
            bankroll: Total amount to invest across both bets
            outcome_a_name: Name of outcome A (e.g., "Lakers")
            outcome_b_name: Name of outcome B (e.g., "Celtics")
            book_a: Sportsbook name for outcome A
            book_b: Sportsbook name for outcome B
            fee_pct: Override fee percentage (uses default if None)
        
        Returns:
            StakeBreakdown with complete bet information
        """
        prob_a = 1 / odds_a
        prob_b = 1 / odds_b
        combined = prob_a + prob_b
        
        if combined >= 1.0:
            raise ValueError(
                f"No arbitrage opportunity exists. Combined implied probability "
                f"is {combined:.4f} (needs to be < 1.0). "
                f"You would LOSE money on this bet."
            )
        
        # Calculate guaranteed return
        guaranteed_return = bankroll / combined
        
        # Calculate individual stakes
        stake_a = bankroll * prob_a / combined
        stake_b = bankroll * prob_b / combined
        
        # Profit
        profit = guaranteed_return - bankroll
        profit_pct = (profit / bankroll) * 100
        
        # Build scenario analysis
        return_if_a = stake_a * odds_a
        return_if_b = stake_b * odds_b
        
        # American odds for display
        from .odds_converter import OddsConverter
        american_a = OddsConverter.decimal_to_american(odds_a)
        american_b = OddsConverter.decimal_to_american(odds_b)
        
        # Fee calculation
        fee = self.default_fee_pct if fee_pct is None else fee_pct
        profit_after_fees = profit - (guaranteed_return * fee / 100) if fee > 0 else None
        
        return StakeBreakdown(
            stakes={
                outcome_a_name: {
                    "book": book_a,
                    "stake": round(stake_a, 2),
                    "odds_decimal": round(odds_a, 4),
                    "odds_american": american_a,
                    "potential_return": round(return_if_a, 2),
                },
                outcome_b_name: {
                    "book": book_b,
                    "stake": round(stake_b, 2),
                    "odds_decimal": round(odds_b, 4),
                    "odds_american": american_b,
                    "potential_return": round(return_if_b, 2),
                },
            },
            total_stake=round(bankroll, 2),
            guaranteed_return=round(guaranteed_return, 2),
            guaranteed_profit=round(profit, 2),
            profit_percentage=round(profit_pct, 4),
            scenario_outcomes=[
                {
                    "outcome": f"{outcome_a_name} wins",
                    "return": round(return_if_a, 2),
                    "profit": round(return_if_a - bankroll, 2),
                },
                {
                    "outcome": f"{outcome_b_name} wins",
                    "return": round(return_if_b, 2),
                    "profit": round(return_if_b - bankroll, 2),
                },
            ],
            profit_after_fees=round(profit_after_fees, 2) if profit_after_fees is not None else None,
        )

    def calculate_three_way(
        self,
        odds_a: float,
        odds_b: float,
        odds_c: float,
        bankroll: float,
        outcome_a_name: str = "Outcome A",
        outcome_b_name: str = "Outcome B",
        outcome_c_name: str = "Draw",
        book_a: str = "Book A",
        book_b: str = "Book B",
        book_c: str = "Book C",
        fee_pct: float | None = None,
    ) -> StakeBreakdown:
        """Calculate exact stakes for a 3-outcome arb bet (e.g., soccer)."""
        prob_a = 1 / odds_a
        prob_b = 1 / odds_b
        prob_c = 1 / odds_c
        combined = prob_a + prob_b + prob_c
        
        if combined >= 1.0:
            raise ValueError(
                f"No arbitrage opportunity exists. Combined implied probability "
                f"is {combined:.4f} (needs to be < 1.0)."
            )
        
        guaranteed_return = bankroll / combined
        
        stake_a = bankroll * prob_a / combined
        stake_b = bankroll * prob_b / combined
        stake_c = bankroll * prob_c / combined
        
        profit = guaranteed_return - bankroll
        profit_pct = (profit / bankroll) * 100
        
        return_if_a = stake_a * odds_a
        return_if_b = stake_b * odds_b
        return_if_c = stake_c * odds_c
        
        from .odds_converter import OddsConverter
        american_a = OddsConverter.decimal_to_american(odds_a)
        american_b = OddsConverter.decimal_to_american(odds_b)
        american_c = OddsConverter.decimal_to_american(odds_c)
        
        fee = self.default_fee_pct if fee_pct is None else fee_pct
        profit_after_fees = profit - (guaranteed_return * fee / 100) if fee > 0 else None
        
        return StakeBreakdown(
            stakes={
                outcome_a_name: {
                    "book": book_a,
                    "stake": round(stake_a, 2),
                    "odds_decimal": round(odds_a, 4),
                    "odds_american": american_a,
                    "potential_return": round(return_if_a, 2),
                },
                outcome_b_name: {
                    "book": book_b,
                    "stake": round(stake_b, 2),
                    "odds_decimal": round(odds_b, 4),
                    "odds_american": american_b,
                    "potential_return": round(return_if_b, 2),
                },
                outcome_c_name: {
                    "book": book_c,
                    "stake": round(stake_c, 2),
                    "odds_decimal": round(odds_c, 4),
                    "odds_american": american_c,
                    "potential_return": round(return_if_c, 2),
                },
            },
            total_stake=round(bankroll, 2),
            guaranteed_return=round(guaranteed_return, 2),
            guaranteed_profit=round(profit, 2),
            profit_percentage=round(profit_pct, 4),
            scenario_outcomes=[
                {
                    "outcome": f"{outcome_a_name} wins",
                    "return": round(return_if_a, 2),
                    "profit": round(return_if_a - bankroll, 2),
                },
                {
                    "outcome": f"{outcome_b_name} wins",
                    "return": round(return_if_b, 2),
                    "profit": round(return_if_b - bankroll, 2),
                },
                {
                    "outcome": f"{outcome_c_name}",
                    "return": round(return_if_c, 2),
                    "profit": round(return_if_c - bankroll, 2),
                },
            ],
            profit_after_fees=round(profit_after_fees, 2) if profit_after_fees is not None else None,
        )

    def fill_arb_opportunity(
        self, arb: ArbOpportunity, bankroll: float, fee_pct: float | None = None
    ) -> tuple[ArbOpportunity, StakeBreakdown]:
        """
        Fill in the stake amounts for a detected ArbOpportunity.
        
        Returns the updated ArbOpportunity and a full StakeBreakdown.
        """
        if arb.outcome_c is not None:
            breakdown = self.calculate_three_way(
                odds_a=arb.odds_a_decimal,
                odds_b=arb.odds_b_decimal,
                odds_c=arb.odds_c_decimal,
                bankroll=bankroll,
                outcome_a_name=arb.outcome_a,
                outcome_b_name=arb.outcome_b,
                outcome_c_name=arb.outcome_c,
                book_a=arb.book_a,
                book_b=arb.book_b,
                book_c=arb.book_c,
                fee_pct=fee_pct,
            )
            arb.stake_c = breakdown.stakes[arb.outcome_c]["stake"]
        else:
            breakdown = self.calculate_two_way(
                odds_a=arb.odds_a_decimal,
                odds_b=arb.odds_b_decimal,
                bankroll=bankroll,
                outcome_a_name=arb.outcome_a,
                outcome_b_name=arb.outcome_b,
                book_a=arb.book_a,
                book_b=arb.book_b,
                fee_pct=fee_pct,
            )
        
        arb.stake_a = breakdown.stakes[arb.outcome_a]["stake"]
        arb.stake_b = breakdown.stakes[arb.outcome_b]["stake"]
        arb.total_stake = breakdown.total_stake
        arb.guaranteed_return = breakdown.guaranteed_return
        arb.guaranteed_profit = breakdown.guaranteed_profit
        
        return arb, breakdown
