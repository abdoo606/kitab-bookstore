# C&D Municipal Sales — Directory Concept Demo

A working front-end concept built proactively against the public project
specification (WordPress redesign + dynamic manufacturer directory, posted
October 19, 2026). It demonstrates the core behaviour the spec asks for —
before any WordPress work begins:

- **Manufacturer directory** rendered from structured records (one card per
  record), with live text search + equipment-category filter.
- **Equipment category templates** that list related manufacturers
  automatically from the same records.
- Site sections per spec: Home, Manufacturers, Equipment/Products,
  Resources (line card; catalogs stay on manufacturer sites), News/Insights
  (structured for a future Project Gallery), About/Team, Contact with a
  spam-protected form concept.

All manufacturer records here are **invented samples**. Real names, logos
and line-card data would come from the client.

## How this maps to the WordPress build
| Demo element | WordPress equivalent |
|---|---|
| `assets/data.js` records | Custom Post Type `manufacturer` |
| name/logo/description/website | ACF fields per record |
| categories / applications | Taxonomies `equipment_category`, `application` |
| Directory grid + filters | Archive template + facet filter (preselected free/core approach preferred) |
| Equipment category blocks | Taxonomy templates querying related manufacturers |
| Staff editing this file | **Nobody does in production** — staff use wp-admin only |

Recommended stack for the proposal: Gutenberg + custom blocks (or Bricks)
with ACF-driven templates, deployed to the client's existing IONOS WordPress
hosting via staging → production with backup/rollback, DNS/email untouched,
full admin access handed over, premium-license costs disclosed up front.
Performance/accessibility/SEO per spec: responsive layouts, WCAG 2.2 AA
fundamentals, editable titles/meta, XML sitemap, redirects for changed URLs,
GA4 + Search Console if access is provided, one live/recorded training
session plus short written guides, 30-day post-launch defect warranty.

## Checks performed
Served locally (all assets HTTP 200), JavaScript syntax-checked, directory
search/filter/category behaviour exercised, mobile navigation checked.
Contact form sends nothing in this concept; production delivery requires
wiring + a real in-box delivery test, which the proposal should name as a
launch checklist item.
