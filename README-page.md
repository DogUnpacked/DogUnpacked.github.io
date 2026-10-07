# Dog Unpacked — hub page notes (`index.html`)

The hub page is the single link in every bio: platform buttons, a plain signup for The Sunday Breed File
newsletter, the latest long-form video, and a short Breed Files note. Brand scope: **every breed, one at a time**.

Replace `https://SITE/` below with the live address once GitHub Pages (or a custom domain) is set up.

## Section order

Hero (logo, eyebrow, title, tagline, description, proof row, mobile breed strip) → platform buttons
(YouTube, Instagram, TikTok) → newsletter (`#subscribe`) → Latest (`#latest`, only when a video ID is set) →
Breed Files (`#breed-files`, text only) → footer.

## Newsletter signup (Kit)

Plain newsletter signup. Email is required. Breed is optional: it's saved to the subscriber's Kit custom field
`breed` and does **not** change the signup. Everyone gets the same Sunday newsletter.

- Posts to Kit form 10011711: `email_address`, `fields[breed]` (only when filled in, Title-Cased by
  `script.js`), `tags[]=24362096` (`source:landing`, backup for the form's own auto-tag setting).
- Without JS the form still posts; a blank breed is then sent as an empty `fields[breed]`.
- IDs and the remaining Kit dashboard steps: `KIT.md`.

## Omitted until supplied

| Item | How to switch it on |
|---|---|
| Facebook button | `index.html`: uncomment the Facebook `<li>` in the platform list and replace `{{FACEBOOK_URL}}`. CSS is ready. |
| Business email | `index.html` footer: uncomment the "For brands and partnerships" line and replace both `{{BUSINESS_EMAIL}}`. |
| OG / Twitter image | `index.html` `<head>` comment lists the tags to add for `{{OG_IMAGE}}` (1200×630, absolute URL) and the `twitter:card` switch. |
| GoatCounter account | Create the free account with site code `dogunpacked` (or change `GOATCOUNTER_SITE` at the top of `script.js`). Until then nothing is recorded. |

## Latest video

The ID lives in one place: `index.html` → `<section id="latest" data-video-id="...">`.
Empty = section hidden. An 11-character ID = `script.js` shows the section with a click-to-load thumbnail
(no YouTube iframe until the visitor clicks; the embed uses youtube-nocookie.com).

Update it automatically:

```bash
python3 scripts/update_latest_video.py            # writes the newest long-form video ID if it changed
python3 scripts/update_latest_video.py --dry-run  # just show what it would do
```

It reads the channel RSS feed (channel id `UC_2f25vzJLiV799CfoHfDHA` = @DogUnpacked), skips Shorts
(`GET /shorts/<id>` without redirects: 200 = Short, redirect to /watch = long-form; falls back to the feed's
own `/shorts/` link if YouTube rate-limits the check) and anything 180 s or shorter, then rewrites the ID in
`index.html`. It never commits; review and commit the change yourself. Exit 0 with "no change" when the ID is already current.

## Bio links (UTM)

| Platform | Bio link |
|---|---|
| YouTube | `https://SITE/?utm_source=youtube&utm_medium=bio` |
| TikTok | `https://SITE/?utm_source=tiktok&utm_medium=bio` |
| Instagram | `https://SITE/?utm_source=instagram&utm_medium=bio` |
| Facebook | `https://SITE/?utm_source=facebook&utm_medium=bio` |

Pinned comments / descriptions on a breed video combine breed + UTM:

| Use | Link |
|---|---|
| TikTok pinned comment, Pit Bull video | `https://SITE/?breed=pit-bull&utm_source=tiktok&utm_medium=pin` |
| YouTube pinned comment, German Shepherd video | `https://SITE/?breed=gsd&utm_source=youtube&utm_medium=pin` |
| YouTube description, Doberman video | `https://SITE/?breed=dobie&utm_source=youtube&utm_medium=description` |
| Instagram story, Rottweiler | `https://SITE/?breed=rottweiler&utm_source=instagram&utm_medium=story` |
| Facebook post, Golden Retriever | `https://SITE/?breed=golden-retriever&utm_source=facebook&utm_medium=post` |

GoatCounter's count.js sends the query string with each page view; GoatCounter uses `utm_source` / `ref` as the
referrer, so bio and pin traffic shows up per platform in its Referrers view.

## Breed-aware URLs (`?breed=`)

`?breed=<lowercase-hyphenated-slug>` pre-fills "Your dog's breed (optional)" and changes the heading to
"Join the Sunday Breed File — [Breed] edition". Nothing else changes, and the visitor can clear or edit the field.

Display name = hyphens become spaces, then Title Case. Shortcuts: `gsd` → German Shepherd, `pitbull` → Pit Bull,
`corso` → Cane Corso, `dobie` → Doberman (`BREED_OVERRIDES` in `script.js`). Anything that isn't letters and
hyphens (or is over 40 characters) is ignored and the default page shows, with no error. Values are written with
`textContent` only. No cookies, no storage. Any well-formed slug is accepted (so `?breed=shiba-inu` works without a
code change), which also means a made-up word renders as "[Word] edition".

| Breed | URL |
|---|---|
| German Shepherd | `https://SITE/?breed=german-shepherd` (or `?breed=gsd`) |
| Pit Bull | `https://SITE/?breed=pit-bull` (or `?breed=pitbull`) |
| Rottweiler | `https://SITE/?breed=rottweiler` |
| Doberman | `https://SITE/?breed=doberman` (or `?breed=dobie`) |
| Cane Corso | `https://SITE/?breed=cane-corso` (or `?breed=corso`) |
| Husky | `https://SITE/?breed=husky` |
| Golden Retriever | `https://SITE/?breed=golden-retriever` |
| Labrador | `https://SITE/?breed=labrador` |
| Beagle | `https://SITE/?breed=beagle` |
| Corgi | `https://SITE/?breed=corgi` |
| Chihuahua | `https://SITE/?breed=chihuahua` |
| French Bulldog | `https://SITE/?breed=french-bulldog` |
| Dachshund | `https://SITE/?breed=dachshund` |
| Belgian Malinois | `https://SITE/?breed=belgian-malinois` |
| Australian Shepherd | `https://SITE/?breed=australian-shepherd` |
| Border Collie | `https://SITE/?breed=border-collie` |
| Boxer | `https://SITE/?breed=boxer` |
| Great Dane | `https://SITE/?breed=great-dane` |
| Mixed breed | `https://SITE/?breed=mixed-breed` |

## Measurement (GoatCounter, cookie-free)

| Event | GoatCounter path | When |
|---|---|---|
| Page view | (automatic, count.js) | every load |
| Platform click | `outbound-youtube`, `outbound-instagram`, `outbound-tiktok` (`outbound-facebook` once enabled) | platform button click |
| Newsletter submit | `subscribe-<breed-slug>` (e.g. `subscribe-german-shepherd`), or `subscribe-none` when breed is blank | valid submit, just before posting to Kit |

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

## Future-proofing

- Later `/breeds/<slug>/` pages (for example `/breeds/doberman/`) should reuse this template and the
  **shared `styles.css`** (link it as `../../styles.css`, don't fork it), plus `script.js`.
- A breed page can pre-set the breed with the same logic as `?breed=` (or by pre-filling `#breed`).

## Assets

- Photos: `images/breeds/*.webp` (WebP, under 30 KB each, explicit width/height, `loading="lazy"`).
  Sources and licenses: `assets/CREDITS.md`.
- Review screenshots: `python3 scripts/screenshot_preview.py` (Playwright) writes `assets/preview-v2-*.png`
  (gitignored).
