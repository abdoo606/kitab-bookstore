/* Zero-dependency accessible progressive enhancement for CSKT DEWR working prototype.
   All interactive widgets are keyboard accessible, announce updates via ARIA live regions,
   and never transmit user input externally. */
(function () {
  "use strict";

  var data = window.DEWR_SAMPLE_DATA || { projects: [], timeline: [], documents: [], staff: [], careers: [] };

  /* 1. Dismissible Public Meeting / Advisory Banner (Section 5.10) */
  var dismissBtn = document.getElementById("dismiss-banner");
  var banner = document.getElementById("public-banner");
  if (dismissBtn && banner) {
    dismissBtn.addEventListener("click", function () {
      banner.hidden = true;
    });
  }

  /* 2. Accessible Before-and-After Restoration Slider (Section 4.6 & 5.7) */
  var slider = document.getElementById("restore-range");
  var afterLayer = document.getElementById("compare-after");
  var divider = document.getElementById("compare-divider");
  var readout = document.getElementById("restore-readout");
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

  /* 3. Interactive GIS Project Explorer + Basin SVG Map (Section 5.7 & 5.11) */
  var mapPinsGroup = document.getElementById("map-pins");
  var projectList = document.getElementById("project-cards");
  var projectFilter = document.getElementById("project-category-filter");
  var activeDetail = document.getElementById("active-project-detail");

  function renderProjectInspector(proj) {
    if (!activeDetail || !proj) return;
    activeDetail.innerHTML = "";
    var badge = document.createElement("span");
    badge.className = "badge badge-pine";
    badge.textContent = proj.category + " · " + proj.status;

    var h3 = document.createElement("h3");
    h3.textContent = proj.title;

    var basin = document.createElement("p");
    basin.innerHTML = "<strong>Watershed / Area:</strong> " + proj.basin;

    var desc = document.createElement("p");
    desc.textContent = proj.summary;

    var metrics = document.createElement("p");
    metrics.innerHTML = "<strong>Key Indicators:</strong> " + proj.metrics;

    var slot = document.createElement("div");
    slot.className = "status-note";
    slot.innerHTML = "<strong>ArcGIS Online / StoryMaps CMS Embed Slot:</strong> <code>" +
      proj.storymapSlug +
      "</code> — Staff paste any CSKT ArcGIS WebMap or StoryMap URL in the WordPress editor block; responsive iframe sandboxing, keyboard title, and fallback table load automatically.";

    activeDetail.appendChild(badge);
    activeDetail.appendChild(h3);
    activeDetail.appendChild(basin);
    activeDetail.appendChild(desc);
    activeDetail.appendChild(metrics);
    activeDetail.appendChild(slot);
  }

  function renderProjects() {
    if (!projectList) return;
    var selectedCat = projectFilter ? projectFilter.value : "ALL";
    var filtered = data.projects.filter(function (p) {
      return selectedCat === "ALL" || p.category === selectedCat;
    });

    projectList.innerHTML = "";
    if (mapPinsGroup) mapPinsGroup.innerHTML = "";

    filtered.forEach(function (p, idx) {
      var card = document.createElement("article");
      card.className = "card";
      var top = document.createElement("div");
      top.innerHTML = '<span class="badge">' + p.category + "</span><h3>" + p.title + "</h3><p>" + p.summary + "</p>";
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "btn btn-river";
      btn.textContent = "Inspect GIS Layer & StoryMap Slot";
      btn.addEventListener("click", function () { renderProjectInspector(p); });
      card.appendChild(top);
      card.appendChild(btn);
      projectList.appendChild(card);

      if (mapPinsGroup) {
        var g = document.createElementNS("http://www.w3.org/2000/svg", "g");
        g.setAttribute("class", "map-pin");
        g.setAttribute("tabindex", "0");
        g.setAttribute("role", "button");
        g.setAttribute("aria-label", p.title + " in " + p.basin);
        g.setAttribute("aria-pressed", idx === 0 ? "true" : "false");

        var circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
        circle.setAttribute("cx", String(p.x));
        circle.setAttribute("cy", String(p.y));
        circle.setAttribute("r", "11");
        circle.setAttribute("fill", "#0d4f6b");
        circle.setAttribute("stroke", "#ffffff");
        circle.setAttribute("stroke-width", "2.5");

        var label = document.createElementNS("http://www.w3.org/2000/svg", "text");
        label.setAttribute("x", String(p.x + 15));
        label.setAttribute("y", String(p.y + 4));
        label.setAttribute("fill", "#0f2430");
        label.setAttribute("font-size", "12");
        label.setAttribute("font-weight", "700");
        label.textContent = p.basin.split("/")[0].trim();

        var activate = function () {
          Array.prototype.forEach.call(mapPinsGroup.children, function (el) {
            el.setAttribute("aria-pressed", "false");
          });
          g.setAttribute("aria-pressed", "true");
          renderProjectInspector(p);
        };
        g.addEventListener("click", activate);
        g.addEventListener("keydown", function (ev) {
          if (ev.key === "Enter" || ev.key === " ") {
            ev.preventDefault();
            activate();
          }
        });

        g.appendChild(circle);
        g.appendChild(label);
        mapPinsGroup.appendChild(g);
      }
    });

    if (filtered.length > 0) renderProjectInspector(filtered[0]);
  }

  if (projectFilter) projectFilter.addEventListener("change", renderProjects);
  renderProjects();

  /* 4. Interactive Educational Compact Timeline (Section 5.7) */
  var timelineBtns = document.getElementById("timeline-steps");
  var timelineCard = document.getElementById("timeline-panel");
  if (timelineBtns && timelineCard && data.timeline.length) {
    var showStep = function (index) {
      var item = data.timeline[index];
      Array.prototype.forEach.call(timelineBtns.children, function (b, i) {
        b.setAttribute("aria-selected", i === index ? "true" : "false");
      });
      timelineCard.innerHTML =
        '<span class="badge badge-ochre">' + item.year + "</span>" +
        "<h3>" + item.era + "</h3>" +
        "<p>" + item.detail + "</p>";
    };
    data.timeline.forEach(function (step, idx) {
      var b = document.createElement("button");
      b.type = "button";
      b.className = "timeline-btn";
      b.setAttribute("role", "tab");
      b.setAttribute("aria-selected", idx === 0 ? "true" : "false");
      b.textContent = step.era;
      b.addEventListener("click", function () { showStep(idx); });
      timelineBtns.appendChild(b);
    });
    showStep(0);
  }

  /* 5. Searchable & Filterable Document Library + Staff & Careers (Sections 5.6, 5.8, 5.14) */
  var docSearch = document.getElementById("doc-search");
  var docCat = document.getElementById("doc-category");
  var docYear = document.getElementById("doc-year");
  var docResults = document.getElementById("doc-results");
  var docCount = document.getElementById("doc-count");

  function renderDocs() {
    if (!docResults) return;
    var q = (docSearch ? docSearch.value : "").trim().toLowerCase();
    var c = docCat ? docCat.value : "ALL";
    var y = docYear ? docYear.value : "ALL";

    var rows = data.documents.filter(function (d) {
      var matchQ = !q || (d.title + " " + d.summary + " " + d.program + " " + d.id).toLowerCase().indexOf(q) !== -1;
      var matchC = c === "ALL" || d.category === c;
      var matchY = y === "ALL" || d.year === y;
      return matchQ && matchC && matchY;
    });

    if (docCount) {
      docCount.textContent = rows.length + " sample document" + (rows.length === 1 ? "" : "s") + " matched";
    }
    docResults.innerHTML = "";
    rows.forEach(function (d) {
      var row = document.createElement("div");
      row.className = "doc-item";
      row.innerHTML =
        "<div>" +
          '<span class="badge">' + d.category + "</span> " +
          '<span class="badge badge-pine">' + d.year + " · " + d.version + "</span>" +
          '<h3 style="margin:0.4rem 0 0.25rem;font-size:1.05rem;">' + d.title + "</h3>" +
          '<p style="margin:0 0 0.25rem;color:#425460;">' + d.summary + "</p>" +
          '<div class="doc-meta">ID: ' + d.id + " · Program: " + d.program + " · Format: " + d.size + "</div>" +
        "</div>" +
        '<div><span class="badge badge-ochre">Demo Entry</span></div>';
      docResults.appendChild(row);
    });
  }
  if (docSearch) docSearch.addEventListener("input", renderDocs);
  if (docCat) docCat.addEventListener("change", renderDocs);
  if (docYear) docYear.addEventListener("change", renderDocs);
  renderDocs();

  /* Staff Directory & Careers */
  var staffContainer = document.getElementById("staff-grid");
  var staffFilter = document.getElementById("staff-area-filter");
  function renderStaff() {
    if (!staffContainer) return;
    var area = staffFilter ? staffFilter.value : "ALL";
    staffContainer.innerHTML = "";
    data.staff
      .filter(function (s) { return area === "ALL" || s.area === area; })
      .forEach(function (s) {
        var card = document.createElement("article");
        card.className = "card";
        card.innerHTML =
          '<div><span class="badge badge-pine">' + s.area + "</span>" +
          "<h3>" + s.name + "</h3>" +
          "<p><strong>" + s.title + "</strong></p>" +
          "<p>" + s.bio + "</p></div>" +
          '<div class="doc-meta">Phone: ' + s.phone + "<br>Email: " + s.email + "</div>";
        staffContainer.appendChild(card);
      });
  }
  if (staffFilter) staffFilter.addEventListener("change", renderStaff);
  renderStaff();

  var careerContainer = document.getElementById("career-list");
  if (careerContainer) {
    data.careers.forEach(function (job) {
      var item = document.createElement("article");
      item.className = "card";
      item.innerHTML =
        '<div><span class="badge badge-ochre">' + job.type + "</span>" +
        "<h3>" + job.title + "</h3>" +
        "<p><strong>" + job.program + "</strong></p>" +
        "<p>" + job.note + "</p></div>";
      careerContainer.appendChild(item);
    });
  }

  /* 6. Static Safe Public Comment / Meeting Notice Form Demo (Section 5.9) */
  var commentForm = document.getElementById("public-comment-form");
  var commentStatus = document.getElementById("comment-status");
  if (commentForm && commentStatus) {
    commentForm.addEventListener("submit", function (ev) {
      ev.preventDefault();
      var topic = document.getElementById("comment-topic").value;
      commentStatus.hidden = false;
      commentStatus.textContent =
        "Demo preview only (no data sent or stored): In the production WordPress site, your submission on \"" +
        topic +
        "\" generates a reference receipt, notifies the designated DEWR program inbox with spam protection, and exports cleanly to CSV for public-comment records.";
    });
  }
})();
