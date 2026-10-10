#!/usr/bin/env python3
"""Refresh data/latest.json — the hub page's "Latest" section — with the 3 newest long-form videos.

  python3 scripts/update_latest_video.py            # write data/latest.json if anything changed
  python3 scripts/update_latest_video.py --dry-run  # only print what would change
  python3 scripts/update_latest_video.py --rebuild  # ignore the current file, use the feed only
  python3 scripts/update_latest_video.py --channel-id UCxxxx  # other channel

script.js reads data/latest.json for the visible Latest section:
  [{"id", "title", "published", "upload_datetime", "description"}, ...]  newest first, max 3.
  published is the America/New_York calendar date people see (YYYY-MM-DD), not the UTC day.
  upload_datetime is that same instant as a full ISO 8601 timestamp with the Eastern offset,
  for example 2026-10-07T21:00:20-04:00. A date with no time is never invented into a timestamp.
  description is one plain sentence. The YouTube description is kept only when it is short and
  has no exclamation marks, emoji, or hashtags. Otherwise it is
  "<title>. A Dog Unpacked YouTube video."
  First entry = click-to-load embed; the others = small cards. Empty list -> section hidden.

The same records rewrite only the VideoObject JSON-LD block in index.html, between the
LATEST-VIDEOS-JSONLD markers. uploadDate is upload_datetime. A video with no verified
timestamp is left out of that block. The rest of index.html is not edited.

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
     Each published timestamp is converted to America/New_York. published stores the
     calendar date. upload_datetime stores the full timestamp with the Eastern offset.

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
from datetime import datetime
from zoneinfo import ZoneInfo

# Resolved once on 2026-10-07 from https://www.youtube.com/@DogUnpacked
# (page HTML: "externalId":"UC_2f25vzJLiV799CfoHfDHA", canonical /channel/UC_2f25vzJLiV799CfoHfDHA).
CHANNEL_ID = "UC_2f25vzJLiV799CfoHfDHA"
MIN_SECONDS = 180

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "latest.json"
INDEX = ROOT / "index.html"
KEEP = 3
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
NS = {
    "a": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
    "media": "http://search.yahoo.com/mrss/",
}
VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
DATE_ONLY = re.compile(r"^\d{4}-\d{2}-\d{2}$")
UPLOAD_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}$")
NEW_YORK = ZoneInfo("America/New_York")
JSONLD_START = "<!-- LATEST-VIDEOS-JSONLD:START -->"
JSONLD_END = "<!-- LATEST-VIDEOS-JSONLD:END -->"


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
            "youtube_description": e.findtext("media:group/media:description", default="", namespaces=NS) or "",
            # The feed's own link says /shorts/ for Shorts: fallback signal when the GET check is blocked.
            "link": (e.find("a:link", NS).get("href", "") if e.find("a:link", NS) is not None else ""),
        })
    out.sort(key=lambda x: x["published"], reverse=True)
    return out


def parse_moment(published):
    """Absolute timestamp in America/New_York, or None when there is no time to convert.

    A YYYY-MM-DD value has no time of day, so it cannot become uploadDate.
    """
    text = str(published or "").strip()
    if not text or DATE_ONLY.fullmatch(text):
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        moment = datetime.fromisoformat(text)
    except ValueError:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=ZoneInfo("UTC"))
    return moment.astimezone(NEW_YORK)


def eastern_date(published):
    """YYYY-MM-DD in America/New_York.

    The channel feed publishes an absolute timestamp (UTC). Keeping the first
    ten characters would store the UTC day, so a video that goes live in the
    evening Eastern time would be dated the next day. A value that is already
    YYYY-MM-DD is returned unchanged.
    """
    text = str(published or "").strip()
    if not text or DATE_ONLY.fullmatch(text):
        return text
    moment = parse_moment(text)
    if moment is None:
        raise ValueError(f"unparsed timestamp: {published}")
    return moment.date().isoformat()


def eastern_datetime(published):
    """Full ISO 8601 timestamp in America/New_York, or "" when the time is unknown."""
    moment = parse_moment(published)
    if moment is None:
        return ""
    text = moment.isoformat(timespec="seconds")
    if not UPLOAD_RE.fullmatch(text):
        return ""
    return text


def short_and_clean(text):
    """True when a YouTube description can be copied into VideoObject as-is."""
    text = (text or "").strip()
    if not text or len(text) > 180 or "\n" in text or "\r" in text:
        return False
    if "!" in text or "#" in text or "http://" in text or "https://" in text or "www." in text:
        return False
    for ch in text:
        code = ord(ch)
        if code > 0xFFFF or 0x1F000 <= code <= 0x1FAFF or 0x2600 <= code <= 0x27BF:
            return False
    return text.endswith(".") and text.count(".") == 1


def choose_description(title, youtube_description):
    youtube = (youtube_description or "").strip()
    if short_and_clean(youtube):
        return youtube
    return f"{title}. A Dog Unpacked YouTube video."


def video_record(src, youtube_description=""):
    title = str(src.get("title") or "")
    upload = eastern_datetime(src.get("upload_datetime") or src.get("published") or "")
    published = eastern_date(upload or src.get("published") or "")
    record = {"id": src["id"], "title": title, "published": published}
    if upload:
        record["upload_datetime"] = upload
    record["description"] = choose_description(title, youtube_description)
    return record


def description_ok(text):
    if not text or "!" in text or "#" in text:
        return False
    for ch in text:
        code = ord(ch)
        if code > 0xFFFF or 0x1F000 <= code <= 0x1FAFF or 0x2600 <= code <= 0x27BF:
            return False
    return True


def home_jsonld_block(videos):
    graph = []
    for v in videos:
        upload = v.get("upload_datetime") or ""
        description = (v.get("description") or "").strip()
        if not UPLOAD_RE.fullmatch(upload) or not description_ok(description):
            print(f"  ! leaving VideoObject out for {v['id']} (no verified timestamp or description)")
            continue
        graph.append(
            {
                "@type": "VideoObject",
                "name": v["title"],
                "description": description,
                "thumbnailUrl": "https://i.ytimg.com/vi/" + v["id"] + "/hqdefault.jpg",
                "uploadDate": upload,
                "embedUrl": "https://www.youtube.com/embed/" + v["id"],
                "contentUrl": "https://www.youtube.com/watch?v=" + v["id"],
            }
        )
    payload = {"@context": "https://schema.org", "@graph": graph}
    body = json.dumps(payload, ensure_ascii=False, indent=2)
    indented = "\n".join(("  " + line) if line else "" for line in body.split("\n"))
    return (
        f"{JSONLD_START}\n"
        f"  <script type=\"application/ld+json\">\n"
        f"{indented}\n"
        f"  </script>\n"
        f"  {JSONLD_END}"
    )


def sync_home_jsonld(videos, dry_run):
    """Rewrite the marked VideoObject block. Returns True when the block changed."""
    text = INDEX.read_text(encoding="utf-8")
    if JSONLD_START not in text or JSONLD_END not in text:
        print("  ! index.html is missing LATEST-VIDEOS-JSONLD markers; VideoObject block not updated")
        return False
    start = text.index(JSONLD_START)
    end = text.index(JSONLD_END) + len(JSONLD_END)
    block = home_jsonld_block(videos)
    if text[start:end] == block:
        return False
    if dry_run:
        print("Latest: would update the VideoObject block in index.html (dry run, not written)")
        return True
    INDEX.write_text(text[:start] + block + text[end:], encoding="utf-8")
    print("Latest: updated the VideoObject block in index.html")
    return True


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
            item = {
                "id": v["id"],
                "title": str(v.get("title", "")),
                "published": str(v.get("published", "")),
            }
            if v.get("upload_datetime"):
                item["upload_datetime"] = str(v["upload_datetime"])
            if v.get("description"):
                item["description"] = str(v["description"])
            out.append(item)
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
        merged[v["id"]] = video_record(v)
    for v in found:
        merged[v["id"]] = video_record(v, v.get("youtube_description") or "")
    new = sorted(merged.values(), key=lambda x: x["published"], reverse=True)[:KEEP]

    for i, v in enumerate(new):
        print(f"  {i + 1}. {v['published']}  {v.get('upload_datetime') or '(no timestamp)'}  {v['id']}  {v['title']}")
    if not new:
        print("Latest: no long-form video found; data/latest.json left as is. no change")
        return 0
    data_changed = new != current
    if args.dry_run:
        # Build the block once so a missing timestamp is reported, then compare.
        html_changed = False
        text = INDEX.read_text(encoding="utf-8")
        if JSONLD_START in text and JSONLD_END in text:
            start = text.index(JSONLD_START)
            end = text.index(JSONLD_END) + len(JSONLD_END)
            html_changed = text[start:end] != home_jsonld_block(new)
        else:
            print("  ! index.html is missing LATEST-VIDEOS-JSONLD markers; VideoObject block not updated")
        if not data_changed and not html_changed:
            print("Latest: no change")
            return 0
        if data_changed:
            print("Latest: would update data/latest.json (dry run, not written)")
        if html_changed:
            print("Latest: would update the VideoObject block in index.html (dry run, not written)")
        return 0
    if data_changed:
        DATA.parent.mkdir(parents=True, exist_ok=True)
        DATA.write_text(json.dumps(new, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Latest: updated data/latest.json (newest: {new[0]['id']})")
    html_changed = sync_home_jsonld(new, dry_run=False)
    if not data_changed and not html_changed:
        print("Latest: no change")
    return 0


if __name__ == "__main__":
    sys.exit(main())
