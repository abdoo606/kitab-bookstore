(function () {
  "use strict";
  document.querySelectorAll("[data-year]").forEach(function (el) {
    el.textContent = String(new Date().getFullYear());
  });
  var toggle = document.querySelector("[data-nav-toggle]");
  var nav = document.getElementById("site-nav");
  if (toggle && nav) {
    toggle.addEventListener("click", function () {
      var open = nav.classList.toggle("open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
  }
  // Concept forms never send or store anything.
  document.querySelectorAll("[data-concept-form]").forEach(function (form) {
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var status = form.querySelector("[data-form-status]");
      if (status) status.textContent = "Concept only: nothing was sent or stored. In production this would use a GDPR-compliant, double-opt-in newsletter/payment service hosted or processed under an EU data-processing agreement.";
    });
  });
  // Members-only DEMO toggle (no real authentication in this concept).
  var memberBtn = document.querySelector("[data-member-demo]");
  var memberPanel = document.getElementById("member-panel");
  if (memberBtn && memberPanel) {
    memberBtn.addEventListener("click", function () {
      var willShow = memberPanel.hidden;
      memberPanel.hidden = !willShow;
      memberBtn.setAttribute("aria-expanded", willShow ? "true" : "false");
      memberBtn.textContent = willShow ? "Hide members-only demo" : "Preview members-only area (demo)";
    });
  }
  // Events agenda + archive (events.html only)
  var upcomingBox = document.querySelector("[data-upcoming]");
  var archiveBox = document.querySelector("[data-archive-list]");
  if ((upcomingBox || archiveBox) && Array.isArray(window.MSA_EVENTS)) {
    var fmt = function (iso) {
      return new Date(iso + "T12:00:00").toLocaleDateString("en-GB", { year: "numeric", month: "long", day: "numeric" });
    };
    var card = function (ev, withRegister) {
      var a = document.createElement("article"); a.className = "event-card";
      var when = document.createElement("p"); when.className = "event-date";
      var t = document.createElement("time"); t.dateTime = ev.date; t.textContent = fmt(ev.date);
      when.appendChild(t); when.appendChild(document.createTextNode(" · " + ev.venue + " · " + ev.kind));
      var h = document.createElement("h3"); h.textContent = ev.title;
      var m = document.createElement("p"); m.className = "meta"; m.textContent = ev.meta;
      var s = document.createElement("p"); s.textContent = ev.summary;
      a.append(when, h, m, s);
      if (withRegister) {
        var p = document.createElement("p");
        var b = document.createElement("button"); b.type = "button"; b.className = "btn"; b.textContent = "Register (placeholder)";
        b.addEventListener("click", function () { b.textContent = "In production: member login → registration"; });
        var n = document.createElement("span"); n.className = "note"; n.textContent = " → members-only registration / conference platform in production";
        p.append(b, n); a.appendChild(p);
      }
      return a;
    };
    var upcoming = window.MSA_EVENTS.filter(function (e) { return e.status === "upcoming"; }).sort(function (a, b) { return a.date < b.date ? -1 : 1; });
    var past = window.MSA_EVENTS.filter(function (e) { return e.status === "past"; }).sort(function (a, b) { return a.date > b.date ? -1 : 1; });
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
        if (q && (e.title + " " + e.meta + " " + e.summary + " " + e.kind).toLowerCase().indexOf(q) === -1) return false;
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
