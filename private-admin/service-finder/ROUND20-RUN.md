# Round 20 run — 2026-10-21

## Honest headline

- **Client replies so far: still zero. Confirmed payments: zero.** Gmail checked again
  this round (Iditarod / Canadian Club of Ottawa / Memory Studies Association, incl.
  spam & trash, complete scope): **0 replies**.
- Canadian Club of Ottawa's stated deadline (Oct 21, 2026) has now been reached with
  no reply. Still watching: Memory Studies Association (Nov 1, 2026) and Iditarod
  (Nov 2, 2026). No follow-ups sent (rule: no extra emails without a reply).

## Opportunity hunt (worldwide, excluding the Arab world)

Four search waves: public libraries / Friends-of-library groups; heritage railway,
lighthouse and astronomy nonprofits; PH/ZA/IN NGO website RFPs; farmers markets and
food co-ops. **Qualified: 0. Emailed: 0.** Screened-out records preserved in
`round20/excerpts.txt` + `round20/sources.json`; snapshot in `results/round20/`
(3 records, 0 errors; tool regex flags them "conflicting_deadlines_review" — human
verdict governs: all deadlines passed).

- City of Berkeley / Berkeley Public Library rebranding RFP 26-11785-C — due
  May 21, 2026 (passed); city procurement, not a small-nonprofit website job.
- Friends of Gates Public Library (Rochester, NY) — due Aug 28, 2026 (passed).
- Lackawanna County Library System website & PR RFP — due Jun 26, 2026 (passed);
  no plain public submission email outside the attachment.
- Also seen and rejected without records: City of Waverly (due Apr 6, 2026),
  New Rochelle PL 2025 (3 references), Hartford PL 2025, Southeastern Railway
  Museum strategic-planning RFP (not website work, 3 references), Cecil County
  Library strategic planning (not website work), Berkeley Digital Experience
  platform (due Jan 20, 2026). Hunger Task Force / Cloverdale reappeared from
  earlier rounds — already screened, ignored. Nobody was contacted.

## ShieldScan MAX 12.0 (Genius Idea #2, port 8808)

- **8 new passive, evidence-backed checks:** open-redirect-shaped links
  (`?next=`/`?url=` pointing off-site), `mailto:` form actions, file-upload
  surface inventory, inline `style=` attributes (CSP readiness), external
  `<base>` tags hijacking relative URLs, third-party web fonts (visitor-IP
  privacy); status-only probes for public API docs (`openapi.json`,
  `swagger-ui/`) and GraphQL endpoints (200/400/405).
- **More illustration:** category mini-donut rings join the radar in the
  illustrated HTML risk report.
- **Fuller one-link automation:** SARIF, findings CSV and the Markdown report
  now ride inside the single scan response and are downloadable directly from
  the web UI — one customer link in, every file out, no CLI needed. CLI
  `--out` / portfolio JSON stay slim.
- Tests **39/39**. Samples regenerated: weak demo F 0/100 (68 findings),
  good demo A+ 96/100 (11). Zip: `shieldscan-v12.zip`.

## TradeAtlas (Genius Idea #14, port 8820) — NEW, built at the user's request

An **educational** atlas of trading knowledge: 16 classic strategies (each with
textbook rules AND how it fails), 10 analysis methods, 8 candlestick patterns
illustrated in SVG with invented example prices, position-size / risk-reward /
expectancy calculators, 8 risk rules and a glossary. JSON + calculator APIs.

Deliberate scope limits, stated on every page: **education only — not financial
advice, no buy/sell signals, no live data, no broker links, no profit promises**
(most short-term traders lose money; the atlas says so prominently). Tests 6/6.
Zip: `tradeatlas-v1.zip`.

## Portfolio state

13 previews live (8808–8820): ShieldScan MAX 12.0, BillForge, PageForge,
MenuCraft, ChatCart, SlotBook, EventCraft, QuoteForge, StarFunnel, PawTag,
TapCard, StayGuide, TradeAtlas. service-finder tests 22/22.

## Payment note (unchanged)

If a client agrees: 50/50 milestones, USDT-TRC20
`TVDjBzZuHu3drJ1H4jbanLyNb9Ss3uMBNy` (public receive address only), small test
transfer deducted from the first milestone, TXID verified before paid start.
Never share a seed phrase or private key with anyone.
