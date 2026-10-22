# CSKT Division of Engineering & Water Resources (DEWR) — Working Concept & Technical Blueprint

Prepared proactively by **Abdulrhman** (`abdulrhmant948@gmail.com` · `https://github.com/abdoo606`) in response to the public **CSKT Natural Resources Department — Division of Engineering & Water Resources (DEWR) Website Design & Development RFP** (Proposals Due: **October 29, 2026 at 4:30 p.m. MDT** to `Elizabeth.Dempsey@cskt.org`).

> **Disclaimer:** This folder is an unofficial demonstration prototype built specifically for DEWR proposal evaluation. All text, project metrics, document entries, and staff contacts are labelled sample placeholders. No data is collected or transmitted.

## Live Working Pages Included in This Prototype
1. **`index.html` — Home, Audience Router, Core Programs & Before/After Restoration Slider**
   - Top dismissible **Public Notice / Meeting Banner** (`Section 5.10`).
   - 7-Audience Quick Router (`Section 3.4`: Tribal Members, Water Users/Irrigators/Allottees, Community & Educators, Partner Agencies, Contractors, Media, Prospective Employees).
   - **Accessible Interactive Before-and-After Restoration Slider** (`Sections 4.6 & 5.7`) operable by touch, mouse, or keyboard arrows.
2. **`projects-gis.html` — Interactive Watershed Map, ArcGIS StoryMaps Hub & Compact Timeline**
   - Keyboard-navigable SVG basin locator synced with category filters and **ArcGIS Online / StoryMaps CMS embed slots** (`Sections 4.6, 5.7, 5.11`).
   - Tab-accessible **CSKT–Montana Water Compact Educational Timeline** (`Section 5.7`).
3. **`documents.html` — Searchable Document Library, Staff Directory, Careers & Public Comment Form**
   - Instant keyword + category + year filterable **Document Library** with version and file-size metadata (`Sections 5.6 & 5.8`).
   - Program-filterable **Staff Directory** & **Career Opportunities** (`Section 5.14`).
   - Accessible **Public Comment & Meeting RSVP Form** preview (`Section 5.9`).
4. **`STYLE-GUIDE.md` — DEWR Digital Brand & Website Style Guide Starter (`Section 4.5`)**
   - Documented AAA/AA color tokens, typography scale, and reusable Gutenberg CMS block specs.

## Recommended CMS & Ownership Model (`Sections 5.1 & 5.13`)
- **Open-Source WordPress 6.x (Custom Lightweight Block Theme, Zero Page-Builder Lock-In):**
  - `$0` proprietary CMS license fee; Custom Post Types (`dewr_project`, `dewr_document`, `dewr_notice`, `dewr_staff`, `dewr_job`) + clean Gutenberg blocks so DEWR staff create/update pages, documents, notices, ArcGIS embeds, and before/after sliders without HTML/code.
  - **100% CSKT Ownership:** Domain (`csktwatercompact.com`), hosting account, SSL, GA4 property, Git repository, and Digital Style Guide belong strictly to CSKT DEWR from day one.

## Honest Solo-Developer Disclosure
- I am an independent solo developer (`github.com/abdoo606`), **not** a multi-person agency, hold **no CSKT Indian Preference certification (`0 / 10 IPO points`)**, and **do not claim three prior paid government client references** (`Section 7.10`) — I will never invent references.
- Instead, I built this working DEWR prototype upfront so your selection committee can inspect real accessible code, GIS/document UX, and fixed-milestone pricing directly before committing a single dollar.
