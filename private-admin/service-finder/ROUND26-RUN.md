# Round 26 run — 2026-10-21 (follow-up + new hunt + ShieldScan v18 + TradeAtlas v7 + ToolLibrary)

## Gmail
- Rechecked, including spam/trash: only the four previously sent messages to
  the three earlier outreach targets — **0 replies, 0 acceptances, 0 payments**.
- Standing deadlines remain **Memory Studies Association: Nov 1, 2026** and
  **Iditarod: Nov 2, 2026 17:00 AKST**. Canadian Club of Ottawa's deadline was
  Oct 21, 2026; no reply had arrived at this check.

## New worldwide non-Arab service hunt (angles: South Africa/Kenya + global originals)
**Result: 0 qualified, 0 emailed.** Originals were fetched and screened under
the standing rules (public submission email + honestly meetable gates + live
deadline + scope that can be built first):

- **SACNASP (South Africa)** unified digital-system RFP to
  `scm@sacnasp.org.za` — closed **Mar 20, 2026**; scope is an enterprise
  statutory platform, not a small website service.
- **Iziko Museums (South Africa)** — Central Supplier Database public
  procurement; displayed items closed Sep 25/30, 2026 and none is a website
  service.
- **Rights and Resources Initiative** website redesign — expired **May 29,
  2026** and requires 10 years' experience, client testimonials, CVs and
  insurance/certifications/licenses.
- **Critical Ecosystem Partnership Fund (CEPF)** website redesign — due
  **Oct 24, 2016** and scored on comparable firm projects/reputation.
- Kenya-specific searching produced expired reposts, vendor marketing or
  procurement portals rather than a live original with public-email
  submission. Nawiri was not re-hunted because it was screened in an earlier
  round.
- Evidence: `round26/excerpts.txt`, `round26/sources.json`; snapshot in
  `results/round26/` (4 records, 0 errors; all machine-triaged `expired`;
  human verdicts above govern). service-finder tests **30/30**.

## ShieldScan MAX 18.0 (live, port 8808) — from audit to drift alarm
- **Security Drift Watch:** every one-link audit now mints a stable SHA-256
  security fingerprint spanning score/finding codes, security-header
  presence, cookie names/flags (never cookie values), TLS identity and the
  public attack surface. Scan time, response milliseconds and the daily
  certificate-days countdown are excluded from the hash. Reusing
  `security-fingerprint.json` or `report.json` as a baseline classifies later
  change as regressions / improvements / neutral changes and yields a
  stability score, response actions and priority patch steps.
- Drift coverage goes beyond changed finding titles: lost headers, new
  sensitive-path probe hits, new third-party/form destinations, cookie-flag
  loss, TLS downgrade/near-expiry, score drops and surface growth. It is in
  the illustrated report (new SVG), one-page summary, Markdown, audit bundle
  (`security-fingerprint.json` + `drift-watch.json`), UI downloads, CLI
  (`--fingerprint-out`, `--drift-out`) and the generated CI workflow (which
  automatically uses a committed `tools/shieldscan-baseline.json`).
- **6 new passive checks** (patch library **150 codes**): duplicate security
  headers, CDN/cache debug headers, JWT `alg=none`, JWT lifetime over 90 days
  (token/claims never printed), third-party import-map hosts, and Speculation
  Rules prefetch/prerender surface.
- **4 new status-only probes (46 total):** `.git/index`, `WEB-INF/web.xml`,
  `.aws/config`, `backup.sql.gz` — status only, sensitive bodies never read.
- Tests **64/64**. Regenerated samples: weak **F 0/100, 119 findings** (12
  critical, 11 high, 15 medium, 57 low, 24 info); good **A+ 96/100, 12
  findings**. Weak-demo calendar: 95 tasks, 144.8 hours, 41 workdays. The
  weak→good demo re-audit drift report shows **87 improvements, 0
  regressions**. All new same-file edits were applied strictly sequentially
  with compile/test verification.

## TradeAtlas v7.0 (live, port 8820) — candle anatomy enters the blind race
- New candle-structure feature family: gap, range, signed body/3-bar body,
  close location, wick balance, range expansion and volume surprise. The 30
  nearest candle neighbours vote by median and distance weight under the same
  no-lookahead rule and 10/25 bps cost scoring; `majority_vote_v2` adds the
  candle vote to the v6 ensemble. The v4 return-analog method and its pinned
  result were not changed.
- Bundled **real AAPL daily**, 100 hidden-future attempts, horizon 5:
  return-analog median **44.0%**, candle median **50.0%**, candle weighted
  **49.0%**, majority v2 **57.0%**, naive momentum **58.0%**, always-up
  **56.0%**. Standalone candle-weighted calls lose after costs (**−0.157%/
  trade at 10 bps; −0.307% at 25 bps**). Majority v2 nets **+0.158%/trade at
  10 bps**—the same as always-long's +0.157% on this rising sample—and only
  **+0.008% at 25 bps**. Verdict remains: **no demonstrated tradable edge**.
- Close-only MSFT monthly data now reports candle methods as unavailable
  (`null`, 0 attempts) instead of fabricating candle anatomy; close-based
  methods continue unchanged (analog 45.0%, momentum 55.0%).
- README version-evolution table now carries the v7 row. Tests **25/25**,
  including a future-mutation no-lookahead test and pinned real-AAPL v7
  numbers. Samples regenerated from the v7 code.

## ToolLibrary — Genius Idea #20 (live, port 8826)
Community tool-lending desk for libraries of things and equipment sheds:
member tiers/limits, tool inventory with replacement values and deposits,
staff checkout with external deposit-hold references, one on-time renewal,
condition check-in, explicit late/damage fee policy, deposit-applied versus
deposit-released arithmetic, a maintenance queue for damaged/unsafe returns,
lost-tool replacement charges, idempotent fee payments, and overdue /
deposit / maintenance reporting. Deposit holds are records only; the app is
not a payment processor and rejects card-shaped numbers.

Deterministic demo at 2026-10-21: drill late fee **4.00** (2 billable days
after grace); damaged tile saw has **35.00** of a 60.00 deposit applied and
**25.00 released**, and sits in maintenance; 3 active loans, 1 overdue,
**215.00** active deposit holds, inventory replacement value **1,430.00**.
Tests **8/8** (including a repeated FIFO check after fixing fee ordering to
use an internal sequence rather than randomized fee IDs).

## Publication
- Live portfolio: **19 previews, ports 8808–8826**, all verified HTTP 200.
- GitHub: branch `arena/78ba5633-kitab-bookstore`; this round's commit also
  lands the small Round 25 snapshot-path correction that raced the Round 25
  commit.
- Product packages for Drive: `shieldscan-v18.zip`, `tradeatlas-v7.zip`,
  `toollibrary-v1.zip`, `service-finder-round26.zip`, plus this run file and
  `round26-opportunities.csv`.
- Outreach total remains: **3 targets contacted in earlier rounds, 0 replies,
  0 acceptances, 0 payments**.
