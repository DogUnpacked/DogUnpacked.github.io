#!/usr/bin/env python3
"""Build the /videos/ hub and long-form watch pages from data/videos.json.

Python standard library only. GitHub Pages serves the HTML this writes.

    python3 scripts/build_videos.py
    python3 scripts/build_videos.py --refresh
    python3 scripts/build_videos.py --add VIDEO_ID

--refresh reads the channel RSS feed and the Videos and Shorts tabs, adds
uploads whose ids are not already in data/videos.json, and rebuilds. Ids
already in the file are not changed. If the network fails, the file is left
alone and the pages are still rebuilt from it.

Shorts are listed on the hub only. Long-form videos also get /videos/<slug>/.
"""

import argparse
import html
import json
import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "videos.json"
BREEDS = ROOT / "data" / "breeds.json"
VIDEOS_DIR = ROOT / "videos"
SITEMAP_VIDEOS = ROOT / "sitemap-videos.xml"
ROBOTS = ROOT / "robots.txt"
SITE = "https://dogunpacked.com"
CHANNEL_ID = "UC_2f25vzJLiV799CfoHfDHA"
SUBSCRIBE = "https://www.youtube.com/@DogUnpacked?sub_confirmation=1"
VIDEOS_PAGE = "https://www.youtube.com/@DogUnpacked/videos"
SHORTS_PAGE = "https://www.youtube.com/@DogUnpacked/shorts"
HUB_TITLE = "Dog Breed Videos: Behavior by Breed | Dog Unpacked"
HUB_DESC = (
    "Long-form videos and Shorts from Dog Unpacked on dog behavior by breed, newest first."
)
NEW_YORK = ZoneInfo("America/New_York")
UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
# The watch page served to this client includes uploadDate and shortDescription.
META_UA = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
NS = {
    "a": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
    "media": "http://search.yahoo.com/mrss/",
}
VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
PUBLISHED_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}$")
DURATION_RE = re.compile(r"^PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$")
HASHTAG_RE = re.compile(r"#\w+")
URL_RE = re.compile(r"https?://\S+|www\.\S+", re.I)
LABEL_RE = re.compile(r"^[^:]{1,90}:$")
# Cadence lines from older descriptions are not repeated on the site.
CADENCE_RE = re.compile(r"\bNew videos every (?:week|day)\.?", re.I)
WEEKLY_LINE_RE = re.compile(r"^Subscribe for weekly\b", re.I)
MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]
PLAY_SVG = (
    '<span class="lite-yt-play" aria-hidden="true">'
    '<svg viewBox="0 0 68 48" width="68" height="48">'
    '<path d="M66.5 7.7a8.5 8.5 0 0 0-6-6C55.2.3 34 .3 34 .3s-21.2 0-26.5 1.4a8.5 8.5 0 0 0-6 6C.1 13 .1 24 .1 24s0 11 1.4 16.3a8.5 8.5 0 0 0 6 6C12.8 47.7 34 47.7 34 47.7s21.2 0 26.5-1.4a8.5 8.5 0 0 0 6-6C67.9 35 67.9 24 67.9 24s0-11-1.4-16.3z" fill="#b3261e"/>'
    '<path d="M27 34V14l18 10z" fill="#fff"/></svg></span>'
)
THUMB = "https://i.ytimg.com/vi/{vid}/hqdefault.jpg"
THUMB_DIR = ROOT / "images" / "video-thumbs"

# Above-the-fold rules. styles.css repeats them so the deferred sheet does not move the layout.
CRITICAL_CSS = """
    @font-face{font-family:"Nunito Fallback";src:local("Arial"),local("Helvetica"),local("Liberation Sans");size-adjust:100%;ascent-override:101%;descent-override:35%;line-gap-override:0%}
    @font-face{font-family:"Fraunces Fallback";src:local("Georgia"),local("Times New Roman"),local("Liberation Serif");size-adjust:96%;ascent-override:102%;descent-override:27%;line-gap-override:0%}
    :root{--navy:#1B2A4A;--navy-muted:#4F5D78;--cream:#F5EDDC;--cream-deep:#EFE6D4;--amber:#D89B3D;--card:#FBF6EC;--border:#E0D4BC;--border-strong:#CDBE9E;--radius:14px;--header:3.5rem}
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
    .site-nav a{display:inline-flex;align-items:center;justify-content:center;min-height:44px;padding:.4rem .7rem;border-radius:999px;color:var(--navy);text-decoration:none;font-weight:800;font-size:.92rem}
    .site-nav a.nav-cta{background:var(--navy);color:var(--cream);padding-inline:.9rem}
    .nav-cta-short,.site-nav a.nav-desktop{display:none}
    .video-hub,.video-watch{width:min(100% - 2rem,68rem);margin-inline:auto;padding:1.25rem 0 3.5rem}
    .video-watch{width:min(100% - 2rem,40rem)}
    .video-hub h1,.video-watch h1{margin:0;font-family:"Fraunces Fallback",Georgia,serif;font-size:clamp(1.9rem,4.8vw,2.7rem);font-weight:700;letter-spacing:-.03em;line-height:1.12}
    .crumbs{display:flex;flex-wrap:wrap;gap:.35rem;align-items:center;margin:0 0 .9rem;color:var(--navy-muted);font-size:.88rem;font-weight:700}
    .crumbs a{color:var(--navy);font-weight:800;text-decoration:none}
    .video-dek,.video-status{margin:.7rem 0 0;color:var(--navy-muted);font-weight:700}
    .video-kicker{margin:0;color:var(--navy-muted);font-size:.78rem;font-weight:800;letter-spacing:.04em;text-transform:uppercase}
    .video-controls{display:grid;gap:.85rem;margin:1rem 0 0}
    .video-type{margin:0;padding:0;border:0;min-width:0}
    .video-type legend,.video-breed label{margin:0 0 .35rem;padding:0;color:var(--navy-muted);font-size:.78rem;font-weight:800;letter-spacing:.04em;text-transform:uppercase}
    .video-type-options{display:flex;width:min(100%,28rem);border:1px solid var(--border-strong);border-radius:999px;overflow:hidden;background:var(--card)}
    .video-type-option{position:relative;display:flex;flex:1 1 0}
    .video-type-option input{position:absolute;width:1px;height:1px;margin:-1px;padding:0;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}
    .video-type-option span{display:inline-flex;align-items:center;justify-content:center;width:100%;min-height:44px;padding:.2rem .7rem;font-size:.92rem;font-weight:800;white-space:nowrap}
    .video-type-option input:checked+span{background:var(--navy);color:var(--cream)}
    .video-type-option input:focus-visible+span{outline:3px solid var(--navy);outline-offset:-3px}
    .video-breed{display:grid;gap:.35rem;max-width:22rem}
    .video-breed select{min-height:44px;padding:0 .75rem;border:1px solid var(--border-strong);border-radius:999px;background:var(--card);color:var(--navy);font:inherit;font-size:.92rem;font-weight:800}
    .video-empty{margin:1rem 0 0;font-weight:800}
    .video-list{display:grid;gap:.9rem;margin:1rem 0 0;padding:0;list-style:none}
    .video-card{display:grid;background:var(--navy);color:var(--cream);border-radius:14px;overflow:hidden}
    .video-card[hidden]{display:none}
    .video-card-link{display:grid;color:inherit;text-decoration:none}
    .video-card-media{display:block;background:#111}
    .video-card-media img{display:block;width:100%;height:auto;aspect-ratio:4/3;object-fit:cover;background:#111}
    .video-card-body{display:grid;gap:.25rem;padding:.75rem .95rem .9rem}
    .video-card h2{margin:0;color:var(--cream);font-family:"Fraunces Fallback",Georgia,serif;font-size:1.15rem;font-weight:700;line-height:1.25}
    .video-card-kicker{margin:0;color:var(--amber);font-size:.78rem;font-weight:800;letter-spacing:.04em;text-transform:uppercase}
    .video-card time{color:var(--cream);font-size:.88rem;font-weight:800}
    .lite-yt{position:relative;aspect-ratio:16/9;width:100%;margin-top:1rem;border-radius:10px;overflow:hidden;background:#0B1326}
    .lite-yt-btn{position:absolute;inset:0;display:block;width:100%;height:100%;padding:0;border:0;background:#0B1326;cursor:pointer}
    .lite-yt-btn img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}
    .lite-yt-play{position:absolute;left:50%;top:50%;display:inline-flex;line-height:0;transform:translate(-50%,-50%)}
    @media (max-width:540px){.video-type-option span{padding-inline:.45rem;font-size:.82rem}}
    @media (max-width:640px){.nav-cta-long{display:none}.nav-cta-short{display:inline}.header-inner{gap:.25rem}.brand{gap:.3rem}.brand img{width:32px;height:32px}.brand-word{font-size:.75rem}.site-nav{gap:0}.site-nav a{padding:.2rem .26rem;font-size:.75rem}.site-nav a.nav-cta{padding-inline:.4rem}}
    @media (min-width:720px){.video-list{grid-template-columns:1fr 1fr}}
    @media (min-width:840px){.site-nav a.nav-desktop{display:inline-flex}}
"""


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


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


def fetch(url, timeout=25, user_agent=None, data=None):
    headers = {"User-Agent": user_agent or UA, "Accept-Language": "en-US,en;q=0.9"}
    body = None
    if data is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read().decode("utf-8", "replace")


def json_object_after(html_text, marker):
    start = html_text.find(marker)
    if start < 0:
        return None
    start = html_text.find("{", start)
    if start < 0:
        return None
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(html_text)):
        char = html_text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return json.loads(html_text[start:index + 1])
    return None


def parse_moment(value):
    text = str(value or "").strip()
    if not text or re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        moment = datetime.fromisoformat(text)
    except ValueError:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=ZoneInfo("UTC"))
    moment = moment.astimezone(NEW_YORK).replace(microsecond=0)
    stamp = moment.isoformat()
    if not PUBLISHED_RE.fullmatch(stamp):
        return None
    return stamp


def iso_duration(seconds):
    try:
        seconds = int(seconds)
    except (TypeError, ValueError):
        return ""
    if seconds < 0:
        return ""
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    text = "PT"
    if hours:
        text += f"{hours}H"
    if minutes:
        text += f"{minutes}M"
    if secs or text == "PT":
        text += f"{secs}S"
    return text


def duration_seconds(value):
    match = DURATION_RE.fullmatch(str(value or ""))
    if not match:
        return None
    hours, minutes, secs = match.groups()
    return int(hours or 0) * 3600 + int(minutes or 0) * 60 + int(secs or 0)


def duration_phrase(value):
    seconds = duration_seconds(value)
    if seconds is None:
        return ""
    if seconds < 60:
        return f"{seconds} sec"
    minutes, secs = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    parts = []
    if hours:
        parts.append(f"{hours} hr")
    if minutes:
        parts.append(f"{minutes} min")
    if secs:
        parts.append(f"{secs} sec")
    return " ".join(parts)


def duration_card(value):
    seconds = duration_seconds(value)
    if seconds is None:
        return ""
    if seconds < 60:
        return f"{seconds} sec"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} min"
    hours, minutes = divmod(minutes, 60)
    if minutes:
        return f"{hours} hr {minutes} min"
    return f"{hours} hr"


def format_day(stamp):
    year, month, day = stamp[:10].split("-")
    return f"{MONTHS[int(month) - 1]} {int(day)}, {year}"


def clean_description(text):
    """YouTube description with hashtags and links removed. No new sentences."""
    text = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
    kept = []
    for line in text.split("\n"):
        line = URL_RE.sub("", line)
        line = HASHTAG_RE.sub("", line)
        line = CADENCE_RE.sub("", line)
        line = re.sub(r"[ \t]{2,}", " ", line).strip(" \t-")
        if not line:
            continue
        if re.fullmatch(r"subscribe:?", line, flags=re.I) or WEEKLY_LINE_RE.match(line):
            continue
        if LABEL_RE.fullmatch(line):
            continue
        kept.append(line)
    return "\n".join(kept).strip()


def first_sentence(text):
    for mark in (". ", "? ", "! "):
        pass
    match = re.search(r".+?[.!?](?=\s|$)", text.replace("\n", " ").strip())
    if not match:
        return ""
    return match.group(0).strip()


def meta_sentence(title, cleaned):
    sentence = first_sentence(cleaned)
    if (
        sentence
        and sentence.endswith((".", "?"))
        and "!" not in sentence
        and not has_emoji(sentence)
        and len(sentence) <= 155
    ):
        return sentence
    plain = f"{title}."
    if "!" not in plain and not has_emoji(plain) and plain.endswith(".") and len(plain) <= 155:
        return plain
    return "A Dog Unpacked video on YouTube."


def load_breeds():
    payload = json.loads(BREEDS.read_text(encoding="utf-8"))
    return payload["breeds"]


def breed_names(breeds):
    return {breed["slug"]: breed["name"] for breed in breeds}


def page_map(breeds):
    found = {}
    for breed in breeds:
        for video in breed.get("videos") or []:
            if not isinstance(video, dict):
                continue
            vid = video.get("id")
            if not isinstance(vid, str) or not VIDEO_ID.fullmatch(vid):
                continue
            found.setdefault(vid, [])
            if breed["slug"] not in found[vid]:
                found[vid].append(breed["slug"])
    return found


def breed_patterns(breeds):
    """Longest name or alias first, so French Bulldog wins over Bulldog."""
    rows = []
    seen = set()
    for breed in breeds:
        phrases = [breed.get("name") or ""]
        phrases.extend(breed.get("aliases") or [])
        for phrase in phrases:
            phrase = str(phrase or "").strip()
            if len(phrase) < 4 or (phrase.lower(), breed["slug"]) in seen:
                continue
            seen.add((phrase.lower(), breed["slug"]))
            rows.append((phrase, breed["slug"]))
    rows.sort(key=lambda item: len(item[0]), reverse=True)
    compiled = []
    for phrase, slug in rows:
        words = phrase.split()
        last = words[-1]
        if last.lower().endswith("y") and len(last) > 2 and last[-2].lower() not in "aeiou":
            last_pat = re.escape(last[:-1]) + r"(?:y|ies)"
        elif last.lower().endswith("s"):
            last_pat = re.escape(last)
        else:
            last_pat = re.escape(last) + "s?"
        body = r"\s+".join([re.escape(word) for word in words[:-1]] + [last_pat])
        compiled.append((re.compile(rf"(?<![A-Za-z0-9]){body}(?![A-Za-z0-9])", re.I), slug, phrase))
    return compiled


def breeds_named_in_title(title, patterns):
    # Keep the word inside a hashtag so "#beagle" still names Beagle.
    text = (title or "").replace("#", " ")
    spans = []
    for pattern, slug, phrase in patterns:
        for match in pattern.finditer(text):
            spans.append((match.start(), match.end(), slug, phrase))
    kept = []
    for start, end, slug, phrase in spans:
        covered = any(
            start >= other_start and end <= other_end and (end - start) < (other_end - other_start)
            for other_start, other_end, _other_slug, _other_phrase in spans
        )
        if not covered:
            kept.append((start, slug))
    slugs = []
    for _start, slug in sorted(kept):
        if slug not in slugs:
            slugs.append(slug)
    return slugs


def assign_breeds(video_id, title, pages, patterns):
    named = breeds_named_in_title(title, patterns)
    # A title that names exactly one breed links only to that breed.
    if len(named) == 1:
        return named
    placed = pages.get(video_id) or []
    if placed:
        return list(placed)
    return []


def title_assignment(title, patterns):
    named = breeds_named_in_title(title, patterns)
    if len(named) == 1:
        return named
    return []


def check_breed_matching(patterns):
    cases = [
        ("Rottweiler vs Doberman vs German Shepherd", []),
        ("Ranking 8 Guard Dog Breeds Worst to Best", []),
        ("8 Things Your German Shepherd Does That Aren't What You Think", ["german-shepherd"]),
        ("The French Bulldog Was Bred for One Job. You're Sitting On It.", ["french-bulldog"]),
        ("3 Things Only Corgi Owners UNDERSTAND", ["corgi"]),
        ("3 Things You DIDN'T Know About Pit Bulls", ["pit-bull"]),
        ("Why Dogs Yawn When You Yawn", []),
        ("Your Husky Isn't Being Dramatic (Siberian Husky Explained)", ["husky"]),
        ("Why Your Australian Shepherd Herds the Kids", ["australian-shepherd"]),
        ("German Shepherd and Belgian Malinois", []),
        ("3 Things You DIDN'T Know About Golden Retrievers", ["golden-retriever"]),
        ("Your Labrador Isn't Greedy (Lab Explained)", ["labrador"]),
        ("Why This Breed Is A Scent-Tracking Genius #dog #beagle #dogshorts", ["beagle"]),
    ]
    for title, expect in cases:
        got = title_assignment(title, patterns)
        if got != expect:
            raise SystemExit(f"breed match failed for {title!r}: {got} != {expect}")


def slugify(title):
    text = re.sub(r"\s*\([^)]*\)", " ", title or "")
    text = HASHTAG_RE.sub(" ", text)
    if "—" in text or "–" in text:
        head = re.split(r"\s[—–]\s", text, maxsplit=1)[0]
        if len(head.split()) >= 4:
            text = head
    text = text.lower().replace("'", "").replace("’", "").replace("'", "")
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    if len(text) > 60 and "-" in text[:60]:
        text = text[:60].rsplit("-", 1)[0].strip("-")
    elif len(text) > 60:
        text = text[:60].strip("-")
    return text


def unique_slug(title, used):
    base = slugify(title) or "video"
    slug = base
    number = 2
    while slug in used or slug in {"long", "short", "videos"}:
        slug = f"{base}-{number}"
        number += 1
    used.add(slug)
    return slug


def load_videos():
    if not DATA.is_file():
        return []
    payload = json.loads(DATA.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise SystemExit("data/videos.json must be a list")
    videos = []
    for item in payload:
        if not isinstance(item, dict) or not VIDEO_ID.fullmatch(str(item.get("id") or "")):
            raise SystemExit("data/videos.json has an entry without a video id")
        videos.append(item)
    return videos


def normalize(record, breeds_for, used_slugs):
    vid = record["id"]
    title = str(record.get("title") or "").strip()
    kind = record.get("type")
    published = str(record.get("published") or "")
    if kind not in {"long", "short"}:
        raise SystemExit(f"{vid} type must be long or short")
    if not title:
        raise SystemExit(f"{vid} is missing a title")
    if not PUBLISHED_RE.fullmatch(published):
        raise SystemExit(f"{vid} published is not an ISO timestamp with an offset")
    out = {
        "id": vid,
        "title": title,
        "type": kind,
        "published": published,
    }
    duration = str(record.get("duration") or "")
    if duration:
        if not DURATION_RE.fullmatch(duration):
            raise SystemExit(f"{vid} duration is not ISO 8601")
        out["duration"] = duration
    out["description"] = str(record.get("description") or "")
    if not isinstance(breeds_for, list):
        raise SystemExit(f"{vid} breeds must be a list")
    out["breeds"] = breeds_for
    if kind == "long":
        slug = str(record.get("slug") or "")
        if not slug:
            slug = unique_slug(title, used_slugs)
        elif not SLUG_RE.fullmatch(slug):
            raise SystemExit(f"{vid} has a bad slug: {slug}")
        else:
            if slug in used_slugs:
                raise SystemExit(f"duplicate slug {slug}")
            used_slugs.add(slug)
        out["slug"] = slug
    transcript = record.get("transcript")
    if isinstance(transcript, str) and transcript.strip():
        out["transcript"] = transcript.strip()
    return out


def prepare(records, breeds):
    patterns = breed_patterns(breeds)
    check_breed_matching(patterns)
    pages = page_map(breeds)
    names = breed_names(breeds)
    used_slugs = set()
    # Keep stored slugs first so a newly generated slug cannot collide with one.
    existing = [record for record in records if record.get("type") == "long" and record.get("slug")]
    existing_ids = {record["id"] for record in existing}
    rest = [record for record in records if record["id"] not in existing_ids]
    normalized = []
    for record in existing + rest:
        assigned = assign_breeds(record["id"], record.get("title") or "", pages, patterns)
        for slug in assigned:
            if slug not in names:
                raise SystemExit(f"{record['id']} breed slug is not in breeds.json: {slug}")
        normalized.append(normalize(record, assigned, used_slugs))
    normalized.sort(key=lambda item: item["published"], reverse=True)
    if "!" in HUB_TITLE or "!" in HUB_DESC or has_emoji(HUB_TITLE) or has_emoji(HUB_DESC):
        raise SystemExit("hub title or description breaks the brand rules")
    if len(HUB_TITLE) > 60:
        raise SystemExit(f"hub title is {len(HUB_TITLE)} characters")
    if len(HUB_DESC) > 155 or not HUB_DESC.endswith("."):
        raise SystemExit("hub meta description must be one sentence under 155 characters")
    return normalized


def collect_ids(node, found):
    if isinstance(node, dict):
        vid = node.get("videoId")
        if isinstance(vid, str) and VIDEO_ID.fullmatch(vid):
            found.append(vid)
        cid = node.get("contentId")
        if isinstance(cid, str) and VIDEO_ID.fullmatch(cid):
            found.append(cid)
        for value in node.values():
            collect_ids(value, found)
    elif isinstance(node, list):
        for value in node:
            collect_ids(value, found)


def continuation_token(node):
    if isinstance(node, dict):
        command = node.get("continuationCommand")
        if isinstance(command, dict) and isinstance(command.get("token"), str):
            return command["token"]
        for value in node.values():
            found = continuation_token(value)
            if found:
                return found
    elif isinstance(node, list):
        for value in node:
            found = continuation_token(value)
            if found:
                return found
    return ""


def tab_contents(data, title):
    tabs = (
        data.get("contents", {})
        .get("twoColumnBrowseResultsRenderer", {})
        .get("tabs", [])
    )
    if not isinstance(tabs, list):
        return []
    for tab in tabs:
        renderer = tab.get("tabRenderer") if isinstance(tab, dict) else None
        if not isinstance(renderer, dict):
            continue
        if str(renderer.get("title") or "").lower() != title:
            continue
        contents = ((renderer.get("content") or {}).get("richGridRenderer") or {}).get("contents")
        if isinstance(contents, list):
            return contents
    return []


def browse_more(html_text, token, seen):
    key_match = re.search(r'"INNERTUBE_API_KEY":"([^"]+)"', html_text)
    version_match = re.search(r'"INNERTUBE_CLIENT_VERSION":"([^"]+)"', html_text)
    if not key_match or not version_match or not token:
        return []
    url = f"https://www.youtube.com/youtubei/v1/browse?key={key_match.group(1)}&prettyPrint=false"
    found = []
    for _page in range(4):
        if not token or token in seen:
            break
        seen.add(token)
        try:
            payload = json.loads(fetch(url, data={
                "context": {
                    "client": {
                        "clientName": "WEB",
                        "clientVersion": version_match.group(1),
                        "hl": "en",
                        "gl": "US",
                    }
                },
                "continuation": token,
            }))
        except Exception:
            break
        ids = []
        collect_ids(payload, ids)
        fresh = [vid for vid in ids if vid not in found]
        found.extend(fresh)
        token = continuation_token(payload)
        if not fresh:
            break
    return found


def feed_entries():
    xml_text = fetch(f"https://www.youtube.com/feeds/videos.xml?channel_id={CHANNEL_ID}")
    root = ET.fromstring(xml_text)
    entries = []
    for entry in root.findall("a:entry", NS):
        link_node = entry.find("a:link", NS)
        link = link_node.get("href", "") if link_node is not None else ""
        entries.append({
            "id": entry.findtext("yt:videoId", default="", namespaces=NS),
            "title": entry.findtext("a:title", default="", namespaces=NS) or "",
            "published": entry.findtext("a:published", default="", namespaces=NS) or "",
            "description": entry.findtext("media:group/media:description", default="", namespaces=NS) or "",
            "link": link,
        })
    return entries


def tab_ids(url, title):
    page = fetch(url)
    data = json_object_after(page, "ytInitialData")
    if not data:
        raise ValueError(f"no ytInitialData on {url}")
    contents = tab_contents(data, title)
    ids = []
    collect_ids(contents, ids)
    ids.extend(browse_more(page, continuation_token(contents), set()))
    ordered = []
    for vid in ids:
        if vid not in ordered:
            ordered.append(vid)
    return ordered


def is_short(video_id):
    opener = urllib.request.build_opener(NoRedirect)
    req = urllib.request.Request(
        f"https://www.youtube.com/shorts/{video_id}",
        headers={"User-Agent": UA},
    )
    try:
        with opener.open(req, timeout=20) as response:
            return response.status == 200
    except urllib.error.HTTPError as error:
        if error.code in (301, 302, 303, 307, 308):
            location = error.headers.get("Location", "")
            if "/watch" in location:
                return False
        return None
    except Exception:
        return None


def watch_metadata(video_id):
    page = ""
    for agent in (META_UA, UA):
        try:
            page = fetch(f"https://www.youtube.com/watch?v={video_id}", user_agent=agent)
        except Exception:
            continue
        player = json_object_after(page, "ytInitialPlayerResponse") or {}
        details = player.get("videoDetails") or {}
        if details.get("title") and details.get("channelId"):
            micro = ((player.get("microformat") or {}).get("playerMicroformatRenderer") or {})
            published = parse_moment(micro.get("uploadDate") or micro.get("publishDate") or "")
            if not published:
                match = re.search(r'itemprop="uploadDate" content="([^"]+)"', page)
                if match:
                    published = parse_moment(html.unescape(match.group(1)))
            duration = iso_duration(details.get("lengthSeconds"))
            if not duration:
                match = re.search(r'itemprop="duration" content="([^"]+)"', page)
                if match and DURATION_RE.fullmatch(html.unescape(match.group(1))):
                    duration = html.unescape(match.group(1))
            return {
                "title": str(details.get("title") or "").strip(),
                "description": str(details.get("shortDescription") or ""),
                "published": published or "",
                "duration": duration,
                "channel": str(details.get("channelId") or ""),
            }
    return None


def discover(known_ids):
    """Ids from RSS and the Videos and Shorts tabs. Raises if every source fails."""
    hints = {}
    rss = {}
    errors = []
    try:
        entries = feed_entries()
    except Exception as error:
        entries = []
        errors.append(f"RSS failed ({error})")
        print(f"Videos: channel RSS failed ({error})", file=sys.stderr)
    for entry in entries:
        vid = entry["id"]
        if not VIDEO_ID.fullmatch(vid):
            continue
        rss[vid] = entry
        if "/shorts/" in entry["link"]:
            hints[vid] = "short"
        elif "/watch" in entry["link"]:
            hints[vid] = "long"
    for title, url, kind in (("videos", VIDEOS_PAGE, "long"), ("shorts", SHORTS_PAGE, "short")):
        try:
            for vid in tab_ids(url, title):
                hints[vid] = kind
        except Exception as error:
            errors.append(f"{title} tab failed ({error})")
            print(f"Videos: {title} tab failed ({error})", file=sys.stderr)
    if not hints and errors:
        raise RuntimeError("; ".join(errors))
    new_ids = [vid for vid in hints if vid not in known_ids]
    return hints, rss, new_ids


def record_from_network(video_id, hint, rss_entry):
    meta = None
    try:
        meta = watch_metadata(video_id)
    except Exception as error:
        print(f"  ! watch page failed for {video_id} ({error})", file=sys.stderr)
    if meta and meta.get("channel") and meta["channel"] != CHANNEL_ID:
        print(f"  ! {video_id} is not on this channel; skipping", file=sys.stderr)
        return None
    title = (meta or {}).get("title") or (rss_entry or {}).get("title") or ""
    description = (meta or {}).get("description")
    if description is None:
        description = (rss_entry or {}).get("description") or ""
    published = (meta or {}).get("published") or parse_moment((rss_entry or {}).get("published") or "")
    duration = (meta or {}).get("duration") or ""
    if not title or not published:
        print(f"  ! {video_id} has no title or publish time; skipping", file=sys.stderr)
        return None
    kind = hint
    if kind not in {"long", "short"}:
        short = is_short(video_id)
        if short is True:
            kind = "short"
        elif short is False:
            kind = "long"
        else:
            seconds = duration_seconds(duration)
            if seconds is None:
                print(f"  ! {video_id} type is unknown; skipping", file=sys.stderr)
                return None
            kind = "short" if seconds <= 180 else "long"
    record = {
        "id": video_id,
        "title": title.strip(),
        "type": kind,
        "published": published,
        "description": description,
    }
    if duration:
        record["duration"] = duration
    return record


def merge_new(current, additions):
    by_id = {item["id"]: item for item in current}
    for record in additions:
        if record["id"] in by_id:
            continue
        by_id[record["id"]] = record
    return list(by_id.values())


def thumb(video_id):
    return THUMB.format(vid=video_id)


def local_thumb(video_id):
    """Same-origin copy of the YouTube hqdefault, used only for the hub's first card."""
    path = THUMB_DIR / f"{video_id}.jpg"
    if path.is_file() and path.stat().st_size > 1000:
        return f"/images/video-thumbs/{video_id}.jpg"
    return ""


def ensure_local_thumb(video_id):
    """Save the YouTube thumbnail for the newest video. A network miss keeps the build going."""
    if local_thumb(video_id):
        return
    try:
        req = urllib.request.Request(thumb(video_id), headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=20) as response:
            data = response.read()
        if len(data) < 1000 or not data.startswith(b"\xff\xd8"):
            raise ValueError("response was not a JPEG")
        THUMB_DIR.mkdir(parents=True, exist_ok=True)
        (THUMB_DIR / f"{video_id}.jpg").write_bytes(data)
        print(f"Videos: saved thumbnail for {video_id}")
    except Exception as exc:
        print(f"Videos: thumbnail for {video_id} left on YouTube ({exc})", file=sys.stderr)


def description_html(cleaned):
    blocks = re.split(r"\n{2,}", cleaned)
    parts = []
    for block in blocks:
        lines = [esc(line) for line in block.split("\n") if line.strip()]
        if lines:
            parts.append("<p>" + "<br>\n".join(lines) + "</p>")
    return "\n".join(parts)


def json_script(payload):
    body = json.dumps(payload, ensure_ascii=False, indent=2).replace("<", "\\u003c")
    return f'  <script type="application/ld+json">\n{body}\n  </script>'


def video_object(video):
    cleaned = clean_description(video.get("description") or "") or video["title"]
    content = (
        f"https://www.youtube.com/watch?v={video['id']}"
        if video["type"] == "long"
        else f"https://www.youtube.com/shorts/{video['id']}"
    )
    obj = {
        "@type": "VideoObject",
        "@id": f"{SITE}/videos/#{video['id']}",
        "name": video["title"],
        "description": cleaned,
        "thumbnailUrl": thumb(video["id"]),
        "uploadDate": video["published"],
        "contentUrl": content,
        "embedUrl": f"https://www.youtube-nocookie.com/embed/{video['id']}",
    }
    if video.get("duration"):
        obj["duration"] = video["duration"]
    return obj


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
    return f"""  <a class="skip-link" href="#main">Skip to content</a>
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
        <a class="nav-videos" href="/videos/" aria-current="page">Videos</a>
        <a class="nav-articles" href="/articles/">Articles</a>
        <a class="nav-desktop" href="/#contact">Contact</a>
      </nav>
    </div>
  </header>
"""


def footer():
    return f"""  <footer class="footer" id="footer">
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
          <a href="{SUBSCRIBE}" rel="noopener noreferrer" target="_blank">YouTube<span class="visually-hidden"> (opens in a new tab)</span></a>
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


def head(title, description, canonical, image, preload_image):
    preload = ""
    if preload_image:
        preload = (
            f'\n  <link rel="preconnect" href="https://i.ytimg.com" crossorigin>'
            f'\n  <link rel="preload" as="image" href="{esc(preload_image)}" fetchpriority="high">'
        )
    image_meta = ""
    if image:
        image_meta = f"""
  <meta property="og:image" content="{esc(image)}">
  <meta property="og:image:width" content="480">
  <meta property="og:image:height" content="360">
  <meta property="og:image:type" content="image/jpeg">
  <meta property="og:image:alt" content="{esc(title)}">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:image" content="{esc(image)}">
  <meta name="twitter:image:alt" content="{esc(title)}">"""
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
  <link rel="canonical" href="{esc(canonical)}">{preload}
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
  <meta property="og:url" content="{esc(canonical)}">
  <meta property="og:site_name" content="Dog Unpacked">
  <meta property="og:title" content="{esc(title)}">
  <meta property="og:description" content="{esc(description)}">
  <meta name="twitter:title" content="{esc(title)}">
  <meta name="twitter:description" content="{esc(description)}">{image_meta}
</head>
"""


def filter_controls(breed_slugs, names):
    options = ['<option value="">All breeds</option>']
    fallback = [
        '<a href="/videos/">All</a>',
        '<a href="/videos/?type=long">Long-form</a>',
        '<a href="/videos/?type=short">Shorts</a>',
    ]
    for slug in breed_slugs:
        options.append(f'<option value="{esc(slug)}">{esc(names[slug])}</option>')
        fallback.append(f'<a href="/videos/?breed={esc(slug)}">{esc(names[slug])}</a>')
    return f"""    <form class="video-controls" id="video-controls" action="/videos/" method="get">
      <fieldset class="video-type">
        <legend>Type</legend>
        <div class="video-type-options">
          <label class="video-type-option"><input type="radio" name="type" value="" checked><span>All</span></label>
          <label class="video-type-option"><input type="radio" name="type" value="long"><span>Long-form</span></label>
          <label class="video-type-option"><input type="radio" name="type" value="short"><span>Shorts</span></label>
        </div>
      </fieldset>
      <div class="video-breed">
        <label for="video-breed">Breed</label>
        <select id="video-breed" name="breed">
          {''.join(options)}
        </select>
      </div>
    </form>
    <noscript>
      <style>.video-controls{{display:none}}</style>
      <nav class="video-fallback" aria-label="Filter videos">{''.join(fallback)}</nav>
    </noscript>
    <p class="video-empty" hidden>No videos match</p>"""


FILTER_SCRIPT = """  <script>
    (function () {
      var form = document.getElementById("video-controls");
      var breedSelect = document.getElementById("video-breed");
      var empty = document.querySelector(".video-empty");
      if (!form || !breedSelect) return;
      var cards = Array.prototype.slice.call(document.querySelectorAll(".video-card"));
      var radios = Array.prototype.slice.call(form.querySelectorAll('input[name="type"]'));
      var known = {};
      Array.prototype.forEach.call(breedSelect.options, function (option) {
        known[option.value] = true;
      });

      function readUrl() {
        var params = new URLSearchParams(location.search);
        var type = params.get("type");
        var slug = params.get("breed");
        var hash = location.hash.replace(/^#/, "");
        if (type !== "long" && type !== "short") {
          type = !params.has("type") && (hash === "long" || hash === "short") ? hash : "";
        }
        if (slug === null) {
          slug = hash && known[hash] ? hash : "";
        } else if (!known[slug]) {
          slug = "";
        }
        return {type: type, breed: slug};
      }

      function writeUrl(state) {
        var params = new URLSearchParams();
        if (state.type) params.set("type", state.type);
        if (state.breed) params.set("breed", state.breed);
        var query = params.toString();
        var next = location.pathname + (query ? "?" + query : "");
        var current = location.pathname + location.search + location.hash;
        if (next !== current) history.replaceState(null, "", next);
      }

      function current() {
        var type = "";
        radios.forEach(function (radio) {
          if (radio.checked) type = radio.value;
        });
        return {type: type, breed: breedSelect.value || ""};
      }

      function apply(state, updateUrl) {
        radios.forEach(function (radio) {
          radio.checked = radio.value === state.type;
        });
        breedSelect.value = state.breed;
        var shown = 0;
        cards.forEach(function (card) {
          var typeOk = !state.type || card.getAttribute("data-type") === state.type;
          var breeds = (card.getAttribute("data-breeds") || "").split(/\\s+/);
          var breedOk = !state.breed || breeds.indexOf(state.breed) !== -1;
          var match = typeOk && breedOk;
          card.hidden = !match;
          if (match) shown += 1;
        });
        if (empty) empty.hidden = shown !== 0;
        if (updateUrl) writeUrl(state);
      }

      apply(readUrl(), true);
      radios.forEach(function (radio) {
        radio.addEventListener("change", function () { apply(current(), true); });
      });
      breedSelect.addEventListener("change", function () { apply(current(), true); });
      form.addEventListener("submit", function (event) {
        event.preventDefault();
        apply(current(), true);
      });
    })();
  </script>
"""


def hub_page(videos, names):
    breed_slugs = []
    for video in videos:
        for slug in video["breeds"]:
            if slug not in breed_slugs:
                breed_slugs.append(slug)
    breed_slugs.sort(key=lambda slug: names[slug].lower())
    controls = filter_controls(breed_slugs, names)
    cards = []
    for index, video in enumerate(videos):
        eager = index == 0
        loading = ' loading="eager"' if eager else ' loading="lazy"'
        fetchpriority = ' fetchpriority="high"' if eager else ""
        decoding = "sync" if index == 0 else "async"
        if video["type"] == "long":
            href = f"/videos/{video['slug']}/"
            extra = ""
            kind = "Long-form"
        else:
            href = f"https://www.youtube.com/shorts/{video['id']}"
            extra = ' rel="noopener noreferrer" target="_blank"'
            kind = "Short"
        hidden = ""
        if video["type"] == "short":
            hidden = '<span class="visually-hidden"> (opens in a new tab)</span>'
        breed_html = ""
        if video["breeds"]:
            links = ", ".join(
                f'<a href="/breeds/{esc(slug)}/">{esc(names[slug])}</a>' for slug in video["breeds"]
            )
            breed_html = f'<p class="video-card-breeds">{links}</p>'
        length = duration_card(video.get("duration"))
        kicker = esc(kind if not length else f"{kind} · {length}")
        data_breeds = " ".join(video["breeds"])
        src = local_thumb(video["id"]) if index == 0 else ""
        src = src or thumb(video["id"])
        referrer = "" if src.startswith("/") else ' referrerpolicy="no-referrer"'
        cards.append(
            f'<li class="video-card" data-type="{esc(video["type"])}" data-breeds="{esc(data_breeds)}">'
            f'<a class="video-card-link" href="{esc(href)}"{extra}>'
            f'<span class="video-card-media"><img src="{esc(src)}" width="480" height="360" alt=""{loading}{fetchpriority} decoding="{decoding}"{referrer}></span>'
            f'<span class="video-card-body"><p class="video-card-kicker">{kicker}</p>'
            f"<h2>{esc(video['title'])}</h2>"
            f'<time datetime="{esc(video["published"])}">{esc(format_day(video["published"]))}</time>'
            f"{hidden}</span></a>{breed_html}</li>"
        )
    graph = [
        breadcrumb([("Dog Unpacked", f"{SITE}/"), ("Videos", f"{SITE}/videos/")]),
        {
            "@type": "ItemList",
            "name": HUB_TITLE,
            "numberOfItems": len(videos),
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": index,
                    "name": video["title"],
                    "url": (
                        f"{SITE}/videos/{video['slug']}/"
                        if video["type"] == "long"
                        else f"https://www.youtube.com/shorts/{video['id']}"
                    ),
                }
                for index, video in enumerate(videos, start=1)
            ],
        },
    ]
    graph.extend(video_object(video) for video in videos)
    payload = {"@context": "https://schema.org", "@graph": graph}
    image = thumb(videos[0]["id"]) if videos else ""
    preload = (local_thumb(videos[0]["id"]) if videos else "") or image
    page = f"""{head(HUB_TITLE, HUB_DESC, f"{SITE}/videos/", image, preload)}
<body>
{header()}
  <main id="main">
    <div class="video-hub">
      <nav class="crumbs" aria-label="Breadcrumb">
        <a href="/">Dog Unpacked</a>
        <span aria-hidden="true">/</span>
        <span aria-current="page">Videos</span>
      </nav>
      <h1>Dog breed videos</h1>
      <p class="video-dek">Long-form videos and Shorts from Dog Unpacked, newest first.</p>
      <p class="video-subscribe"><a href="{SUBSCRIBE}" rel="noopener noreferrer" target="_blank">Subscribe on YouTube<span class="visually-hidden"> (opens in a new tab)</span></a></p>
      {controls}
      <ul class="video-list">
        {''.join(cards)}
      </ul>
    </div>
  </main>
{footer()}
{FILTER_SCRIPT}
{json_script(payload)}
{goatcounter()}</body>
</html>
"""
    return page


def related_items(video, videos, names):
    same = []
    others = []
    for other in videos:
        if other["id"] == video["id"]:
            continue
        shared = set(other["breeds"]) & set(video["breeds"])
        if video["breeds"] and shared:
            same.append(other)
        else:
            others.append(other)
    picks = (same + others)[:4]
    items = []
    for other in picks:
        if other["type"] == "long":
            href = f"/videos/{other['slug']}/"
            extra = ""
            hidden = ""
        else:
            href = f"https://www.youtube.com/shorts/{other['id']}"
            extra = ' rel="noopener noreferrer" target="_blank"'
            hidden = '<span class="visually-hidden"> (opens in a new tab)</span>'
        items.append(f'<li><a href="{esc(href)}"{extra}>{esc(other["title"])}</a>{hidden}</li>')
    return "\n".join(items)


def watch_page(video, videos, names):
    canonical = f"{SITE}/videos/{video['slug']}/"
    cleaned = clean_description(video.get("description") or "")
    description = meta_sentence(video["title"], cleaned)
    graph = {
        "@context": "https://schema.org",
        "@graph": [
            breadcrumb([
                ("Dog Unpacked", f"{SITE}/"),
                ("Videos", f"{SITE}/videos/"),
                (video["title"], canonical),
            ]),
            video_object(video),
        ],
    }
    breed_html = ""
    if video["breeds"]:
        label = "Breed page" if len(video["breeds"]) == 1 else "Breed pages"
        links = ", ".join(
            f'<a href="/breeds/{esc(slug)}/">{esc(names[slug])}</a>' for slug in video["breeds"]
        )
        breed_html = f'<p class="video-breeds">{label}: {links}</p>'
    length = duration_phrase(video.get("duration"))
    meta = f'<time datetime="{esc(video["published"])}">{esc(format_day(video["published"]))}</time>'
    if length:
        meta += f" · {esc(length)}"
    transcript_html = ""
    transcript = video.get("transcript") or ""
    if transcript:
        transcript_html = (
            "<h2>Transcript excerpt</h2>\n"
            f'<div class="video-transcript">{description_html(transcript)}</div>'
        )
    body_html = description_html(cleaned)
    image = thumb(video["id"])
    watch_url = f"https://www.youtube.com/watch?v={video['id']}"
    page = f"""{head(video["title"], description, canonical, image, image)}
<body>
{header()}
  <main id="main">
    <article class="video-watch">
      <nav class="crumbs" aria-label="Breadcrumb">
        <a href="/">Dog Unpacked</a>
        <span aria-hidden="true">/</span>
        <a href="/videos/">Videos</a>
        <span aria-hidden="true">/</span>
        <span aria-current="page">{esc(video["title"])}</span>
      </nav>
      <p class="video-kicker">Dog Unpacked</p>
      <h1>{esc(video["title"])}</h1>
      <p class="video-meta">{meta}</p>
      {breed_html}
      <div class="lite-yt" id="watch-embed">
        <button type="button" class="lite-yt-btn" aria-label="Play: {esc(video["title"])}">
          <img src="{esc(image)}" alt="" width="480" height="360" decoding="async" fetchpriority="high" referrerpolicy="no-referrer">
          {PLAY_SVG}
        </button>
      </div>
      <p class="video-yt"><a href="{esc(watch_url)}" rel="noopener noreferrer" target="_blank">Watch on YouTube<span class="visually-hidden"> (opens in a new tab)</span></a></p>
      <h2>Description</h2>
      <div class="video-description">
        {body_html}
      </div>
      {transcript_html}
      <h2>More videos</h2>
      <ul class="video-more">
        {related_items(video, videos, names)}
      </ul>
      <p class="video-subscribe"><a href="{SUBSCRIBE}" rel="noopener noreferrer" target="_blank">Subscribe on YouTube<span class="visually-hidden"> (opens in a new tab)</span></a></p>
    </article>
  </main>
{footer()}
  <script>
    (function () {{
      var root = document.getElementById("watch-embed");
      if (!root) return;
      var btn = root.querySelector(".lite-yt-btn");
      if (!btn) return;
      btn.addEventListener("click", function () {{
        var iframe = document.createElement("iframe");
        iframe.src = "https://www.youtube-nocookie.com/embed/{video["id"]}?autoplay=1&rel=0";
        iframe.title = {json.dumps(video["title"])};
        iframe.allow = "accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share";
        iframe.allowFullscreen = true;
        iframe.referrerPolicy = "strict-origin-when-cross-origin";
        root.textContent = "";
        root.appendChild(iframe);
      }});
    }})();
  </script>
{json_script(graph)}
{goatcounter()}</body>
</html>
"""
    return page


def write_pages(videos, breeds):
    if videos:
        ensure_local_thumb(videos[0]["id"])
    names = breed_names(breeds)
    VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
    (VIDEOS_DIR / "index.html").write_text(hub_page(videos, names), encoding="utf-8")
    slugs = set()
    for video in videos:
        if video["type"] != "long":
            continue
        slug = video["slug"]
        slugs.add(slug)
        folder = VIDEOS_DIR / slug
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "index.html").write_text(watch_page(video, videos, names), encoding="utf-8")
    if VIDEOS_DIR.is_dir():
        for child in VIDEOS_DIR.iterdir():
            if child.is_dir() and child.name not in slugs:
                index = child / "index.html"
                if index.is_file():
                    index.unlink()
                try:
                    child.rmdir()
                except OSError:
                    pass
    return slugs


def xml_text(value):
    return html.escape(str(value), quote=False)


def write_video_sitemap(videos):
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"',
        '        xmlns:video="http://www.google.com/schemas/sitemap-video/1.1">',
    ]
    shorts = [video for video in videos if video["type"] == "short"]
    longs = [video for video in videos if video["type"] == "long"]

    def video_block(video):
        cleaned = clean_description(video.get("description") or "") or video["title"]
        if len(cleaned) > 2048:
            cleaned = cleaned[:2048].rsplit(" ", 1)[0]
        seconds = duration_seconds(video.get("duration"))
        duration = f"\n      <video:duration>{seconds}</video:duration>" if seconds is not None else ""
        content = (
            f"https://www.youtube.com/watch?v={video['id']}"
            if video["type"] == "long"
            else f"https://www.youtube.com/shorts/{video['id']}"
        )
        return (
            "    <video:video>\n"
            f"      <video:thumbnail_loc>{xml_text(thumb(video['id']))}</video:thumbnail_loc>\n"
            f"      <video:title>{xml_text(video['title'])}</video:title>\n"
            f"      <video:description>{xml_text(cleaned)}</video:description>\n"
            f"      <video:player_loc>https://www.youtube-nocookie.com/embed/{xml_text(video['id'])}</video:player_loc>\n"
            f"      <video:content_loc>{xml_text(content)}</video:content_loc>"
            f"{duration}\n"
            f"      <video:publication_date>{xml_text(video['published'])}</video:publication_date>\n"
            "      <video:family_friendly>yes</video:family_friendly>\n"
            "      <video:live>no</video:live>\n"
            "    </video:video>"
        )

    if shorts:
        blocks = "\n".join(video_block(video) for video in shorts)
        lines.append(f"  <url>\n    <loc>{SITE}/videos/</loc>\n{blocks}\n  </url>")
    for video in sorted(longs, key=lambda item: (item["published"], item["id"])):
        lines.append(
            f"  <url>\n    <loc>{SITE}/videos/{xml_text(video['slug'])}/</loc>\n"
            f"{video_block(video)}\n  </url>"
        )
    lines.append("</urlset>")
    SITEMAP_VIDEOS.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_robots():
    text = ROBOTS.read_text(encoding="utf-8") if ROBOTS.is_file() else "User-agent: *\nAllow: /\n"
    line = "Sitemap: https://dogunpacked.com/sitemap-videos.xml"
    if line not in text:
        if not text.endswith("\n"):
            text += "\n"
        text += line + "\n"
        ROBOTS.write_text(text, encoding="utf-8")


def write_json(videos):
    DATA.parent.mkdir(parents=True, exist_ok=True)
    DATA.write_text(json.dumps(videos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def refresh(current, only_id=None):
    known = {item["id"] for item in current}
    if only_id:
        if not VIDEO_ID.fullmatch(only_id):
            raise SystemExit(f"not a video id: {only_id}")
        if only_id in known:
            print(f"Videos: {only_id} already listed; left unchanged")
            return current, False
        record = record_from_network(only_id, "", None)
        if not record:
            print(f"Videos: could not add {only_id}", file=sys.stderr)
            return current, False
        print(f"Videos: added {only_id} ({record['type']})")
        return merge_new(current, [record]), True
    try:
        hints, rss, new_ids = discover(known)
    except Exception as error:
        print(f"Videos: feed unavailable ({error}). Rebuilding from data/videos.json.", file=sys.stderr)
        return current, False
    additions = []
    for vid in new_ids:
        record = record_from_network(vid, hints.get(vid, ""), rss.get(vid))
        if record:
            additions.append(record)
            print(f"  + {record['type']:<5} {record['published']}  {vid}  {record['title']}")
        # An id that could not be read stays out of the file so the next run retries it.
    if not additions:
        print("Videos: no new uploads")
    return merge_new(current, additions), bool(additions)


def refresh_sitemap():
    import build_sitemap

    build_sitemap.write()


def build(videos, breeds):
    videos = prepare(videos, breeds)
    write_pages(videos, breeds)
    write_json(videos)
    write_video_sitemap(videos)
    write_robots()
    refresh_sitemap()
    longs = [video for video in videos if video["type"] == "long"]
    shorts = [video for video in videos if video["type"] == "short"]
    transcripts = [video["id"] for video in videos if video.get("transcript")]
    print(
        f"Wrote /videos/ ({len(videos)} videos, {len(longs)} long, {len(shorts)} short) "
        f"and {len(longs)} watch pages."
    )
    if transcripts:
        print("Transcripts used for: " + ", ".join(transcripts))
    else:
        print("Transcripts: none. Caption tracks were not available, so no excerpt was added.")
    return videos


def main():
    parser = argparse.ArgumentParser(description="Build the Dog Unpacked videos hub.")
    parser.add_argument("--refresh", action="store_true", help="add new uploads from YouTube, then rebuild")
    parser.add_argument("--add", metavar="VIDEO_ID", help="add one video id if it is not already listed")
    args = parser.parse_args()
    if args.refresh and args.add:
        print("Use either --refresh or --add, not both.", file=sys.stderr)
        return 2
    breeds = load_breeds()
    try:
        current = load_videos()
    except ValueError as error:
        print(f"data/videos.json is not valid JSON ({error})", file=sys.stderr)
        return 1
    changed = False
    if args.refresh or args.add:
        try:
            current, changed = refresh(current, only_id=args.add)
        except SystemExit:
            raise
        except Exception as error:
            print(f"Videos: refresh failed ({error}). Rebuilding from the current file.", file=sys.stderr)
            changed = False
        if args.add and not changed and args.add not in {item["id"] for item in current}:
            if current:
                build(current, breeds)
            return 1
    elif not current:
        print("data/videos.json is missing. Run python3 scripts/build_videos.py --refresh", file=sys.stderr)
        return 1
    build(current, breeds)
    return 0


if __name__ == "__main__":
    sys.exit(main())
