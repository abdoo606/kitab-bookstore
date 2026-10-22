/* Unofficial working prototype data for CSKT Division of Engineering & Water Resources (DEWR).
   ALL entries below are clearly marked placeholder/sample items modelling the CMS content types
   requested in the October 2026 DEWR Website Design & Development RFP (Sections 4 & 5).
   No real water right records, staff personal contacts, or live telemetry are claimed here. */

window.DEWR_SAMPLE_DATA = {
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
    {
      era: "1. Water Compact Framework",
      year: "Compact Ratification & Federal Enactment",
      detail: "Establishes cooperative Tribal–State water administration, instream flow protections, and federal settlement funding for rehabilitation, fishery restoration, and water management infrastructure."
    },
    {
      era: "2. Division Expansion",
      year: "DEWR Program Growth & Technical Capacity",
      detail: "Expansion across hydrology, civil and irrigation engineering, GIS mapping, stream restoration, dam safety, water measurement, and public education across the Flathead Indian Reservation."
    },
    {
      era: "3. Modernization & Restoration",
      year: "Multi-Year Field & Infrastructure Delivery",
      detail: "Coordinated headgate automation, canal lining/piping, fish passage barriers removal, wetland reconnection, and transparent public reporting."
    },
    {
      era: "4. Long-Term Stewardship",
      year: "Unified Digital Hub & Public Access (2027+)",
      detail: "Single accessible CMS owned and operated by CSKT DEWR staff connecting Tribal members, water users, partner agencies, and educators to maps, notices, and technical archives."
    }
  ],

  documents: [
    {
      id: "DOC-2026-01",
      title: "[Sample] Annual Reservation Hydrology & Streamflow Summary Report",
      category: "Technical Reports",
      program: "Hydrology & Water Compact",
      year: "2026",
      version: "v2.1 (Tagged Accessible PDF)",
      size: "2.4 MB PDF",
      summary: "Seasonal snowpack, runoff volume, gaging station QA notes, and basin-by-basin hydrographs."
    },
    {
      id: "DOC-2026-02",
      title: "[Sample] Water User Measurement & Headgate Turnout Information Guide",
      category: "Forms & Water Users",
      program: "Irrigation Modernization",
      year: "2026",
      version: "v1.4 (Fillable PDF + Web Form)",
      size: "640 KB PDF",
      summary: "Plain-language guide for irrigators, landowners, and Allottees on diversion measurement schedules and field contacts."
    },
    {
      id: "DOC-2026-03",
      title: "[Sample] Public Meeting Notice & Watershed Restoration Presentation Packet",
      category: "Public Notices",
      program: "Stream & Fishery Restoration",
      year: "2026",
      version: "v1.0",
      size: "1.8 MB PDF",
      summary: "Community open-house agenda, before-and-after channel cross-sections, and public comment instructions."
    },
    {
      id: "DOC-2025-04",
      title: "[Sample] Construction Contracting & Engineering Standard Specifications Overview",
      category: "Procurement & Engineering",
      program: "Engineering & Infrastructure",
      year: "2025",
      version: "v3.0",
      size: "3.1 MB PDF",
      summary: "Reference package for civil consultants, construction bidders, and Indian Preference Office coordination."
    },
    {
      id: "DOC-2025-05",
      title: "[Sample] CSKT–Montana Water Compact Educational FAQ for Classrooms & Residents",
      category: "Educational Materials",
      program: "Public Outreach & Education",
      year: "2025",
      version: "v1.2",
      size: "920 KB PDF",
      summary: "Illustrated overview of Tribal water stewardship, watershed ecology, and Compact implementation milestones."
    }
  ],

  staff: [
    {
      name: "[Sample] Program Lead — Division Administration",
      title: "Division Manager",
      area: "Administration & Compact Coordination",
      bio: "Oversees multi-program engineering, hydrology, restoration scheduling, and interagency Water Compact coordination.",
      phone: "406-304-0000 (Sample)",
      email: "dewr-office-sample@example.org"
    },
    {
      name: "[Sample] Information & Education Coordinator",
      title: "Information & Education Program Manager",
      area: "Public Outreach & Education",
      bio: "Leads public notices, community meetings, educational StoryMaps, digital communications, and media inquiries.",
      phone: "406-304-0001 (Sample)",
      email: "outreach-sample@example.org"
    },
    {
      name: "[Sample] Senior Water Resources Engineer",
      title: "Supervisory Civil / Irrigation Engineer",
      area: "Engineering & Infrastructure",
      bio: "Directs canal modernization design, headworks rehabilitation, construction QA, and contractor submittals.",
      phone: "406-304-0002 (Sample)",
      email: "engineering-sample@example.org"
    },
    {
      name: "[Sample] Lead Watershed Hydrologist & GIS Specialist",
      title: "Hydrology & GIS Lead",
      area: "Hydrology & GIS",
      bio: "Manages basin gaging networks, ArcGIS Online applications, StoryMaps publishing, and hydrologic datasets.",
      phone: "406-304-0003 (Sample)",
      email: "gis-hydrology-sample@example.org"
    }
  ],

  careers: [
    {
      title: "[Sample] Water Resources Civil Engineer (PE / EIT)",
      program: "Engineering & Infrastructure · Ronan, MT",
      type: "Full-Time Tribal Government Position",
      note: "Supports irrigation modernization, hydraulic modeling, and construction inspection. Links directly to official CSKT Personnel application portal."
    },
    {
      title: "[Sample] Hydrologic Technician — Field Gaging & Telemetry",
      program: "Hydrology & Water Measurement · Ronan, MT",
      type: "Full-Time / Seasonal Field Role",
      note: "Performs discharge measurements, sensor calibration, and watershed data quality review across the Flathead Reservation."
    },
    {
      title: "[Sample] GIS & Environmental Restoration Specialist",
      program: "Stream Restoration & GIS · Ronan, MT",
      type: "Full-Time Technical Role",
      note: "Maintains ArcGIS Online web maps, field survey layers, and restoration StoryMaps in coordination with CSKT Natural Resources."
    }
  ]
};
