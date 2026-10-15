#!/usr/bin/env python3
"""Build the /articles/ hub from data/articles.json.

Python standard library only. No network. GitHub Pages serves the HTML this
writes. Article pages keep their own URLs; this script only writes the hub
and refreshes sitemap.xml.

    python3 scripts/build_articles.py

To add an article, publish its HTML (the meta description is the card dek),
add one object to data/articles.json, and run this script.
"""

import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "articles.json"
BREEDS = ROOT / "data" / "breeds.json"
ARTICLES_DIR = ROOT / "articles"
SITE = "https://dogunpacked.com"
HUB_TITLE = "Dog Breed Behavior Articles | Dog Unpacked"
HUB_DESC = "Behavior articles from Dog Unpacked on why dogs do what their breed was built for."
HUB_H1 = "Dog breed behavior articles"
HUB_DEK = "Why dogs do what their breed was built for."
MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
PATH_RE = re.compile(r"^/(?:[a-z0-9]+(?:-[a-z0-9]+)*/)+$")
META_RE = re.compile(r'<meta name="description" content="([^"]*)">')
HREF_RE = re.compile(r'\b(?:href|src)="([^"]+)"')
SRCSET_RE = re.compile(r'\bsrcset="([^"]+)"')
CADENCE_RE = re.compile(
    r"\bevery (?:week|day|sunday)\b|\bweekly\b|\bnew articles every\b",
    re.I,
)
BANNED_PHRASES = ("breed files", "bred that way", "facebook")
SIZES = "(min-width: 1040px) 22rem, (min-width: 720px) 32rem, calc(100vw - 2rem)"

# Above-the-fold rules. styles.css repeats them so the deferred sheet does not move the layout.
CRITICAL_CSS = """
    @font-face{font-family:"Nunito Fallback";src:local("Arial"),local("Helvetica"),local("Liberation Sans");size-adjust:100%;ascent-override:101%;descent-override:35%;line-gap-override:0%}
    @font-face{font-family:"Fraunces Fallback";src:local("Georgia"),local("Times New Roman"),local("Liberation Serif");size-adjust:96%;ascent-override:102%;descent-override:27%;line-gap-override:0%}
    :root{--navy:#1B2A4A;--navy-muted:#4F5D78;--cream:#F5EDDC;--cream-deep:#EFE6D4;--amber:#D89B3D;--border:#E0D4BC;--border-strong:#CDBE9E;--radius:14px;--header:3.5rem}
    *,*::before,*::after{box-sizing:border-box}
    .skip-link{position:absolute;left:.75rem;top:-3.5rem}
    .visually-hidden{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}
    body{margin:0;font-family:"Nunito Fallback",system-ui,sans-serif;font-size:1.0625rem;line-height:1.55;color:var(--navy);background:linear-gradient(180deg,#F8F3E8 0%,var(--cream) 28%,var(--cream-deep) 100%)}
    img,svg{max-width:100%;height:auto}
    .site-header{position:sticky;top:0;z-index:30;min-height:var(--header);background:rgba(245,237,220,.96);border-bottom:1px solid var(--border)}
    .header-inner{display:flex;align-items:center;justify-content:space-between;gap:.75rem;min-height:var(--header);width:min(100% - 2rem,68rem);margin-inline:auto}
    .brand{display:inline-flex;align-items:center;gap:.6rem;min-height:44px;color:var(--navy);text-decoration:none;font-weight:800}
    .brand img{width:40px;height:40px;border-radius:50%}
    .brand-word{font-size:1rem;line-height:1.1;white-space:nowrap}
    .site-nav{display:flex;align-items:center;gap:.15rem}
    .site-nav a{display:inline-flex;align-items:center;justify-content:center;min-height:44px;padding:.4rem .7rem;border-radius:999px;color:var(--navy);text-decoration:none;font-weight:800;font-size:.92rem;white-space:nowrap}
    .site-nav a.nav-cta{background:var(--navy);color:var(--cream);padding-inline:.9rem}
    .nav-cta-short,.site-nav a.nav-desktop{display:none}
    .article-hub{width:min(100% - 2rem,68rem);margin-inline:auto;padding:1.25rem 0 3.5rem}
    .article-hub h1{margin:0;font-family:"Fraunces Fallback",Georgia,serif;font-size:clamp(1.9rem,4.8vw,2.7rem);font-weight:700;letter-spacing:-.03em;line-height:1.12}
    .crumbs{display:flex;flex-wrap:wrap;gap:.35rem;align-items:center;margin:0 0 .9rem;color:var(--navy-muted);font-size:.88rem;font-weight:700}
    .crumbs a{color:var(--navy);font-weight:800;text-decoration:none}
    .article-dek{margin:.7rem 0 0;color:var(--navy-muted);font-weight:700}
    .article-list{display:grid;gap:.9rem;margin:1rem 0 0;padding:0;list-style:none}
    .article-card{display:grid;background:var(--navy);color:var(--cream);border-radius:14px;overflow:hidden}
    .article-card-link{display:grid;color:inherit;text-decoration:none}
    .article-card-media{display:block;background:#111}
    .article-card-media img{display:block;width:100%;height:auto;background:#111}
    .article-card-body{display:grid;gap:.35rem;padding:.75rem .95rem .9rem}
    .article-card h2{margin:0;color:var(--cream);font-family:"Fraunces Fallback",Georgia,serif;font-size:1.15rem;font-weight:700;line-height:1.25}
    .article-card-dek{margin:0;color:var(--cream);font-size:.92rem;font-weight:700;line-height:1.35}
    .article-card time{color:var(--cream);font-size:.88rem;font-weight:800}
    .article-card-breed{margin:0;padding:0 .95rem .9rem}
    .article-card-breed a{display:inline-flex;align-items:center;min-height:44px;color:var(--cream);font-weight:800}
    @media (max-width:640px){.nav-cta-long{display:none}.nav-cta-short{display:inline}.header-inner{gap:.25rem}.brand{gap:.3rem}.brand img{width:32px;height:32px}.brand-word{font-size:.75rem}.site-nav{gap:0}.site-nav a{padding:.2rem .26rem;font-size:.75rem}.site-nav a.nav-cta{padding-inline:.4rem}}
    @media (min-width:720px){.article-list{grid-template-columns:1fr 1fr}}
    @media (min-width:840px){.site-nav a.nav-desktop{display:inline-flex}}
"""


def esc(value):
    return html.escape(str(value), quote=True)


def has_emoji(text):
    for char in text:
        code = ord(char)
        if (
            code > 0xFFFF
            or 0x1F000 <= code <= 0x1FAFF
            or 0x2600 <= code <= 0x27BF
            or 0xFE00 <= code <= 0xFE0F
        ):
            return True
    return False


def check_copy(label, text):
    if "!" in text or has_emoji(text):
        raise SystemExit(f"{label} has an exclamation mark or emoji")
    lowered = text.lower()
    for phrase in BANNED_PHRASES:
        if phrase in lowered:
            raise SystemExit(f"{label} mentions {phrase}")
    if CADENCE_RE.search(text):
        raise SystemExit(f"{label} makes a cadence promise")


def format_day(stamp):
    year, month, day = stamp.split("-")
    return f"{MONTHS[int(month) - 1]} {int(day)}, {year}"


def load_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except ValueError as error:
        raise SystemExit(f"{path.relative_to(ROOT)} is not valid JSON ({error})") from error


def breed_names():
    payload = load_json(BREEDS)
    return {breed["slug"]: breed["name"] for breed in payload["breeds"]}


def local_file(url):
    if not url.startswith("/") or url.startswith("//"):
        return None
    path = url.split("#", 1)[0].split("?", 1)[0]
    if path in ("", "/"):
        return ROOT / "index.html"
    rel = path.lstrip("/")
    if path.endswith("/"):
        return ROOT / rel / "index.html"
    return ROOT / rel


def require_file(url, label):
    path = local_file(url)
    if path is None or not path.is_file():
        raise SystemExit(f"{label} does not resolve: {url}")
    return path


def srcset_urls(srcset):
    urls = []
    for part in str(srcset or "").split(","):
        bits = part.strip().split()
        if len(bits) != 2 or not bits[0].startswith("/") or not bits[1].endswith("w"):
            raise SystemExit(f"bad image srcset: {srcset}")
        urls.append(bits[0])
    if not urls:
        raise SystemExit("image srcset is empty")
    return urls


def load_articles(names):
    if not DATA.is_file():
        raise SystemExit("data/articles.json is missing")
    payload = load_json(DATA)
    if not isinstance(payload, list):
        raise SystemExit("data/articles.json must be a list")
    articles = []
    seen = set()
    for item in payload:
        if not isinstance(item, dict):
            raise SystemExit("each article must be an object")
        path = str(item.get("path") or "")
        title = str(item.get("title") or "").strip()
        description = str(item.get("description") or "").strip()
        published = str(item.get("published") or "")
        breed = str(item.get("breed") or "")
        image = str(item.get("image") or "")
        if not PATH_RE.fullmatch(path):
            raise SystemExit(f"bad article path: {path}")
        if path in seen:
            raise SystemExit(f"duplicate article path: {path}")
        seen.add(path)
        if not title or not description:
            raise SystemExit(f"{path} needs a title and description")
        if not DATE_RE.fullmatch(published):
            raise SystemExit(f"{path} published must be YYYY-MM-DD")
        if breed not in names:
            raise SystemExit(f"{path} breed is not in breeds.json: {breed}")
        try:
            width = int(item.get("width"))
            height = int(item.get("height"))
            og_width = int(item.get("og_width"))
            og_height = int(item.get("og_height"))
        except (TypeError, ValueError):
            raise SystemExit(f"{path} image dimensions must be integers") from None
        if min(width, height, og_width, og_height) < 1:
            raise SystemExit(f"{path} image dimensions must be positive")
        og_image = str(item.get("og_image") or "")
        alt = str(item.get("alt") or "").strip()
        if not alt:
            raise SystemExit(f"{path} needs image alt text")
        require_file(path, "article page")
        require_file(image, "article image")
        require_file(og_image, "article share image")
        for url in srcset_urls(item.get("image_srcset")):
            require_file(url, "article image srcset")
        if image not in srcset_urls(item.get("image_srcset")):
            raise SystemExit(f"{path} image is not in its srcset")
        page = (ROOT / path.strip("/") / "index.html").read_text(encoding="utf-8")
        meta = META_RE.search(page)
        if meta is None or html.unescape(meta.group(1)) != description:
            raise SystemExit(f"{path} description must match that page's meta description")
        if f"<h1>{title}</h1>" not in page:
            raise SystemExit(f"{path} title must match that page's h1")
        if 'class="nav-articles" href="/articles/" aria-current="page"' not in page:
            raise SystemExit(f"{path} must show the Articles tab as current")
        if '<a href="/">Home</a>' not in page or '<a href="/articles/">Articles</a>' not in page:
            raise SystemExit(f"{path} breadcrumb must be Home, then Articles")
        if "https://dogunpacked.com/articles/" not in page:
            raise SystemExit(f"{path} BreadcrumbList must include Articles")
        check_copy(f"{path} title", title)
        check_copy(f"{path} description", description)
        check_copy(f"{path} alt", alt)
        articles.append({
            "title": title,
            "path": path,
            "description": description,
            "published": published,
            "breed": breed,
            "breed_name": names[breed],
            "image": image,
            "image_srcset": ", ".join(part.strip() for part in str(item["image_srcset"]).split(",")),
            "width": width,
            "height": height,
            "alt": alt,
            "og_image": og_image,
            "og_width": og_width,
            "og_height": og_height,
        })
    articles.sort(key=lambda article: (article["published"], article["title"]), reverse=True)
    return articles


def check_hub_copy():
    if len(HUB_TITLE) > 60:
        raise SystemExit(f"hub title is {len(HUB_TITLE)} characters")
    if len(HUB_DESC) > 155 or not HUB_DESC.endswith(".") or ". " in HUB_DESC:
        raise SystemExit("hub meta description must be one sentence under 155 characters")
    for label, text in (
        ("hub title", HUB_TITLE),
        ("hub description", HUB_DESC),
        ("hub heading", HUB_H1),
        ("hub dek", HUB_DEK),
    ):
        check_copy(label, text)
    if format_day("2026-10-14") != "October 14, 2026":
        raise SystemExit("date formatting drifted")


def json_script(payload):
    body = json.dumps(payload, ensure_ascii=False, indent=2).replace("<", "\\u003c")
    return f'  <script type="application/ld+json">\n{body}\n  </script>'


def breadcrumb(items):
    return {
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


def header():
    return """  <a class="skip-link" href="#main">Skip to content</a>
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
        <a class="nav-breeds" href="/breeds/">Breeds</a>
        <a class="nav-videos" href="/videos/">Videos</a>
        <a class="nav-articles" href="/articles/" aria-current="page">Articles</a>
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
          <a href="/videos/">Videos</a>
          <a href="/articles/">Articles</a>
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


def goatcounter():
    return """  <script>
    (function () {
      var s = document.createElement("script");
      s.async = true;
      s.setAttribute("data-goatcounter", "https://dogunpackedcom.goatcounter.com/count");
      function start() { s.src = "https://gc.zgo.at/count.js"; }
      if (document.readyState === "complete") start();
      else window.addEventListener("load", start);
      document.body.appendChild(s);
    })();
  </script>
"""


def head(articles):
    first = articles[0] if articles else None
    preload = ""
    image_meta = """
  <meta name="twitter:card" content="summary">"""
    if first:
        preload = (
            f'\n  <link rel="preload" as="image" href="{esc(first["image"])}" type="image/webp" fetchpriority="high"'
            f' imagesrcset="{esc(first["image_srcset"])}" imagesizes="{esc(SIZES)}">'
        )
        image = f"{SITE}{first['og_image']}"
        image_meta = f"""
  <meta property="og:image" content="{esc(image)}">
  <meta property="og:image:width" content="{first['og_width']}">
  <meta property="og:image:height" content="{first['og_height']}">
  <meta property="og:image:type" content="image/webp">
  <meta property="og:image:alt" content="{esc(first['alt'])}">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:image" content="{esc(image)}">
  <meta name="twitter:image:alt" content="{esc(first['alt'])}">"""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{esc(HUB_TITLE)}</title>
  <meta name="description" content="{esc(HUB_DESC)}">
  <meta name="theme-color" content="#F5EDDC">
  <meta name="color-scheme" content="light">
  <link rel="canonical" href="{SITE}/articles/">{preload}
  <style>{CRITICAL_CSS}
  </style>
  <noscript><link rel="stylesheet" href="/styles.css"></noscript>
  <script>
    requestAnimationFrame(function () {{
      requestAnimationFrame(function () {{
        var link = document.createElement("link");
        link.rel = "stylesheet";
        link.href = "/styles.css";
        document.head.appendChild(link);
      }});
    }});
  </script>
  <link rel="icon" href="/favicon.ico" sizes="16x16 32x32 48x48">
  <link rel="icon" type="image/png" sizes="32x32" href="/favicon-32.png">
  <link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">
  <meta property="og:type" content="website">
  <meta property="og:url" content="{SITE}/articles/">
  <meta property="og:site_name" content="Dog Unpacked">
  <meta property="og:title" content="{esc(HUB_TITLE)}">
  <meta property="og:description" content="{esc(HUB_DESC)}">
  <meta name="twitter:title" content="{esc(HUB_TITLE)}">
  <meta name="twitter:description" content="{esc(HUB_DESC)}">{image_meta}
</head>
"""


def card(article, index):
    eager = index == 0
    loading = ' loading="eager"' if eager else ' loading="lazy"'
    fetchpriority = ' fetchpriority="high"' if eager else ""
    decoding = "sync" if eager else "async"
    return (
        '<li class="article-card">'
        f'<a class="article-card-link" href="{esc(article["path"])}">'
        '<span class="article-card-media">'
        f'<img src="{esc(article["image"])}" srcset="{esc(article["image_srcset"])}" sizes="{esc(SIZES)}" '
        f'width="{article["width"]}" height="{article["height"]}" alt=""{loading}{fetchpriority} decoding="{decoding}">'
        "</span>"
        '<span class="article-card-body">'
        f'<h2>{esc(article["title"])}</h2>'
        f'<p class="article-card-dek">{esc(article["description"])}</p>'
        f'<time datetime="{esc(article["published"])}">{esc(format_day(article["published"]))}</time>'
        "</span></a>"
        f'<p class="article-card-breed"><a href="/breeds/{esc(article["breed"])}/">{esc(article["breed_name"])}</a></p>'
        "</li>"
    )


def hub_page(articles):
    graph = {
        "@context": "https://schema.org",
        "@graph": [
            breadcrumb([("Home", f"{SITE}/"), ("Articles", f"{SITE}/articles/")]),
            {
                "@type": "ItemList",
                "name": HUB_TITLE,
                "numberOfItems": len(articles),
                "itemListElement": [
                    {
                        "@type": "ListItem",
                        "position": index,
                        "name": article["title"],
                        "url": f"{SITE}{article['path']}",
                    }
                    for index, article in enumerate(articles, start=1)
                ],
            },
        ],
    }
    cards = "".join(card(article, index) for index, article in enumerate(articles))
    return f"""{head(articles)}
<body>
{header()}
  <main id="main">
    <div class="article-hub">
      <nav class="crumbs" aria-label="Breadcrumb">
        <a href="/">Home</a>
        <span aria-hidden="true">/</span>
        <span aria-current="page">Articles</span>
      </nav>
      <h1>{esc(HUB_H1)}</h1>
      <p class="article-dek">{esc(HUB_DEK)}</p>
      <ul class="article-list">
        {cards}
      </ul>
    </div>
  </main>
{footer()}
{json_script(graph)}
{goatcounter()}</body>
</html>
"""


def check_links(page):
    urls = HREF_RE.findall(page)
    for srcset in SRCSET_RE.findall(page):
        for part in srcset.split(","):
            bits = part.strip().split()
            if bits:
                urls.append(bits[0])
    for url in urls:
        if url.startswith(("#", "http://", "https://", "mailto:", "tel:")):
            continue
        require_file(url, "hub link")


def check_jsonld(page):
    blocks = re.findall(
        r'<script type="application/ld\+json">\s*(.*?)\s*</script>',
        page,
        flags=re.S,
    )
    if len(blocks) != 1:
        raise SystemExit(f"expected one JSON-LD block, found {len(blocks)}")
    try:
        payload = json.loads(blocks[0])
    except ValueError as error:
        raise SystemExit(f"JSON-LD did not parse ({error})") from error
    types = [node.get("@type") for node in payload.get("@graph", [])]
    if "BreadcrumbList" not in types or "ItemList" not in types:
        raise SystemExit(f"JSON-LD graph is missing BreadcrumbList or ItemList: {types}")
    return payload


def refresh_sitemap():
    import build_sitemap

    build_sitemap.write()


def main():
    check_hub_copy()
    articles = load_articles(breed_names())
    page = hub_page(articles)
    payload = check_jsonld(page)
    listed = payload["@graph"][1]["numberOfItems"]
    if listed != len(articles):
        raise SystemExit("ItemList count does not match the cards")
    ARTICLES_DIR.mkdir(parents=True, exist_ok=True)
    (ARTICLES_DIR / "index.html").write_text(page, encoding="utf-8")
    check_links(page)
    refresh_sitemap()
    print(f"Wrote /articles/ with {len(articles)} article{'s' if len(articles) != 1 else ''}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
