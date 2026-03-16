"""
Sportsbook Fee & Trust Database
ONLY US state-licensed, regulated sportsbooks. No offshore books.
Research verified March 2026: All major US books have $0 withdrawal fees.
"""

SPORTSBOOK_DATA = {
    "fanduel": {
        "display_name": "FanDuel", "withdrawal_fee_pct": 0.0,
        "min_withdrawal": 10.0, "min_bet": 0.10, "payout_speed_days": "1-3",
        "trusted": True, "us_licensed": True, "states_count": 21,
        "license_info": "Licensed in 21+ states. Largest US sportsbook (~38% market share).",
        "notes": "No fees. PayPal/Venmo/ACH free. Fastest payouts.",
        "arb_risk": "medium",
    },
    "draftkings": {
        "display_name": "DraftKings", "withdrawal_fee_pct": 0.0,
        "min_withdrawal": 20.0, "min_bet": 0.10, "payout_speed_days": "1-3",
        "trusted": True, "us_licensed": True, "states_count": 24,
        "license_info": "Licensed in 24+ states. 2nd largest (~29% share).",
        "notes": "No fees. $20 min withdrawal. Dropped surcharge Aug 2024.",
        "arb_risk": "high",
    },
    "betmgm": {
        "display_name": "BetMGM", "withdrawal_fee_pct": 0.0,
        "min_withdrawal": 20.0, "min_bet": 0.50, "payout_speed_days": "3-5",
        "trusted": True, "us_licensed": True, "states_count": 20,
        "license_info": "Operated by Entain/MGM. Licensed in 20+ states.",
        "notes": "No fees. Higher min bet ($0.50). Slightly slower payouts.",
        "arb_risk": "medium",
    },
    "caesars": {
        "display_name": "Caesars Sportsbook", "withdrawal_fee_pct": 0.0,
        "min_withdrawal": 20.0, "min_bet": 0.10, "payout_speed_days": "3-5",
        "trusted": True, "us_licensed": True, "states_count": 20,
        "license_info": "Operated by Caesars Entertainment. 20+ states.",
        "notes": "No fees. Strong market coverage.",
        "arb_risk": "medium",
    },
    "espnbet": {
        "display_name": "ESPN BET", "withdrawal_fee_pct": 0.0,
        "min_withdrawal": 10.0, "min_bet": 0.50, "payout_speed_days": "2-5",
        "trusted": True, "us_licensed": True, "states_count": 17,
        "license_info": "Operated by Penn Entertainment. 17+ states.",
        "notes": "No fees. Powered by Penn National.",
        "arb_risk": "low",
    },
    "fanatics": {
        "display_name": "Fanatics Sportsbook", "withdrawal_fee_pct": 0.0,
        "min_withdrawal": 10.0, "min_bet": 0.50, "payout_speed_days": "1-2",
        "trusted": True, "us_licensed": True, "states_count": 23,
        "license_info": "Licensed in 23 states + DC. Fastest-growing.",
        "notes": "No fees. Fastest payouts (24-48 hrs). Never accepted credit cards.",
        "arb_risk": "low",
    },
    "hardrockbet": {
        "display_name": "Hard Rock Bet", "withdrawal_fee_pct": 0.0,
        "min_withdrawal": 10.0, "min_bet": 0.50, "payout_speed_days": "2-5",
        "trusted": True, "us_licensed": True, "states_count": 6,
        "license_info": "Operated by Seminole Tribe. FL, AZ, NJ, VA, OH, TN.",
        "notes": "No fees. Competitive odds. Expanding rapidly.",
        "arb_risk": "low",
    },
    "betrivers": {
        "display_name": "BetRivers", "withdrawal_fee_pct": 0.0,
        "min_withdrawal": 10.0, "min_bet": 0.50, "payout_speed_days": "2-5",
        "trusted": True, "us_licensed": True, "states_count": 15,
        "license_info": "Operated by Rush Street Interactive. 15+ states.",
        "notes": "No fees. Lower $10 minimum.",
        "arb_risk": "low",
    },
    "pointsbet": {
        "display_name": "PointsBet", "withdrawal_fee_pct": 0.0,
        "min_withdrawal": 20.0, "min_bet": 0.50, "payout_speed_days": "2-5",
        "trusted": True, "us_licensed": True, "states_count": 13,
        "license_info": "Acquired by Fanatics. 13 states.",
        "notes": "No fees. Transitioning to Fanatics platform.",
        "arb_risk": "low",
    },
    "bet365": {
        "display_name": "bet365", "withdrawal_fee_pct": 0.0,
        "min_withdrawal": 10.0, "min_bet": 0.50, "payout_speed_days": "1-3",
        "trusted": True, "us_licensed": True, "states_count": 10,
        "license_info": "World's largest sportsbook. NJ, CO, OH, VA + expanding.",
        "notes": "No fees. Highest limits. Excellent live betting.",
        "arb_risk": "high",
    },
    "unibet": {
        "display_name": "Unibet", "withdrawal_fee_pct": 0.0,
        "min_withdrawal": 10.0, "min_bet": 0.10, "payout_speed_days": "3-5",
        "trusted": True, "us_licensed": True, "states_count": 5,
        "license_info": "Operated by Kindred Group. NJ, PA, IN, IA, VA.",
        "notes": "No fees. European operator.",
        "arb_risk": "medium",
    },
}

DEFAULT_TRUSTED_BOOKS = [
    "fanduel", "draftkings", "betmgm", "caesars", "espnbet",
    "fanatics", "hardrockbet", "betrivers", "pointsbet", "bet365",
]

def get_book_fee(book_key): return SPORTSBOOK_DATA.get(book_key, {}).get("withdrawal_fee_pct", 0.0)
def get_book_info(book_key): return SPORTSBOOK_DATA.get(book_key)
def get_all_books(): return SPORTSBOOK_DATA
def is_trusted(book_key):
    b = SPORTSBOOK_DATA.get(book_key)
    return b.get("trusted", False) and b.get("us_licensed", False) if b else False
def get_arb_risk(book_key): return SPORTSBOOK_DATA.get(book_key, {}).get("arb_risk", "unknown")
