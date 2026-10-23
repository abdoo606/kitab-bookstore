/* Unofficial working prototype data for CSKT Division of Engineering & Water Resources (DEWR).
   ALL entries below are clearly marked placeholder/sample items modelling the CMS content types
   requested in the October 2026 DEWR Website Design & Development RFP + Questions & Answers
   Addendum #1 (published October 22, 2026).

   LEGAL / CULTURAL NOTES BAKED INTO THIS DATASET:
   - No real water right records, staff personal contacts, live telemetry, or official CSKT
     publications are claimed here. Every item carries an explicit [Sample] prefix.
   - ZERO stock photography and ZERO AI-generated imagery (Addendum Q35). All visuals in this
     prototype are original inline SVG vector diagrams authored for DEWR.
   - The CSKT Tribal Seal is NEVER redrawn, traced, colour-sampled, or approximated. It is
     reserved as an official-asset placement zone only (Addendum Q27/Q28).
   - Salish (Séliš / Ql̓ispé) and Ksanka (Ktunaxa) strings are stored as real Unicode text with
     combining marks so they render correctly once DEWR-approved fonts are licensed. */

window.DEWR_SAMPLE_DATA = {
  meta: {
    addendumVersion: "Addendum #1 — October 22, 2026",
    addendumDate: "2026-10-22",
    proposalDeadline: "2026-10-29T16:30:00-06:00",
    proposalDeadlineLabel: "Thursday, October 29, 2026 · 4:30 p.m. MDT",
    interviewWindow: "November 9–12, 2026",
    cms: "WordPress 6.x on CSKT-managed WP Engine (Q1, Q19, Q20, Q21)",
    migrationCounts: { publishedPages: 33, privatePages: 3, mediaFiles: 359, images: 199, documents: 133, other: 27 }
  },

  /* ---------------------------------------------------------------- Q27 — BRANDING CONCEPTS */
  brandingConcepts: [
    {
      id: "concept-a",
      code: "Concept A",
      name: "Unified NRD Identity",
      tagline: "One Natural Resources Department mark with DEWR as a named division lock-up.",
      rationale:
        "Treats the Department of Natural Resources as the single public brand and places DEWR, Fish Wildlife Recreation & Conservation, and Environmental Protection beneath it as a consistent division name line. Fewest marks to maintain, strongest shared recognition across department pages, and one predictable place for the official CSKT Seal.",
      bestFor: "Maximum consistency and the lowest ongoing design-maintenance cost for DEWR staff.",
      tradeoffs:
        "DEWR's individual program identity is quieter; division-level recognition depends entirely on the name lock-up staying readable at small sizes.",
      palette: ["#0D4F6B", "#164E3A", "#0F2430", "#C08A2E"],
      mark: "unified"
    },
    {
      id: "concept-b",
      code: "Concept B",
      name: "Coordinated Three-Division System",
      tagline: "A shared visual grammar with three distinct division marks: FWRC, EP, and DEWR.",
      rationale:
        "Gives each division its own recognisable silhouette built from the same geometric language, colour tokens, and typographic scale, while a shared NRD signature bar keeps them visibly related. Supports division-specific outreach (fish screens, water quality, engineering) without fragmenting into unrelated logos.",
      bestFor: "Public-facing program campaigns where division identity matters (hatchery, water quality advisories, construction notices).",
      tradeoffs:
        "Three marks mean three sets of usage rules and more design governance; the system only holds together if the shared tokens are enforced.",
      palette: ["#0D4F6B", "#2B6E5A", "#7A4A2B", "#C08A2E"],
      mark: "triad"
    },
    {
      id: "concept-c",
      code: "Concept C",
      name: "Watershed & Water Compact System",
      tagline: "A contour-line watershed motif carrying the CSKT–Montana Water Compact story.",
      rationale:
        "Abstract topographic contours and a meandering channel line express the Flathead watershed and the Compact's cooperative water stewardship without borrowing any sacred or ceremonial imagery. Division names sit in a single flexible band, so a fourth program can be added later without a new mark.",
      bestFor: "Leading with water stewardship and the Compact — the strongest fit for csktwatercompact.com as the public Compact home.",
      tradeoffs:
        "The watershed motif is decorative rather than literal, so it must never be presented as an actual map or boundary depiction.",
      palette: ["#0D4F6B", "#15616D", "#164E3A", "#B4763C"],
      mark: "watershed"
    }
  ],

  /* ------------------------------------------------------- Q27/Q28 — SEAL & CULTURAL REVIEW GATES */
  sealPolicy: {
    heading: "Official CSKT Tribal Seal — reserved placement zone only",
    points: [
      "This zone is an empty, correctly proportioned placeholder. The prototype never redraws, traces, recolours, crops, or approximates the sovereign CSKT Tribal Seal.",
      "The production site will display only the official artwork file supplied by DEWR (PNG/SVG with clear-space rules and a stated minimum print size).",
      "Approved placements: site footer, the About the Tribes page, and formal public-notice documents. No seal on social graphics, merch, or program badges without written authorisation.",
      "Minimum clear space is protected at 1× the seal's height on all sides, with no overlaid text, gradient, or photo behind it."
    ],
    culturalGate: [
      "Every concept, motif, colour, and Salish/Ksanka string is submitted first to DEWR, and DEWR routes it to the CSKT Culture Committees for review (Addendum Q28).",
      "No culturally sensitive imagery, plant knowledge, ceremony references, or language is published before written Culture Committee approval is recorded.",
      "The contractor never contacts Culture Committees, Elders, or Tribal members directly; all review traffic flows through the DEWR project manager.",
      "Approval status is tracked per asset (Draft → DEWR review → Culture Committee review → Approved) inside the CMS workflow, with an audit note on each change."
    ]
  },

  /* --------------------------------------------------- Q29 — SALISH & KSANKA TYPOGRAPHY SUPPORT */
  languageSupport: {
    heading: "Salish (Séliš / Ql̓ispé) and Ksanka (Ktunaxa) Unicode support",
    note:
      "Both languages use characters outside the Basic Latin range. The prototype loads a Unicode-complete fallback stack and renders real combining marks and glottal stops — never ASCII approximations.",
    samples: [
      { lang: "Salish (Séliš / Ql̓ispé)", text: "Séliš · Ql̓ispé · Nɫawqin", note: "Glottal stop (ʼ) and barred-L (ɫ) preserved as true Unicode." },
      { lang: "Ksanka (Ktunaxa)", text: "Ktunaxa · Qat̕ ]", note: "Sample string for font-coverage verification only; wording pending Culture Committee review." }
    ],
    technical: [
      "UTF-8 output end-to-end with no character-encoding truncation in the CMS database, search index, or PDF export.",
      "Language tags applied to markup (lang=\"sal\" for Salish content, lang=\"kut\" for Ktunaxa) so screen readers switch pronunciation rules correctly.",
      "Font licensing confirmed with DEWR before any embedded webfont is purchased or self-hosted; a system fallback stack is used until then.",
      "Combining diacritics tested at 200% zoom and in the printed style guide, not only on screen."
    ]
  },

  /* ---------------------------------------- Q24–Q26 — DEDICATED "MAPS AND DATA" HUB (4 CATEGORIES) */
  mapsData: [
    {
      id: "interactive-maps",
      number: "1",
      title: "Interactive Maps",
      intro:
        "Embedded ArcGIS Online web maps and dashboards for watershed, project, and gaging views. Embeds are added by DEWR's GIS Analyst; the contractor receives no direct access to DEWR's ArcGIS Online organisation account (Addendum Q25).",
      items: [
        { title: "[Sample] Reservation-Wide Project Explorer", type: "ArcGIS Web App", note: "Project points, status, and photo placeholders.", slot: "arcgis-webapp-slot-projects" },
        { title: "[Sample] Stream Gage & Diversion Dashboard", type: "ArcGIS Dashboard", note: "Stage/discharge summary views and seasonal comparisons.", slot: "arcgis-dashboard-slot-hydrology-gages" },
        { title: "[Sample] Restoration Corridor Viewer", type: "ArcGIS Web Map", note: "Reach-level restoration extents and treatment types.", slot: "arcgis-webmap-slot-restoration" }
      ]
    },
    {
      id: "water-resources-data",
      number: "2",
      title: "Water Resources and Data",
      intro:
        "Downloadable hydrology datasets, annual summaries, and measurement guidance. Datasets are published only after DEWR data-quality review and carry explicit vintage, units, and caveat statements.",
      items: [
        { title: "[Sample] Annual Streamflow Summary Tables", type: "CSV + PDF", note: "Station-level monthly means, units, and completeness flags." },
        { title: "[Sample] Diversion Measurement Field Protocol", type: "PDF", note: "Plain-language method sheet for water users." },
        { title: "[Sample] Snowpack & Runoff Outlook Notes", type: "PDF", note: "Seasonal narrative with data provenance statements." }
      ]
    },
    {
      id: "project-maps",
      number: "3",
      title: "Project Maps",
      intro:
        "Static, print-safe maps and figure sets tied to individual construction, restoration, and modernization projects — built for field packets and public meetings.",
      items: [
        { title: "[Sample] Mission Valley Lateral Piping Phasing Map", type: "PDF figure", note: "Phase boundaries, turnout locations, construction windows." },
        { title: "[Sample] Jocko Floodplain Reconnection Plan Set", type: "PDF figure", note: "Pre/post channel alignment and planting zones." },
        { title: "[Sample] Dam Safety Inundation Reference Figure", type: "PDF figure", note: "Reference-only figure pending DEWR engineering sign-off." }
      ]
    },
    {
      id: "storymaps",
      number: "4",
      title: "ArcGIS StoryMaps",
      intro:
        "Narrative, scroll-based stories for public education and project storytelling. StoryMaps are authored inside DEWR's own ArcGIS organisation and embedded by URL only (Addendum Q26).",
      items: [
        { title: "[Sample] Following the Water: A Flathead Watershed Story", type: "StoryMap embed", note: "Basin overview and seasonal water story.", slot: "arcgis-storymap-slot-watershed" },
        { title: "[Sample] Restoring the Jocko: Before & After", type: "StoryMap embed", note: "Restoration chronology with vector diagrams.", slot: "arcgis-storymap-slot-jocko-corridor" },
        { title: "[Sample] How the Compact Works", type: "StoryMap embed", note: "Plain-language Compact explainer.", slot: "arcgis-storymap-slot-compact" }
      ]
    }
  ],

  arcgisAccessNote:
    "Access model (Q25): DEWR's GIS Analyst publishes each Web App, Dashboard, or StoryMap from DEWR's ArcGIS Online organisation and shares a public URL. The contractor embeds that URL in a responsive, accessible block and never requests an org-account login, API key, or editing seat. Any map change is requested through the GIS Analyst, and embeds degrade to a titled link if a service is unavailable.",

  /* ----------------------------------------------------------------- Q30 — NEWSLETTER SIGNUP */
  newsletterTopics: [
    { id: "notices", label: "Public meeting & open-house notices" },
    { id: "projects", label: "Project construction & restoration updates" },
    { id: "water", label: "Water supply, gaging & seasonal outlook" },
    { id: "jobs", label: "DEWR job openings" }
  ],

  /* --------------------------------------------------- Q32 — MEETINGS & OPEN HOUSES CALENDAR */
  meetings: [
    { id: "MTG-2026-11", title: "[Sample] Flathead Basin Fall Water Management Open House", date: "2026-11-18", time: "6:00 p.m. – 8:00 p.m. MT", location: "Ronan, MT — Community Room (sample)", type: "Open House", commentWindow: "Closes Nov 25, 2026 · 11:59 p.m. MT", status: "Upcoming" },
    { id: "MTG-2026-11b", title: "[Sample] Water Compact Administration Quarterly Session", date: "2026-11-05", time: "10:00 a.m. – 12:00 p.m. MT", location: "Virtual + Ronan, MT (sample)", type: "Public Meeting", commentWindow: "Closes Nov 12, 2026 · 11:59 p.m. MT", status: "Upcoming" },
    { id: "MTG-2026-10", title: "[Sample] Jocko Restoration Community Update", date: "2026-10-14", time: "5:30 p.m. – 7:00 p.m. MT", location: "Arlee, MT (sample)", type: "Community Update", commentWindow: "Closed Oct 21, 2026", status: "Past" },
    { id: "MTG-2026-09", title: "[Sample] Irrigation Measurement Field Day", date: "2026-09-23", time: "9:00 a.m. – 1:00 p.m. MT", location: "Mission Valley (sample)", type: "Field Day", commentWindow: "Closed Sep 30, 2026", status: "Past" }
  ],

  /* ------------------------------------------------------- Q33 — CSKT PERSONNEL JOBS INTEGRATION */
  jobsIntegration: {
    officeName: "CSKT Personnel Office",
    policy:
      "DEWR does not host its own applicant database or collect applications. Every opening on this site is a short summary that links out to the official CSKT Personnel Office posting, where the Tribe's application, Indian Preference policy, background-check, and drug-testing requirements apply. The prototype shows the summary + outbound link pattern only.",
    jobs: [
      { title: "[Sample] Water Resources Civil Engineer (PE / EIT)", program: "Engineering & Infrastructure", location: "Ronan, MT", type: "Full-Time Tribal Government Position", ref: "CSKT-PER-0000-SAMPLE", posted: "2026-10-01", closes: "2026-11-06" },
      { title: "[Sample] Hydrologic Technician — Field Gaging & Telemetry", program: "Hydrology & Water Measurement", location: "Ronan, MT", type: "Full-Time / Seasonal Field Role", ref: "CSKT-PER-0001-SAMPLE", posted: "2026-09-18", closes: "2026-10-30" },
      { title: "[Sample] GIS & Environmental Restoration Specialist", program: "Stream Restoration & GIS", location: "Ronan, MT", type: "Full-Time Technical Role", ref: "CSKT-PER-0002-SAMPLE", posted: "2026-09-05", closes: "2026-10-24" }
    ]
  },

  /* --------------------------------------------- Q48 — SOURCE-CITED "SETH BOT" Q&A DEMO CORPUS */
  sethBot: {
    disclaimer:
      "Demonstration only. Answers below are drawn from DEWR-approved public sources and cite the document and page. This tool gives general information about the CSKT–Montana Water Compact and DEWR processes — it is not legal advice, not a water-rights determination, and not an official DEWR statement. For decisions about your own water right or allotment, contact DEWR directly.",
    sources: {
      "compact-faq": { label: "CSKT–Montana Water Compact Public FAQ (sample document set)", url: "https://csktwatercompact.com/documents-and-links/" },
      "dewr-rfp": { label: "DEWR Website Redesign & Development RFP (October 2026)", url: "https://csktwatercompact.com/" },
      "addendum-1": { label: "DEWR RFP Questions & Answers Addendum #1 (October 22, 2026)", url: "https://csktwatercompact.com/wp-content/uploads/2026/10/Addendum-1_October_22_2026.pdf" },
      "water-user-guide": { label: "Water User Measurement & Headgate Guide (sample document set)", url: "https://csktwatercompact.com/documents-and-links/" }
    },
    entries: [
      {
        id: "what-is-compact",
        question: "What is the CSKT–Montana Water Compact?",
        keywords: ["compact", "what is", "treaty", "agreement", "montana"],
        answer:
          "The Compact is the negotiated Tribal–State framework for administering water rights on and around the Flathead Indian Reservation, alongside federal enactment and funding for water management, restoration, and irrigation infrastructure. DEWR administers the Tribal side of that work day to day.",
        citations: [{ source: "compact-faq", page: "p. 1–2" }]
      },
      {
        id: "who-measures",
        question: "Do I have to measure my diversion as an irrigator?",
        keywords: ["measure", "diversion", "headgate", "irrigator", "turnout", "flow"],
        answer:
          "Measurement requirements follow your specific water right, decree, and district rules — they are not one-size-fits-all. The Water User Measurement & Headgate Guide summarises common field practices (staff plate reading, turnout scheduling, reporting cadence). DEWR staff confirm your actual obligation before any structure change.",
        citations: [{ source: "water-user-guide", page: "p. 3–5" }, { source: "compact-faq", page: "p. 7" }]
      },
      {
        id: "comment-window",
        question: "How long do I have to submit a public comment?",
        keywords: ["comment", "deadline", "public comment", "how long", "submit"],
        answer:
          "Each notice states its own comment window, and the online form closes automatically at the stated date and time — late submissions are refused by the form rather than silently accepted. The Meetings & Open Houses calendar lists the closing time for every open item.",
        citations: [{ source: "addendum-1", page: "Q31" }]
      },
      {
        id: "data-access",
        question: "Can I download the streamflow data behind the maps?",
        keywords: ["data", "download", "csv", "streamflow", "gage", "map", "arcgis"],
        answer:
          "Yes — the Maps and Data hub publishes downloadable summary tables and figures with units, vintage, and completeness notes. Live ArcGIS layers stay inside DEWR's own ArcGIS Online organisation and are shown here through embedded public views; raw layer editing is never exposed to the public or the contractor.",
        citations: [{ source: "addendum-1", page: "Q24–Q26" }]
      },
      {
        id: "jobs",
        question: "How do I apply for a job with DEWR?",
        keywords: ["job", "apply", "career", "hiring", "employment", "personnel"],
        answer:
          "Openings are summarised on the DEWR site and then link out to the official CSKT Personnel Office posting, which carries the real application, closing date, Indian Preference provisions, and pre-employment requirements. This site never collects applications or résumés.",
        citations: [{ source: "addendum-1", page: "Q33" }]
      },
      {
        id: "seal",
        question: "Can the website use the Tribal Seal?",
        keywords: ["seal", "logo", "brand", "tribal seal", "official"],
        answer:
          "Only the official artwork supplied by DEWR is used, and only in approved placements such as the footer and formal notices. It is never redrawn or restyled, and all branding concepts go through DEWR to the CSKT Culture Committees before publication.",
        citations: [{ source: "addendum-1", page: "Q27–Q29" }]
      }
    ]
  },

  /* --------------------------------------- Q18 — PAGE + METADATA + IN-PDF FULL-TEXT SEARCH CORPUS */
  searchIndex: [
    {
      id: "page-home",
      kind: "Page",
      title: "Home & Programs",
      url: "index.html",
      meta: "DEWR overview · six core programs · audiences",
      body:
        "The Division of Engineering and Water Resources protects Tribal water resources through science engineering and cultural stewardship on the Flathead Indian Reservation. Programs cover Water Compact implementation stream wetland and fishery restoration irrigation modernization measurement dam safety civil infrastructure hydrology stream gaging ArcGIS and public education notices careers."
    },
    {
      id: "page-maps",
      kind: "Page",
      title: "Maps and Data",
      url: "projects-gis.html#maps-data",
      meta: "Interactive Maps · Water Resources and Data · Project Maps · ArcGIS StoryMaps",
      body:
        "Dedicated Maps and Data hub with four categories interactive maps water resources and data downloadable tables project maps figures and ArcGIS StoryMaps narratives. Embeds are published by the DEWR GIS Analyst from the DEWR ArcGIS Online organisation."
    },
    {
      id: "page-branding",
      kind: "Page",
      title: "Branding Concepts & Style Guide",
      url: "branding.html",
      meta: "Concept A · Concept B · Concept C · seal zone · Salish and Ksanka type",
      body:
        "Three branding concepts a unified Natural Resources Department identity a coordinated three division system for Fish Wildlife Recreation and Conservation Environmental Protection and DEWR and a watershed and water compact contour system. Includes the reserved official CSKT Seal placement zone and Salish Selis Qlipse and Ksanka Ktunaxa Unicode typography support with Culture Committee review."
    },
    {
      id: "page-involved",
      kind: "Page",
      title: "Get Involved · Meetings · Public Comment",
      url: "get-involved.html",
      meta: "calendar · comment deadline · newsletter · Seth Bot Q&A",
      body:
        "Meetings and open houses calendar newsletter signup public comment form with automatic deadline cutoff PDF and DOCX attachment staff CSV export and the source cited Seth Bot water compact question and answer demonstration."
    },
    {
      id: "doc-hydro",
      kind: "PDF",
      title: "[Sample] Annual Reservation Hydrology & Streamflow Summary Report",
      url: "documents.html#doc-library",
      meta: "Technical Reports · Hydrology & Water Compact · 2026 · v2.1",
      pages: [
        { page: 1, text: "Annual hydrology and streamflow summary cover page prepared for the Division of Engineering and Water Resources. Reporting period snowpack accumulation runoff volume gaging station network." },
        { page: 4, text: "Methods. Fifteen minute stage recordings were converted to discharge using the current rating curve for each station. Rating curve revisions are documented in appendix B. Uncertainty is reported at the ninety five percent confidence interval." },
        { page: 12, text: "Findings by basin. The Jocko basin produced above median runoff while the Mission Valley laterals showed reduced seepage losses following pipeline conversion. Peak flow timing shifted earlier by approximately nine days relative to the thirty year median." },
        { page: 23, text: "Data quality and caveats. Ice affected records between December and February are flagged as estimated. Users should not treat estimated periods as measured values. Annual summary tables are published as CSV alongside this report." }
      ]
    },
    {
      id: "doc-headgate",
      kind: "PDF",
      title: "[Sample] Water User Measurement & Headgate Turnout Information Guide",
      url: "documents.html#doc-library",
      meta: "Forms & Water Users · Irrigation Modernization · 2026 · v1.4",
      pages: [
        { page: 1, text: "Water user measurement and headgate turnout information guide for irrigators landowners and allottees. Plain language instructions." },
        { page: 3, text: "Reading a staff plate. Read the water surface at eye level against the graduated plate and record the value to the nearest tenth of a foot. Record the date time and gate setting on the turnout log sheet." },
        { page: 5, text: "Reporting schedule. Weekly readings are typical during the irrigation season. Contact DEWR before changing a measuring structure. Do not modify a headgate or weir without written approval because changes invalidate the rating." },
        { page: 9, text: "Who to call. Field contact numbers are maintained by DEWR and updated each season. This sample document contains no real staff contact details." }
      ]
    },
    {
      id: "doc-notice",
      kind: "PDF",
      title: "[Sample] Public Meeting Notice & Watershed Restoration Presentation Packet",
      url: "documents.html#doc-library",
      meta: "Public Notices · Stream & Fishery Restoration · 2026 · v1.0",
      pages: [
        { page: 1, text: "Public meeting notice and watershed restoration presentation packet. Open house agenda and public comment instructions." },
        { page: 2, text: "Comment period. Written comments may be submitted through the online public comment form until the closing date and time stated on the notice. Comments received after the cutoff are not accepted by the form." },
        { page: 6, text: "Before and after channel cross sections for the restoration reach including floodplain reconnection and riparian planting zones." }
      ]
    },
    {
      id: "doc-specs",
      kind: "PDF",
      title: "[Sample] Construction Contracting & Engineering Standard Specifications Overview",
      url: "documents.html#doc-library",
      meta: "Procurement & Engineering · Engineering & Infrastructure · 2025 · v3.0",
      pages: [
        { page: 1, text: "Construction contracting and engineering standard specifications overview for civil consultants and construction bidders." },
        { page: 8, text: "Indian Preference. Contractors must follow the Tribes Indian Preference requirements and coordinate with the Tribal Employment Rights Office. Submittal procedures and bonding requirements are listed in section four." },
        { page: 15, text: "Temporary erosion and sediment control requirements including silt fence placement inlet protection and stabilization timing before seasonal shutdown." }
      ]
    },
    {
      id: "doc-faq",
      kind: "PDF",
      title: "[Sample] CSKT–Montana Water Compact Educational FAQ for Classrooms & Residents",
      url: "documents.html#doc-library",
      meta: "Educational Materials · Public Outreach & Education · 2025 · v1.2",
      pages: [
        { page: 1, text: "Water Compact educational frequently asked questions for classrooms and residents." },
        { page: 2, text: "What the Compact does. It quantifies and administers water rights and provides a cooperative framework between the Tribes the State of Montana and federal partners while protecting instream flows." },
        { page: 7, text: "Glossary. Allottee decree instream flow irrigation district priority date reserved water right trust land. Terms are defined in plain language for classroom use." }
      ]
    }
  ],

  /* --------------------------------------------------------------- EXISTING PROTOTYPE CONTENT */
  projects: [
    {
      id: "jocko-floodplain",
      title: "[Sample] Jocko River Floodplain & Bull Trout Habitat Restoration",
      category: "Stream & Fishery Restoration",
      basin: "Lower Flathead / Jocko Basin",
      status: "Active Construction",
      x: 350,
      y: 235,
      summary: "Channel reconnection, riparian willow planting, and fish passage screening supporting native bull trout and westslope cutthroat trout habitat.",
      storymapSlug: "arcgis-storymap-slot-jocko-corridor",
      metrics: "4.2 river miles · Engineered fish screen · Seasonal flow monitoring"
    },
    {
      id: "mission-lateral-pipe",
      title: "[Sample] Mission Valley Lateral Piping & Measurement Modernization",
      category: "Irrigation Modernization",
      basin: "Mission Valley Irrigation District",
      status: "Phase II Design & Construction",
      x: 285,
      y: 170,
      summary: "Converting open seepage laterals to pressurized pipeline with automated turnout measurement to conserve instream flows and improve farm delivery reliability.",
      storymapSlug: "arcgis-webapp-slot-mission-laterals",
      metrics: "Estimated 6,800 acre-feet/yr seepage reduction · Automated telemetry turnouts"
    },
    {
      id: "crow-dam-safety",
      title: "[Sample] Reservoir Outlet Works & Dam Safety Instrumentation Upgrade",
      category: "Engineering & Infrastructure",
      basin: "Central Reservation Storage",
      status: "Engineering Review",
      x: 245,
      y: 125,
      summary: "Structural gate rehabilitation, piezometer instrumentation, and updated operational telemetry under DEWR engineering oversight.",
      storymapSlug: "arcgis-storymap-slot-dam-infrastructure",
      metrics: "24/7 headwater stage telemetry · Updated emergency action documentation"
    },
    {
      id: "compact-gage-network",
      title: "[Sample] Flathead Basin Compact Streamflow & Diversion Gaging Network",
      category: "Hydrology & Water Compact",
      basin: "Reservation-Wide Watersheds",
      status: "Ongoing Operations",
      x: 165,
      y: 95,
      summary: "Real-time stream gages, staff plates, and seasonal hydrologic reporting supporting CSKT–Montana Water Compact administration.",
      storymapSlug: "arcgis-dashboard-slot-hydrology-gages",
      metrics: "Real-time 15-min stage/discharge feed · Public CSV/PDF annual summaries"
    }
  ],

  timeline: [
    { era: "1. Water Compact Framework", year: "Compact Ratification & Federal Enactment", detail: "Establishes cooperative Tribal–State water administration, instream flow protections, and federal settlement funding for rehabilitation, fishery restoration, and water management infrastructure." },
    { era: "2. Division Expansion", year: "DEWR Program Growth & Technical Capacity", detail: "Expansion across hydrology, civil and irrigation engineering, GIS mapping, stream restoration, dam safety, water measurement, and public education across the Flathead Indian Reservation." },
    { era: "3. Modernization & Restoration", year: "Multi-Year Field & Infrastructure Delivery", detail: "Coordinated headgate automation, canal lining/piping, fish passage barriers removal, wetland reconnection, and transparent public reporting." },
    { era: "4. Long-Term Stewardship", year: "Unified Digital Hub & Public Access (2027+)", detail: "Single accessible CMS owned and operated by CSKT DEWR staff connecting Tribal members, water users, partner agencies, and educators to maps, notices, and technical archives." }
  ],

  documents: [
    { id: "DOC-2026-01", title: "[Sample] Annual Reservation Hydrology & Streamflow Summary Report", category: "Technical Reports", program: "Hydrology & Water Compact", year: "2026", version: "v2.1 (Tagged Accessible PDF)", size: "2.4 MB PDF", summary: "Seasonal snowpack, runoff volume, gaging station QA notes, and basin-by-basin hydrographs.", searchId: "doc-hydro" },
    { id: "DOC-2026-02", title: "[Sample] Water User Measurement & Headgate Turnout Information Guide", category: "Forms & Water Users", program: "Irrigation Modernization", year: "2026", version: "v1.4 (Fillable PDF + Web Form)", size: "640 KB PDF", summary: "Plain-language guide for irrigators, landowners, and Allottees on diversion measurement schedules and field contacts.", searchId: "doc-headgate" },
    { id: "DOC-2026-03", title: "[Sample] Public Meeting Notice & Watershed Restoration Presentation Packet", category: "Public Notices", program: "Stream & Fishery Restoration", year: "2026", version: "v1.0", size: "1.8 MB PDF", summary: "Community open-house agenda, before-and-after channel cross-sections, and public comment instructions.", searchId: "doc-notice" },
    { id: "DOC-2025-04", title: "[Sample] Construction Contracting & Engineering Standard Specifications Overview", category: "Procurement & Engineering", program: "Engineering & Infrastructure", year: "2025", version: "v3.0", size: "3.1 MB PDF", summary: "Reference package for civil consultants, construction bidders, and Indian Preference Office coordination.", searchId: "doc-specs" },
    { id: "DOC-2025-05", title: "[Sample] CSKT–Montana Water Compact Educational FAQ for Classrooms & Residents", category: "Educational Materials", program: "Public Outreach & Education", year: "2025", version: "v1.2", size: "920 KB PDF", summary: "Illustrated overview of Tribal water stewardship, watershed ecology, and Compact implementation milestones.", searchId: "doc-faq" }
  ],

  staff: [
    { name: "[Sample] Program Lead — Division Administration", title: "Division Manager", area: "Administration & Compact Coordination", bio: "Oversees multi-program engineering, hydrology, restoration scheduling, and interagency Water Compact coordination.", phone: "406-304-0000 (Sample)", email: "dewr-office-sample@example.org" },
    { name: "[Sample] Information & Education Coordinator", title: "Information & Education Program Manager", area: "Public Outreach & Education", bio: "Leads public notices, community meetings, educational StoryMaps, digital communications, and media inquiries.", phone: "406-304-0001 (Sample)", email: "outreach-sample@example.org" },
    { name: "[Sample] Senior Water Resources Engineer", title: "Supervisory Civil / Irrigation Engineer", area: "Engineering & Infrastructure", bio: "Directs canal modernization design, headworks rehabilitation, construction QA, and contractor submittals.", phone: "406-304-0002 (Sample)", email: "engineering-sample@example.org" },
    { name: "[Sample] Lead Watershed Hydrologist & GIS Specialist", title: "Hydrology & GIS Lead", area: "Hydrology & GIS", bio: "Manages basin gaging networks, ArcGIS Online applications, StoryMaps publishing, and hydrologic datasets.", phone: "406-304-0003 (Sample)", email: "gis-hydrology-sample@example.org" }
  ]
};
