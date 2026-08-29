"""Backend unit tests: pure logic + HTTP guards (no network in CI)."""
import pytest
from fastapi.testclient import TestClient
import main
from main import app, _base_host, _spotify, _parse_shazam, ALLOWED_HOSTS, ALLOWED_EXT, MAX_UPLOAD

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


def test_parse_shazam_raises_when_empty():
    with pytest.raises(Exception):
        _parse_shazam({})
    with pytest.raises(Exception):
        _parse_shazam(None)


def test_parse_shazam_extracts_track_and_links():
    res = {"track": {"title": "Song", "subtitle": "Artist", "images": {"coverart": "http://img"},
                     "sections": [{"metadata": [{"title": "Open in Spotify", "text": "https://open.spotify.com/track/1"}]}]}}
    out = _parse_shazam(res)
    assert out["title"] == "Song"
    assert out["artist"] == "Artist"
    assert out["cover"] == "http://img"
    assert out["spotify"] == "https://open.spotify.com/track/1"


def test_detect_file_rejects_bad_ext():
    r = client.post("/api/detect-file", files={"file": ("song.txt", b"hello", "text/plain")})
    assert r.status_code == 415


def test_detect_file_rejects_oversized(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "MAX_UPLOAD", 10)
    r = client.post("/api/detect-file", files={"file": ("song.mp3", b"x" * 20, "audio/mpeg")})
    assert r.status_code == 413


def test_detect_file_accepts_known_ext():
    # .wav is allowed; garbage bytes -> decode fails 422 (proves it passed the ext gate, NOT 415/413)
    r = client.post("/api/detect-file", files={"file": ("song.wav", b"\0" * 100, "audio/wav")})
    assert r.status_code in (200, 422, 500)
    assert r.status_code != 415 and r.status_code != 413