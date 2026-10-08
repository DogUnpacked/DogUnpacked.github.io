# Kit (ConvertKit) — landing signup ("The Sniff Test" newsletter)

Public IDs for the Dog Unpacked hub page. **No API keys or secrets** belong in this file.
Account plan: **Free** (verified via API `GET /v4/account`, `plan_type: free`). Custom fields and tags are
included on Free. Keep it that way: no paid features.

| Field | Value |
| --- | --- |
| Form ID | `10011711` |
| data-uid | `ae44e15ea4` |
| Subscribe action | `https://app.kit.com/forms/10011711/subscriptions` |
| Email field | `email_address` |
| Breed field (optional) | `fields[breed]` → custom field **breed** (key `breed`, id `1388795`, HTML name `ck_field_1388795_breed`). Saved on the subscriber only; it does not change the signup. Omitted from the post when blank. |
| Source tag | `source:landing` (id `24362096`); page also posts `tags[]=24362096` as a backup |
| JS embed (not used) | `https://dog-unpacked.kit.com/ae44e15ea4/index.js` |
| Double opt-in / incentive email | ON (keep on) |

The page uses a **brand-styled HTML form** (Navy/Cream) that posts to the action above, not Kit's
default embed chrome. With JS, `script.js` sends the post in the background exactly like Kit's own embed script
(`fetch` POST of the form data, headers `Accept: application/json` and `X-CKJS-Version: 6`; Kit answers CORS with
`access-control-allow-origin: *` and returns `{"status":"success"}`), then shows "Check your inbox — one click to
confirm and you're in." on the page, with a smaller line under it: "Not there in a few minutes? Check your spam
or junk folder." Any failure falls back to a normal POST (Kit's hosted success message).
Form setting checked via the public form config: reCAPTCHA is **off**, so the background post isn't challenged. It is a plain newsletter signup: email required, breed optional. Everyone gets the
same Sunday issue of The Sniff Test. `script.js` Title-Cases the breed (`german shepherd` → `German Shepherd`,
`gsd` → `German Shepherd`) before posting.

## Created via API (2026-10-07)

- Custom field `breed` (id 1388795). Free and reversible (`DELETE /v4/custom_fields/1388795`).
- Tag `source:landing` (id 24362096). Free and reversible.

## Still to do in the Kit dashboard (the V4 API can't change these)

1. **Form name**: rename "German Shepherd File (landing)" to **The Sniff Test (landing)**.
2. **Breed field on the form**: in the form builder, add a custom field mapped to **breed** and leave
   **Required unchecked** (optional). Label it "Your dog's breed (optional)". The brand page already posts it.
3. **Auto-tag**: form settings → add tag **source:landing**, so every subscriber through this form is tagged
   even if Kit ignores the hidden `tags[]` input.
4. **Confirmation / incentive email** (double opt-in, keep ON): make it a plain newsletter confirmation for
   The Sniff Test, e.g. subject "Confirm your subscription to The Sniff Test", body "Click below to
   confirm. Then look for The Sniff Test in your inbox on Sunday." **No guide / PDF / timeline
   promise**, no incentive download. Remove any "working and power breeds" wording.
   After confirming, redirect to **https://dogunpacked.com/?confirmed=1** (not the YouTube subscribe
   prompt). The page then shows "You're in." in the newsletter section (see `README-page.md`).
5. **Sender name**: Settings → Email → the sending address `from_name` is currently the bare email address.
   Change to **Dog Unpacked — The Sniff Test**.
6. **Descriptions**: form heading/subheading and Creator Profile byline/bio (currently empty): use
   "every breed, one at a time". Remove any "working and power breeds" wording.
7. **Success message (needed)**: the form's "after subscribe" message currently reads "Check your inbox to
   confirm — we'll send the File when it's ready." That promises a File, which the newsletter signup doesn't.
   It shows when JS is off or the background submit falls back to a normal POST. Change it to match the page:
   **"Check your inbox — one click to confirm and you're in."** (Keep "after subscribe" = show message, no redirect.)

Do not invent form IDs. Do not commit `KIT_API_KEY` (it belongs only in GitHub Actions secrets for the
newsletter send pipeline, and locally in the gitignored `.kit-api-key.local`).
