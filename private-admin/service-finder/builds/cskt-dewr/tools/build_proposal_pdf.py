#!/usr/bin/env python3
"""
Builds DEWR-Website-Proposal-Abdulrhman-Addendum1.pdf

Generates the Addendum #1 supplement to the CSKT DEWR Website Redesign proposal.
Deterministic, no network access, no external assets.

Usage:  python3 tools/build_proposal_pdf.py
"""
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether, ListFlowable, ListItem,
)

OUT = "DEWR-Website-Proposal-Abdulrhman-Addendum1.pdf"

INK = colors.HexColor("#0F2430")
RIVER = colors.HexColor("#0D4F6B")
RIVER_DARK = colors.HexColor("#083549")
PINE = colors.HexColor("#164E3A")
OCHRE = colors.HexColor("#84500C")
PAPER = colors.HexColor("#F4F7F8")
BORDER = colors.HexColor("#CBD8DF")
MUTED = colors.HexColor("#425460")

ss = getSampleStyleSheet()


def st(name, **kw):
    base = dict(fontName="Helvetica", fontSize=9.6, leading=13.4, textColor=INK,
                spaceAfter=4, alignment=TA_LEFT)
    base.update(kw)
    return ParagraphStyle(name, **base)


H1 = st("H1", fontName="Helvetica-Bold", fontSize=15.5, leading=19, textColor=RIVER,
        spaceBefore=2, spaceAfter=7)
H2 = st("H2", fontName="Helvetica-Bold", fontSize=11.4, leading=14.4, textColor=RIVER_DARK,
        spaceBefore=10, spaceAfter=4)
H3 = st("H3", fontName="Helvetica-Bold", fontSize=10, leading=13, textColor=PINE,
        spaceBefore=7, spaceAfter=3)
BODY = st("Body", spaceAfter=5)
SMALL = st("Small", fontSize=8.3, leading=11.2, textColor=MUTED, spaceAfter=3)
LEAD = st("Lead", fontSize=10.4, leading=14.6, textColor=INK, spaceAfter=6)
COVER_T = st("CoverT", fontName="Helvetica-Bold", fontSize=23, leading=27, textColor=RIVER_DARK,
             spaceAfter=8)
COVER_S = st("CoverS", fontSize=11.4, leading=15.4, textColor=MUTED, spaceAfter=10)
TBL = st("Tbl", fontSize=8.2, leading=10.6, spaceAfter=0)
TBLB = st("TblB", fontName="Helvetica-Bold", fontSize=8.2, leading=10.6, spaceAfter=0)
TBLH = st("TblH", fontName="Helvetica-Bold", fontSize=8.2, leading=10.6,
          textColor=colors.white, spaceAfter=0)


BULLET = st("Bullet", fontSize=9.6, leading=13.2, leftIndent=15, firstLineIndent=-10,
            spaceAfter=3.2)


def bullets(items, style=BULLET, bullet_char="\u2022", indent=15):
    """Bullets rendered as inline glyphs so they always render and always extract."""
    return [Paragraph(f"{bullet_char}&nbsp;&nbsp;{i}", style) for i in items]


def table(rows, widths, header=True, zebra=True, valign="TOP"):
    data = []
    for r_i, row in enumerate(rows):
        line = []
        for cell in row:
            if isinstance(cell, tuple):  # (text, style) override
                line.append(Paragraph(cell[0], cell[1]))
            else:
                line.append(Paragraph(cell, TBLH if (header and r_i == 0) else TBL))
        data.append(line)
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    cmds = [
        ("VALIGN", (0, 0), (-1, -1), valign),
        ("GRID", (0, 0), (-1, -1), 0.4, BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 4.5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4.5),
        ("TOPPADDING", (0, 0), (-1, -1), 3.6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.6),
    ]
    if header:
        cmds += [("BACKGROUND", (0, 0), (-1, 0), RIVER),
                 ("LINEBELOW", (0, 0), (-1, 0), 0.8, RIVER_DARK)]
    if zebra:
        for i in range(1 if header else 0, len(rows)):
            if i % 2 == 0:
                cmds.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#F7FAFB")))
    t.setStyle(TableStyle(cmds))
    return t


def callout(title, lines, accent=OCHRE):
    body = [Paragraph(f"<b>{title}</b>", st("coT", fontName="Helvetica-Bold", fontSize=9.4,
                                            leading=12.4, textColor=INK, spaceAfter=3))]
    body += [Paragraph(l, st("coB", fontSize=8.9, leading=12, spaceAfter=2.5)) for l in lines]
    t = Table([[body]], colWidths=[6.9 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFF8EC")),
        ("LINEBEFORE", (0, 0), (0, -1), 3.2, accent),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("BOX", (0, 0), (-1, -1), 0.4, BORDER),
    ]))
    return t


def header_footer(canvas, doc):
    canvas.saveState()
    if doc.page > 1:
        canvas.setFillColor(RIVER)
        canvas.rect(0, LETTER[1] - 0.42 * inch, LETTER[0], 0.42 * inch, stroke=0, fill=1)
        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica-Bold", 7.6)
        canvas.drawString(0.62 * inch, LETTER[1] - 0.27 * inch,
                          "CSKT DEWR — Website Design & Development Proposal · Addendum #1 Response")
        canvas.setFont("Helvetica", 7.6)
        canvas.drawRightString(LETTER[0] - 0.62 * inch, LETTER[1] - 0.27 * inch,
                               "Abdulrhman · Independent Developer")
    canvas.setStrokeColor(BORDER)
    canvas.setLineWidth(0.4)
    canvas.line(0.62 * inch, 0.62 * inch, LETTER[0] - 0.62 * inch, 0.62 * inch)
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 7.4)
    canvas.drawString(0.62 * inch, 0.44 * inch,
                      "Submitted to Elizabeth.Dempsey@cskt.org · Deadline Oct 29, 2026, 4:30 p.m. MDT")
    canvas.drawRightString(LETTER[0] - 0.62 * inch, 0.44 * inch, f"Page {doc.page}")
    canvas.restoreState()


def build():
    doc = BaseDocTemplate(OUT, pagesize=LETTER,
                          leftMargin=0.62 * inch, rightMargin=0.62 * inch,
                          topMargin=0.72 * inch, bottomMargin=0.78 * inch,
                          title="DEWR Website Design & Development — Addendum #1 Response",
                          author="Abdulrhman",
                          subject="CSKT DEWR Website Redesign RFP — Supplement for Questions & Answers Addendum #1",
                          creator="Abdulrhman")
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=header_footer)])

    S = []

    # ------------------------------------------------------------------ COVER
    S.append(Spacer(1, 0.35 * inch))
    S.append(Paragraph("CONFEDERATED SALISH AND KOOTENAI TRIBES", st(
        "cov1", fontName="Helvetica-Bold", fontSize=9.4, leading=12, textColor=OCHRE, spaceAfter=3)))
    S.append(Paragraph("Natural Resources Department · Division of Engineering &amp; Water Resources (DEWR)",
                       st("cov2", fontSize=9.4, leading=12, textColor=MUTED, spaceAfter=16)))
    S.append(Paragraph("DEWR Website Redesign &amp; Development", COVER_T))
    S.append(Paragraph("Proposal — Addendum #1 Response &amp; Scope Update", COVER_T))
    S.append(Spacer(1, 0.1 * inch))
    S.append(Paragraph(
        "A fully updated response to the DEWR Questions &amp; Answers Addendum published October 22, 2026 — "
        "including the three required branding concepts, the dedicated Maps and Data hub, searchable PDF text in the "
        "base scope, a deadline-locked public comment workflow, and a revised fixed price of <b>$5,400 USD</b> with "
        "<b>$0 hosting cost</b> on CSKT's managed WP Engine account.", COVER_S))
    S.append(Spacer(1, 0.18 * inch))

    cover_rows = [
        ["RFP solicitation", "CSKT DEWR Website Redesign &amp; Development Services<br/>"
                             "<b>Deadline: Thursday, October 29, 2026, 4:30 p.m. MDT</b> (superseded by Addendum #1)"],
        ["Addendum responded to", "Questions &amp; Answers Addendum #1 — published October 22, 2026"],
        ["Designated contact", "Elizabeth Dempsey, Information &amp; Education Program Manager<br/>Elizabeth.Dempsey@cskt.org · 406-304-1079"],
        ["Proposer", "Abdulrhman — Independent Web Designer &amp; Full-Stack Developer (solo, remote)"],
        ["Contact", "abdulrhmant948@gmail.com · github.com/abdoo606"],
        ["Live working prototype", "Five-page accessible concept built specifically for DEWR (see Section 2)"],
        ["Indian Preference", "Non-IPO proposer — <b>0 of 10</b> optional Indian Preference points claimed"],
        ["Tax status", "<b>IRS Form W-8BEN</b> — non-U.S. individual contractor"],
        ["Base fixed price", "<b>$5,400 USD</b> (unchanged) · hosting <b>$0</b> on CSKT WP Engine"],
        ["Optional add-ons", "Seth Bot Q&amp;A <b>$950 USD</b> · legacy PDF remediation <b>$12 per PDF</b>"],
        ["Interview availability", "Virtual — <b>November 9–12, 2026</b>, any window in Mountain Time"],
        ["Submission date", "October 23, 2026 (remote delivery, single PDF as required)"],
    ]
    S.append(table(cover_rows, [1.85 * inch, 5.05 * inch], header=False, zebra=True))

    S.append(Spacer(1, 0.22 * inch))
    S.append(callout("What changed since the October 21 submission", [
        "Addendum #1 answers 55 questions and materially changes five things: hosting moves to CSKT's own WP Engine "
        "(so hosting is $0), the migration volume is now a fixed number (33 published pages, 3 private pages, "
        "359 media files), PDF full-text search is required in the base scope, three branding concepts are required "
        "rather than one, and the deadline moved to <b>October 29, 2026 at 4:30 p.m. MDT</b>.",
        "This document supersedes the written proposal submitted October 21, 2026. The price did not increase: every "
        "newly required item is either already in scope or mapped to an explicitly optional line item.",
    ], accent=RIVER))

    S.append(PageBreak())

    # ------------------------------------------------------- 1. COMPLIANCE MATRIX
    S.append(Paragraph("1. Addendum #1 Response Matrix", H1))
    S.append(Paragraph(
        "Each row states what the addendum asked for and what this proposal commits to. Items marked "
        "<b>Included</b> are inside the $5,400 fixed price; items marked <b>Optional</b> are separately priced and "
        "may be declined without affecting the base scope.", LEAD))

    rows = [
        ["#", "Addendum requirement (paraphrased)", "Commitment in this proposal", "Price"],
        ["Q1", "Website platform must be WordPress on CSKT-managed WP Engine.",
         "WordPress 6.x block theme deployed to the CSKT WP Engine account. No other host is proposed.", "Included"],
        ["Q2", "Cost evaluated on a 10/100 base-point scale, priced in USD.",
         "$5,400 USD fixed, itemised in Section 6 of this document.", "Included"],
        ["Q3/Q4", "Single-owner and remote firms are eligible.",
         "Solo independent developer, fully remote (UTC+3), overlapping Mountain Time mornings daily.", "—"],
        ["Q5/Q55", "No minimum firm size, tenure, or revenue; international firms eligible.",
         "Non-U.S. individual contractor filing IRS Form W-8BEN. No size or tenure threshold is met by design.", "—"],
        ["Q6", "Indian Preference is optional; IPO certification is not required.",
         "0 of 10 optional points claimed. No certification is asserted, and no false claim is made.", "—"],
        ["Q9", "The Tribe pays the 3% CSKT contracting fee.",
         "Acknowledged. The 3% is paid by DEWR and is not loaded into the proposal price.", "—"],
        ["Q11", "General liability insurance after selection, before work begins.",
         "Certificate provided on selection and before the first billable hour; not a proposal-stage requirement.", "—"],
        ["Q13", "Migration volume: 33 published pages, 3 private pages, 359 media files.",
         "All 36 pages and all 359 files (199 images, 133 documents, 27 other) inventoried and migrated at 90%+ coverage.", "Included"],
        ["Q16/Q17", "WCAG 2.1 AA minimum, 2.2 AA welcomed; PDF remediation priced separately.",
         "2.2 AA targeted; audit report handed to DEWR. Legacy PDF tagging at $12 per PDF, quoted after inventory.", "Optional"],
        ["Q18", "Base search must include pages, metadata, and text inside PDFs.",
         "Index covers page copy, metadata (category, program, year, version), and PDF text, returning the matched page.", "Included"],
        ["Q19/Q20/Q21", "Keep or replace Elementor; coordinate DNS/SSL with CSKT IT five business days pre-launch.",
         "Elementor not required and not used. GoDaddy DNS/SSL cutover coordinated with CSKT IT 5 business days out.", "Included"],
        ["Q24/Q25/Q26", "Dedicated Maps and Data page with four categories; no contractor ArcGIS org access.",
         "Four-category hub built. All ArcGIS publishing via the DEWR GIS Analyst; URL embeds only, no logins or keys.", "Included"],
        ["Q27", "Present three initial branding concepts, including unified vs. three-division exploration.",
         "Concept A (unified NRD), Concept B (FWRC/EP/DEWR), Concept C (watershed/Compact) — each with rationale and trade-offs.", "Included"],
        ["Q28", "Seal placement and cultural review via DEWR to CSKT Culture Committees.",
         "Official Seal artwork only, never redrawn. Per-asset approval tracked Draft → DEWR → Culture Committee → Approved.", "Included"],
        ["Q29", "Support Salish and Ksanka language typography.",
         "UTF-8 end-to-end, correct lang attributes (sal / kut), licensed-font decision deferred to DEWR.", "Included"],
        ["Q30", "Newsletter signup.",
         "Topic-grouped signup with double opt-in, stored consent record, and one-click unsubscribe.", "Included"],
        ["Q31", "Public comment form with deadline cutoff, upload, auto-email, staff export, public-record notice.",
         "Automatic time-based lock, PDF/DOCX validation (25 MB), reference number, staff notification, one-click CSV export.", "Included"],
        ["Q32", "Simple meetings and open houses calendar.",
         "One-screen publishing; past meetings retained with materials; no third-party tracking embeds.", "Included"],
        ["Q33", "Jobs should link to CSKT Personnel.",
         "Job summaries link out to the official CSKT Personnel Office posting; no applications collected on the site.", "Included"],
        ["Q35", "Zero stock photos and zero AI-generated landscapes.",
         "Original vector illustrations only. Photographs supplied by DEWR with documented rights and approval.", "Included"],
        ["Q37", "Virtual interviews November 9–12, 2026.",
         "Available for any window in that range, Mountain Time, with screen-share of the live prototype.", "—"],
        ["Q38", "Deadline moved to October 29, 2026, 4:30 p.m. MDT.",
         "This supplement is submitted before the revised deadline.", "—"],
        ["Q48", "Optional interactive Water Compact Q&amp;A tool using DEWR-approved sources.",
         "Source-cited Seth Bot prototype; answers only from approved sources, cites page, refuses to guess.", "Optional"],
    ]
    S.append(table(rows, [0.55 * inch, 2.5 * inch, 3.25 * inch, 0.6 * inch]))
    S.append(Spacer(1, 0.1 * inch))
    S.append(Paragraph(
        "Every row above is reflected in the live prototype, not only in this document. Where a requirement could not be "
        "honestly met at proposal stage — accessibility certification, real ArcGIS layers, or actual Tribal records — the "
        "prototype says so in plain language rather than implying compliance.", SMALL))

    S.append(PageBreak())

    # ------------------------------------------------------- 2. PROTOTYPE
    S.append(Paragraph("2. What I Built Before Being Asked — Updated for Addendum #1", H1))
    S.append(Paragraph(
        "The prototype is now five linked pages instead of three, and every Addendum #1 requirement has a working "
        "demonstration. It remains static HTML, CSS, and vanilla JavaScript: no framework, no build step, no tracking, "
        "no cookies, and no network requests. All data is labelled <code>[Sample]</code>.", LEAD))

    rows2 = [
        ["Page", "What it demonstrates", "Addendum items"],
        ["Home &amp; Programs", "Audience routing, site-wide search, before/after restoration slider, newsletter signup",
         "Q18, Q27–Q29, Q30, Q35"],
        ["Maps and Data", "Four-category hub, project explorer with keyboard-operable pins, Compact timeline, data inventory table",
         "Q24–Q26, Q35"],
        ["Documents &amp; Staff", "Document library with PDF full-text search, staff directory, careers via CSKT Personnel, technical notes",
         "Q18, Q33, Q19–Q21"],
        ["Branding Concepts", "Three concepts with rationale and trade-offs, reserved Seal zone, Salish/Ksanka typography samples",
         "Q27–Q29, Q35"],
        ["Get Involved", "Meetings calendar, deadline-locked comment form with CSV export, newsletter, Seth Bot",
         "Q30–Q33, Q48"],
    ]
    S.append(table(rows2, [1.15 * inch, 4.1 * inch, 1.65 * inch]))

    S.append(Paragraph("2.1 Search: the requirement most bidders will under-scope", H2))
    S.append(Paragraph(
        "Q18 makes searchable text inside PDFs a base requirement. That is not a plugin toggle: it needs a text "
        "extraction pipeline, an index that stores page numbers, and a results interface that tells the visitor which "
        "page matched. The prototype implements the full pattern on sample documents — searching “staff plate” returns "
        "the measurement guide with “matched on PDF page 3”, and searching “rating curve” returns the hydrology report "
        "at page 4. Scanned image-only PDFs need OCR, which I count and quote separately rather than bury in a change "
        "order.", BODY))

    S.append(Paragraph("2.2 Public comments: a deadline that actually closes", H2))
    S.append(Paragraph(
        "The comment form stores a closing date and time in Mountain Time, compares the current time against it, and "
        "disables submission when it passes — with a screen-reader announcement explaining why. Late comments are "
        "refused, not silently accepted. Attachments are limited to PDF/DOC/DOCX at 25 MB, the submitter receives a "
        "reference number, the assigned staff member is notified, and staff can export every submission to CSV in one "
        "click. A public-record consent checkbox is mandatory before submission.", BODY))

    S.append(Paragraph("2.3 Maps and Data: four categories, one access rule", H2))
    S.append(Paragraph(
        "The hub separates <b>Interactive Maps</b>, <b>Water Resources and Data</b>, <b>Project Maps</b>, and "
        "<b>ArcGIS StoryMaps</b> so a visitor knows whether a link opens a live map, a CSV, or a printed figure. "
        "All ArcGIS content is published by DEWR's GIS Analyst from DEWR's own ArcGIS Online organisation; I embed a "
        "public URL and hold no login, API key, or editing seat. If a service is unavailable the embed degrades to a "
        "titled link, and the page never breaks.", BODY))

    S.append(Paragraph("2.4 Seth Bot: useful only because it refuses to guess", H2))
    S.append(Paragraph(
        "The demonstration answers six common questions, prints the source document and page or question reference for "
        "each answer, and returns a written refusal plus a staff escalation path when no approved passage matches. It "
        "carries a permanent notice that it is not legal advice and not a water-rights determination. Because safe "
        "operation depends on curated, reviewed source content — ongoing staff work — it is priced as a separate "
        "optional item rather than hidden inside the base fee.", BODY))

    S.append(PageBreak())

    # ------------------------------------------------------- 3. BRANDING
    S.append(Paragraph("3. Branding, the Tribal Seal, and Language Support (Q27–Q29)", H1))
    S.append(Paragraph(
        "Three directions are presented as starting points, not as a finished brand. Each states its rationale, the "
        "case it serves best, and its honest trade-off — because a concept with no downside has not been thought "
        "through.", LEAD))

    rows3 = [
        ["", "Concept A · Unified NRD", "Concept B · Three-division", "Concept C · Watershed/Compact"],
        ["Structure", "One department mark with a division name line beneath it",
         "Three related marks sharing one geometric language and a signature bar",
         "Abstract contour motif with a channel line and a flexible division band"],
        ["Strength", "Consistency; lowest maintenance cost for DEWR staff",
         "Division-specific recognition for program campaigns",
         "Tells the Compact and watershed story on csktwatercompact.com"],
        ["Trade-off", "DEWR's individual identity is quieter at small sizes",
         "Three marks mean more rules and design governance",
         "Decorative, and must never read as a real map or boundary"],
    ]
    S.append(table(rows3, [0.8 * inch, 2.05 * inch, 2.05 * inch, 2.0 * inch]))

    S.append(Paragraph("3.1 How the choice is made", H2))
    S.extend(bullets([
        "Each concept is judged on recognisability at 24px, behaviour in a single colour, relationship to the official Seal, and how easily DEWR staff can apply it without a designer.",
        "The selected direction receives two structured revision rounds before the full style guide and templates are locked.",
        "The decision belongs to DEWR. I present, explain, and build — I do not push a favourite.",
    ]))

    S.append(Paragraph("3.2 The official CSKT Seal", H2))
    S.append(Paragraph(
        "The Seal is a sovereign emblem, and the prototype treats it accordingly. <b>It is never redrawn, traced, "
        "recoloured, cropped, or approximated anywhere in this project.</b> The prototype reserves an empty, correctly "
        "proportioned placement zone and enforces the rules that the production CMS will carry:", BODY))
    S.extend(bullets([
        "Only the official artwork file supplied by DEWR is used — never a screenshot or a colour-sampled copy.",
        "Approved placements: site footer, About the Tribes page, and formal public-notice documents.",
        "No seal on social graphics, merchandise, program badges, or as a background watermark without written authorisation.",
        "Minimum clear space of one seal-height on every side; no text overlay, gradient, or photograph behind it.",
        "Fixed, DEWR-approved alt text; a defined minimum size so the seal never renders illegibly.",
    ]))

    S.append(Paragraph("3.3 The cultural review gate is a schedule dependency, not a formality", H2))
    S.append(Paragraph(
        "Every concept, colour, motif, photograph, and language string goes to DEWR first, and <b>DEWR routes it to the "
        "CSKT Culture Committees</b>. I never contact Culture Committees, Elders, or Tribal members directly. Each asset "
        "carries a status — Draft, DEWR review, Culture Committee review, Approved — recorded in the CMS with an audit "
        "note. Phase 1 therefore ends with an <em>approved visual direction</em>, not a finished brand, and Phase 2 "
        "templates are built only against approved assets. If review needs more time, the milestone waits. I will not "
        "publish first and ask later, and I will not bill review time as a change order.", BODY))

    S.append(Paragraph("3.4 Salish and Ksanka typography (Q29)", H2))
    S.append(Paragraph(
        "Both languages use characters that ordinary Latin fonts drop or mangle — glottal stops, barred characters, and "
        "combining diacritics. Support is handled as an engineering requirement:", BODY))
    S.extend(bullets([
        "UTF-8 end to end across the database, editor, search index, sitemap, and PDF exports, verified with real strings rather than English test copy.",
        "Correct language attributes (<code>lang=\"sal\"</code>, <code>lang=\"kut\"</code>) so screen readers switch pronunciation rules instead of reading the words as English.",
        "A Unicode-complete fallback stack renders correctly now; a licensed webfont is purchased and self-hosted only after DEWR confirms licensing.",
        "Combining marks verified at 200% zoom, in print, and at small sizes for both screen and the printed guide.",
        "Wording and orthography come from DEWR and the Culture Committees — I never invent language content.",
    ]))

    S.append(Paragraph("3.5 Imagery: zero stock, zero AI (Q35)", H2))
    S.append(Paragraph(
        "No stock photograph, no AI-generated landscape, and no scraped image exists anywhere in the build. Every "
        "illustration is original inline SVG geometry authored for DEWR; icons are simple shapes, never traced "
        "cultural symbols. On the live site, photographs are DEWR-supplied with a recorded source, permission, and "
        "photographer credit, and recognisable people require a documented release. I will not use an image generator "
        "for land, water, people, or cultural material, and I will not pass a stock subscription to DEWR as a hidden "
        "cost.", BODY))

    S.append(PageBreak())

    # ------------------------------------------------------- 4. TECHNICAL
    S.append(Paragraph("4. Technical Approach on CSKT's Own Infrastructure (Q1, Q19–Q21)", H1))

    rows4 = [
        ["Area", "Commitment"],
        ["Hosting", "CSKT-managed <b>WP Engine</b> account. <b>$0 hosting cost</b> in this proposal — no hosting line item, no markup, no reseller."],
        ["Licensing", "Custom theme and plugins released under <b>GPLv2 or later</b> (WordPress-compatible). No proprietary lock-in, no licence renewal held by me."],
        ["Page builder", "Elementor is not required and not used. Content is built with native WordPress blocks and structured content types so staff are not trapped in a builder."],
        ["Launch coordination", "GoDaddy DNS and SSL cutover coordinated with <b>CSKT IT five business days before launch</b>, with a documented rollback point."],
        ["Domain", "Site continues on <code>csktwatercompact.com</code> or moves to a DEWR-chosen new domain — DEWR decides; I execute either path."],
        ["Content model", "Custom post types for Projects, Documents, Notices, Meetings, Jobs, and Staff, with reusable block patterns so non-technical editors publish without a developer."],
        ["Search", "Page copy + metadata + extracted PDF text, with page-level results. OCR for scanned PDFs counted and quoted separately."],
        ["ArcGIS", "Public URL embeds only, published by the DEWR GIS Analyst. No contractor access to DEWR's ArcGIS Online organisation, no API keys, no editing seats."],
        ["Accessibility", "WCAG 2.1 AA floor, 2.2 AA target. Automated + manual keyboard and screen-reader audit with the report handed to DEWR."],
        ["Security", "Enforced 2FA on administrative accounts, least-privilege roles, managed WAF at the WP Engine layer, automated updates on a staging-first schedule, and no plugin without a maintained release track."],
        ["Analytics", "GA4 (or DEWR's existing analytics) limited to page views, document downloads, and internal search terms. No advertising pixels, no cross-site trackers."],
        ["Backups", "WP Engine automated backups plus a pre-launch export retained by DEWR. Restore procedure documented and rehearsed."],
        ["Ownership", "DEWR owns the domain, hosting account, database, theme code, design source files, documentation, and every credential. Nothing is held by me after handover."],
        ["Redirects", "Full 301 map from every legacy URL, verified after cutover, so bookmarks and search rankings survive the migration."],
    ]
    S.append(table(rows4, [1.25 * inch, 5.65 * inch]))

    S.append(Paragraph("4.1 What “90%+ migrated” actually means", H2))
    S.append(Paragraph(
        "Of the 33 published pages and 3 private pages, every page is reviewed and classified Retain, Consolidate, "
        "Update, Archive, or Remove with DEWR. Approximately 90% or more of the existing content is migrated; the "
        "remainder is either genuinely obsolete or needs DEWR-authored replacement text. All 359 media files "
        "(199 images, 133 documents, 27 other) are inventoried, and every file is either migrated or explicitly "
        "recorded as retired — nothing disappears silently. New program and project archive pages are created on top of "
        "the migrated set.", BODY))

    S.append(Paragraph("4.2 PDF remediation is quoted, not hidden", H2))
    S.append(Paragraph(
        "Many legacy PDFs were exported from desktop publishing tools without tags, reading order, alt text, or "
        "bookmarks. Remediating them is real work, so it is priced per document at <b>$12 per PDF</b> after inventory. "
        "DEWR decides how many to remediate, in what order, and whether to remediate at all. Nothing about this line "
        "item affects the base scope.", BODY))

    S.append(PageBreak())

    # ------------------------------------------------------- 5. SCHEDULE
    S.append(Paragraph("5. Schedule and Collaboration", H1))
    S.append(Paragraph(
        "The schedule assumes a January 2027 start. If DEWR selects earlier, the phases compress rather than overlap "
        "recklessly — accessibility audit and content migration are the two steps I will not run in parallel.", BODY))

    rows5 = [
        ["Phase", "Deliverables", "Window", "Gate"],
        ["1 · Discovery, content audit, branding concepts",
         "Kickoff; full inventory of 36 pages and 359 files; sitemap and IA; three branding concepts; approved visual direction and style guide",
         "Jan 6 – Jan 31, 2027", "DEWR approval + Culture Committee review of visuals"],
        ["2 · WordPress, GIS and interactive build",
         "Staging on CSKT WP Engine; custom block theme; Maps and Data hub; search index with PDF text; comment workflow; calendar; jobs; newsletter",
         "Feb 1 – Mar 19, 2027", "Staging review with DEWR editors"],
        ["3 · Migration, accessibility QA, training",
         "Migration of approved content; 301 map; WCAG 2.1/2.2 audit; two recorded staff training sessions; written manuals",
         "Mar 22 – Apr 23, 2027", "Audit report accepted; editors publish unaided"],
        ["4 · Launch and 90-day warranty",
         "DNS/SSL cutover with CSKT IT; GA4 verification; credential handover; 90 days of included fixes",
         "Late Apr / May 2027 + 90 days", "Launch sign-off and handover checklist"],
    ]
    S.append(table(rows5, [1.5 * inch, 3.4 * inch, 0.95 * inch, 1.05 * inch]))

    S.append(Paragraph("5.1 How collaboration works day to day", H2))
    S.extend(bullets([
        "One shared milestone checklist and one live staging URL that multiple DEWR reviewers can open on desktop and mobile.",
        "Consolidated written feedback per milestone, with two structured revision rounds and a written change log before sign-off.",
        "Weekly short written status update with what moved, what is blocked, and what I need from DEWR — no status theatre.",
        "Working hours overlap Mountain Time mornings; urgent launch-window issues answered the same business day.",
    ]))

    S.append(callout("Honest risk statement", [
        "The two genuine risks on this project are content readiness and cultural review timing — both outside my "
        "control and both owned by DEWR. I will surface a slipping dependency the week it appears rather than the week "
        "the milestone is due, and I will not absorb an approval delay by quietly cutting accessibility or migration "
        "quality to protect a date.",
    ], accent=PINE))

    S.append(Paragraph("6. Fixed Price and Optional Items (Q2, Q9, Q11)", H1))

    rows6 = [
        ["#", "Scope line", "What is included", "USD"],
        ["1", "Planning, discovery and content inventory",
         "Kickoff, stakeholder sessions, inventory of 36 pages and 359 media files, sitemap/IA, discovery report", "$850"],
        ["2", "UX design, three branding concepts and style guide",
         "Three concepts, two revision rounds, approved visual system, complete style guide and templates", "$1,150"],
        ["3", "WordPress build on CSKT WP Engine",
         "Custom GPL block theme, Maps and Data hub, PDF-text search, comment workflow, calendar, jobs, newsletter, GA4, security hardening", "$1,900"],
        ["4", "Approved content migration and 301 redirects",
         "36 pages and 359 media files at 90%+ migration, redirect map, post-launch verification", "$900"],
        ["5", "Accessibility QA, training, launch and 90-day warranty",
         "WCAG 2.1/2.2 audit, two recorded trainings, written manuals, DNS/SSL cutover, 90 days of fixes", "$600"],
        ["", "<b>Total fixed turnkey implementation</b>", "All deliverables above · milestone-gated, paid on phase approval", "<b>$5,400</b>"],
    ]
    S.append(table(rows6, [0.28 * inch, 1.95 * inch, 4.02 * inch, 0.65 * inch]))

    S.append(Paragraph("6.1 Optional items — decline freely, nothing breaks", H2))
    rows6b = [
        ["Optional item", "Basis", "USD"],
        ["“Seth Bot” source-cited Water Compact Q&amp;A", "Fixed build, curated approved-source corpus, citation UI, staff escalation queue, handover training", "$950"],
        ["Legacy PDF remediation", "Per document, after inventory: tagging, reading order, alt text, bookmarks", "$12 / PDF"],
        ["Post-warranty support", "Monthly retainer (updates, backup verification, security monitoring, up to 3 hrs of edits) or on-demand", "$140 / mo or $45 / hr"],
        ["Substantive copywriting or new multimedia", "Only if requested, quoted after scope confirmation", "$45 / hr"],
    ]
    S.append(table(rows6b, [2.0 * inch, 4.25 * inch, 0.65 * inch]))

    S.append(Paragraph("6.2 Commercial terms", H2))
    S.extend(bullets([
        "<b>Hosting: $0 in this proposal.</b> CSKT's existing managed WP Engine account carries the site; DEWR pays WP Engine directly, with no markup or reseller margin from me.",
        "<b>3% CSKT contracting fee is paid by DEWR</b> and is not loaded into the price above.",
        "<b>General liability insurance</b> is arranged after selection and before work begins, as Q11 requires — not at proposal stage.",
        "<b>IRS Form W-8BEN</b> supplied with contracting paperwork as a non-U.S. individual contractor.",
        "<b>Milestone-gated payment:</b> 25% at Phase 1 approval, 30% at Phase 2 approval, 30% at Phase 3 approval, 15% at launch sign-off. No payment is due for a phase DEWR has not accepted.",
        "<b>Low-risk pilot:</b> DEWR may contract Phase 1 alone ($850) and decide on Phases 2–5 only after seeing the completed audit, sitemap, and visual direction.",
        "<b>Change control:</b> any work outside the written scope is quoted in writing before it starts. There are no surprise invoices.",
    ]))

    S.append(PageBreak())

    # ------------------------------------------------------- 7. FINAL
    S.append(Paragraph("7. Availability, References and Closing Statement", H1))

    S.append(Paragraph("7.1 Virtual interview availability (Q37)", H2))
    S.append(Paragraph(
        "I am available for a virtual interview on <b>any date between November 9 and November 12, 2026</b>, in any "
        "window that suits the committee in Mountain Time. I will screen-share the live prototype and walk through the "
        "search, the comment deadline lock, the Maps and Data hub, and the branding concepts — and I am comfortable "
        "being asked to change something live to prove it is real code.", BODY))

    S.append(Paragraph("7.2 References and prior experience — stated honestly", H2))
    S.append(Paragraph(
        "I am a solo independent developer. I do not have three prior paid agency client references, I do not hold "
        "CSKT Indian Preference certification, and I do not claim prior paid Tribal government contracts. I will not "
        "fabricate or borrow references to look larger than I am. What I can offer instead is verifiable: five working "
        "public builds, including this DEWR-specific prototype, with all source code inspectable on GitHub, plus a "
        "milestone structure where DEWR pays only for phases it has reviewed and accepted. If the committee requires a "
        "multi-staff agency with prior government references, this proposal should be set aside — and there will be no "
        "follow-up pressure of any kind.", BODY))

    S.append(Paragraph("7.3 Why this is worth a place on the shortlist", H2))
    S.extend(bullets([
        "<b>I built the thing before asking to be trusted.</b> Five pages, every Addendum #1 requirement demonstrated, all code public.",
        "<b>The price did not move when the scope grew.</b> New requirements were absorbed or moved to clearly optional lines.",
        "<b>Hosting is genuinely $0</b> because the site belongs on CSKT's own WP Engine account — not on a reseller plan I profit from.",
        "<b>Honesty is a design decision here.</b> Labelled sample data, stated limitations, no invented certification, and a bot that refuses to guess.",
        "<b>Cultural review is treated as a dependency, not an obstacle.</b> No seal imitation, no AI imagery, no published asset without written approval.",
    ]))

    S.append(callout("Statement of commitment", [
        "If selected, DEWR receives a fixed price, a written scope, weekly written status, and full ownership of every "
        "credential and file at handover. I will tell you early when something is behind. I will not quietly cut "
        "accessibility or migration quality to protect a date. And I will not publish a single cultural asset without "
        "the Culture Committees' written approval.",
        "<b>Abdulrhman</b> · abdulrhmant948@gmail.com · github.com/abdoo606",
    ], accent=RIVER))

    S.append(Spacer(1, 0.14 * inch))
    S.append(Paragraph("Document control", H3))
    S.append(Paragraph(
        "This document supersedes the written proposal submitted October 21, 2026, and responds to the DEWR Questions "
        "&amp; Answers Addendum #1 published October 22, 2026. Prototype content is sample data and is not an official "
        "CSKT publication. Nothing in this proposal claims an accessibility certification, a Tribal government "
        "reference, or Indian Preference status that does not exist.", SMALL))

    doc.build(S)
    print("Wrote", OUT)


if __name__ == "__main__":
    build()
