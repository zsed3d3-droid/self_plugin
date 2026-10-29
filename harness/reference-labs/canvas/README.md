# Motion Canvas native renderer lab

```sh
cd harness/reference-labs/canvas
docker compose up --build -d
```

Open http://127.0.0.1:8872 . Health: `/health`. Compose project `self-plugin-reference-canvas`, host8872, internal8862, independent `motion-canvas-output` volume. This public package never attaches to the original private lab's volume. Original/runtime data is not copied.

Actual Motion Canvas core/2d3.17.2 Player/Stage renders a synthetic10-second vector explanation. No autoplay. Play/pause, frame seek, explicit step controls, readable HTML transcript and PNG capture are supported. Reduced motion leaves playback paused and offers static steps. PNGs+metadata get unique names and persist under `/data/frames`; the remaining service state is stateless. Stop without deleting volumes.

From repository root, run `npm ci`, `npx playwright install chromium`, then:

```sh
REFERENCE_EVIDENCE_ROOT=/absolute/private/reference-checks npm run test:reference:canvas
```

The shared Playwright wrapper reuses the original browser approach. Unique run outputs stay outside Git. REFERENCE_BASE_URL can override the default8872 URL; the POST Origin whitelist must match any changed browser port.

Package/runtime source bytes remain unchanged for the scene, player, HTML/CSS and lockfile. Public changes are Compose naming/hostport, server Origin whitelist, test import/output URLs and documentation. Original private source manifest and runtime evidence are distinguished in VERIFICATION.json; original screenshots/reports/frames/auth are not bundled.

Review source pin7b91435c301d530351dcf5ebb91dd139c002e405 differs from npm runtime gitHeade735a995aa738ca682feb4204a39ee7db7b5d279. Keep both notices under licenses/. An internal bootstrap/MetaFile bridge is exact-version-specific and requires revalidation on upgrade. The dependency lock retains package integrity values.

This verifies actual fixed-frame rendering and PNG persistence, not encoded video, a full editor, audio synchronization, performance superiority, human preference or deployment in a prior product.
