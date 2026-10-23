# DEWR Digital Brand & Website Style Guide — Starter

Version 2.0 · updated for **DEWR RFP Questions & Answers Addendum #1 (October 22, 2026)**
Status: **DRAFT — awaiting DEWR review and CSKT Culture Committee approval.**

> This guide is a proposal, not an adopted brand. Every rule below is subject to DEWR approval, and
> any cultural element is subject to review by the CSKT Culture Committees before publication.

---

## 1. Colour tokens

| Token | Hex | Use | Contrast on white |
| --- | --- | --- | --- |
| `--ink` | `#0F2430` | Body text, headings | **15.8:1** (AAA) |
| `--river` | `#0D4F6B` | Primary brand, links, headings | **8.6:1** (AAA) |
| `--river-dark` | `#083549` | Hover/active, dark panels | 12.4:1 (AAA) |
| `--pine` | `#164E3A` | Secondary brand, success states | **9.4:1** (AAA) |
| `--ochre` | `#84500C` | Attention/callout borders | 6.5:1 (AA+) |
| `--muted` | `#425460` | Secondary text on `#F4F7F8` | **7.1:1** (AAA) |
| `--paper` | `#F4F7F8` | Page background | — |
| `--border` | `#CBD8DF` | Dividers, card borders | — |
| `--focus` | `#D97706` | Focus ring (3px, 3px offset) | 3.4:1 against white |

**Rules**

- Never place body text on a mid-tone without checking contrast; minimum **4.5:1**, target **7:1**.
- Colour is never the only carrier of meaning — pair it with text, an icon, or a pattern.
- The Seal is never recoloured, tinted, or used as a background watermark.

## 2. Typography

- **Body:** system UI stack (`system-ui, -apple-system, "Segoe UI", Roboto, Arial, sans-serif`) —
  zero webfont cost and instant rendering on rural cellular connections.
- **Scale:** 16px base · 1.25 ratio · body line-height 1.6 · headings 1.25–1.3.
- **Measure:** 60–75 characters per line.
- **Salish (`Séliš / Ql̓ispé`) and Ksanka (`Ktunaxa`):** rendered from a Unicode-complete fallback
  stack (`Noto Sans`, `Gentium Plus`, `Charis SIL`) with the correct `lang` attribute
  (`lang="sal"`, `lang="kut"`). No ASCII substitution is ever used for a glottal stop or a barred
  character. A licensed webfont is only embedded once DEWR confirms licensing.
- **Never** render Salish or Ksanka words in all-caps — case conversion can break combining marks.

## 3. Logo and Seal policy (Q27–Q29)

### 3.1 Three concept directions

| | Concept A · Unified NRD | Concept B · Three-division system | Concept C · Watershed/Compact |
| --- | --- | --- | --- |
| Structure | One department mark + division name line | Three related marks + shared signature bar | Contour motif + flexible division band |
| Strength | Consistency, lowest maintenance | Division-specific recognition | Compact and watershed storytelling |
| Trade-off | Quieter division identity | More governance and rules | Decorative, must never look like a real map |
| Best fit | Department-wide pages | Program campaigns and advisories | csktwatercompact.com as Compact home |

Evaluation criteria: recognisability at 24px, one-colour performance, behaviour beside the Seal, and
how easily DEWR staff can apply it without a designer.

### 3.2 Official CSKT Seal

- **Never** redraw, trace, recolour, crop, rotate, or approximate the Seal. Use only the official
  artwork file supplied by DEWR.
- **Approved placements:** site footer, About the Tribes page, formal public-notice documents.
- **Not permitted** without written authorisation: social graphics, merchandise, program badges,
  slideshow backgrounds, watermarks.
- **Clear space:** minimum 1× seal height on all sides. No text overlay, gradient, or photo behind it.
- **Alt text:** fixed wording approved by DEWR, not improvised per page.
- **Minimum size:** defined per medium so the seal never renders as an illegible thumbnail.

### 3.3 Cultural review gate

1. Draft asset → 2. DEWR review → 3. CSKT Culture Committee review → 4. Approved & published.
Status is recorded per asset in the CMS. Nothing bypasses step 3. The contractor never contacts
Culture Committees, Elders, or Tribal members directly — all traffic goes through DEWR.

## 4. Imagery and illustration policy (Q35)

- **No stock photography. No AI-generated imagery.** Not for land, water, people, or cultural material.
- **Original vector diagrams only** in the prototype: inline SVG, authored for DEWR, no third-party assets.
- Live-site photographs must be **DEWR-supplied** with recorded source, permission, and photographer credit.
- Photograph slots are labelled placeholders stating exactly what is needed and who approves it.
- Identity of any recognisable person requires a documented release.
- Icons are simple geometry — never traced cultural symbols, petroglyph reproductions, or beadwork patterns.

## 5. Components

- **Card:** 1px `--border`, 10px radius, 20–24px padding, single primary action.
- **Button:** primary (`--river` fill, white text), outline (`--river` border), ghost-light (on dark banners only). Minimum 44×44px target.
- **Form field:** 2px border `#8FA8B5`, 8px radius, `<label>` always visible (never placeholder-only), inline hint text, error summary announced with `role="alert"`.
- **Callout / gate box:** 6px left border in `--ochre` (policy), `--river` (technical), or `--pine` (approval/process).
- **Result item:** type badge (`Page` / `PDF`), title link, metadata line, matched snippet with `<mark>`, and the **PDF page number** when the hit came from inside a document.
- **Embed slot:** fixed aspect ratio, dashed border when empty, caption + “open in new tab” link when live.

## 6. Writing style

- Plain language at roughly an 8th-grade reading level; define technical terms once, in place.
- Active voice. “DEWR publishes the map”, not “the map is published by DEWR”.
- State deadlines with date, time, and time zone, and say what happens after the cutoff.
- Every sample or placeholder is prefixed `[Sample]` — never present invented data as real.
- Never claim a certification, partnership, prior client, or government affiliation that does not exist.

## 7. Accessibility contract

- WCAG **2.1 AA minimum**, **2.2 AA target**; Section 508 alignment.
- Keyboard operation for every interactive element; visible focus at all times.
- Skip link on every page; one `<h1>`; logical heading order.
- `aria-live="polite"` on search results, filter counts, form outcomes, and timeline changes.
- Forms: explicit labels, described-by hints, error summary, and no time-limited input without warning.
- `prefers-reduced-motion` disables animation; nothing auto-plays.
- Tested with automated tooling **and** manual keyboard + screen-reader passes before launch — the prototype does not claim conformance on its own.

## 8. Content ownership

CSKT DEWR owns the domain, the WP Engine hosting account, the WordPress database, the theme and
plugin code (GPLv2+), the style guide, the Figma/design source files, and all documentation. Nothing
is hosted, licensed, or held by the contractor after handover.
