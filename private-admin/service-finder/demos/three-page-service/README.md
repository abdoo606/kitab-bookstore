# Three-Page Service Website — Demo & Handover Notes

An independent demo built as a work sample for small service-business website requests
(such as Freelancer project 40776894). The business ("Brightpath Consulting"), prices and
copy are fictional placeholders. This is **not** a delivered client project and must not be
described as one.

## Pages
- `index.html` — Home: value statement, hero, service cards, why-us, call to action.
- `services.html` — Services: one section per offering with price/duration hints.
- `contact.html` — Contact: enquiry form with confirmation message.

Standards-compliant HTML/CSS/vanilla JS. Fully responsive (desktop/tablet/mobile),
semantic landmarks, skip link, focus styles, basic SEO + Open Graph meta per page.
No build step and no external assets — it runs offline and on any static host.

## Edit the text (no HTML knowledge needed)
Open `assets/content.js` and change the words between quotes:
- `businessName`, `heroTitle`, `heroText`
- `services` list (title / text / price per service) — add or remove blocks freely
Save and refresh. The HTML files contain the same text as a fallback if JavaScript is off.

To swap images/branding: this demo intentionally uses CSS-only styling (no image files to
break). Add your logo/photos as files and reference them from the HTML, and adjust the
colour variables at the top of `assets/styles.css` (`--brand`, `--ink`, `--alt`).

## Make the contact form deliver email (required before real use)
The demo ships in **demo mode**: the form validates, applies spam checks (honeypot field +
minimum fill-time) and shows a confirmation, but **no email is sent**. To go live:

1. Create a form endpoint that emails you submissions, e.g. Web3Forms or Formspree
   (free tiers exist), or a small mail script on your own hosting.
2. Paste its URL into `formEndpoint` in `assets/content.js`.
3. Submit a real test enquiry and confirm it arrives in your inbox (check spam folder too).
4. Only then remove the "demo mode" hint on `contact.html` if you wish.

Honeypot + timing checks deter basic bots but are not a guarantee; keep the endpoint's
own spam filtering enabled as well.

## Analytics (optional)
`analyticsId` in `assets/content.js` is reserved for a Plausible domain or GA4 ID.
It is empty (disabled) in this demo; add your provider's snippet per its instructions
and re-test page loading afterwards.

## Deploy (any static host)
- Netlify / Vercel / Cloudflare Pages: drag this folder in, no build command.
- GitHub Pages: push the folder contents and enable Pages on the branch.
- Classic hosting: upload the files via FTP keeping the folder structure.

## Local check
```bash
python3 -m http.server 8000   # then open http://localhost:8000
```
Check all three pages at phone width (≈375px) and desktop width, submit the form once
in demo mode, and confirm the confirmation message appears.
