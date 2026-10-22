# Canadian Club of Ottawa — Website Redesign: Working Concept + Scoped Response Notes

Prepared proactively by an independent web developer in response to the Club's public
**Request for Proposals: Website Redesign** (published October 2, 2026; proposals by email to
admin@canadianclubottawa.ca by **11:59 PM, Wednesday, October 21, 2026**).

This folder is a **working concept sample**, not the finished website and not a full
compliant proposal. It exists so reviewers can judge actual templates and behaviour
instead of claims. Final visual design must follow the Club's refreshed brand identity
(separate RFP), so identity here is deliberately placeholder.

## What's in the concept (mapped to your 7 core pages)
- `index.html` — **Home** + **About/History** section: next-event card fed from the
  events data (in production: from the CMS), membership pathways, season overview.
- `events.html` — **Upcoming Events** listing (auto-sorted, registration buttons that
  would link to your existing ticketing platform) and **Past Events/Archive** with
  working year filter + text search over clearly-invented sample data
  (`assets/events-data.js`).
- `membership.html` — **Membership** tiers (placeholder prices), **Sponsorship** block,
  and **Contact** form concept (labelled fields, honeypot field; sends nothing).

Accessibility basics included: skip link, landmarks, labelled controls, visible focus,
`aria-current`, live-region result count, reduced-motion respect, responsive layout.

## Recommended production approach (summary)
- **CMS: WordPress** with a lightweight block theme — staff update pages and events
  without developer help; an *Events* custom post type drives Home “next event”,
  listings and the archive automatically. Ticketing stays on your existing platform
  via clear outbound links (no payment data on the site).
- **Content migration:** inventory current pages, migrate agreed core content,
  retire/redirect the rest with a redirect map; the existing site stays live until
  the replacement is tested and approved (per your RFP).
- **SEO/analytics:** editable titles/meta, XML sitemap, GA4 if you provide access.
- **Testing/handover:** cross-device checks, keyboard/screen-reader pass on key
  templates, one recorded staff training session + short written guides.

## Timeline fit with your schedule
Discovery/structure Nov–Dec 2026 → design after brand approval (Q1 2027) →
development + migration Mar–May 2027 → testing/training/launch Jun 2027.
The scoped phase below can run inside that schedule without disrupting the season.

## Scoped offer (Phase A) — itemized fixed price
**USD 600 fixed** for: design system + all 7 core templates delivered as working,
accessible HTML/CSS/JS ready to become the WordPress theme — 10 working days after
approved brand assets + agreed content, 2 revision rounds, source files included.
Phased payment welcomed (e.g. 50% start / 50% approval). **Phase B** (WordPress
build-out, content migration, training, launch support) quoted as a fixed price after
Phase A discovery, so the Club commits in stages. Hosting/domain/platform licences
are the Club's direct costs and excluded; no recurring fee is charged by me unless
separately agreed.

## Honest disclosures (please weigh accordingly)
- I am an **independent developer**, not an agency, and I **do not have two client
  references** to provide. Instead of dressing up samples, my public work is open
  for inspection: this concept, plus independent builds on GitHub (account
  `abdoo606`) — all clearly labelled as samples, not client work.
- If a fully compliant proposal with references is required, please treat this
  package as an evaluation sample only and disregard it as a bid.
- Content, photography, final copy, membership/ticketing accounts and brand assets
  come from the Club; anything not listed above is out of scope until quoted.

## Checks performed on this concept
JavaScript syntax check; served locally and verified every page/asset returns
HTTP 200; events listing, year filter, search and concept-form behaviour exercised
in code review. No analytics, cookies or data collection are present in the sample.
