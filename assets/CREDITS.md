# Image credits — Dog Unpacked hub page

Every photo on the page comes from Unsplash, Pexels, or Storyblocks. Record each one here
before it goes live. Replace any image whose source or license can't be documented.

## Breed photos (Unsplash License — free for commercial use, no attribution required)

License: https://unsplash.com/license

| File(s) | Breed | Photo page | Photographer | Unsplash CDN id | License |
|---|---|---|---|---|---|
| `images/breeds/german-shepherd-480.webp`, `images/breeds/german-shepherd-240.webp` | German Shepherd | https://unsplash.com/photos/a-german-shepherd-dog-looking-at-the-camera-bBH_LitbjXI | Sabbra Cadabra (@sabbracadabra) | `photo-1693507078013-b4256d9baf9f` | Unsplash License |
| `images/breeds/pit-bull-480.webp`, `images/breeds/pit-bull-240.webp` | Pit Bull | https://unsplash.com/photos/adult-black-and-white-american-pit-bull-terrier-pWqToFDCrJ8 | Yohan Cho (@yohoney) | `photo-1543495915-8d5f641a4bfa` | Unsplash License |
| `images/breeds/rottweiler-480.webp`, `images/breeds/rottweiler-240.webp` | Rottweiler | https://unsplash.com/photos/a-large-black-and-brown-dog-on-a-leash-pgZ84X4Z4yM | Michael Starkie (@starkie_pics) | `photo-1640262653842-3da89bc3e9b0` | Unsplash License |
| `images/breeds/doberman-480.webp`, `images/breeds/doberman-240.webp` | Doberman | https://unsplash.com/photos/a-doberman-dog-sits-attentively-outdoors-with-mountains-behind-vKzRKRmANbM | Ile Gorgievski (@ilegorgievski) | `photo-1757781956803-2efc6921abe9` | Unsplash License |

Provenance notes:
- The original JPGs (480 px, committed in c487c96 as `images/{gsd,pitbull,rottweiler,doberman}.jpg`)
  were pixel-matched against the Unsplash CDN ids listed in the original README. The WebP files are
  re-encodes of those JPGs (`-480` = original framing, `-240` = square crop for the mobile strip).
- Photo pages and photographers were confirmed through search-engine copies of the Unsplash pages,
  because unsplash.com shows a bot check to automated fetches. Doberman: page matched by its
  description and publish date (13 Sep 2025, the same date encoded in the CDN id). Open each link once
  in a normal browser to double-check before launch.

## Brand artwork (owned by Dog Unpacked — not stock)

| File(s) | Notes |
|---|---|
| `images/logo-*.{png,webp}`, `favicon.ico`, `favicon-32.png`, `apple-touch-icon.png`, `images/og-image.png` | Dog Unpacked logo and derivatives (see `scripts/build_logo_assets.py`). |

## Pending

| Placeholder | Needed |
|---|---|
| `{{OG_IMAGE}}` | 1200×630 Unpacked box photo. Add its source here when supplied (own photo, or Unsplash / Pexels / Storyblocks with license URL). |
