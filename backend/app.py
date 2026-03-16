"""
Arb Finder - FastAPI Backend (Phase 4)
Full application with key rotation, profit tracking, notifications, and fee data.

Run: uvicorn backend.app:app --reload --port 8000
"""

import asyncio
import os
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.config import get_api_key, load_env
from backend.core.odds_converter import OddsConverter
from backend.core.arbitrage import ArbitrageScanner, ArbOpportunity
from backend.core.calculator import StakeCalculator
from backend.services.odds_fetcher import OddsFetcher
from backend.services.key_rotation import KeyRotationManager
from backend.services.profit_tracker import ProfitTracker
from backend.services.notifications import NotificationService
from backend.services.sportsbook_fees import (
    get_book_fee, get_book_info, get_all_books, is_trusted, SPORTSBOOK_DATA, get_arb_risk,
)
from backend.services.book_rotation import BookRotationService
from backend.services.scheduler import SmartScheduler
from backend.core.budget_optimizer import optimize_budget

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ─── Pydantic Models ──────────────────────────────────────────────────────────

class ManualCalcRequest(BaseModel):
    odds_a: float
    odds_b: float
    odds_c: Optional[float] = None
    odds_format: str = "american"
    bankroll: float = Field(default=100.0, ge=1.0)
    outcome_a_name: str = "Team A"
    outcome_b_name: str = "Team B"
    outcome_c_name: str = "Draw"
    book_a: str = "Book A"
    book_b: str = "Book B"
    book_c: str = "Book C"
    fee_pct: float = Field(default=0.0, ge=0.0)

class StakeInfo(BaseModel):
    book: str
    stake: float
    odds_decimal: float
    odds_american: float
    potential_return: float

class CalcResponse(BaseModel):
    is_arb: bool
    stakes: dict[str, StakeInfo]
    total_stake: float
    guaranteed_return: float
    guaranteed_profit: float
    profit_percentage: float
    profit_after_fees: Optional[float] = None
    scenarios: list[dict]
    combined_implied_probability: float
    arb_margin: float

class ArbOpportunityResponse(BaseModel):
    event_name: str
    sport: str
    commence_time: Optional[str] = None
    outcome_a: str
    book_a: str
    book_a_display: Optional[str] = None
    odds_a_decimal: float
    odds_a_american: float
    stake_a: float
    outcome_b: str
    book_b: str
    book_b_display: Optional[str] = None
    odds_b_decimal: float
    odds_b_american: float
    stake_b: float
    outcome_c: Optional[str] = None
    book_c: Optional[str] = None
    book_c_display: Optional[str] = None
    odds_c_decimal: Optional[float] = None
    odds_c_american: Optional[float] = None
    stake_c: Optional[float] = None
    total_stake: float
    guaranteed_return: float
    guaranteed_profit: float
    guaranteed_profit_after_fees: Optional[float] = None
    profit_percentage: float
    arb_margin: float
    book_a_trusted: Optional[bool] = None
    book_b_trusted: Optional[bool] = None

class ScanResponse(BaseModel):
    opportunities: list[ArbOpportunityResponse]
    total_found: int
    events_scanned: int
    sports_scanned: list[str]
    bankroll: float
    scan_time: str
    api_usage: dict

class TrackBetRequest(BaseModel):
    event_name: str
    sport: str
    commence_time: Optional[str] = None
    outcome_a: str
    book_a: str
    odds_a_decimal: float
    odds_a_american: float
    stake_a: float
    outcome_b: str
    book_b: str
    odds_b_decimal: float
    odds_b_american: float
    stake_b: float
    outcome_c: Optional[str] = None
    book_c: Optional[str] = None
    odds_c_decimal: Optional[float] = None
    odds_c_american: Optional[float] = None
    stake_c: Optional[float] = None
    total_stake: float
    guaranteed_return: float
    guaranteed_profit: float
    profit_percentage: float
    arb_margin: float

class ResolveBetRequest(BaseModel):
    winning_outcome: str
    actual_profit: Optional[float] = None
    notes: Optional[str] = None

class AddKeyRequest(BaseModel):
    api_key: str

class AutoScanConfig(BaseModel):
    enabled: bool
    interval_seconds: int = Field(default=120, ge=30)
    bankroll: Optional[float] = None
    sports: Optional[list[str]] = None

class SettingsUpdate(BaseModel):
    bankroll: Optional[float] = Field(default=None, ge=1.0)
    scan_sports: Optional[list[str]] = None
    enabled_books: Optional[list[str]] = None
    min_profit_pct: Optional[float] = Field(default=None, ge=0.0)
    max_profit_pct: Optional[float] = Field(default=None, ge=0.0)
    auto_scan_interval: Optional[int] = Field(default=None, ge=30)

class NotificationConfigRequest(BaseModel):
    min_profit_to_notify: Optional[float] = None
    email_address: Optional[str] = None
    email_password: Optional[str] = None
    pushover_user_key: Optional[str] = None
    pushover_app_token: Optional[str] = None


# ─── Application State ────────────────────────────────────────────────────────

class AppState:
    def __init__(self):
        self.key_manager = KeyRotationManager()
        self.fetcher: Optional[OddsFetcher] = None
        self.scanner = ArbitrageScanner(min_profit_pct=0.3, max_profit_pct=20.0)
        self.calculator = StakeCalculator()
        self.converter = OddsConverter()
        self.tracker = ProfitTracker()
        self.notifier = NotificationService()
        self.book_rotation = BookRotationService()
        self.scheduler = SmartScheduler()
        self.latest_arbs: list[ArbOpportunityResponse] = []
        self.last_scan_time: Optional[str] = None
        self.events_scanned: int = 0
        self.bankroll: float = 1000.0
        self.scan_sports: list[str] = [
            "basketball_nba", "americanfootball_nfl", "baseball_mlb",
            "icehockey_nhl", "soccer_epl", "soccer_usa_mls",
        ]
        self.enabled_books: list[str] = [
            "fanduel", "draftkings", "betmgm", "caesars",
            "espnbet", "fanatics", "hardrockbet", "betrivers",
            "pointsbet", "bet365",
        ]
        self.auto_scan_task: Optional[asyncio.Task] = None
        self.auto_scan_interval: int = 120
        self.auto_scan_enabled: bool = False

    def initialize(self):
        load_env()
        primary = os.environ.get("ODDS_API_KEY", "")
        if primary:
            self.key_manager.add_key(primary)
        i = 2
        while True:
            key = os.environ.get(f"ODDS_API_KEY_{i}", "")
            if not key:
                break
            self.key_manager.add_key(key)
            i += 1
        logger.info(f"Loaded {self.key_manager.get_status()['total_keys']} API key(s)")

        # Notifications setup (email is free, pushover is optional)
        notify_email = os.environ.get("NOTIFY_EMAIL", "")
        notify_email_pw = os.environ.get("NOTIFY_EMAIL_PASSWORD", "")
        pushover_user = os.environ.get("PUSHOVER_USER_KEY", "")
        pushover_token = os.environ.get("PUSHOVER_APP_TOKEN", "")
        min_notify = float(os.environ.get("MIN_PROFIT_TO_NOTIFY", "25.0"))

        self.notifier = NotificationService(
            email_address=notify_email or None,
            email_password=notify_email_pw or None,
            pushover_user_key=pushover_user or None,
            pushover_app_token=pushover_token or None,
            min_profit_to_notify=min_notify,
        )

        if self.notifier.email_configured:
            logger.info(f"Email notifications enabled ({notify_email}, min: ${min_notify})")
        if self.notifier.pushover_configured:
            logger.info(f"Pushover notifications enabled (min: ${min_notify})")
        if not self.notifier.is_configured:
            logger.info("No notifications configured. Add NOTIFY_EMAIL + NOTIFY_EMAIL_PASSWORD to .env for free email alerts.")

        self._refresh_fetcher()

    def _refresh_fetcher(self):
        current_key = self.key_manager.get_current_key()
        if current_key:
            self.fetcher = OddsFetcher(
                api_key=current_key, regions="us",
                odds_format="decimal", bookmakers=self.enabled_books,
            )
        else:
            self.fetcher = None

    def rotate_key_if_needed(self):
        current = self.key_manager.get_current_key()
        if self.fetcher and current and self.fetcher.api_key != current:
            self._refresh_fetcher()

state = AppState()


# ─── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    state.initialize()

    # Set up scheduler callbacks
    async def scheduled_scan(sports: list[str]) -> list:
        """Callback for scheduler - runs a scan with specific sports."""
        state.rotate_key_if_needed()
        if not state.fetcher:
            logger.warning("Scheduled scan skipped: no API key")
            return []
        try:
            events = await state.fetcher.get_all_odds(sports)
            usage = state.fetcher.get_usage()
            if usage.get("remaining_requests") is not None:
                state.key_manager.report_usage(
                    state.fetcher.api_key, usage["remaining_requests"], usage["used_requests"],
                )
                state.rotate_key_if_needed()

            arbs = _run_scan_pipeline(events, state.bankroll)
            state.latest_arbs = arbs
            state.events_scanned = len(events)
            state.last_scan_time = datetime.now(timezone.utc).isoformat()
            return [a.model_dump() for a in arbs]
        except Exception as e:
            logger.error(f"Scheduled scan failed: {e}")
            return []

    async def scheduled_notify(arbs: list[dict], label: str):
        """Callback for scheduler - sends digest email."""
        if state.notifier.is_configured:
            state.notifier.send_digest(arbs, label)

    state.scheduler.set_callbacks(scheduled_scan, scheduled_notify)

    # Auto-start scheduler if email is configured (cloud mode)
    if state.notifier.email_configured:
        state.scheduler.start()
        logger.info("Smart scheduler auto-started (email notifications configured)")

    logger.info("Arb Finder backend started (Phase 5)")
    yield
    state.scheduler.stop()
    if state.auto_scan_task and not state.auto_scan_task.done():
        state.auto_scan_task.cancel()

app = FastAPI(title="Arb Finder", version="0.5.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _get_book_display(book_key: str) -> str:
    info = get_book_info(book_key)
    return info["display_name"] if info else book_key.title()

def _run_scan_pipeline(events: list[dict], bankroll: float) -> list[ArbOpportunityResponse]:
    all_arbs: list[ArbOpportunity] = []
    for event in events:
        all_arbs.extend(state.scanner.scan_event(event))

    best: dict[str, ArbOpportunity] = {}
    for arb in all_arbs:
        key = f"{arb.event_name}|{arb.book_a}|{arb.book_b}"
        if key not in best or arb.profit_percentage > best[key].profit_percentage:
            best[key] = arb

    results: list[ArbOpportunityResponse] = []
    for arb in sorted(best.values(), key=lambda a: a.profit_percentage, reverse=True):
        filled, breakdown = state.calculator.fill_arb_opportunity(arb, bankroll)

        commence_time = None
        for event in events:
            ename = f"{event.get('away_team', '')} @ {event.get('home_team', '')}"
            if ename == arb.event_name:
                commence_time = event.get("commence_time")
                break

        fee_a = get_book_fee(arb.book_a)
        fee_b = get_book_fee(arb.book_b)
        profit_after_fees = filled.guaranteed_profit
        if fee_a > 0:
            profit_after_fees -= filled.guaranteed_return * (fee_a / 100)
        if fee_b > 0:
            profit_after_fees -= filled.guaranteed_return * (fee_b / 100)

        results.append(ArbOpportunityResponse(
            event_name=filled.event_name, sport=filled.sport,
            commence_time=commence_time,
            outcome_a=filled.outcome_a, book_a=filled.book_a,
            book_a_display=_get_book_display(filled.book_a),
            odds_a_decimal=filled.odds_a_decimal, odds_a_american=filled.odds_a_american,
            stake_a=filled.stake_a,
            outcome_b=filled.outcome_b, book_b=filled.book_b,
            book_b_display=_get_book_display(filled.book_b),
            odds_b_decimal=filled.odds_b_decimal, odds_b_american=filled.odds_b_american,
            stake_b=filled.stake_b,
            outcome_c=filled.outcome_c, book_c=filled.book_c,
            book_c_display=_get_book_display(filled.book_c) if filled.book_c else None,
            odds_c_decimal=filled.odds_c_decimal,
            odds_c_american=filled.odds_c_american if filled.odds_c_decimal else None,
            stake_c=filled.stake_c,
            total_stake=filled.total_stake, guaranteed_return=filled.guaranteed_return,
            guaranteed_profit=filled.guaranteed_profit,
            guaranteed_profit_after_fees=round(profit_after_fees, 2),
            profit_percentage=filled.profit_percentage, arb_margin=filled.arb_margin,
            book_a_trusted=is_trusted(filled.book_a),
            book_b_trusted=is_trusted(filled.book_b),
        ))
    return results

async def _auto_scan_loop():
    while True:
        try:
            state.rotate_key_if_needed()
            if state.fetcher:
                events = await state.fetcher.get_all_odds(state.scan_sports)
                usage = state.fetcher.get_usage()
                if usage.get("remaining_requests") is not None:
                    state.key_manager.report_usage(
                        state.fetcher.api_key, usage["remaining_requests"], usage["used_requests"],
                    )
                    state.rotate_key_if_needed()

                state.latest_arbs = _run_scan_pipeline(events, state.bankroll)
                state.events_scanned = len(events)
                state.last_scan_time = datetime.now(timezone.utc).isoformat()

                if state.notifier.is_configured and state.latest_arbs:
                    arb_dicts = [a.model_dump() for a in state.latest_arbs]
                    sent = await state.notifier.notify_batch(arb_dicts)
                    if sent:
                        logger.info(f"Sent {sent} push notification(s)")
        except Exception as e:
            logger.error(f"Auto-scan error: {e}")
            if state.fetcher and ("401" in str(e) or "429" in str(e)):
                state.key_manager.report_error(state.fetcher.api_key)
                state.rotate_key_if_needed()
        await asyncio.sleep(state.auto_scan_interval)


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/health")
async def health_check():
    return {
        "status": "healthy", "version": "0.4.0",
        "api_keys": state.key_manager.get_status()["total_keys"],
        "total_api_requests_remaining": state.key_manager.get_total_remaining(),
        "notifications_configured": state.notifier.is_configured,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

@app.post("/api/calculate", response_model=CalcResponse)
async def manual_calculate(req: ManualCalcRequest):
    converter = state.converter
    try:
        dec_a = converter.normalize_to_decimal(req.odds_a, req.odds_format)
        dec_b = converter.normalize_to_decimal(req.odds_b, req.odds_format)
        dec_c = converter.normalize_to_decimal(req.odds_c, req.odds_format) if req.odds_c else None
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid odds: {e}")

    check = (state.scanner.check_three_way_arb(dec_a, dec_b, dec_c) if dec_c
             else state.scanner.check_two_way_arb(dec_a, dec_b))

    if not check["is_arb"]:
        return CalcResponse(
            is_arb=False, stakes={}, total_stake=req.bankroll,
            guaranteed_return=0, guaranteed_profit=0, profit_percentage=0,
            scenarios=[], combined_implied_probability=check["combined_implied_probability"],
            arb_margin=0,
        )

    try:
        if dec_c:
            breakdown = state.calculator.calculate_three_way(
                dec_a, dec_b, dec_c, req.bankroll,
                req.outcome_a_name, req.outcome_b_name, req.outcome_c_name,
                req.book_a, req.book_b, req.book_c, req.fee_pct,
            )
        else:
            breakdown = state.calculator.calculate_two_way(
                dec_a, dec_b, req.bankroll,
                req.outcome_a_name, req.outcome_b_name,
                req.book_a, req.book_b, req.fee_pct,
            )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    stakes_response = {
        name: StakeInfo(book=info["book"], stake=info["stake"],
            odds_decimal=info["odds_decimal"], odds_american=info["odds_american"],
            potential_return=info["potential_return"])
        for name, info in breakdown.stakes.items()
    }
    return CalcResponse(
        is_arb=True, stakes=stakes_response,
        total_stake=breakdown.total_stake, guaranteed_return=breakdown.guaranteed_return,
        guaranteed_profit=breakdown.guaranteed_profit,
        profit_percentage=breakdown.profit_percentage,
        profit_after_fees=breakdown.profit_after_fees,
        scenarios=breakdown.scenario_outcomes,
        combined_implied_probability=check["combined_implied_probability"],
        arb_margin=check["arb_margin"],
    )

@app.get("/api/scan", response_model=ScanResponse)
async def scan_for_arbs(
    sports: Optional[str] = Query(default=None),
    bankroll: Optional[float] = Query(default=None),
    min_profit: Optional[float] = Query(default=None),
):
    state.rotate_key_if_needed()
    if not state.fetcher:
        raise HTTPException(status_code=503, detail="No API keys configured.")

    scan_sports = sports.split(",") if sports else state.scan_sports
    scan_bankroll = bankroll or state.bankroll
    original_min = state.scanner.min_profit_pct
    if min_profit is not None:
        state.scanner.min_profit_pct = min_profit

    try:
        events = await state.fetcher.get_all_odds(scan_sports)
        usage = state.fetcher.get_usage()
        if usage.get("remaining_requests") is not None:
            state.key_manager.report_usage(
                state.fetcher.api_key, usage["remaining_requests"], usage["used_requests"],
            )
            state.rotate_key_if_needed()

        arbs = _run_scan_pipeline(events, scan_bankroll)
        state.latest_arbs = arbs
        state.events_scanned = len(events)
        state.last_scan_time = datetime.now(timezone.utc).isoformat()

        if state.notifier.is_configured and arbs:
            arb_dicts = [a.model_dump() for a in arbs]
            await state.notifier.notify_batch(arb_dicts)

        return ScanResponse(
            opportunities=arbs, total_found=len(arbs),
            events_scanned=len(events), sports_scanned=scan_sports,
            bankroll=scan_bankroll, scan_time=state.last_scan_time,
            api_usage=state.key_manager.get_status(),
        )
    except Exception as e:
        logger.error(f"Scan failed: {e}")
        if state.fetcher and ("401" in str(e) or "429" in str(e)):
            state.key_manager.report_error(state.fetcher.api_key)
            state.rotate_key_if_needed()
        raise HTTPException(status_code=500, detail=f"Scan failed: {str(e)}")
    finally:
        state.scanner.min_profit_pct = original_min

@app.get("/api/arbs", response_model=ScanResponse)
async def get_latest_arbs():
    return ScanResponse(
        opportunities=state.latest_arbs, total_found=len(state.latest_arbs),
        events_scanned=state.events_scanned, sports_scanned=state.scan_sports,
        bankroll=state.bankroll, scan_time=state.last_scan_time or "never",
        api_usage=state.key_manager.get_status(),
    )

# ─── Profit Tracker ──────────────────────────────────────────────────────────

@app.post("/api/bets")
async def track_bet(req: TrackBetRequest):
    bet = state.tracker.add_bet(req.model_dump())
    return {"status": "tracked", "bet": bet}

@app.get("/api/bets")
async def get_bets(
    status: Optional[str] = Query(default=None),
    sport: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    bets = state.tracker.get_all_bets(status=status, sport=sport, limit=limit, offset=offset)
    return {"bets": bets, "count": len(bets)}

@app.get("/api/bets/stats")
async def get_bet_stats():
    return state.tracker.get_stats()

@app.get("/api/bets/{bet_id}")
async def get_bet(bet_id: str):
    bet = state.tracker.get_bet(bet_id)
    if not bet:
        raise HTTPException(status_code=404, detail="Bet not found")
    return bet

@app.put("/api/bets/{bet_id}/resolve")
async def resolve_bet(bet_id: str, req: ResolveBetRequest):
    bet = state.tracker.resolve_bet(bet_id, req.winning_outcome, req.actual_profit, req.notes)
    if not bet:
        raise HTTPException(status_code=404, detail="Bet not found")
    return {"status": "resolved", "bet": bet}

@app.put("/api/bets/{bet_id}/cancel")
async def cancel_bet(bet_id: str, notes: Optional[str] = Query(default=None)):
    bet = state.tracker.cancel_bet(bet_id, notes)
    if not bet:
        raise HTTPException(status_code=404, detail="Bet not found")
    return {"status": "cancelled", "bet": bet}

@app.delete("/api/bets/{bet_id}")
async def delete_bet(bet_id: str):
    if not state.tracker.delete_bet(bet_id):
        raise HTTPException(status_code=404, detail="Bet not found")
    return {"status": "deleted"}

# ─── API Key Management ──────────────────────────────────────────────────────

@app.get("/api/keys")
async def get_api_keys():
    return state.key_manager.get_status()

@app.post("/api/keys")
async def add_api_key(req: AddKeyRequest):
    state.key_manager.add_key(req.api_key)
    state._refresh_fetcher()
    return state.key_manager.get_status()

@app.delete("/api/keys/{index}")
async def remove_api_key(index: int):
    state.key_manager.remove_key(index)
    state._refresh_fetcher()
    return state.key_manager.get_status()

@app.post("/api/keys/reset")
async def reset_api_keys():
    state.key_manager.reset_all()
    state._refresh_fetcher()
    return state.key_manager.get_status()

# ─── Sportsbook Info ─────────────────────────────────────────────────────────

@app.get("/api/sportsbooks")
async def get_sportsbooks():
    return {
        "books": {
            key: {
                "display_name": data["display_name"],
                "trusted": data["trusted"],
                "withdrawal_fee_pct": data["withdrawal_fee_pct"],
                "min_withdrawal": data["min_withdrawal"],
                "min_bet": data["min_bet"],
                "license_info": data["license_info"],
                "notes": data["notes"],
                "withdrawal_methods": data["withdrawal_methods"],
            }
            for key, data in SPORTSBOOK_DATA.items()
        }
    }

@app.get("/api/sportsbooks/{book_key}")
async def get_sportsbook_info(book_key: str):
    info = get_book_info(book_key)
    if not info:
        raise HTTPException(status_code=404, detail=f"Sportsbook '{book_key}' not found")
    return info

# ─── Notifications ────────────────────────────────────────────────────────────

@app.get("/api/notifications")
async def get_notification_config():
    return state.notifier.get_config()

@app.put("/api/notifications")
async def update_notification_config(req: NotificationConfigRequest):
    if req.min_profit_to_notify is not None:
        state.notifier.min_profit_to_notify = req.min_profit_to_notify
    if req.email_address:
        state.notifier.email_address = req.email_address
    if req.email_password:
        state.notifier.email_password = req.email_password
    if req.pushover_user_key:
        state.notifier.pushover_user_key = req.pushover_user_key
    if req.pushover_app_token:
        state.notifier.pushover_app_token = req.pushover_app_token
    return state.notifier.get_config()

@app.post("/api/notifications/test")
async def test_notification():
    if not state.notifier.is_configured:
        raise HTTPException(
            status_code=400,
            detail="No notification method configured. Add NOTIFY_EMAIL + NOTIFY_EMAIL_PASSWORD to .env for free email alerts."
        )
    test_arb = {
        "event_name": "Test Event", "outcome_a": "Team A", "book_a": "TestBook",
        "stake_a": 250, "outcome_b": "Team B", "book_b": "TestBook2", "stake_b": 250,
        "total_stake": 500, "guaranteed_return": 530,
        "guaranteed_profit": 999, "profit_percentage": 6.0,
    }
    orig = state.notifier.min_profit_to_notify
    state.notifier.min_profit_to_notify = 0
    sent = await state.notifier.notify_arb(test_arb)
    state.notifier.min_profit_to_notify = orig
    return {"sent": sent}

# ─── Auto-Scan + Settings ────────────────────────────────────────────────────

@app.post("/api/auto-scan")
async def configure_auto_scan(config: AutoScanConfig):
    if config.enabled and not state.fetcher:
        raise HTTPException(status_code=503, detail="No API keys configured.")
    state.auto_scan_interval = config.interval_seconds
    if config.bankroll:
        state.bankroll = config.bankroll
    if config.sports:
        state.scan_sports = config.sports
    if config.enabled and not state.auto_scan_enabled:
        state.auto_scan_enabled = True
        state.auto_scan_task = asyncio.create_task(_auto_scan_loop())
        return {"status": "started", "interval_seconds": config.interval_seconds}
    elif not config.enabled and state.auto_scan_enabled:
        state.auto_scan_enabled = False
        if state.auto_scan_task:
            state.auto_scan_task.cancel()
        return {"status": "stopped"}
    elif config.enabled:
        return {"status": "updated", "interval_seconds": config.interval_seconds}
    return {"status": "already_stopped"}

@app.get("/api/auto-scan")
async def get_auto_scan_status():
    return {
        "enabled": state.auto_scan_enabled,
        "interval_seconds": state.auto_scan_interval,
        "sports": state.scan_sports, "bankroll": state.bankroll,
        "last_scan_time": state.last_scan_time,
        "cached_arbs": len(state.latest_arbs),
    }

@app.get("/api/settings")
async def get_settings():
    return {
        "bankroll": state.bankroll, "scan_sports": state.scan_sports,
        "enabled_books": state.enabled_books,
        "min_profit_pct": state.scanner.min_profit_pct,
        "max_profit_pct": state.scanner.max_profit_pct,
        "auto_scan_interval": state.auto_scan_interval,
        "api_keys": state.key_manager.get_status(),
        "notifications": state.notifier.get_config(),
    }

@app.put("/api/settings")
async def update_settings(settings: SettingsUpdate):
    updated = {}
    if settings.bankroll is not None:
        state.bankroll = settings.bankroll; updated["bankroll"] = settings.bankroll
    if settings.scan_sports is not None:
        state.scan_sports = settings.scan_sports; updated["scan_sports"] = settings.scan_sports
    if settings.enabled_books is not None:
        state.enabled_books = settings.enabled_books
        if state.fetcher: state.fetcher.bookmakers = settings.enabled_books
        updated["enabled_books"] = settings.enabled_books
    if settings.min_profit_pct is not None:
        state.scanner.min_profit_pct = settings.min_profit_pct; updated["min_profit_pct"] = settings.min_profit_pct
    if settings.max_profit_pct is not None:
        state.scanner.max_profit_pct = settings.max_profit_pct; updated["max_profit_pct"] = settings.max_profit_pct
    if settings.auto_scan_interval is not None:
        state.auto_scan_interval = settings.auto_scan_interval; updated["auto_scan_interval"] = settings.auto_scan_interval
    return {"status": "updated", "changes": updated}

@app.get("/api/sports")
async def get_available_sports():
    if not state.fetcher:
        raise HTTPException(status_code=503, detail="No API keys configured.")
    try:
        sports = await state.fetcher.get_sports()
        return {"sports": [s for s in sports if s.get("active")], "configured": state.scan_sports}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/convert-odds")
async def convert_odds(odds: float = Query(), from_format: str = Query(default="american")):
    try:
        d = state.converter.normalize_to_decimal(odds, from_format)
        return {
            "decimal": round(d, 4),
            "american": state.converter.decimal_to_american(d),
            "implied_probability_pct": round(state.converter.decimal_to_implied_probability(d) * 100, 2),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ─── Budget Optimizer ─────────────────────────────────────────────────────────

class BudgetRequest(BaseModel):
    budget: float = Field(ge=10.0, description="Total budget to allocate across arbs")
    max_per_arb_pct: float = Field(default=0, ge=0, le=100.0)
    min_per_arb: float = Field(default=0, ge=0)
    max_arbs: int = Field(default=0, ge=0, le=50)

@app.post("/api/budget")
async def optimize_budget_endpoint(req: BudgetRequest):
    """
    Allocate a total budget across multiple arb opportunities to maximize profit.
    Uses book rotation to spread bets and avoid detection.
    System automatically determines the best split - no manual config needed.
    """
    if not state.latest_arbs:
        raise HTTPException(status_code=400, detail="No arbs available. Run a scan first.")

    state.book_rotation.load_from_tracker(state.tracker)

    rotation_scores = {}
    for arb in state.latest_arbs:
        for book_key in [arb.book_a, arb.book_b]:
            if book_key not in rotation_scores:
                risk = get_arb_risk(book_key)
                rotation_scores[book_key] = state.book_rotation.get_book_usage_score(book_key, risk)

    arb_dicts = [a.model_dump() for a in state.latest_arbs]

    # Smart defaults: system decides based on budget and available arbs
    num_arbs = len(arb_dicts)
    auto_max_arbs = req.max_arbs if req.max_arbs > 0 else min(num_arbs, max(3, int(req.budget / 100)))
    auto_max_pct = req.max_per_arb_pct if req.max_per_arb_pct > 0 else min(60, max(25, 100 / max(auto_max_arbs, 1)))
    auto_min_per = req.min_per_arb if req.min_per_arb > 0 else max(10, req.budget * 0.03)

    # Load book rotation data from history
    state.book_rotation.load_from_tracker(state.tracker)

    # Build rotation scores for each book
    rotation_scores = {}
    for arb in state.latest_arbs:
        for book_key in [arb.book_a, arb.book_b]:
            if book_key not in rotation_scores:
                risk = get_arb_risk(book_key)
                rotation_scores[book_key] = state.book_rotation.get_book_usage_score(book_key, risk)

    # Convert arbs to dicts for optimizer
    arb_dicts = [a.model_dump() for a in state.latest_arbs]

    # Build fee lookup from sportsbook data
    fee_lookup = {}
    for arb in state.latest_arbs:
        for book_key in [arb.book_a, arb.book_b]:
            if book_key not in fee_lookup:
                fee_lookup[book_key] = get_book_fee(book_key)

    # Run optimizer
    plan = optimize_budget(
        budget=req.budget,
        arbs=arb_dicts,
        book_rotation_scores=rotation_scores,
        book_fee_lookup=fee_lookup,
        max_per_arb_pct=auto_max_pct,
        min_per_arb=auto_min_per,
        max_arbs=auto_max_arbs,
    )

    # Format response
    allocs = []
    for a in plan.allocations:
        book_a_key = a.arb.get("book_a", "")
        book_b_key = a.arb.get("book_b", "")
        book_a_info = get_book_info(book_a_key) or {}
        book_b_info = get_book_info(book_b_key) or {}

        allocs.append({
            "event_name": a.arb.get("event_name", ""),
            "sport": a.arb.get("sport", ""),
            "commence_time": a.arb.get("commence_time"),
            "outcome_a": a.arb.get("outcome_a", ""),
            "book_a": book_a_key,
            "book_a_display": book_a_info.get("display_name", book_a_key),
            "book_a_min_bet": book_a_info.get("min_bet", 0),
            "book_a_arb_risk": book_a_info.get("arb_risk", "unknown"),
            "stake_a": a.stake_a,
            "odds_a_american": a.arb.get("odds_a_american", 0),
            "outcome_b": a.arb.get("outcome_b", ""),
            "book_b": book_b_key,
            "book_b_display": book_b_info.get("display_name", book_b_key),
            "book_b_min_bet": book_b_info.get("min_bet", 0),
            "book_b_arb_risk": book_b_info.get("arb_risk", "unknown"),
            "stake_b": a.stake_b,
            "odds_b_american": a.arb.get("odds_b_american", 0),
            "outcome_c": a.arb.get("outcome_c"),
            "book_c": a.arb.get("book_c"),
            "stake_c": a.stake_c,
            "allocated_amount": a.allocated_amount,
            "guaranteed_profit": a.guaranteed_profit,
            "profit_pct": a.profit_pct,
            "rotation_score": a.rotation_score,
        })

    return {
        "total_budget": plan.total_budget,
        "total_allocated": plan.total_allocated,
        "total_remaining": plan.total_remaining,
        "total_guaranteed_profit": plan.total_guaranteed_profit,
        "overall_roi": plan.overall_roi,
        "allocations": allocs,
        "books_used": plan.books_used,
        "warnings": plan.warnings,
    }


# ─── Book Rotation Info ───────────────────────────────────────────────────────

@app.get("/api/book-rotation")
async def get_book_rotation():
    """Get book usage summary and rotation scores."""
    state.book_rotation.load_from_tracker(state.tracker)
    usage = state.book_rotation.get_usage_summary()

    scores = {}
    for book_key in SPORTSBOOK_DATA:
        risk = get_arb_risk(book_key)
        scores[book_key] = {
            "display_name": SPORTSBOOK_DATA[book_key]["display_name"],
            "arb_risk": risk,
            "usage_penalty": state.book_rotation.get_book_usage_score(book_key, risk),
            "bet_count": usage.get(book_key, {}).get("bet_count", 0),
            "last_used": usage.get(book_key, {}).get("last_used"),
        }

    return {"books": scores}


# ─── Smart Scheduler ──────────────────────────────────────────────────────────

@app.get("/api/scheduler")
async def get_scheduler_status():
    """Get the smart scheduler status and next scan time."""
    return state.scheduler.get_status()

@app.post("/api/scheduler/start")
async def start_scheduler():
    """Start the smart scheduler."""
    if not state.fetcher:
        raise HTTPException(status_code=503, detail="No API keys configured.")
    state.scheduler.start()
    return state.scheduler.get_status()

@app.post("/api/scheduler/stop")
async def stop_scheduler():
    """Stop the smart scheduler."""
    state.scheduler.stop()
    return state.scheduler.get_status()