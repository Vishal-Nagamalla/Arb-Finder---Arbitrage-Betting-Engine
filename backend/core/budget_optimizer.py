"""
Budget Optimizer
Given a total budget and list of arb opportunities, determines the optimal
allocation across multiple arbs to maximize total guaranteed profit while:
1. Staying within the budget
2. Spreading bets across different sportsbooks (anti-detection)
3. Respecting minimum bet amounts per book

Uses a greedy allocation with book rotation penalties.
"""

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class BudgetAllocation:
    """A single arb bet within a budget plan."""
    arb: dict                   # The arb opportunity data
    allocated_amount: float     # Total allocated to this arb
    stake_a: float              # Stake on outcome A
    stake_b: float              # Stake on outcome B
    stake_c: float | None       # Stake on outcome C (3-way)
    guaranteed_profit: float    # Profit from this allocation
    profit_pct: float           # ROI for this allocation
    rotation_score: float       # Book rotation safety score


@dataclass
class BudgetPlan:
    """Complete budget allocation plan across multiple arbs."""
    total_budget: float
    total_allocated: float
    total_remaining: float
    total_guaranteed_profit: float
    overall_roi: float
    allocations: list[BudgetAllocation]
    books_used: dict[str, int]       # book -> times used
    warnings: list[str]


def optimize_budget(
    budget: float,
    arbs: list[dict],
    book_rotation_scores: dict[str, float] | None = None,
    book_fee_lookup: dict[str, float] | None = None,
    max_per_arb_pct: float = 40.0,
    min_per_arb: float = 20.0,
    max_arbs: int = 10,
) -> BudgetPlan:
    """
    Allocate a budget across multiple arb opportunities.
    
    Args:
        budget: Total amount willing to invest
        arbs: List of ArbOpportunityResponse dicts
        book_rotation_scores: Pre-computed rotation scores {book: penalty}
        book_fee_lookup: {book_key: withdrawal_fee_pct} for fee-adjusted profit
        max_per_arb_pct: Max % of budget on any single arb
        min_per_arb: Minimum allocation per arb (below this, skip)
        max_arbs: Maximum number of different arbs to spread across
    
    Returns:
        BudgetPlan with optimal allocations (profits are fee-adjusted)
    """
    if not arbs:
        return BudgetPlan(
            total_budget=budget, total_allocated=0, total_remaining=budget,
            total_guaranteed_profit=0, overall_roi=0,
            allocations=[], books_used={}, warnings=["No arb opportunities available"],
        )

    remaining = budget
    allocations: list[BudgetAllocation] = []
    books_used: dict[str, int] = {}
    warnings: list[str] = []
    used_events: set[str] = set()

    # Score and sort arbs
    scored_arbs = []
    for arb in arbs:
        profit_pct = arb.get("profit_percentage", 0)
        if profit_pct <= 0:
            continue

        book_a = arb.get("book_a", "")
        book_b = arb.get("book_b", "")

        # Base rotation penalty
        penalty_a = (book_rotation_scores or {}).get(book_a, 1.0)
        penalty_b = (book_rotation_scores or {}).get(book_b, 1.0)

        # Additional penalty for books already used in this plan
        dynamic_a = penalty_a + books_used.get(book_a, 0) * 0.5
        dynamic_b = penalty_b + books_used.get(book_b, 0) * 0.5

        avg_penalty = (dynamic_a + dynamic_b) / 2
        score = profit_pct / max(avg_penalty, 0.5)

        scored_arbs.append((score, arb))

    scored_arbs.sort(key=lambda x: x[0], reverse=True)

    for score, arb in scored_arbs:
        if remaining < min_per_arb:
            break
        if len(allocations) >= max_arbs:
            break

        # Skip duplicate events (different book combos for same game)
        event_key = arb.get("event_name", "")
        if event_key in used_events:
            continue

        # Smart allocation: weight by profit percentage relative to others
        # High ROI arbs get more money, low ROI arbs get less
        profit_pct = arb.get("profit_percentage", 0)

        # Check if these books are being overused in this plan
        book_a = arb.get("book_a", "")
        book_b = arb.get("book_b", "")
        times_a = books_used.get(book_a, 0)
        times_b = books_used.get(book_b, 0)
        max_book_uses = max(times_a, times_b)

        # Allocation strategy:
        # - First arb (best ROI, fresh books): gets up to 50% of remaining budget
        # - Subsequent arbs with fresh books: up to 40% of remaining
        # - Arbs reusing books already in plan: capped lower to spread risk
        if max_book_uses == 0:
            # Fresh books - allocate generously, proportional to ROI quality
            if len(allocations) == 0:
                alloc_amount = min(remaining, remaining * 0.6)  # Best arb gets up to 60%
            else:
                alloc_amount = min(remaining, remaining * 0.5)
        elif max_book_uses == 1:
            # Books used once already - reduce allocation
            alloc_amount = min(remaining, remaining * 0.35)
        else:
            # Books used 2+ times - minimal allocation for safety
            alloc_amount = min(remaining, remaining * 0.2)

        # Floor: don't go below minimum
        if alloc_amount < min_per_arb:
            continue

        # Calculate stakes proportionally
        profit_pct = arb.get("profit_percentage", 0)
        arb_margin = arb.get("arb_margin", 0)

        odds_a = arb.get("odds_a_decimal", 2.0)
        odds_b = arb.get("odds_b_decimal", 2.0)

        prob_a = 1 / odds_a
        prob_b = 1 / odds_b
        combined = prob_a + prob_b

        if combined >= 1.0:
            continue  # Not actually an arb

        stake_a = round(alloc_amount * prob_a / combined, 2)
        stake_b = round(alloc_amount * prob_b / combined, 2)
        actual_total = stake_a + stake_b

        guaranteed_return = actual_total / combined
        guaranteed_profit = round(guaranteed_return - actual_total, 2)

        # Deduct sportsbook fees from profit
        if book_fee_lookup:
            fee_a = book_fee_lookup.get(book_a, 0.0)
            fee_b = book_fee_lookup.get(book_b, 0.0)
            if fee_a > 0:
                guaranteed_profit -= round(guaranteed_return * (fee_a / 100), 2)
            if fee_b > 0:
                guaranteed_profit -= round(guaranteed_return * (fee_b / 100), 2)

        if guaranteed_profit <= 0:
            continue

        # Handle 3-way
        stake_c = None
        if arb.get("outcome_c") and arb.get("odds_c_decimal"):
            odds_c = arb["odds_c_decimal"]
            prob_c = 1 / odds_c
            combined_3 = prob_a + prob_b + prob_c
            if combined_3 >= 1.0:
                continue
            stake_a = round(alloc_amount * prob_a / combined_3, 2)
            stake_b = round(alloc_amount * prob_b / combined_3, 2)
            stake_c = round(alloc_amount * prob_c / combined_3, 2)
            actual_total = stake_a + stake_b + stake_c
            guaranteed_return = actual_total / combined_3
            guaranteed_profit = round(guaranteed_return - actual_total, 2)

            # Deduct fees for 3-way
            if book_fee_lookup:
                book_c = arb.get("book_c", "")
                fee_a = book_fee_lookup.get(book_a, 0.0)
                fee_b = book_fee_lookup.get(book_b, 0.0)
                fee_c = book_fee_lookup.get(book_c, 0.0)
                for fee in [fee_a, fee_b, fee_c]:
                    if fee > 0:
                        guaranteed_profit -= round(guaranteed_return * (fee / 100), 2)

        allocation = BudgetAllocation(
            arb=arb,
            allocated_amount=round(actual_total, 2),
            stake_a=stake_a,
            stake_b=stake_b,
            stake_c=stake_c,
            guaranteed_profit=guaranteed_profit,
            profit_pct=round((guaranteed_profit / actual_total) * 100, 2) if actual_total > 0 else 0,
            rotation_score=round(score, 4),
        )

        allocations.append(allocation)
        remaining -= actual_total
        used_events.add(event_key)

        # Track book usage
        book_a = arb.get("book_a", "")
        book_b = arb.get("book_b", "")
        books_used[book_a] = books_used.get(book_a, 0) + 1
        books_used[book_b] = books_used.get(book_b, 0) + 1

    # Warnings
    overused = [b for b, c in books_used.items() if c >= 3]
    if overused:
        warnings.append(f"Books used 3+ times (higher detection risk): {', '.join(overused)}")

    total_profit = sum(a.guaranteed_profit for a in allocations)
    total_allocated = sum(a.allocated_amount for a in allocations)

    return BudgetPlan(
        total_budget=budget,
        total_allocated=round(total_allocated, 2),
        total_remaining=round(budget - total_allocated, 2),
        total_guaranteed_profit=round(total_profit, 2),
        overall_roi=round((total_profit / total_allocated) * 100, 2) if total_allocated > 0 else 0,
        allocations=allocations,
        books_used=books_used,
        warnings=warnings,
    )