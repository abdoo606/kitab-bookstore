# Enveritas — client pack (round 49, #78)

**Contact:** `jeff@enveritas.org`  ·  **Sent:** 2026-10-22  ·  **Message id:** `1a163980dab27cc0`  ·  **Subject:** Verifiable proof-of-work for the cocoa supply chain

The one-pager and pricing were emailed. This folder now also holds the working
backend, so the build is not a promise — it is a thing you can run.

## What is built

EUDR plot-risk + evidence backend — 5 capabilities, all covered by tests.

- Polygon validation, spherical-exact area, self-intersection and point-in-polygon (pure Python, no GeoPandas).
- EUDR-style risk score with five attributable triggers (deforestation window, protected area, geolocation quality, declared-vs-measured area, country baseline).
- Pluggable forest-loss provider (`ForestIndex`) — swap the fixture for a satellite API without touching the scoring code.
- Hash-chained assessment ledger with tamper detection at row level.
- Merkle dossier: a buyer verifies a single plot offline, without downloading the shipment and without trusting our server.

## Run it

```bash
cd backend
python3 -m unittest test_eudr -q      # 34 tests
python3 app.py demo
```

## What is deliberately not built

- No satellite provider is bundled. `ForestIndex` is a fixture; production needs a contract with a forest-monitoring API (Global Forest Watch, or the customer's own layer).
- No shapefile/GeoJSON importer yet — input is a JSON list of rings.
- No UI. This is the engine the one-pager promised, not the studio.

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
