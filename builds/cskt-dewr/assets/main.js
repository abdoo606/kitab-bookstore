/* Zero-dependency accessible progressive enhancement for the CSKT DEWR working prototype.
   Addendum #1 build (October 22, 2026).

   Scope of this file:
   1.  Dismissible public-notice banner
   2.  Accessible Before/After restoration slider
   3.  Interactive GIS project explorer + basin SVG map
   4.  Document library filters
   5.  Compact timeline stepper
   6.  Staff / careers filters
   7.  Full-text search across pages, metadata AND text inside PDFs (Addendum Q18), with page numbers
   8.  Public comment form: live deadline cutoff, PDF/DOCX validation, acknowledgement + staff CSV export (Q31)
   9.  Meetings & open houses calendar with upcoming/past filter (Q32)
   10. Source-cited "Seth Bot" Q&A demo that refuses to answer outside its approved corpus (Q48)
   11. Newsletter signup validation (Q30)
   12. Branding concept comparison (Q27)

   PRIVACY: nothing here transmits data anywhere. There is no analytics, no third-party script,
   no cookie, and no network request. Every "submission" stays in this browser tab for the demo. */
(function () {
  "use strict";

  var data = window.DEWR_SAMPLE_DATA || {};
  var byId = function (id) { return document.getElementById(id); };
  var esc = function (s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  };
  var announce = function (el, msg) { if (el) { el.textContent = msg; } };

  /* ------------------------------------------------------------------ 1. BANNER */
  var dismissBtn = byId("dismiss-banner");
  var banner = byId("public-banner");
  if (dismissBtn && banner) {
    dismissBtn.addEventListener("click", function () {
      banner.hidden = true;
      var live = byId("banner-status");
      if (live) { live.textContent = "Public notice banner dismissed."; }
    });
  }

  /* ------------------------------------------------------- 2. BEFORE / AFTER SLIDER */
  var slider = byId("restore-range");
  var afterLayer = byId("compare-after");
  var divider = byId("compare-divider");
  var readout = byId("restore-readout");
  if (slider && afterLayer && divider) {
    var syncSlider = function (val) {
      var pct = Math.max(5, Math.min(95, Number(val) || 50));
      afterLayer.style.clipPath = "inset(0 0 0 " + pct + "%)";
      divider.style.left = pct + "%";
      if (readout) {
        readout.textContent = pct + "% split (left: pre-restoration incised channel · right: restored floodplain & fish screen)";
      }
    };
    slider.addEventListener("input", function (e) { syncSlider(e.target.value); });
    syncSlider(slider.value);
  }

  /* ----------------------------------------------------- 3. INTERACTIVE GIS EXPLORER */
  var mapPinsGroup = byId("map-pins");
  var projectList = byId("project-cards");
  var projectFilter = byId("project-category-filter");
  var activeDetail = byId("active-project-detail");
  var projects = data.projects || [];

  var showProject = function (p) {
    if (!activeDetail || !p) { return; }
    activeDetail.innerHTML =
      '<h3>' + esc(p.title) + '</h3>' +
      '<p class="doc-meta">' + esc(p.category) + ' · ' + esc(p.basin) + ' · <strong>' + esc(p.status) + '</strong></p>' +
      '<p>' + esc(p.summary) + '</p>' +
      '<p class="doc-meta"><strong>Sample metrics:</strong> ' + esc(p.metrics) + '</p>' +
      '<div class="embed-slot"><strong>ArcGIS embed slot (published by DEWR GIS Analyst)</strong>' +
      'StoryMap / Web App reference: <code>' + esc(p.storymapSlug) + '</code>. ' +
      'Rendered from DEWR\u2019s own ArcGIS Online organisation \u2014 no contractor account access (Addendum Q25).</div>';
  };

  if (projectList || mapPinsGroup) {
    var render = function () {
      var cat = projectFilter ? projectFilter.value : "ALL";
      var visible = projects.filter(function (p) { return cat === "ALL" || p.category === cat; });

      if (projectList) {
        projectList.innerHTML = visible.map(function (p) {
          return '<article class="card"><div><span class="badge">' + esc(p.category) + '</span>' +
            '<h3>' + esc(p.title) + '</h3><p>' + esc(p.summary) + '</p></div>' +
            '<a href="#" data-project="' + esc(p.id) + '">Open project summary &rarr;</a></article>';
        }).join("") || '<p class="empty-state">No sample projects in this category.</p>';
        Array.prototype.forEach.call(projectList.querySelectorAll("[data-project]"), function (a) {
          a.addEventListener("click", function (ev) {
            ev.preventDefault();
            var p = projects.filter(function (x) { return x.id === a.getAttribute("data-project"); })[0];
            showProject(p);
            if (activeDetail) { activeDetail.scrollIntoView({ block: "nearest" }); }
          });
        });
      }

      if (mapPinsGroup) {
        mapPinsGroup.innerHTML = visible.map(function (p) {
          return '<g class="map-pin" data-project="' + esc(p.id) + '" tabindex="0" role="button" ' +
            'aria-label="' + esc(p.title) + '">' +
            '<circle cx="' + p.x + '" cy="' + p.y + '" r="13" fill="#c08a2e" stroke="#0f2430" stroke-width="3"></circle>' +
            '<circle cx="' + p.x + '" cy="' + p.y + '" r="4" fill="#0f2430"></circle></g>';
        }).join("");
        Array.prototype.forEach.call(mapPinsGroup.querySelectorAll("[data-project]"), function (g) {
          var open = function () {
            var p = projects.filter(function (x) { return x.id === g.getAttribute("data-project"); })[0];
            showProject(p);
          };
          g.addEventListener("click", open);
          g.addEventListener("keydown", function (e) {
            if (e.key === "Enter" || e.key === " ") { e.preventDefault(); open(); }
          });
        });
      }
    };
    if (projectFilter) { projectFilter.addEventListener("change", render); }
    render();
    showProject(projects[0]);
  }

  /* -------------------------------------------------------- 4. DOCUMENT LIBRARY FILTER */
  var docSearch = byId("doc-search");
  var docCategory = byId("doc-category");
  var docYear = byId("doc-year");
  var docList = byId("doc-list");
  var docCount = byId("doc-count");
  var docs = data.documents || [];

  if (docList) {
    var renderDocs = function () {
      var q = (docSearch ? docSearch.value : "").trim().toLowerCase();
      var cat = docCategory ? docCategory.value : "ALL";
      var yr = docYear ? docYear.value : "ALL";
      var hits = docs.filter(function (d) {
        var hay = (d.title + " " + d.summary + " " + d.category + " " + d.program + " " + d.version).toLowerCase();
        return (!q || hay.indexOf(q) !== -1) &&
          (cat === "ALL" || d.category === cat) &&
          (yr === "ALL" || d.year === yr);
      });
      docList.innerHTML = hits.map(function (d) {
        return '<li class="doc-item"><div><span class="badge">' + esc(d.category) + '</span>' +
          '<h3>' + esc(d.title) + '</h3><p>' + esc(d.summary) + '</p>' +
          '<p class="doc-meta">' + esc(d.id) + ' · ' + esc(d.program) + ' · ' + esc(d.year) + ' · ' +
          esc(d.version) + ' · ' + esc(d.size) + '</p></div>' +
          '<a href="#doc-library">View record &rarr;</a></li>';
      }).join("") || '<li class="empty-state">No sample documents match those filters.</li>';
      if (docCount) { docCount.textContent = hits.length + " of " + docs.length + " sample documents shown."; }
    };
    [docSearch, docCategory, docYear].forEach(function (el) { if (el) { el.addEventListener("input", renderDocs); } });
    renderDocs();
  }

  /* --------------------------------------------------------------- 5. COMPACT TIMELINE */
  var timelineSteps = data.timeline || [];
  var tlButtons = byId("timeline-buttons");
  var tlPanel = byId("timeline-detail");
  if (tlButtons && tlPanel && timelineSteps.length) {
    tlButtons.innerHTML = timelineSteps.map(function (t, i) {
      return '<button type="button" class="timeline-btn" data-step="' + i + '" aria-pressed="' + (i === 0) + '">' + esc(t.era) + '</button>';
    }).join("");
    var showStep = function (i) {
      var t = timelineSteps[i];
      tlPanel.innerHTML = '<h3>' + esc(t.year) + '</h3><p>' + esc(t.detail) + '</p>';
      Array.prototype.forEach.call(tlButtons.querySelectorAll("button"), function (b) {
        b.setAttribute("aria-pressed", String(Number(b.getAttribute("data-step")) === i));
      });
    };
    Array.prototype.forEach.call(tlButtons.querySelectorAll("button"), function (b) {
      b.addEventListener("click", function () { showStep(Number(b.getAttribute("data-step"))); });
    });
    showStep(0);
  }

  /* --------------------------------------------------------- 6. STAFF / CAREERS FILTER */
  var staffFilter = byId("staff-area-filter");
  var staffList = byId("staff-list");
  var staff = data.staff || [];
  if (staffList) {
    var renderStaff = function () {
      var area = staffFilter ? staffFilter.value : "ALL";
      staffList.innerHTML = staff.filter(function (s) { return area === "ALL" || s.area === area; })
        .map(function (s) {
          return '<article class="card"><div><span class="badge">' + esc(s.area) + '</span>' +
            '<h3>' + esc(s.name) + '</h3><p class="doc-meta">' + esc(s.title) + '</p><p>' + esc(s.bio) + '</p>' +
            '<p class="doc-meta">' + esc(s.phone) + ' · ' + esc(s.email) + '</p></div></article>';
        }).join("") || '<p class="empty-state">No sample staff in this program area.</p>';
    };
    if (staffFilter) { staffFilter.addEventListener("change", renderStaff); }
    renderStaff();
  }

  /* ============================================================ 7. FULL-TEXT SEARCH (Q18)
     Searches page copy, document metadata, AND the extracted text of each PDF page,
     returning the matching page number — exactly what the base proposal must deliver. */
  var ftInput = byId("site-search-input");
  var ftResults = byId("site-search-results");
  var ftStatus = byId("site-search-status");
  var ftScope = byId("site-search-scope");

  var snippet = function (text, term) {
    var lower = text.toLowerCase();
    var at = lower.indexOf(term);
    if (at === -1) { return esc(text.slice(0, 190)) + (text.length > 190 ? "\u2026" : ""); }
    var start = Math.max(0, at - 70);
    var end = Math.min(text.length, at + term.length + 110);
    var raw = (start > 0 ? "\u2026" : "") + text.slice(start, end) + (end < text.length ? "\u2026" : "");
    return esc(raw).replace(new RegExp("(" + term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + ")", "gi"), "<mark>$1</mark>");
  };

  var runSearch = function (term) {
    if (!ftResults) { return; }
    var q = (term || "").trim().toLowerCase();
    if (q.length < 2) {
      ftResults.innerHTML = "";
      announce(ftStatus, "Type at least two characters to search pages, document metadata, and the text inside PDFs.");
      return;
    }
    var scope = ftScope ? ftScope.value : "ALL";
    var out = [];
    var idx = data.searchIndex || [];

    idx.forEach(function (entry) {
      var isPdf = entry.kind === "PDF";
      if ((scope === "PAGES" && isPdf) || (scope === "PDFS" && !isPdf)) { return; }

      if (!isPdf) {
        var hay = (entry.title + " " + entry.meta + " " + entry.body).toLowerCase();
        if (hay.indexOf(q) !== -1) {
          out.push({ kind: entry.kind, title: entry.title, url: entry.url, meta: entry.meta, body: snippet(entry.body, q), page: null });
        }
        return;
      }

      // PDF: match metadata and, failing that, the page-level extracted text.
      var metaHay = (entry.title + " " + entry.meta).toLowerCase();
      var pageHit = (entry.pages || []).filter(function (p) { return p.text.toLowerCase().indexOf(q) !== -1; })[0];
      if (metaHay.indexOf(q) !== -1 || pageHit) {
        out.push({
          kind: "PDF",
          title: entry.title,
          url: entry.url,
          meta: entry.meta,
          body: pageHit ? snippet(pageHit.text, q) : snippet(entry.meta, q),
          page: pageHit ? pageHit.page : null
        });
      }
    });

    if (!out.length) {
      ftResults.innerHTML = '<li class="empty-state">No match for <strong>' + esc(term) + '</strong> in this demo corpus. On the live site the same query would run against all ' +
        ((data.meta && data.meta.migrationCounts && data.meta.migrationCounts.publishedPages) || 33) +
        ' published pages plus the OCR text of every migrated PDF.</li>';
      announce(ftStatus, "No results found.");
      return;
    }

    ftResults.innerHTML = out.map(function (r) {
      return '<li class="result-item"><span class="result-kind' + (r.kind === "PDF" ? " is-pdf" : "") + '">' + esc(r.kind) + '</span>' +
        '<h3><a href="' + esc(r.url) + '">' + esc(r.title) + '</a></h3>' +
        '<p class="result-meta">' + esc(r.meta) + (r.page ? ' · <strong>Matched on PDF page ' + esc(r.page) + '</strong>' : '') + '</p>' +
        '<p>' + r.body + '</p></li>';
    }).join("");
    announce(ftStatus, out.length + " result" + (out.length === 1 ? "" : "s") + " for \u201c" + term + "\u201d" +
      (out.filter(function (r) { return r.page; }).length ? " (including text found inside PDF pages)." : "."));
  };

  if (ftInput) {
    var debounce;
    ftInput.addEventListener("input", function () {
      clearTimeout(debounce);
      var v = ftInput.value;
      debounce = setTimeout(function () { runSearch(v); }, 180);
    });
    if (ftScope) { ftScope.addEventListener("change", function () { runSearch(ftInput.value); }); }
    var ftForm = byId("site-search-form");
    if (ftForm) {
      ftForm.addEventListener("submit", function (e) { e.preventDefault(); runSearch(ftInput.value); });
    }
  }

  /* ================================================= 8. PUBLIC COMMENT FORM (Q31)
     Demonstrates: automatic deadline cutoff, DOC/PDF-only attachment validation,
     acknowledgement with reference number, and one-click staff CSV export. */
  var commentForm = byId("public-comment-form");
  var cutoffDeadline = new Date(Date.UTC(2026, 10, 25, 6, 59, 0)); // Nov 25, 2026 11:59 p.m. MT = 06:59 UTC next day
  var submissions = [];
  var refCounter = 0;

  var setCutoffState = function () {
    var badge = byId("cutoff-badge");
    var notice = byId("cutoff-notice");
    var submit = byId("comment-submit");
    var closed = Date.now() > cutoffDeadline.getTime();
    if (badge) {
      badge.textContent = closed
        ? "Comment window CLOSED"
        : "Comment window open · closes " + cutoffDeadline.toLocaleString(undefined, {
            month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit", timeZoneName: "short"
          });
    }
    if (notice) {
      notice.hidden = !closed;
      if (closed) {
        notice.className = "form-alert is-error";
        notice.innerHTML = "<strong>This comment window closed automatically.</strong> The form is locked because the published deadline has passed. Late comments are not accepted into the public record. Contact DEWR directly to find out when the next window opens.";
      }
    }
    if (submit) {
      submit.disabled = closed;
      submit.textContent = closed ? "Comment window closed" : "Submit public comment";
      submit.setAttribute("aria-disabled", String(closed));
    }
    return closed;
  };
  setCutoffState();
  setInterval(setCutoffState, 60000);

  if (commentForm) {
    commentForm.addEventListener("submit", function (e) {
      e.preventDefault();
      var err = byId("comment-error");
      var ok = byId("comment-success");
      if (err) { err.hidden = true; }
      if (ok) { ok.hidden = true; }

      if (setCutoffState()) { return; }

      var name = (byId("c-name") || {}).value || "";
      var email = (byId("c-email") || {}).value || "";
      var topic = (byId("c-topic") || {}).value || "";
      var body = (byId("c-body") || {}).value || "";
      var fileInput = byId("c-file");
      var consent = byId("c-consent");
      var problems = [];

      if (name.trim().length < 2) { problems.push("Enter your full name."); }
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email.trim())) { problems.push("Enter a valid email address."); }
      if (body.trim().length < 20) { problems.push("Your comment must be at least 20 characters so staff can act on it."); }
      if (consent && !consent.checked) { problems.push("Confirm you understand your comment becomes part of the public record."); }

      if (fileInput && fileInput.files && fileInput.files.length) {
        var f = fileInput.files[0];
        var ext = f.name.split(".").pop().toLowerCase();
        if (["pdf", "doc", "docx"].indexOf(ext) === -1) { problems.push("Attachments must be PDF, DOC, or DOCX."); }
        if (f.size > 25 * 1024 * 1024) { problems.push("Attachment must be 25 MB or smaller."); }
      }

      if (problems.length) {
        if (err) {
          err.hidden = false;
          err.className = "form-alert is-error";
          err.innerHTML = "<strong>Please fix " + problems.length + " item" + (problems.length === 1 ? "" : "s") + ":</strong><ul>" +
            problems.map(function (p) { return "<li>" + esc(p) + "</li>"; }).join("") + "</ul>";
          err.setAttribute("tabindex", "-1");
          err.focus();
        }
        return;
      }

      refCounter += 1;
      var ref = "DEWR-CMT-2026-" + String(refCounter).padStart(4, "0");
      var fileName = (fileInput && fileInput.files && fileInput.files.length) ? fileInput.files[0].name : "";
      submissions.push({
        ref: ref,
        name: name.trim(),
        email: email.trim(),
        topic: topic,
        body: body.trim(),
        attachment: fileName || "(none)",
        received: new Date().toISOString()
      });

      if (ok) {
        ok.hidden = false;
        ok.className = "form-alert is-ok";
        ok.innerHTML = "<strong>Recorded (demo only — nothing left this browser).</strong> Reference <code>" + ref +
          "</code>. On the live site this action stores the entry in the CMS, emails an acknowledgement to the address you gave, " +
          "and notifies the assigned DEWR staff member. Your comment and any attachment become part of the public record.";
        ok.setAttribute("tabindex", "-1");
        ok.focus();
      }
      commentForm.reset();
      renderExportState();
    });
  }

  var renderExportState = function () {
    var btn = byId("export-csv");
    var count = byId("export-count");
    if (count) {
      count.textContent = submissions.length
        ? submissions.length + " demo submission" + (submissions.length === 1 ? "" : "s") + " ready to export."
        : "No demo submissions yet — submit the form above to test the staff export.";
    }
    if (btn) {
      btn.disabled = submissions.length === 0;
      btn.setAttribute("aria-disabled", String(submissions.length === 0));
    }
  };
  renderExportState();

  var csvBtn = byId("export-csv");
  if (csvBtn) {
    csvBtn.addEventListener("click", function () {
      if (!submissions.length) { return; }
      var cols = ["ref", "received", "name", "email", "topic", "attachment", "body"];
      var csv = cols.join(",") + "\r\n" + submissions.map(function (s) {
        return cols.map(function (c) {
          var v = String(s[c] == null ? "" : s[c]).replace(/"/g, '""');
          return '"' + v + '"';
        }).join(",");
      }).join("\r\n");
      var blob = new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8;" });
      var a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = "dewr-public-comments-demo.csv";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setTimeout(function () { URL.revokeObjectURL(a.href); }, 1500);
      announce(byId("export-live"), "CSV export downloaded with " + submissions.length + " rows.");
    });
  }

  /* --------------------------------------------------- 9. MEETINGS CALENDAR (Q32) */
  var meetingList = byId("meeting-list");
  var meetingFilter = byId("meeting-filter");
  var meetings = data.meetings || [];
  if (meetingList) {
    var renderMeetings = function () {
      var f = meetingFilter ? meetingFilter.value : "UPCOMING";
      var rows = meetings.filter(function (m) {
        return f === "ALL" || (f === "UPCOMING" && m.status === "Upcoming") || (f === "PAST" && m.status === "Past");
      });
      meetingList.innerHTML = rows.map(function (m) {
        var d = new Date(m.date + "T12:00:00");
        var closed = m.commentWindow.indexOf("Closed") === 0;
        return '<li class="meeting-item' + (m.status === "Past" ? " is-past" : "") + '">' +
          '<div class="meeting-date"><time datetime="' + esc(m.date) + '">' +
          d.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" }) + '</time></div>' +
          '<div class="meeting-body"><h3>' + esc(m.title) + '</h3>' +
          '<p>' + esc(m.time) + ' · ' + esc(m.location) + ' · ' + esc(m.type) + '</p>' +
          '<span class="comment-window' + (closed ? " is-closed" : "") + '">' +
          (closed ? "Comment window closed" : "Comment window open · " + esc(m.commentWindow)) + '</span></div></li>';
      }).join("") || '<li class="empty-state">No sample meetings in this view.</li>';
    };
    if (meetingFilter) { meetingFilter.addEventListener("change", renderMeetings); }
    renderMeetings();
  }

  /* ------------------------------------------------------ 10. SETH BOT Q&A (Q48) */
  var botForm = byId("bot-form");
  var botInput = byId("bot-input");
  var botLog = byId("bot-log");

  var botAnswer = function (question) {
    var q = question.toLowerCase();
    var entries = (data.sethBot && data.sethBot.entries) || [];
    var scored = entries.map(function (e) {
      var score = 0;
      e.keywords.forEach(function (k) { if (q.indexOf(k) !== -1) { score += k.length; } });
      if (q.indexOf(e.question.toLowerCase().slice(0, 24)) !== -1) { score += 40; }
      return { e: e, score: score };
    }).sort(function (a, b) { return b.score - a.score; });

    if (!scored.length || scored[0].score < 3) {
      return {
        text: "I can only answer from DEWR-approved source documents, and I don\u2019t have an approved passage that covers that question. Rather than guess, I\u2019d rather hand this to a person: contact DEWR directly and a staff member will respond. (Demonstration guardrail: unsupported questions are refused, never invented.)",
        cites: []
      };
    }
    var e = scored[0].e;
    return {
      text: e.answer,
      cites: e.citations.map(function (c) {
        var s = (data.sethBot.sources || {})[c.source] || { label: c.source, url: "#" };
        return '<a href="' + esc(s.url) + '" rel="noopener">' + esc(s.label) + "</a> · " + esc(c.page);
      })
    };
  };

  var pushMsg = function (text, who, cites) {
    if (!botLog) { return; }
    var div = document.createElement("div");
    div.className = "bot-msg " + (who === "user" ? "is-user" : "is-bot");
    var html = "<p>" + esc(text) + "</p>";
    if (cites && cites.length) {
      html += '<div class="bot-cites"><strong>Sources cited:</strong><ul style="margin:0.25rem 0 0;padding-left:1.1rem">' +
        cites.map(function (c) { return "<li>" + c + "</li>"; }).join("") + "</ul></div>";
    }
    if (who === "bot" && !(cites && cites.length)) {
      html += '<div class="bot-cites"><strong>No approved source matched.</strong> Escalated to DEWR staff instead of guessing.</div>';
    }
    div.innerHTML = html;
    botLog.appendChild(div);
    botLog.scrollTop = botLog.scrollHeight;
  };

  if (botForm) {
    botForm.addEventListener("submit", function (e) {
      e.preventDefault();
      var q = (botInput.value || "").trim();
      if (q.length < 3) { return; }
      pushMsg(q, "user");
      var a = botAnswer(q);
      setTimeout(function () {
        pushMsg(a.text, "bot", a.cites);
        announce(byId("bot-status"), "Seth Bot replied. " + (a.cites.length ? a.cites.length + " source cited." : "No approved source matched; routed to staff."));
      }, 260);
      botInput.value = "";
    });
    Array.prototype.forEach.call(document.querySelectorAll("[data-bot-q]"), function (chip) {
      chip.addEventListener("click", function () {
        if (!botInput) { return; }
        botInput.value = chip.getAttribute("data-bot-q");
        botForm.dispatchEvent(new Event("submit", { cancelable: true }));
      });
    });
  }

  /* ------------------------------------------------------ 11. NEWSLETTER SIGNUP (Q30) */
  var nlForm = byId("newsletter-form");
  if (nlForm) {
    nlForm.addEventListener("submit", function (e) {
      e.preventDefault();
      var email = (byId("nl-email") || {}).value || "";
      var msg = byId("nl-status");
      var topics = Array.prototype.slice.call(document.querySelectorAll('input[name="nl-topic"]:checked'))
        .map(function (c) { return c.value; });
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email.trim())) {
        if (msg) {
          msg.hidden = false;
          msg.className = "form-alert is-error";
          msg.textContent = "Enter a valid email address so DEWR can send the confirmation link.";
        }
        return;
      }
      if (msg) {
        msg.hidden = false;
        msg.className = "form-alert is-ok";
        msg.textContent = "Demo only: nothing was sent or stored. On the live site this performs the double opt-in flow — " +
          "a confirmation email to " + email.trim() + " selecting " +
          (topics.length ? topics.length + " topic group(s)" : "all notices") +
          ", an unsubscribe link in every issue, and a stored consent record with its timestamp.";
      }
      nlForm.reset();
    });
  }

  /* -------------------------------------------------- 12. BRANDING CONCEPT COMPARE (Q27) */
  Array.prototype.forEach.call(document.querySelectorAll("[data-concept-select]"), function (btn) {
    btn.addEventListener("click", function () {
      var id = btn.getAttribute("data-concept-select");
      Array.prototype.forEach.call(document.querySelectorAll(".concept-card"), function (card) {
        card.classList.toggle("is-selected", card.getAttribute("data-concept") === id);
      });
      announce(byId("concept-status"), "Concept " + id.replace("concept-", "").toUpperCase() +
        " selected for the shortlist. On the live site this records the preference against the DEWR reviewer's account.");
    });
  });
})();
