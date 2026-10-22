# 2026-10-RFP — bid decision (written 2026-10-22 16:00 UTC)

## The clock

| fact | value |
|---|---|
| deadline | **2026-10-23, 18:00 CEST (16:00 UTC)** — 24 h after this memo |
| submit to | `callfortender@iarc.who.int` |
| files | exactly two: `Technical Proposal TECH IARC – 2026 10 RFP PLW Automation Software` and `Financial Proposal FIN …` |
| size / formats | ≤ 15 MB total; `.pdf .xls .doc .ppt` (+ `.docx`/`.xlsx` confirmed accepted) |
| validity | 120 days from submission |
| scoring | technical 70 % / financial 30 %; pass mark **70 % of 115 = 80.5** |
| demo | 2–4 Nov 2026, 1 h on Teams; IARC sends a ~250-page book chapter the day before |
| award | framework contract, end of Nov 2026 |

## What IARC will actually test

From the Q&A addendum (msg `1a1642fb852461d3`, 2026-10-22 15:16 UTC):

* everything up to the XML conversion should run **inside Word**, as a **plug-in** — a
  convert-first architecture is not what they asked for;
* **BITS 2.0 is mandatory** for books, **JATS 1.2** for journals (we currently emit JATS 1.3);
* the incumbent is **eXtyles**; ~70 `.xsb` dictionaries must be rebuilt from scratch
  (INERA copyright), documents up to **2 500 KB**;
* the demo must show the solution **fully operational with all capabilities** on a 250-page
  chapter with figures, tables and ~100 references;
* Office 365, Word **32-bit**, named-user licences, no Macs, desktop preferred, EU-only cloud
  if any, offline operation preferable, SharePoint a plus;
* support: urgent 24 h / medium 48 h; remote training plus optional 1–2 days in Lyon;
* ~15 book types, 5–6 books a year.

## Gap against `builds/iarc-plw-xml` (what exists today)

| requirement | today | gap |
|---|---|---|
| Word plug-in (Office.js/COM) | none — browser studio | build from zero |
| BITS 2.0 export | none | new DTD mapping + validation |
| JATS 1.2 | JATS 1.3 | version mapping |
| reference parsing + PubMed/Crossref | demo-level only | real API clients, rate limits, deposits |
| ~70 house-style rule sets | 3 demo rules | weeks of WHO-style rule authoring |
| 250-page / 6 000-reference performance | untested | load + profiling work |
| table auto-format, hard returns, auto-styling, auto-redact | none | the 10 "essential" points |
| migration, training, SLA, security review | none | services, not code |

## Decision: **do not submit a bid**

Not because the work is uninteresting — because a bid is a promise to be *fully operational* in
twelve days, and we would be promising it against a 250-page live test with a team of one and no
Word add-in. Losing honestly costs nothing; winning on a promise we cannot keep would put a WHO
agency in breach of its publication schedule and put us in a contract we cannot perform.

The eligibility section also asks for date of incorporation, country, and three years of turnover
— figures that must be true and signed. They are not ours to invent.

## What the documents are still worth

1. **A precise buyer profile.** "5–6 scientific books a year, 15 book types, no Word templates,
   replacing eXtyles, 4+5 named users" describes a niche we can serve commercially without a
   tender: medical/scientific publishers and UN agencies with the same eXtyles-shaped problem.
2. **A build spec** for a Word-native BITS 2.0 packager — a product we could sell per seat, not a
   bespoke tender response.
3. **A relationship.** A one-paragraph note offering to be consulted on the Word-template work
   they said "may be considered" keeps a door open at zero cost.

## If the user overrides and wants a bid anyway

Before 12:00 CEST tomorrow we would need, from the user, in writing:

* legal entity name, country, incorporation date, VAT/tax status, three years of turnover;
* confirmation that a **working Word add-in** can be demonstrated on 2–4 Nov (not a mock-up);
* acceptance of the 120-day validity and the IARC general conditions (document 02-LETTER).

Without those three, any TECH file we produce is a document we cannot stand behind.
