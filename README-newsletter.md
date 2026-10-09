# Dog Unpacked — Newsletter + Kit pipeline

**The Sniff Test** — weekly educational newsletter sent through **Kit** (formerly ConvertKit) via GitHub Actions. One behavior, one job, one study. Every breed, one at a time.

**Do not publish until Josh provides:** Kit form ID (landing signup), `KIT_API_KEY`, and guide PDFs. (CAN-SPAM postal footer: Kit injects its shared address — see Compliance.)

## Cadence

| | |
|--|--|
| Day | Sunday |
| Send time | **6:00 AM Eastern (America/New_York), year-round** |
| Cron | `0 10 * * 0` (10:00 UTC = 6:00 AM EDT) **and** `0 11 * * 0` (11:00 UTC = 6:00 AM EST) |

Cadence: **weekly, Sunday** (replaces the earlier Tue + Thu schedule).

GitHub cron is **UTC-only**, so the workflow schedules both Sunday triggers and a **DST guard** step lets exactly one of them
send. It keys off which cron fired (`github.event.schedule`): the 10:00 UTC run proceeds only while New York is on
daylight time (UTC-4, EDT); the 11:00 UTC run proceeds only while it is on standard time (UTC-5, EST). The other run logs
a skip and exits 0 without checking out or calling Kit. Because the decision depends on the trigger rather than the
wall-clock hour, a late cron start (GitHub can delay scheduled runs by minutes to ~an hour) still sends. US clock changes
happen at 2:00 AM local (before 10:00 UTC), so the DST-switch Sundays (e.g. Nov 1, 2026) work too. No manual cron edits
are needed when DST starts or ends.

**Daily cadence remains parked** (not scheduled). Do not enable a daily cron unless Josh explicitly asks.

The Sunday cron only posts to Kit when `newsletters/<that Sunday's ET date>.md` exists **and** its frontmatter
says `status: ready` (and not `send: false`). Otherwise it logs a skip and exits 0. `_template.md` never matches a date.

Manual runs: **Actions → Send The Sniff Test → Run workflow**. `dry_run` defaults to **true** so a manual click cannot accidentally blast.

## How to add an issue

1. Copy `newsletters/_template.md` to `newsletters/YYYY-MM-DD.md`.
2. Use the **America/New_York calendar date** of the Sunday you want it to send (not UTC date).
3. Fill `subject`, `preview`, and the Markdown body.
4. When the issue is approved, change `status: draft` to `status: ready`. **Nothing is sent without `status: ready`**
   (opt-in: a missing status, `draft`, or anything else is skipped). Leave `send: true`.
5. Commit to `main` before that day’s 6:00 AM ET send (10:00 UTC in EDT / 11:00 UTC in EST).

Example:

```bash
cp newsletters/_template.md newsletters/2026-10-11.md
# edit subject / preview / body, then set status: ready once approved
git add newsletters/2026-10-11.md && git commit -m "Newsletter 2026-10-11" && git push
```

## How to skip a send day

- **No file** for that Sunday’s ET date → `scripts/send.py` exits 0 (no-op).
- File present but frontmatter `status` is not `ready` (e.g. `draft`, or missing) → exits 0 without posting.
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

- One scheduled send per Sunday (the DST guard skips the other trigger; a `concurrency` group prevents overlapping runs)
- Manual dispatch with `dry_run: true` unless you intend a live send
- Avoid re-running live after a successful create

## Email design (branded wrapper)

`scripts/send.py` wraps every issue in the branded **The Sniff Test** email (no change to how issues are written):
navy header with the Dog Unpacked logo (`https://dogunpacked.com/images/logo-256.png`), the wordmark and
"Every breed, one at a time"; amber rule; cream card with the issue date, subject as headline and 17px / 1.6 body;
links underlined in amber; a paragraph with a YouTube link becomes a video card (i.ytimg.com thumbnail + navy
"Watch on YouTube" button); a "Hit reply" paragraph gets a subtle amber-accent box; the last line starting with "—"
is the signature and the short line before it the italic tagline; footer with the disclaimer, dogunpacked.com and
unsubscribe. Table layout, inline CSS, 600px max, Georgia / Helvetica-Arial fallbacks (Fraunces / Nunito load from
dogunpacked.com where clients allow web fonts), Outlook ghost table, mobile and dark-mode CSS. Colors are the site
tokens from `styles.css`.

Preview any issue locally: `python3 scripts/send.py --dry-run --preview-out /tmp/issue.html` (on the issue's ET date,
or monkeypatch `send.today_et`).

### Kit template (avoid double wrapping)

Kit always wraps broadcast `content` in an email template, and every Kit template must contain its own unsubscribe
link and mailing address. With the account default (Classic/Modern/Text Only) you get Kit's styling and a second
footer ("Unsubscribe | Update your profile | address") under ours. To avoid that, one-time setup in Kit (custom HTML
templates; reported available on the Free plan):

1. Kit → **Send → Email Templates → New Email Template → HTML** (or "Import code / Create HTML template").
2. Name it **The Sniff Test**, paste the full contents of `kit/sniff-test-template.html`, save. (Kit should show
   it as valid: it has `{{ message_content }}`, `{{ unsubscribe_url }}` and `{{ address }}`.) Don't make it the
   account default unless you want it for other emails too.
3. Get its id: run the workflow manually with **list_templates = true** (read-only), or open the template in Kit
   and copy the number from the URL.
4. GitHub → **Settings → Secrets and variables → Actions → Variables → New repository variable**:
   `KIT_SNIFF_TEMPLATE_ID` = that id.

When the variable is set, `send.py` sends `email_template_id` and leaves the unsubscribe link to the template (one
line under the brand footer: "Unsubscribe · mailing address"). When it is unset, the content's own footer carries
the unsubscribe link and Kit's default template adds its footer too. Regenerate the template file after design
changes with `python3 scripts/send.py --write-kit-template kit/sniff-test-template.html` and re-paste it in Kit.

## Disclaimer footer

Every send includes the educational disclaimer and an unsubscribe link (`{{ unsubscribe_url }}`, in the content
footer or in the Sniff Test Kit template). The mailing address comes from Kit's `{{ address }}`. Do **not** put a
personal mailing address in the send script or anywhere in this repo.

## Compliance

- **CAN-SPAM postal footer:** Kit injects the footer address (Kit’s shared CAN-SPAM address). Do not hardcode Josh’s personal address anywhere (landing page, newsletters, or `send.py`).
- If the brand ever needs to **receive** mail, replace Kit’s shared address in Kit’s account/settings with a PO box or virtual mailbox (e.g. `600 1st Ave, Ste 330 PMB 92768, Seattle, WA 98104-2246`). That is the only postal address allowed if one must be hardcoded; otherwise leave footer injection to Kit.
- Landing `index.html` must not include a postal address.

## Files

| Path | Role |
|------|------|
| `newsletters/_template.md` | Frontmatter + body scaffold |
| `newsletters/YYYY-MM-DD.md` | One issue per send day |
| `scripts/send.py` | ET date lookup → branded HTML → Kit POST |
| `kit/sniff-test-template.html` | Kit custom HTML template code (generated by `send.py --write-kit-template`) |
| `.github/workflows/send-newsletter.yml` | Two Sunday crons + DST guard (6:00 AM ET) + workflow_dispatch |
| `assets/` | Guide PDFs (e.g. `german-shepherd-file.pdf` when ready) |
