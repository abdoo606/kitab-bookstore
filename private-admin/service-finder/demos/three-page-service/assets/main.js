(function () {
  "use strict";
  var content = window.SITE_CONTENT || {};

  // Footer year
  var year = document.getElementById("year");
  if (year) year.textContent = new Date().getFullYear();

  // Fill simple text slots: <... data-content="heroTitle">
  document.querySelectorAll("[data-content]").forEach(function (el) {
    var key = el.getAttribute("data-content");
    if (typeof content[key] === "string" && content[key]) el.textContent = content[key];
  });

  // Render services (keeps the static HTML fallbacks if config is missing)
  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  var services = Array.isArray(content.services) ? content.services : [];
  var cards = document.getElementById("service-cards");
  if (cards && services.length) {
    cards.innerHTML = services.map(function (s) {
      return '<article class="card"><h3>' + esc(s.title) + "</h3><p>" + esc(s.text) + "</p></article>";
    }).join("");
  }
  var details = document.getElementById("service-details");
  if (details && services.length) {
    details.innerHTML = services.map(function (s) {
      return '<article class="service"><h2>' + esc(s.title) + "</h2><p>" + esc(s.text) +
        '</p><p class="price">' + esc(s.price || "") + "</p></article>";
    }).join("");
  }

  // Mobile navigation
  var toggle = document.querySelector(".nav-toggle");
  var nav = document.getElementById("site-nav");
  if (toggle && nav) {
    toggle.addEventListener("click", function () {
      var open = nav.classList.toggle("open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
  }

  // Contact form: validation + honeypot + submit-time check (spam signals).
  // These are deterrents, not a guarantee; pair with endpoint-side filtering.
  var form = document.getElementById("contact-form");
  if (!form) return;
  var status = document.getElementById("form-status");
  var loadedAt = Date.now();

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    var name = form.name.value.trim();
    var email = form.email.value.trim();
    var message = form.message.value.trim();

    function fail(text) { status.textContent = text; status.className = "form-status error"; }

    // Honeypot filled or submitted instantly => almost certainly a bot.
    if (form.company_website.value || Date.now() - loadedAt < 3000) {
      status.textContent = "Thanks — your message has been received."; // do not tip off bots
      status.className = "form-status ok";
      form.reset();
      return;
    }
    if (!name) return fail("Please add your name.");
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email)) return fail("Please add a valid email address.");
    if (message.length < 10) return fail("Please tell us a little more (at least a sentence).");

    var payload = { name: name, email: email, topic: form.topic.value, message: message };

    if (!content.formEndpoint) {
      // Demo mode: nothing is sent anywhere. Configure formEndpoint to go live.
      console.info("[demo mode] Form validated, not sent:", payload);
      status.textContent = "Thanks, " + name + " — your message is ready to send. (Demo mode: no email was sent yet. See README.md to connect delivery.)";
      status.className = "form-status ok";
      form.reset();
      return;
    }

    status.textContent = "Sending…";
    status.className = "form-status";
    fetch(content.formEndpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(payload)
    }).then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      status.textContent = "Thanks, " + name + " — your message has been sent. We reply within one working day.";
      status.className = "form-status ok";
      form.reset();
    }).catch(function () {
      fail("Sorry, sending failed. Please try again in a moment.");
    });
  });
})();
