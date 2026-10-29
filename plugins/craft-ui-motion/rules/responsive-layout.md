---
trigger: always_on
description: UI 생성·수정 시 반응형 축소 붕괴, 전역 가로 넘침, 잘못된 스크롤 소유권을 방지한다.
---

# Responsive Layout Gate

When creating or changing UI:

- Inspect the rendered layout at 320px, the failing width, changed breakpoints at b-1/b/b+1, and desktop before claiming completion.
- Classify content before styling: bounded buttons/badges/status/count+unit are atomic (`nowrap`, and `shrink-0` only when they are flex items); prose is flexible; long unbroken tokens need a local wrap escape.
- Every constrained parent needs an explicit escape route: wrap, stack, approved compact state, or a named local scroller. Never hide root-cause overflow with page-level `overflow-x:hidden`, tiny text, global `nowrap`, global `break-all`, or content deletion.
- Preserve semantic data tables. Reuse one bounded horizontal wrapper and give the table a measured readable minimum width instead of squeezing every column into the viewport.
- Search and inline action forms (`form[role="search"]`, `.toolbar-search`): Never let action buttons wrap or drop below the input into vertical stack slop. Enforce `display: flex; gap: 8px; align-items: center;` with `button { flex-shrink: 0; white-space: nowrap; }` and `input { min-width: 0; flex: 1 1 auto; }` so the control maintains a clean, aligned single-line inline form even down to 320px mobile viewports.
- Fixed-aspect graphics & composite viewers (Canvas, PDF.js, SVG, charts): Fit viewport scale dynamically to container width (`effectiveScale = Math.min(baseScale, (clientWidth - padding) / unscaledWidth)`) via ResizeObserver instead of blind CSS squashing; enforce `min-width: 0; max-width: 100%;` on all ancestors to prevent grid/flex overflow explosions.
- List + inspector split views: below the split breakpoint open the inspector as a full-viewport overlay/drawer, never stacked under a long list. Clamp machine-generated text (JSON, logs) with an expand control.
- Normal pages use document scrolling. Internal vertical scroll is allowed only for deliberate, bounded, and accessible regions such as dialogs, drawers, app shells, data grids, listboxes, or code editors; detect actual overflow by geometry, not by the `overflow-y` property alone.
- Report tested widths, long-content cases, root and local overflow measurements, screenshots, and any unverified state.
