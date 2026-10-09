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
GOATCOUNTER_SNIPPET = (
    '<script data-goatcounter="https://dogunpackedcom.goatcounter.com/count" '
    'async src="//gc.zgo.at/count.js"></script>'
)
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
        if len(breed["facts"]) > 3:
            raise SystemExit(f"more than 3 facts for {breed['slug']}")
        blob = " ".join(
            [breed["name"], breed["job"]["text"]]
            + [fact["text"] for fact in breed["facts"]]
        )
        if breed.get("atts"):
            blob += " " + breed["atts"]["text"]
        if "!" in blob:
            raise SystemExit(f"exclamation mark in {breed['slug']}")
        if BANNED.search(blob):
            raise SystemExit(f"banned word in {breed['slug']}: {BANNED.search(blob).group(0)}")
        if re.search(r"working\s*&\s*power breeds", blob, re.I):
            raise SystemExit(f"banned phrase in {breed['slug']}")
        if "@" in blob:
            raise SystemExit(f"@ in breed copy for {breed['slug']}")
        texts = [breed["job"]["text"]] + [fact["text"] for fact in breed["facts"]]
        for i, left in enumerate(texts):
            for right in texts[i + 1 :]:
                if similarity(left, right) > 0.6:
                    raise SystemExit(f"near-duplicate copy in {breed['slug']}")
        photo = breed.get("photo") or {}
        author = photo.get("author") or ""
        if not photo.get("placeholder"):
            if any(mark in author for mark in ("!", "@")) or "http" in author.lower() or "www." in author.lower():
                raise SystemExit(f"messy photo credit for {breed['slug']}: {author}")
        videos_for(breed)
    ids = []
    for breed in breeds:
        for item in breed.get("videos") or []:
            ids.append(item["id"])
    if len(ids) != len(set(ids)):
        raise SystemExit("same YouTube id is listed on more than one breed")
    return breeds


def similarity(left, right):
    stop = {
        "a", "an", "the", "of", "to", "and", "in", "for", "from", "with", "as", "by",
        "on", "at", "or", "that", "this", "was", "were", "are", "is", "be", "been",
        "their", "its", "it", "they", "them", "his", "her", "who", "which",
    }

    def stems(text):
        words = re.sub(r"[^a-z0-9 ]", " ", text.lower()).split()
        out = []
        for word in words:
            if word in stop or len(word) <= 2:
                continue
            if word.endswith("ies") and len(word) > 4:
                word = word[:-3] + "y"
            elif word.endswith("s") and not word.endswith("ss") and len(word) > 4:
                word = word[:-1]
            out.append(word)
        return out

    left_counts = {}
    right_counts = {}
    for word in stems(left):
        left_counts[word] = left_counts.get(word, 0) + 1
    for word in stems(right):
        right_counts[word] = right_counts.get(word, 0) + 1
    keys = set(left_counts) | set(right_counts)
    if not keys:
        return 0.0
    dot = sum(left_counts.get(key, 0) * right_counts.get(key, 0) for key in keys)
    left_norm = sum(value * value for value in left_counts.values()) ** 0.5
    right_norm = sum(value * value for value in right_counts.values()) ** 0.5
    if not left_norm or not right_norm:
        return 0.0
    return dot / (left_norm * right_norm)


VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")


def videos_for(breed):
    """Cards come from the breed's videos list, not from data/latest.json.

    latest.json only feeds the home page. Long videos (type "video") stay
    ahead of Shorts (type "short").
    """
    raw = breed.get("videos") or []
    if not isinstance(raw, list):
        raise SystemExit(f"videos must be a list for {breed['slug']}")
    found = []
    seen = set()
    saw_short = False
    for item in raw:
        if not isinstance(item, dict):
            raise SystemExit(f"bad video entry for {breed['slug']}")
        vid = item.get("id") or ""
        title = item.get("title") or ""
        kind = item.get("type") or ""
        url = item.get("url") or ""
        if not VIDEO_ID.fullmatch(vid):
            raise SystemExit(f"bad video id for {breed['slug']}: {vid}")
        if vid in seen:
            raise SystemExit(f"duplicate video id for {breed['slug']}: {vid}")
        seen.add(vid)
        if kind == "video":
            expect = "https://www.youtube.com/watch?v=" + vid
            if saw_short:
                raise SystemExit(f"long video listed after a Short for {breed['slug']}")
        elif kind == "short":
            expect = "https://www.youtube.com/shorts/" + vid
            saw_short = True
        else:
            raise SystemExit(f"video type must be video or short for {breed['slug']}")
        if url != expect:
            raise SystemExit(f"video url does not match type for {breed['slug']}: {url}")
        if not title.strip():
            raise SystemExit(f"missing video title for {breed['slug']}")
        published = item.get("published") or ""
        if published and not DATE_RE.fullmatch(published):
            raise SystemExit(f"bad video date for {breed['slug']}: {published}")
        found.append({"id": vid, "title": title, "type": kind, "url": url, "published": published})
    return found


def clip_sentence(text, room):
    text = text.strip()
    if len(text) <= room:
        return text
    cut = text[:room].rsplit(" ", 1)[0].rstrip(" ,;:")
    if len(cut) < 40:
        cut = text[:room].rstrip(" ,;:")
    if cut and not cut.endswith("."):
        cut += "."
    return cut


def meta_description(breed):
    """About 150 characters, using only this breed's job line and facts."""
    parts = [breed["job"]["text"].strip()] + [fact["text"].strip() for fact in breed["facts"]]
    desc = ""
    for part in parts:
        candidate = part if not desc else desc + " " + part
        if len(candidate) <= 155:
            desc = candidate
            continue
        if len(desc) < 130:
            room = 155 - (len(desc) + (1 if desc else 0))
            trimmed = clip_sentence(part, room)
            if trimmed:
                desc = (desc + " " + trimmed).strip()
        break
    if not desc:
        desc = clip_sentence(parts[0], 155)
    if "!" in desc or "@" in desc:
        raise SystemExit("bad character in description for " + breed["slug"])
    return desc


def page_title(name):
    """Search-style title. Shorten the shared ending so the result stays near 60 characters."""
    options = [
        f"{name}: Original Job, Origin and Size | Dog Unpacked",
        f"{name}: Job, Origin and Size | Dog Unpacked",
        f"{name}: Job, Origin, Size | Dog Unpacked",
        f"{name}: Job, Origin | Dog Unpacked",
        f"{name}: Origin | Dog Unpacked",
    ]
    for option in options:
        if len(option) <= 60:
            return option
    return min(options, key=len)


def related_breeds(breed, breeds):
    """Alphabetical neighbors in the same AKC group, wrapping at the ends. Up to four."""
    group = sorted(
        (item for item in breeds if item["group"] == breed["group"]),
        key=lambda item: item["name"].casefold(),
    )
    count = len(group)
    if count < 2:
        return []
    index = next(i for i, item in enumerate(group) if item["slug"] == breed["slug"])
    picked = []
    for step in range(1, count):
        for offset in (step, -step):
            picked.append(group[(index + offset) % count])
            if len(picked) == 4 or len(picked) == count - 1:
                return sorted(picked, key=lambda item: item["name"].casefold())
    return sorted(picked, key=lambda item: item["name"].casefold())


DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def json_ld(crumbs, videos=None):
    graph = [
        {
            "@type": "BreadcrumbList",
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": index,
                    "name": name,
                    "item": url,
                }
                for index, (name, url) in enumerate(crumbs, start=1)
            ],
        }
    ]
    for vid in videos or []:
        published = vid.get("published") or ""
        if not DATE_RE.fullmatch(published):
            continue
        graph.append(
            {
                "@type": "VideoObject",
                "name": vid["title"],
                "thumbnailUrl": "https://i.ytimg.com/vi/" + vid["id"] + "/hqdefault.jpg",
                "uploadDate": published,
                "embedUrl": "https://www.youtube.com/embed/" + vid["id"],
                "contentUrl": vid["url"],
            }
        )
    payload = {"@context": "https://schema.org", "@graph": graph}
    return json.dumps(payload, ensure_ascii=False, indent=2)


def head(title, description, canonical, image, image_w, image_h, image_alt, crumbs, videos=None, extra_head=""):
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
  <link rel="canonical" href="{esc(canonical)}">{extra_head}
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
{json_ld(crumbs, videos)}
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
        <a class="nav-cta" href="/#subscribe" aria-label="Free newsletter">
          <span class="nav-cta-long">Free newsletter</span>
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
          <a href="/#subscribe">The Sniff Test, the free newsletter</a>
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
        <p class="footer-privacy">Privacy: we store your email with Kit to send the newsletter, and contact messages are delivered by Formspree. Unsubscribe anytime. Page views are counted with GoatCounter, which uses no cookies.</p>
      </div>
    </div>
  </footer>
"""


def photo_block(breed):
    photo = breed["photo"]
    if photo.get("placeholder"):
        initial = esc(breed["name"][:1])
        return f"""<div class="breed-hero-photo breed-hero-photo--empty" role="img" aria-label="No photo yet for {esc(breed['name'])}">
        <span aria-hidden="true">{initial}</span>
      </div>"""
    return f"""<figure class="breed-hero-photo">
        <img src="/{esc(photo["file"])}" width="{int(photo["width"])}" height="{int(photo["height"])}" alt="{esc(photo.get("alt") or breed["name"])}" decoding="async" fetchpriority="high">
      </figure>"""


def credit_line(breed):
    seen = set()
    links = []
    items = [breed["job"]] + list(breed["facts"])
    if breed.get("atts"):
        items.append(breed["atts"])
    for item in items:
        url = item.get("source_url") or ""
        name = item.get("source_name") or ""
        if not url or url in seen:
            continue
        seen.add(url)
        links.append(f'<a href="{esc(url)}">{esc(name)}</a>')
    sources = ", ".join(links)
    photo = breed["photo"]
    if photo.get("placeholder"):
        return f'<p class="breed-credit">Sources: {sources}.</p>'
    license_bit = esc(photo["license"])
    if photo.get("license_url"):
        license_bit = f'<a href="{esc(photo["license_url"])}">{esc(photo["license"])}</a>'
    return (
        f'<p class="breed-credit">Photo: {esc(photo["author"])}. {license_bit}. '
        f'<a href="{esc(photo["source_url"])}">Image source</a>. Sources: {sources}.</p>'
    )


def signup_block(breed, invite):
    signup = breed.get("signup_slug") or breed["slug"]
    invite_html = ""
    if invite:
        invite_html = '<p class="signup-invite">If you want this breed covered, put the name in the breed field.</p>'
    return f"""<section class="breed-signup" aria-labelledby="sniff-heading">
        <p class="newsletter-eyebrow">Free weekly email</p>
        <h2 id="sniff-heading">The Sniff Test</h2>
        {invite_html}
        <p>A free email every Sunday: one behavior, one job, one study, and what to do tonight.</p>
        <p class="signup-when">About a two-minute read.</p>
        <a class="btn btn--primary" href="/?breed={esc(signup)}#subscribe" data-goatcounter-click="signup-from-breed-{esc(breed["slug"])}" data-goatcounter-title="{esc("Signup from " + breed["name"])}">Get the free newsletter</a>
        <p class="signup-free">Free. Unsubscribe anytime.</p>
      </section>"""


def video_block(breed):
    vids = videos_for(breed)
    if not vids:
        return ""
    links = []
    for vid in vids:
        kind = '<span class="breed-video-type">Short</span>' if vid["type"] == "short" else ""
        thumb = "https://i.ytimg.com/vi/" + vid["id"] + "/hqdefault.jpg"
        links.append(
            f'<a class="breed-video-link" href="{esc(vid["url"])}" rel="noopener noreferrer" target="_blank" data-goatcounter-click="video-from-breed-{esc(breed["slug"])}" data-goatcounter-title="{esc("Video from " + breed["name"])}">'
            f'<span class="breed-video-thumb">'
            f'<img src="{esc(thumb)}" width="480" height="360" alt="" loading="lazy" decoding="async" fetchpriority="low" referrerpolicy="no-referrer">'
            f'</span>'
            f'<span class="breed-video-copy">'
            f'<span class="breed-video-kicker">Dog Unpacked{kind}</span>'
            f'<span class="breed-video-title">{esc(vid["title"])}</span>'
            f'</span>'
            f'<span class="visually-hidden"> (opens in a new tab)</span></a>'
        )
    label = "Dog Unpacked video" if len(vids) == 1 else "Dog Unpacked videos"
    return f'<section class="breed-video" aria-label="{label}">{"".join(links)}</section>'


def related_block(breed, breeds):
    picks = related_breeds(breed, breeds)
    items = "".join(
        f'<li><a href="/breeds/{esc(item["slug"])}/">{esc(item["name"])}</a></li>'
        for item in picks
    )
    nav = ""
    if items:
        nav = f"""<nav class="related-breeds" aria-label="Related breeds">
        <h2>Related breeds</h2>
        <ul>
          {items}
        </ul>
      </nav>"""
    return nav + """
      <p class="breed-back"><a href="/breeds/">Breeds</a></p>"""


def breed_page(breed, breeds):
    slug = breed["slug"]
    canonical = f"{SITE}/breeds/{slug}/"
    description = meta_description(breed)
    title = page_title(breed["name"])
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
    fact_html = ""
    if breed["facts"]:
        items = "".join(f"<li><p>{esc(fact['text'])}</p></li>" for fact in breed["facts"])
        fact_html = f"""<section class="breed-block" aria-labelledby="facts-heading">
        <h2 id="facts-heading">Facts</h2>
        <ol class="fact-list">
          {items}
        </ol>
      </section>"""
    atts = ""
    if breed.get("atts"):
        atts = f"""<p class="breed-atts">{esc(breed["atts"]["text"])}</p>"""
    vids = videos_for(breed)
    video_html = video_block(breed)
    label = breed.get("group_label") or ""
    fact_blob = " ".join(fact["text"] for fact in breed["facts"]).lower()
    tag = ""
    if label and label.lower() not in {"other", "mixed breed"} and label.lower() not in fact_blob:
        tag = f'<p class="group-tag">{esc(label)}</p>'
    invite = not video_html
    page = f"""{head(title, description, canonical, image, image_w, image_h, image_alt, crumbs, vids)}
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
      {tag}
      <h1>{esc(breed["name"])}</h1>
      {photo_block(breed)}
      <section class="breed-block" aria-labelledby="job-heading">
        <h2 id="job-heading">The job</h2>
        <p>{esc(breed["job"]["text"])}</p>
      </section>
      {video_html if video_html else signup_block(breed, True)}
      {fact_html}
      {atts}
      {signup_block(breed, False) if video_html else ""}
      {credit_line(breed)}
      {related_block(breed, breeds)}
    </article>
  </main>
{footer()}
  {GOATCOUNTER_SNIPPET}
</body>
</html>
"""
    return page


def index_page(breeds):
    canonical = f"{SITE}/breeds/"
    title = "Dog breeds: job, origin and size | Dog Unpacked"
    description = (
        "Every breed the American Kennel Club recognizes, plus the American Pit Bull Terrier and mixed breeds. "
        "Each page lists the original job, origin and size."
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
    for index, breed in enumerate(breeds):
        photo = breed["photo"]
        search = " ".join(
            [breed["name"], breed["slug"].replace("-", " ")]
            + list(breed.get("aliases") or [])
            + list(breed.get("nicknames") or [])
        ).lower()
        if photo.get("placeholder"):
            media = f'<span class="breed-card-fallback" aria-hidden="true">{esc(breed["name"][:1])}</span>'
        else:
            # The first row is on screen at every breakpoint (2, 3, or 4 columns).
            # The first thumb is the LCP image, so it is eager and high priority.
            if index == 0:
                extra = ' fetchpriority="high" decoding="sync"'
            elif index < 4:
                extra = ' decoding="async"'
            else:
                extra = ' loading="lazy" decoding="async"'
            media = (
                f'<img src="/{esc(photo["thumb"])}" width="{int(photo["thumb_width"])}" height="{int(photo["thumb_height"])}" '
                f'alt="{esc(photo.get("alt") or breed["name"])}"{extra}>'
            )
        cards.append(
            f'<a class="breed-card" href="/breeds/{esc(breed["slug"])}/" data-group="{esc(breed["group"])}" data-name="{esc(search)}">{media}<span>{esc(breed["name"])}</span></a>'
        )
    first_thumb = ""
    for breed in breeds:
        photo = breed["photo"]
        if not photo.get("placeholder"):
            first_thumb = f'\n  <link rel="preload" as="image" href="/{esc(photo["thumb"])}" type="image/webp" fetchpriority="high">'
            break
    page = f"""{head(title, description, canonical, f"{SITE}/images/og-image.png", 1200, 630, "Dog Unpacked logo", crumbs, extra_head=first_thumb)}
{header("breeds")}
  <main id="main">
    <div class="wrap breed-index">
      <h1>Breeds</h1>
      <p class="breed-intro">Every breed the American Kennel Club recognizes, plus the American Pit Bull Terrier and mixed breeds.</p>
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
  {GOATCOUNTER_SNIPPET}
</body>
</html>
"""
    return page


def sitemap_url(loc):
    return f"  <url><loc>{loc}</loc><lastmod>2026-10-09</lastmod></url>"


def write_sitemap(breeds):
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
        sitemap_url("https://dogunpacked.com/"),
        sitemap_url("https://dogunpacked.com/breeds/"),
    ]
    for breed in breeds:
        lines.append(sitemap_url(f"https://dogunpacked.com/breeds/{breed['slug']}/"))
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
        (folder / "index.html").write_text(breed_page(breed, breeds), encoding="utf-8")
    write_sitemap(breeds)
    write_csv(breeds)
    write_credits(breeds)
    photos = sum(1 for b in breeds if not b["photo"].get("placeholder"))
    print(f"Wrote {len(breeds)} breed pages ({photos} with photos) and /breeds/.")


if __name__ == "__main__":
    main()
