(function () {
  "use strict";
  var data = window.MANUFACTURERS || [];
  var cards = document.getElementById("cards");
  var empty = document.getElementById("empty");
  var count = document.getElementById("count");
  var q = document.getElementById("q");
  var cat = document.getElementById("cat");
  var chips = document.getElementById("chips");
  var related = document.getElementById("related");

  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  var categories = Array.from(new Set(data.flatMap(function (m) { return m.categories; }))).sort();
  categories.forEach(function (c) {
    var o = document.createElement("option"); o.value = c; o.textContent = c; cat.appendChild(o);
  });

  function card(m) {
    return '<article class="card"><div class="logo-slot" aria-hidden="true">' + esc(m.name.charAt(0)) + "</div>" +
      "<h3>" + esc(m.name) + "</h3><p>" + esc(m.description) + "</p>" +
      '<p class="tags">' + m.categories.map(function (c) { return '<span class="tag">' + esc(c) + "</span>"; }).join(" ") +
      m.applications.map(function (a) { return '<span class="tag tag-app">' + esc(a) + "</span>"; }).join(" ") + "</p>" +
      '<p><a href="' + esc(m.website) + '">Manufacturer website →</a></p></article>';
  }
  function render() {
    var needle = q.value.trim().toLowerCase();
    var chosen = cat.value;
    var shown = data.filter(function (m) {
      var hay = (m.name + " " + m.description + " " + m.categories.join(" ") + " " + m.applications.join(" ")).toLowerCase();
      return (!needle || hay.indexOf(needle) !== -1) && (!chosen || m.categories.indexOf(chosen) !== -1);
    });
    cards.innerHTML = shown.map(card).join("");
    empty.hidden = shown.length > 0;
    count.textContent = shown.length + " of " + data.length + " sample records";
  }
  q.addEventListener("input", render);
  cat.addEventListener("change", render);
  render();

  function showRelated(category, btn) {
    chips.querySelectorAll("button").forEach(function (b) { b.setAttribute("aria-pressed", b === btn ? "true" : "false"); });
    var list = data.filter(function (m) { return m.categories.indexOf(category) !== -1; });
    related.innerHTML = "<h3>" + esc(category) + "</h3>" +
      (list.length ? '<div class="grid">' + list.map(card).join("") + "</div>"
                   : "<p>No sample manufacturers in this category yet.</p>");
  }
  categories.forEach(function (c, i) {
    var b = document.createElement("button");
    b.type = "button"; b.className = "chip"; b.textContent = c; b.setAttribute("aria-pressed", i === 0 ? "true" : "false");
    b.addEventListener("click", function () { showRelated(c, b); });
    chips.appendChild(b);
    if (i === 0) showRelated(c, b);
  });

  var toggle = document.querySelector(".nav-toggle");
  var nav = document.getElementById("site-nav");
  if (toggle && nav) toggle.addEventListener("click", function () {
    var open = nav.classList.toggle("open");
    toggle.setAttribute("aria-expanded", open ? "true" : "false");
  });

  document.querySelectorAll("[data-demo-form]").forEach(function (form) {
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var note = form.querySelector("[data-form-note]");
      if (form.company_website.value) { if (note) note.textContent = "Thanks — received."; form.reset(); return; }
      if (note) note.textContent = "Concept only: validated locally, nothing sent. Production wiring + a real delivery test are part of the full build.";
      form.reset();
    });
  });
})();
