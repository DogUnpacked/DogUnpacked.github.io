# Dog Unpacked — Newsletter + Kit pipeline

**The Sniff Test** — weekly educational newsletter sent through **Kit** (formerly ConvertKit) via GitHub Actions. One behavior, one job, one study. Every breed, one at a time.

**Do not publish until Josh provides:** Kit form ID (landing signup), `KIT_API_KEY`, and guide PDFs. (CAN-SPAM postal footer: Kit injects its shared address — see Compliance.)

## Cadence

| | |
|--|--|
| Day | Sunday |
| Cron | `0 13 * * 0` (13:00 UTC) |
| Local (ET) | ~9:00 AM Eastern in summer (EDT); ~8:00 AM Eastern in winter (EST) |

Cadence: **weekly, Sunday** (replaces the earlier Tue + Thu schedule).

GitHub cron is **UTC-only**. When the US observes daylight saving, the Eastern wall-clock time of the send shifts by one hour. If you need a fixed 9 AM ET year-round, adjust the cron when DST starts/ends, or accept the one-hour drift.

**Daily cadence remains parked** (not scheduled). Do not enable a daily cron unless Josh explicitly asks.

Manual runs: **Actions → Send The Sniff Test → Run workflow**. `dry_run` defaults to **true** so a manual click cannot accidentally blast.

## How to add an issue

1. Copy `newsletters/_template.md` to `newsletters/YYYY-MM-DD.md`.
2. Use the **America/New_York calendar date** of the Sunday you want it to send (not UTC date).
3. Fill `subject`, `preview`, and the Markdown body.
4. Leave `send: true`.
5. Commit to `main` before that day’s 13:00 UTC send.

Example:

```bash
cp newsletters/_template.md newsletters/2026-10-11.md
# edit subject / preview / body
git add newsletters/2026-10-11.md && git commit -m "Newsletter 2026-10-11" && git push
```

## How to skip a send day

- **No file** for that Sunday’s ET date → `scripts/send.py` exits 0 (no-op).
- Or keep the file and set frontmatter `send: false` → exits 0 without posting.

## Local dry-run

```bash
# Pretend today is the issue date, or temporarily rename a file to today's ET date:
python3 scripts/send.py --dry-run
```

Dry-run never calls Kit and does not need `KIT_API_KEY`.

## Kit API key (secret)

1. In Kit: Settings → Developer → create a **V4 API key**.
2. In the GitHub repo: **Settings → Secrets and variables → Actions → New repository secret**.
3. Name: `KIT_API_KEY`. Value: the key. Never commit the key.
4. **Rotate** by creating a new key in Kit, updating the GitHub secret, then revoking the old key in Kit.

The landing-page signup form ID is separate from this API key. The landing page posts to Kit form `10011711` (email + `fields[breed]`) — see `KIT.md` and the HTML comment in `index.html`.

## Duplicate-send caveat

Kit `POST /v4/broadcasts` has **no idempotency key**. Re-running the live workflow on the same day (or a cron retry after a partial success) can create a **second** broadcast with the same subject.

`scripts/send.py` does a **best-effort** `GET /v4/broadcasts?slim=true` and skips if a broadcast subject already matches exactly. That is not a guarantee (pagination, renamed subjects, races). Prefer:

- One scheduled run per send day (Sunday)
- Manual dispatch with `dry_run: true` unless you intend a live send
- Avoid re-running live after a successful create

## Disclaimer footer

Every send appends an educational disclaimer and Kit’s `{{ unsubscribe_url }}` via `scripts/send.py` (`DISCLAIMER_HTML`). Do **not** put a personal mailing address in the send script or anywhere in this repo.

## Compliance

- **CAN-SPAM postal footer:** Kit injects the footer address (Kit’s shared CAN-SPAM address). Do not hardcode Josh’s personal address anywhere (landing page, newsletters, or `send.py`).
- If the brand ever needs to **receive** mail, replace Kit’s shared address in Kit’s account/settings with a PO box or virtual mailbox (e.g. `600 1st Ave, Ste 330 PMB 92768, Seattle, WA 98104-2246`). That is the only postal address allowed if one must be hardcoded; otherwise leave footer injection to Kit.
- Landing `index.html` must not include a postal address.

## Files

| Path | Role |
|------|------|
| `newsletters/_template.md` | Frontmatter + body scaffold |
| `newsletters/YYYY-MM-DD.md` | One issue per send day |
| `scripts/send.py` | ET date lookup → Kit POST |
| `.github/workflows/send-newsletter.yml` | Cron + workflow_dispatch |
| `assets/` | Guide PDFs (e.g. `german-shepherd-file.pdf` when ready) |
