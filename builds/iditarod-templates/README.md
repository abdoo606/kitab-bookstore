# Iditarod Historic Trail Alliance — Concept Templates (3)

Responsive concept templates prepared proactively for the Alliance's website
redesign Request for Proposals (issued October 1, 2026; proposals due
November 2, 2026). They implement the draft sitemap in RFP Attachment 1 for
three key templates so reviewers can judge actual work, not just claims:

- `index.html` — Homepage: "This is the INHT" visual story (Locations &
  Landscapes, Multiple Uses, History, Communities), Learn and About entry
  points, newsletter signup concept.
- `plan-a-trip.html` — Plan a Trip: maps placeholder with text alternative,
  Visitor Guide, Recreation Info, Passport Program, Auto Tour, Places to Visit.
- `get-involved.html` — Get Involved: Donate / Membership / Store calls to
  action, stewardship work, gateway communities, workshops, grants,
  volunteer-interest concept form.
- `SITEMAP.md` — the full proposed information architecture.

## Approach notes (summary)
- Semantic HTML, one shared header/footer, skip link, visible focus states,
  labelled form controls, `prefers-reduced-motion` support — a practical
  starting point toward the RFP's WCAG 2.2 AA target (full conformance
  requires testing with final content, media and CMS components).
- No external assets or tracking in these templates; works offline and on
  any static host for review. Final photography, copy and branding assets
  to be supplied/approved by the Alliance.
- Platform recommendation for the full build would be finalized in discovery
  (e.g., WordPress vs. an equivalent staff-friendly CMS) based on the
  required webstore, donations/membership with payment processing, donor
  data management and email integration.

## Explicitly NOT included in this concept package
CMS configuration, content migration, production webstore, payment
processing, donation/membership back-end, interactive map implementation,
analytics setup. Forms on these pages do not send or store any data.

## Content needs list (for the Alliance, if proceeding)
Final homepage story copy and photography for the four story themes;
segment-by-segment map data + text alternatives; visitor safety guidance;
Passport Program stop list; auto-tour stops/directions; gateway community
profiles; store product/photo list; staff & board bios; annual reports.

## Checks performed
Pages and assets served locally with HTTP 200; JavaScript syntax-checked;
templates reviewed at mobile and desktop widths; heading order and form
labels checked manually. No data collection occurs in this package.
