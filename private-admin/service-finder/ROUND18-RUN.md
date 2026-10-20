# Round 18 run record — 2026-10-21

## Housekeeping first: round 17 fully closed
Finished the round-17 Drive archiving left pending last turn: shieldscan-v9.zip into the
ShieldScan folder, new "PawTag — Genius Idea 11" folder with pawtag-v1.zip + README, and
service-finder-round17.zip + ROUND17-RUN.md + round17-opportunities.csv at Drive root.
Closing comment added on "ابدأ هنا" (doco.FJbGNakssYodKBpx6ap2xA). Round 17 commit was
already pushed last turn (c194ca4).

## Replies check
Gmail targeted search (Iditarod / Canadian Club of Ottawa / Memory Studies Association,
incl. spam/trash, complete): **0 replies**. Open clocks: MSA Nov 1, Iditarod Nov 2, 2026.

## Prospect hunt (worldwide, excluding Arab countries; public-email rule; originals verified)
Three fresh waves (museums/heritage; associations with Nov–Dec deadlines; UK/AU charity
tenders + libraries/festivals/conservation): **0 qualified, 0 emailed.**
- Kitsap Community Foundation (WA, USA), Gretchen@kitsapfoundation.org — deadline Apr 15, 2026 passed.
- Breakthrough T1D Canada — deadline Oct 9, 2026 passed (vendor already selected Oct 19).
- 1000 Friends of Oregon ($15,000) — deadline Aug 10, 2026 passed; site launch due Oct 30, 2026.
- Also rejected: rfpmart Nov-2026 "GLOBAL" listings (paywalled aggregator, no public email);
  Achievement First (round-10 screen: enterprise 41-site firm RFP); Esplanade (due Jun 1, 2026);
  UK Find-a-Tender portal frameworks (registration gates); Studios of Key West (already launched).

## ShieldScan MAX upgraded: v9.0 → v10.0
- **New precise checks (passive only):** third-party iframes without `sandbox`, SRI tags missing
  `crossorigin` (hash silently unenforced), password fields blocking paste or forcing
  `autocomplete="off"`, cleartext `ws://` WebSocket references, JS source-map pointers in
  production, and SPF records over the RFC 7208 10-lookup limit. Each ships evidence,
  risk text, patch steps + snippets, effort tier and standards mapping (NIST 800-63B etc.).
  A real bug was caught by the new tests on first run ("unsandboxed" in an iframe title
  suppressing the check) and fixed with a proper attribute-boundary match.
- **More illustration:** category radar (spider) chart in the illustrated report.
- **Fuller one-link automation:** SARIF 2.1.0 export (`--sarif`, GitHub code-scanning ready)
  and a spreadsheet findings CSV with per-row patch steps (`--csv`) join HTML/JSON/one-page/
  client email/WhatsApp outputs from the single customer link.
- Tests **32/32 OK**. Samples: weak F 0/100 (53 findings), good A+ 96/100 (10), re-audit,
  portfolio, one-page, client email, SARIF, CSV. Preview port 8808 shows "ShieldScan MAX 10.0".

## Genius idea #12 — TapCard (new)
Digital business-card one-pager for NFC/QR: initials avatar, one-tap Save-contact (real
vCard .vcf download), WhatsApp/call/email, directions (auto maps search), services, hours,
socials and a share button. Tests **5/5 OK**. Preview port 8818. Sellable to realtors,
barbers, sales reps, tradespeople, freelancers; bundles with NFC cards/QR stands.

## Previews (all HTTP 200, verified this round)
8808 ShieldScan v10 · 8809 BillForge · 8810 PageForge · 8811 MenuCraft · 8812 ChatCart · 8813 SlotBook · 8814 EventCraft · 8815 QuoteForge · 8816 StarFunnel · 8817 PawTag · 8818 TapCard.

## Next steps
1. Watch inbox through Nov 2 (MSA Nov 1, Iditarod Nov 2) — decisive window.
2. Keep hunting public-email nonprofits/clubs/small associations outside the Arab world;
   build-first; verify originals (deadlines + reference/insurance/portal gates) before outreach.
3. Lead offers: TapCard/QuoteForge/StarFunnel/PawTag/MenuCraft for local businesses and
   professionals; ShieldScan v10 audits (now with SARIF/CSV deliverables); USDT-TRC20.
