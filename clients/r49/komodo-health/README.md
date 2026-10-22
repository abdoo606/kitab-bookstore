# Komodo Health — client pack (round 49, #81)

**Contact:** `ramraj.velmurugan@komodohealth.com`  ·  **Sent:** 2026-10-22  ·  **Message id:** `1a163985357dece0`  ·  **Subject:** EU AI Act: Annex IV pack for the AI analyst

The one-pager and pricing were emailed. This folder now also holds the working
backend, so the build is not a promise — it is a thing you can run.

## What is built

Annex IV technical-documentation generator — 5 capabilities, all covered by tests.

- AI Act risk classifier returning prohibited / high-risk / limited / minimal, with the article or Annex III clause cited for every reason.
- Nine-section Annex IV pack with per-section completeness and an explicit gap list.
- Mandatory-field validation plus structural checks (fully automatic with no oversight, decisions about persons with no affected groups).
- SHA-256 evidence manifest with verification — detects an edited or deleted evidence file after the pack was signed.
- Deterministic pack id; Markdown for humans, JSON for a repository.

## Run it

```bash
cd backend
python3 -m unittest test_annex -q       # 36 tests
python3 app.py demo
```

## What is deliberately not built

- Not legal advice. The classifier encodes the regulation's triggers, not a lawyer's judgement.
- No EU declaration of conformity is generated — section 8 requires the signed document as evidence.
- No connection to Komodo's internal model registry; input is a JSON system description.

## Files

| path | what |
|---|---|
| `backend/` | source, tests, CLI — **private, git-ignored, never emailed before M1** |
| `PRICING.md` | the exact numbers that were sent, no rounding |
| `README.md` | this file |

## Handover rule

`backend/` stays private until M1 is received. After that it is zipped, the
README inside it is regenerated with the customer's name, and the archive is
sent over. Until then, a demo can be run live on a call — that is the whole
point of having it here.
