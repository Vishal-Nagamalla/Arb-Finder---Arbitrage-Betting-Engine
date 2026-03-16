# Arb Finder - Sports Betting Arbitrage Engine

Personal tool for detecting guaranteed-profit arbitrage opportunities across US-licensed sportsbooks. Scans odds in real-time, calculates exact stake splits, and emails you when profitable opportunities appear.

## How It Works

Sportsbooks set their own odds independently. When two books disagree enough on a game, you can bet both sides and guarantee profit regardless of outcome. This tool finds those windows automatically.

**Example:** BetMGM has Lakers at +155, DraftKings has Celtics at -143. Bet $200 on Lakers (BetMGM) and $300 on Celtics (DraftKings). No matter who wins, you get $510 back on $500 invested = $10 guaranteed profit.

## Features

- **Live Scanner** - Scans 10+ sportsbooks across NBA, NFL, MLB, NHL, MLS, EPL, MMA, NCAAB
- **Budget Optimizer** - Input your total budget, system determines optimal split across multiple arbs with book rotation for anti-detection
- **Manual Calculator** - Input odds from any two books, get exact stake amounts and profit breakdown
- **Smart Scheduler** - Auto-scans at optimal times (11am, 12:30pm, 5:30pm, 6:30pm, 8pm ET) and emails you when arbs are found
- **Bet History & P/L Tracking** - Track every bet, resolve outcomes, view cumulative profit by sport and book
- **Book Rotation** - Spreads bets across different sportsbooks to avoid detection/limiting
- **API Key Rotation** - Multiple Odds API keys for extended monthly quota
- **Email Notifications** - Free Gmail-based alerts with styled HTML digest emails
- **Mobile Responsive** - Access from your phone when you get an alert
- **Password Protected** - Secure your deployed instance

## Trusted Sportsbooks (US-Licensed Only)

FanDuel, DraftKings, BetMGM, Caesars, ESPN BET, Fanatics, Hard Rock Bet, BetRivers, PointsBet, bet365, Unibet

All verified US state-licensed with $0 withdrawal fees. No offshore books.

## Project Structure

```
arb-finder/
  .env                          # Your secrets (never commit this)
  Dockerfile                    # For cloud deployment
  railway.toml                  # Railway config (optional)
  backend/
    app.py                      # FastAPI server with all endpoints
    config.py                   # Environment loader
    core/
      odds_converter.py         # American/Decimal/Probability conversion
      arbitrage.py              # Arb detection engine
      calculator.py             # Stake split calculator
      budget_optimizer.py       # Multi-arb budget allocation
    services/
      odds_fetcher.py           # The Odds API integration
      key_rotation.py           # Multi-key API management
      profit_tracker.py         # SQLite bet history & P/L
      notifications.py          # Email (Gmail) + Pushover alerts
      sportsbook_fees.py        # Book fee/trust database
      book_rotation.py          # Anti-detection book spreading
      scheduler.py              # Smart auto-scan scheduler
    models/
      schemas.py                # Data models
  frontend/
    app/
      page.tsx                  # Live Scanner dashboard
      budget/page.tsx           # Budget optimizer
      calculator/page.tsx       # Manual calculator
      history/page.tsx          # Bet history & P/L
      settings/page.tsx         # Configuration
    components/
      Sidebar.tsx               # Navigation (desktop sidebar + mobile bottom nav)
    lib/
      api.ts                    # API client with auth
      utils.ts                  # Formatting helpers
```

## Quick Start (Local)

### 1. Get an API Key

Sign up at https://the-odds-api.com/ (free, 500 requests/month)

### 2. Set Up Environment

```bash
cd arb-finder

# Create .env file
cp .env.example .env
# Edit .env and add your API key + email credentials
```

Your `.env` file:
```
ODDS_API_KEY=your_key_here
NOTIFY_EMAIL=your.email@gmail.com
NOTIFY_EMAIL_PASSWORD=xxxx xxxx xxxx xxxx
MIN_PROFIT_TO_NOTIFY=25.0
APP_PASSWORD=pick_any_secret_password
```

### 3. Start Backend

```bash
pip install httpx pydantic fastapi "uvicorn[standard]"
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

### Backend on Render (Free)

1. Push code to a private GitHub repo
2. Go to https://render.com, connect GitHub
3. New > Web Service > select your repo
4. Environment: Docker
5. Add environment variables:
   - `ODDS_API_KEY` - your API key
   - `NOTIFY_EMAIL` - your Gmail address
   - `NOTIFY_EMAIL_PASSWORD` - Gmail app password
   - `MIN_PROFIT_TO_NOTIFY` - minimum profit to alert (e.g., 25.0)
   - `APP_PASSWORD` - any secret password to protect your API
6. Select Free tier, deploy

### Frontend on Vercel (Free)

1. Go to https://vercel.com, connect GitHub
2. Import your repo, set Root Directory to `frontend`
3. Add environment variables:
   - `NEXT_PUBLIC_API_URL` - your Render URL + /api (e.g., https://arb-finder-xyz.onrender.com/api)
   - `BACKEND_URL` - your Render URL (e.g., https://arb-finder-xyz.onrender.com)
   - `NEXT_PUBLIC_APP_PASSWORD` - same password you set on Render
4. Deploy

### Access from Phone

Bookmark your Vercel URL on your iPhone. In Safari, tap Share > Add to Home Screen for an app-like experience.

## Gmail App Password Setup

1. Go to https://myaccount.google.com/security
2. Enable 2-Factor Authentication
3. Go to https://myaccount.google.com/apppasswords
4. Create password named "Arb Finder"
5. Copy the 16-character code into your .env

## API Usage Optimization

- Smart scheduler uses ~30 API calls/day (5 scans x 6 sports)
- ~900 calls/month fits within 2 free API keys
- Add multiple keys: `ODDS_API_KEY`, `ODDS_API_KEY_2`, `ODDS_API_KEY_3`
- System auto-rotates when one key runs low

## The Math

For a 2-outcome event with decimal odds d1 and d2:

- Arb exists when: `(1/d1) + (1/d2) < 1.0`
- Stake on outcome 1: `bankroll * (1/d1) / ((1/d1) + (1/d2))`
- Stake on outcome 2: `bankroll * (1/d2) / ((1/d1) + (1/d2))`
- Guaranteed return: `bankroll / ((1/d1) + (1/d2))`
- Profit: `return - bankroll`

## Best Times to Find Arbs

- **11am-1pm ET** - Lines posted for evening games
- **5-7pm ET** - Pre-game rush, lines moving fast
- **NFL Sundays 12-1pm ET** - Massive multi-game slate
- **Right before tip-off/puck drop** - Last-minute line movements

Built by Vishal Nagamalla | https://vishal-nagamalla.github.io/