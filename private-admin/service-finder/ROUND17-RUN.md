# Round 17 run record — 2026-10-21

## Replies check
Gmail targeted search (Iditarod / Canadian Club of Ottawa / Memory Studies Association): **0 replies**.
Open clocks: MSA Nov 1, Iditarod Nov 2, 2026.

## Prospect hunt (worldwide, excluding Arab countries; public-email rule; originals verified)
Three fresh waves (animal welfare; historical societies/theatre/sports leagues; food banks/gardens):
**0 qualified, 0 emailed.**
- Guelph Humane Society (Canada), Nderaucourt@guelphhumane.ca — deadline Apr 20, 2026 passed.
- Rare / Coastal 500 (USA), coastal500@rare.org — read the full RFP PDF: deadline **Jan 23, 2026** passed,
  and Appendix 1 requires ≥3 past projects with client contacts (honest gate fail). Budget was $10k.
- Hunger Task Force (Milwaukee) — deadline Apr 21, 2026 passed; submission email obfuscated in excerpt.
- Achievement First resurfaced (screened in round 10 — not re-hunted). Rest were vendor self-promo pages.

## ShieldScan MAX upgraded: v8.0 → v9.0
- **New precise checks (passive/status-only):** legacy X-XSS-Protection filter, SHA-256-only SRI,
  inline event-handler inventory (CSP readiness), external meta-refresh bounces, publicly triggerable
  wp-cron.php, www/apex duplicate-host serving, certificate-SAN hostname inventory, HTTP/3 notice,
  well-known change-password URL.
- **More illustration:** per-area traffic lights (✓/!/✕ at a glance) + per-page heat strip for crawls.
- **Fuller one-link automation:** WhatsApp-ready short summary joins the client email (UI button +
  `client_whatsapp` in JSON); CLI `--client-email` writes the ready-to-send email directly.
- Tests **29/29 OK**. Samples: weak F 0/100 (47 findings), good A+ 96/100 (10), re-audit, portfolio,
  one-page, client email. Preview port 8808 shows "ShieldScan MAX 9.0".

## Genius idea #11 — PawTag (new)
Lost-pet rescue one-pager for collar-tag QRs: pet profile + medical alerts + one-tap WhatsApp/call
to owner (and vet), "send my location" via browser geolocation into WhatsApp. Exact home address
never shown. Tests **5/5 OK**. Preview port 8817. Sellable via pet shops/groomers/vets and owners.

## Previews (all HTTP 200, verified this round)
8808 ShieldScan v9 · 8809 BillForge · 8810 PageForge · 8811 MenuCraft · 8812 ChatCart · 8813 SlotBook · 8814 EventCraft · 8815 QuoteForge · 8816 StarFunnel · 8817 PawTag.

## Next steps
1. Watch inbox through Nov 2 (MSA Nov 1, Iditarod Nov 2) — decisive window.
2. Keep hunting public-email nonprofits/clubs/small associations outside the Arab world; build-first;
   verify originals (deadlines + reference gates) before any outreach.
3. Lead offers: QuoteForge/StarFunnel/PawTag/MenuCraft for local businesses; ShieldScan v9 audits; USDT-TRC20.
