from app import create_app
from app.ratelimit import RateLimiter


def test_blocks_requests_over_the_limit(clock):
    limiter = RateLimiter(limit=3, window=60, clock=clock)
    assert [limiter.allow("ip") for _ in range(4)] == [True, True, True, False]


def test_limit_is_per_key(clock):
    limiter = RateLimiter(limit=1, window=60, clock=clock)
    assert limiter.allow("a") is True
    assert limiter.allow("b") is True


def test_window_slides(clock):
    limiter = RateLimiter(limit=2, window=60, clock=clock)
    limiter.allow("ip")
    clock.advance(30)
    limiter.allow("ip")
    assert limiter.allow("ip") is False
    clock.advance(31)  # first hit has left the window
    assert limiter.allow("ip") is True


def test_api_returns_429_with_retry_after(tmp_path, clock):
    app = create_app(
        {"DATABASE": str(tmp_path / "rl.db"), "CLOCK": clock, "WALL_CLOCK": clock, "RATE_LIMIT": 3}
    )
    client = app.test_client()
    codes = [client.get("/stats").status_code for _ in range(4)]
    assert codes == [401, 401, 401, 429]
    assert int(client.get("/stats").headers["Retry-After"]) >= 1
