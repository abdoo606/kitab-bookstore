# Memory Studies Association — Working Concept + Proposal Notes

Prepared proactively by Abdulrhman (independent web developer, GitHub `abdoo606`) in response to the Association's public call **“Web Designer/Developer Needed for International Non-Profit Association Website”** (posted 28 Sep 2026; applications to info@memorystudiesassociation.org with subject “website development” by **1 November 2026**). This folder is an unofficial concept: placeholder copy, invented sample events, no real login/payment/mailing, no data collected.

## What you can click through here
- `index.html` — Home + About pattern: announcements that can feed a newsletter, membership value, GDPR/EU-hosting/WCAG signals.
- `events.html` — Public events agenda + archive with **working year filter and text search** over labelled sample data (`assets/events-data.js` = the future CMS content type).
- `membership.html` — Dues tiers/donations placeholders, a **members-only area demo** (panel reveal, no auth in concept), double-opt-in newsletter concept, and the conference-tooling recommendation.
- Shared `assets/styles.css` (design system starter) + `assets/main.js`. Accessibility basics included: skip link, landmarks, labelled controls, visible focus, reduced-motion respect, semantic headings/time elements.

## Recommended platform (and why)
**WordPress on EU-based hosting, rebuilt cleanly — keeping your existing membership approach rather than replacing it blindly.**
- Your current site already runs WordPress with a membership plugin (Paid Memberships Pro cookies are visible today), so member accounts/levels can be migrated instead of re-created for ~1,500 members.
- Membership/dues/donations: membership plugin levels + an EU-friendly payment processor (cards + iDEAL for NL members; SEPA where useful). Dues bands by career stage/country are configuration, not custom code. Automated receipts + renewal reminders.
- Mail campaigns: EU-based newsletter provider under a data-processing agreement (double opt-in, consent records, segments synced from membership levels/interests — no CSV juggling).
- Members-only content/events: level-based content rules + event registration for online seminars; profile/consent/data-export-erasure self-service for GDPR rights.
- Conference: **keep specialist conference software (e.g. Dryfta)** for submissions/review/registration/payments/programme; the website links to it cleanly. Rebuilding that inside WordPress before 1 July 2027 would be the main schedule/budget risk. Optional later SSO only if the platform supports it properly.
- GDPR/WCAG/security: EU hosting + EU subprocessors list, consent-managed embeds/analytics (or EU-hosted analytics), backups/updates/2FA/least-privilege roles, WCAG 2.2 AA-oriented templates + staff guidance (templates help; final compliance also depends on content practices — training covers this).

## Answers to “What We’d Like From You”
- **Relevant experience (honest):** I am an independent (solo) developer. I do **not** claim past client work for associations and I have **no client references to offer** — the call does not require references, and I will not invent any. What I can show is working code built for exactly these patterns (membership-style gated content, searchable directories/archives, event listings, accessible templates):
  - This MSA concept (agenda + archive filters, members-area demo).
  - Canadian Club of Ottawa concept — 7-page association/club template set with events archive: https://github.com/abdoo606/kitab-bookstore/tree/arena/78ba5633-kitab-bookstore/private-admin/service-finder/builds/canadian-club-ottawa
  - Searchable/filterable directory demo: https://github.com/abdoo606/kitab-bookstore/tree/arena/78ba5633-kitab-bookstore/private-admin/service-finder/builds/cd-municipal-directory
  - Independent full-stack sample (React/TypeScript + Node/PostgreSQL, login + role-based CRUD): https://github.com/abdoo606/hospital-website/tree/arena/cbc41b37-hospital-website/services/fullstack-milestone
  All samples are independent builds, not paid client sites. Please judge the code itself.
- **Development cost estimate (fixed, phased):**
  - **Phase A — USD 750 fixed:** design system + production-ready template set (Home, About, Announcements/Events agenda + archive, Membership/dues, Members area, Conference front-door, Contact/legal patterns) + platform & migration blueprint (hosting, plugins, payments, mail, GDPR checklist). 12 working days after brand/content access; 2 revision rounds. (This concept is the starting point, so Phase A is largely de-risked.)
  - **Phase B — implementation, fixed after Phase A (indicative USD 1,900–2,900):** WordPress build on EU hosting, membership/payment/mail configuration, content migration for agreed scope, redirects, testing, launch. The range depends mainly on migration volume and the Dryfta/SSO decision; the fixed number is confirmed in writing before Phase B starts — no hourly meter running.
- **Subsequent annual platform costs (at cost, paid by MSA directly to providers; estimates):** EU hosting ~€120–€300/yr; domain ~€15/yr; membership/newsletter licences ~€0–€400/yr depending on tiers/list size; payment-processor transaction fees per payment. No markup from me on platform costs.
- **Timeline to launch before 1 July 2027 (solo-safe milestones):** Dec 2026 — Phase A templates for design approval; Jan–Feb 2027 — approved-design WordPress build + membership/payment/mail setup on staging; Mar–Apr 2027 — content migration + member-account migration test + staff tryout; May 2027 — accessibility/GDPR checks, training, fixes; Jun 2027 — launch window (buffer before 1 July).
- **Maintenance availability + outline costs:** Available after launch. Either USD 45/hour ad-hoc (30-min minimum, agreed estimates first) or a small USD 120/month retainer (updates, backups checks, uptime/security monitoring, small content-structure tweaks; larger work quoted fixed). You keep full admin access and exports — no lock-in to me.
- **Training:** Yes — two live online sessions for your non-technical team (publishing, events, members, mailings) + short written guides with screenshots, included in Phase B.

## Limits stated upfront
Solo delivery (no agency team), English working language, EU providers to be contracted by MSA (I configure; accounts/data stay yours), GDPR roles/DPA to be agreed in writing before any personal-data migration, and conference-platform internals stay with that platform. If MSA needs a multi-person agency with client references, this proposal will not fit — please disregard it. If a small, fixed-price, code-first build does fit, I would be glad to discuss details.

Contact: Abdulrhman — abdulrhmant948@gmail.com — github.com/abdoo606
