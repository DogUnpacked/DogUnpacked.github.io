#!/usr/bin/env python3
"""Build the static breed directory from data/breeds.json.

Python standard library only. No network. GitHub Pages serves the HTML this
writes, so run it before you commit:

    python3 scripts/build_breeds.py

Adding a breed later: add one object to data/breeds.json, add its photo
(or set photo.placeholder to true), then run this script again.
"""

import csv
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "breeds.json"
LATEST = ROOT / "data" / "latest.json"
SITEMAP = ROOT / "sitemap.xml"
CSV_PATH = ROOT / "docs" / "breed-facts-review.csv"
CREDITS = ROOT / "assets" / "CREDITS.md"
BREEDS_DIR = ROOT / "breeds"
SITE = "https://dogunpacked.com"
CREDIT_START = "<!-- BREED-DIRECTORY-CREDITS:START -->"
CREDIT_END = "<!-- BREED-DIRECTORY-CREDITS:END -->"

BANNED = re.compile(
    r"\b(dangerous|safe|aggressive|aggression|facebook|preorder)\b",
    re.I,
)

GROUPS = [
    "Sporting",
    "Hound",
    "Working",
    "Terrier",
    "Toy",
    "Non-Sporting",
    "Herding",
    "Other",
]


def esc(value):
    return html.escape(str(value), quote=True)


def load():
    payload = json.loads(DATA.read_text(encoding="utf-8"))
    breeds = payload["breeds"]
    slugs = [b["slug"] for b in breeds]
    if len(slugs) != len(set(slugs)):
        raise SystemExit("duplicate breed slug in data/breeds.json")
    for breed in breeds:
        blob = " ".join(
            [breed["name"], breed["job"]["text"], breed["home"]]
            + [fact["text"] for fact in breed["facts"]]
        )
        if breed.get("atts"):
            blob += " " + breed["atts"]["text"] + " " + breed["atts"]["note"]
        if "!" in blob:
            raise SystemExit(f"exclamation mark in {breed['slug']}")
        if BANNED.search(blob):
            raise SystemExit(f"banned word in {breed['slug']}: {BANNED.search(blob).group(0)}")
        if "@" in blob:
            raise SystemExit(f"@ in breed copy for {breed['slug']}")
        if not breed["facts"]:
            raise SystemExit(f"no facts for {breed['slug']}")
        photo = breed.get("photo") or {}
        author = photo.get("author") or ""
        if not photo.get("placeholder"):
            if any(mark in author for mark in ("!", "@")) or "http" in author.lower() or "www." in author.lower():
                raise SystemExit(f"messy photo credit for {breed['slug']}: {author}")
    return breeds


def videos_for(breed):
    if not LATEST.exists():
        return []
    try:
        latest = json.loads(LATEST.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    names = [breed["name"]] + list(breed.get("aliases") or [])
    found = []
    for item in latest:
        if not isinstance(item, dict):
            continue
        title = item.get("title") or ""
        vid = item.get("id") or ""
        if not re.fullmatch(r"[A-Za-z0-9_-]{11}", vid):
            continue
        for name in names:
            if len(name) < 4:
                continue
            if re.search(r"\b" + re.escape(name) + r"\b", title, re.I):
                found.append({"id": vid, "title": title})
                break
    return found


def meta_description(breed):
    text = breed["job"]["text"].strip()
    prefix = breed["name"] + ": "
    room = 155 - len(prefix)
    if len(text) > room:
        cut = text[: room - 1].rsplit(" ", 1)[0].rstrip(" ,;:")
        text = cut + "."
    desc = prefix + text
    if "!" in desc:
        raise SystemExit("exclamation in description for " + breed["slug"])
    return desc


def breadcrumb_ld(items):
    payload = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": index,
                "name": name,
                "item": url,
            }
            for index, (name, url) in enumerate(items, start=1)
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def head(title, description, canonical, image, image_w, image_h, image_alt, crumbs):
    image_meta = ""
    if image:
        image_meta = f"""
  <meta property="og:image" content="{esc(image)}">
  <meta property="og:image:width" content="{int(image_w)}">
  <meta property="og:image:height" content="{int(image_h)}">
  <meta property="og:image:type" content="image/webp">
  <meta property="og:image:alt" content="{esc(image_alt)}">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:image" content="{esc(image)}">
  <meta name="twitter:image:alt" content="{esc(image_alt)}">"""
    else:
        image_meta = """
  <meta name="twitter:card" content="summary">"""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(description)}">
  <meta name="theme-color" content="#F5EDDC">
  <meta name="color-scheme" content="light">
  <link rel="canonical" href="{esc(canonical)}">
  <link rel="preload" href="/fonts/fraunces-latin.woff2" as="font" type="font/woff2" crossorigin>
  <link rel="preload" href="/fonts/nunito-latin.woff2" as="font" type="font/woff2" crossorigin>
  <link rel="stylesheet" href="/styles.css">
  <link rel="icon" href="/favicon.ico" sizes="16x16 32x32 48x48">
  <link rel="icon" type="image/png" sizes="32x32" href="/favicon-32.png">
  <link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">
  <meta property="og:type" content="website">
  <meta property="og:url" content="{esc(canonical)}">
  <meta property="og:site_name" content="Dog Unpacked">
  <meta property="og:title" content="{esc(title)}">
  <meta property="og:description" content="{esc(description)}">
  <meta name="twitter:title" content="{esc(title)}">
  <meta name="twitter:description" content="{esc(description)}">{image_meta}
  <script type="application/ld+json">
{breadcrumb_ld(crumbs)}
  </script>
</head>
"""


def header(current):
    breeds_current = ' aria-current="page"' if current == "breeds" else ""
    return f"""<body>
  <a class="skip-link" href="#main">Skip to content</a>
  <header class="site-header">
    <div class="wrap header-inner">
      <a class="brand" href="/">
        <img src="/images/logo-256.webp" width="40" height="40" alt="">
        <span class="brand-word">Dog Unpacked</span>
      </a>
      <nav class="site-nav" aria-label="Site">
        <a class="nav-cta" href="/#subscribe">
          <span class="nav-cta-long">The Sniff Test</span>
          <span class="nav-cta-short">Subscribe</span>
        </a>
        <a class="nav-breeds" href="/breeds/"{breeds_current}>Breeds</a>
        <a class="nav-desktop" href="/#contact">Contact</a>
      </nav>
    </div>
  </header>
"""


def footer():
    return """  <footer class="footer" id="footer">
    <div class="wrap">
      <div class="footer-top">
        <div class="footer-brand-block">
          <p class="footer-brand">Dog Unpacked</p>
          <p class="footer-tag">He's not broken. He's bred that way.</p>
          <p class="footer-scope">Every breed, one at a time.</p>
        </div>
        <nav class="footer-nav" aria-label="Footer">
          <a href="/#subscribe">The Sniff Test</a>
          <a href="/breeds/">Breeds</a>
          <a href="/#contact">Contact</a>
          <a href="https://www.youtube.com/@DogUnpacked?sub_confirmation=1" rel="noopener noreferrer" target="_blank">YouTube<span class="visually-hidden"> (opens in a new tab)</span></a>
          <a href="https://www.instagram.com/dogunpacked" rel="noopener noreferrer" target="_blank">Instagram<span class="visually-hidden"> (opens in a new tab)</span></a>
          <a href="https://www.tiktok.com/@dogsunpacked" rel="noopener noreferrer" target="_blank">TikTok<span class="visually-hidden"> (opens in a new tab)</span></a>
        </nav>
      </div>
      <div class="footer-legal">
        <p>&copy; Dog Unpacked 2026</p>
        <p class="footer-disclaimer">Educational content only — not veterinary or training advice.</p>
        <p class="footer-privacy">Privacy: we store your email with Kit to send the newsletter, and contact messages are delivered by Formspree. Unsubscribe anytime.</p>
      </div>
    </div>
  </footer>
"""


def source_line(name, url):
    return (
        f'<p class="fact-source">Source: <a href="{esc(url)}">{esc(name)}</a></p>'
    )


def photo_block(breed):
    photo = breed["photo"]
    if photo.get("placeholder"):
        initial = esc(breed["name"][:1])
        return f"""<div class="breed-hero-photo breed-hero-photo--empty" role="img" aria-label="No photo yet for {esc(breed['name'])}">
        <span aria-hidden="true">{initial}</span>
        <p>Photo coming. The facts below do not depend on one.</p>
      </div>"""
    license_bit = esc(photo["license"])
    if photo.get("license_url"):
        license_bit = f'<a href="{esc(photo["license_url"])}">{esc(photo["license"])}</a>'
    return f"""<figure class="breed-hero-photo">
        <img src="/{esc(photo["file"])}" width="{int(photo["width"])}" height="{int(photo["height"])}" alt="{esc(photo.get("alt") or breed["name"])}" decoding="async" fetchpriority="high">
        <figcaption>Photo: {esc(photo["author"])}. {license_bit}. <a href="{esc(photo["source_url"])}">Source</a>.</figcaption>
      </figure>"""


def breed_page(breed):
    slug = breed["slug"]
    canonical = f"{SITE}/breeds/{slug}/"
    description = meta_description(breed)
    title = f"{breed['name']} — Dog Unpacked"
    photo = breed["photo"]
    if photo.get("placeholder"):
        image = f"{SITE}/images/og-image.png"
        image_w, image_h, image_alt = 1200, 630, "Dog Unpacked logo"
    else:
        image = f"{SITE}/{photo['file']}"
        image_w, image_h = photo["width"], photo["height"]
        image_alt = photo.get("alt") or breed["name"]
    crumbs = [
        ("Dog Unpacked", f"{SITE}/"),
        ("Breeds", f"{SITE}/breeds/"),
        (breed["name"], canonical),
    ]
    facts = []
    for fact in breed["facts"]:
        facts.append(
            "<li><p>"
            + esc(fact["text"])
            + "</p>"
            + source_line(fact["source_name"], fact["source_url"])
            + "</li>"
        )
    atts = ""
    if breed.get("atts"):
        atts = f"""<section class="breed-block" aria-labelledby="atts-heading">
        <h2 id="atts-heading">Temperament test</h2>
        <p>{esc(breed["atts"]["text"])}</p>
        {source_line(breed["atts"]["source_name"], breed["atts"]["source_url"])}
        <p class="breed-note">{esc(breed["atts"]["note"])}</p>
      </section>"""
    video_html = ""
    vids = videos_for(breed)
    if vids:
        links = []
        for vid in vids:
            url = "https://www.youtube.com/watch?v=" + vid["id"]
            links.append(
                f'<li><a href="{esc(url)}" rel="noopener noreferrer" target="_blank">{esc(vid["title"])}<span class="visually-hidden"> (opens in a new tab)</span></a></li>'
            )
        video_html = f"""<section class="breed-block" aria-labelledby="video-heading">
        <h2 id="video-heading">On YouTube</h2>
        <ul class="breed-links">{"".join(links)}</ul>
      </section>"""
    kicker = breed.get("group_label") or breed["group"]
    signup = breed.get("signup_slug") or slug
    page = f"""{head(title, description, canonical, image, image_w, image_h, image_alt, crumbs)}
{header("breeds")}
  <main id="main">
    <article class="wrap breed-article">
      <nav class="crumbs" aria-label="Breadcrumb">
        <a href="/">Dog Unpacked</a>
        <span aria-hidden="true">/</span>
        <a href="/breeds/">Breeds</a>
        <span aria-hidden="true">/</span>
        <span aria-current="page">{esc(breed["name"])}</span>
      </nav>
      <p class="kicker">{esc(kicker)}</p>
      <h1>{esc(breed["name"])}</h1>
      {photo_block(breed)}
      <section class="breed-block" aria-labelledby="job-heading">
        <h2 id="job-heading">The job</h2>
        <p>{esc(breed["job"]["text"])}</p>
        {source_line(breed["job"]["source_name"], breed["job"]["source_url"])}
      </section>
      <section class="breed-block" aria-labelledby="facts-heading">
        <h2 id="facts-heading">Facts</h2>
        <ol class="fact-list">
          {"".join(facts)}
        </ol>
      </section>
      <section class="breed-block" aria-labelledby="home-heading">
        <h2 id="home-heading">What that means at home</h2>
        <p>{esc(breed["home"])}</p>
        <p class="breed-note">This follows from the job above.</p>
      </section>
      {atts}
      {video_html}
      <section class="breed-signup" aria-labelledby="sniff-heading">
        <h2 id="sniff-heading">The Sniff Test</h2>
        <p>One behavior, one job, one study. The same Sunday letter for every dog.</p>
        <a class="btn btn--primary" href="/?breed={esc(signup)}#subscribe">Get The Sniff Test</a>
      </section>
    </article>
  </main>
{footer()}
</body>
</html>
"""
    return page


def index_page(breeds):
    canonical = f"{SITE}/breeds/"
    title = "Dog breeds — Dog Unpacked"
    description = (
        "AKC-recognized breeds, plus American Pit Bull Terrier and mixed breed. "
        "Each page gives the original job, sourced facts, and a photo."
    )
    crumbs = [("Dog Unpacked", f"{SITE}/"), ("Breeds", canonical)]
    buttons = ['<button type="button" class="group-filter" data-group="" aria-pressed="true">All</button>']
    present = {b["group"] for b in breeds}
    for group in GROUPS:
        if group in present:
            buttons.append(
                f'<button type="button" class="group-filter" data-group="{esc(group)}" aria-pressed="false">{esc(group)}</button>'
            )
    cards = []
    for breed in breeds:
        photo = breed["photo"]
        search = " ".join(
            [breed["name"], breed["slug"].replace("-", " ")]
            + list(breed.get("aliases") or [])
            + list(breed.get("nicknames") or [])
        ).lower()
        if photo.get("placeholder"):
            media = f'<span class="breed-card-fallback" aria-hidden="true">{esc(breed["name"][:1])}</span>'
        else:
            media = (
                f'<img src="/{esc(photo["thumb"])}" width="{int(photo["thumb_width"])}" height="{int(photo["thumb_height"])}" '
                f'alt="" loading="lazy" decoding="async">'
            )
        cards.append(
            f'<a class="breed-card" href="/breeds/{esc(breed["slug"])}/" data-group="{esc(breed["group"])}" data-name="{esc(search)}">{media}<span>{esc(breed["name"])}</span></a>'
        )
    page = f"""{head(title, description, canonical, f"{SITE}/images/og-image.png", 1200, 630, "Dog Unpacked logo", crumbs)}
{header("breeds")}
  <main id="main">
    <div class="wrap breed-index">
      <nav class="crumbs" aria-label="Breadcrumb">
        <a href="/">Dog Unpacked</a>
        <span aria-hidden="true">/</span>
        <span aria-current="page">Breeds</span>
      </nav>
      <p class="kicker">Every breed, one at a time</p>
      <h1>Breeds</h1>
      <p class="dek">The job comes first. Open a breed and read what it was built to do.</p>
      <p class="breed-intro">The American Kennel Club's breeds-by-year list names 205 breeds, with one entry called Fox Terrier. Smooth Fox Terrier and Wire Fox Terrier each have a page here, because AKC publishes a separate standard for each. Toy Fox Terrier is already its own breed. American Pit Bull Terrier is included from the United Kennel Club. Mixed breed has a page of its own.</p>
      <div class="breed-tools">
        <div class="field">
          <label for="breed-search">Search breeds</label>
          <input id="breed-search" type="search" autocomplete="off" spellcheck="false" placeholder="Type a breed">
        </div>
        <div class="group-filters" role="group" aria-label="Filter by AKC group">
          {"".join(buttons)}
        </div>
      </div>
      <p id="breed-empty" class="breed-empty" hidden>No breed matches that search.</p>
      <div class="breed-directory" id="breed-directory">
        {"".join(cards)}
      </div>
    </div>
  </main>
{footer()}
  <script src="/breeds/filter.js" defer></script>
</body>
</html>
"""
    return page


def write_sitemap(breeds):
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
        "  <url><loc>https://dogunpacked.com/</loc></url>",
        "  <url><loc>https://dogunpacked.com/breeds/</loc></url>",
    ]
    for breed in breeds:
        lines.append(f"  <url><loc>https://dogunpacked.com/breeds/{breed['slug']}/</loc></url>")
    lines.append("</urlset>")
    SITEMAP.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_csv(breeds):
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CSV_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["breed", "fact", "source_url"])
        for breed in breeds:
            writer.writerow([breed["name"], breed["job"]["text"], breed["job"]["source_url"]])
            for fact in breed["facts"]:
                writer.writerow([breed["name"], fact["text"], fact["source_url"]])
            if breed.get("atts"):
                writer.writerow([breed["name"], breed["atts"]["text"], breed["atts"]["source_url"]])


def write_credits(breeds):
    rows = [
        "| File | Breed | Author | License | License URL | Source |",
        "|---|---|---|---|---|---|",
    ]
    placeholders = []
    for breed in breeds:
        photo = breed["photo"]
        if photo.get("placeholder"):
            placeholders.append(breed["name"])
            continue
        files = f"`{photo['file']}`, `{photo['thumb']}`"
        rows.append(
            "| "
            + " | ".join(
                [
                    files,
                    breed["name"].replace("|", "/"),
                    photo["author"].replace("|", "/"),
                    photo["license"].replace("|", "/"),
                    photo.get("license_url") or "",
                    photo["source_url"],
                ]
            )
            + " |"
        )
    note = ""
    if placeholders:
        note = "\n\nPlaceholder (no verified photo yet): " + ", ".join(placeholders) + ".\n"
    block = (
        "\n## Breed directory\n\n"
        "Generated by `scripts/build_breeds.py` from `data/breeds.json`. "
        "Do not edit this table by hand. Swap a photo by replacing the files "
        "and the `photo` object, then rerun the script.\n\n"
        + "\n".join(rows)
        + note
    )
    text = CREDITS.read_text(encoding="utf-8")
    if CREDIT_START not in text:
        text = text.rstrip() + "\n\n" + CREDIT_START + "\n" + CREDIT_END + "\n"
    start = text.index(CREDIT_START)
    end = text.index(CREDIT_END)
    CREDITS.write_text(text[:start] + CREDIT_START + "\n" + block + "\n" + text[end:], encoding="utf-8")


def main():
    breeds = load()
    # Drop generated pages that are no longer in the data file.
    if BREEDS_DIR.exists():
        keep = {b["slug"] for b in breeds}
        for path in BREEDS_DIR.iterdir():
            if path.is_dir() and path.name not in keep and path.name != "filter.js":
                index = path / "index.html"
                if index.exists():
                    index.unlink()
                try:
                    path.rmdir()
                except OSError:
                    pass
    (BREEDS_DIR / "index.html").write_text(index_page(breeds), encoding="utf-8")
    for breed in breeds:
        folder = BREEDS_DIR / breed["slug"]
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "index.html").write_text(breed_page(breed), encoding="utf-8")
    write_sitemap(breeds)
    write_csv(breeds)
    write_credits(breeds)
    photos = sum(1 for b in breeds if not b["photo"].get("placeholder"))
    print(f"Wrote {len(breeds)} breed pages ({photos} with photos) and /breeds/.")


if __name__ == "__main__":
    main()
