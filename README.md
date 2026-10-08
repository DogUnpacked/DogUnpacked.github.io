# Dog Unpacked — Landing Site

A polished, mobile-first link-in-bio hub page for **Dog Unpacked**. Static HTML/CSS plus a small plain-JS enhancement script. Host it for free on **GitHub Pages**.

Page spec, placeholders, breed-aware URLs, UTM bio links and analytics events: see **`README-page.md`**.

## Newsletter pipeline

The newsletter is **The Sniff Test** (weekly, Sunday). See **`README-newsletter.md`** for the Kit send scaffold (Sunday cron, issue files, dry-run). The landing signup posts to Kit (form IDs in `KIT.md`).

## What’s included

| File | Purpose |
|------|---------|
| `index.html` | Hub page (header, hero with The Sniff Test, platforms, breed frames, latest video, a short Coming soon note, contact, footer) |
| `styles.css` | Navy / cream / amber mobile-first styles |
| `script.js` | GoatCounter events, `?breed=` personalization, breed Title-Case, lite YouTube embed |
| `fonts/` | Self-hosted Nunito and Fraunces (OFL) |
| `data/latest.json` | Latest section data: up to 3 newest long-form videos `{id, title, published}`, newest first |
| `scripts/update_latest_video.py` | Refreshes `data/latest.json` from the channel feed (skips Shorts); prints "Latest: no change" when current |
| `README-page.md` | Page notes: placeholders, bio/breed URLs, events |
| `KIT.md` | Kit form/field/tag IDs + remaining dashboard steps |
| `assets/CREDITS.md` | Photo sources and licenses |
| `README.md` | This file |

## Placeholders you must fill in

Before going live, replace these:

### 1. Social links (`index.html`) — already set

Live profile URLs are already in place. Only change them if the handles change:

| Platform | URL |
|----------|-----|
| YouTube | `https://www.youtube.com/@DogUnpacked?sub_confirmation=1` |
| Instagram | `https://www.instagram.com/dogunpacked` |
| TikTok | `https://www.tiktok.com/@dogsunpacked` |

### 2. Tagline (editable)

In the hero, change:

```html
<p class="tagline">He's not broken. He's bred that way.</p>
```

Brand thesis is set. Look for the `<!-- EDITABLE: ... -->` comment above it if you need to tweak.

### 3. Newsletter (The Sniff Test) — Kit

The signup form posts to Kit form `10011711` (`https://app.kit.com/forms/10011711/subscriptions`) with
`email_address` and an optional `fields[breed]`. Double opt-in stays on in Kit. IDs, the `breed` custom field, the
`source:landing` tag and the remaining Kit dashboard steps are in **`KIT.md`**. No Formspree.

### 4. Logo, favicons & share image — done

The brand logo is live in the hero (circular badge above the "Dog Unpacked" wordmark, 144px on phones / 168px on wider screens).

| File | Use |
|------|-----|
| `logo-original.png` (not in the repo) | Full-res master, kept outside the published repo (1.8 MB). Put it at `images/logo-original.png` locally to regenerate. |
| `images/logo-256.{png,webp}`, `images/logo-512.{png,webp}` | Hero logo (`<picture>` + `srcset`) |
| `favicon.ico` (16/32/48), `favicon-32.png` | Browser tab icons |
| `apple-touch-icon.png` (180×180) | iOS home-screen icon |
| `images/og-image.png` (1200×630) | Share card, linked from Open Graph and Twitter meta |

Regenerate everything from the master with `python3 scripts/build_logo_assets.py` (needs Pillow).

**OG image:** `images/og-image.png` is linked with an absolute `https://dogunpacked.com/` URL. Replace the file when a box photo is ready.

---

## Publish for free on GitHub Pages

**Live:** https://dogunpacked.com/ — repo https://github.com/DogUnpacked/DogUnpacked.github.io, Pages from `main` / root. Push to `main` to update the site. The steps below are kept for reference.

### Option A — New repo (recommended)

1. Create a new GitHub repository (e.g. `dog-unpacked` or `dog-unpacked.github.io`).
2. Upload these files to the **root** of the repo (or push via git):

   ```bash
   cd dog-unpacked-landing
   git init
   git add .
   git commit -m "Add Dog Unpacked landing page"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
   git push -u origin main
   ```

3. On GitHub: **Settings → Pages**.
4. Under **Build and deployment → Source**, choose **Deploy from a branch**.
5. Branch: `main`, folder: `/ (root)`. Click **Save**.
6. Wait a minute. Your site will be at:

   `https://YOUR_USERNAME.github.io/YOUR_REPO/`

   (If the repo is named `YOUR_USERNAME.github.io`, it will be `https://YOUR_USERNAME.github.io/`.)

### Option B — GitHub website UI (no git required)

1. Create a new empty repo on GitHub.
2. Click **Add file → Upload files** and upload `index.html`, `styles.css`, `script.js`, the favicon files and the `images/` folder.
3. Commit.
4. Enable Pages as in steps 3–6 above.

### Custom domain (optional)

In **Settings → Pages → Custom domain**, add your domain and follow GitHub’s DNS instructions. HTTPS is free via GitHub.

---

## Local preview

Open `index.html` in a browser, or from this folder:

```bash
# Python
python3 -m http.server 8080

# then visit http://localhost:8080
```

## Design notes

- **Mobile-first** link-in-bio layout; large tap targets.
- **Palette (official):** Navy `#1B2A4A`, Cream `#F5EDDC`, Amber `#D89B3D` (accent only).
- **Motifs:** refined SVG paw mark (hero, watermarks, footer) — not emoji/cartoon.
- **Desktop (≥960px):** the breed frames sit beside the tagline and the signup. On a phone they sit under the platform row, so the signup stays in the first screen.
- **Fonts:** Fraunces (headings) + Nunito (body/buttons), self-hosted Latin subsets, `font-display: swap`, with metric-matched local fallbacks.
- No frameworks or build step — plain HTML/CSS/JS.

### Breed photos

Local WebP files in `images/breeds/` (Unsplash License). Photo pages, photographers and license for each
are recorded in **`assets/CREDITS.md`**. Every new photo must come from Unsplash, Pexels or Storyblocks and
be added there.

## License

Content and branding belong to Josh / Dog Unpacked. Code in this folder is free to use and modify for the Dog Unpacked brand.
