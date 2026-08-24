/*
 * track.js — modular analytics kernel for utility sites.
 *
 * Drop into ANY tool site:
 *   <script src="common/track.js" data-ga="G-XXXXXXX"></script>
 *
 * - No GA ID (or data-ga="" )  -> fully no-op, zero cost, zero network.
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
})();