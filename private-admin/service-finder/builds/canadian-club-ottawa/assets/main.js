(function () {
  "use strict";
  // Footer year
  document.querySelectorAll("[data-year]").forEach(function (el) {
    el.textContent = String(new Date().getFullYear());
  });
  // Mobile nav toggle
  var toggle = document.querySelector("[data-nav-toggle]");
  var nav = document.getElementById("site-nav");
  if (toggle && nav) {
    toggle.addEventListener("click", function () {
      var open = nav.classList.toggle("open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
  }
  // Concept contact form: never sends anything
  var form = document.querySelector("[data-concept-form]");
  if (form) {
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var status = form.querySelector("[data-form-status]");
      if (form.company && form.company.value) { status.textContent = ""; return; } // honeypot
      status.textContent = "Concept only: this sample form does not send or store anything. In production it would deliver to the Club's inbox via a tested, spam-protected form service.";
    });
  }
  // Events rendering (events.html only)
  var upcomingBox = document.querySelector("[data-upcoming]");
  var archiveBox = document.querySelector("[data-archive-list]");
  if ((upcomingBox || archiveBox) && Array.isArray(window.CCO_EVENTS)) {
    var fmt = function (iso) {
      var d = new Date(iso + "T12:00:00");
      return d.toLocaleDateString("en-CA", { year: "numeric", month: "long", day: "numeric" });
    };
    var card = function (ev, withRegister) {
      var a = document.createElement("article");
      a.className = "event-card";
      var when = document.createElement("p"); when.className = "event-date";
      var t = document.createElement("time"); t.dateTime = ev.date; t.textContent = fmt(ev.date);
      when.appendChild(t); when.appendChild(document.createTextNode(" · " + ev.venue));
      var h = document.createElement("h3"); h.textContent = ev.title;
      var sp = document.createElement("p"); sp.className = "speaker"; sp.textContent = ev.speaker;
      var s = document.createElement("p"); s.textContent = ev.summary;
      a.append(when, h, sp, s);
      if (withRegister) {
        var p = document.createElement("p");
        var link = document.createElement("a"); link.className = "btn"; link.href = "#"; link.textContent = "Register (placeholder)";
        link.addEventListener("click", function (e) { e.preventDefault(); });
        var note = document.createElement("span"); note.className = "note"; note.textContent = " → Club's ticketing platform in production";
        p.append(link, note); a.appendChild(p);
      }
      return a;
    };
    var upcoming = window.CCO_EVENTS.filter(function (e) { return e.status === "upcoming"; })
      .sort(function (a, b) { return a.date < b.date ? -1 : 1; });
    var past = window.CCO_EVENTS.filter(function (e) { return e.status === "past"; })
      .sort(function (a, b) { return a.date > b.date ? -1 : 1; });
    if (upcomingBox) upcoming.forEach(function (e) { upcomingBox.appendChild(card(e, true)); });
    var yearSel = document.querySelector("[data-year-filter]");
    var search = document.querySelector("[data-search]");
    var count = document.querySelector("[data-count]");
    var years = Array.from(new Set(past.map(function (e) { return e.date.slice(0, 4); }))).sort().reverse();
    if (yearSel) years.forEach(function (y) { var o = document.createElement("option"); o.value = y; o.textContent = y; yearSel.appendChild(o); });
    var renderArchive = function () {
      if (!archiveBox) return;
      var yv = yearSel ? yearSel.value : "";
      var q = search ? search.value.trim().toLowerCase() : "";
      var rows = past.filter(function (e) {
        if (yv && e.date.slice(0, 4) !== yv) return false;
        if (q && (e.title + " " + e.speaker + " " + e.summary).toLowerCase().indexOf(q) === -1) return false;
        return true;
      });
      archiveBox.innerHTML = "";
      rows.forEach(function (e) { archiveBox.appendChild(card(e, false)); });
      if (count) count.textContent = rows.length + " sample archive entr" + (rows.length === 1 ? "y" : "ies") + " shown.";
      if (!rows.length) archiveBox.innerHTML = "<p>No sample entries match. Try clearing the filters.</p>";
    };
    if (yearSel) yearSel.addEventListener("change", renderArchive);
    if (search) search.addEventListener("input", renderArchive);
    var ff = document.querySelector("[data-filter-form]");
    if (ff) ff.addEventListener("submit", function (e) { e.preventDefault(); });
    renderArchive();
  }
})();
