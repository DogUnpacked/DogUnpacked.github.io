# Dog Unpacked — hub page notes (`index.html`)

The hub page is the single link in every bio: platform buttons, a plain signup for The Sniff Test
(weekly newsletter), the latest long-form video, and a short Breed Files note. Brand scope: **every breed, one at a time**.

Replace `https://SITE/` below with the live address once GitHub Pages (or a custom domain) is set up.

## Section order

Hero (logo, eyebrow, title, tagline, description, proof row, mobile breed strip) → platform buttons
(YouTube, Instagram, TikTok — Facebook is not used) → newsletter (`#subscribe`) → Latest (`#latest`, only when `data/latest.json` lists a video) →
Breed Files (`#breed-files`, text only) → footer.

## Newsletter signup (Kit)

Copy: badge "FREE WEEKLY NEWSLETTER" → heading "Join The Sniff Test" → "The Dog Unpacked newsletter, in your
inbox every Sunday. One behavior. One job. One study. 90 seconds to read." → button "Get The Sniff Test" →
"Free. No spam. Unsubscribe anytime."

Plain newsletter signup. Email is required. Breed is optional: it's saved to the subscriber's Kit custom field
`breed` and does **not** change the signup. Everyone gets the same Sunday issue of The Sniff Test.

- Posts to Kit form 10011711: `email_address`, `fields[breed]` (only when filled in, Title-Cased by
  `script.js`), `tags[]=24362096` (`source:landing`, backup for the form's own auto-tag setting).
- How success works: `script.js` submits the form in the background the same way Kit's own embed script
  does (`fetch` POST of the form data with `Accept: application/json`; Kit allows this from any site and answers
  `{"status":"success"}`). On success the form is replaced by "Check your inbox — one click to confirm and you're
  in." If Kit returns a validation error the visitor sees "That didn't go through. Check your email address and
  try again." If the request fails for any other reason (network, blocked, unexpected reply) the form falls back
  to a normal POST and Kit's hosted page confirms instead. If Kit ever flags a signup for its spam check
  (`"quarantined"`), the visitor is sent to Kit's check page.
- Without JS the form still posts normally (Kit's hosted page); a blank breed is then sent as an empty `fields[breed]`.
- Not yet tested end to end with a real inbox (planned). Local tests mocked Kit; nothing was sent to Kit.
- IDs and the remaining Kit dashboard steps: `KIT.md`.

## Placeholders / omitted until supplied

| Item | How to switch it on |
|---|---|
| `https://SITE/` (this file) | The live address once hosting is set up. |
| Business email | Footer: a commented "For brands and partnerships" line. Uncomment it and replace both `{{BUSINESS_EMAIL}}` only when a dedicated brand address exists. Never put a personal Gmail on the page. |
| OG / Twitter image | `index.html` `<head>` comment lists the tags to add for `{{OG_IMAGE}}` (1200×630, absolute URL) and the `twitter:card` switch. |
| Kit success message | Kit's own form setting still says "…we'll send the File when it's ready." It only shows when JS is off or the background submit fails. Change it in the Kit dashboard (see `KIT.md`). |
| GoatCounter account | Create the free account with site code `dogunpacked` (or change `GOATCOUNTER_SITE` at the top of `script.js`). Until then nothing is recorded. |

## Latest video (`data/latest.json`)

`index.html` is never edited for a new video. `script.js` reads `data/latest.json`:

```json
[
  { "id": "tyUgyQCYGGA", "title": "Exact YouTube title", "published": "2026-09-22" }
]
```

Up to 3 long-form videos, newest first. The first shows as a click-to-load 16:9 thumbnail (no YouTube iframe
until the visitor clicks; the embed uses youtube-nocookie.com). The second and third show as small cards that
open the YouTube watch page in a new tab. Fewer entries = fewer cards. Empty list, missing file or broken
JSON = the section stays hidden. Shorts never go in this file.

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
| YouTube | `https://SITE/?utm_source=youtube&utm_medium=bio` |
| TikTok | `https://SITE/?utm_source=tiktok&utm_medium=bio` |
| Instagram | `https://SITE/?utm_source=instagram&utm_medium=bio` |

Pinned comments / descriptions on a breed video combine breed + UTM:

| Use | Link |
|---|---|
| TikTok pinned comment, Pit Bull video | `https://SITE/?breed=pit-bull&utm_source=tiktok&utm_medium=pin` |
| YouTube pinned comment, German Shepherd video | `https://SITE/?breed=gsd&utm_source=youtube&utm_medium=pin` |
| YouTube description, Doberman video | `https://SITE/?breed=dobie&utm_source=youtube&utm_medium=description` |
| Instagram story, Rottweiler | `https://SITE/?breed=rottweiler&utm_source=instagram&utm_medium=story` |

GoatCounter's count.js sends the query string with each page view; GoatCounter uses `utm_source` / `ref` as the
referrer, so bio and pin traffic shows up per platform in its Referrers view.

## Breed-aware URLs (`?breed=`)

`?breed=<lowercase-hyphenated-slug>` pre-fills "Your dog's breed (optional)" and changes the heading to
"Join The Sniff Test — [Breed] edition". Nothing else changes, and the visitor can clear or edit the field.

Display name = hyphens become spaces, then Title Case. Shortcuts: `gsd` → German Shepherd, `pitbull` → Pit Bull,
`corso` → Cane Corso, `dobie` → Doberman (`BREED_OVERRIDES` in `script.js`). Anything that isn't letters and
hyphens (or is over 40 characters) is ignored and the default page shows, with no error. Values are written with
`textContent` only. No cookies, no storage. Only known breeds get an edition: the 19 names in the
form's `#breed-list` datalist plus the aliases in `BREED_OVERRIDES` (`gsd`, `pitbull`, `corso`, `dobie`). An unknown
slug such as `?breed=xyz` shows the default page, so nobody can craft a link that puts arbitrary words in the
heading. To add a breed (e.g. `shiba-inu`), add an `<option value="Shiba Inu">` to the datalist in `index.html`.

Pinned comments: add `&utm_source=<platform>&utm_medium=pin` to any breed URL below, e.g.
`https://SITE/?breed=pit-bull&utm_source=tiktok&utm_medium=pin`. The right-hand column is the ready-made pin link
with `PLATFORM` to replace (`tiktok`, `youtube` or `instagram`).

| Breed | URL | Pinned-comment link |
|---|---|---|
| German Shepherd | `https://SITE/?breed=german-shepherd` (or `?breed=gsd`) | `https://SITE/?breed=german-shepherd&utm_source=PLATFORM&utm_medium=pin` |
| Pit Bull | `https://SITE/?breed=pit-bull` (or `?breed=pitbull`) | `https://SITE/?breed=pit-bull&utm_source=PLATFORM&utm_medium=pin` |
| Rottweiler | `https://SITE/?breed=rottweiler` | `https://SITE/?breed=rottweiler&utm_source=PLATFORM&utm_medium=pin` |
| Doberman | `https://SITE/?breed=doberman` (or `?breed=dobie`) | `https://SITE/?breed=doberman&utm_source=PLATFORM&utm_medium=pin` |
| Cane Corso | `https://SITE/?breed=cane-corso` (or `?breed=corso`) | `https://SITE/?breed=cane-corso&utm_source=PLATFORM&utm_medium=pin` |
| Husky | `https://SITE/?breed=husky` | `https://SITE/?breed=husky&utm_source=PLATFORM&utm_medium=pin` |
| Golden Retriever | `https://SITE/?breed=golden-retriever` | `https://SITE/?breed=golden-retriever&utm_source=PLATFORM&utm_medium=pin` |
| Labrador | `https://SITE/?breed=labrador` | `https://SITE/?breed=labrador&utm_source=PLATFORM&utm_medium=pin` |
| Beagle | `https://SITE/?breed=beagle` | `https://SITE/?breed=beagle&utm_source=PLATFORM&utm_medium=pin` |
| Corgi | `https://SITE/?breed=corgi` | `https://SITE/?breed=corgi&utm_source=PLATFORM&utm_medium=pin` |
| Chihuahua | `https://SITE/?breed=chihuahua` | `https://SITE/?breed=chihuahua&utm_source=PLATFORM&utm_medium=pin` |
| French Bulldog | `https://SITE/?breed=french-bulldog` | `https://SITE/?breed=french-bulldog&utm_source=PLATFORM&utm_medium=pin` |
| Dachshund | `https://SITE/?breed=dachshund` | `https://SITE/?breed=dachshund&utm_source=PLATFORM&utm_medium=pin` |
| Belgian Malinois | `https://SITE/?breed=belgian-malinois` | `https://SITE/?breed=belgian-malinois&utm_source=PLATFORM&utm_medium=pin` |
| Australian Shepherd | `https://SITE/?breed=australian-shepherd` | `https://SITE/?breed=australian-shepherd&utm_source=PLATFORM&utm_medium=pin` |
| Border Collie | `https://SITE/?breed=border-collie` | `https://SITE/?breed=border-collie&utm_source=PLATFORM&utm_medium=pin` |
| Boxer | `https://SITE/?breed=boxer` | `https://SITE/?breed=boxer&utm_source=PLATFORM&utm_medium=pin` |
| Great Dane | `https://SITE/?breed=great-dane` | `https://SITE/?breed=great-dane&utm_source=PLATFORM&utm_medium=pin` |
| Mixed breed | `https://SITE/?breed=mixed-breed` | `https://SITE/?breed=mixed-breed&utm_source=PLATFORM&utm_medium=pin` |

## Measurement (GoatCounter, cookie-free)

| Event | GoatCounter path | When |
|---|---|---|
| Page view | (automatic, count.js) | every load |
| Platform click | `outbound-youtube`, `outbound-instagram`, `outbound-tiktok` | platform button click |
| Newsletter (The Sniff Test) submit | `subscribe-<breed-slug>` (e.g. `subscribe-german-shepherd`), or `subscribe-none` when breed is blank | valid submit, just before posting to Kit |
| Latest click | `latest_click-<video-id>` (e.g. `latest_click-tyUgyQCYGGA`) | play on the embed, or a click on a small card |

All calls go through `track()` in `script.js`, which does nothing if GoatCounter is blocked or missing.

## December: when the German Shepherd File is on sale

Section 5 (Breed Files) becomes **one product card**, only for a guide that actually exists:

- Header art: the Unpacked box label in HTML/CSS (no image): kraft-brown card border, cream label, navy
  stencil-style text. Line 1 `CONTENTS: 1 GERMAN SHEPHERD`, line 2 `NOT ANXIOUS · ON SHIFT`.
- Title "German Shepherd File", a two-line description, the price, and a real Buy button
  (Kit Commerce, which works on the Free plan, or Gumroad).
- Add a second card only when a second guide exists. No "coming soon" cards.

Component sketch (removed from the live CSS to keep it tidy; drop into `styles.css` when needed):

```html
<article class="product-card">
  <div class="box-label" aria-hidden="true">
    <div class="box-label-inner">
      <span class="box-label-line1">Contents: 1 German Shepherd</span>
      <span class="box-label-line2">Not anxious · On shift</span>
    </div>
  </div>
  <h3>German Shepherd File</h3>
  <p>[two-line description]</p>
  <p class="price">$[price]</p>
  <a class="btn btn--primary" href="[Kit Commerce / Gumroad URL]">Buy the German Shepherd File</a>
</article>
```

```css
.box-label { background: #B08355; border: 2px solid #8C6239; border-radius: 6px; padding: .7rem; }
.box-label-inner { background: var(--cream); border: 2px dashed var(--navy); padding: .6rem .7rem;
  display: flex; flex-direction: column; align-items: center; gap: .25rem; text-align: center;
  color: var(--navy); text-transform: uppercase; font-family: "Arial Black", Arial, var(--font); font-weight: 900; }
.box-label-line1, .box-label-line2 { position: relative; display: inline-block; }
/* stencil bridges: one cream hairline per text line */
.box-label-line1::after, .box-label-line2::after { content: ""; position: absolute; inset: 0; pointer-events: none;
  background: repeating-linear-gradient(to bottom, transparent 0 .6em, var(--cream) .6em calc(.6em + 1.5px),
  transparent calc(.6em + 1.5px) 1.15em); }
.box-label-line1 { font-size: .9rem; letter-spacing: .1em; }
.box-label-line2 { font-size: .74rem; letter-spacing: .16em; }
```

The full earlier implementation (four cards with badges) is in git history at commit 3bf7784.

## GitHub Pages readiness

- All asset, script, style and data paths are relative (`images/…`, `styles.css`, `script.js`, `data/latest.json`),
  so the page works at `https://<user>.github.io/<repo>/` and on a custom domain.
- `.nojekyll` is in the repo root so Pages serves files as they are.
- `data/latest.json` is committed and not gitignored. Local secrets (`.kit-api-key.local`, `.env*`) and review
  screenshots (`assets/preview-*.png`) are gitignored.
- `images/logo-original.png` (1.8 MB) is not used by the page; the page uses the WebP/PNG logo sizes. Delete it or move
  it out of the published folder before publishing if you don't need it in the repo. `images/og-image.png` is also
  unlinked until the OG image is supplied (see placeholders).

## Future-proofing

- Later `/breeds/<slug>/` pages (for example `/breeds/doberman/`) should reuse this template and the
  **shared `styles.css`** (link it as `../../styles.css`, don't fork it), plus `script.js`.
- A breed page can pre-set the breed with the same logic as `?breed=` (or by pre-filling `#breed`).

## Assets

- Photos: `images/breeds/*.webp` (WebP, under 30 KB each, explicit width/height, `loading="lazy"`).
  Sources and licenses: `assets/CREDITS.md`.
- Review screenshots: `python3 scripts/screenshot_preview.py` (Playwright) writes `assets/preview-v2-*.png`
  (gitignored).
