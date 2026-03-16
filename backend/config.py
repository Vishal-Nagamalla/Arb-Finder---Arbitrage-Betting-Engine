"""
Config loader - reads from .env file and environment variables.
"""

import os
from pathlib import Path


def load_env():
    """Load variables from .env file into os.environ."""
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip())


def get_api_key() -> str:
    """Get the Odds API key from environment."""
    load_env()
    key = os.environ.get("ODDS_API_KEY", "")
    if not key:
        raise ValueError(
            "ODDS_API_KEY not found. Create a .env file in arb-finder/ root "
            "with: ODDS_API_KEY=your_key_here"
        )
    return key
