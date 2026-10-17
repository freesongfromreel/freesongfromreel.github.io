/*
 * track.js — modular analytics kernel for utility sites.
 *
 * Drop into ANY tool site:
 *   <script src="common/track.js" data-ga="G-XXXXXXX"></script>
 *
 * - No GA ID (or data-ga="G-NMDXLM3Z2J" )  -> fully no-op, zero cost, zero network.
 * - With a GA4 ID               -> loads gtag lazily, fires page_view once,
 *                                  exposes window.track(name, params).
 * - Privacy-first: visitor id in localStorage, no cookies.
 */
(function () {
  var script = document.currentScript || {};
  var gaId = (script.getAttribute && script.getAttribute("data-ga")) || "";
  var enabled = /^(G|GT|UA)-/.test(gaId);

  var cid = localStorage.getItem("visitor_id");
  if (!cid) {
    cid = "v-" + Math.random().toString(36).slice(2) + Date.now().toString(36);
    try { localStorage.setItem("visitor_id", cid); } catch (e) {}
  }

  var loaded = false;
  function loadGtag() {
    if (loaded) return;
    loaded = true;
    var s = document.createElement("script");
    s.async = true;
    s.src = "https://www.googletagmanager.com/gtag/js?id=" + encodeURIComponent(gaId);
    document.head.appendChild(s);
    window.dataLayer = window.dataLayer || [];
    window.gtag = function () { window.dataLayer.push(arguments); };
    window.gtag("js", new Date());
    window.gtag("config", gaId, { client_id: cid, send_page_view: false });
  }

  window.track = function (name, params) {
    if (!enabled) return;
    try {
      loadGtag();
      var p = params || {};
      p.client_id = cid;
      window.gtag("event", name, p);
    } catch (e) { /* never break the page for analytics */ }
  };

  function onReady(fn) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", fn);
    } else {
      fn();
    }
  }
  onReady(function () {
    if (enabled) window.track("page_view");
  });

  /* Optional delegated click catcher for links/CTAs: enable per-page with
     data-capture="1" on this script tag. Fires a semantic event per click and
     skips elements with an inline onclick (explicit handlers win).
     Events: nav_click, blog_post_click, sample_click, retry_click, apk_click,
     bmc_click, anchor_click, link_click, plus any data-track="name" override. */
  var CAPTURE = /(?:^|\s)data-capture=/.test(script.outerHTML) || script.getAttribute("data-capture") === "1";
  if (CAPTURE) {
    document.addEventListener("click", function (ev) {
      var t = ev.target;
      var a = t && t.closest ? t.closest("a") : null;
      if (!a || !window.track) return;
      if (a.getAttribute("onclick")) return; // explicit inline tracking wins
      var href = a.getAttribute("href") || "";
      var label = (a.getAttribute("aria-label") || a.textContent || "").trim().slice(0, 40) || href;
      var dt = a.getAttribute("data-track");
      if (dt) { window.track(dt, { label: label, dest: href }); return; }
      if (a.closest(".navlinks")) { window.track("nav_click", { dest: href, page: location.pathname }); return; }
      if (a.classList.contains("card")) { window.track("blog_post_click", { post: href }); return; }
      if (a.classList.contains("retry")) { window.track("retry_click", {}); return; }
      if (/\?track=/.test(href) || /verify\.html/.test(href)) { window.track("sample_click", {}); return; }
      if (/\.apk/.test(href) || a.hasAttribute("download")) { window.track("apk_click", {}); return; }
      if (/buymeacoffee/.test(href)) { window.track("bmc_click", {}); return; }
      if (/^#/.test(href)) { window.track("anchor_click", { dest: href }); return; }
      window.track("link_click", { dest: href, page: location.pathname });
    });
  }
})();