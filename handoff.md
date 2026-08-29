# Handoff — FreeSongFromReel (reel → song detection tool)

Session snapshot: 2026-08-29 (supersedes 08-24 snapshot). Everything below is
the durable state + the open decisions for the next session. Read this first.

## 1. What this is

A free tool: paste any social video URL (Instagram Reel, TikTok, YouTube, X,
Facebook) **or drop a local video/audio file** → backend extracts audio
(yt-dlp + ffmpeg for URLs; ffmpeg only for files) → Shazam identifies it
(shazamio, no API key) → page shows title/artist + Spotify link.
Monetization plan: **Google AdSense on a static site** (free tool, no paywall).
No subscription — decided, do not re-open. Free (vs the paid clones) is the
stated differentiator in copy + schema.

## 2. Live state (verified working)

| Thing | Value |
|---|---|
| Live site | **https://freesongfromreel.github.io/** (200, GitHub Pages via GitHub Actions, `site/` folder) |
| GitHub org | `freesongfromreel` (renamed from `songfromreel` — brand collision with live competitor songfromreel.com) |
| Repo (source of truth) | `freesongfromreel/freesongfromreel.github.io` |
| Mirror repo | `afrowalkmanstudios/songfromreel.github.io` (both in sync, push both) |
| Backend | FastAPI on Render free: https://reel2song-backend.onrender.com (health `/health`). Endpoints: `/api/detect` (URL) + **`/api/detect-file` (file upload)** |
| Frontend↔backend | `site/index.html` → `var API = .../api/detect`, `var API_FILE = .../api/detect-file` |
| Help page | `site/help.html` — per-platform "download the video yourself" guides (IG/TikTok official buttons; YT/X screen-record; FB download menu), linked from index + footer + sitemap |
| GA4 | Property "FreeSongFromReel", Measurement ID `G-NMDXLM3Z2J`, wired via `site/common/track.js` on all 6 pages |
| Hidden inbox (FormSubmit) | `afrowalkmanstudios@gmail.com` — contact form + waitlist both post here; **activation email must be clicked once** then it flows |
| GSC | Property added + **verified via HTML file** (`googlee47db03d7de72591.html` still in repo). Sitemap submit was "couldn't fetch" once — likely pre-verification; resubmit. |
| CI/CD | push to `main` → `site.yml` deploys Pages + `backend.yml` runs tests and deploys Render via its REST API (secrets `RENDER_API_KEY` + `RENDER_SERVICE_ID`) |

**All tests pass:** `pytest backend/tests site/tests` → 18 passed.

## 3. Hard engineering facts (learned, don't re-litigate)

- **Render free tier's shared datacenter IPs are blacklisted** by IG (429),
  TikTok (IP block), YouTube (bot-check). The SAME reel extracts fine from a
  residential/clean IP. **Root cause = IP reputation, not code.** No code fix
  can un-poison a shared IP.
- **The file-upload path sidesteps IP reputation entirely:** the user's own
  browser/device downloads the video (their IP, their login) and uploads the
  bytes; the backend only ever sees the file. `yt-dlp` stays for the URL path
  but is no longer the only route. Live-verified Aug 29: real wav → upload →
  ffmpeg → Shazam (all ran; test tone correctly returned "could not identify").
- **CORS blocks browser-side downloads from IG/TikTok/YT** — none send
  `Access-Control-Allow-Origin` for a browser cross-origin fetch. No JS can
  fetch those videos from a page; "user downloads then uploads" is the only
  client-side pattern that works.
- **Render deploys from the LINKED REPO/branch, not the triggering one:** the
  REST deploy call just enqueues a build of what Render has configured. After
  a repo rename/org change, Render may still pull the OLD mirror → pushes to
  org do nothing visible. If a backend change doesn't go live, check which
  repo Render's service is linked to and push THAT repo too (both remotes
  here are kept in sync).
- **`python-multipart` is required for FastAPI `UploadFile`/FormData** — a
  missing/glued line in requirements breaks the whole build (collect error:
  `Form data requires "python-multipart"`).
- yt-dlp android-client retry (`player_client: android`) is wired for YT;
  it only sometimes helps. IG/TikTok need a different IP, period.
- `secrets` is **NOT a valid context in step-level `if:`** → map to `env:`
  first, gate on `env.X`. (Broke the workflow with "Unrecognized named-value:
  'secrets'" otherwise.)
- `render-exports/render-github-action` **does not exist (404)**. Use Render's
  REST API directly: `POST https://api.render.com/v1/services/$ID/deploys` with
  `Authorization: Bearer $KEY`. See `backend.yml` for the working pattern.
- Repo import into an org **does NOT carry secrets, Pages source, or Actions
  environments** — re-add secrets, re-enable Pages (Source: GitHub Actions
  for a subfolder site), environments auto-create or make manually.
- Pages "Deploy from a branch" only offers `/` or `/docs`. Use
  **GitHub Actions source** (upload-pages-artifact `path: site`) to publish any
  folder.
- **Pages stale-deployment deadlock:** a stuck "in progress" Pages build blocks
  EVERY new deploy with "Please cancel <sha>... or wait". No REST API cancels
  it. **Fix: Settings → Pages → Unpublish site**, then re-enable GitHub Actions
  source. This clears the queue (verified).
- A rename (org + repo) keeps secrets/workflows/Pages config; update local git
  remotes afterwards.

## 4. The reusable traffic-validation kit (`site/common/`)

Copy `site/common/` into ANY future utility site:

- **`track.js`** — GA4 loader. Tag: `<script src="common/track.js"
  data-ga="G-XXX">`. No GA ID → fully no-op (zero network). Privacy-first:
  localStorage visitor id, no cookies. Exposes `window.track(name, params)`.
  Fires: `page_view` + `search_attempt` / `search_success` / `search_error`
  (tool funnel) + `waitlist_signup` / `contact_submit`.
- **`waitlist.html`** — email capture → FormSubmit (hidden inbox). Hidden until
  DATA_EMAIL set.
- **`README.md`** — wiring guide for the next site.

## 5. Validation status (what we learned about the niche)

- **niche scatter** (`/workspace/utility-site-clone/`): reel/music seeds score
  100% tool-shaped / 0% crowded → bottom-right "BUILD" quadrant. Scripts:
  `keyword_suggest.py` → `suggestions_all.csv` → `plot_niche_scatter.py`.
  (Patched `_TOOL` regex to include identify/recognize/find-song/song-from.)
- **SERP check** ("identify song from reel"): **crowded field** — ~8-10 direct
  clones (song-fromreel.com, ClipMusic, MelodySeek, SongFinder, Song
  Detector...). "Free" is NOT a differentiator — they all say free.
  Differentiated queries (free/no-signup) still surface the same crowd.
- **Therefore**: treat reel→song as `build IF we have a real edge`, not a
  greenfield. Existing utility niches (converter, timer, pdf, random) look
  cleaner on the scatter.
- **SEO pass done Aug 29**: `robots.txt` + `sitemap.xml` (site root),
  canonical, WebApplication schema (price 0), H1/footer rebranded "Free Song
  from Reel", GSC verified via HTML file. Waiting on Google to crawl (resubmit
  sitemap + request indexing after verified).

## 6. Decisions to make NEXT (todo, rough priority)

1. **Watch GA4 for a few days** — Realtime + `search_attempt` vs
   `search_error` (platform-tagged: `instagram`/`tiktok`/`youtube`/`file`) vs
   `waitlist_signup`. Decides: are people finding it? Want it but backend
   broken? (Traffic signal.)
2. **Decide backend host now that IP reputation is the blocker** (only matters
   for the URL path; the file path is host-agnostic):
   - A) **Home IP via Cloudflare Tunnel** — cleanest IP, $0, but PC must stay
     on 24/7 + consumer-ISP ToS risk.
   - B) **Cheap VPS ~$1-3/mo dedicated clean IP** — test the IP FIRST with one
     yt-dlp of a known real reel before committing.
   - C) Keep Render — broken for most links, not viable for traffic.
   - D) Oracle Always Free — idle ARM reclaim kills a sleeping backend; bad fit.
   - Tor: never (all three platforms block Tor exit nodes).
3. **AdSense** — only after traffic shows up (~700-1,400 views/mo clears ~$2/mo
   at $2-5 RPM). Needs legal pages (done), ~100-200 views/day ideal.
4. **Domain** (~$10/yr .com via Cloudflare) — only when a niche proves revenue.
   `freesongfromreel` still free as .com/.io if ever needed.
5. **GSC sitemap** — property is verified (Aug 29); resubmit `sitemap.xml`
   (first submit said "couldn't fetch", likely pre-verification). Then request
   indexing for `/` + `help.html` via URL Inspection once crawlable.
6. **Traffic push when ready** — Reddit r/NameThatSong / r/TipOfMyTongue
   helpful-answer play + TikTok/YT comment sections; SEO alone takes 4-8 wks.
   Lead with the free angle (that's the differentiator vs paid clones).
7. **Cleanup: revoke the GitHub PAT** used this session once everything's
   pushed (your responsibility — noted once, not again).
8. **Optional: Invidious/Piped fallback for YT** if YT links become common
   (deferred — not built).

## 6b. File-upload feature (flag if you ever revert)

- Backend: `/api/detect-file` (multipart `file`), ext allow-list, 50MB cap,
  ffmpeg decode → shared `_recognize`. `python-multipart` added to
  requirements.txt (build breaks without it).
- Frontend: `📁 File` button + drag&drop on the URL card; same result UI;
  `search_attempt/success/error` tagged `platform:'file'`.
- `help.html` explains how to download from each platform (official buttons +
  screen-record fallback). Added to footer + sitemap + smoke-test PAGES list.

## 7. Repo layout (one codebase)

```
site/          static frontend (index + help + legal pages + common/ kit) → Pages
backend/       FastAPI (main.py: /api/detect, /api/detect-file, /health) + tests + Dockerfile → Render
workflows/     site.yml (Pages), backend.yml (test + Render REST deploy)
handoff.md    this file
```

## 8. Security notes

- Secrets live in GitHub repo Secrets (the `***` seen in tool output is a
  display artifact, NOT file corruption — verify with a hexdump if in doubt).
- Never store the PAT in a remote URL — embed it only in the one-off push URL,
  then scrub with `git remote set-url` immediately after.