"""In-memory LRU cache with per-entry expiry."""
import threading
import time
from collections import OrderedDict

_MISSING = object()


class TTLCache:
    """Tiny LRU cache whose entries expire `ttl` seconds after being set."""

    def __init__(self, capacity=128, ttl=60, clock=time.monotonic):
        self.capacity = capacity
        self.ttl = ttl
        self.clock = clock
        self._data = OrderedDict()
        self._lock = threading.RLock()

    def get(self, key, default=None):
        with self._lock:
            entry = self._data.get(key)
            if entry is None:
                return default
            value, expires_at = entry
            if self.clock() >= expires_at:
                del self._data[key]
                return default
            self._data.move_to_end(key) #Added this to send key from least recent to most recent
            return value

    def set(self, key, value):
        with self._lock:
            self._data[key] = (value, self.clock() + self.ttl)
            self._data.move_to_end(key)
            if len(self._data) > self.capacity:
                self._data.popitem(last=False)

    def invalidate(self, key):
        with self._lock:
            self._data.pop(key, None)

    def get_or_compute(self, key, fn):
        """Return the cached value, computing and storing it on a miss."""
        with self._lock: #Added this to run concurrently 
            value = self.get(key, _MISSING)
            if value is _MISSING:
                value = fn()
                self.set(key, value)
            return value
