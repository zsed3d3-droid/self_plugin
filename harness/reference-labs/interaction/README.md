# Interaction reference lab

A synthetic document-review task comparing CSS, Motion, Anime.js, Animate.css and GSAP. Next 16.4.3 App Router, React 19.3.1 client state and Tailwind 4.3.3 are actual compiled dependencies. This is a comparison fixture, not a production product or animation authoring tool.

```sh
cd harness/reference-labs/interaction
docker compose up --build -d
```

Open http://127.0.0.1:8871/ . Health: http://127.0.0.1:8871/health . Compose uses the unique `self-plugin-reference-interaction` project; the container is read-only and stateless. There is no database. Browser-local review state survives browser reloads but does not establish server durability. Use `docker compose stop` to stop; preserve prior results and do not prune or remove volumes/images as part of verification.

The shared task is select a document → hide/show details → cancel or confirm review → change selection → return. State changes immediately; finite animation acknowledges details visibility and never gates confirmation. Each selected mode dynamically imports its own runtime. The full Animate.css stylesheet loads only in that mode. No external runtime service or paid asset is needed.

## Browser checks

From repository root, prepare the shared pinned Playwright runtime once:

```sh
npm ci
npx playwright install chromium
REFERENCE_EVIDENCE_ROOT=/absolute/path/to/private-evidence node harness/reference-labs/interaction/verify.mjs
```

The script uses `harness/browser/playwright.mjs` and defaults to port8871; set `REFERENCE_LAB_BASE` only for another explicitly selected local instance. The output path is required and must be outside this checkout. `INTERACTION_VERIFY_OUTPUT` remains an accepted explicit alias. It retains screenshots, decoded asset sizes, source hashes, errors and interrupted-state observations. The20 cases cover five modes at320/390/1440 and five reduced-motion checks. They check actual intermediate opacity, rapid reversal, one completion per revision, keyboard/cancel/focus, confirmation, selection changes and direct reload. These are fixed-task observations, not FPS, measured human task time or user preference.

## License and evidence boundaries

Read [NOTICE.md](NOTICE.md), exact retained files in `licenses/`, and `package-provenance.json`. The pinned npm Animate.css4.1.1 artifact is MIT while the separately inspected current upstream is Hippocratic2.1. GSAP uses its own current no-charge terms, not MIT; preserve its notices. The Webpack notice banner is deliberately retained after minimization. Fixed Animate.css keyframes restart on reversal; correct final cancellation state is tested, smooth retargeting is not claimed.

Original UI code is copied byte-for-byte; host port, Compose project, verification import/output configuration and documentation differ. `VERIFICATION.json` separately identifies original proof hashes and the checks run against this public package. It contains summaries rather than the original raw reports or absolute workstation paths. Prior private captures/records are not included. A fresh clone still needs Docker to build the application and a browser runtime for the explicit checks.
