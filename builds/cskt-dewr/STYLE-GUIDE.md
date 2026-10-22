# CSKT Division of Engineering & Water Resources (DEWR) — Digital Brand & Website Style Guide Starter

Prepared for **Section 4.5 (Branding & Visual Identity)** of the CSKT DEWR Website Design & Development RFP (due October 29, 2026). All final palette, cultural motifs, photography rules, and typography choices are subject to review and approval by DEWR and CSKT leadership.

## 1. Visual Identity Direction
Inspired by the waters, conifer watersheds, and bedrock valleys of the Flathead Indian Reservation, balancing scientific/engineering clarity with warmth and accessibility:

| Token | Hex | Intended Usage | Contrast on `#FFFFFF` | WCAG Rating |
|---|---|---|---|---|
| `--ink` | `#0F2430` | Primary body copy, headings, footer ground | **15.8 : 1** | AAA |
| `--river` | `#0D4F6B` | Primary actions, active navigation, GIS map pins | **8.6 : 1** | AAA |
| `--pine` | `#164E3A` | Restoration & watershed badges, active timeline state | **9.4 : 1** | AAA |
| `--ochre` | `#84500C` | Public notice accents, version callouts | **6.4 : 1** | AA / AAA Large |
| `--paper` | `#F4F7F8` | Low-glare technical reading background | — | — |
| `--focus` | `#D97706` | High-visibility 3px keyboard focus outline | **3.2 : 1** non-text | WCAG 2.2 2.4.11 |

## 2. Typography & Readability Standards
- **Primary UI & Body Stack:** System native grotesque (`system-ui, -apple-system, "Segoe UI", Roboto, sans-serif`) for instant zero-FOIT rendering on rural mobile connections across Lake, Sanders, Missoula, and Flathead counties.
- **Scale:** `16px` root (`1rem`), `1.6` body line-height, `68–72ch` maximum line measure so complex hydrologic and Compact explanations stay scannable.
- **Heading Hierarchy:** Strict single `<h1>` per page followed sequentially by `<h2>` and `<h3>` sections with zero skipped heading levels.

## 3. Reusable CMS Page Templates & Block Library
1. ** Emergency / Public Meeting Banner Block** — Toggleable sitewide banner with expiration date and keyboard dismiss control.
2. **Audience Router Grid** — Direct pathways for Tribal Members, Water Users/Allottees, Community/Educators, Partner Agencies, Contractors, Media, and Prospective Employees.
3. **Interactive Before/After Restoration Block** — Two DEWR-approved photographs + alt descriptions rendered as a keyboard/touch range slider with zero third-party JS dependencies.
4. **ArcGIS Online & StoryMaps Embed Block** — Validated HTTPS `arcgis.com` embed wrapper with mandatory accessible `title`, full-screen external link, and plain-language summary fallback.
5. **Versioned Document Library Entry** — Structured taxonomy (`Category`, `Program`, `Publication Year`, `Version`, `File Size`, `Summary`) replacing unindexed PDF folders.
6. **Staff Directory & Career Card** — Role-managed custom post types so authorized staff update bios, contacts, and job openings without editing page layout code.
