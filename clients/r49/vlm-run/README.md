# VLM Run — client pack (round 49, #80)

**Contact:** `hiring@vlm.run`  ·  **Sent:** 2026-10-22  ·  **Message id:** `1a163983cba3616a`  ·  **Subject:** One public release → SBOM diff report (licence + install-hook gate)

The one-pager and pricing were emailed. This folder now also holds the working
backend, so the build is not a promise — it is a thing you can run.

## What is built

Release gate (SBOM diff + licence + install hooks) — 5 capabilities, all covered by tests.

- CycloneDX and minimal SBOM loaders; three-way diff (added / removed / upgraded / licence drift) with version-aware sorting.
- SPDX expression parser with AND/OR precedence and parentheses — so `MIT OR GPL-3.0` passes while `MIT AND GPL-3.0` fails.
- Licence policy: deny-list, allow-list, unknown handling, per-release override.
- Install-hook detector for package.json lifecycle scripts, setup.py, requirements.txt and pyproject.toml, with severity and reason per finding.
- Gate verdict (pass / review / fail) plus a Markdown report and JSON for CI. Exit codes 0/1/2.

## Run it

```bash
cd backend
python3 -m unittest test_release_gate -q  # 35 tests
python3 app.py demo
```

## What is deliberately not built

- Licence data is not fetched from a registry — the SBOM must already carry it (CycloneDX from Syft/Trivy does).
- No transitive-graph analysis beyond what the SBOM contains.
- No GitHub App; it runs as a CLI step, which is what was offered.

## Files

| path | what |
|---|---|
| `backend/` | source, tests, CLI — **private, git-ignored, never emailed before M1** |
| `PRICING.md` | the exact numbers that were sent, no rounding |
| `README.md` | this file |

## Handover rule

`backend/` stays private until M1 is received. After that it is zipped, the
README inside it is regenerated with the customer's name, and the archive is
sent over. Until then, a demo can be run live on a call — that is the whole
point of having it here.
