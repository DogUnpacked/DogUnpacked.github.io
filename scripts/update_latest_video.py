#!/usr/bin/env python3
"""Refresh data/latest.json — the hub page's "Latest" section — with the 3 newest long-form videos.

  python3 scripts/update_latest_video.py            # write data/latest.json if anything changed
  python3 scripts/update_latest_video.py --dry-run  # only print what would change
  python3 scripts/update_latest_video.py --rebuild  # ignore the current file, use the feed only
  python3 scripts/update_latest_video.py --channel-id UCxxxx  # other channel

index.html is never edited for a new video. script.js reads data/latest.json:
  [{"id": "<11-char id>", "title": "<exact YouTube title>", "published": "YYYY-MM-DD"}, ...]  newest first, max 3.
  First entry = click-to-load embed; the others = small cards. Empty list -> section hidden.

How it works
  1. Reads the public channel RSS feed (no API key):
     https://www.youtube.com/feeds/videos.xml?channel_id=<CHANNEL_ID>  (newest ~15 uploads, Shorts included)
  2. Skips Shorts: GET https://www.youtube.com/shorts/<id> with redirects disabled.
     200 = Short; 30x redirect to /watch = long-form. If YouTube answers with a rate-limit or consent
     redirect instead, the feed entry's own link (/shorts/ vs /watch) decides.
  3. Also skips anything <= 180 s when the watch page exposes "lengthSeconds" (if it can't be read,
     the Shorts check alone decides).
  4. Merges the long-form videos found with the entries already in data/latest.json (so a long-form video
     that has scrolled out of the 15-entry feed behind newer Shorts is kept), newest first, keeps 3.

Prints "Latest: no change" when the result equals the current file.
Exit codes: 0 = updated or no change; 1 = network/parse error (file untouched). Standard library only.
"""
import argparse
import json
import pathlib
import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

# Resolved once on 2026-10-07 from https://www.youtube.com/@DogUnpacked
# (page HTML: "externalId":"UC_2f25vzJLiV799CfoHfDHA", canonical /channel/UC_2f25vzJLiV799CfoHfDHA).
CHANNEL_ID = "UC_2f25vzJLiV799CfoHfDHA"
MIN_SECONDS = 180

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "latest.json"
KEEP = 3
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
NS = {
    "a": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
}
VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # surface 30x as HTTPError instead of following it


def fetch(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def is_short(video_id):
    """True = Short, False = long-form, None = inconclusive (e.g. YouTube's rate-limit/consent redirect)."""
    opener = urllib.request.build_opener(NoRedirect)
    req = urllib.request.Request(f"https://www.youtube.com/shorts/{video_id}", headers={"User-Agent": UA})
    try:
        with opener.open(req, timeout=20) as r:
            return r.status == 200
    except urllib.error.HTTPError as e:
        if e.code in (301, 302, 303, 307, 308):
            location = e.headers.get("Location", "")
            if "/watch" in location:
                return False  # redirected to /watch -> long-form
            return None  # redirected somewhere else (google.com/sorry, consent page)
        return None
    except Exception:
        return None


def duration_seconds(video_id):
    try:
        html = fetch(f"https://www.youtube.com/watch?v={video_id}")
    except Exception:
        return None
    m = re.search(r'"lengthSeconds":"(\d+)"', html)
    return int(m.group(1)) if m else None


def feed_entries(channel_id):
    xml = fetch(f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}")
    root = ET.fromstring(xml)
    out = []
    for e in root.findall("a:entry", NS):
        out.append({
            "id": e.findtext("yt:videoId", default="", namespaces=NS),
            "title": e.findtext("a:title", default="", namespaces=NS),
            "published": e.findtext("a:published", default="", namespaces=NS),
            # The feed's own link says /shorts/ for Shorts: fallback signal when the GET check is blocked.
            "link": (e.find("a:link", NS).get("href", "") if e.find("a:link", NS) is not None else ""),
        })
    out.sort(key=lambda x: x["published"], reverse=True)
    return out


def read_current():
    try:
        data = json.loads(DATA.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    except ValueError as e:
        print(f"  ! {DATA.relative_to(ROOT)} is not valid JSON ({e}); rebuilding from the feed")
        return []
    out = []
    for v in data if isinstance(data, list) else []:
        if isinstance(v, dict) and VIDEO_ID.match(str(v.get("id", ""))):
            out.append({"id": v["id"], "title": str(v.get("title", "")), "published": str(v.get("published", ""))})
    return out


def classify(v):
    """True = long-form, False = Short/too short, None = unknown."""
    short = is_short(v["id"])
    how = "GET /shorts"
    if short is None and v["link"]:
        short, how = ("/shorts/" in v["link"]), "feed link (GET /shorts inconclusive)"
    if short:
        print(f"  - skip Short     {v['id']}  {v['title']}  [{how}]")
        return False
    secs = duration_seconds(v["id"])
    if secs is not None and secs <= MIN_SECONDS:
        print(f"  - skip {secs:>4}s     {v['id']}  {v['title']}")
        return False
    if short is None and secs is None:
        print(f"  ? unknown        {v['id']}  {v['title']}  (Shorts check and duration both unavailable; skipping)")
        return None
    print(f"  + long-form {('%ss' % secs) if secs is not None else '?s'}  {v['id']}  {v['title']}  [{how}]")
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--channel-id", default=CHANNEL_ID)
    ap.add_argument("--dry-run", action="store_true", help="print the result, don't write data/latest.json")
    ap.add_argument("--rebuild", action="store_true", help="ignore the current data/latest.json")
    args = ap.parse_args()

    current = read_current()
    try:
        entries = feed_entries(args.channel_id)
    except Exception as e:
        print(f"Could not read the channel feed: {e}", file=sys.stderr)
        return 1

    known = {v["id"] for v in current}
    found = []
    for v in entries:
        if not VIDEO_ID.match(v["id"]):
            continue
        if v["id"] in known and not args.rebuild:
            print(f"  = already listed {v['id']}  {v['title']}")
            found.append(v)  # refresh title/date from the feed
            continue
        if classify(v):
            found.append(v)

    merged = {}
    for v in ([] if args.rebuild else current):
        merged[v["id"]] = v
    for v in found:
        merged[v["id"]] = {"id": v["id"], "title": v["title"], "published": v["published"][:10]}
    new = sorted(merged.values(), key=lambda x: x["published"], reverse=True)[:KEEP]

    for i, v in enumerate(new):
        print(f"  {i + 1}. {v['published']}  {v['id']}  {v['title']}")
    if new == current:
        print("Latest: no change")
        return 0
    if not new:
        print("Latest: no long-form video found; data/latest.json left as is. no change")
        return 0
    if args.dry_run:
        print("Latest: would update data/latest.json (dry run, not written)")
        return 0
    DATA.parent.mkdir(parents=True, exist_ok=True)
    DATA.write_text(json.dumps(new, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Latest: updated data/latest.json (newest: {new[0]['id']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
