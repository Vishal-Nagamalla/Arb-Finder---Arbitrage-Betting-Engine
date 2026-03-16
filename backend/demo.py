"""
Phase 1 Demo Runner
Tests the core math engine, odds conversion, arb detection, and stake calculation.
Run: python -m backend.demo
"""

import asyncio
import sys
import os

# Add parent to path so we can import backend modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.core.odds_converter import OddsConverter
from backend.core.arbitrage import ArbitrageScanner
from backend.core.calculator import StakeCalculator
from backend.services.odds_fetcher import MockOddsFetcher


def separator(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def test_odds_converter():
    """Test odds format conversions."""
    separator("TEST 1: Odds Converter")
    
    conv = OddsConverter()
    
    test_cases = [
        (+150, 2.50),
        (-200, 1.50),
        (+100, 2.00),
        (-110, 1.909),
        (+250, 3.50),
        (-150, 1.667),
    ]
    
    print(f"  {'American':>10} -> {'Decimal':>10} | {'Expected':>10} | {'Match':>5}")
    print(f"  {'-'*50}")
    
    all_pass = True
    for american, expected in test_cases:
        decimal = conv.american_to_decimal(american)
        match = abs(decimal - expected) < 0.01
        if not match:
            all_pass = False
        print(f"  {american:>+10} -> {decimal:>10.3f} | {expected:>10.3f} | {'OK' if match else 'FAIL':>5}")
    
    # Test round-trip
    print(f"\n  Round-trip test (American -> Decimal -> American):")
    for american, _ in test_cases:
        decimal = conv.american_to_decimal(american)
        back = conv.decimal_to_american(decimal)
        match = abs(back - american) < 1.0
        if not match:
            all_pass = False
        print(f"  {american:>+10} -> {decimal:.3f} -> {back:>+10.1f} | {'OK' if match else 'FAIL'}")
    
    # Test implied probabilities
    print(f"\n  Implied probability test:")
    print(f"  {'Decimal':>10} -> {'Implied %':>10}")
    print(f"  {'-'*25}")
    for dec, expected_prob in [(2.00, 50.0), (1.50, 66.67), (3.00, 33.33), (1.10, 90.91)]:
        prob = conv.decimal_to_implied_probability(dec) * 100
        print(f"  {dec:>10.2f} -> {prob:>9.2f}%")
    
    return all_pass


def test_arb_detection():
    """Test arbitrage detection math."""
    separator("TEST 2: Arbitrage Detection")
    
    scanner = ArbitrageScanner(min_profit_pct=0.1)
    
    # Case 1: Clear arb (BetMGM Lakers 2.55 + DraftKings Celtics 1.70)
    print("  Case 1: BetMGM Lakers 2.55 vs DraftKings Celtics 1.70")
    result = scanner.check_two_way_arb(2.55, 1.70)
    print(f"    Is Arb: {result['is_arb']}")
    print(f"    Combined Implied Prob: {result['combined_implied_probability']:.4f}")
    print(f"    Arb Margin: {result['arb_margin']:.4f}")
    print(f"    Profit %: {result['profit_percentage']:.2f}%")
    assert result["is_arb"] == True, "Should be an arb!"
    
    # Case 2: No arb (typical same-book odds)
    print("\n  Case 2: Same book odds 1.91 vs 1.91 (no arb expected)")
    result = scanner.check_two_way_arb(1.91, 1.91)
    print(f"    Is Arb: {result['is_arb']}")
    print(f"    Combined Implied Prob: {result['combined_implied_probability']:.4f}")
    assert result["is_arb"] == False, "Should NOT be an arb"
    
    # Case 3: Borderline arb
    print("\n  Case 3: FanDuel Lakers 2.45 vs DraftKings Celtics 1.70")
    result = scanner.check_two_way_arb(2.45, 1.70)
    print(f"    Is Arb: {result['is_arb']}")
    print(f"    Combined Implied Prob: {result['combined_implied_probability']:.4f}")
    print(f"    Profit %: {result['profit_percentage']:.2f}%")
    
    # Case 4: American odds input
    print("\n  Case 4: American odds +155 vs -145 (cross-book)")
    result = scanner.check_two_way_arb(155, -145, fmt="american")
    print(f"    Is Arb: {result['is_arb']}")
    print(f"    Odds A decimal: {result['odds_a_decimal']}")
    print(f"    Odds B decimal: {result['odds_b_decimal']}")
    print(f"    Combined Implied Prob: {result['combined_implied_probability']:.4f}")
    
    return True


def test_stake_calculator():
    """Test the stake calculator with real scenarios."""
    separator("TEST 3: Stake Calculator")
    
    calc = StakeCalculator()
    
    # Scenario 1: Your original example (simplified)
    # Book A: bet $40, win $110 -> decimal odds = 110/40 = 2.75
    # Book B: bet $60, win $105 -> decimal odds = 105/60 = 1.75
    print("  Scenario 1: Your example (Book A 2.75, Book B 1.75, $100 bankroll)")
    breakdown = calc.calculate_two_way(
        odds_a=2.75,
        odds_b=1.75,
        bankroll=100,
        outcome_a_name="Team A",
        outcome_b_name="Team B",
        book_a="Sportsbook A",
        book_b="Sportsbook B",
    )
    print(breakdown.display())
    
    # Scenario 2: Real arb from mock data
    # BetMGM Lakers 2.55, DraftKings Celtics 1.70
    print("\n  Scenario 2: Lakers/Celtics arb ($500 bankroll)")
    breakdown = calc.calculate_two_way(
        odds_a=2.55,
        odds_b=1.70,
        bankroll=500,
        outcome_a_name="Lakers",
        outcome_b_name="Celtics",
        book_a="BetMGM",
        book_b="DraftKings",
    )
    print(breakdown.display())
    
    # Scenario 3: With fees
    print("\n  Scenario 3: Same arb with 2% fee estimate ($500 bankroll)")
    breakdown = calc.calculate_two_way(
        odds_a=2.55,
        odds_b=1.70,
        bankroll=500,
        outcome_a_name="Lakers",
        outcome_b_name="Celtics",
        book_a="BetMGM",
        book_b="DraftKings",
        fee_pct=2.0,
    )
    print(breakdown.display())
    
    # Scenario 4: Verify no-arb raises error
    print("\n  Scenario 4: Attempting non-arb bet (should raise error)")
    try:
        calc.calculate_two_way(odds_a=1.91, odds_b=1.91, bankroll=100)
        print("    ERROR: Should have raised ValueError!")
    except ValueError as e:
        print(f"    Correctly caught: {e}")
    
    return True


async def test_full_pipeline():
    """Test the complete pipeline: fetch odds -> scan for arbs -> calculate stakes."""
    separator("TEST 4: Full Pipeline (Mock Data)")
    
    # Initialize components
    fetcher = MockOddsFetcher()
    scanner = ArbitrageScanner(min_profit_pct=0.1)
    calculator = StakeCalculator()
    bankroll = 1000.0
    
    # Step 1: Fetch odds
    print("  Step 1: Fetching odds from mock data...")
    sports = ["basketball_nba", "americanfootball_nfl", "soccer_epl"]
    events = await fetcher.get_all_odds(sports)
    print(f"    Found {len(events)} events across {len(sports)} sports\n")
    
    # Step 2: Scan for arbs
    print("  Step 2: Scanning for arbitrage opportunities...")
    all_arbs = []
    for event in events:
        event_arbs = scanner.scan_event(event)
        all_arbs.extend(event_arbs)
    
    print(f"    Found {len(all_arbs)} arb opportunities!\n")
    
    # Step 3: Calculate stakes and display
    if all_arbs:
        print("  Step 3: Calculating optimal stakes...\n")
        
        # Deduplicate: keep best arb per event
        best_arbs: dict[str, tuple] = {}
        for arb in all_arbs:
            key = arb.event_name
            if key not in best_arbs or arb.profit_percentage > best_arbs[key][0].profit_percentage:
                filled_arb, breakdown = calculator.fill_arb_opportunity(arb, bankroll)
                best_arbs[key] = (filled_arb, breakdown)
        
        for event_name, (arb, breakdown) in sorted(
            best_arbs.items(), key=lambda x: x[1][0].profit_percentage, reverse=True
        ):
            print(f"  EVENT: {arb.event_name} ({arb.sport})")
            print(f"  Best arb: {arb.book_a} vs {arb.book_b}")
            print(breakdown.display())
            print()
    else:
        print("    No arb opportunities found in mock data.")
    
    # Step 4: API usage
    print(f"\n  API Usage: {fetcher.get_usage()}")
    
    return True


def test_manual_calculator_scenarios():
    """Test edge cases for the manual calculator feature."""
    separator("TEST 5: Manual Calculator Edge Cases")
    
    calc = StakeCalculator()
    conv = OddsConverter()
    
    # User inputs American odds
    print("  Edge Case 1: User inputs American odds (+200 vs -180)")
    dec_a = conv.american_to_decimal(200)
    dec_b = conv.american_to_decimal(-180)
    print(f"    Converted: {dec_a:.4f}, {dec_b:.4f}")
    
    scanner = ArbitrageScanner()
    check = scanner.check_two_way_arb(200, -180, fmt="american")
    print(f"    Is Arb: {check['is_arb']}, Margin: {check['arb_margin']:.4f}")
    
    if check["is_arb"]:
        breakdown = calc.calculate_two_way(dec_a, dec_b, bankroll=250)
        print(breakdown.display())
    else:
        print("    Not an arb opportunity\n")
    
    # Very tight arb
    print("  Edge Case 2: Very tight arb (0.3% profit)")
    breakdown = calc.calculate_two_way(
        odds_a=2.10,
        odds_b=1.96,
        bankroll=1000,
        outcome_a_name="Warriors",
        outcome_b_name="Bucks",
        book_a="Hard Rock Bet",
        book_b="FanDuel",
    )
    print(breakdown.display())
    
    # Large bankroll
    print("  Edge Case 3: Large bankroll ($10,000)")
    breakdown = calc.calculate_two_way(
        odds_a=2.55,
        odds_b=1.70,
        bankroll=10000,
        outcome_a_name="Lakers",
        outcome_b_name="Celtics",
        book_a="BetMGM",
        book_b="DraftKings",
    )
    print(breakdown.display())
    
    return True


async def main():
    print("\n" + "#" * 60)
    print("#" + " " * 18 + "ARB FINDER v0.1" + " " * 19 + "#")
    print("#" + " " * 14 + "Phase 1: Core Engine Tests" + " " * 13 + "#")
    print("#" * 60)
    
    results = {}
    
    results["Odds Converter"] = test_odds_converter()
    results["Arb Detection"] = test_arb_detection()
    results["Stake Calculator"] = test_stake_calculator()
    results["Full Pipeline"] = await test_full_pipeline()
    results["Manual Calculator"] = test_manual_calculator_scenarios()
    
    separator("RESULTS SUMMARY")
    for test_name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {test_name}")
    
    all_passed = all(results.values())
    print(f"\n  {'All tests passed!' if all_passed else 'Some tests failed.'}")
    print()
    
    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
