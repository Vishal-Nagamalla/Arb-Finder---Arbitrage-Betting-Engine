"""
Odds Converter Module
Handles conversion between American (+150, -200), Decimal (2.50, 1.50),
and Implied Probability (0.40, 0.667) formats.

All internal calculations use Decimal odds for consistency.
"""


class OddsConverter:
    """Convert between odds formats used by different sportsbooks."""

    @staticmethod
    def american_to_decimal(american: float) -> float:
        """
        Convert American odds to Decimal odds.
        
        American +150 -> Decimal 2.50  (bet 100, win 250 total)
        American -200 -> Decimal 1.50  (bet 200, win 300 total)
        """
        if american > 0:
            return 1 + (american / 100)
        elif american < 0:
            return 1 + (100 / abs(american))
        else:
            raise ValueError("American odds cannot be zero")

    @staticmethod
    def decimal_to_american(decimal: float) -> float:
        """
        Convert Decimal odds to American odds.
        
        Decimal 2.50 -> American +150
        Decimal 1.50 -> American -200
        """
        if decimal < 1.0:
            raise ValueError("Decimal odds must be >= 1.0")
        if decimal >= 2.0:
            return round((decimal - 1) * 100, 1)
        else:
            return round(-100 / (decimal - 1), 1)

    @staticmethod
    def decimal_to_implied_probability(decimal: float) -> float:
        """
        Convert Decimal odds to implied probability.
        
        Decimal 2.50 -> 0.40 (40% implied chance)
        Decimal 1.50 -> 0.667 (66.7% implied chance)
        """
        if decimal <= 0:
            raise ValueError("Decimal odds must be positive")
        return 1 / decimal

    @staticmethod
    def implied_probability_to_decimal(probability: float) -> float:
        """
        Convert implied probability to Decimal odds.
        
        0.40 -> Decimal 2.50
        0.667 -> Decimal 1.499
        """
        if probability <= 0 or probability >= 1:
            raise ValueError("Probability must be between 0 and 1 (exclusive)")
        return 1 / probability

    @staticmethod
    def american_to_implied_probability(american: float) -> float:
        """Shortcut: American odds to implied probability."""
        decimal = OddsConverter.american_to_decimal(american)
        return OddsConverter.decimal_to_implied_probability(decimal)

    @staticmethod
    def normalize_to_decimal(odds: float, fmt: str = "decimal") -> float:
        """
        Normalize any odds format to Decimal.
        
        Args:
            odds: The odds value
            fmt: One of "decimal", "american", "probability"
        
        Returns:
            Decimal odds as float
        """
        fmt = fmt.lower()
        if fmt == "decimal":
            return odds
        elif fmt == "american":
            return OddsConverter.american_to_decimal(odds)
        elif fmt == "probability":
            return OddsConverter.implied_probability_to_decimal(odds)
        else:
            raise ValueError(f"Unknown format: {fmt}. Use 'decimal', 'american', or 'probability'")
