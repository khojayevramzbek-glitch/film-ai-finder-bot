import time
import threading
import logging
from typing import List, Optional, Dict

logger = logging.getLogger(__name__)


class APIKeyPool:
    """
    Thread-safe API Key Pool Manager with Round-Robin distribution,
    automatic rate-limit detection, cooldown tracking, and failover support.
    """

    def __init__(self, keys: List[str], service_name: str = "API", default_cooldown: int = 60):
        self.service_name = service_name
        self.default_cooldown = default_cooldown
        # Clean and deduplicate keys while preserving order
        seen = set()
        self.keys: List[str] = [k.strip() for k in keys if k.strip() and not (k.strip() in seen or seen.add(k.strip()))]
        self._current_index = 0
        self._cooldowns: Dict[str, float] = {}  # key -> timestamp when it becomes available again
        self._lock = threading.Lock()

    @property
    def total_count(self) -> int:
        """Returns total number of configured keys."""
        return len(self.keys)

    def is_empty(self) -> bool:
        """Checks if pool has any keys."""
        return len(self.keys) == 0

    def get_active_count(self) -> int:
        """Returns number of currently available (non-cooldown) keys."""
        now = time.time()
        with self._lock:
            return sum(1 for k in self.keys if self._cooldowns.get(k, 0) <= now)

    def get_key(self) -> Optional[str]:
        """
        Retrieves the next available API key using Round-Robin.
        If all keys are in cooldown, returns the one with the earliest expiration.
        """
        if not self.keys:
            return None

        now = time.time()
        with self._lock:
            total = len(self.keys)
            # Try to find a non-cooldown key starting from current index
            for _ in range(total):
                key = self.keys[self._current_index]
                self._current_index = (self._current_index + 1) % total
                if self._cooldowns.get(key, 0) <= now:
                    return key

            # If all keys are currently cooling down, return the one that will expire first
            earliest_key = min(self.keys, key=lambda k: self._cooldowns.get(k, 0))
            logger.warning(
                f"[{self.service_name}] Barcha {total} ta API kalitlari vaqtinchalik limitda. "
                f"Eng tez tiklanadigan kalit tanlandi."
            )
            return earliest_key

    def report_rate_limit(self, key: str, cooldown_seconds: Optional[int] = None) -> None:
        """
        Marks a key as rate-limited (HTTP 429 / Quota Exceeded) and sets a cooldown timer.
        """
        if not key:
            return

        cd = cooldown_seconds or self.default_cooldown
        expire_at = time.time() + cd

        with self._lock:
            self._cooldowns[key] = expire_at
            active_count = sum(1 for k in self.keys if self._cooldowns.get(k, 0) <= time.time())
            masked_key = f"{key[:6]}...{key[-4:]}" if len(key) > 10 else "***"
            logger.warning(
                f"⚠️ [{self.service_name}] Kalitda limit tugadi: {masked_key}. "
                f"{cd}s kutish rejimiga olindi. Qolgan faol kalitlar: {active_count}/{len(self.keys)}"
            )

    def report_success(self, key: str) -> None:
        """Clears any cooldown on a successful request."""
        if not key:
            return
        with self._lock:
            if key in self._cooldowns and self._cooldowns[key] <= time.time():
                del self._cooldowns[key]
