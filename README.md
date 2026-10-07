# Dog Unpacked — Landing Site

A polished, mobile-first link-in-bio landing page for **Dog Unpacked**. Static HTML/CSS (plus a tiny optional script). Host it for free on **GitHub Pages**.

## Newsletter pipeline

See **`README-newsletter.md`** for the Kit send scaffold (Thursday cron, issue files, dry-run). Formspree stays on the landing form until a Kit form ID exists (§3.1).

## What’s included

| File | Purpose |
|------|---------|
| `index.html` | Main page (hero, social, newsletter, shop, footer) |
| `styles.css` | Navy / cream / amber mobile-first styles + desktop side art |
| `script.js` | Optional: warns if Formspree ID isn’t set yet |
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

### 3. Newsletter — free Formspree endpoint

The form posts to:

```html
action="https://formspree.io/f/YOUR_FORM_ID"
```

**How to get a free Formspree endpoint:**

1. Go to [https://formspree.io](https://formspree.io) and create a free account.
2. Click **New Form**, name it (e.g. “Dog Unpacked Newsletter”).
3. Copy the form endpoint URL (looks like `https://formspree.io/f/abcdefgh`).
4. In `index.html`, replace `YOUR_FORM_ID` with your real form ID so the action becomes your endpoint.
5. Submit a test email from the live site and confirm it arrives in Formspree (and your inbox if you set email notifications).

**Fallback (no Formspree):** change the form to a mailto, e.g.:

```html
<form action="mailto:you@example.com" method="POST" enctype="text/plain">
```

(Mailto depends on the visitor’s email app and is less reliable on mobile.)

### 4. Shop / guide “Buy” links

| Placeholder | Replace with |
|-------------|--------------|
| German Shepherd / Pit Bull / Rottweiler **File** cards | Buttons say **Coming December** (`href="#"`, `aria-disabled`) until sell links exist |

Guide titles match the brief (… File). Sell links still TBD.

### 5. Logo, favicons & share image — done

The brand logo is live in the hero (circular badge above the "Dog Unpacked" wordmark, 144px on phones / 168px on wider screens).

| File | Use |
|------|-----|
| `images/logo-original.png` | Full-res master (do not link from the page) |
| `images/logo-256.{png,webp}`, `images/logo-512.{png,webp}` | Hero logo (`<picture>` + `srcset`) |
| `favicon.ico` (16/32/48), `favicon-32.png` | Browser tab icons |
| `apple-touch-icon.png` (180×180) | iOS home-screen icon |
| `images/og-image.png` (1200×630) | Open Graph / Twitter share card |

Regenerate everything from the master with `python3 scripts/build_logo_assets.py` (needs Pillow).

**Before publishing:** `og:image` / `twitter:image` currently use relative paths. Switch them to absolute URLs (e.g. `https://<user>.github.io/<repo>/images/og-image.png`) and add `og:url` once the GitHub Pages URL is known — see the comment in `<head>`.

---

## Publish for free on GitHub Pages

### Option A — New repo (recommended)

1. Create a new GitHub repository (e.g. `dog-unpacked` or `dog-unpacked.github.io`).
2. Upload these files to the **root** of the repo (or push via git):

   ```bash
   cd dog-unpacked-landing
   git init
   git add index.html styles.css script.js README.md
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
2. Click **Add file → Upload files** and upload `index.html`, `styles.css`, `script.js`, and optionally this `README.md`.
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
- **Desktop side art (≥960px):** left/right rails with geometric navy/cream/amber photo frames (GSD, Rottweiler, Doberman, Pit Bull) plus subtle SVG breed silhouettes. Hidden on mobile so the centered column stays clean.
- **Fonts:** Fraunces (display) + Nunito (UI) via Google Fonts, with system fallbacks.
- No frameworks or build step — plain HTML/CSS.

### External images (Unsplash)

Side-rail photos load from **Unsplash** (`images.unsplash.com`) under the [Unsplash License](https://unsplash.com/license) — free for commercial use, no paid stock license required. They need a network connection on first load. If you prefer fully offline hosting, download the four images into an `images/` folder and point the `<img src>` values in `index.html` at local files.

| Breed | Unsplash photo |
|-------|----------------|
| German Shepherd | `photo-1693507078013-b4256d9baf9f` |
| Rottweiler | `photo-1640262653842-3da89bc3e9b0` |
| Doberman | `photo-1757781956803-2efc6921abe9` |
| Pit Bull | `photo-1543495915-8d5f641a4bfa` |

## License

Content and branding belong to Josh / Dog Unpacked. Code in this folder is free to use and modify for the Dog Unpacked brand.
