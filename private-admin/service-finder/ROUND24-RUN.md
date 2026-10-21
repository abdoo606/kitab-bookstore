# Round 24 run — 2026-10-21 (follow-up + new hunt + ShieldScan v16 + TradeAtlas v5 + ClassTrack)

## Gmail
- Rechecked at the start of this round (full + archived + spam/trash searches
  for all three outreach targets): only our own 4 sent messages; **0 replies,
  0 acceptances, 0 payments.** Deadlines standing: **Canadian Club of Ottawa —
  Oct 21, 2026 (today)**; Memory Studies Association — Nov 1, 2026; Iditarod —
  Nov 2, 2026 17:00 AKST.

## Round 23 closeout completed at this round's start
- Drive: `tradeatlas-v4.zip` → file `1uNCkcIWt29JOm5Wl0rwuoT5xc8rIiL-V`;
  new folder `17-GiftCardDesk` (`12qxU7eFo_kCH_G0gDXGUiCCGHGUz9Q1z`) with zip
  `1w2l-KWYVSUUyE_BYIfK-kuKtguFVfB06` + README `1x3T5xWVzU4KvjBuEByrV132B0aSPmSd3`;
  root files `service-finder-round23.zip` `18PfI_wjbJw7VRseb7LTahCOw4nMzmBqM`,
  `ROUND23-RUN.md` `11I6Stq2Mjr3eMH0Tj8zRxC5ItpLaKVxp`,
  `round23-opportunities.csv` `17QcpLmb6tQPktbI3_PXNDVXrSxKiJqzp`;
  progress comment `doco.WNjp4rUZFxzUx1xRmPkOkw`.

## New worldwide non-Arab service hunt (angles: UK conservation/heritage & church
bodies, independent schools/charter networks, sports federations)
**Result: 0 qualified, 0 emailed.** Originals fetched/verified:
- **IPDA (UK)** website review & redesign tender — individuals welcomed, but
  the closing date on the original page is **28 April 2017** (zombie page).
- **Westminster Foundation for Democracy (UK)** website services tender with
  email submission — a **2025** proceeding; the original page is gone (403).
- **Friendship Public Charter School (Washington DC)** website design RFP,
  public email — deadline passed **Jul 31, 2026**.
- **SFUSD RFP SFUSD-PD-FY26#81** website redesign, email submission — deadline
  passed **Apr 24, 2026**; formal public-district procurement.
- Also seen, not excerpted: Warwickshire Wildlife Trust (2023, in-person);
  Achievement First re-issued RFP (organisation already screened out in an
  earlier round — not re-hunted per standing rules); Government of Meghalaya
  sports-site tender (₹45 lakh completed-project pre-qualification).
- Evidence + verdicts: `round24/excerpts.txt`, `round24/sources.json`,
  snapshot `results/round24/` (4 records, all `expired`).

## ShieldScan MAX 16.0 (live, port 8808) — one link audits the neighbourhood
- **Automatic sibling-host expansion**: on HTTPS targets, hostnames from the
  TLS certificate under the same registrable domain (max 5) get a bounded
  passive header/cookie mini-audit (one HTTPS GET each); findings merge into
  the report labeled by host, with a surface row in the illustrated report.
- **7 new passive checks** (patch library **139 codes**): CSP via `<meta>`,
  session-replay tools (Hotjar/FullStory/Clarity/LogRocket/Smartlook),
  browser-fingerprinting library, unpinned CDN scripts (`@latest`),
  plain-HTTP `rel=canonical`, X-Frame-Options vs `frame-ancestors` conflict,
  DNS TXT third-party verification inventory (provider names only).
- **4 new status-only probes (38 total)**: `.env.production`,
  `actuator/heapdump`, `elmah.axd`, Laravel `telescope` (`probe_debug` also
  added to the default CI policy deny list).
- Tests **56/56**. Samples: weak **F 0/100, 110 findings** (12 critical,
  11 high, 15 medium, 51 low, 21 info); good **A+ 96/100, 12 findings**.

## TradeAtlas v5.0 (live, port 8820) — the forecast test gets harder to fool
- **Multi-horizon evaluation** (1/3/5/10/20 bars): real AAPL analog accuracy
  **41/44/44/47/36%** — no edge at any horizon.
- **Regime split** (price vs causal SMA-20; 10-bar vol vs trailing-100
  median), scored vs always-up in the same bucket: AAPL analog loses all four
  buckets (above-SMA20 **44.3% vs 65.6%**).
- **Analog path simulation**: seeded bootstrap over the *real* forward paths
  of look-alike setups → terminal + max-drawdown percentiles (AAPL latest
  setup, 20 bars: p5 −15.1%, median +0.4%, p95 +7.7%; median worst dip 5.7%,
  p95 16.5%). Historical dispersion, never a promise.
- **Second real sample**: MSFT monthly 2000–2010 via new `min_history` →
  analog **45.0%** vs always-up 47.5% / momentum 55.0% → same no-edge
  verdict; its 60% at 6 months is exposed by neighbouring horizons.
- Feature vectors precomputed once per evaluation (v4 recomputed per
  origin); a test pins AAPL at 44.0% so the cache provably changes nothing.
- Tests **20/20**; spec + forecast endpoint live-verified (44.0%, no-edge).

## ClassTrack — Genius Idea #18 (live, port 8824)
Fitness-studio class-pack credit ledger: FIFO-by-expiry pack spending,
capacity sessions, **idempotent `booking_ref`** (double-tap safe), free
waitlist with automatic promotion-charging, late-cancel/no-show forfeiture as
explicit studio policy, door check-in + post-session no-show sweep, and an
outstanding-credits (liability) report. Card numbers rejected; consumer-law
caution on pack expiry printed in the report. Tests **7/7** (demo pack of 10
→ 9 after a double-submitted booking charged exactly once).

## Publication
- Live portfolio: **17 previews, ports 8808–8824**.
- GitHub: `arena/78ba5633-kitab-bookstore` (this round's commit).
- service-finder tests: 30/30 OK.
