# Round 27 run — 2026-10-21 (recovery + follow-up + new hunt + ShieldScan v19 + TradeAtlas v8 + FoundDesk)

## Workspace recovery

The sandbox had reset outside-repo work. The repository was restored to
branch `arena/78ba5633-kitab-bookstore` at pushed baseline `db17ece`, and
ShieldScan v18, TradeAtlas v7 and ToolLibrary v1 were recovered from their
Round 26 Drive zip archives. All recovered Python entry points compiled
before new work began. The service-finder virtualenv was recreated locally;
it is intentionally not published.

## Gmail

Targeted complete searches for the three earlier website-service targets —
Iditarod, Memory Studies Association and Canadian Club of Ottawa — returned
**0 reply messages**. There is still **no service acceptance and no payment**.

A separate Agentplace message (`1a15b7a0adcf0ab4`) only acknowledges that an
application is under review. It is not one of the three website-service
targets, not an acceptance and not a payment.

Standing deadlines remain **Memory Studies Association: Nov 1, 2026** and
**Iditarod: Nov 2, 2026 17:00 AKST**. Canadian Club of Ottawa's deadline was
Oct 21, 2026; no reply had arrived at this check.

## New worldwide non-Arab service hunt

**Result: 0 qualified, 0 emailed.** Four originals with public email routes
were fetched and screened under the standing rules (public submission email +
honestly meetable gates + live deadline + scope that can be built first):

- **Ghana Chamber of Mines** corporate website redesign,
  `Chamber@GhanaChamberOfMines.Org` — deadline passed **Jan 31, 2026**; the
  request is for an agency/firm to deliver a corporate platform including a
  membership portal, publications/events hubs, CMS migration and optimization.
- **Jamaica Athletics Administrative Association** website redesign,
  `JAAAWebRFP@gmail.com` — deadline passed **Feb 16, 2026**; scope includes
  athlete dashboards, secure portals, registration/payments, company
  background and team biographies.
- **Southern Nevada Health District 27RFP002**, `procurement@snhd.org` —
  deadline passed **Aug 24, 2026**. The $100,000 project is a 4,000+ page
  WordPress migration and requires five years' continuous similar service,
  public-sector WCAG experience and three client references, none of which
  can be promised honestly from the current record.
- **C40 Cities** 2026–2028 web development/support RfP,
  `digital.comms@c40.org` — deadline passed **Feb 20, 2026**; it requires at
  least three similar projects, comparable references, named personnel, SLA
  evidence and insurance for a three-year global contract.

Evidence: `round27/excerpts.txt` and `round27/sources.json`. The local
snapshot in `results/round27/` produced **4 records, 0 errors**, all
machine-triaged `needs_deadline_review` because its parser did not extract
the deadline forms from the combined excerpts file. The fetched originals
and human verdicts above govern. service-finder tests: **30/30**.

## ShieldScan MAX 19.0 (live, port 8808) — attack paths and blast radius

- **Attack Path & Blast-Radius Autopilot:** passive findings are now joined
  into up to nine deterministic, evidence-linked path families (secret/source
  exposure, browser script injection, session/account theft, transport
  interception, UI redress, third-party supply chain, admin/CMS takeover,
  privacy/data exfiltration and API-discovery abuse). Each path separates
  observed preconditions from a clearly hypothetical impact stage, carries a
  risk score/confidence, impacted assets, business impact and ranked
  break-the-chain fixes using the findings' existing patch steps. The report
  also identifies the five highest-leverage breakpoints and rebuilds the
  graph without those finding codes as a labelled simulation, not a promise.
- The result is exported through the illustrated HTML report, one-page
  summary, Markdown, JSON, UI download, `--attack-paths-out`, generated CI
  artifacts and the audit bundle as `attack-paths.json` (**25 bundle files**).
- **6 new passive checks** take the patch/standards library to **156 codes**:
  HTTP browser-report collectors (hostnames only, never token-bearing URLs),
  wildcard `Clear-Site-Data`, COOP/COEP `unsafe-none`, and CSP directives
  placed in a `<meta>` tag where browsers ignore them. **6 status-only
  probes** take the total to **52**: `.hg` metadata, `server.key`,
  `credentials.json`, `.ssh/id_dsa`, WordPress and Laravel logs.
- The documented/generated `--ci-pack` and `--policy` CLI options are now
  wired to the parser, so the generated GitHub Actions gate can run as
  written.
- Tests **68/68**. Samples regenerated: weak **F 0/100, 130 findings** (15
  critical, 13 high, 16 medium, 62 low, 24 info), with **9 critical
  attack paths** and maximum path risk 99; good **A+ 96/100, 12 findings, 0
  actionable attack paths**. Weak-demo calendar: 106 tasks, 154.8 hours, 45
  workdays, finishing 2026-12-23. New sample:
  `sample-attack-paths.json`.

ShieldScan remains passive/defensive only: authorization gates, status-only
sensitive-path probes, no secret-body downloads, and redacted evidence.

## TradeAtlas v8.0 (live, port 8820) — indicator regimes join, and lose honestly

- New **indicator-regime analog family** with 15 origin-time features: RSI
  level/slope, ATR-normalized MACD, Bollinger %B/bandwidth, SMA-20/50
  distance and slope, Donchian/Stochastic position, ADX balance/strength,
  realized-volatility regime, and real volume surprise where volume exists.
  Neighbours obey the same `j + horizon <= origin` rule. The original v4
  analog definition and pinned result are unchanged.
- New `indicator_analog_now`, `indicator_analog_median`,
  `indicator_analog_weighted`, `majority_vote_v3`, and a coverage-labelled
  `consensus_3plus` subset. The `best_method_on_this_sample` label is now
  reserved for full-test methods so a small self-selected subset cannot be
  crowned as the winner.
- Bundled **real AAPL daily**, 100 hidden-future attempts, horizon 5:
  original analog **44.0%**, indicator median **49.0%**, indicator weighted
  **46.0%**, majority v3 **46.0%**, naive momentum **58.0%**. Indicator/v3
  calls lose after both 10 and 25 bps costs. `consensus_3plus` shows
  **65.4% on only 26/100 attempts (26.0% coverage)** and falls from
  **+0.022%/trade at 10 bps to −0.128% at 25 bps**.
- Close-only MSFT monthly (40 attempts, horizon 3 months): the indicator
  family can run from the close path (47.5% median, 52.5% weighted/v3),
  while candle methods still correctly report unavailable rather than
  inventing candle anatomy. Its consensus subset made only five calls, so no
  accuracy headline is shown.
- README's version-evolution table now documents v8 beside v4–v7. Tests
  **28/28**, including future-mutation and pinned real-AAPL accuracy/cost
  tests. Conclusion remains **no demonstrated tradable edge**; v8 improves
  the measurement and honesty, not the underlying forecast truth.

## FoundDesk — Genius Idea #21 (live, port 8827)

A privacy-preserving lost-and-found desk for schools, libraries, venues,
transit hubs and community centres. Its public catalogue exposes only broad
category, colour family, coarse area, date and held-until. Brands, exact
locations, identifying marks, storage bins, contacts and full serials stay
staff-only; public search cannot enumerate private marks. Claims receive a
deterministic staff score (private-mark overlap, serial evidence, brand,
colour, date and location) while claimants see only a broad match band.
Valuable/sensitive items require supervisor approval/release, pickup codes
are one-time and stored only as hashes, and expired items flow into a
donation / secure-disposal / authority-transfer queue. Card-shaped numbers
are rejected; a score supports staff judgment and does not prove ownership.

Deterministic demo at 2026-10-21: six items recorded; a wallet claim scores
**87.5/100** and is released, an umbrella claim scores **53.57/100** and
stays submitted, keys are **22 days retention-overdue**, and an expired
paperback is donated. Report: 4 held, 1 released, 1 donated, 2 claims, 1
valuable/sensitive item still held. Tests **8/8**; five CLI repetitions give
the identical SHA-256 output.

## Restored product baseline

ToolLibrary #20 was rerun after recovery: tests **8/8** and its preview is
live on port 8826 with the same verified demo arithmetic as Round 26.

## Publication

- Currently restored live previews verified HTTP 200: ShieldScan 8808,
  TradeAtlas 8820, ToolLibrary 8826 and FoundDesk 8827.
- Product packages prepared for Drive: `shieldscan-v19.zip`,
  `tradeatlas-v8.zip`, `founddesk-v1.zip` and
  `service-finder-round27.zip`, plus this run file and
  `round27-opportunities.csv`.
- Outreach total remains: **3 targets contacted in earlier rounds, 0
  replies, 0 acceptances, 0 payments**.
