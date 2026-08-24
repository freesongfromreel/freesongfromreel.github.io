"""Backend unit tests: pure logic + HTTP guards (no network in CI)."""
import pytest
from fastapi.testclient import TestClient
from main import app, _base_host, _spotify, ALLOWED_HOSTS

client = TestClient(app)


def test_base_host_extracts_allowed_domains():
    cases = {
        "https://www.instagram.com/reel/abc": "instagram.com",
        "https://m.instagram.com/reel/xyz": "instagram.com",
        "https://vm.tiktok.com/abc": "tiktok.com",
        "https://www.youtube.com/watch?v=1": "youtube.com",
        "https://youtu.be/abc": "youtu.be",
        "https://x.com/user/status/1": "x.com",
    }
    for url, expected in cases.items():
        assert _base_host(url) == expected


def test_base_host_rejects_unknown():
    assert _base_host("https://example.com/x") not in ALLOWED_HOSTS
    assert _base_host("https://evilsite.com/") not in ALLOWED_HOSTS


def test_health():
    assert client.get("/health").json() == {"ok": True}


def test_detect_rejects_non_http():
    r = client.post("/api/detect", json={"url": "notaurl"})
    assert r.status_code == 400
    assert "http" in r.json()["detail"].lower()


def test_detect_rejects_unsupported_host():
    r = client.post("/api/detect", json={"url": "https://example.com/v"})
    assert r.status_code == 400
    assert "unsupported platform" in r.json()["detail"]


def test_detect_accepts_known_host_shape():
    # reaches the _detect boundary; network failure -> 500, NOT 400 (proves host passed)
    r = client.post("/api/detect", json={"url": "https://www.instagram.com/reel/DcPd0UQu2hS/"})
    # either it ran (no network in test env -> exception -> 500) or unexpected
    assert r.status_code in (200, 500)
    if r.status_code == 500:
        assert "platform" not in r.json().get("detail", "")


def test_spotify_parses_provider_row():
    track = {"sections": [{"metadata": [{"title": "Other", "text": "nope"},
                                        {"title": "Apple Music", "text": "https://itunes"},
                                        {"title": "Open in Spotify", "text": "https://open.spotify.com/track/1"}]}]}
    assert _spotify(track) == "https://open.spotify.com/track/1"


def test_spotify_none_when_absent():
    assert _spotify({}) is None
    assert _spotify({"sections": [{"metadata": [{"title": "X", "text": "y"}]}]}) is None