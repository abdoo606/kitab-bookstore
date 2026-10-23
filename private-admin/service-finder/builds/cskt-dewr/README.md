# CSKT DEWR — Working Website Concept

**Unofficial prototype** prepared by Abdulrhman (`github.com/abdoo606`) in response to the
Confederated Salish and Kootenai Tribes' **Division of Engineering & Water Resources (DEWR)**
Website Redesign & Development Services RFP — **updated for Questions & Answers Addendum #1
(published October 22, 2026)**.

> This is a design and behaviour demonstration built with static HTML/CSS/JS and clearly labelled
> `[Sample]` data. It is **not** a WordPress installation, is **not** connected to any CSKT or DEWR
> system, and is **not** an official CSKT publication.

## Pages

| File | Purpose | Addendum #1 items demonstrated |
| --- | --- | --- |
| `index.html` | Home, audience routing, site-wide search, before/after slider | Q18, Q27–Q29, Q35, Q30 |
| `projects-gis.html` | Maps and Data hub, project explorer, Compact timeline, data inventory | Q24–Q26, Q35 |
| `documents.html` | Document library, PDF full-text search, staff directory, careers, technical notes | Q18, Q13/Q17, Q33, Q19–Q21 |
| `branding.html` | Three branding concepts, reserved Seal zone, Salish/Ksanka typography | Q27–Q29, Q35 |
| `get-involved.html` | Meetings calendar, public comment form, newsletter, Seth Bot | Q30–Q33, Q48 |

## Addendum #1 coverage — what is actually implemented

**Q1 / Q19 / Q20 / Q21 — CMS and hosting.** The proposal targets **WordPress 6.x on CSKT's managed
WP Engine** account at **$0 hosting cost** in the base price. Elementor is not required and not used.
GoDaddy DNS/SSL coordination with CSKT IT is scheduled **five business days before launch**. The
custom theme is released under **GPLv2 or later**. This prototype shows the page/template patterns
that the WordPress theme reproduces; it is not itself WordPress.

**Q13 / Q17 — Migration and remediation counts.** `documents.html` states the exact scope:
**33 published pages, 3 private pages, 359 media files** (199 images, 133 documents, 27 other), with
legacy PDF tagging/remediation priced separately at **$12 per PDF**.

**Q16 / Q18 — Accessibility and search.** Skip link, visible focus rings, semantic landmarks, ARIA
live regions on every dynamic update, keyboard-operable slider/map/timeline/forms, and a search
engine that indexes page copy, document metadata, **and the extracted text of each PDF page**, then
reports the matching page number. WCAG 2.1 AA is the floor; 2.2 AA is the target. No certification is
claimed here — conformance is proven by audit during the project.

**Q24–Q26 — Maps and Data hub.** Four explicit categories: *Interactive Maps*, *Water Resources and
Data*, *Project Maps*, *ArcGIS StoryMaps*. All ArcGIS publishing happens inside **DEWR's own ArcGIS
Online organisation** via the DEWR GIS Analyst; the contractor never holds an org login, API key, or
editing seat, and embeds degrade to a titled link.

**Q27–Q29 — Branding, Seal, language.** Three concepts (A unified NRD identity, B coordinated
three-division system, C watershed/Compact system), each with rationale, best-fit use case, honest
trade-off, and palette. The **official CSKT Seal is never redrawn** — only a reserved, correctly
proportioned placement zone, with DEWR → **CSKT Culture Committees** approval recorded per asset.
Salish (`Séliš / Ql̓ispé`) and Ksanka (`Ktunaxa`) render as real Unicode with combining marks and
correct `lang` attributes for screen readers.

**Q30–Q33 — Engagement.** Newsletter with topic groups and double opt-in; public comment form that
**locks itself at the published deadline**, validates PDF/DOCX attachments (25 MB), issues a
reference number, auto-acknowledges, notifies staff, and exports CSV in one click; a simple meetings
and open-houses calendar that keeps past meetings published; and job summaries that hand applications
to the **official CSKT Personnel Office**.

**Q35 — Imagery policy.** **Zero stock photographs. Zero AI-generated imagery.** Every illustration is
original inline SVG authored for DEWR. Photograph positions are labelled placeholders awaiting
DEWR-supplied images with documented rights and approval.

**Q48 — "Seth Bot".** A source-cited Water Compact Q&A demonstration: answers only from
DEWR-approved sources, prints the citation and page, refuses to answer when no approved passage
matches, and carries a permanent non-legal-advice notice. Optional and separately priced.

## Honest limitations

- Static prototype with sample data; not a WordPress install and not connected to DEWR systems.
- No accessibility certification is claimed.
- No real ArcGIS layers, hydrology feeds, Tribal records, staff contacts, or vacancies.
- No prior paid Tribal government contracts and no three-agency reference list are claimed.
- No Indian Preference certification (0 of 10 optional points claimed).

## Run it

```bash
cd builds/cskt-dewr
python3 -m http.server 8080
# open http://localhost:8080/index.html
```

No build step, no dependencies, no tracking, no cookies, no network requests.

## Files

```
index.html            Home, search, before/after slider, newsletter
projects-gis.html     Maps and Data hub, project explorer, Compact timeline
documents.html        Document library, PDF search, staff, careers, technical notes
branding.html         Three branding concepts, Seal zone, language support
get-involved.html     Meetings, public comment, newsletter, Seth Bot
assets/dewr-data.js   Sample content + search corpus + Q&A corpus
assets/main.js        Accessible progressive enhancement (no dependencies)
assets/styles.css     Design tokens and components (WCAG-checked palette)
STYLE-GUIDE.md        Brand, colour, type, component and content rules
DEWR-Website-Proposal-Abdulrhman-Addendum1.pdf   Updated written proposal
```
