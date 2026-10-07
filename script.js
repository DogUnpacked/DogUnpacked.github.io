/**
 * Dog Unpacked — hub page enhancements (plain JS, no framework, no cookies).
 *
 *  1. Cookie-free analytics (GoatCounter): page view, platform clicks, The Sniff Test signup
 *  2. Breed-aware page via ?breed=<slug>
 *  3. Newsletter (The Sniff Test): Title-Case the optional breed before posting to Kit
 *  4. Latest video: shown only when #latest has a data-video-id; click-to-load embed
 *
 * The page works without this file: the Kit form still posts and all links work.
 */
(function () {
  "use strict";

  /* ------------------------------------------------------------------
   * CONFIG
   * ------------------------------------------------------------------ */

  // GoatCounter site code: https://<code>.goatcounter.com (create the account first).
  // Set to "" to disable analytics entirely.
  var GOATCOUNTER_SITE = "dogunpacked";

  // ?breed= shortcuts. Anything else: hyphens -> spaces, Title Case.
  var BREED_OVERRIDES = {
    gsd: "German Shepherd",
    pitbull: "Pit Bull",
    corso: "Cane Corso",
    dobie: "Doberman"
  };

  /* ------------------------------------------------------------------
   * Helpers
   * ------------------------------------------------------------------ */

  function titleCase(str) {
    return String(str)
      .toLowerCase()
      .replace(/\s+/g, " ")
      .trim()
      .replace(/(^|[\s\-'])([a-z])/g, function (m, sep, ch) {
        return sep + ch.toUpperCase();
      });
  }

  // Display name for a typed breed or a slug ("pit-bull", "gsd", "golden retriever").
  function breedName(value) {
    var key = String(value).toLowerCase().replace(/[\s\-]+/g, "");
    if (!key) return "";
    if (Object.prototype.hasOwnProperty.call(BREED_OVERRIDES, key)) {
      return BREED_OVERRIDES[key];
    }
    if (key === "mixedbreed") return "Mixed breed"; // keep datalist casing
    return titleCase(String(value).replace(/-/g, " "));
  }

  function slugify(name) {
    return String(name).toLowerCase().trim().replace(/[^a-z]+/g, "-").replace(/^-+|-+$/g, "");
  }

  // Analytics event. Safe no-op if GoatCounter is blocked or not loaded yet.
  function track(path, title) {
    try {
      if (window.goatcounter && typeof window.goatcounter.count === "function") {
        window.goatcounter.count({ path: path, title: title || path, event: true });
      }
    } catch (e) {
      /* never let analytics break the page */
    }
  }

  /* ------------------------------------------------------------------
   * 1. GoatCounter (cookie-free). Page view is counted automatically by count.js.
   * ------------------------------------------------------------------ */
  function loadAnalytics() {
    if (!GOATCOUNTER_SITE) return;
    var s = document.createElement("script");
    s.async = true;
    s.src = "https://gc.zgo.at/count.js";
    s.setAttribute("data-goatcounter", "https://" + GOATCOUNTER_SITE + ".goatcounter.com/count");
    document.body.appendChild(s);
  }
  if (document.readyState === "complete") {
    loadAnalytics();
  } else {
    window.addEventListener("load", loadAnalytics);
  }

  // Platform button clicks: elements with data-track="<platform>" -> event "outbound-<platform>".
  document.addEventListener("click", function (e) {
    var el = e.target.closest ? e.target.closest("[data-track]") : null;
    if (!el) return;
    var name = el.getAttribute("data-track");
    track("outbound-" + name, "Outbound: " + name);
  });

  /* ------------------------------------------------------------------
   * 2. Breed-aware page: ?breed=<lowercase-hyphenated-slug> (known breeds only)
   * ------------------------------------------------------------------ */
  var breedInput = document.getElementById("breed");
  (function breedAware() {
    var raw;
    try {
      raw = new URLSearchParams(window.location.search).get("breed");
    } catch (e) {
      return;
    }
    if (!raw) return;
    var slug = raw.trim().toLowerCase();
    // Sanitize: letters and single hyphens only, sensible length. Anything else -> default page.
    if (!/^[a-z]+(-[a-z]+)*$/.test(slug) || slug.length > 40) return;

    var name = breedName(slug);
    // Only known breeds (the #breed-list datalist + aliases above) get an edition heading, so a
    // crafted link can't put arbitrary words on the page. Unknown slug -> default page.
    var known = {};
    var opts = document.querySelectorAll("#breed-list option");
    for (var i = 0; i < opts.length; i++) known[slugify(opts[i].value)] = true;
    if (!known[slugify(name)]) return;

    if (breedInput && !breedInput.value) breedInput.value = name;

    var edition = document.getElementById("breed-edition");
    if (edition) edition.textContent = " — " + name + " edition";
  })();

  /* ------------------------------------------------------------------
   * 3. The Sniff Test signup form: normalize the optional breed, count the event, post to Kit.
   * ------------------------------------------------------------------ */
  var form = document.getElementById("newsletter-form");
  var statusEl = document.getElementById("form-status");
  if (form) {
    var submitting = false;
    form.addEventListener("submit", function (e) {
      if (submitting) return;
      if (form.checkValidity && !form.checkValidity()) return; // browser shows messages
      e.preventDefault();
      submitting = true;

      var breed = breedInput ? breedName(breedInput.value) : "";
      if (breedInput) {
        breedInput.value = breed;
        // Blank breed: leave fields[breed] out of the post entirely.
        breedInput.disabled = !breed;
      }
      if (statusEl) {
        statusEl.textContent = "Sending…";
        statusEl.className = "form-note";
      }
      track(breed ? "subscribe-" + slugify(breed) : "subscribe-none", "The Sniff Test signup: " + (breed || "no breed"));
      // Short pause so the analytics beacon can leave before the page navigates to Kit.
      window.setTimeout(function () {
        HTMLFormElement.prototype.submit.call(form);
      }, 150);
    });
    // Back button (bfcache): allow a fresh submit.
    window.addEventListener("pageshow", function () {
      submitting = false;
      if (breedInput) breedInput.disabled = false;
      if (statusEl) statusEl.textContent = "";
    });
  }

  /* ------------------------------------------------------------------
   * 4. Latest video — lite YouTube embed. ID lives in index.html: <section id="latest" data-video-id="...">
   * ------------------------------------------------------------------ */
  var latest = document.getElementById("latest");
  var lite = document.getElementById("latest-video");
  if (latest && lite) {
    var id = (latest.getAttribute("data-video-id") || "").trim();
    if (/^[A-Za-z0-9_-]{11}$/.test(id)) {
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "lite-yt-btn";
      btn.setAttribute("aria-label", "Play the latest Dog Unpacked video");

      var img = document.createElement("img");
      img.src = "https://i.ytimg.com/vi/" + id + "/hqdefault.jpg";
      img.alt = "";
      img.width = 480;
      img.height = 360;
      img.loading = "lazy";
      img.decoding = "async";
      btn.appendChild(img);

      var play = document.createElement("span");
      play.className = "lite-yt-play";
      play.setAttribute("aria-hidden", "true");
      play.innerHTML =
        '<svg viewBox="0 0 68 48" width="68" height="48"><path d="M66.5 7.7a8.5 8.5 0 0 0-6-6C55.2.3 34 .3 34 .3s-21.2 0-26.5 1.4a8.5 8.5 0 0 0-6 6C.1 13 .1 24 .1 24s0 11 1.4 16.3a8.5 8.5 0 0 0 6 6C12.8 47.7 34 47.7 34 47.7s21.2 0 26.5-1.4a8.5 8.5 0 0 0 6-6C67.9 35 67.9 24 67.9 24s0-11-1.4-16.3z" fill="#b3261e"/><path d="M27 34V14l18 10z" fill="#fff"/></svg>';
      btn.appendChild(play);

      btn.addEventListener("click", function () {
        var iframe = document.createElement("iframe");
        iframe.src = "https://www.youtube-nocookie.com/embed/" + id + "?autoplay=1&rel=0";
        iframe.title = "Latest Dog Unpacked video";
        iframe.allow = "accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share";
        iframe.allowFullscreen = true;
        iframe.referrerPolicy = "strict-origin-when-cross-origin";
        lite.innerHTML = "";
        lite.appendChild(iframe);
      });

      lite.appendChild(btn);
      latest.hidden = false;
    }
  }
})();
