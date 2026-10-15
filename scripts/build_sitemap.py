#!/usr/bin/env python3
"""Write sitemap.xml with one lastmod per page, from that file's last git commit.

Python standard library only. No network. The home page, /breeds/, and each
breed page stay in that order. Article URLs in ARTICLES are appended after
them:

    python3 scripts/build_sitemap.py

lastmod is the committer date of the last commit that touched the page, in
strict ISO 8601 (git %cI), for example 2026-10-12T23:34:28-04:00.
When data/videos.json exists, /videos/ and each long-form watch page are
appended after the article URLs. /articles/ is appended last when that hub
page exists, so the URLs already in the sitemap stay in order. A page that
has no commit yet is stamped with the current America/New_York time so the
first build can finish.
"""

import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "breeds.json"
SITEMAP = ROOT / "sitemap.xml"
SITE = "https://dogunpacked.com"
LOC_RE = re.compile(r"<loc>(.*?)</loc>")
ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})$")
BASE_URL_COUNT = 211
ARTICLES = [
    (
        ROOT / "german-shepherd" / "follows-me-everywhere" / "index.html",
        f"{SITE}/german-shepherd/follows-me-everywhere/",
    ),
]


def git_lastmod(path):
    """Committer date of the last commit that touched path, strict ISO 8601."""
    rel = path.relative_to(ROOT).as_posix()
    result = subprocess.run(
        ["git", "log", "-1", "--format=%cI", "--", rel],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    stamp = result.stdout.strip()
    if not stamp:
        # The page is new and not committed yet. Stamp the current Eastern
        # time so the build can finish. The next run after commit replaces
        # this with the committer date.
        stamp = datetime.now(ZoneInfo("America/New_York")).replace(microsecond=0).isoformat()
    if not ISO_RE.fullmatch(stamp):
        raise SystemExit(f"no ISO commit date for {rel}")
    return stamp


def video_rows():
    """Hub plus one URL per long-form watch page, oldest first so new videos append."""
    path = ROOT / "data" / "videos.json"
    if not path.is_file():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise SystemExit("data/videos.json must be a list")
    longs = []
    for item in payload:
        if not isinstance(item, dict) or item.get("type") != "long":
            continue
        slug = str(item.get("slug") or "")
        vid = str(item.get("id") or "")
        if not slug:
            raise SystemExit(f"long-form video {vid} has no slug")
        longs.append((str(item.get("published") or ""), vid, slug))
    longs.sort()
    rows = [(ROOT / "videos" / "index.html", f"{SITE}/videos/")]
    for _published, _vid, slug in longs:
        rows.append((ROOT / "videos" / slug / "index.html", f"{SITE}/videos/{slug}/"))
    return rows


def article_hub_rows():
    """The articles index, appended last so existing sitemap URLs stay put."""
    path = ROOT / "articles" / "index.html"
    if not path.is_file():
        return []
    return [(path, f"{SITE}/articles/")]


def pages(breeds):
    rows = [
        (ROOT / "index.html", f"{SITE}/"),
        (ROOT / "breeds" / "index.html", f"{SITE}/breeds/"),
    ]
    for breed in breeds:
        slug = breed["slug"]
        rows.append((ROOT / "breeds" / slug / "index.html", f"{SITE}/breeds/{slug}/"))
    rows.extend(ARTICLES)
    if len(rows) != BASE_URL_COUNT:
        raise SystemExit(f"expected {BASE_URL_COUNT} base sitemap URLs, got {len(rows)}")
    rows.extend(video_rows())
    rows.extend(article_hub_rows())
    return rows


def load_breeds():
    payload = json.loads(DATA.read_text(encoding="utf-8"))
    return payload["breeds"]


def render(breeds):
    rows = pages(breeds)
    locs = [loc for _path, loc in rows]
    if SITEMAP.exists():
        previous = LOC_RE.findall(SITEMAP.read_text(encoding="utf-8"))
        if previous and previous != locs:
            # Appending article URLs is intentional. Dropping or reordering is not.
            appended = len(locs) > len(previous) and locs[: len(previous)] == previous
            if not appended:
                raise SystemExit("sitemap URL list would change; refusing to write")
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for path, loc in rows:
        if not path.is_file():
            raise SystemExit(f"missing page for {loc}: {path.relative_to(ROOT)}")
        stamp = git_lastmod(path)
        lines.append(f"  <url><loc>{loc}</loc><lastmod>{stamp}</lastmod></url>")
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


def write(breeds=None):
    if breeds is None:
        breeds = load_breeds()
    text = render(breeds)
    SITEMAP.write_text(text, encoding="utf-8")
    print(f"Wrote sitemap.xml with {text.count('<loc>')} URLs.")


def main():
    try:
        write()
    except subprocess.CalledProcessError as exc:
        print(exc.stderr or exc, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
