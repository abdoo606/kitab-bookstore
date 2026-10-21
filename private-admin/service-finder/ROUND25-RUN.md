# Round 25 run — 2026-10-21 (follow-up + new hunt + ShieldScan v17 + TradeAtlas v6 + RentLedger)

## Gmail
- Rechecked (incl. spam/trash) for all three outreach targets: only our own 4
  sent messages — **0 replies, 0 acceptances, 0 payments**. Canadian Club of
  Ottawa deadline was **Oct 21, 2026 (today)**; standing: Memory Studies
  Association Nov 1, 2026 · Iditarod Nov 2, 2026 17:00 AKST.

## New worldwide non-Arab service hunt (angles: NZ councils/sport, AU community
health, CA small libraries & municipalities)
**Result: 0 qualified, 0 emailed.** Originals fetched/verified:
- **South Shore Public Libraries (Nova Scotia, CA)** website RFP with genuine
  email submission (`info@ssplibraries.ca`) — deadline passed **Jun 4, 2026**.
- **City of Vernon (BC, CA)** RFP 26-55-COM corporate website redesign —
  Bonfire portal-only; the listing itself is already removed.
- **Christchurch City Council (NZ)** — the NZ angle runs entirely through the
  GETS portal + a RealMe government-identity account; no public-email route
  exists to answer (structural screen).
- **Grampians Community Health (AU)** website redesign tender — closed
  **Feb 2020**.
- Evidence: `round25/excerpts.txt`, `round25/sources.json`, snapshot
  `results/round24/`→`results/round25/` (4 records; regex triage status
  `conflicting_deadlines_review`, human verdicts above govern).

## ShieldScan MAX 17.0 (live, port 8808) — the report becomes appointments
- **Dated remediation calendar from one link**: findings are ETA-estimated
  (parsed from the audit's own effort labels) and scheduled onto weekdays at
  4 focused hours/day in severity order → `remediation_calendar` JSON, an
  importable **`fix-calendar.ics`** in the audit bundle, and an illustrated
  **Gantt chart** in the HTML report. Weak demo: 92 tasks, ~143h, 41
  workdays (triage-grade estimates, labeled).
- **5 new passive checks** (patch library **144 codes**): weak DKIM key size
  (estimated from the public record), forms submitting to third-party
  domains, DOM HTML-sink inventory, `document.write`, eval-style execution.
- **4 new status-only probes (42 total)**: `.env.local`, Symfony `_profiler`,
  Go `debug/pprof`, ASP.NET `trace.axd`.
- Tests **60/60**. Samples: weak **F 0/100, 115 findings**; good **A+ 96/100,
  12 findings**. (Build note: a mid-round parallel-edit race corrupted EOF
  and dropped several edits; detected via anchor greps, truncated, and every
  piece re-applied strictly sequentially — final file compiles and all 60
  tests pass against the complete feature set.)

## TradeAtlas v6.0 (live, port 8820) — ensembles raced, costs applied, history documented
- **Ensemble evaluation** (same 100 hidden-future attempts, real AAPL):
  analog median **44.0%** → distance-weighted **48.0%** → majority vote
  **55.0%** → agreement-only **56.0% @ 50% coverage**; momentum still leads
  at **58.0%**.
- **Cost-aware re-scoring** ends the story: majority vote nets **≈0.00%/trade
  at 10 bps, −0.15% at 25 bps**; momentum melts +0.17% → +0.02%/trade.
  Direction accuracy without expectancy-after-costs is half the truth, and
  the lab now prints both halves.
- **Version-evolution table** added to the README (v4 44.0% → v5 no edge at
  any horizon/regime + MSFT 45.0% → v6 ensemble gains erased by costs),
  documenting attempt-by-attempt progress of *measurement strength*, not of
  manufactured accuracy. Tests **22/22**; live spec/forecast verified.

## RentLedger — Genius Idea #19 (live, port 8825)
Small-landlord rent & deposit ledger: generated monthly charges (duplicate-
proof), idempotent `pay_ref` payments with FIFO allocation, once-per-charge
late fees as written policy, itemized move-out deposit settlement with
refund deadline, arrears-aging report, jurisdiction cautions printed on the
statement. Demo balance 1700.00 (double-submitted August payment counted
once). Tests **7/7**.

## Publication
- Live portfolio: **18 previews, ports 8808–8825**.
- GitHub: `arena/78ba5633-kitab-bookstore` (this round's commit).
- service-finder tests: 30/30 OK.
