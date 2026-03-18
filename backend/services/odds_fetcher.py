"""
Odds Fetcher Service
Integrates with The Odds API (https://the-odds-api.com/) to pull real-time
sportsbook odds across multiple bookmakers.

API docs: https://the-odds-api.com/liveapi/guides/v4/

Free tier: 500 requests/month
Paid tiers: $20-$80/month for higher limits
"""

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

BASE_URL = "https://api.the-odds-api.com/v4"


class OddsFetcher:
    """Fetch odds data from The Odds API."""

    def __init__(
        self,
        api_key: str,
        regions: str = "us",
        odds_format: str = "decimal",
        bookmakers: list[str] | None = None,
    ):
        """
        Args:
            api_key: Your The Odds API key
            regions: Comma-separated regions (us, us2, uk, eu, au)
            odds_format: "decimal" or "american"
            bookmakers: Optional list of specific bookmaker keys to filter
        """
        self.api_key = api_key
        self.regions = regions
        self.odds_format = odds_format
        self.bookmakers = bookmakers
        self.remaining_requests: int | None = None
        self.used_requests: int | None = None

    def _get_httpx(self):
        """Lazy import httpx so mock can work without it."""
        import httpx
        return httpx

    async def get_sports(self) -> list[dict]:
        """
        Get list of available sports.
        
        Returns:
            List of sport objects with keys: key, group, title, active
        """
        httpx = self._get_httpx()
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BASE_URL}/sports",
                params={"apiKey": self.api_key},
                timeout=30.0,
            )
            response.raise_for_status()
            self._update_usage(response)
            return response.json()

    async def get_odds(
        self,
        sport: str,
        markets: str = "h2h",
        bookmakers_override: list[str] | None = None,
    ) -> list[dict]:
        """
        Get odds for a specific sport across all bookmakers.
        Includes retry logic for reliability.
        """
        httpx = self._get_httpx()
        params = {
            "apiKey": self.api_key,
            "regions": self.regions,
            "oddsFormat": self.odds_format,
            "markets": markets,
        }
        
        books = bookmakers_override or self.bookmakers
        if books:
            params["bookmakers"] = ",".join(books)

        # Retry up to 2 times on failure
        last_error = None
        for attempt in range(3):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{BASE_URL}/sports/{sport}/odds",
                        params=params,
                        timeout=45.0,
                    )
                    response.raise_for_status()
                    self._update_usage(response)
                    
                    events = response.json()
                    logger.info(
                        f"Fetched {len(events)} events for {sport} "
                        f"(Remaining API requests: {self.remaining_requests})"
                    )
                    return events
            except Exception as e:
                last_error = e
                if attempt < 2:
                    logger.warning(f"Retry {attempt + 1} for {sport}: {e}")
                    import asyncio
                    await asyncio.sleep(1)  # Brief pause before retry

        logger.error(f"Failed to fetch {sport} after 3 attempts: {last_error}")
        raise last_error

    async def get_all_odds(self, sports: list[str], markets: str = "h2h",
                          on_usage: callable = None) -> list[dict]:
        """
        Get odds for multiple sports.
        Retries individual sports on failure, logs clearly what succeeded/failed.

        Args:
            on_usage: Optional callback(remaining, used) called after each sport
                      to allow key rotation mid-scan.
        """
        all_events = []
        succeeded = []
        failed = []

        for sport in sports:
            try:
                events = await self.get_odds(sport, markets)
                all_events.extend(events)
                succeeded.append(sport)

                # Report usage after each sport so key manager can rotate mid-scan
                if on_usage and self.remaining_requests is not None:
                    on_usage(self.remaining_requests, self.used_requests)
            except Exception as e:
                failed.append(sport)
                logger.error(f"Skipping {sport}: {e}")
        
        if failed:
            logger.warning(f"Scan complete: {len(succeeded)} sports OK, {len(failed)} failed: {failed}")
        else:
            logger.info(f"Scan complete: all {len(succeeded)} sports fetched, {len(all_events)} total events")

        return all_events

    def _update_usage(self, response):
        """Track API usage from response headers."""
        self.remaining_requests = int(
            response.headers.get("x-requests-remaining", -1)
        )
        self.used_requests = int(
            response.headers.get("x-requests-used", -1)
        )

    def get_usage(self) -> dict:
        """Get current API usage stats."""
        return {
            "remaining_requests": self.remaining_requests,
            "used_requests": self.used_requests,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


# ─── Mock data for development/testing ───────────────────────────────────────

MOCK_EVENTS = [
    {
        "id": "mock_nba_001",
        "sport_key": "basketball_nba",
        "sport_title": "NBA",
        "commence_time": "2026-03-20T00:00:00Z",
        "home_team": "Los Angeles Lakers",
        "away_team": "Boston Celtics",
        "bookmakers": [
            {
                "key": "fanduel",
                "title": "FanDuel",
                "markets": [
                    {
                        "key": "h2h",
                        "outcomes": [
                            {"name": "Los Angeles Lakers", "price": 2.45},
                            {"name": "Boston Celtics", "price": 1.62},
                        ],
                    }
                ],
            },
            {
                "key": "draftkings",
                "title": "DraftKings",
                "markets": [
                    {
                        "key": "h2h",
                        "outcomes": [
                            {"name": "Los Angeles Lakers", "price": 2.30},
                            {"name": "Boston Celtics", "price": 1.70},
                        ],
                    }
                ],
            },
            {
                "key": "betmgm",
                "title": "BetMGM",
                "markets": [
                    {
                        "key": "h2h",
                        "outcomes": [
                            {"name": "Los Angeles Lakers", "price": 2.55},
                            {"name": "Boston Celtics", "price": 1.55},
                        ],
                    }
                ],
            },
            {
                "key": "caesars",
                "title": "Caesars",
                "markets": [
                    {
                        "key": "h2h",
                        "outcomes": [
                            {"name": "Los Angeles Lakers", "price": 2.35},
                            {"name": "Boston Celtics", "price": 1.68},
                        ],
                    }
                ],
            },
        ],
    },
    {
        "id": "mock_nba_002",
        "sport_key": "basketball_nba",
        "sport_title": "NBA",
        "commence_time": "2026-03-20T02:30:00Z",
        "home_team": "Golden State Warriors",
        "away_team": "Milwaukee Bucks",
        "bookmakers": [
            {
                "key": "fanduel",
                "title": "FanDuel",
                "markets": [
                    {
                        "key": "h2h",
                        "outcomes": [
                            {"name": "Golden State Warriors", "price": 1.91},
                            {"name": "Milwaukee Bucks", "price": 1.95},
                        ],
                    }
                ],
            },
            {
                "key": "draftkings",
                "title": "DraftKings",
                "markets": [
                    {
                        "key": "h2h",
                        "outcomes": [
                            {"name": "Golden State Warriors", "price": 2.05},
                            {"name": "Milwaukee Bucks", "price": 1.85},
                        ],
                    }
                ],
            },
            {
                "key": "hardrockbet",
                "title": "Hard Rock Bet",
                "markets": [
                    {
                        "key": "h2h",
                        "outcomes": [
                            {"name": "Golden State Warriors", "price": 2.10},
                            {"name": "Milwaukee Bucks", "price": 1.80},
                        ],
                    }
                ],
            },
        ],
    },
    {
        "id": "mock_nfl_001",
        "sport_key": "americanfootball_nfl",
        "sport_title": "NFL",
        "commence_time": "2026-03-22T18:00:00Z",
        "home_team": "Kansas City Chiefs",
        "away_team": "Philadelphia Eagles",
        "bookmakers": [
            {
                "key": "fanduel",
                "title": "FanDuel",
                "markets": [
                    {
                        "key": "h2h",
                        "outcomes": [
                            {"name": "Kansas City Chiefs", "price": 1.74},
                            {"name": "Philadelphia Eagles", "price": 2.20},
                        ],
                    }
                ],
            },
            {
                "key": "draftkings",
                "title": "DraftKings",
                "markets": [
                    {
                        "key": "h2h",
                        "outcomes": [
                            {"name": "Kansas City Chiefs", "price": 1.80},
                            {"name": "Philadelphia Eagles", "price": 2.15},
                        ],
                    }
                ],
            },
            {
                "key": "betmgm",
                "title": "BetMGM",
                "markets": [
                    {
                        "key": "h2h",
                        "outcomes": [
                            {"name": "Kansas City Chiefs", "price": 1.70},
                            {"name": "Philadelphia Eagles", "price": 2.30},
                        ],
                    }
                ],
            },
        ],
    },
    # This one is designed to have an arb (BetMGM Lakers 2.55 + DraftKings Celtics 1.70)
    # Implied: 1/2.55 + 1/1.70 = 0.3922 + 0.5882 = 0.9804 < 1.0 -> ARB!
    # And also: FanDuel Lakers 2.45 + DraftKings Celtics 1.70 
    # Implied: 1/2.45 + 1/1.70 = 0.4082 + 0.5882 = 0.9964 < 1.0 -> Small ARB!
    
    # Soccer 3-way example
    {
        "id": "mock_epl_001",
        "sport_key": "soccer_epl",
        "sport_title": "EPL",
        "commence_time": "2026-03-21T15:00:00Z",
        "home_team": "Arsenal",
        "away_team": "Liverpool",
        "bookmakers": [
            {
                "key": "fanduel",
                "title": "FanDuel",
                "markets": [
                    {
                        "key": "h2h",
                        "outcomes": [
                            {"name": "Arsenal", "price": 2.60},
                            {"name": "Liverpool", "price": 2.90},
                            {"name": "Draw", "price": 3.40},
                        ],
                    }
                ],
            },
            {
                "key": "draftkings",
                "title": "DraftKings",
                "markets": [
                    {
                        "key": "h2h",
                        "outcomes": [
                            {"name": "Arsenal", "price": 2.75},
                            {"name": "Liverpool", "price": 2.70},
                            {"name": "Draw", "price": 3.50},
                        ],
                    }
                ],
            },
            {
                "key": "betmgm",
                "title": "BetMGM",
                "markets": [
                    {
                        "key": "h2h",
                        "outcomes": [
                            {"name": "Arsenal", "price": 2.55},
                            {"name": "Liverpool", "price": 3.00},
                            {"name": "Draw", "price": 3.60},
                        ],
                    }
                ],
            },
        ],
    },
]


class MockOddsFetcher:
    """Mock fetcher for development and testing."""

    def __init__(self):
        self.remaining_requests = 500
        self.used_requests = 0

    async def get_sports(self) -> list[dict]:
        return [
            {"key": "basketball_nba", "group": "Basketball", "title": "NBA", "active": True},
            {"key": "americanfootball_nfl", "group": "American Football", "title": "NFL", "active": True},
            {"key": "soccer_epl", "group": "Soccer", "title": "EPL", "active": True},
        ]

    async def get_odds(self, sport: str, markets: str = "h2h", **kwargs) -> list[dict]:
        return [e for e in MOCK_EVENTS if e["sport_key"] == sport]

    async def get_all_odds(self, sports: list[str], markets: str = "h2h") -> list[dict]:
        all_events = []
        for sport in sports:
            events = await self.get_odds(sport, markets)
            all_events.extend(events)
        return all_events

    def get_usage(self) -> dict:
        return {
            "remaining_requests": self.remaining_requests,
            "used_requests": self.used_requests,
        }