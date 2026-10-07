#!/usr/bin/env python3
"""
Dog Unpacked — send today's issue of The Sniff Test (weekly newsletter) via Kit (ConvertKit) API v4.

Looks for newsletters/YYYY-MM-DD.md using America's New York (ET) calendar date.
Opt-in only: a live send happens ONLY when that file's frontmatter has `status: ready`.
Exits 0 (no-op success) when there is no file for today, the status is anything other
than `ready` (missing, draft, ...), or frontmatter send: false.

Usage:
  python3 scripts/send.py              # live send (requires KIT_API_KEY)
  python3 scripts/send.py --dry-run    # parse + print payload; no POST

Env:
  KIT_API_KEY   Kit API v4 key (X-Kit-Api-Key). Required unless --dry-run.

Idempotency note:
  Kit's POST /v4/broadcasts has no idempotency key. Re-running this script on
  the same day can create a duplicate broadcast. Best-effort: before POST we
  GET /v4/broadcasts?slim=true and skip if an existing broadcast subject
  exactly matches this issue's subject. That is not a guarantee (pagination,
  renamed subjects, race with another runner). Prefer one scheduled workflow
  run + dry_run default true on manual dispatch.
"""

from __future__ import annotations

import argparse
import html
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

try:
    import json
except ImportError:  # pragma: no cover
    json = None  # type: ignore

ROOT = Path(__file__).resolve().parents[1]
NEWSLETTERS = ROOT / "newsletters"
KIT_API = "https://api.kit.com/v4"
ET = ZoneInfo("America/New_York")

# Kit injects the CAN-SPAM postal footer (shared Kit address). Do not put
# personal mailing addresses here. If a brand address must ever be hardcoded,
# use ONLY: 600 1st Ave, Ste 330 PMB 92768, Seattle, WA 98104-2246
DISCLAIMER_HTML = (
    '<hr style="border:none;border-top:1px solid #E0D4BC;margin:2em 0 1em;">'
    '<p style="font-size:12px;line-height:1.5;color:#6B7A94;">'
    "Educational content only — not veterinary or training advice. "
    "The Sniff Test by Dog Unpacked."
    "<br>"
    '<a href="{{ unsubscribe_url }}">Unsubscribe</a>'
    "</p>"
)


def today_et() -> datetime:
    return datetime.now(ET)


def issue_path_for(day: datetime) -> Path:
    return NEWSLETTERS / f"{day.strftime('%Y-%m-%d')}.md"


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Parse simple YAML-ish frontmatter between --- fences. Body is the rest."""
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    meta_raw, body = parts[1], parts[2]
    meta: dict = {}
    for line in meta_raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, val = line.split(":", 1)
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if val.lower() in ("true", "yes"):
            meta[key] = True
        elif val.lower() in ("false", "no"):
            meta[key] = False
        else:
            meta[key] = val
    return meta, body.lstrip("\n")


def strip_html_comments(text: str) -> str:
    return re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)


def md_to_simple_html(md: str) -> str:
    """Minimal Markdown → HTML (headings, links, lists, paragraphs). Good enough for Kit Classic body."""
    lines = strip_html_comments(md).splitlines()
    out: list[str] = []
    in_ul = False

    def close_ul() -> None:
        nonlocal in_ul
        if in_ul:
            out.append("</ul>")
            in_ul = False

    def inline(s: str) -> str:
        s = html.escape(s)
        s = re.sub(
            r"\[([^\]]+)\]\((https?://[^)]+)\)",
            r'<a href="\2">\1</a>',
            s,
        )
        s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
        s = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", s)
        return s

    para: list[str] = []

    def flush_para() -> None:
        nonlocal para
        if para:
            out.append("<p>" + " ".join(inline(p) for p in para) + "</p>")
            para = []

    for raw in lines:
        line = raw.rstrip()
        if not line.strip():
            flush_para()
            close_ul()
            continue
        if line.startswith("## "):
            flush_para()
            close_ul()
            out.append(f"<h2>{inline(line[3:].strip())}</h2>")
            continue
        if line.startswith("# "):
            flush_para()
            close_ul()
            out.append(f"<h1>{inline(line[2:].strip())}</h1>")
            continue
        if line.lstrip().startswith("- "):
            flush_para()
            if not in_ul:
                out.append("<ul>")
                in_ul = True
            out.append(f"<li>{inline(line.lstrip()[2:].strip())}</li>")
            continue
        close_ul()
        para.append(line.strip())

    flush_para()
    close_ul()
    return "\n".join(out)


def kit_request(method: str, path: str, api_key: str, payload: dict | None = None) -> dict:
    url = f"{KIT_API}{path}"
    data = None
    headers = {
        "X-Kit-Api-Key": api_key,
        "Accept": "application/json",
    }
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        raise SystemExit(f"Kit API {method} {path} failed: HTTP {e.code}: {err_body}") from e


def subject_already_sent(api_key: str, subject: str) -> bool:
    """Best-effort duplicate check via list broadcasts (slim). Not authoritative."""
    # First page only; Kit default page size is large enough for recent sends.
    data = kit_request("GET", "/broadcasts?slim=true", api_key)
    broadcasts = data.get("broadcasts") or data.get("data") or []
    for b in broadcasts:
        if (b.get("subject") or "").strip() == subject.strip():
            return True
    return False


def build_payload(meta: dict, body_md: str) -> dict:
    subject = (meta.get("subject") or "").strip()
    preview = (meta.get("preview") or "").strip()
    if not subject:
        raise SystemExit("Frontmatter missing required 'subject'.")
    content = md_to_simple_html(body_md) + "\n" + DISCLAIMER_HTML
    # send_at = now → schedule immediately; omit subscriber_filter → all subscribers.
    send_at = datetime.now(ET).astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%SZ")
    # Omit subscriber_filter → Kit defaults to all subscribers.
    # To target a segment/tag later, add e.g.:
    #   "subscriber_filter": [{"all": [{"type": "segment", "ids": [SEGMENT_ID]}], "any": None, "none": None}]
    return {
        "subject": subject,
        "preview_text": preview,
        "description": subject,
        "content": content,
        "public": False,
        "published_at": send_at,
        "send_at": send_at,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Send The Sniff Test (Dog Unpacked newsletter) via Kit.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and print the Kit payload; do not POST.",
    )
    args = parser.parse_args()

    day = today_et()
    path = issue_path_for(day)
    print(f"ET date: {day.strftime('%Y-%m-%d %Z')}")
    print(f"Looking for: {path.relative_to(ROOT)}")

    if not path.is_file():
        print("No issue file for today — exiting 0 (no-op).")
        return 0

    text = path.read_text(encoding="utf-8")
    meta, body = parse_frontmatter(text)
    if meta.get("send") is False:
        print("Frontmatter send: false — skipping send, exiting 0.")
        return 0

    status = str(meta.get("status") or "").strip().lower()
    ready = status == "ready"

    payload = build_payload(meta, body)

    if args.dry_run:
        if not ready:
            print(
                f"NOTE: frontmatter status is {status or 'missing'!r}, not 'ready' — "
                "a live run would skip this issue."
            )
        print("DRY RUN — payload that would be POSTed to /v4/broadcasts:")
        print(json.dumps(payload, indent=2))
        print("(No Kit API call made.)")
        return 0

    if not ready:
        print(
            f"Frontmatter status is {status or 'missing'!r}, not 'ready' — "
            "skipping send (opt-in only), exiting 0."
        )
        return 0

    api_key = os.environ.get("KIT_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("KIT_API_KEY is not set. Refusing live send.")

    if subject_already_sent(api_key, payload["subject"]):
        print(
            f"Best-effort skip: a broadcast with subject "
            f"{payload['subject']!r} already exists. Exiting 0."
        )
        return 0

    result = kit_request("POST", "/broadcasts", api_key, payload)
    bid = (result.get("broadcast") or {}).get("id")
    print(f"Created Kit broadcast id={bid}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
