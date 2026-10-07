#!/usr/bin/env python3
"""Put the newest long-form Dog Unpacked YouTube video into the hub page's "Latest" section.

  python3 scripts/update_latest_video.py            # update index.html if a newer video exists
  python3 scripts/update_latest_video.py --dry-run  # only print what would change
  python3 scripts/update_latest_video.py --channel-id UCxxxx  # other channel

How it works
  1. Reads the public channel RSS feed (no API key):
     https://www.youtube.com/feeds/videos.xml?channel_id=<CHANNEL_ID>  (newest first, ~15 entries)
  2. Skips Shorts: GET https://www.youtube.com/shorts/<id> with redirects disabled.
     200 = Short; 30x redirect to /watch = long-form. If YouTube answers with a rate-limit or consent
     redirect instead, the feed entry's own link (/shorts/ vs /watch) decides.
  3. Also skips anything <= 180 s when the watch page exposes "lengthSeconds" (if it can't be read,
     the Shorts check alone decides).
  4. Writes the newest long-form ID into index.html: <section id="latest" data-video-id="...">.
     An empty value keeps the section hidden; script.js shows it when the ID is set.

Exit codes: 0 = updated or "no change" (also when the channel has no long-form video yet; the page is
left as is); 1 = network/parse error (page untouched); 2 = index.html marker not found.
Standard library only.
"""
import argparse
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
PAGE = ROOT / "index.html"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
NS = {
    "a": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
}
MARKER = re.compile(r'(<section\b[^>]*\bid="latest"[^>]*\bdata-video-id=")([^"]*)(")')


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


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--channel-id", default=CHANNEL_ID)
    ap.add_argument("--dry-run", action="store_true", help="print the result, don't write index.html")
    args = ap.parse_args()

    page = PAGE.read_text(encoding="utf-8")
    m = MARKER.search(page)
    if not m:
        print('index.html: <section id="latest" data-video-id="..."> not found', file=sys.stderr)
        return 2
    old_id = m.group(2)

    try:
        entries = feed_entries(args.channel_id)
    except Exception as e:
        print(f"Could not read the channel feed: {e}", file=sys.stderr)
        return 1

    pick = None
    for v in entries:
        short = is_short(v["id"])
        how = "GET /shorts"
        if short is None and v["link"]:
            short, how = ("/shorts/" in v["link"]), "feed link (GET /shorts inconclusive)"
        if short:
            print(f"  - skip Short     {v['id']}  {v['title']}  [{how}]")
            continue
        secs = duration_seconds(v["id"])
        if secs is not None and secs <= MIN_SECONDS:
            print(f"  - skip {secs:>4}s     {v['id']}  {v['title']}")
            continue
        if short is None and secs is None:
            print(f"  ? unknown        {v['id']}  {v['title']}  (Shorts check and duration both unavailable; skipping)")
            continue
        print(f"  + long-form {('%ss' % secs) if secs is not None else '?s'}  {v['id']}  {v['title']}  [{how}]")
        pick = v
        break

    if not pick:
        print(f"No long-form video in the latest {len(entries)} feed entries. "
              f"Leaving the Latest section as is (old ID: {old_id or '(empty, section hidden)'}). no change")
        return 0

    print(f"old ID: {old_id or '(empty)'}")
    print(f"new ID: {pick['id']}  \"{pick['title']}\"  ({pick['published']})")
    if pick["id"] == old_id:
        print("no change")
        return 0
    if args.dry_run:
        print("dry run: index.html not written")
        return 0
    PAGE.write_text(page[: m.start(2)] + pick["id"] + page[m.end(2):], encoding="utf-8")
    print("index.html updated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
