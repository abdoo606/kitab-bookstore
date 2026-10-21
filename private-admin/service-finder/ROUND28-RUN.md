# Round 28 run — 2026-10-21 (recovery + hunt + ShieldScan v20 + TradeAtlas v9 + SafePlate)

## Workspace recovery

The sandbox had reset outside-repo work again. The repository was restored to
branch `arena/78ba5633-kitab-bookstore` at pushed Round 27 commit
`b3c20a3`; ShieldScan v19, TradeAtlas v8, FoundDesk v1 and ToolLibrary v1
were recovered from Drive archives and compile/import-verified before new
work began. The service-finder virtualenv was recreated locally and remains
unpublished.

## Gmail

Targeted spam/trash-inclusive searches for the three earlier website-service
targets — Iditarod, Memory Studies Association and Canadian Club of Ottawa —
returned only the original sent messages: **0 service replies, 0 acceptances,
0 payments**.

Standing deadlines remain **Memory Studies Association: Nov 1, 2026** and
**Iditarod: Nov 2, 2026 17:00 AKST**. Canadian Club of Ottawa's deadline was
Oct 21, 2026; no reply had arrived at this check.

## New worldwide non-Arab service hunt

**Result: 0 qualified, 0 built for, 0 emailed.** Four originals with public
email routes were fetched and screened under the standing rules (worldwide
non-Arab requester + public submission email + live deadline + honestly
meetable gates + work that can be built first):

- **Regional Water Authority / Sacramento Groundwater Authority** website
  redesign and ADA compliance, `aflores@rwah2o.org` — proposals were due
  **Sep 15, 2026**. The work covers two public-authority websites, about 102
  pages and 662 PDFs, ADA remediation, migration, possible intranet and
  public-agency experience.
- **Bellingham Housing Authority** website development/design RFP-BHA-2026-
  04-IT, `procurement@bellinghamhousing.org` — the original is marked
  **[CLOSED]** and proposals were due **May 27, 2026**. Scope included
  rebrand, property directory and 12-month support.
- **Dayton Area Chamber of Commerce EPI Foundation** website design and
  development, `daytonexperience@dacc.org` — proposals were due **Apr 13,
  2026**. The roughly 40-page flagship asks for a comparison tool, CRM forms,
  vendor hosting, comparable experience, team/case-study evidence and
  references.
- **College of Massage Therapists of Ontario** new website design,
  development and maintenance, `communications@cmto.com` — the intent gate
  closed **Jul 7, 2026**, proposals were due **Aug 11, 2026**, and the
  original says no further submissions are accepted. It is a $70,000 regulated
  bilingual English/French platform.

Evidence: `round28/excerpts.txt` and `round28/sources.json`. The local
snapshot in `results/round28/` produced **4 records, 0 errors**, all
machine-triaged `conflicting_deadlines_review` because the combined excerpts
file exposes all four deadlines to every record. The fetched originals and
human verdicts above govern. service-finder tests: **30/30**.

## ShieldScan MAX 20.0 (live, port 8808) — fix verification & closure evidence

- **Fix Verification & Closure Evidence Autopilot:** a scan now either creates
  a verification plan (no baseline) or, given a previous findings-bearing
  `report.json`, produces closure evidence by comparing normalized
  code/title keys with code-level fallback. It reports verified closed, still
  open, inconclusive, new findings, severity changes, raw and verified
  closure rates, critical/high closure, risk points retired/residual,
  sign-off criteria, low/medium exception candidates and a deterministic
  evidence-record ID.
- **Closure cannot be faked by checking less:** a baseline finding is
  inconclusive—not closed—when its relevant probe/email check was disabled,
  the current target is unreachable, or the current crawl is narrower than the
  baseline crawl. Baseline/current target mismatch is also explicit. The
  output is labelled a passive evidence record, not a penetration-test or
  compliance certification.
- New exports and integrations include `fix-verification.json`,
  `closure-certificate.md`, illustrated HTML/Markdown/one-page sections, UI
  downloads, client email/WhatsApp closure summaries, CLI
  `--fix-verification-out` and `--certificate-out`, generated CI artifacts,
  policy handling and the audit bundle (**27 files**).
- **6 new status-only probes** — metrics, health, OIDC, workspace, scaffold
  and server-info paths — take the probe total to **58 paths**. Every new
  code has `PATCHES`, `EFFORT` and `STANDARDS`: **162 patch codes, 162
  standard codes, 150 effort entries**. The weak demo answers all six with
  fake data only; no secret contents are downloaded.
- Tests **72/72**. Samples regenerated from imported current source: weak
  **F 0/100, 136 findings** (15 critical, 15 high, 17 medium, 64 low, 25
  info), 3 pages, 9 attack paths/max risk 99, 111-item verification plan,
  calendar 111 tasks/157.2 hours/46 workdays/finish 2026-12-24; good **A+
  96/100, 12 findings**, 2 pages, 0 attack paths.
- The weak→good demo re-audit intentionally remains honest: baseline and
  current targets are different demo paths, so fix verification reports
  `baseline_mismatch`. `sample-fix-verification.json` and
  `sample-closure-certificate.md` are verification-plan artifacts, not a
  fabricated verified-closure claim.

ShieldScan remains passive/defensive only: authorization gates, status-only
sensitive-path probes, no secret-body downloads and credential redaction.

## TradeAtlas v9.0 (live, port 8820) — path geometry + a causal selector, still no edge

- New **path-geometry analog family** with 16 origin-time features: 20/60-bar
  travel efficiency, volatility-normalized log-trend slopes, 5-bar variance
  ratio, lag-1 autocorrelation, realized skew and downside-variance share,
  60-bar drawdown/run-up/range position, 20-bar maximum drawdown, volatility
  and range compression, signed return streak, and real up/down volume
  balance. It powers `path_analog_median`, `path_analog_weighted`,
  `path_analog_now` and `majority_vote_v4` under the same
  `j + horizon <= origin` no-lookahead rule.
- New **`adaptive_selector`** is causal and auditable: a candidate becomes
  eligible only after 20 fully revealed prior attempts, where an attempt is
  revealed only when `old_origin + horizon <= current_origin`. Eligible
  candidates are ranked by `(revealed_hits + 5)/(revealed_attempts + 10)`;
  otherwise it falls back to the newest majority vote/momentum. Every origin
  choice is kept in `adaptive_selector.selection_log`.
- `consensus_3plus` deliberately retains its v8 four-family definition for
  comparability. The v4 analog definition and pinned AAPL result remain
  untouched.
- Bundled **real AAPL daily**, 100 hidden-future attempts at horizon 5:
  original analog **44.0%**, path median/weighted **47.0%/47.0%**,
  `majority_vote_v4` **51.0%**, `adaptive_selector` **54.0%**, naive momentum
  **58.0%**. The selector used fallback 21 times and then chose momentum 56
  times and path methods 21 times. After costs, the new methods remain
  negative (selector **−0.191%/trade at 10 bps** and **−0.341% at 25 bps**),
  while momentum was +0.166%/+0.016%.
- Close-only real MSFT monthly (40 attempts, horizon 3 months): path/v4 make
  only **28 attempts** because the new family needs an 80-bar warm-up; path
  median **42.9%**, weighted **28.6%**, selector **40.0% over 40**, momentum
  **55.0%**. At 10 bps the selector nets **−4.417%/trade**. On close-only
  data, high/low path pieces collapse to closes and volume balance is zero
  rather than invented.
- README's forecast-attempt evolution table now includes v9 beside v4–v8.
  Tests **32/32**, including future-mutation proof for path vectors/
  neighbours and delayed-reveal/future-mutation proof for selector choices.
  Honest conclusion: **no demonstrated real-data edge**. Causal selection
  prevents information leakage; it does not create information.

## SafePlate — Genius Idea #22 (live, port 8828)

A deterministic allergen substitution and menu-safety desk for small cafés.
Menu declarations are derived from verified ingredient evidence rather than
typed into a static matrix. Before a supplier substitution is approved,
SafePlate gives an item-by-item impact report—allergens added/removed,
guest-answer consequences, cost movement and labels to reprint—and requires a
manager to explicitly acknowledge any material allergen change. Incomplete,
stale or retired evidence forces **ask staff**, shared-station preparation is
visible as cross-contact caution, and no dish is ever called “safe”: the
strongest wording is **no declared presence found**.

Deterministic demo at 2026-10-21: 15 ingredients (13 fresh, 1 pending, 1
stale at 324 days), 6 dishes, average recipe cost **0.92**, satay bowl cost
**1.85**, croissant cost **0.36**. Peanut check: 1 contains, 2 ask-staff, 2
caution, 1 no-declared-presence. Milk + peanut check: 3 contains, 2 ask-staff,
1 no-declared-presence. Opening status is **blocked** by pending/stale
evidence and a never-printed label; one moderate incident follow-up is one day
overdue. `SUB-OAT-2026` removes wheat may-contain, adds soy may-contain,
clears the pending warning and costs **+0.06/serving**; `SUB-SUN-2026`
removes peanut contains/tree-nut may-contain, adds sesame may-contain and
costs **+0.03/serving**. Incident records deliberately store no guest name,
contact, diagnosis or medical details. Tests **8/8**; source SHA-256
`62eedb90fdbf961ccb4663e3a3db3caad012fdb392135634feb8a0462d041ec0`.

## Publication

- Product previews restarted from final code and verified HTTP 200:
  ShieldScan 8808, TradeAtlas 8820, SafePlate 8828.
- Final full local test pass from current sources: ShieldScan **72/72**,
  TradeAtlas **32/32**, SafePlate **8/8**, service-finder **30/30** — 142
  tests total.
- Product packages prepared for Drive:
  - `shieldscan-v20.zip` — 28 files, 976,612 bytes, SHA-256
    `9bf22cbbf291b8c45932f1d17d7fc1565655e6bb2e288a96f0de43d55324df74`
  - `tradeatlas-v9.zip` — 17 files, 168,718 bytes, SHA-256
    `4f91561d5e646ba03880efba5d2906832653bc7b374102460308b1bc886d1263`
  - `safeplate-v1.zip` — 9 files, 33,453 bytes, SHA-256
    `644ac1f65e545b7886c92b6cfc4a19bb35a33e9f3888dcb7eccb9da921d36d1a`
  - plus `service-finder-round28.zip`, this run file and
    `round28-opportunities.csv`.
- Outreach total remains: **3 targets contacted in earlier rounds, 0 replies,
  0 acceptances, 0 payments**.
