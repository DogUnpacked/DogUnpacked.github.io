# Dog Unpacked — hub page notes (`index.html`)

The hub page is the single link in every bio: platforms, The Sunday Breed File signup (email + breed),
latest video, breed owner guides. Brand scope: **every breed, one at a time**.

Replace `https://SITE/` below with the live address once GitHub Pages (or a custom domain) is set up.

## Section order

Hero (logo, eyebrow, title, tagline, description, proof row, mobile breed strip) → platform buttons →
newsletter (`#subscribe`) → Latest video → breed owner guides (`#guides`) → footer.

## Placeholders (each is a one-line change)

| Placeholder | Where | What happens until it's replaced |
|---|---|---|
| `{{FACEBOOK_URL}}` | `index.html`, Facebook `<a href>` in the platform list | Button stays hidden (CSS `:has()` + JS fallback hide any `.needs-url` whose link contains `{{`). |
| `{{BUSINESS_EMAIL}}` | `index.html`, footer "For brands and partnerships" line (appears twice on that one line) | Line stays hidden. |
| `{{LATEST_VIDEO_ID}}` | `index.html`, `data-video-id` on `#latest-video` | A navy/cream card linking to the channel shows instead. With a real 11-character ID, `script.js` shows the thumbnail and loads the iframe (youtube-nocookie) only on click. |
| `{{OG_IMAGE}}` | `index.html` `<head>` comment: `og:image` + `twitter:image` | `images/og-image.png` (logo card) stays. Use an absolute URL when publishing. |
| `GOATCOUNTER_SITE` | top of `script.js` (`"dogunpacked"`) | Script loads from `https://gc.zgo.at/count.js` and reports to `https://dogunpacked.goatcounter.com/count`. Nothing is recorded until that GoatCounter account exists. Set to `""` to switch analytics off. |

## Bio links (UTM)

| Platform | Bio link |
|---|---|
| YouTube | `https://SITE/?utm_source=youtube&utm_medium=bio` |
| TikTok | `https://SITE/?utm_source=tiktok&utm_medium=bio` |
| Instagram | `https://SITE/?utm_source=instagram&utm_medium=bio` |
| Facebook | `https://SITE/?utm_source=facebook&utm_medium=bio` |

GoatCounter records the full path including the query string, so UTM sources show up in its dashboard.

## Breed-aware URLs (`?breed=`)

`?breed=` takes a lowercase, hyphenated slug. The page:

- pre-fills "Your dog's breed",
- changes the heading to "Join the Sunday Breed File — [Breed] edition",
- moves that breed's guide card to the top if a guide exists (German Shepherd, Pit Bull, Rottweiler, Doberman).

Display name = hyphens become spaces, then Title Case. Shortcuts: `gsd` → German Shepherd,
`pitbull` → Pit Bull, `corso` → Cane Corso, `dobie` → Doberman (edit `BREED_OVERRIDES` in `script.js`).
Anything that isn't letters and hyphens (or is over 40 characters) is ignored and the default page shows,
with no error. Values are written with `textContent` only. No cookies, no storage.

Note: any well-formed slug is accepted, including breeds not in the datalist (so `?breed=shiba-inu` works
without a code change). That also means a made-up word renders as "[Word] edition".

| Breed | URL | Guide card first? |
|---|---|---|
| German Shepherd | `https://SITE/?breed=german-shepherd` (or `?breed=gsd`) | yes |
| Pit Bull | `https://SITE/?breed=pit-bull` (or `?breed=pitbull`) | yes |
| Rottweiler | `https://SITE/?breed=rottweiler` | yes |
| Doberman | `https://SITE/?breed=doberman` (or `?breed=dobie`) | yes |
| Cane Corso | `https://SITE/?breed=cane-corso` (or `?breed=corso`) | no guide yet |
| Husky | `https://SITE/?breed=husky` | no guide yet |
| Golden Retriever | `https://SITE/?breed=golden-retriever` | no guide yet |
| Labrador | `https://SITE/?breed=labrador` | no guide yet |
| Beagle | `https://SITE/?breed=beagle` | no guide yet |
| Corgi | `https://SITE/?breed=corgi` | no guide yet |
| Chihuahua | `https://SITE/?breed=chihuahua` | no guide yet |
| French Bulldog | `https://SITE/?breed=french-bulldog` | no guide yet |
| Dachshund | `https://SITE/?breed=dachshund` | no guide yet |
| Belgian Malinois | `https://SITE/?breed=belgian-malinois` | no guide yet |
| Australian Shepherd | `https://SITE/?breed=australian-shepherd` | no guide yet |
| Border Collie | `https://SITE/?breed=border-collie` | no guide yet |
| Boxer | `https://SITE/?breed=boxer` | no guide yet |
| Great Dane | `https://SITE/?breed=great-dane` | no guide yet |
| Mixed breed | `https://SITE/?breed=mixed-breed` | no guide yet |

Breed and UTM combine, for example a pinned TikTok comment on a Pit Bull video:
`https://SITE/?breed=pit-bull&utm_source=tiktok&utm_medium=pin`
More: `?breed=gsd&utm_source=youtube&utm_medium=description`, `?breed=dobie&utm_source=instagram&utm_medium=story`.

## Measurement (GoatCounter, cookie-free)

| Event | GoatCounter path | When |
|---|---|---|
| Page view | page path + query | automatic (count.js) |
| Platform click | `outbound-youtube`, `outbound-instagram`, `outbound-tiktok`, `outbound-facebook` | platform button click |
| Latest card / video | `outbound-youtube-latest`, `latest-video-play` | channel card click / video play |
| Newsletter submit | `subscribe-<normalized-breed-slug>` (title "Newsletter: German Shepherd") | valid form submit, before posting to Kit |
| Guide notify | `guide-notify` | "Get notified when they drop" click |

All calls go through `track()` in `script.js`, which does nothing if GoatCounter is blocked or missing.
Setup still needed: create the free GoatCounter account with site code `dogunpacked` (or change
`GOATCOUNTER_SITE`).

## Newsletter form (Kit)

Posts to Kit form 10011711: `email_address`, `fields[breed]` (custom field `breed`), `tags[]=24362096`
(`source:landing`). The breed is Title-Cased before submit. Dashboard steps still open: see `KIT.md`.

## Future-proofing

- Later `/breeds/<slug>/` pages (for example `/breeds/doberman/`) should reuse this template and the
  **shared `styles.css`** (link it as `../../styles.css`, don't fork it), plus `script.js`.
- The guide card is a reusable component: `li.card.guide-card[data-breed="<slug>"]` containing `.box-label`
  (line 1 "CONTENTS: 1 [BREED]", line 2 the one-line hook), `.badge-soon`, `.card-title`, `.card-blurb`.
  When a guide goes on sale, swap the badge for a `btn btn--primary` buy link inside the card.
- A breed page can pre-set the breed with the same logic as `?breed=` (or by pre-filling `#breed`).

## Assets

- Photos: `images/breeds/*.webp` (WebP, under 30 KB each, explicit width/height, `loading="lazy"`).
  Sources and licenses: `assets/CREDITS.md`.
- Review screenshots: `python3 scripts/screenshot_preview.py` (Playwright) writes
  `assets/preview-v2-*.png` (gitignored).
