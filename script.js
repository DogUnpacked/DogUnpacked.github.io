/**
 * Dog Unpacked — hub page enhancements (plain JS, no framework, no cookies).
 *
 *  1. Cookie-free analytics (GoatCounter): page view, platform clicks, signup, Latest clicks
 *  2. Breed-aware page via ?breed=<slug> (edition, photo or type plate, verified ATTS line)
 *  3. Newsletter (The Sniff Test): Title-Case the optional breed, submit to Kit in the background
 *     and show an inline success message (falls back to a normal form POST)
 *  4. Latest: renders data/latest.json (up to 3 long-form videos); click-to-load embed
 *  5. Contact form: validation, honeypot, background POST to Formspree, inline success/error
 *  6. Confirmed landing: ?confirmed=1 (Kit double opt-in redirect) -> "You're in." in the newsletter section
 *  7. Breed dial: pick a known breed, show the verified angle, keep ?breed= and utm_* in the URL
 *  8. Sticky mobile signup bar once the hero form leaves the screen
 *
 * The page works without this file: the Kit form still posts (Kit's hosted page confirms) and links work.
 */
(function () {
  "use strict";

  /* ------------------------------------------------------------------
   * CONFIG
   * ------------------------------------------------------------------ */

  // Contact form endpoint (Formspree form ID xeaeaajd). To switch forms, change only the ID after /f/.
  // Safety guard: if this ever holds a "{{...}}" placeholder, the form shows its error message and makes
  // no network call. The destination inbox is set in the Formspree dashboard, never in this repo.
  var FORMSPREE_ENDPOINT = "https://formspree.io/f/xeaeaajd";

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

  // Photos that exist in images/breeds/. Src is never built from the query string.
  var BREED_PHOTOS = {
    "german-shepherd": { src: "images/breeds/german-shepherd-480.webp", w: 480, h: 600 },
    "pit-bull": { src: "images/breeds/pit-bull-480.webp", w: 480, h: 480 },
    "rottweiler": { src: "images/breeds/rottweiler-480.webp", w: 480, h: 480 },
    "doberman": { src: "images/breeds/doberman-480.webp", w: 480, h: 600 }
  };

  // Verified ATTS pass rates from the brand brief. A breed missing here gets no number.
  // Pit Bull uses the American Pit Bull Terrier sample. Husky has a rate and no sample size.
  var BREED_STATS = {
    "german-shepherd": "American Temperament Test Society. German Shepherds: 85.7% pass rate, 3,500 dogs.",
    "rottweiler": "American Temperament Test Society. Rottweilers: 85.0% pass rate, 6,216 dogs.",
    "doberman": "American Temperament Test Society. Dobermans: 80.1% pass rate, 1,870 dogs.",
    "pit-bull": "American Temperament Test Society. American Pit Bull Terriers: 87.6% pass rate, 960 dogs.",
    "golden-retriever": "American Temperament Test Society. Golden Retrievers: 85.9% pass rate, 836 dogs.",
    "husky": "American Temperament Test Society. Huskies: 86.7% pass rate."
  };

  function personalizeBreed(name) {
    var slug = slugify(name);
    document.documentElement.setAttribute("data-breed", slug);

    var kicker = document.getElementById("hero-kicker");
    if (kicker) kicker.textContent = name;

    var grid = document.getElementById("breed-grid");
    var caption = document.getElementById("visual-caption");
    var photo = BREED_PHOTOS[slug];
    var fig = document.getElementById("breed-feature");
    var plate = document.getElementById("breed-plate");
    if (photo) {
      var img = document.getElementById("breed-feature-img");
      var cap = document.getElementById("breed-feature-cap");
      if (fig && img) {
        img.width = photo.w;
        img.height = photo.h;
        img.alt = "";
        img.decoding = "async";
        img.loading = window.matchMedia && window.matchMedia("(min-width: 960px)").matches ? "eager" : "lazy";
        img.src = photo.src;
        if (cap) cap.textContent = name;
        fig.hidden = false;
      }
      if (plate) plate.hidden = true;
      if (grid) grid.hidden = true;
      if (caption) caption.hidden = true;
    } else {
      var plateName = document.getElementById("breed-plate-name");
      if (plate && plateName) {
        plateName.textContent = name;
        plate.hidden = false;
      }
      if (fig) fig.hidden = true;
      if (grid) grid.hidden = true;
      if (caption) caption.hidden = true;
    }

    var stat = BREED_STATS[slug];
    var statWrap = document.getElementById("breed-stat");
    var statText = document.getElementById("breed-stat-text");
    if (stat && statWrap && statText) {
      statText.textContent = stat;
      statWrap.hidden = false;
    } else if (statWrap) {
      if (statText) statText.textContent = "";
      statWrap.hidden = true;
    }

    var filesNote = document.getElementById("files-breed-note");
    if (filesNote) {
      filesNote.textContent = slug === "german-shepherd"
        ? "This one is for your German Shepherd."
        : slug === "mixed-breed"
          ? "The next File is chosen from what readers ask for. That includes mixed breeds."
          : "The next File is chosen from what readers ask for. That includes your " + name + ".";
      filesNote.hidden = false;
    }
  }

  var SUCCESS_MESSAGE = "Check your inbox — one click to confirm and you're in.";
  var SUCCESS_SPAM_NOTE = "Not there in a few minutes? Check your spam or junk folder.";
  var CONFIRMED_TITLE = "You're in.";
  var CONFIRMED_MESSAGE = "The Sniff Test lands in your inbox every Sunday.";
  var ERROR_MESSAGE = "That didn't go through. Check your email address and try again.";

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

  // Same as track(), but for events fired before count.js has loaded (e.g. on page load):
  // queued and sent once the script is ready. Dropped silently if analytics never loads.
  var trackQueue = [];
  function trackWhenReady(path, title) {
    if (window.goatcounter && typeof window.goatcounter.count === "function") {
      track(path, title);
    } else {
      trackQueue.push([path, title]);
    }
  }

  /* ------------------------------------------------------------------
   * 1. GoatCounter (cookie-free). Page view is counted automatically by count.js.
   * ------------------------------------------------------------------ */
  function loadAnalytics() {
    if (!GOATCOUNTER_SITE) return;
    var s = document.createElement("script");
    s.async = true;
    s.onload = function () {
      while (trackQueue.length) {
        var ev = trackQueue.shift();
        track(ev[0], ev[1]);
      }
    };
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
    // Non-breaking spaces keep "— Pit Bull edition" together so it wraps as one unit.
    if (edition) edition.textContent = "\u00a0— " + name.replace(/ /g, "\u00a0") + "\u00a0edition";
    personalizeBreed(name);
  })();

  /* ------------------------------------------------------------------
   * 3. The Sniff Test signup form.
   *    Submits like Kit's own embed script (ck.5.js): POST FormData to the form action with
   *    Accept: application/json -> {"status":"success"} JSON (Kit allows CORS from any origin).
   *    Success -> inline message. Kit validation error -> inline error. Network/unknown failure ->
   *    normal form POST, which lands on Kit's hosted confirmation page.
   * ------------------------------------------------------------------ */
  var form = document.getElementById("newsletter-form");
  var statusEl = document.getElementById("form-status");

  function setStatus(text, kind, subText) {
    if (!statusEl) return;
    statusEl.textContent = text;
    statusEl.className = "form-note" + (kind ? " is-" + kind : "");
    if (subText) {
      var sub = document.createElement("span");
      sub.className = "form-note-sub";
      sub.textContent = subText;
      statusEl.appendChild(sub);
    }
  }

  if (form) {
    var submitting = false;
    var submitBtn = form.querySelector('button[type="submit"]');

    var fallbackPost = function () {
      HTMLFormElement.prototype.submit.call(form);
    };

    form.addEventListener("submit", function (e) {
      if (submitting) {
        e.preventDefault();
        return;
      }
      if (form.checkValidity && !form.checkValidity()) return; // browser shows messages

      var breed = breedInput ? breedName(breedInput.value) : "";
      if (breedInput) {
        breedInput.value = breed;
        breedInput.disabled = !breed; // blank breed: leave fields[breed] out of the post
      }
      track(breed ? "subscribe-" + slugify(breed) : "subscribe-none", "The Sniff Test signup: " + (breed || "none"));

      if (!window.fetch || !window.FormData) {
        return; // old browser: let the normal POST happen
      }
      e.preventDefault();
      submitting = true;
      if (submitBtn) submitBtn.disabled = true;
      setStatus("Sending…");

      var data = new FormData(form);
      if (breedInput) breedInput.disabled = false;

      fetch(form.action, {
        method: "POST",
        body: data,
        headers: { Accept: "application/json", "X-CKJS-Version": "6" }
      })
        .then(function (res) {
          return res.json().then(
            function (json) { return { ok: res.ok, json: json }; },
            function () { return { ok: res.ok, json: null }; }
          );
        })
        .then(function (r) {
          var json = r.json || {};
          if (r.ok && (json.status === "success" || r.json === null)) {
            form.hidden = true;
            var privacy = document.querySelector(".form-privacy");
            if (privacy) privacy.hidden = true;
            setStatus(SUCCESS_MESSAGE, "success", SUCCESS_SPAM_NOTE);
            return;
          }
          if (r.ok && json.status === "quarantined" && json.url) {
            window.location.href = json.url; // Kit's spam check page
            return;
          }
          if (json.errors) {
            submitting = false;
            if (submitBtn) submitBtn.disabled = false;
            setStatus(ERROR_MESSAGE, "error");
            return;
          }
          fallbackPost();
        })
        .catch(function () {
          fallbackPost();
        });
    });

    // Back button (bfcache): allow a fresh submit.
    window.addEventListener("pageshow", function () {
      submitting = false;
      if (submitBtn) submitBtn.disabled = false;
      if (breedInput) breedInput.disabled = false;
    });
  }

  /* ------------------------------------------------------------------
   * 6. Confirmed landing: Kit's double opt-in redirects confirmed subscribers to /?confirmed=1.
   *    Replaces the signup form with "You're in." (same treatment as the success state), scrolls the
   *    newsletter section into view, fires subscribe_confirmed once, then drops confirmed=1 from the URL
   *    (other params like ?breed= and utm_* stay) so a refresh or a shared link shows the normal page.
   * ------------------------------------------------------------------ */
  (function confirmedLanding() {
    var params;
    try {
      params = new URLSearchParams(window.location.search);
    } catch (e) {
      return;
    }
    if (params.get("confirmed") !== "1") return;

    var section = document.getElementById("subscribe");
    if (form) form.hidden = true;
    var privacy = document.querySelector(".form-privacy");
    if (privacy) privacy.hidden = true;
    if (statusEl) {
      statusEl.textContent = "";
      statusEl.className = "form-note is-confirmed";
      var title = document.createElement("span");
      title.className = "form-note-title";
      title.textContent = CONFIRMED_TITLE;
      statusEl.appendChild(title);
      statusEl.appendChild(document.createTextNode(CONFIRMED_MESSAGE));
    }

    trackWhenReady("subscribe_confirmed", "The Sniff Test: subscription confirmed");

    try {
      params.delete("confirmed");
      var qs = params.toString();
      window.history.replaceState(window.history.state, "", window.location.pathname + (qs ? "?" + qs : "") + window.location.hash);
    } catch (e) {
      /* URL stays as is; nothing else depends on it */
    }

    if (section && section.scrollIntoView) {
      section.scrollIntoView({ block: "start" });
      // Fonts/images can shift layout before "load"; settle on the section once more then.
      if (document.readyState !== "complete") {
        window.addEventListener("load", function () {
          section.scrollIntoView({ block: "start" });
        });
      }
    }
  })();

  /* ------------------------------------------------------------------
   * 4. Latest — data/latest.json: [{ "id", "title", "published" }, ...] newest first (max 3).
   *    First = 16:9 click-to-load embed (no iframe until click). Next two = small linked cards.
   * ------------------------------------------------------------------ */
  var PLAY_SVG =
    '<svg viewBox="0 0 68 48" width="68" height="48"><path d="M66.5 7.7a8.5 8.5 0 0 0-6-6C55.2.3 34 .3 34 .3s-21.2 0-26.5 1.4a8.5 8.5 0 0 0-6 6C.1 13 .1 24 .1 24s0 11 1.4 16.3a8.5 8.5 0 0 0 6 6C12.8 47.7 34 47.7 34 47.7s21.2 0 26.5-1.4a8.5 8.5 0 0 0 6-6C67.9 35 67.9 24 67.9 24s0-11-1.4-16.3z" fill="#b3261e"/><path d="M27 34V14l18 10z" fill="#fff"/></svg>';
  var VIDEO_ID = /^[A-Za-z0-9_-]{11}$/;
  var MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

  function formatPublished(value) {
    if (typeof value !== "string") return "";
    var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
    if (!m) return "";
    var month = MONTHS[Number(m[2]) - 1];
    if (!month) return "";
    return month + " " + Number(m[3]) + ", " + m[1];
  }

  function appendDate(parent, published) {
    var label = formatPublished(published);
    if (!label) return;
    var time = document.createElement("time");
    time.className = "latest-date";
    time.dateTime = published;
    time.textContent = label;
    parent.appendChild(time);
  }

  function thumb(id, w, h, lazy) {
    var img = document.createElement("img");
    img.src = "https://i.ytimg.com/vi/" + id + "/hqdefault.jpg";
    img.alt = "";
    img.width = w;
    img.height = h;
    if (lazy) img.loading = "lazy";
    img.decoding = "async";
    return img;
  }

  function renderLatest(list) {
    var latest = document.getElementById("latest");
    var lite = document.getElementById("latest-video");
    var more = document.getElementById("latest-more");
    if (!latest || !lite || !Array.isArray(list)) return;
    var videos = list.filter(function (v) {
      return v && typeof v.id === "string" && VIDEO_ID.test(v.id);
    }).slice(0, 3);
    if (!videos.length) return;

    // Newest: lite embed
    var first = videos[0];
    var title = typeof first.title === "string" ? first.title : "Latest Dog Unpacked video";
    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "lite-yt-btn";
    btn.setAttribute("aria-label", "Play: " + title);
    btn.appendChild(thumb(first.id, 480, 360, true));
    var play = document.createElement("span");
    play.className = "lite-yt-play";
    play.setAttribute("aria-hidden", "true");
    play.innerHTML = PLAY_SVG;
    btn.appendChild(play);
    btn.addEventListener("click", function () {
      track("latest_click-" + first.id, "Latest: " + title);
      var iframe = document.createElement("iframe");
      iframe.src = "https://www.youtube-nocookie.com/embed/" + first.id + "?autoplay=1&rel=0";
      iframe.title = title;
      iframe.allow = "accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share";
      iframe.allowFullscreen = true;
      iframe.referrerPolicy = "strict-origin-when-cross-origin";
      lite.innerHTML = "";
      lite.appendChild(iframe);
    });
    lite.appendChild(btn);

    var meta = document.createElement("div");
    meta.className = "latest-meta";
    var heading = document.createElement("h3");
    heading.className = "latest-title";
    heading.textContent = title;
    meta.appendChild(heading);
    appendDate(meta, first.published);
    lite.insertAdjacentElement("afterend", meta);

    // Previous two: small cards
    if (more && videos.length > 1) {
      videos.slice(1).forEach(function (v) {
        var vTitle = typeof v.title === "string" ? v.title : "Watch on YouTube";
        var li = document.createElement("li");
        var a = document.createElement("a");
        a.className = "latest-card";
        a.href = "https://www.youtube.com/watch?v=" + v.id;
        a.target = "_blank";
        a.rel = "noopener noreferrer";
        a.addEventListener("click", function () {
          track("latest_click-" + v.id, "Latest: " + vTitle);
        });
        a.appendChild(thumb(v.id, 480, 360, true));
        var span = document.createElement("span");
        span.className = "latest-card-title";
        span.textContent = vTitle;
        a.appendChild(span);
        appendDate(a, v.published);
        var tab = document.createElement("span");
        tab.className = "visually-hidden";
        tab.textContent = " (opens in a new tab)";
        a.appendChild(tab);
        li.appendChild(a);
        more.appendChild(li);
      });
      more.hidden = false;
    }
    latest.hidden = false;
  }

  if (window.fetch) {
    fetch("data/latest.json", { cache: "no-cache" })
      .then(function (res) {
        if (!res.ok) throw new Error("HTTP " + res.status);
        return res.json();
      })
      .then(renderLatest)
      .catch(function () {
        /* missing or broken JSON: section stays hidden */
      });
  }
  /* ------------------------------------------------------------------
   * 5. Contact form -> Formspree (fetch POST, Accept: application/json).
   *    Order on submit: validate (name, email, topic, message) -> honeypot (filled = show success, send nothing) ->
   *    placeholder endpoint (show error, no network call) -> POST.
   * ------------------------------------------------------------------ */
  var CONTACT_SUCCESS = "Got it. Replies come from Dog Unpacked within a few days.";
  var CONTACT_ERROR = "Didn't send \u2014 try again or reach us on any platform above.";
  var CONTACT_FIELD_ERRORS = {
    name: "Enter your name.",
    email: "Enter a valid email address.",
    topic: "Choose a topic.",
    message: "Write a message."
  };

  var contactForm = document.getElementById("contact-form");
  if (contactForm) {
    var cStatus = document.getElementById("contact-status");
    var cSubmit = document.getElementById("contact-submit");
    var cName = document.getElementById("contact-name");
    var cEmail = document.getElementById("contact-email");
    var cTopic = document.getElementById("contact-topic");
    var cMessage = document.getElementById("contact-message");
    var cWebsite = document.getElementById("contact-website");
    var cCount = document.getElementById("contact-count-n");
    var cSending = false;
    var EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

    if (cSubmit) cSubmit.disabled = false; // disabled in the HTML so the form can't post without JS

    var setContactStatus = function (text, kind) {
      if (!cStatus) return;
      cStatus.textContent = text;
      cStatus.className = "form-note" + (kind ? " is-" + kind : "");
    };

    var fieldError = function (input, key, show) {
      var err = document.getElementById(input.id + "-error");
      input.setAttribute("aria-invalid", show ? "true" : "false");
      if (err) {
        err.textContent = show ? CONTACT_FIELD_ERRORS[key] : "";
        err.hidden = !show;
      }
    };

    var checks = [
      [cName, "name", function (v) { return v.trim().length > 0; }],
      [cEmail, "email", function (v) { return EMAIL_RE.test(v.trim()); }],
      [cTopic, "topic", function (v) { return v !== ""; }],
      [cMessage, "message", function (v) { return v.trim().length > 0 && v.length <= 1000; }]
    ];

    var validate = function () {
      var firstBad = null;
      checks.forEach(function (c) {
        var ok = c[2](c[0].value);
        fieldError(c[0], c[1], !ok);
        if (!ok && !firstBad) firstBad = c[0];
      });
      if (firstBad) firstBad.focus();
      return !firstBad;
    };

    // Clear a field's error as soon as it becomes valid ("change" covers the topic select).
    checks.forEach(function (c) {
      var clear = function () {
        if (c[0].getAttribute("aria-invalid") === "true" && c[2](c[0].value)) fieldError(c[0], c[1], false);
      };
      c[0].addEventListener("input", clear);
      c[0].addEventListener("change", clear);
    });

    if (cMessage && cCount) {
      var updateCount = function () { cCount.textContent = String(cMessage.value.length); };
      cMessage.addEventListener("input", updateCount);
      updateCount();
    }

    var contactDone = function () {
      contactForm.hidden = true;
      setContactStatus(CONTACT_SUCCESS, "success");
    };

    var contactFail = function () {
      cSending = false;
      if (cSubmit) cSubmit.disabled = false;
      setContactStatus(CONTACT_ERROR, "error");
    };

    contactForm.addEventListener("submit", function (e) {
      e.preventDefault();
      if (cSending) return;
      setContactStatus("");
      if (!validate()) return;

      var topicValue = cTopic.value;
      var topicText = cTopic.options[cTopic.selectedIndex].text; // validate() guarantees a real topic

      // Honeypot filled: almost certainly a bot. Pretend it worked; send nothing.
      if (cWebsite && cWebsite.value) {
        contactDone();
        return;
      }

      track("contact_submit-" + topicValue, "Contact: " + topicText);

      // Endpoint not configured yet: error state, no network call.
      if (FORMSPREE_ENDPOINT.indexOf("{{") !== -1 || !window.fetch || !window.FormData) {
        contactFail();
        return;
      }

      cSending = true;
      if (cSubmit) cSubmit.disabled = true;
      setContactStatus("Sending\u2026");

      var data = new FormData();
      data.append("name", cName.value.trim());
      data.append("email", cEmail.value.trim());
      data.append("topic", topicText);
      data.append("message", cMessage.value);
      data.append("_subject", "Dog Unpacked contact \u2014 " + topicText);
      data.append("_gotcha", cWebsite ? cWebsite.value : ""); // Formspree discards non-empty _gotcha server-side

      fetch(FORMSPREE_ENDPOINT, {
        method: "POST",
        body: data,
        headers: { Accept: "application/json" }
      })
        .then(function (res) {
          if (res.ok) contactDone();
          else contactFail();
        })
        .catch(contactFail);
    });
  }

  /* ------------------------------------------------------------------
   * 7. Breed dial. Same known breeds as the form. A figure only when BREED_STATS has one.
   *    Photo src only from BREED_PHOTOS. Click updates the hero, the form, and the URL
   *    without dropping utm_*. No-JS visitors follow the real ?breed= links.
   * ------------------------------------------------------------------ */
  (function breedDial() {
    var picks = document.getElementById("dial-picks");
    var stage = document.getElementById("dial-stage");
    if (!picks || !stage) return;

    var empty = document.getElementById("dial-empty");
    var result = document.getElementById("dial-result");
    var figure = document.getElementById("dial-figure");
    var photo = document.getElementById("dial-photo");
    var cap = document.getElementById("dial-cap");
    var nameEl = document.getElementById("dial-name");
    var statEl = document.getElementById("dial-stat");
    var noteEl = document.getElementById("dial-note");
    var edition = document.getElementById("breed-edition");
    var NO_STAT = "No verified figure for this breed on this page. The letter still starts from him: one behavior, one job, one study.";
    var STAT_NOTE = "A pass rate is a number, not a verdict. You decide what it means.";

    function paint(slug, name, animate) {
      var apply = function () {
        if (empty) empty.hidden = true;
        if (result) result.hidden = false;
        if (nameEl) nameEl.textContent = name;
        var shot = BREED_PHOTOS[slug];
        if (shot && figure && photo) {
          photo.width = shot.w;
          photo.height = shot.h;
          photo.alt = "";
          photo.src = shot.src;
          if (cap) cap.textContent = name;
          figure.hidden = false;
        } else if (figure) {
          figure.hidden = true;
          if (photo) photo.removeAttribute("src");
        }
        var stat = BREED_STATS[slug];
        if (stat && statEl) {
          statEl.textContent = stat;
          statEl.hidden = false;
          if (noteEl) noteEl.textContent = STAT_NOTE;
        } else {
          if (statEl) {
            statEl.textContent = "";
            statEl.hidden = true;
          }
          if (noteEl) noteEl.textContent = NO_STAT;
        }
      };

      var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      if (animate && !reduce && typeof document.startViewTransition === "function") {
        document.startViewTransition(apply);
      } else {
        apply();
      }
    }

    function findPick(slug) {
      var buttons = picks.querySelectorAll(".dial-pick");
      for (var i = 0; i < buttons.length; i++) {
        if (buttons[i].getAttribute("data-dial") === slug) return buttons[i];
      }
      return null;
    }

    function selectDial(slug, fromUrl) {
      var link = findPick(slug);
      if (!link) return;
      var name = link.textContent.replace(/\s+/g, " ").trim();
      var buttons = picks.querySelectorAll(".dial-pick");
      for (var i = 0; i < buttons.length; i++) {
        if (buttons[i] === link) buttons[i].setAttribute("aria-current", "true");
        else buttons[i].removeAttribute("aria-current");
      }
      if (breedInput) breedInput.value = name;
      if (edition) edition.textContent = "\u00a0— " + name.replace(/ /g, "\u00a0") + "\u00a0edition";
      personalizeBreed(name);
      paint(slug, name, !fromUrl);
      if (fromUrl) return;
      try {
        var params = new URLSearchParams(window.location.search);
        params.set("breed", slug);
        params.delete("confirmed");
        var qs = params.toString();
        window.history.replaceState(window.history.state, "", window.location.pathname + (qs ? "?" + qs : "") + window.location.hash);
      } catch (e) {
        /* the panel still updated */
      }
    }

    picks.addEventListener("click", function (e) {
      var link = e.target.closest ? e.target.closest("a.dial-pick") : null;
      if (!link || !picks.contains(link)) return;
      e.preventDefault();
      selectDial(link.getAttribute("data-dial"), false);
    });

    var current = document.documentElement.getAttribute("data-breed");
    if (current) selectDial(current, true);
  })();

  /* ------------------------------------------------------------------
   * 8. Sticky signup on small screens, only after the hero form has scrolled away,
   *    and never over the contact form, the footer, or a finished signup.
   * ------------------------------------------------------------------ */
  (function stickySignup() {
    var bar = document.getElementById("sticky-cta");
    var subscribe = document.getElementById("subscribe");
    if (!bar || !subscribe || !("IntersectionObserver" in window)) return;

    var contact = document.getElementById("contact");
    var footer = document.getElementById("footer");
    var subscribeIn = true;
    var blocking = {};

    function sync() {
      var formHidden = !!(form && form.hidden);
      var blocked = !!(blocking.contact || blocking.footer);
      bar.hidden = subscribeIn || blocked || formHidden;
    }

    new IntersectionObserver(function (entries) {
      subscribeIn = entries[0].isIntersecting;
      sync();
    }).observe(subscribe);

    if (contact || footer) {
      var blockObs = new IntersectionObserver(function (entries) {
        for (var i = 0; i < entries.length; i++) blocking[entries[i].target.id] = entries[i].isIntersecting;
        sync();
      }, { rootMargin: "0px 0px 88px 0px" });
      if (contact) blockObs.observe(contact);
      if (footer) blockObs.observe(footer);
    }

    if (form && window.MutationObserver) {
      new MutationObserver(sync).observe(form, { attributes: true, attributeFilter: ["hidden"] });
    }
    sync();
  })();
})();
