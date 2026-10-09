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
  python3 scripts/send.py --dry-run --preview-out /tmp/issue.html   # + browser preview
  python3 scripts/send.py --write-kit-template kit/sniff-test-template.html
  python3 scripts/send.py --list-templates   # read-only GET /v4/email_templates

Every issue is wrapped in the branded "The Sniff Test" email design automatically
(render_email_content); the Markdown authoring format is unchanged.

Env:
  KIT_API_KEY            Kit API v4 key (X-Kit-Api-Key). Required unless --dry-run.
  KIT_SNIFF_TEMPLATE_ID  Optional. Kit id of the custom HTML template made from
                         kit/sniff-test-template.html; sent as email_template_id.

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

# Kit injects the CAN-SPAM postal footer (shared Kit address) via {{ address }}. Do not put
# personal mailing addresses here. If a brand address must ever be hardcoded,
# use ONLY: 600 1st Ave, Ste 330 PMB 92768, Seattle, WA 98104-2246

# Optional: id of the Kit custom HTML template built from kit/sniff-test-template.html
# (GitHub Actions variable or secret). When set, broadcasts use it (email_template_id) and the
# template supplies the Unsubscribe + mailing-address line. When unset, Kit's account default
# template is used (it adds its own footer under ours). See README-newsletter.md.
TEMPLATE_ENV = "KIT_SNIFF_TEMPLATE_ID"


def sniff_template_id() -> int | None:
    raw = os.environ.get(TEMPLATE_ENV, "").strip()
    if not raw:
        return None
    if not raw.isdigit():
        raise SystemExit(f"{TEMPLATE_ENV} must be a numeric Kit email template id, got {raw!r}.")
    return int(raw)


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


# ---------------------------------------------------------------------------
# Branded email design ("The Sniff Test" wrapper)
# ---------------------------------------------------------------------------
# Brand tokens copied from styles.css (:root) on dogunpacked.com.
NAVY = "#1B2A4A"
NAVY_INK = "#152238"
NAVY_SOFT = "#3A4A6A"
NAVY_MUTED = "#4F5D78"
CREAM = "#F5EDDC"
CREAM_DEEP = "#EFE6D4"
CARD = "#FBF6EC"
AMBER = "#D89B3D"  # accent only, never body text (same rule as the site)
KRAFT_INK = "#8C6239"
BORDER = "#E0D4BC"

SITE_URL = "https://dogunpacked.com"
LOGO_URL = f"{SITE_URL}/images/logo-256.png"  # 256px PNG, transparent corners, shown at 72px
WORDMARK = "The Sniff Test"
TAGLINE = "Every breed, one at a time"

# Web-safe stacks. Fraunces/Nunito load (from dogunpacked.com) only in clients that
# support web fonts (Apple Mail, iOS Mail); everyone else gets Georgia / Helvetica-Arial.
FONT_TEXT = "Nunito,'Helvetica Neue',Helvetica,Arial,sans-serif"
FONT_DISPLAY = "Fraunces,Georgia,'Times New Roman',serif"

# Kit Liquid. Kit replaces these at send time (the current pipeline already relies on it).
UNSUBSCRIBE_URL = "{{ unsubscribe_url }}"
ADDRESS = "{{ address }}"

EMAIL_CSS = (
    "@font-face{font-family:Fraunces;font-style:normal;font-weight:500 800;"
    f"src:url('{SITE_URL}/fonts/fraunces-latin.woff2') format('woff2');}}"
    "@font-face{font-family:Nunito;font-style:normal;font-weight:400 800;"
    f"src:url('{SITE_URL}/fonts/nunito-latin.woff2') format('woff2');}}"
    "body{margin:0!important;padding:0!important;-webkit-text-size-adjust:100%;-ms-text-size-adjust:100%;}"
    "table,td{mso-table-lspace:0pt;mso-table-rspace:0pt;}"
    "img{border:0;outline:none;text-decoration:none;-ms-interpolation-mode:bicubic;}"
    "a[x-apple-data-detectors]{color:inherit!important;text-decoration:none!important;}"
    ".sn-link:hover{color:" + KRAFT_INK + "!important;}"
    "@media screen and (max-width:520px){"
    ".sn-outer{padding:12px 0 24px!important;}"
    ".sn-pad{padding-left:22px!important;padding-right:22px!important;}"
    ".sn-body{padding-top:28px!important;padding-bottom:28px!important;}"
    ".sn-text,.sn-text li{font-size:17px!important;line-height:1.6!important;}"
    ".sn-h1{font-size:28px!important;}"
    ".sn-word{font-size:28px!important;}"
    ".sn-btn a{display:block!important;}"
    ".sn-radius-top{border-radius:0!important;}"
    ".sn-radius-bottom{border-radius:0!important;}"
    "}"
    "@media (prefers-color-scheme:dark){"
    ".sn-bg{background:#0E1626!important;}"
    ".sn-card{background:" + NAVY_INK + "!important;border-color:" + NAVY_SOFT + "!important;}"
    ".sn-card,.sn-text,.sn-text li,.sn-h1,.sn-h2,.sn-sign{color:" + CREAM + "!important;}"
    ".sn-link{color:" + AMBER + "!important;}"
    ".sn-muted,.sn-muted a{color:#B9C1D3!important;}"
    ".sn-reply{background:#1F2F52!important;}"
    ".sn-btn td{background:" + AMBER + "!important;}"
    ".sn-btn a{color:" + NAVY + "!important;background:" + AMBER + "!important;}"
    "}"
    # Outlook.com dark mode
    "[data-ogsc] .sn-text,[data-ogsc] .sn-text li,[data-ogsc] .sn-h1,[data-ogsc] .sn-sign{color:" + CREAM + "!important;}"
    "[data-ogsc] .sn-link{color:" + AMBER + "!important;}"
)

# Outlook (Windows) ignores web fonts and would fall back to Times; pin it to safe fonts.
MSO_HEAD = (
    "<!--[if mso]><noscript><xml><o:OfficeDocumentSettings><o:PixelsPerInch>96</o:PixelsPerInch>"
    "</o:OfficeDocumentSettings></xml></noscript>"
    "<style>td,p,li,a,span{font-family:Arial,Helvetica,sans-serif!important;}"
    ".sn-serif{font-family:Georgia,'Times New Roman',serif!important;}</style><![endif]-->"
)

YOUTUBE_ID_RE = re.compile(
    r"(?:youtu\.be/|youtube\.com/(?:watch\?(?:[^#\s]*&)?v=|shorts/|embed/|live/))([A-Za-z0-9_-]{11})"
)
REPLY_RE = re.compile(r"\b(hit|just|simply)\s+reply\b|\breply to this\b", re.IGNORECASE)
LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")


def _p_style(size: int = 17, color: str = NAVY, extra: str = "") -> str:
    return (
        f"margin:0 0 20px;font-family:{FONT_TEXT};font-size:{size}px;line-height:1.6;"
        f"color:{color};{extra}"
    )


def _inline_email(s: str, link_color: str = NAVY) -> str:
    """Escape + inline Markdown (links, bold, italic) with email-safe inline styles."""
    s = html.escape(s, quote=False)
    s = re.sub(
        r"\[([^\]]+)\]\((https?://[^)\s]+)\)",
        lambda m: (
            f'<a href="{html.escape(m.group(2), quote=True)}" class="sn-link" target="_blank" '
            f'style="color:{link_color};font-weight:700;text-decoration:underline;'
            f'text-decoration-color:{AMBER};text-decoration-thickness:2px;text-underline-offset:3px;">'
            f"{m.group(1)}</a>"
        ),
        s,
    )
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", s)
    return s


def md_blocks(md: str) -> list[tuple[str, object]]:
    """Split the issue Markdown into blocks: ('p', text) / ('h1'|'h2', text) / ('ul', [items])."""
    blocks: list[tuple[str, object]] = []
    para: list[str] = []
    items: list[str] = []

    def flush() -> None:
        nonlocal para, items
        if para:
            blocks.append(("p", " ".join(para)))
            para = []
        if items:
            blocks.append(("ul", items))
            items = []

    for raw in strip_html_comments(md).splitlines():
        line = raw.rstrip()
        if not line.strip():
            flush()
        elif line.startswith("## "):
            flush()
            blocks.append(("h2", line[3:].strip()))
        elif line.startswith("# "):
            flush()
            blocks.append(("h1", line[2:].strip()))
        elif line.lstrip().startswith("- "):
            if para:
                blocks.append(("p", " ".join(para)))
                para = []
            items.append(line.lstrip()[2:].strip())
        else:
            if items:
                blocks.append(("ul", items))
                items = []
            para.append(line.strip())
    flush()
    return blocks


def youtube_thumbnail(video_id: str, check: bool = True) -> str:
    """i.ytimg.com thumbnail: 1280x720 maxres when it exists, else the always-present hqdefault."""
    maxres = f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg"
    if not check:
        return maxres
    try:
        req = urllib.request.Request(maxres, method="HEAD")
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                return maxres
    except Exception:  # noqa: BLE001 - any failure → safe fallback
        pass
    return f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"


def _divider(width: int = 48) -> str:
    return (
        '<table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin:8px 0 24px;">'
        f'<tr><td width="{width}" height="3" bgcolor="{AMBER}" '
        f'style="width:{width}px;height:3px;line-height:3px;font-size:0;background:{AMBER};border-radius:2px;">&nbsp;</td></tr>'
        "</table>"
    )


def _video_block(text: str, check_thumb: bool) -> str | None:
    m = LINK_RE.search(text)
    if not m:
        return None
    vid = YOUTUBE_ID_RE.search(m.group(2))
    if not vid:
        return None
    url = html.escape(m.group(2), quote=True)
    title = html.escape(m.group(1), quote=False)
    label = text[: m.start()].strip().rstrip(":").strip()
    label_html = html.escape(label or "New on YouTube", quote=False)
    thumb = html.escape(youtube_thumbnail(vid.group(1), check_thumb), quote=True)
    alt = html.escape(m.group(1), quote=True)
    return (
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:8px 0 28px;">'
        f'<tr><td style="padding:0 0 6px;font-family:{FONT_TEXT};font-size:12px;line-height:1.4;font-weight:800;'
        f'letter-spacing:1.5px;text-transform:uppercase;color:{KRAFT_INK};" class="sn-muted">{label_html}</td></tr>'
        f'<tr><td style="padding:0 0 14px;"><a href="{url}" target="_blank" class="sn-h2 sn-serif" '
        f'style="font-family:{FONT_DISPLAY};font-size:21px;line-height:1.3;font-weight:700;color:{NAVY};text-decoration:none;">'
        f"{title}</a></td></tr>"
        f'<tr><td style="padding:0 0 16px;"><a href="{url}" target="_blank" style="text-decoration:none;">'
        f'<img src="{thumb}" width="520" alt="{alt}" '
        f'style="display:block;width:100%;max-width:520px;height:auto;border-radius:10px;border:1px solid {BORDER};"></a></td></tr>'
        '<tr><td align="left">'
        '<table role="presentation" cellpadding="0" cellspacing="0" border="0" class="sn-btn"><tr>'
        f'<td align="center" bgcolor="{NAVY}" style="border-radius:10px;background:{NAVY};">'
        f'<a href="{url}" target="_blank" style="display:inline-block;padding:14px 26px;font-family:{FONT_TEXT};'
        f'font-size:16px;line-height:1.2;font-weight:800;color:{CREAM};text-decoration:none;border-radius:10px;'
        f'background:{NAVY};">Watch on YouTube</a></td></tr></table>'
        "</td></tr></table>"
    )


def _reply_block(text: str) -> str:
    return (
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:4px 0 28px;">'
        f'<tr><td class="sn-reply" bgcolor="{CREAM}" style="background:{CREAM};border-left:4px solid {AMBER};'
        'border-radius:0 10px 10px 0;padding:18px 22px;">'
        f'<p class="sn-text" style="{_p_style(extra="margin:0;")}">{_inline_email(text)}</p>'
        "</td></tr></table>"
    )


def render_issue_body(body_md: str, check_thumb: bool = True) -> str:
    """Body blocks → styled HTML. Authoring stays plain Markdown; patterns pick the styling:
    a paragraph with a YouTube link → video card + navy button; 'hit reply' → gold-accent box;
    a closing line starting with an em dash → signature (the line just before it → tagline)."""
    blocks = md_blocks(body_md)
    sig_idx = None
    for i in range(len(blocks) - 1, -1, -1):
        kind, val = blocks[i]
        if kind == "p" and str(val).lstrip().startswith(("—", "–", "-- ")):
            sig_idx = i
            break
    tagline_idx = None
    if sig_idx is not None and sig_idx > 0 and blocks[sig_idx - 1][0] == "p":
        prev = str(blocks[sig_idx - 1][1])
        if len(prev) <= 90 and not LINK_RE.search(prev) and not REPLY_RE.search(prev):
            tagline_idx = sig_idx - 1

    out: list[str] = []
    for i, (kind, val) in enumerate(blocks):
        if kind == "h1":
            out.append(
                f'<h2 class="sn-h2 sn-serif" style="margin:8px 0 14px;font-family:{FONT_DISPLAY};font-size:24px;'
                f'line-height:1.25;font-weight:700;color:{NAVY};">{_inline_email(str(val))}</h2>'
            )
        elif kind == "h2":
            out.append(
                f'<h3 class="sn-h2 sn-serif" style="margin:8px 0 12px;font-family:{FONT_DISPLAY};font-size:21px;'
                f'line-height:1.3;font-weight:700;color:{NAVY};">{_inline_email(str(val))}</h3>'
            )
        elif kind == "ul":
            lis = "".join(
                f'<li style="margin:0 0 8px;font-family:{FONT_TEXT};font-size:17px;line-height:1.6;color:{NAVY};">'
                f"{_inline_email(it)}</li>"
                for it in val  # type: ignore[union-attr]
            )
            out.append(f'<ul class="sn-text" style="margin:0 0 20px;padding:0 0 0 22px;">{lis}</ul>')
        elif i == tagline_idx:
            out.append(_divider())
            out.append(
                f'<p class="sn-sign sn-serif" style="margin:0 0 6px;font-family:{FONT_DISPLAY};font-size:20px;'
                f'line-height:1.4;font-style:italic;font-weight:600;color:{NAVY};">{_inline_email(str(val))}</p>'
            )
        elif i == sig_idx:
            if tagline_idx is None:
                out.append(_divider())
            out.append(
                f'<p class="sn-muted" style="margin:0;font-family:{FONT_TEXT};font-size:15px;line-height:1.5;'
                f'font-weight:700;color:{NAVY_MUTED};">{_inline_email(str(val))}</p>'
            )
        else:
            text = str(val)
            video = _video_block(text, check_thumb)
            if video:
                out.append(video)
            elif REPLY_RE.search(text):
                out.append(_reply_block(text))
            else:
                out.append(f'<p class="sn-text" style="{_p_style()}">{_inline_email(text)}</p>')
    return "\n".join(out)


def _issue_date_label(day: datetime | None) -> str:
    if not day:
        return ""
    return f"{day.strftime('%A')}, {day.strftime('%B')} {day.day}, {day.year}"


def render_email_content(
    meta: dict,
    body_md: str,
    day: datetime | None = None,
    *,
    legal_in_template: bool = False,
    check_thumb: bool = True,
) -> str:
    """The branded email as one HTML fragment (what goes into Kit's `content`).

    legal_in_template=False: the footer carries the Unsubscribe link itself (works with
    any Kit template). True: the Sniff Test Kit template (kit/sniff-test-template.html)
    supplies the Unsubscribe + mailing-address line right under this footer, so it is
    left out here to avoid two unsubscribe links.
    """
    subject = html.escape((meta.get("subject") or "").strip(), quote=False)
    date_label = html.escape(_issue_date_label(day), quote=False)
    body_html = render_issue_body(body_md, check_thumb=check_thumb)
    muted_link = f"color:{NAVY_MUTED};text-decoration:underline;"
    unsub = (
        ""
        if legal_in_template
        else f' &nbsp;&middot;&nbsp; <a href="{UNSUBSCRIBE_URL}" style="{muted_link}">Unsubscribe</a>'
    )
    eyebrow = (
        f'<p class="sn-muted" style="margin:0 0 8px;font-family:{FONT_TEXT};font-size:12px;line-height:1.4;'
        f'font-weight:800;letter-spacing:1.5px;text-transform:uppercase;color:{KRAFT_INK};">{date_label}</p>'
        if date_label
        else ""
    )
    headline = (
        f'<h1 class="sn-h1 sn-serif" style="margin:0 0 22px;font-family:{FONT_DISPLAY};font-size:32px;'
        f'line-height:1.15;font-weight:700;letter-spacing:-0.5px;color:{NAVY};">{subject}</h1>'
        if subject
        else ""
    )
    return f"""<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" class="sn-bg" bgcolor="{CREAM_DEEP}" style="background:{CREAM_DEEP};width:100%;">
<tr><td align="center" class="sn-outer" style="padding:28px 12px 32px;">
<!--[if mso]><table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" align="center"><tr><td><![endif]-->
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;margin:0 auto;">
<tr><td align="center" bgcolor="{NAVY}" class="sn-pad sn-radius-top" style="background:{NAVY};border-radius:14px 14px 0 0;padding:30px 32px 26px;">
<a href="{SITE_URL}" target="_blank" style="text-decoration:none;"><img src="{LOGO_URL}" width="72" height="72" alt="Dog Unpacked" style="display:block;margin:0 auto 14px;width:72px;height:72px;border-radius:50%;border:2px solid {AMBER};"></a>
<p class="sn-word sn-serif" style="margin:0;font-family:{FONT_DISPLAY};font-size:32px;line-height:1.1;font-weight:700;letter-spacing:-0.5px;color:{CREAM};">{WORDMARK}</p>
<p style="margin:8px 0 0;font-family:{FONT_TEXT};font-size:12px;line-height:1.4;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:{AMBER};">{TAGLINE}</p>
</td></tr>
<tr><td height="4" bgcolor="{AMBER}" style="height:4px;line-height:4px;font-size:0;background:{AMBER};">&nbsp;</td></tr>
<tr><td bgcolor="{CARD}" class="sn-card sn-pad sn-body sn-radius-bottom" style="background:{CARD};border:1px solid {BORDER};border-top:0;border-radius:0 0 14px 14px;padding:38px 44px 40px;font-family:{FONT_TEXT};font-size:17px;line-height:1.6;color:{NAVY};text-align:left;">
{eyebrow}{headline}{body_html}
</td></tr>
<tr><td align="center" class="sn-pad sn-muted" style="padding:26px 32px 4px;font-family:{FONT_TEXT};font-size:13px;line-height:1.6;color:{NAVY_MUTED};">
<p style="margin:0 0 8px;font-family:{FONT_TEXT};font-size:13px;line-height:1.6;color:{NAVY_MUTED};">Educational content only — not veterinary or training advice. {WORDMARK} by Dog Unpacked.</p>
<p style="margin:0;font-family:{FONT_TEXT};font-size:13px;line-height:1.6;color:{NAVY_MUTED};"><a href="{SITE_URL}" target="_blank" style="{muted_link}font-weight:700;">dogunpacked.com</a>{unsub}</p>
</td></tr>
</table>
<!--[if mso]></td></tr></table><![endif]-->
</td></tr>
</table>"""


def render_template_legal_row() -> str:
    """Required Kit template footer (unsubscribe + address), styled to sit under the brand footer."""
    link = f"color:{NAVY_MUTED};text-decoration:underline;"
    return (
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" class="sn-bg" '
        f'bgcolor="{CREAM_DEEP}" style="background:{CREAM_DEEP};width:100%;"><tr>'
        f'<td align="center" class="sn-muted" style="padding:0 24px 36px;font-family:{FONT_TEXT};font-size:12px;'
        f'line-height:1.6;color:{NAVY_MUTED};">'
        f'<a href="{UNSUBSCRIBE_URL}" style="{link}">Unsubscribe</a> &nbsp;&middot;&nbsp; {ADDRESS}'
        "</td></tr></table>"
    )


def render_document(inner_html: str, title: str = WORDMARK, legal_row: bool = False) -> str:
    """Full HTML document (head + responsive/dark-mode CSS) around the content."""
    legal = render_template_legal_row() if legal_row else ""
    return f"""<!DOCTYPE html>
<html lang="en" xmlns="http://www.w3.org/1999/xhtml" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="X-UA-Compatible" content="IE=edge">
<meta name="x-apple-disable-message-reformatting">
<meta name="format-detection" content="telephone=no, date=no, address=no, email=no">
<meta name="color-scheme" content="light dark">
<meta name="supported-color-schemes" content="light dark">
<title>{html.escape(title, quote=False)}</title>
{MSO_HEAD}
<style>{EMAIL_CSS}</style>
</head>
<body class="sn-bg" style="margin:0;padding:0;background:{CREAM_DEEP};">
{inner_html}
{legal}
</body>
</html>
"""


def render_kit_template() -> str:
    """Code for the Kit custom HTML template (Send > Email Templates > New > HTML)."""
    return render_document("{{ message_content }}", legal_row=True)


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


def build_payload(
    meta: dict,
    body_md: str,
    day: datetime | None = None,
    template_id: int | None = None,
    check_thumb: bool = True,
) -> dict:
    subject = (meta.get("subject") or "").strip()
    preview = (meta.get("preview") or "").strip()
    if not subject:
        raise SystemExit("Frontmatter missing required 'subject'.")
    legal_in_template = template_id is not None
    content = render_email_content(
        meta, body_md, day, legal_in_template=legal_in_template, check_thumb=check_thumb
    )
    if not legal_in_template:
        # Kit's default templates don't carry our <head> CSS; ship it with the content so
        # clients that honour body <style> (Apple Mail, iOS) still get mobile + dark mode.
        content = f"<style>{EMAIL_CSS}</style>\n{content}"
    # send_at = now → schedule immediately; omit subscriber_filter → all subscribers.
    send_at = datetime.now(ET).astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%SZ")
    # Omit subscriber_filter → Kit defaults to all subscribers.
    # To target a segment/tag later, add e.g.:
    #   "subscriber_filter": [{"all": [{"type": "segment", "ids": [SEGMENT_ID]}], "any": None, "none": None}]
    payload = {
        "subject": subject,
        "preview_text": preview,
        "description": subject,
        "content": content,
        "public": False,
        "published_at": send_at,
        "send_at": send_at,
    }
    if template_id is not None:
        payload["email_template_id"] = template_id
    return payload


def render_preview(payload: dict) -> str:
    """Local, browser-viewable approximation of the delivered email (Kit Liquid filled with
    stand-ins). With a Sniff Test template id this is exactly template + content."""
    content = payload["content"]
    if "email_template_id" in payload:
        doc = render_kit_template().replace("{{ message_content }}", content)
    else:
        doc = render_document(content, title=payload.get("subject") or WORDMARK)
    return doc.replace(UNSUBSCRIBE_URL, "#unsubscribe").replace(
        ADDRESS, "[mailing address added by Kit]"
    )


def list_templates(api_key: str) -> int:
    """Read-only: print the account's email templates (GET /v4/email_templates)."""
    data = kit_request("GET", "/email_templates", api_key)
    for t in data.get("email_templates") or []:
        default = " (account default)" if t.get("is_default") else ""
        print(f"{t.get('id')}\t{t.get('category')}\t{t.get('name')}{default}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Send The Sniff Test (Dog Unpacked newsletter) via Kit.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and print the Kit payload; do not POST.",
    )
    parser.add_argument(
        "--preview-out",
        metavar="PATH",
        help="With --dry-run: also write a browser-viewable HTML preview of the email to PATH.",
    )
    parser.add_argument(
        "--write-kit-template",
        metavar="PATH",
        help="Write the Kit custom HTML template code (paste into Kit) to PATH and exit.",
    )
    parser.add_argument(
        "--list-templates",
        action="store_true",
        help="Read-only: list Kit email templates (needs KIT_API_KEY) and exit.",
    )
    args = parser.parse_args()

    if args.write_kit_template:
        Path(args.write_kit_template).write_text(render_kit_template(), encoding="utf-8")
        print(f"Wrote Kit template code to {args.write_kit_template}")
        return 0
    if args.list_templates:
        key = os.environ.get("KIT_API_KEY", "").strip()
        if not key:
            raise SystemExit("KIT_API_KEY is not set.")
        return list_templates(key)

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

    template_id = sniff_template_id()
    payload = build_payload(meta, body, day, template_id)

    if args.dry_run:
        if not ready:
            print(
                f"NOTE: frontmatter status is {status or 'missing'!r}, not 'ready' — "
                "a live run would skip this issue."
            )
        print("DRY RUN — payload that would be POSTed to /v4/broadcasts:")
        print(json.dumps(payload, indent=2))
        if template_id is None:
            print(f"NOTE: {TEMPLATE_ENV} not set — Kit's account default template will wrap this content.")
        if args.preview_out:
            out = Path(args.preview_out)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(render_preview(payload), encoding="utf-8")
            print(f"Preview written to {out}")
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
