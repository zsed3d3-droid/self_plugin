# Anti-slop / Unslop UI comparison lab

```sh
cd harness/reference-labs/anti-slop
docker compose up --build -d
```

[After](http://127.0.0.1:8873/after.html), [before](http://127.0.0.1:8873/before.html), [countercase](http://127.0.0.1:8873/countercase.html). Docker healthcheck requests `/after.html`; this static server has no `/health` API. Project `self-plugin-reference-anti-slop` is separate from the original private lab. No LLM, login, remote API or saved user state. Read-only/stateless container; no data volume is needed.

Selected rules cover nested boundaries, decorative icon purpose, explicit workflow state, semantic keyboard controls and focus. Countercases preserve meaningful workspace boundaries and owner markers. The fixture deliberately retains BEFORE's keyboard failure as a diagnostic contrast; AFTER and COUNTERCASE implement the intended task. This is not a new product or evidence of adoption in previous products.

From the repository root, run `npm ci` and `npx playwright install chromium`, then:

```sh
REFERENCE_EVIDENCE_ROOT=/absolute/private/reference-checks npm run test:reference:anti-slop
```

Each run creates additive timestamp/UUID screenshots and observation records outside Git. The shared harness/browser/playwright.mjs reuses the original Playwright approach; it starts no host service. REFERENCE_BASE_URL can override the default8873 URL.

Public packaging changes only project/port/helper/evidence-output paths and documentation, not the authored web UI bytes. VERIFICATION.json distinguishes original private evidence from checks actually rerun against this public package. Original screenshots, source/image archives and absolute local paths are not bundled. Read adapter.md, rules.json and WHY.md for conditional adoption, rejected defaults and observed repairs. This package does not establish human completion time, user preference or full accessibility compliance.
