# Dog Unpacked — hub page notes (`index.html`)

The hub page is the single link in every bio, and the place owned revenue starts. The primary action is The Sniff Test (free Sunday newsletter). YouTube subscribe and follows on TikTok and Instagram are the secondary actions. Brand scope: **every breed, one at a time**.

Live address: https://dogunpacked.com/ (custom domain on GitHub Pages, repo `DogUnpacked/DogUnpacked.github.io`, `main` branch root; DNS in Cloudflare, A records to GitHub Pages IPs plus `www` CNAME to `dogunpacked.github.io`, all DNS only). The old https://dogunpacked.github.io/ address redirects here.

## Section order

Sticky header (logo, wordmark, "Free newsletter" jump; Breeds and Contact from 840px) → hero (kicker, tagline as the H1, one-line promise, and the signup card) → platform row (YouTube, Instagram, TikTok — Facebook is not used) → one proof line (Morrill et al. 2022) → Find your breed (`#find-breed`: photo cards for breeds with a Dog Unpacked video or Short, then "See all 208 breeds" to `/breeds/`) → Latest (`#latest`, only when `data/latest.json` lists a video) → a short Coming soon note for Breed Files (`#guides`, no nav link) → Contact (`#contact`, Formspree form) → footer. On a phone, once the signup card scrolls out of view, a bar sticks to the bottom until the contact section or the footer is on screen, and it stays hidden after a signup. The bar names The Sniff Test as the free weekly email and its button says "Get the free newsletter".

On a 390×844 phone the email field, breed field, and "Get the free newsletter" button sit in the first screen, with the three platform buttons still in that screen. A `?breed=` visit keeps that order. It fills the breed field and the kicker. It does not swap photos.

## Newsletter signup (Kit)

Copy: eyebrow "Free weekly email" → heading "The Sniff Test" → "A free email every Sunday: one behavior, one job, one study, and what to do tonight." → "About a two-minute read." → button "Get the free newsletter" → "Free. Unsubscribe anytime." No badge and no "No spam." The document title is "Everything Dog Unpacked — He's not broken. He's bred that way." Issues run 250 to 400 words, so the page does not say "90 seconds."

Plain newsletter signup. Email is required. Breed is optional: it's saved to the subscriber's Kit custom field
`breed` and does **not** change the signup. Everyone gets the same Sunday issue of The Sniff Test.

- Posts to Kit form 10011711: `email_address`, `fields[breed]` (only when filled in, Title-Cased by
  `script.js`), `tags[]=24362096` (`source:landing`, backup for the form's own auto-tag setting).
- How success works: `script.js` submits the form in the background the same way Kit's own embed script
  does (`fetch` POST of the form data with `Accept: application/json`; Kit allows this from any site and answers
  `{"status":"success"}`). On success the form is replaced by "Check your inbox — one click to confirm and you're
  in." with a smaller, muted line under it: "Not there in a few minutes? Check your spam or junk folder." If Kit returns a validation error the visitor sees "That didn't go through. Check your email address and
  try again." If the request fails for any other reason (network, blocked, unexpected reply) the form falls back
  to a normal POST and Kit's hosted page confirms instead. If Kit ever flags a signup for its spam check
  (`"quarantined"`), the visitor is sent to Kit's check page.
- Without JS the form still posts normally (Kit's hosted page); a blank breed is then sent as an empty `fields[breed]`.
- Confirmed landing: Kit's double opt-in redirects confirmed subscribers to `https://dogunpacked.com/?confirmed=1`
  (set in Kit; no YouTube prompt, no redirect onward). With `confirmed=1` in the query string, `script.js` replaces the
  form with "You're in." (heading weight) and "The Sniff Test lands in your inbox every Sunday.", scrolls the
  newsletter section into view, fires the GoatCounter event `subscribe_confirmed` once, then removes `confirmed=1`
  from the address bar with `history.replaceState` (`?breed=` and `utm_*` stay), so a refresh or a shared link
  shows the normal page.
- Not yet tested end to end with a real inbox (planned). Local tests mocked Kit; nothing was sent to Kit.
- IDs and the remaining Kit dashboard steps: `KIT.md`.

## Placeholders / omitted until supplied

| Item | How to switch it on |
|---|---|
| Share image | Live: `images/og-image.png` (1200×630 logo card, absolute URL, `summary_large_image`). Replace that file when a box photo is ready and keep the same meta tags. |
| Kit success message | Kit's own form setting still says "…we'll send the File when it's ready." It only shows when JS is off or the background submit fails. Change it in the Kit dashboard (see `KIT.md`). |
| GoatCounter account | Live site code `dogunpackedcom` (`https://dogunpackedcom.goatcounter.com/count`). The counter tag sits just before `</body>` on every page. It uses no cookies. |

## Contact form (Formspree)

A compact card just above the footer replaces the old footer email line: no email address (business or personal)
appears anywhere on the page or in the repo. Messages go to the business inbox through Formspree.

- Copy: heading "Contact" → "Brands, partnerships, corrections, or a breed you want covered." → Name, Email, Topic
  (required; starts on a "Choose a topic" placeholder, then Brand / partnership, Request a breed, Correction, Other), Message (max 1000 characters, live counter) → button "Send".
  Success: "Got it. Replies come from Dog Unpacked within a few days." Error: "Didn't send — try again or reach us on
  any platform above." Field errors: "Enter your name." / "Enter a valid email address." / "Choose a topic." / "Write a message."
- `script.js` sends a background `fetch` POST to `FORMSPREE_ENDPOINT` with `Accept: application/json`. Fields sent:
  `name`, `email` (Formspree uses it as the reply-to), `topic` (the option text), `message`,
  `_subject` = "Dog Unpacked contact — <topic>", `_gotcha` (honeypot value, empty for humans).
- Honeypot: an off-screen `website` input (`aria-hidden`, `tabindex="-1"`, `autocomplete="off"`). If it is filled,
  the page shows the success message and sends nothing; `_gotcha` is the server-side backstop.
- The form needs JavaScript (the button is disabled in the HTML and enabled by `script.js`; a `<noscript>` line says
  "This form needs JavaScript. Reach us on any platform above."). There is no `action` attribute, so it can never post
  somewhere unexpected.
- GoatCounter event `contact_submit-<topic>` on every valid, non-honeypot submit.

**Plug in / change the Formspree form ID** — one line, near the top of `script.js`:

```js
var FORMSPREE_ENDPOINT = "https://formspree.io/f/xeaeaajd";
```

Replace only the ID after `/f/`. The destination inbox is set in the Formspree dashboard (form → Settings), never in
this repo. Guard: if the value ever contains a `{{...}}` placeholder, submits show the error message and make no
network call.

**Spam filtering (Formspree dashboard, form → Settings → Spam protection):**

- Formshield: on (already on for `xeaeaajd`). Start on Neutral; switch to Aggressive only if spam gets through.
- reCAPTCHA: must stay **off**. This form submits with `fetch` (AJAX), and Formspree's built-in reCAPTCHA breaks AJAX
  submits (every send would show the error message). Using reCAPTCHA would need our own reCAPTCHA key plus page code.
- Restrict to Domain (if the plan offers it): set `dogunpacked.com`. Formspree checks the Referer and sends
  submissions from anywhere else to spam. Update it if a custom domain is added.
- `_gotcha` (honeypot) needs no setup.

**Checklist before relying on it** (after deploy, from the live page):

- [ ] Submit one test message for each topic: Brand / partnership, Request a breed, Correction, Other.
- [ ] Confirm all four arrive at the business inbox with the right subject ("Dog Unpacked contact — <topic>") and
      that Reply goes to the sender's email.
- [ ] Confirm the honeypot discards: in devtools, set `document.getElementById('contact-website').value = 'x'`, submit,
      see the success message, and confirm nothing arrives (Network tab shows no request to formspree.io).
- [ ] Confirm the error state: offline (devtools → Network → Offline), submit, see "Didn't send — …".
- [ ] Check Formspree's submission count matches what you sent (free plan has a monthly limit).

## Latest video (`data/latest.json`)

`index.html` is never edited for a new video. `script.js` reads `data/latest.json`:

```json
[
  { "id": "tyUgyQCYGGA", "title": "Exact YouTube title", "published": "2026-09-22" }
]
```

Up to 3 long-form videos, newest first. The first shows as a click-to-load 16:9 thumbnail (no YouTube iframe
until the visitor clicks; the embed uses youtube-nocookie.com), with the title and `published` date under it.
The second and third show as small cards that open the YouTube watch page in a new tab. Fewer entries = fewer
cards. Empty list, missing file or broken JSON = the section stays hidden. Shorts never go in this file.

**Sunday update procedure** (after a new long-form video is live):

```bash
python3 scripts/update_latest_video.py --dry-run  # see what would change
python3 scripts/update_latest_video.py            # writes data/latest.json, or prints "Latest: no change"
git add data/latest.json && git commit -m "Latest: <video title>" && git push   # once hosting is connected
```

The script reads the channel RSS feed (channel id `UC_2f25vzJLiV799CfoHfDHA` = @DogUnpacked), skips Shorts
(`GET /shorts/<id>` without redirects: 200 = Short, redirect to /watch = long-form; falls back to the feed's own
`/shorts/` link if YouTube rate-limits the check) and anything 180 s or shorter, then merges what it finds with
the current file and keeps the 3 newest. Merging matters because the feed only holds the last ~15 uploads, so a
long-form video can drop out of it behind newer Shorts; it stays listed until 3 newer long-form videos exist.
`--rebuild` ignores the current file. It never commits. To change the list by hand, edit `data/latest.json`
directly (exact title, `YYYY-MM-DD` date).

## Bio links (UTM)

Platforms: YouTube, TikTok (`@dogsunpacked`), Instagram. Facebook is not used.

| Platform | Bio link |
|---|---|
| YouTube | `https://dogunpacked.com/?utm_source=youtube&utm_medium=bio` |
| TikTok | `https://dogunpacked.com/?utm_source=tiktok&utm_medium=bio` |
| Instagram | `https://dogunpacked.com/?utm_source=instagram&utm_medium=bio` |

Pinned comments / descriptions on a breed video combine breed + UTM:

| Use | Link |
|---|---|
| TikTok pinned comment, Pit Bull video | `https://dogunpacked.com/?breed=pit-bull&utm_source=tiktok&utm_medium=pin` |
| YouTube pinned comment, German Shepherd video | `https://dogunpacked.com/?breed=gsd&utm_source=youtube&utm_medium=pin` |
| YouTube description, Doberman video | `https://dogunpacked.com/?breed=dobie&utm_source=youtube&utm_medium=description` |
| Instagram story, Rottweiler | `https://dogunpacked.com/?breed=rottweiler&utm_source=instagram&utm_medium=story` |

GoatCounter's count.js sends the query string with each page view; GoatCounter uses `utm_source` / `ref` as the
referrer, so bio and pin traffic shows up per platform in its Referrers view.

## Breed-aware URLs (`?breed=`)

`?breed=<lowercase-hyphenated-slug>` pre-fills "Your dog's breed (optional)" and adds "— for your [Breed]" after "The Sniff Test". That line names his dog. It is the same Sunday letter for every breed, not a separate issue. The visitor can clear or edit the field.

Display name = hyphens become spaces, then Title Case. Shortcuts: `gsd` → German Shepherd, `pitbull` → American Pit Bull Terrier,
`corso` → Cane Corso, `dobie` → Doberman (`BREED_OVERRIDES` in `script.js`). Anything that isn't letters and
hyphens (or is over 40 characters) is ignored and the default page shows, with no error. Values are written with
`textContent` only. The query does not change any image `src`. No cookies, no storage. Only known breeds get the "for your" line: the 19 names in the
form's `#breed-list` datalist plus the aliases in `BREED_OVERRIDES` (`gsd`, `pitbull`, `corso`, `dobie`). An unknown
slug such as `?breed=xyz` shows the default page, so nobody can craft a link that puts arbitrary words in the
heading. To add a breed (e.g. `shiba-inu`), add an `<option value="Shiba Inu">` to the datalist in `index.html`.

For a known breed, `script.js` also sets the hero kicker to the breed name (default kicker: "Every breed, one at a time"). `?breed=pit-bull` and `?breed=pitbull` both use the name American Pit Bull Terrier. The Find your breed cards are ordinary links to `/breeds/<slug>/` and do not depend on the query. Pass rates live on the breed pages, not on this hub.

Pinned comments: add `&utm_source=<platform>&utm_medium=pin` to any breed URL below, e.g.
`https://dogunpacked.com/?breed=pit-bull&utm_source=tiktok&utm_medium=pin`. The right-hand column is the ready-made pin link
with `PLATFORM` to replace (`tiktok`, `youtube` or `instagram`).

| Breed | URL | Pinned-comment link |
|---|---|---|
| German Shepherd | `https://dogunpacked.com/?breed=german-shepherd` (or `?breed=gsd`) | `https://dogunpacked.com/?breed=german-shepherd&utm_source=PLATFORM&utm_medium=pin` |
| American Pit Bull Terrier | `https://dogunpacked.com/?breed=pit-bull` (or `?breed=pitbull`) | `https://dogunpacked.com/?breed=pit-bull&utm_source=PLATFORM&utm_medium=pin` |
| Rottweiler | `https://dogunpacked.com/?breed=rottweiler` | `https://dogunpacked.com/?breed=rottweiler&utm_source=PLATFORM&utm_medium=pin` |
| Doberman | `https://dogunpacked.com/?breed=doberman` (or `?breed=dobie`) | `https://dogunpacked.com/?breed=doberman&utm_source=PLATFORM&utm_medium=pin` |
| Cane Corso | `https://dogunpacked.com/?breed=cane-corso` (or `?breed=corso`) | `https://dogunpacked.com/?breed=cane-corso&utm_source=PLATFORM&utm_medium=pin` |
| Husky | `https://dogunpacked.com/?breed=husky` | `https://dogunpacked.com/?breed=husky&utm_source=PLATFORM&utm_medium=pin` |
| Golden Retriever | `https://dogunpacked.com/?breed=golden-retriever` | `https://dogunpacked.com/?breed=golden-retriever&utm_source=PLATFORM&utm_medium=pin` |
| Labrador | `https://dogunpacked.com/?breed=labrador` | `https://dogunpacked.com/?breed=labrador&utm_source=PLATFORM&utm_medium=pin` |
| Beagle | `https://dogunpacked.com/?breed=beagle` | `https://dogunpacked.com/?breed=beagle&utm_source=PLATFORM&utm_medium=pin` |
| Corgi | `https://dogunpacked.com/?breed=corgi` | `https://dogunpacked.com/?breed=corgi&utm_source=PLATFORM&utm_medium=pin` |
| Chihuahua | `https://dogunpacked.com/?breed=chihuahua` | `https://dogunpacked.com/?breed=chihuahua&utm_source=PLATFORM&utm_medium=pin` |
| French Bulldog | `https://dogunpacked.com/?breed=french-bulldog` | `https://dogunpacked.com/?breed=french-bulldog&utm_source=PLATFORM&utm_medium=pin` |
| Dachshund | `https://dogunpacked.com/?breed=dachshund` | `https://dogunpacked.com/?breed=dachshund&utm_source=PLATFORM&utm_medium=pin` |
| Belgian Malinois | `https://dogunpacked.com/?breed=belgian-malinois` | `https://dogunpacked.com/?breed=belgian-malinois&utm_source=PLATFORM&utm_medium=pin` |
| Australian Shepherd | `https://dogunpacked.com/?breed=australian-shepherd` | `https://dogunpacked.com/?breed=australian-shepherd&utm_source=PLATFORM&utm_medium=pin` |
| Border Collie | `https://dogunpacked.com/?breed=border-collie` | `https://dogunpacked.com/?breed=border-collie&utm_source=PLATFORM&utm_medium=pin` |
| Boxer | `https://dogunpacked.com/?breed=boxer` | `https://dogunpacked.com/?breed=boxer&utm_source=PLATFORM&utm_medium=pin` |
| Great Dane | `https://dogunpacked.com/?breed=great-dane` | `https://dogunpacked.com/?breed=great-dane&utm_source=PLATFORM&utm_medium=pin` |
| Mixed breed | `https://dogunpacked.com/?breed=mixed-breed` | `https://dogunpacked.com/?breed=mixed-breed&utm_source=PLATFORM&utm_medium=pin` |

## Measurement (GoatCounter, cookie-free)

The site counts page views with GoatCounter, which uses no cookies. The same script tag is on the home page, `/breeds/`, and every breed page:

```html
<script data-goatcounter="https://dogunpackedcom.goatcounter.com/count" async src="//gc.zgo.at/count.js"></script>
```

`script.js` does not add a second copy of that script, so the home page is counted once. Signup and video clicks on the list below use `data-goatcounter-click` and `data-goatcounter-title` on the link or button. Those attributes do not add JavaScript, and they do not change the Kit form post.

| Event | GoatCounter path | When |
|---|---|---|
| Page view | (automatic, count.js) | every load |
| Home signup click | `signup-home` | click on the home signup button |
| Sticky bar click | `signup-sticky` | click on the sticky signup link |
| Breed page signup | `signup-from-breed-<slug>` (e.g. `signup-from-breed-german-shepherd`) | click on that breed page's signup link |
| Breed video card | `video-from-breed-<slug>` | click on a video card on that breed page |
| Platform click | `outbound-youtube`, `outbound-instagram`, `outbound-tiktok` | platform button click |
| Newsletter (The Sniff Test) submit | `subscribe-<breed-slug>` (e.g. `subscribe-german-shepherd`), or `subscribe-none` when breed is blank | valid submit, just before posting to Kit |
| Latest click | `latest_click-<video-id>` (e.g. `latest_click-tyUgyQCYGGA`) | play on the embed, or a click on a small card |
| Newsletter confirmed | `subscribe_confirmed` | page opened with `?confirmed=1` (Kit's double opt-in redirect) |
| Contact submit | `contact_submit-<topic>`: `contact_submit-brand-partnership`, `-request-a-breed`, `-correction`, `-other` | valid contact submit (not honeypot), just before posting to Formspree |

The last five events go through `track()` in `script.js`, which does nothing if GoatCounter is blocked or missing. The four click paths above do not.

## Coming soon (`#guides`)

A short navy band, not a product card and not in the nav. Label "Coming soon", heading "Breed Files", then: in-depth breed guides are in the works, starting with the German Shepherd. The line is "The Sniff Test, our free newsletter, is where that news goes." No price, no date, no buy or preorder button, and no line that subscribers hear about it first.

The signup pitch stays "One behavior, one job, one study, and what to do tonight." The page does not show a sample letter or a second explanation of that order.

## GitHub Pages readiness

- All asset, script, style and data paths are relative (`images/…`, `styles.css`, `script.js`, `data/latest.json`),
  so the page works at `https://<user>.github.io/<repo>/` and on a custom domain.
- `.nojekyll` is in the repo root so Pages serves files as they are.
- `data/latest.json` is committed and not gitignored. Local secrets (`.kit-api-key.local`, `.env*`) and review
  screenshots (`assets/preview-*.png`) are gitignored.
- `images/logo-original.png` (1.8 MB master, unused by the page) was removed from the repo before publishing; keep it
  outside the repo and copy it to `images/` only to run `scripts/build_logo_assets.py`. `images/og-image.png` is
  unlinked until the OG image is supplied (see placeholders).

## Future-proofing

- Later `/breeds/<slug>/` pages (for example `/breeds/doberman/`) should reuse this template and the
  **shared `styles.css`** (link it as `../../styles.css`, don't fork it), plus `script.js`.
- A breed page can pre-set the breed with the same logic as `?breed=` (or by pre-filling `#breed`).

## Assets

- Photos: `images/breeds/*.webp` (WebP, explicit width/height). Sources and licenses: `assets/CREDITS.md`.
- Fonts: self-hosted Latin variable subsets in `fonts/` (Nunito, Fraunces), SIL Open Font License (`fonts/OFL-*.txt`). No Google Fonts request.
- Share image: `images/og-image.png` (1200×630), linked with absolute `https://dogunpacked.com/` URLs.
- Review screenshots: `python3 scripts/screenshot_preview.py` (Playwright) writes `assets/preview-v2-*.png`
  (gitignored).
