---
name: responsive-layout-guard
description: >-
  Diagnose, implement, and verify responsive web layout fixes when UI clips,
  overflows, collapses into vertical text, squeezes tables or badges, or creates
  accidental nested scrolling. Use for responsive frontend changes and audits.
---

# Responsive Layout Guard

Use this skill for implementation or review of responsive layout. Preserve explicit product behavior, accessibility, and the existing stack.

## 1. Establish ground truth

1. Read the actual markup, styling, dynamic render path, and existing tests before proposing a fix.
2. Inventory every visible control and every hidden state affected by the same layout.
3. Identify the current stack and reuse existing layout primitives. Do not introduce a framework, component system, or test dependency only for this repair.
4. Separate observed facts from hypotheses. If a screenshot and source disagree, inspect the live DOM and report the discrepancy.

## 2. Reproduce before editing

Render at:

- 320px;
- 375px;
- the reported or first failing width;
- every changed breakpoint at b-1, b, and b+1;
- one desktop baseline at 1280px or wider;
- 200% text-only resize;
- 400% page zoom or an equivalent 320 CSS px reflow case.

Record:

- root `clientWidth` and `scrollWidth`;
- the failing container's bounding box and child boxes;
- each intended local scroller's `clientWidth`, `scrollWidth`, `clientHeight`, and `scrollHeight`;
- computed `white-space`, `word-break`, `overflow-wrap`, `min-width`, and flex shrink behavior where relevant;
- before screenshots and untested states.

Do not use a generic “overflowing elements must be an empty list” check. Carousels, transforms, clipping tracks, and deliberate table scrollers can be wider by design.

## 3. Classify content

| Content | Default policy |
|---|---|
| Bounded button, badge, status, count+unit | `white-space: nowrap`; `flex-shrink: 0` only as a flex item |
| Flexible title or prose | normal wrapping; `min-width: 0` only in a flex/grid context that must shrink |
| Korean proper name | adequate column minimum plus `word-break: keep-all`; verify stress overflow |
| Long natural-language English | `lang="en"` and normal wrapping |
| Unbroken identifier, URL, or chemical token | local `overflow-wrap` escape and access to the full value |
| Multi-column comparison table | semantic table, one named horizontal region, measured table minimum |
| Fixed-aspect graphic / composite viewer (Canvas, PDF.js, SVG, chart, map) | Fit viewport scale dynamically to container width (`clientWidth - padding`) via ResizeObserver; never blind CSS squashing; ancestors require `min-width: 0; max-width: 100%` |

Never apply `min-width:0`, `nowrap`, `break-all`, or `shrink-0` globally.

## 4. Choose the parent's escape route

Use the first existing/native option that preserves the product:

1. reuse existing wrap/stack behavior;
2. let the parent wrap;
3. switch row to column at the content failure point;
4. hide only redundant visual text in an approved compact state while preserving the accessible name;
5. use one bounded horizontal scroller for intrinsically two-dimensional content;
6. add a menu or alternate renderer only when the product requires it.

Do not solve layout failure with page-level horizontal clipping, font shrinking alone, deleted functionality, broad `!important`, or viewport scaling.

## 5. Scroll ownership

- Root horizontal overflow is a project failure unless explicitly required.
- A data table may be wider inside one labelled horizontal region.
- A normal document should not gain an accidental second vertical scroll owner.
- A deliberate, bounded, and accessible region may own internal vertical scrolling. Examples include dialogs, drawers, app shells, data grids, listboxes, and code editors; examples are not an exhaustive allowlist.
- Treat an element as an actual vertical scroller only when its computed overflow permits scrolling and `scrollHeight > clientHeight + 1`.
- Do not claim that `overflow-x:auto` plus `overflow-y:visible` preserves visible overflow; verify computed values and geometry.
- Do not add sticky positioning without checking overflow ancestors, offsets, stacking contexts, and both scroll axes.

## 6. Tables

1. Keep native table semantics unless an alternate presentation is explicitly required.
2. Reuse an existing horizontal wrapper; do not nest duplicate scrollers.
3. Derive the table minimum from column budgets and representative/stress data.
4. Keep bounded headers and atomic values intact; allow descriptive columns to wrap normally.
5. Preserve `<caption>`, `<th scope="col|row">`, keyboard action paths, visible focus, and a perceivable scroll affordance.
6. Do not hide columns or create a card renderer without an explicit priority and equivalence contract.

## 6-1. List + inspector split views

A list with a side inspector must not degrade into "inspector stacked under the list" on narrow widths — with 100 rows the detail ends up at the bottom of the page and selection appears to do nothing.

1. Below the split breakpoint, open the inspector as a full-viewport overlay or slide-over drawer with its own close control and safe-area padding; keep the list scroll position.
2. Keep one scroll owner per state: the list scrolls when the inspector is closed; the overlay scrolls when it is open.
3. Machine-generated text (service prompts, JSON payloads, logs) inside lists or transcripts is clamped to about 6–8 lines with an explicit expand/collapse control; valid JSON is pretty-printed when expanded.

## 7. Composite viewers (Canvas / PDF / Charts)

When rendering fixed-aspect bitmapped graphics coupled with absolute DOM overlays (Canvas + TextLayer, SVG annotators, chart layers, map pins):

1. **Synchronize engine scale, never blind CSS squash**: Do not rely on `canvas { max-width: 100% }` or `transform: scale()`. Desynchronization breaks text selection, search highlights, and pointer hitboxes. Derive the engine's internal scale from the observed container width:
   `effectiveScale = Math.min(baseScale, (container.clientWidth - paddingX) / unscaledWidth)`.
2. **Confinement armor across ancestor grid/flex layouts**: Every ancestor element in the layout path must enforce `min-width: 0; max-width: 100%; box-sizing: border-box;` to prevent flex/grid items from blowing out due to `min-width: auto`.
3. **Anti-oscillation & rAF debouncing**: Ignore subpixel container fluctuations ($\Delta < 2\text{px}$) and batch viewport recalculations via `requestAnimationFrame` or debounced resize handlers to stop infinite resize loop thrashing.
4. **Fluid clamping ceiling**: Retain `Math.min(baseScale, fitScale)` so the graphic scales down gracefully on narrow viewports but never stretches unnaturally large on wide viewports.

## 8. Stress cases

At minimum test:

- a long Korean proper name;
- a 32–40 character unbroken Latin token;
- mixed Korean/English labels;
- four-digit localized counts with units;
- the longest status and action labels;
- zero/empty, loading, error, and populated states when they exist;
- every drawer, modal, carousel slide, or menu touched by the same layout;
- composite viewers on narrow viewports (320px–375px) for text layer / canvas 1:1 coordinate match.
- list + inspector screens at 390px with a row selected in the largest dataset;
- the largest real dataset available (repetition, mixing and truncation often appear only there).

## 9. Browser acceptance checks

For each required viewport:

```js
const root = document.documentElement;
const rootOverflow = root.scrollWidth - root.clientWidth;
if (rootOverflow > 1) throw new Error(`root horizontal overflow: ${rootOverflow}px`);
```

List actual vertical scrollers:

```js
const actualVerticalScrollers = [...document.querySelectorAll("*")].filter((el) => {
  const style = getComputedStyle(el);
  const scrollable = ["auto", "scroll"].includes(style.overflowY);
  const visible = el.getClientRects().length > 0;
  return visible
    && scrollable
    && el.scrollHeight > el.clientHeight + 1;
});
```

Compare the list with the reviewed scroll-owner contract for the current UI state. Do not add production allow markers merely to silence failures; a deliberate owner must have a clear boundary, keyboard access, and a documented reason.

Verify composite viewer layer alignment:

```js
const viewerSurfaces = document.querySelectorAll(".pdf-page-surface, .composite-viewer-surface");
for (const surface of viewerSurfaces) {
  const canvas = surface.querySelector("canvas");
  const overlay = surface.querySelector(".cospedia-pdf-text-layer, .composite-text-layer");
  if (canvas && overlay) {
    const diff = Math.abs(canvas.getBoundingClientRect().width - overlay.getBoundingClientRect().width);
    if (diff > 1.5) throw new Error(`Overlay scale desynchronization: ${diff}px mismatch between canvas and text layer`);
  }
}
```

Also assert:

- all required controls are visible or have an approved reachable replacement;
- atomic labels compute to `white-space: nowrap` and are not clipped;
- container height covers all visible children;
- whenever an intended table scroller has `scrollWidth > clientWidth`, its focus and scroll affordance remain available;
- desktop behavior has not regressed;
- keyboard Tab, Enter/Space, Escape, and focus return work for touched interactions.

## 10. Delivery report

Do not claim completion without reporting:

- root cause;
- changed files and why each was necessary;
- before/after measurements;
- tested widths and states;
- screenshots or equivalent browser evidence;
- automated/manual checks actually run and their results;
- remaining exceptions and why they are safe;
- anything not verified.
