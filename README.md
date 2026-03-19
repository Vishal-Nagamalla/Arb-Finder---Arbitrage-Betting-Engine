# Arb Finder - Real-Time Sports Arbitrage Detection Engine

Full-stack system that monitors real-time odds across 11 US-licensed sportsbooks, detects guaranteed-profit arbitrage opportunities across moneyline, spread, and totals markets, calculates optimal stake allocations, and delivers push notifications to your phone, all running autonomously on cloud infrastructure.

## How Arbitrage Works

Sportsbooks set odds independently. When two books disagree enough on a game, you can bet both sides and lock in a guaranteed profit regardless of outcome.

**Example:** BetMGM has Lakers at +155, DraftKings has Celtics at -143.
- Bet $200 on Lakers (BetMGM), $300 on Celtics (DraftKings)
- Lakers win: BetMGM pays $510. Profit: $10.
- Celtics win: DraftKings pays $510. Profit: $10.
- Guaranteed $10 profit on $500 invested, no matter the outcome.

## Architecture

```
                        cron-job.org
                        (keep-alive ping every 14min)
                              |
                              v
Phone (ntfy)         Vercel (Next.js PWA)          Render (FastAPI)          The Odds API
    |                      |                              |                       |
    | <-- push notifs --   | <---- REST API ---->         | <--- odds data -----> |
    |                      |                              |     (h2h, spreads,    |
    |                 [React UI]                    [FastAPI Server]    totals)   |
    |                 - Scanner                     - Smart Scheduler (9/day)     |
    |                 - Calculator                  - Arb Scanner (3 markets)     |
    |                 - Budget Optimizer            - Stake Calculator            |
    |                 - Bet History                 - Budget Optimizer            |
    |                 - Settings (persistent)       - Key Rotation (6 keys)      |
    |                                               - Book Rotation              |
    |                                               - Notification Service       |
    |                                                     |
    |                                               [Neon Postgres]
    |                                               - Bet history
    |                                               - Persistent settings
```

## Tech Stack

**Backend:** Python, FastAPI, Uvicorn, httpx, Pydantic
**Frontend:** Next.js 14, React, TypeScript, Tailwind CSS
**Database:** Neon Postgres (cloud), SQLite (local dev)
**Deployment:** Render (backend), Vercel (frontend PWA)
**Notifications:** ntfy.sh (free push notifications)
**Data Source:** The Odds API (real-time sportsbook odds)
**Auth:** Bearer token middleware

## Key Engineering Features

### Multi-Key API Rotation
Manages a pool of API keys with automatic failover. Tracks remaining credits per key, detects dead keys via HTTP status codes, and switches to the next healthy key mid-scan. Monthly auto-reset when the API billing cycle refreshes.

### Three-Market Arb Detection
Scans moneyline (h2h), point spreads, and totals (over/under) markets simultaneously. For each game, compares every cross-book pairing and identifies where `(1/odds_A) + (1/odds_B) < 1.0`. Filters started games, validates odds bounds, and deduplicates overlapping opportunities.

### Smart Scheduler
Nine daily scans at optimal times (11am, 12:30pm, 5-8pm ET every 30min). Each scan selects relevant sports based on time of day to conserve API credits. Always-on via external health check pings. Sends push notifications on every scan (arbs found or status update).

### Budget Optimizer with Book Rotation
Given a total budget and multiple arb opportunities, determines optimal allocation using weighted scoring. Factors in ROI, sportsbook detection risk ratings, and historical bet frequency per book. Prevents account limiting by spreading activity across low-risk books.

### Progressive Web App
Installable on iPhone via Safari "Add to Home Screen". Full-screen standalone experience with no browser chrome. Bottom navigation on mobile, sidebar on desktop. Scan results persist in React context across page navigation.

### Persistent Settings
All user configuration (bankroll, sports, sportsbooks, intervals) saved to Postgres via the settings API. Survives backend redeploys. Loads on boot, saves on every settings change.

## Supported Markets

| Market | Description | Arb Viable |
|--------|-------------|:----------:|
| Moneyline (h2h) | Who wins the game | Yes |
| Point Spread | Margin of victory | Yes |
| Totals (O/U) | Combined score over/under | Yes |
| Props | Player/event specifics | Requires paid API |
| Futures | Season-long outcomes | No (can't lock both sides) |
| Parlays | Multi-bet combos | No (not guaranteed) |

## Trusted Sportsbooks

All US state-licensed, $0 withdrawal fees, with arb detection risk ratings:

| Book | Risk | Notes |
|------|:----:|-------|
| ESPN BET | Low | Safest for frequent arb betting |
| Fanatics | Low | Fastest payouts (24-48 hrs) |
| Hard Rock Bet | Low | Competitive odds, expanding |
| BetRivers | Low | Low minimums |
| PointsBet | Low | Transitioning to Fanatics |
| FanDuel | Medium | Largest US book (~38% share) |
| BetMGM | Medium | Higher min bet ($0.50) |
| Caesars | Medium | Strong market coverage |
| Unibet | Medium | European operator |
| DraftKings | High | Active arb detection |
| bet365 | High | Highest limits but monitors closely |

## The Math

For 2-way arb with decimal odds d1, d2:

```
Arb exists when:     (1/d1) + (1/d2) < 1.0
Stake on outcome 1:  bankroll * (1/d1) / ((1/d1) + (1/d2))
Stake on outcome 2:  bankroll * (1/d2) / ((1/d1) + (1/d2))
Guaranteed return:   bankroll / ((1/d1) + (1/d2))
Profit:              return - bankroll
```

## API Budget

Each Odds API call with `h2h,spreads,totals` costs 3 credits. Free tier = 500 credits/key/month.

| Sports | Scans/Day | Credits/Day | Credits/Month | Keys Needed |
|--------|-----------|-------------|---------------|:-----------:|
| 1 (NBA only) | 9 | 27 | 810 | 2 |
| 3 (NBA+NHL+MLB) | 9 | 81 | 2,430 | 5 |
| 6 (all major) | 9 | 162 | 4,860 | 10 |

## Realistic Expectations

- **Arb frequency:** 0-8 per day depending on sports activity
- **Profit margins:** 0.3-4% per arb
- **Window duration:** 2-30 minutes before odds converge
- **Best times:** 5-8pm ET (pre-game line movement)
- **Best days:** NFL Sundays, multi-game NBA/NHL nights
- **Risk:** Sportsbook account limiting (book rotation mitigates)