# Common kit — traffic-validation modules (reusable across utility sites)

Drop-in modules for measuring traffic and capturing demand on any static tool site.
Copy `common/` wholesale into the next site. No build step.

## Files

| File | Purpose | Config |
|---|---|---|
| `track.js` | Analytics kernel: GA4 page views + events, privacy-first (localStorage visitor id, no cookies). No-op until given a GA ID. | `data-ga="G-XXXX"` on the script tag |
| `waitlist.html` | Demand-capture widget: email box that posts to FormSubmit, emits `waitlist_signup` event. | `DATA_EMAIL` const inside the script |

## How to wire into a new site

1. Copy the `common/` folder into the site.
2. In `<head>` (or before your tool script): include analytics once
   ```html
   <script src="common/track.js" data-ga="G-XXXXXXX"></script>
   ```
   Leave `data-ga=""` to keep it fully off (no network, no errors).
3. In your tool's JS, fire events at the funnels that matter for validation:
   ```js
   window.track("search_attempt");   // user clicked the button
   window.track("search_success");   // got a result
   window.track("search_error");     // errored
   ```
   Only `search_attempt` and `search_error` matter pre-backend-fix; `search_success`
   starts mattering once detection works.
4. Paste the `waitlist.html` block (HTML + `<style>` + `<script>`) into the page before
   `</body>`, set `DATA_EMAIL` to the signup inbox, and click the one-time FormSubmit
   activation email the first signup triggers.
5. Watch GA4 (Realtime + Events reports) to see visits and the attempt→error funnel.

## Notes

- Everything degrades gracefully: no GA ID → `track()` is a no-op; no `DATA_EMAIL` →
  waitlist widget hides itself. A fresh copy of this kit is inert until configured.
- GA4 property creation is free: analytics.google.com → Admin → Create property.
  The Measurement ID is `G-XXXXXXXXXX`.
- The `search_*` events are the demand signal for the "is this niche worth it" question:
  high attempts + high errors = people want it but it's broken (fix backend);
  low attempts = people aren't finding the page (SEO/sharing problem).
