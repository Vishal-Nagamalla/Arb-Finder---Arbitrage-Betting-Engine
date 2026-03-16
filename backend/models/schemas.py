"""
Data Models / Schemas
Pure Python dataclasses - no external dependencies.
Pydantic versions can be swapped in when deploying with FastAPI.
"""

from dataclasses import dataclass, field


# Default sportsbooks to track
DEFAULT_BOOKS = [
    "fanduel", "draftkings", "betmgm", "caesars", "pointsbet",
    "betrivers", "unibet", "bovada", "hardrockbet", "espnbet",
]

DEFAULT_SPORTS = [
    "basketball_nba", "americanfootball_nfl", "baseball_mlb", "icehockey_nhl",
]


@dataclass
class ScanConfig:
    sports: list = field(default_factory=lambda: list(DEFAULT_SPORTS))
    min_profit_pct: float = 0.5
    max_profit_pct: float = 20.0
    poll_interval_seconds: int = 60
    bankroll: float = 1000.0


@dataclass
class AppConfig:
    odds_api_key: str = ""
    enabled_books: list = field(default_factory=lambda: list(DEFAULT_BOOKS))
    scan: ScanConfig = field(default_factory=ScanConfig)
