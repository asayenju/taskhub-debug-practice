"""TaskHub: a small multi-user task manager API."""
import os
import time

from flask import Flask, g, jsonify, request

from .auth import TokenStore
from .cache import TTLCache
from .db import init_db
from .ratelimit import RateLimiter


def create_app(config=None):
    app = Flask(__name__)
    app.config.update(
        DATABASE="taskhub.db",
        RATE_LIMIT=100,
        RATE_WINDOW=60,
        TOKEN_TTL=3600,
        CACHE_TTL=30,
        WEBHOOK_SECRET=os.environ.get("WEBHOOK_SECRET", "dev-secret"),
        CLOCK=time.monotonic,
        WALL_CLOCK=time.time,
    )
    if config:
        app.config.update(config)

    app.limiter = RateLimiter(
        app.config["RATE_LIMIT"], app.config["RATE_WINDOW"], clock=app.config["CLOCK"]
    )
    app.tokens = TokenStore(ttl=app.config["TOKEN_TTL"], clock=app.config["WALL_CLOCK"])
    app.cache = TTLCache(capacity=256, ttl=app.config["CACHE_TTL"], clock=app.config["CLOCK"])
    init_db(app.config["DATABASE"])

    @app.before_request
    def throttle():
        key = request.remote_addr or "unknown"
        if not app.limiter.allow(key):
            resp = jsonify(error="rate limit exceeded")
            resp.status_code = 429
            resp.headers["Retry-After"] = str(int(app.limiter.retry_after(key)) + 1)
            return resp

    @app.teardown_appcontext
    def close_db(exc):
        conn = g.pop("db", None)
        if conn is not None:
            conn.close()

    from .routes import bp

    app.register_blueprint(bp)
    return app
