"""
Smart Scheduler
Runs arb scans at optimal times and sends email digests.

Optimal scan windows (all times ET):
- 11:00 AM: Lines posted for evening games (NBA, NHL, MLB)
- 12:30 PM: Mid-day check, lines moving
- 5:30 PM: Pre-game rush, best arb windows
- 6:30 PM: Right before tip-off/puck drop
- 8:00 PM: Late games + west coast lines

API optimization:
- Each scan uses ~1 request per sport
- 6 sports x 5 scans/day = ~30 requests/day
- 30 x 30 days = ~900/month (under 2 keys worth)
- Skip sports with no games (weekday NFL, off-season, etc.)
"""

import asyncio
import logging
from datetime import datetime, time, timezone, timedelta
from typing import Callable, Awaitable

logger = logging.getLogger(__name__)

# ET timezone - compute correct offset based on DST
def _get_et_offset() -> timedelta:
    """Get current ET offset. EDT (Mar-Nov) = UTC-4, EST (Nov-Mar) = UTC-5."""
    now = datetime.now(timezone.utc)
    month = now.month
    # Simplified DST check: March 2nd Sunday through November 1st Sunday
    # Good enough for our purposes
    if 3 <= month <= 10:
        return timedelta(hours=-4)  # EDT
    elif month == 11:
        # First Sunday of November
        return timedelta(hours=-5)  # EST (approximate)
    else:
        return timedelta(hours=-5)  # EST (Dec, Jan, Feb)

# Default scan schedule (ET times)
# Peak window (5-8pm) gets extra scans since that's when arbs appear most
DEFAULT_SCHEDULE = [
    {"hour": 11, "minute": 0, "label": "Morning lines"},
    {"hour": 12, "minute": 30, "label": "Mid-day check"},
    {"hour": 17, "minute": 0, "label": "Pre-game early"},
    {"hour": 17, "minute": 30, "label": "Pre-game rush"},
    {"hour": 18, "minute": 0, "label": "Line movement"},
    {"hour": 18, "minute": 30, "label": "Tip-off window"},
    {"hour": 19, "minute": 0, "label": "Early games"},
    {"hour": 19, "minute": 30, "label": "Line adjustments"},
    {"hour": 20, "minute": 0, "label": "Late games"},
]
# 9 scans x ~6 sports = ~54 API calls/day = ~1620/month (needs 3-4 keys)

# Sports to scan by time of day (skip irrelevant sports to save API calls)
SPORT_SCHEDULE = {
    "morning": [
        "basketball_nba", "icehockey_nhl", "baseball_mlb",
        "soccer_epl", "soccer_usa_mls",
    ],
    "afternoon": [
        "basketball_nba", "icehockey_nhl", "baseball_mlb",
        "americanfootball_nfl", "soccer_epl", "soccer_usa_mls",
    ],
    "evening": [
        "basketball_nba", "icehockey_nhl", "baseball_mlb",
        "americanfootball_nfl",
    ],
}


def get_sports_for_time(hour_et: int) -> list[str]:
    """Get relevant sports based on ET hour."""
    if hour_et < 14:
        return SPORT_SCHEDULE["morning"]
    elif hour_et < 18:
        return SPORT_SCHEDULE["afternoon"]
    else:
        return SPORT_SCHEDULE["evening"]


def et_now() -> datetime:
    """Get current time in ET."""
    return datetime.now(timezone.utc) + _get_et_offset()


def next_scan_time(schedule: list[dict] | None = None) -> tuple[datetime, str]:
    """Calculate the next scheduled scan time (in UTC)."""
    schedule = schedule or DEFAULT_SCHEDULE
    now_et = et_now()
    today = now_et.date()

    for slot in schedule:
        scan_et = datetime.combine(
            today,
            time(slot["hour"], slot["minute"]),
            tzinfo=timezone(_get_et_offset()),
        )
        if scan_et > now_et:
            scan_utc = scan_et - _get_et_offset()  # Convert to UTC
            return scan_utc, slot["label"]

    # All today's scans passed, schedule first scan tomorrow
    tomorrow = today + timedelta(days=1)
    first = schedule[0]
    scan_et = datetime.combine(
        tomorrow,
        time(first["hour"], first["minute"]),
        tzinfo=timezone(_get_et_offset()),
    )
    scan_utc = scan_et - _get_et_offset()
    return scan_utc, first["label"]


class SmartScheduler:
    """Manages scheduled scans with optimal timing and API conservation."""

    def __init__(self):
        self.enabled: bool = False
        self.schedule: list[dict] = list(DEFAULT_SCHEDULE)
        self.task: asyncio.Task | None = None
        self.last_run: str | None = None
        self.last_label: str | None = None
        self.next_run: str | None = None
        self.next_label: str | None = None
        self.total_scheduled_runs: int = 0
        self._scan_callback: Callable[..., Awaitable] | None = None
        self._notify_callback: Callable[..., Awaitable] | None = None

    def set_callbacks(
        self,
        scan_fn: Callable[..., Awaitable],
        notify_fn: Callable[..., Awaitable],
    ):
        """Set the scan and notification functions to call on schedule."""
        self._scan_callback = scan_fn
        self._notify_callback = notify_fn

    def start(self):
        if self.enabled:
            return
        self.enabled = True
        self.task = asyncio.create_task(self._run_loop())
        nxt, label = next_scan_time(self.schedule)
        self.next_run = nxt.isoformat()
        self.next_label = label
        logger.info(f"Scheduler started. Next scan: {label} at {nxt.isoformat()}")

    def stop(self):
        self.enabled = False
        if self.task and not self.task.done():
            self.task.cancel()
        self.next_run = None
        self.next_label = None
        logger.info("Scheduler stopped")

    async def _run_loop(self):
        """Main scheduler loop - sleeps until next scan time, runs, repeats."""
        while self.enabled:
            try:
                nxt, label = next_scan_time(self.schedule)
                self.next_run = nxt.isoformat()
                self.next_label = label

                # Calculate sleep duration
                now = datetime.now(timezone.utc)
                sleep_seconds = (nxt - now).total_seconds()

                if sleep_seconds > 0:
                    logger.info(
                        f"Scheduler: next scan '{label}' in "
                        f"{int(sleep_seconds // 3600)}h {int((sleep_seconds % 3600) // 60)}m"
                    )
                    await asyncio.sleep(sleep_seconds)

                if not self.enabled:
                    break

                # Run the scan
                logger.info(f"Scheduler: running '{label}' scan...")
                hour_et = et_now().hour
                sports = get_sports_for_time(hour_et)

                if self._scan_callback:
                    arbs = await self._scan_callback(sports)
                    self.last_run = datetime.now(timezone.utc).isoformat()
                    self.last_label = label
                    self.total_scheduled_runs += 1

                    # Always notify - even with 0 arbs so user knows system is alive
                    if self._notify_callback:
                        await self._notify_callback(arbs or [], label)

                    logger.info(
                        f"Scheduler: '{label}' complete. "
                        f"Found {len(arbs) if arbs else 0} arbs. "
                        f"Used {len(sports)} API requests."
                    )

                # Small buffer before calculating next
                await asyncio.sleep(60)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                await asyncio.sleep(300)  # Wait 5 min on error

    def get_status(self) -> dict:
        now_et = et_now()
        return {
            "enabled": self.enabled,
            "current_time_et": now_et.strftime("%I:%M %p ET"),
            "schedule": [
                {
                    "time_et": f"{s['hour']}:{s['minute']:02d}",
                    "label": s["label"],
                }
                for s in self.schedule
            ],
            "next_scan": self.next_label,
            "next_scan_time": self.next_run,
            "last_scan": self.last_label,
            "last_scan_time": self.last_run,
            "total_runs": self.total_scheduled_runs,
            "estimated_daily_api_calls": len(self.schedule) * 6,  # ~6 sports per scan
        }