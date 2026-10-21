# Round 22 run — 2026-10-21

## Honest headline

- **Client replies so far: still zero. Confirmed payments: zero.** Gmail was
  checked again for Iditarod / Canadian Club of Ottawa / Memory Studies
  Association including spam and trash (complete search scope): **0 replies**.
- Still watching Memory Studies Association (Nov 1, 2026) and Iditarod
  (Nov 2, 2026). No follow-up emails were sent.

## Opportunity hunt (worldwide, excluding the Arab world)

New angles: zoos/aquariums/museums, chambers of commerce, community
foundations/food banks/humane societies, and international NGO website
consultancies in the Caribbean, Africa and Asia-Pacific. Originals (including
full TOR PDFs) were read for every live lead. **Qualified: 0. Emailed: 0.**

Records in `round22/excerpts.txt` + `round22/sources.json`; snapshot in
`results/round22/` (4 records, 0 errors; service-finder tests 22/22).
Human verdicts govern over tool labels:

- **Caribbean Policy Development Centre (Barbados)** — the round's one truly
  live, public-email website consultancy (`cpdcsubmissions@gmail.com`,
  deadline Oct 22, 2026). Screened out: the TOR requires a university degree,
  **7+ years** of professional experience, a similar-assignment track record
  and a professional reference at shortlist ("Only applicants meeting the
  criteria should apply") — none of which can be represented honestly.
- **ILRI NPA-FORAGE (Ethiopia)** — digital platform consultancy, deadline
  Nov 1, 2026, but recruitment-portal only, with bachelor's-degree,
  5–7-year-experience, Amharic-fluency, Addis Ababa duty-station and
  business-licence/VAT-receipt gates.
- **International Seabed Authority (Jamaica)** — expired Oct 20, 2026 and
  explicitly closed to individual consultants (screened in earlier rounds too).
- **Civic Voice (East Africa)** — expired Aug 24, 2026; 3-year/portfolio/
  legal-registration gates.

Nobody was contacted.

## ShieldScan MAX 14.0 (Genius Idea #2, port 8808)

One authorized customer link now does even more of the work itself:

- **9 new passive, evidence-backed checks:** JWT-shaped tokens in page source
  (values never reproduced), exposed chat-webhook receiver URLs (Slack /
  Discord / Telegram / Teams / Zapier / Make / Google Chat — provider named,
  secret never printed), private-IP / `localhost` / `.local` disclosure
  (masked), obsolete Flash/Java plugin embeds, `data:`-URI scripts,
  `javascript:`-URI links, live-chat widget inventory, public crypto-address
  inventory, and **DNSSEC** posture via the parent-zone DS record.
- **4 new status-only probes (30 total):** `.ssh/id_rsa`, `.bash_history`,
  `terraform.tfstate`, `composer.lock` — status codes only, bodies never read.
- **Fix-It server-config generator:** the same one-link run now assembles a
  review-ready **Nginx + Apache + DNS** drop-in containing only the blocks
  that match findings actually present (HTTPS redirect, security headers,
  sensitive-file deny rules, TRACE/index/cache rules, SPF/DMARC/CAA/MTA-STS/
  DNSSEC/security.txt checklist). UI button, bundle file
  `fix-it-server-config.txt`, CLI `--fix-script`. It changes nothing on the
  server by itself — it is a staged, human-reviewed starting point.
- **New illustration:** third-party supply-chain surface (external hosts,
  cross-origin scripts, trackers, chat widgets, cloud storage, staging hosts,
  webhook receivers, executable downloads).
- Tests **47/47**. Samples: weak F 0/100 (**93 findings**), good A+ 96/100
  (12). Artifact: `shieldscan-v14.zip`. Patch library now covers **121**
  finding codes.

## TradeAtlas v3.0 — Market Lab MAX (Genius Idea #14, port 8820)

Still bring-your-own lawful data — no fabricated live prices, no advice:

- **Indicators:** snapshots add **Stochastic %K/%D** and **ADX with +DI/−DI**
  (Wilder), joining SMA/EMA, RSI, MACD, Bollinger and ATR.
- **9 strategy engines** (was 7): new **stochastic zone reversal** and
  **ADX trend-strength onset**. Latest long/short (buy/sell) *conditions* are
  reported on **1m, 5m, 15m, 1h, 4h, 1d, 1w** wherever the supplied base
  interval honestly supports them — otherwise "no fresh trigger" is stated.
- **All-engine tournament per timeframe:** every engine gets the same
  100-signal, next-bar-entry, cost-adjusted test on the same bars and is
  ranked by historical expectancy — with an explicit warning that the top
  row is the most over-fit row.
- **70/30 walk-forward split:** earlier-vs-later slices of the same 100
  trades with a robustness verdict. In the synthetic sample the 1w consensus
  headline (+1.12% expectancy, 54% accuracy) is flagged `degraded_later` —
  its later slice is negative. That is the point of the tool: single-number
  accuracy hides fragility.
- **Equity-curve points** in every backtest (UI sparkline).
- **Multi-symbol watchlist** (`POST /api/lab/watchlist`): one file per symbol
  across crypto/stocks/FX/futures/indices → latest-condition heatmap on all
  honest timeframes. Symbols are deliberately never ranked.
- **Market presets:** per-asset-class cost ranges to research and data traps,
  so the cost field starts from homework instead of fantasy.
- **100-attempt accuracy test, re-run:** `sample-lab-validation.json`
  (clearly **synthetic** prices, software validation only) again tested
  exactly 100 completed consensus signals on every timeframe — accuracies
  44% (1m), 54% (5m), 51% (15m), 56% (1h), 48% (4h), 51% (1d), 54% (1w);
  expectancy −0.41%…+1.12%; max drawdown up to 87%. Tournament winners
  differed by timeframe. **None of this says anything about real markets.**
  Real accuracy exists only on real bars the user supplies, and even then it
  is history, not a forecast.
- Tests **15/15**. Artifact: `tradeatlas-v3.zip`.

## JobProof (Genius Idea #16, port 8822) — NEW

Before/after job-proof pages for cleaners, movers, detailers, handymen and
garden crews:

- 5 trade checklist templates; **completion is blocked** while mandatory
  items are open unless an override note is recorded.
- Before/after **condition log** per area (1-5) with an improved/same/worse
  delta — pre-existing wear documented before work starts.
- Itemized quote + add-ons, photo links, timestamps, full event history.
- Client page (reference + access code): progress, **approve with rating** or
  **flag an issue**; approval generates a proof receipt.
- Manager board with masked contacts; crew/manager code gates in the demo;
  obvious door-code/password text is rejected from job fields.
- Honest boundary: demo acknowledgement record — not a legal e-signature,
  tax invoice or payment system.
- Tests **7/7**. Sample job `JP-20261021-4CF8B3` (100%, approved, 325 USD).
  Artifact: `jobproof-v1.zip`.

## Portfolio state

15 live previews (8808–8822): ShieldScan MAX 14.0, BillForge, PageForge,
MenuCraft, ChatCart, SlotBook, EventCraft, QuoteForge, StarFunnel, PawTag,
TapCard, StayGuide, TradeAtlas v3.0, RepairDesk, JobProof.

## Payment note (unchanged)

If a client agrees: 50/50 milestones, USDT-TRC20
`TVDjBzZuHu3drJ1H4jbanLyNb9Ss3uMBNy` (public receive address only), small test
transfer deducted from the first milestone, TXID verified before paid start.
Never share a seed phrase or private key with anyone.
