import threading
import time

from app.cache import TTLCache


def test_entries_expire_after_ttl(clock):
    cache = TTLCache(ttl=10, clock=clock)
    cache.set("a", 1)
    clock.advance(9)
    assert cache.get("a") == 1
    clock.advance(1)
    assert cache.get("a") is None


def test_least_recently_used_entry_is_evicted(clock):
    cache = TTLCache(capacity=2, ttl=100, clock=clock)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.get("a")  # "a" is now the most recently used
    cache.set("c", 3)
    assert cache.get("a") == 1
    assert cache.get("b") is None
    assert cache.get("c") == 3


def test_get_or_compute_runs_once_under_concurrency():
    cache = TTLCache()
    calls = []

    def slow_compute():
        calls.append(1)
        time.sleep(0.05)
        return "value"

    threads = [threading.Thread(target=cache.get_or_compute, args=("k", slow_compute)) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(calls) == 1
