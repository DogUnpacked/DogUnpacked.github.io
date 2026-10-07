/**
 * Dog Unpacked — hub page enhancements (plain JS, no framework, no cookies).
 *
 *  1. Cookie-free analytics (GoatCounter) + click/submit events
 *  2. Breed-aware page via ?breed=<slug>
 *  3. Newsletter: Title-Case the breed before posting to Kit
 *  4. Latest video: click-to-load YouTube embed (no iframe until click)
 *  5. Hide "needs-url" elements whose link is still a {{PLACEHOLDER}}
 *
 * The page works without this file: the Kit form still posts and all links work.
 */
(function () {
  "use strict";

  /* ------------------------------------------------------------------
   * CONFIG — the only values you should need to edit here.
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
    if (Object.prototype.hasOwnProperty.call(BREED_OVERRIDES, key)) {
      return BREED_OVERRIDES[key];
    }
    // "Mixed breed" keeps its datalist casing.
    if (key === "mixedbreed") return "Mixed breed";
    return titleCase(String(value).replace(/-/g, " "));
  }

  // Canonical slug for comparing a breed with guide cards: "German Shepherd" -> "german-shepherd".
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

  // Outbound / CTA clicks: any element with data-track="<event name>".
  document.addEventListener("click", function (e) {
    var el = e.target.closest ? e.target.closest("[data-track]") : null;
    if (!el) return;
    var name = el.getAttribute("data-track");
    if (name === "guide-notify") {
      track("guide-notify", "Guides: get notified");
    } else {
      track("outbound-" + name, "Outbound: " + name);
    }
  });

  /* ------------------------------------------------------------------
   * 5. Hide placeholder-only elements (CSS :has() also hides them; this is the fallback).
   * ------------------------------------------------------------------ */
  var needsUrl = document.querySelectorAll(".needs-url");
  for (var i = 0; i < needsUrl.length; i++) {
    var a = needsUrl[i].querySelector("a");
    if (a && a.getAttribute("href").indexOf("{{") !== -1) {
      needsUrl[i].hidden = true;
    }
  }

  /* ------------------------------------------------------------------
   * 2. Breed-aware page: ?breed=<lowercase-hyphenated-slug>
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

    if (breedInput && !breedInput.value) breedInput.value = name;

    var edition = document.getElementById("breed-edition");
    if (edition) edition.textContent = " — " + name + " edition";

    var list = document.getElementById("guide-list");
    if (list) {
      var target = slugify(name);
      var cards = list.querySelectorAll(".guide-card");
      for (var j = 0; j < cards.length; j++) {
        if (cards[j].getAttribute("data-breed") === target) {
          list.insertBefore(cards[j], list.firstElementChild);
          break;
        }
      }
    }
  })();

  /* ------------------------------------------------------------------
   * 3. Newsletter form: normalize breed, count the event, then post to Kit.
   * ------------------------------------------------------------------ */
  var form = document.getElementById("newsletter-form");
  var statusEl = document.getElementById("form-status");
  if (form) {
    var submitting = false;
    form.addEventListener("submit", function (e) {
      if (breedInput) breedInput.value = breedName(breedInput.value);
      if (submitting) return;
      if (form.checkValidity && !form.checkValidity()) return; // browser shows messages
      e.preventDefault();
      submitting = true;
      if (statusEl) {
        statusEl.textContent = "Sending…";
        statusEl.className = "form-note";
      }
      var breed = breedInput ? breedInput.value : "";
      track("subscribe-" + slugify(breed || "unknown"), "Newsletter: " + (breed || "unknown"));
      // Short pause so the analytics beacon can leave before the page navigates to Kit.
      window.setTimeout(function () {
        HTMLFormElement.prototype.submit.call(form);
      }, 150);
    });
    // Back button (bfcache): allow a fresh submit and clear the status line.
    window.addEventListener("pageshow", function () {
      submitting = false;
      if (statusEl) statusEl.textContent = "";
    });
  }

  /* ------------------------------------------------------------------
   * 4. Latest video — lite YouTube embed.
   * ------------------------------------------------------------------ */
  var lite = document.getElementById("latest-video");
  if (lite) {
    var id = lite.getAttribute("data-video-id") || "";
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
        lite.classList.add("is-playing");
        track("latest-video-play", "Latest video: play");
      });

      lite.innerHTML = "";
      lite.appendChild(btn);
      lite.classList.add("has-video");
    }
  }
})();
