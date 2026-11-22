from unittest import mock

from app.auth import TokenStore, extract_bearer, hash_password, verify_password


def test_password_roundtrip():
    stored = hash_password("correct horse")
    assert verify_password("correct horse", stored) is True
    assert verify_password("wrong horse", stored) is False


def test_same_password_hashes_differently():
    assert hash_password("pw") != hash_password("pw")


def test_password_check_is_constant_time():
    import hmac

    stored = hash_password("secret")
    with mock.patch("hmac.compare_digest", wraps=hmac.compare_digest) as spy:
        verify_password("secret", stored)
    assert spy.called


def test_bearer_header_parsing():
    assert extract_bearer("Bearer abc123") == "abc123"
    assert extract_bearer("Basic abc123") is None
    assert extract_bearer("Bearer") is None
    assert extract_bearer(None) is None


def test_bearer_scheme_is_case_insensitive():
    assert extract_bearer("bearer abc123") == "abc123"
    assert extract_bearer("BEARER abc123") == "abc123"


def test_tokens_expire(clock):
    store = TokenStore(ttl=100, clock=clock)
    token = store.issue(7)
    clock.advance(99)
    assert store.validate(token) == 7
    clock.advance(1)
    assert store.validate(token) is None


def test_revoked_tokens_stop_working(clock):
    store = TokenStore(clock=clock)
    token = store.issue(1)
    store.revoke(token)
    assert store.validate(token) is None
