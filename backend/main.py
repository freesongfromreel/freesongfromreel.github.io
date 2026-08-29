"""Reel2Song detection backend. Separated from the static site.

Flow: video URL -> yt-dlp extracts audio -> shazamio identifies -> {title, artist, spotify}.
      or uploaded file -> ffmpeg extracts audio -> shazamio identifies (same shape).

Run:  PATH="$PWD/.venv/bin:$PATH" python -m uvicorn main:app --port 8000
"""
import os, tempfile, shutil, re, subprocess
from urllib.parse import urlparse
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Reel2Song API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # public tool; tighten to site origin if abuse appears
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
)

ALLOWED_HOSTS = {
    "instagram.com", "tiktok.com", "youtube.com", "youtu.be",
    "x.com", "twitter.com", "facebook.com", "fb.watch", "threads.net",
}

MAX_UPLOAD = 50 * 1024 * 1024  # 50MB; Render free has 512MB RAM
ALLOWED_EXT = {".mp4", ".mov", ".m4v", ".webm", ".mkv", ".3gp",
               ".mp3", ".m4a", ".wav", ".ogg", ".aac", ".flac", ".opus", ".aiff"}


class DetectReq(BaseModel):
    url: str


def _base_host(url: str) -> str:
    host = urlparse(url).netloc.lower()
    host = re.sub(r"^(www\.|m\.|vm\.|mbasic\.)", "", host)
    # match against known allowed hosts directly (handles .com, .co.uk, .be correctly)
    for allowed in ALLOWED_HOSTS:
        if host == allowed or host.endswith("." + allowed):
            return allowed
    return host


def _parse_shazam(res: dict) -> dict:
    """Parse a shazamio recognize() result. Pure + testable (no network)."""
    track = (res or {}).get("track") or {}
    mt = (res or {}).get("matches") or []
    if not track and not mt:
        raise HTTPException(404, "could not identify the song (0 results)")
    title = track.get("title") or (mt[0].get("track", {}).get("title") if mt else None)
    artist = track.get("subtitle") or (mt[0].get("track", {}).get("subtitle") if mt else None)
    cover = ((track.get("images") or {}).get("coverart")) if track else None
    return {
        "ok": True,
        "title": title,
        "artist": artist,
        "cover": cover,
        "spotify": _spotify(track),
    }


async def _recognize(audio_bytes: bytes) -> dict:
    """Fingerprint raw audio bytes via Shazam. Shared by URL + file paths."""
    from shazamio import Shazam
    res = await Shazam().recognize(audio_bytes)
    return _parse_shazam(res)


def _extract_audio(data: bytes, work: Path) -> Path:
    """Decode any uploaded video/audio bytes to a mono 16kHz wav via ffmpeg."""
    src = work / "upload.bin"
    src.write_bytes(data)
    out = work / "audio.wav"
    try:
        ff = "ffmpeg"
        try:
            import imageio_ffmpeg
            ff = imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            pass
        subprocess.run(
            [ff, "-y", "-i", str(src), "-vn", "-ac", "1", "-ar", "16000", str(out)],
            capture_output=True, timeout=120,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        pass  # fall through to existence check
    if not out.exists():
        raise HTTPException(422, "could not decode audio from that file — is it a video/audio file?")
    return out


async def _detect(url: str) -> dict:
    work = Path(tempfile.mkdtemp(prefix="reel_"))
    try:
        audio = _download_audio(url, work)
        if not audio:
            raise HTTPException(422, "no audio track found in that post")
        res = await _recognize(audio.read_bytes())
        res["source"] = _base_host(url)
        return res
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _download_audio(url: str, work: Path):
    """Download audio via yt-dlp. Retries with android player client to dodge YT bot-checks."""
    import yt_dlp
    last_err = None
    variants = [{}]
    if "youtube" in url or "youtu.be" in url:
        variants.append({"extractor_args": {"youtube": {"player_client": ["android"]}}})
    for i, extra in enumerate(variants):
        opts = {
            "format": "ba/b",
            "extract_audio": True,
            "audio_format": "m4a",
            "audio_quality": "0",
            "outtmpl": str(work / "%(id)s.%(ext)s"),
            "quiet": True,
            "no_warnings": True,
        }
        opts.update(extra)
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.extract_info(url, download=True)
            audio = next(work.glob("*.m4a"), next(work.glob("*.mp3"), None))
            if audio:
                return audio
        except Exception as e:  # yt-dlp raises DownloadError etc.; try next variant
            last_err = e
    if isinstance(last_err, Exception):
        msg = str(last_err).strip()
        # friendly mapping for the common bot-wall
        if "Sign in to confirm" in msg or "bot" in msg.lower():
            raise HTTPException(422, "YouTube blocked the request (bot-check). Try an Instagram or TikTok link, or retry later.")
        raise HTTPException(502, msg[:300])
    return None


def _spotify(track: dict):
    """Pull a public streaming URL from shazamio's track data if present."""
    if not track:
        return None
    for section in track.get("sections") or []:
        for meta in section.get("metadata") or []:
            title = (meta.get("title") or "").lower()
            if "spotify" in title or "open.spotify" in str(meta.get("text", "")):
                return meta.get("text") or meta.get("url")
    return None


@app.post("/api/detect")
async def detect(req: DetectReq):
    url = (req.url or "").strip()
    if not re.match(r"^https?://", url):
        raise HTTPException(400, "paste a valid http(s) URL")
    host = _base_host(url)
    if host not in ALLOWED_HOSTS:
        raise HTTPException(400, f"unsupported platform (allowed: {', '.join(sorted(ALLOWED_HOSTS))})")
    try:
        return await _detect(url)
    except HTTPException:
        raise
    except Exception as e:  # surface failures to the site as plain errors
        raise HTTPException(500, str(e)[:300])


@app.post("/api/detect-file")
async def detect_file(file: UploadFile = File(...)):
    """Detect a song from an uploaded video/audio file (browser never touches the platforms)."""
    name = (file.filename or "").lower()
    ext = os.path.splitext(name)[1].lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(415, f"unsupported file type '{ext or '(none)'}' — upload a video or audio file (mp4, mov, webm, mp3, m4a, wav…)")
    data = await file.read()
    if not data:
        raise HTTPException(422, "empty file")
    if len(data) > MAX_UPLOAD:
        raise HTTPException(413, f"file too large — max {MAX_UPLOAD // (1024 * 1024)}MB")
    work = Path(tempfile.mkdtemp(prefix="reel_f_"))
    try:
        audio = _extract_audio(data, work)
        res = await _recognize(audio.read_bytes())
        res["source"] = "file"
        return res
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e)[:300])
    finally:
        shutil.rmtree(work, ignore_errors=True)


@app.get("/health")
async def health():
    return {"ok": True}


if __name__ == "__main__":
    # self-check: run without starting the server
    import asyncio
    async def _check():
        for bad in ["notaurl", "https://example.com/x"]:
            try:
                await detect(DetectReq(url=bad))
                print("FAIL: should have raised for", bad)
            except HTTPException:
                pass
        print("self-check ok: bad-URL guard works")
    asyncio.run(_check())