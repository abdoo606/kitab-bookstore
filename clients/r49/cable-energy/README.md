# Cable Energy — client pack (round 49, #79)

**Contact:** `theo@cable.energy`  ·  **Sent:** 2026-10-22  ·  **Message id:** `1a1639822f207935`  ·  **Subject:** Audit trail for agent-driven billing (tamper drill in 90 seconds)

The one-pager and pricing were emailed. This folder now also holds the working
backend, so the build is not a promise — it is a thing you can run.

## What is built

Agent-billing audit core — 6 capabilities, all covered by tests.

- Append-only metering log: hash chain **plus** HMAC per row, so rewriting the chain is not enough to forge history.
- Idempotent ingestion keyed on (agent_id, event_id) — the double-billing bug every agent platform hits.
- Integer micro-USD pricing, half-up rounding, no floats anywhere in the money path.
- Deterministic invoice replay: same log plus same rate card gives the same invoice id, byte for byte.
- Reconciliation that catches a changed amount, a dropped event, and an invoice edited after it was issued.
- Two tamper drills (`units`, `rehash`) that report detection point and elapsed time.

## Run it

```bash
cd backend
python3 -m unittest test_billing -q    # 36 tests
python3 app.py demo
```

## What is deliberately not built

- No billing provider integration (Stripe/Chargebee webhooks) — the log is the source of truth, export is JSON.
- No multi-tenant database. Files are JSON; a Postgres adapter is a day of work once M1 lands.
- No UI dashboard — the drill output is CLI text.

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
