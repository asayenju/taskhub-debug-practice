"""Sliding-window rate limiter."""
import time


class RateLimiter:
    """Allow at most `limit` requests per `window` seconds for each key."""

    def __init__(self, limit, window, clock=time.monotonic):
        self.limit = limit
        self.window = window
        self.clock = clock
        self._hits = {}

    def allow(self, key):
        now = self.clock()
        hits = self._hits.setdefault(key, [])
        cutoff = now - self.window
        hits[:] = [t for t in hits if t > cutoff]
        if len(hits) > self.limit:
            return False
        hits.append(now)
        return True

    def retry_after(self, key):
        """Seconds until the oldest hit leaves the window."""
        hits = self._hits.get(key)
        if not hits:
            return 0
        return max(0, hits[0] + self.window - self.clock())
