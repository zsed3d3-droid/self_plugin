# Shared browser verification runtime

This small wrapper reuses the existing Playwright capture approach. It introduces no new browser framework or host service. From the repository root:

```sh
npm ci
npx playwright install chromium
```

The dependency is pinned to Playwright1.62.1 by package.json and package-lock.json. Lab services run in their own Docker Compose projects; browser checks are CLI tools.

Set REFERENCE_EVIDENCE_ROOT to an absolute private directory outside this repository before running reference checks. Each run creates a unique additive output directory and retains failures/screenshots. Original private runs are not bundled. Browser automation is a bounded synthetic check, not user research or an accessibility certification.
