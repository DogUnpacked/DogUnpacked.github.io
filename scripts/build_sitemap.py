#!/usr/bin/env python3
"""Write sitemap.xml with one lastmod per page, from that file's last git commit.

Python standard library only. No network. The 210 URLs stay the home page,
/breeds/, and each breed page, in that order:

    python3 scripts/build_sitemap.py

lastmod is the committer date of the last commit that touched the page, in
strict ISO 8601 (git %cI), for example 2026-10-12T23:34:28-04:00.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "breeds.json"
SITEMAP = ROOT / "sitemap.xml"
SITE = "https://dogunpacked.com"
LOC_RE = re.compile(r"<loc>(.*?)</loc>")
ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})$")
URL_COUNT = 210


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
    if not stamp or not ISO_RE.fullmatch(stamp):
        raise SystemExit(f"no ISO commit date for {rel}")
    return stamp


def pages(breeds):
    rows = [
        (ROOT / "index.html", f"{SITE}/"),
        (ROOT / "breeds" / "index.html", f"{SITE}/breeds/"),
    ]
    for breed in breeds:
        slug = breed["slug"]
        rows.append((ROOT / "breeds" / slug / "index.html", f"{SITE}/breeds/{slug}/"))
    return rows


def load_breeds():
    payload = json.loads(DATA.read_text(encoding="utf-8"))
    return payload["breeds"]


def render(breeds):
    rows = pages(breeds)
    if len(rows) != URL_COUNT:
        raise SystemExit(f"expected {URL_COUNT} sitemap URLs, got {len(rows)}")
    locs = [loc for _path, loc in rows]
    if SITEMAP.exists():
        previous = LOC_RE.findall(SITEMAP.read_text(encoding="utf-8"))
        if previous and previous != locs:
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
