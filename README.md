# Reel to Song Finder

Identify the song in any Instagram Reel, TikTok, YouTube, X or Facebook video URL — free.
Static AdSense-friendly frontend on GitHub Pages + a cleanly separated detection backend on
Render's free tier. **GitOps CI/CD with automated deploy.**

## Architecture

```
Visitors ──> songfromreel.github.io     (static site, GitHub Pages, ~$0)
                  │ POST /api/detect
                  ▼
             backend (FastAPI + yt-dlp + shazamio, Render free, ~$0)
                  └ return {title, artist, cover, spotify?}
```

### Why the backend is a real server, not a Worker/Pages
Detection needs **Python + a binary ffmpeg + yt-dlp subprocess**. Cloudflare Workers and
GitHub Pages are both static/JS-only — they cannot run it. The backend must be an always-on
server, and **Render's free web service** is the best fit for a pre-revenue tool (see
"Hosting decision" below).

## Layout
```
site/       static site (deployed to GitHub Pages from site/ at root)
backend/    FastAPI detector (Render)
tests/      pytest suites — backend/tests (API logic) + site/tests (static smoke)
.github/workflows/   site.yml (validate+deploy Pages) + backend.yml (test+deploy Render)
```

## CI/CD (GitHub Actions, GitOps)
Two automatically-run workflows on `push` to `main` (PRs run the test jobs only):

| Workflow | On push | Does |
|---|---|---|
| `site.yml`     | `site/**` | 1. smoke-test the static site, 2. deploy to Pages |
| `backend.yml`  | `backend/**` | 1. install ffmpeg+deps, 2. `pytest`, 3. deploy to **Render** |

So **push to main → site rebuilds + backend redeploys automatically.** Only manual config is
the backend URL in `site/index.html` → `var API = ...` (set once, then it's stable).

### Hosting decision (final): Render free tier, not Fly
Detection can't run on CF Workers / GitHub Pages. Among real servers:

- **Render free** wins for a pre-revenue tool: **750 instance-hours/month**, 512MB/0.1CPU,
  **spins down after 15 min idle** (cold-start ~10–30s) → **~$0 while idle**, and **no credit
  card** required for the free instance type. Ideal for bursty AdSense-phase traffic.
- **Fly.io** makes you pay (~$2–4/mo after trial credits). Better latency/cold-start, but not
  worth it before traction.
- **Oracle Always Free** (4 OCPU ARM, 24GB) is the best raw free power for the long-run, but
  needs card verification + fiddly setup — overkill for now.

## What I need from you (exact, and where)
Do this once, then backend deploys are automatic on every push:

1. **Render account** → https://dashboard.render.com → sign up (free, email/Google/GitHub).
2. **Create the backend service** (free):
   - Dashboard → **New → Web Service**
   - Connect your GitHub repo; **Root Directory** = `backend`
   - Environment: **Python 3**; Region: nearest to you.
   - Build command: `sudo apt-get update && sudo apt-get install -y ffmpeg && python -m pip install -r requirements.txt`
   - Start command: `python -m uvicorn main:app --host 0.0.0.0 --port 8000`
   - Instance type: **Free** → **Create Web Service**.
   - Note its URL, e.g. `https://reel2song-backend.onrender.com`.
3. **Point the site at it** — in `site/index.html` change:
   ```js
   var API = "https://reel2song-backend.onrender.com/api/detect";
   ```
   (push again; the site redeploys to Pages.)
4. **Wire up auto-deploy** (optional but recommended) — Render:
   `https://dashboard.render.com/account/settings` → **API Keys → Create** (scope: read+deploy).
   Then in your **GitHub repo → Settings → Secrets and variables → Actions** add:
   - `RENDER_API_KEY` = the key above
   - `RENDER_SERVICE_ID` = your service's ID (in the dashboard URL after `/srv-`, or
     **Settings → Details**)
   Until both are set, the site still deploys to Pages but backend deploy prints a skip note.

## Test suites
- `backend/tests/test_main.py` — host allow-list, scheme guard, health, Spotify-row parser,
  known/unknown host routing. Network-free.
- `site/tests/test_site.py` — all pages present with title+description, index advertises
  IG/TikTok/YT/X, footer links resolve, inline JS braces balanced.
- Run locally:
  ```bash
  pip install -r backend/requirements.txt -r backend/requirements-dev.txt
  python -m pytest backend/tests site/tests
  ```

## Terraform — skip (decision)
CI/CD (Actions) *is* your deployment automation. Terraform automates *provisioning* — ~4
resources here, fewer than the ceremony it adds (state bucket, apply step). Reach for it past
~6 resources or to re-create the whole tool portfolio from one script; day-to-day deploys
stay Actions either way.

## Verified
- `pytest` 13/13 green.
- End-to-end live test: real public reel → `{"ok":true,"title":"mr. goodman munni","artist":"bleood"}`.

## Need ffmpeg? (only if shazamio errors "ffmpeg not found" on Render)
The build command installs ffmpeg at deploy. If the image still lacks it, check Render logs and
confirm the build command ran the `sudo apt-get install -y ffmpeg` step (it's part of the
recommended setup above).