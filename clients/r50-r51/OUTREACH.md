# R50–R51 — two paid-outreach rounds (10 sends, 0 jobs)

Goal set by the user: **money, not employment**. Every email sells a fixed-price deliverable and states
all five numbers. No CV, no "looking for a role", no hourly rate.

## Why these buyers

Both rounds sell to **intermediaries who already deliver the compliance work for many end clients**
(consultancies, customs brokers). One sale to them covers many of their clients, so they can justify a
$2.2k–$2.4k tool from a single engagement invoice. End customers were deliberately not targeted:
a first-time cold email to an importer rarely converts, while a consultancy buying throughput does.

## Round 50 — EU AI Act, Annex IV evidence (5 sends)

Offer: **Annex Evidence Workbench** — classify (Art. 5 / Annex III / Annex I / Art. 50) → score the 9
Annex IV sections → SHA-256 manifest + root hash → verify → rebuild and diff at every model release.
Offline, Python standard library, white-label.

Demo: `builds/annex-evidence-workbench/index.html`

Price: **turnkey $2,400 · M1 $600 · M2 $600 · M3 $600 · $190/mo**
M1 classification + 9-section generator · M2 manifest, verify, gap report · M3 CI diff, handover, tests.

| # | Recipient | Company | Hook used |
|---|-----------|---------|-----------|
| 82 | contact@clarifyconsult.com | Clarify Consult (BE) | their own line: Annex IV "maintained current after every substantial model update" |
| 83 | info@cruxdigits.nl | Crux Digits (NL) | €950 fixed-price AI Act Check — evidence assembly is the cost centre |
| 84 | julien.winkin@luxgap.com | Luxgap (LU) | four frameworks, one evidence base; they promise a reply in one business day |
| 85 | contact@dpo-consulting.com | DPO Consulting (FR) | their step order ends at Annex IV structure + conformity assessment |
| 86 | info@innfactory.ai | innFactory (DE) | they sell an "AI Officer" and build n8n automations — webhook-triggered rebuild |
| | | Sent 2026-10-22, ids 1a164321–1a164325 | |

## Round 51 — EUDR, DDS evidence (5 sends)

Offer: **EUDR Evidence Vault** — per-plot risk (missing geolocation, centroid, area mismatch, forest loss
in window, country baseline) → DDS payload for TRACES → sealed evidence pack + hash-chained retention
ledger → diff per lot. Offline, Python standard library, white-label.

Demo: `builds/eudr-evidence-vault/index.html`

Price: **turnkey $2,200 · M1 $550 · M2 $550 · M3 $550 · $190/mo**
M1 plot risk + DDS payload · M2 manifest, ledger, verify · M3 supplier ingestion, diffs, handover, tests.

| # | Recipient | Company | Hook used |
|---|-----------|---------|-----------|
| 87 | info@global-traceability.com | Global Traceability | they promise EUDR "simple and cost-effective" — evidence work is what breaks that promise |
| 88 | compliance@sustalium.com | Sustalium | their point that a DDS mismatching the declared product is denied entry |
| 89 | info@impactbuying.com | ImpactBuying (NL/DE) | mid-sized importers: too much volume to do by hand, too small for a platform |
| 90 | ~~info@gaston-schul.com~~ → andrea.kuncova@wood-paper.cz | Gaston Schul bounced **550 5.4.1** (Exchange blocks the address); replaced with Wood & Paper a.s. (CZ) | customs desk compares statement to declaration at the border → supplier-file volume at a mid-size operator |
| 91 | contact@4-pack.com | 4Pack (UK) | EUDR sits underneath PPWR for wood-fibre packaging |
| | | Sent 2026-10-22, ids 1a164340–1a164344 and 1a16434b (replacement) | |

**Dates used (verified Oct 2026, not the 2025 schedule):** large and medium operators **30 Dec 2026**,
micro and small **30 Jun 2027**. The earlier 30 Dec 2025 date was postponed twice — using the current
date is itself a credibility signal.

**Bounces:** 1 of 10 — `info@gaston-schul.com` rejected by Microsoft Exchange with `550 5.4.1 Recipient address rejected: Access denied`. The address exists on their site but the mailbox refuses external mail. Replaced same round with a named recipient at Wood & Paper (CZ); no repeat attempts to gaston-schul.com.

## Dedupe

Checked `in:sent` per domain before sending (single OR query, 0 hits) against 81 prior clients + all
threads. Recipients #82–#91 are new; no prior contact with any of these domains.

## Pipeline value

| Round | Sends | Price per sale | Value if one closes |
|-------|-------|----------------|---------------------|
| R50 | 5 | $4,200 + $190/mo | $4,200 upfront |
| R51 | 5 | $3,850 + $190/mo | $3,850 upfront |
| both | 10 | — | **$8,050** if both, $4,200 if one |

Payment: USDT TRC-20 `TVDjBzZuHu3drJ1H4jbanLyNb9Ss3uMBNy`. No bank, no IBAN, no Wise.

## Standing rule that shaped the copy

Backends stay private until M1 (`clients/*/*/backend/` is git-ignored). What is public is the **demo** and
the **price**; what is paid for is the build, the handover, and the tests. Each email says explicitly what
is *not* included (legal opinions, DPO sign-off, notified-body liaison) so no sale is oversold.
