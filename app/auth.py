"""Password hashing and bearer-token sessions."""
import hashlib
import os
import secrets
import time
import hmac


def hash_password(password, salt=None):
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
    return f"{salt.hex()}${digest.hex()}"


def verify_password(password, stored):
    salt_hex, _ = stored.split("$")
    candidate = hash_password(password, bytes.fromhex(salt_hex))
    return hmac.compare_digest(candidate, stored) #Used compare_digest to prevent timing attacks

def extract_bearer(header):
    """Return the token from 'Authorization: Bearer <token>', else None."""
    if not header:
        return None
    parts = header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer": #Bearer is case sensitive so lowered parts to match lower letters bearer
        return None
    return parts[1]


class TokenStore:
    """Opaque session tokens that expire after `ttl` seconds."""

    def __init__(self, ttl=3600, clock=time.time):
        self.ttl = ttl
        self.clock = clock
        self._tokens = {}

    def issue(self, user_id):
        token = secrets.token_urlsafe(32)
        self._tokens[token] = (user_id, self.clock() + self.ttl)
        return token

    def validate(self, token):
        entry = self._tokens.get(token)
        if entry is None:
            return None
        user_id, expires_at = entry
        if self.clock() >= expires_at:
            del self._tokens[token]
            return None
        return user_id

    def revoke(self, token):
        self._tokens.pop(token, None)
