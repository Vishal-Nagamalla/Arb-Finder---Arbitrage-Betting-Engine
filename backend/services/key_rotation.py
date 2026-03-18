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
        """Get the current active API key."""
        if not self.keys:
            return None

        # Find a non-exhausted key starting from current index
        attempts = 0
        while attempts < len(self.keys):
            entry = self.keys[self._current_index]
            if not entry["exhausted"]:
                return entry["key"]
            self._current_index = (self._current_index + 1) % len(self.keys)
            attempts += 1

        logger.warning("All API keys exhausted!")
        return None

    def report_usage(self, api_key: str, remaining: int, used: int):
        """Update usage stats for a key after a request."""
        for entry in self.keys:
            if entry["key"] == api_key:
                entry["remaining"] = remaining
                entry["used"] = used
                entry["last_used"] = datetime.now(timezone.utc).isoformat()

                # Rotate early - need at least 10 calls for a full scan
                # (6 sports with retry potential)
                if remaining is not None and remaining <= 15:
                    entry["exhausted"] = True
                    logger.info(
                        f"API key low ({remaining} left), rotating to next key"
                    )
                    self._rotate()
                break

    def report_error(self, api_key: str):
        """Mark a key as potentially exhausted on error (e.g., 401/429)."""
        for entry in self.keys:
            if entry["key"] == api_key:
                entry["exhausted"] = True
                logger.warning(f"API key marked exhausted due to error")
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
        self._current_index = 0

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