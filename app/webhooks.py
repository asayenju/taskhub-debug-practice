"""Signature checking for incoming webhooks."""
import hashlib
import hmac
import time


def sign(secret, body, timestamp):
    """Hex HMAC-SHA256 signature for a webhook delivery."""
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def verify(secret, body, signature, timestamp, now=None, tolerance=300):
    """True if `signature` is valid and the delivery is recent (anti-replay)."""
    now = time.time() if now is None else now
    if abs(now - timestamp) > tolerance:
        return False
    return hmac.compare_digest(sign(secret, body, timestamp), signature)
