"""
API Key Rotation Manager
Manages multiple Odds API keys and rotates between them
to maximize monthly request quotas.

Each free account gives 500 requests/month.
5 keys = 2,500 requests/month, etc.
"""

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class KeyRotationManager:
    """Rotates through multiple API keys to maximize request quotas."""

    def __init__(self, api_keys: list[str] | None = None):
        self.keys: list[dict] = []
        if api_keys:
            for key in api_keys:
                self.add_key(key)
        self._current_index = 0

    def add_key(self, api_key: str):
        """Add a new API key to the rotation pool."""
        if not api_key or not api_key.strip():
            return

        api_key = api_key.strip()

        # Don't add duplicates
        for k in self.keys:
            if k["key"] == api_key:
                logger.warning("Duplicate API key, skipping")
                return

        self.keys.append({
            "key": api_key,
            "remaining": None,  # Unknown until first use
            "used": None,
            "last_used": None,
            "exhausted": False,
        })
        logger.info(f"Added API key (total: {len(self.keys)} keys)")

    def remove_key(self, index: int):
        """Remove a key by index."""
        if 0 <= index < len(self.keys):
            self.keys.pop(index)
            if self._current_index >= len(self.keys):
                self._current_index = 0

    def get_current_key(self) -> str | None:
        """Get the current active API key. Sticks with current until it's low or exhausted."""
        if not self.keys:
            return None

        # If current key is still good, keep using it
        current = self.keys[self._current_index]
        if not current["exhausted"]:
            return current["key"]

        # Current key is exhausted, find the next non-exhausted one
        for i in range(len(self.keys)):
            idx = (self._current_index + 1 + i) % len(self.keys)
            entry = self.keys[idx]
            if not entry["exhausted"]:
                self._current_index = idx
                logger.info(f"Switched to key index {idx}")
                return entry["key"]

        logger.warning("All API keys exhausted!")
        return None

    def report_usage(self, api_key: str, remaining: int, used: int):
        """Update usage stats for a key after a request."""
        for entry in self.keys:
            if entry["key"] == api_key:
                entry["remaining"] = remaining
                entry["used"] = used
                entry["last_used"] = datetime.now(timezone.utc).isoformat()

                # Rotate when truly low - less than ~2 full scans worth
                if remaining is not None and remaining <= 5:
                    entry["exhausted"] = True
                    logger.info(
                        f"API key truly exhausted ({remaining} left), marking dead"
                    )
                    self._rotate()
                elif remaining is not None and remaining <= 30:
                    # Getting low but not dead - rotate to spread usage
                    logger.info(f"API key getting low ({remaining} left), rotating")
                    self._rotate()
                break

    def report_error(self, api_key: str):
        """Handle an API error. Only marks exhausted if key is actually low or untested."""
        for entry in self.keys:
            if entry["key"] == api_key:
                remaining = entry["remaining"]
                if remaining is None or remaining <= 20:
                    # Key is untested or actually low - mark it dead
                    entry["exhausted"] = True
                    logger.warning(f"API key marked exhausted (remaining: {remaining})")
                else:
                    # Key has plenty of credits - probably a transient error
                    # Don't kill it, just rotate away temporarily
                    logger.warning(
                        f"API key got error but has {remaining} remaining - "
                        f"rotating but NOT marking exhausted"
                    )
                self._rotate()
                break

    def _rotate(self):
        """Move to the next key in the pool."""
        if len(self.keys) <= 1:
            return
        self._current_index = (self._current_index + 1) % len(self.keys)
        logger.info(f"Rotated to key index {self._current_index}")

    def reset_all(self):
        """Reset exhausted status on all keys (for new month)."""
        for entry in self.keys:
            entry["exhausted"] = False
            entry["remaining"] = None
            entry["used"] = None
        self._current_index = 0
        self._last_reset_month = datetime.now(timezone.utc).month
        logger.info("All API keys reset (fresh start)")

    def check_monthly_reset(self):
        """Auto-reset all keys on the 1st of each month (Odds API monthly cycle)."""
        current_month = datetime.now(timezone.utc).month
        if not hasattr(self, "_last_reset_month"):
            self._last_reset_month = current_month
        if current_month != self._last_reset_month:
            logger.info(f"New month detected ({self._last_reset_month} -> {current_month}), resetting all API keys")
            self.reset_all()

    def get_total_remaining(self) -> int:
        """Get total remaining requests across all keys."""
        total = 0
        for entry in self.keys:
            if entry["remaining"] is not None and not entry["exhausted"]:
                total += entry["remaining"]
            elif entry["remaining"] is None and not entry["exhausted"]:
                # Key hasn't been used yet, don't assume - will update after first request
                total += 0
        return total

    def get_status(self) -> dict:
        """Get status of all keys (masking the actual key values)."""
        status = []
        for i, entry in enumerate(self.keys):
            masked = entry["key"][:8] + "..." + entry["key"][-4:] if len(entry["key"]) > 12 else "***"
            status.append({
                "index": i,
                "key_masked": masked,
                "remaining": entry["remaining"],
                "used": entry["used"],
                "last_used": entry["last_used"],
                "exhausted": entry["exhausted"],
                "active": i == self._current_index,
            })

        return {
            "total_keys": len(self.keys),
            "total_remaining": self.get_total_remaining(),
            "untested_keys": sum(1 for e in self.keys if e["remaining"] is None and not e["exhausted"]),
            "current_index": self._current_index,
            "keys": status,
        }