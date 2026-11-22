import pytest

from app import create_app


class FakeClock:
    def __init__(self, start=1_700_000_000.0):
        self.now = start

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def app(tmp_path, clock):
    return create_app(
        {
            "TESTING": True,
            "DATABASE": str(tmp_path / "test.db"),
            "CLOCK": clock,
            "WALL_CLOCK": clock,
            "RATE_LIMIT": 1000,
        }
    )


@pytest.fixture
def client(app):
    return app.test_client()


def signup(client, username="alice", password="password123"):
    """Register + log in. Returns an Authorization header dict."""
    assert client.post("/register", json={"username": username, "password": password}).status_code == 201
    token = client.post("/login", json={"username": username, "password": password}).get_json()["token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth(client):
    return signup(client)
