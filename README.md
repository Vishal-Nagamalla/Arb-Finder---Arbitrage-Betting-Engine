# Arb Finder - Arbitrage Betting Engine

Personal tool for detecting and calculating sports betting arbitrage opportunities across multiple sportsbooks.

## Project Structure

```
arb-finder/
  backend/
    core/
      odds_converter.py   # Convert between American, Decimal, Implied Probability
      arbitrage.py         # Scan odds data and detect arb opportunities
      calculator.py        # Calculate exact stake splits for guaranteed profit
    services/
      odds_fetcher.py      # The Odds API integration + mock data for testing
    models/
      schemas.py           # Data models and configuration
    tests/                 # Test suite (expanding)
    demo.py                # Full pipeline demo - run this to see it all work
    requirements.txt       # Python dependencies
```

## Quick Start

```bash
# Run the demo (no API key needed, uses mock data)
cd arb-finder
python -m backend.demo

# Install deps for real API usage
pip install httpx pydantic fastapi uvicorn
```

## How It Works

1. **Odds Fetcher** pulls real-time odds from The Odds API across 10+ sportsbooks
2. **Arbitrage Scanner** checks every cross-book combination for arb opportunities
3. **Stake Calculator** computes exact dollar amounts per bet to guarantee profit

### The Math

For a 2-outcome event, an arb exists when:
  `(1/odds_A) + (1/odds_B) < 1.0`

The guaranteed profit percentage is:
  `profit% = (1 - combined_implied_probability) / combined_implied_probability * 100`

## API Key Setup

1. Get a free key at https://the-odds-api.com/
2. Set as environment variable: `export ODDS_API_KEY=your_key_here`

## Phases

- [x] Phase 1: Core math engine + API integration
- [ ] Phase 2: FastAPI backend with scheduled polling
- [ ] Phase 3: Next.js dashboard UI
- [ ] Phase 4: Notifications + profit tracking
- [ ] Phase 5: Cloud deployment
