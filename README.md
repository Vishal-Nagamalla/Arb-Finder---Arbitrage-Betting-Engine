# Arb Finder - Sports Betting Arbitrage Engine

Personal tool that detects guaranteed-profit arbitrage opportunities across US-licensed sportsbooks, calculates exact bet amounts, and sends push notifications to your phone when opportunities appear.

## How Arbitrage Works

Sportsbooks set odds independently. When two books disagree enough, you can bet both sides and guarantee profit no matter who wins.

**Example:** BetMGM has Lakers at +155, DraftKings has Celtics at -143.
- Bet $200 on Lakers (BetMGM)
- Bet $300 on Celtics (DraftKings)
- If Lakers win: BetMGM pays $510. Profit: $10.
- If Celtics win: DraftKings pays $510. Profit: $10.
- Either way, you invested $500 and get back $510. Guaranteed.

## What This System Does

1. **Scans** 10+ sportsbooks across NBA, NFL, MLB, NHL, MLS, EPL, MMA, NCAAB
2. **Detects** odds discrepancies that create arbitrage windows
3. **Calculates** exact dollar amounts to bet on each side
4. **Notifies** you via push notification on your phone
5. **Optimizes** how to spread your budget across multiple arbs
6. **Rotates** which sportsbooks you use to avoid detection
7. **Tracks** your bet history and cumulative profit in a persistent database
8. **Runs 24/7** on the cloud, scanning automatically at optimal times

## Features

- **Live Scanner** - One-click scan across all sportsbooks with retry logic
- **Budget Optimizer** - Input total budget, system determines optimal allocation across arbs with book rotation
- **Manual Calculator** - Input odds from any two books, get full arb breakdown
- **Smart Scheduler** - Auto-scans at 11am, 12:30pm, 5:30pm, 6:30pm, 8pm ET daily
- **Push Notifications** - Free via ntfy.sh app on iPhone/Android
- **Bet History** - Persistent Neon Postgres storage, tracks P/L by sport and book
- **Book Rotation** - Spreads bets across sportsbooks to avoid account limits
- **API Key Rotation** - Multiple Odds API keys for extended monthly quota
- **Mobile App** - PWA installable on iPhone home screen
- **Password Protected** - Secure API with bearer token auth
- **Started Game Filter** - Automatically removes games already in progress
- **Scan Lock** - Prevents wasted API calls from rapid clicking

## Trusted Sportsbooks (US-Licensed Only)

FanDuel, DraftKings, BetMGM, Caesars, ESPN BET, Fanatics, Hard Rock Bet, BetRivers, PointsBet, bet365, Unibet

All verified US state-licensed. All have $0 withdrawal fees for standard methods (PayPal, Venmo, bank transfer). No offshore books.

Each book has an arb detection risk rating:
- **Low Risk** (safe to use frequently): ESPN BET, Fanatics, Hard Rock, BetRivers, PointsBet
- **Medium Risk** (spread usage out): FanDuel, BetMGM, Caesars, Unibet
- **High Risk** (use sparingly): DraftKings, bet365

## The Math

For a 2-outcome event with decimal odds d1 and d2:

- Arb exists when: `(1/d1) + (1/d2) < 1.0`
- Stake on outcome 1: `bankroll * (1/d1) / ((1/d1) + (1/d2))`
- Stake on outcome 2: `bankroll * (1/d2) / ((1/d1) + (1/d2))`
- Guaranteed return: `bankroll / ((1/d1) + (1/d2))`
- Profit: `return - bankroll`

## Project Structure

```
arb-finder/
  .env                              # Secrets (never commit)
  Dockerfile                        # Cloud deployment
  backend/
    app.py                          # FastAPI server, all endpoints, auth middleware
    config.py                       # Environment loader
    core/
      odds_converter.py             # American/Decimal/Probability conversion
      arbitrage.py                  # Arb detection engine (2-way and 3-way)
      calculator.py                 # Exact stake split calculator
      budget_optimizer.py           # Multi-arb budget allocation with rotation
    services/
      odds_fetcher.py               # The Odds API integration with retry logic
      key_rotation.py               # Multi-key API management
      profit_tracker.py             # Neon Postgres / SQLite bet history
      notifications.py              # ntfy.sh push + Resend email + Gmail SMTP
      sportsbook_fees.py            # Book fee/trust/risk database
      book_rotation.py              # Anti-detection sportsbook spreading
      scheduler.py                  # Smart auto-scan at optimal times
    models/
      schemas.py                    # Data models
  frontend/
    public/
      manifest.json                 # PWA manifest
      icon-192.png                  # App icon
      icon-512.png                  # App icon
      apple-touch-icon.png          # iOS icon
    app/
      layout.tsx                    # Root layout with PWA meta tags
      page.tsx                      # Live Scanner dashboard
      budget/page.tsx               # Budget optimizer
      calculator/page.tsx           # Manual calculator
      history/page.tsx              # Bet history and P/L tracking
      settings/page.tsx             # Configuration
    components/
      Sidebar.tsx                   # Desktop sidebar + mobile bottom nav
    lib/
      api.ts                        # API client with auth headers
      utils.ts                      # Formatting and time helpers
```

## Quick Start (Local Development)

### 1. Get an API Key

Sign up at https://the-odds-api.com/ (free, 500 requests/month)

### 2. Set Up Environment

```bash
cd arb-finder
cp .env.example .env
# Edit .env with your API key
```

Minimum `.env` for local dev:
```
ODDS_API_KEY=your_key_here
```

### 3. Start Backend

```bash
pip install httpx pydantic fastapi "uvicorn[standard]" psycopg2-binary
uvicorn backend.app:app --reload --port 8000
```

### 4. Start Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000

## Cloud Deployment (Runs 24/7)

### Backend: Render (Free)

1. Push code to a private GitHub repo
2. Go to https://render.com, sign up, connect GitHub
3. New > Web Service > select your repo
4. Environment: Docker
5. Add environment variables:
   - `ODDS_API_KEY` - your Odds API key
   - `DATABASE_URL` - your Neon Postgres connection string
   - `NTFY_TOPIC` - your ntfy.sh topic for push notifications
   - `DASHBOARD_URL` - your Vercel URL
   - `MIN_PROFIT_TO_NOTIFY` - set to 0 for all arbs
   - `APP_PASSWORD` - secret password to protect API
6. Select Free tier, deploy

### Frontend: Vercel (Free)

1. Go to https://vercel.com, sign up, connect GitHub
2. Import repo, set Root Directory to `frontend`
3. Add environment variables:
   - `NEXT_PUBLIC_API_URL` - Render URL + /api
   - `BACKEND_URL` - Render URL
   - `NEXT_PUBLIC_APP_PASSWORD` - same password as Render
4. Deploy

### Database: Neon Postgres (Free, via Vercel)

1. In Vercel, go to Storage tab > Create Database > Neon Postgres
2. Copy the connection string from the database dashboard
3. Add it as `DATABASE_URL` in Render's environment variables
4. Redeploy Render

### Push Notifications: ntfy.sh (Free)

1. Download "ntfy" app on iPhone from App Store
2. Subscribe to a secret topic name (e.g., `arb-finder-vishal-x9k2`)
3. Add `NTFY_TOPIC=arb-finder-vishal-x9k2` to Render
4. Redeploy

### Install as iPhone App

1. Open your Vercel URL in **Safari** on iPhone
2. Tap Share > "Add to Home Screen"
3. Choose "Open as Web App"

## How the Scheduler Works

The backend runs 5 scans per day at optimal times (all ET):
- **11:00 AM** - Morning lines posted for evening games
- **12:30 PM** - Mid-day line movement check
- **5:30 PM** - Pre-game rush, best arb windows
- **6:30 PM** - Right before tip-off/puck drop
- **8:00 PM** - Late games and west coast lines

Each scan checks relevant sports for that time slot to conserve API calls. Total: ~30 API calls/day, ~900/month (fits in 2 free keys).

When arbs are found, you get a push notification with exact bet instructions and a button to open your dashboard.

## API Usage

- 5 scans/day x 6 sports = ~30 calls/day, ~900/month
- Each free Odds API key = 500 requests/month
- 2 keys = 1,000/month (enough with margin)
- Add keys: `ODDS_API_KEY`, `ODDS_API_KEY_2`, `ODDS_API_KEY_3`
- System auto-rotates when one key runs low
- Scan lock prevents wasted calls from double-clicking
- Retry logic (3 attempts) prevents lost data from timeouts

## When to Find Arbs

- **11am-1pm ET** - Lines first posted for evening games
- **5-7pm ET** - Pre-game rush, lines moving fast
- **NFL Sundays 12-1pm ET** - Massive multi-game slate
- **Right before tip-off** - Last-minute line movements

Arbs are rare and short-lived (minutes to hours). Odds for games are only available 12-48 hours before start time.

## Security

- `APP_PASSWORD` protects all API endpoints
- API keys and database credentials only exist on Render
- Health check is the only public endpoint
- All sportsbook data stays on your private infrastructure

Built by Vishal Nagamalla | https://vishal-nagamalla.github.io/