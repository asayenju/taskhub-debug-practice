from app.webhooks import sign, verify

SECRET = "s3cret"
BODY = b'{"event": "task.created"}'


def test_valid_signature_is_accepted():
    sig = sign(SECRET, BODY, 1000)
    assert verify(SECRET, BODY, sig, 1000, now=1000) is True


def test_tampered_body_is_rejected():
    sig = sign(SECRET, BODY, 1000)
    assert verify(SECRET, b'{"event": "task.deleted"}', sig, 1000, now=1000) is False


def test_old_deliveries_are_rejected():
    sig = sign(SECRET, BODY, 1000)
    assert verify(SECRET, BODY, sig, 1000, now=1000 + 301) is False


def test_replayed_signature_cannot_be_given_a_fresh_timestamp():
    sig = sign(SECRET, BODY, 1000)
    # An attacker captured (BODY, sig) and re-sends it later with a new timestamp.
    assert verify(SECRET, BODY, sig, 5000, now=5000) is False


def test_endpoint_accepts_signed_delivery(client, clock):
    ts = int(clock())
    sig = sign("dev-secret", BODY, ts)
    resp = client.post("/webhooks/incoming", data=BODY, headers={"X-Signature": sig, "X-Timestamp": str(ts)})
    assert resp.status_code == 202


def test_endpoint_rejects_bad_signature(client, clock):
    resp = client.post(
        "/webhooks/incoming", data=BODY, headers={"X-Signature": "00", "X-Timestamp": str(int(clock()))}
    )
    assert resp.status_code == 401
