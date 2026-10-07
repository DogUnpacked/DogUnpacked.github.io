# Kit (ConvertKit) — landing signup ("The Sunday Breed File")

Public IDs for the Dog Unpacked hub page. **No API keys or secrets** belong in this file.
Account plan: **Free** (verified via API `GET /v4/account`, `plan_type: free`). Custom fields and tags are
included on Free. Keep it that way: no paid features.

| Field | Value |
| --- | --- |
| Form ID | `10011711` |
| data-uid | `ae44e15ea4` |
| Subscribe action | `https://app.kit.com/forms/10011711/subscriptions` |
| Email field | `email_address` |
| Breed field | `fields[breed]` → custom field **breed** (key `breed`, id `1388795`, HTML name `ck_field_1388795_breed`) |
| Source tag | `source:landing` (id `24362096`); page also posts `tags[]=24362096` as a backup |
| JS embed (not used) | `https://dog-unpacked.kit.com/ae44e15ea4/index.js` |
| Double opt-in / incentive email | ON (keep on) |

The page uses a **brand-styled HTML form** (Navy/Cream) that POSTs to the action above, not Kit's
default embed chrome. `script.js` Title-Cases the breed (`german shepherd` → `German Shepherd`,
`gsd` → `German Shepherd`) before posting.

## Created via API (2026-10-07)

- Custom field `breed` (id 1388795). Free and reversible (`DELETE /v4/custom_fields/1388795`).
- Tag `source:landing` (id 24362096). Free and reversible.

## Still to do in the Kit dashboard (the V4 API can't change these)

1. **Form name**: rename "German Shepherd File (landing)" to **The Breed File (landing)**
   (Grow → Landing Pages & Forms → form 10011711 → title).
2. **Form fields**: in the form builder, add a custom field mapped to **breed** (required) so Kit's own
   embed, preview and reports show it. The brand page already posts `fields[breed]`.
3. **Auto-tag**: form settings → Incentive / "Add tag" → **source:landing**, so every subscriber
   through this form is tagged even if Kit ignores the hidden `tags[]` input.
4. **Incentive email** (double opt-in, keep ON): rewrite the subject/body for The Sunday Breed File
   and the "free one-page timeline for your breed". Remove any "working and power breeds" wording.
   Point the incentive at the German Shepherd timeline for now.
5. **Sender name**: Settings → Email → sending address `from_name` is currently the bare email address.
   Change to **Dog Unpacked — The Breed File**.
6. **Descriptions**: wherever Kit shows a form, profile or sender description (form heading/subheading,
   Creator Profile byline/bio, currently empty), use "every breed, one at a time". Remove any
   "working and power breeds" wording.
7. **Success message / redirect** (optional): set the form's success message, for example
   "Check your inbox to confirm. Your breed's File follows."

Do not invent form IDs. Do not commit `KIT_API_KEY` (it belongs only in GitHub Actions secrets for the
newsletter send pipeline, and locally in the gitignored `.kit-api-key.local`).
