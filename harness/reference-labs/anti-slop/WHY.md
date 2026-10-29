# Why these changes

## Initial scope and source-based hypothesis

This is an authored diagnostic fixture, not a naturally occurring production incident. BEFORE intentionally presents the same three records inside repeated card boundaries, adds non-informational icon tiles, uses color/dots instead of explicit state labels, and uses a clickable div without keyboard activation. These are declared fixture conditions, not observed user feedback.

Hypothesis: removing redundant visual containers while preserving task grouping, adding explicit states and using a real button will make the same information and keyboard path unambiguous. The meaningful selectable workspace boundary in COUNTERCASE must remain. No timing or preference claim is planned.

AFTER changes only those dimensions. The three records' titles, owners, states and due dates remain. COUNTERCASE retains fieldset/legend, radio scope choices and supplementary owner markers, because they communicate identity or selection scope. Source heuristics do not authorize a universal border, icon or font ban.

Actual screenshots, task observations, failures, repairs and image/source fingerprints are appended after execution. Initial empty source snapshot and coherent source snapshot must both precede first Docker build. A repair or rebuild after service start first requires a normal source/image snapshot.

## Harness preparation failure

A relative working-directory mistake prevented the first test-file write. The existing fixture source was unchanged by that failed command. The first static build succeeded and was retained. A normal source/image snapshot was taken before adding the missing test harness and correcting documentation. No browser result existed at that point.

## Actual sequential task failure and repair

The first browser run passed nine variant/width combinations, but its scope-selection check ended immediately after changing the radio. It did not test a subsequent search. Direct inspection also showed the final row separator sitting almost against the enclosing workspace border.

A stronger same-task sequence selected Personal with Space and then searched for the keyboard task. At320px the actual radio returned to Team. The retained failing run is `2026-10-29T10-54-31-343Z-cde63610-ab2d-4a74-b251-316ef7c7ebc0`; both before-search and after-search frames were inspected. This is an observed state-reset defect in the new fixture, not an author claim or user preference.

Cause: render rebuilt the radio inputs and always checked the first workspace, instead of storing the chosen scope separately. The repair stores selectedScope outside render and updates it on radio change. A search now rebuilds presentation using that value. The final row divider inside each workspace was removed while keeping the outer semantic fieldset boundary. The radio focus shape follows its circular control. No group or record was deleted. A normal source/image snapshot preceded this repair and rebuild.

The new browser sequence also fingerprints the test script and captures keyboard-return frames. The earlier pass remains a bounded result with a known missing sequential check; it is not retroactively promoted into prevention success.

## Frame inspection caught a focus-shape gap after the functional pass

The second full browser run passed the stronger selected-scope sequence at all three widths. Inspection of `320-countercase-scope-selected.png` still showed a rectangular native outline around the circular radio. Merely assigning border-radius had not changed that browser's visible native outline. The detail dialog also used an unrounded outline on its borderless close button. These are visual observations, not inferred from passing computed-style checks.

After another normal source/image snapshot, the radio keeps native semantics and keyboard behavior but renders its focus with a circular box-shadow while removing that input's native outline. The close control uses the shared button radius. The browser test now checks the radio focus treatment and retains focused screenshots for direct inspection. No focus indication was removed without replacement.

The third run's inspected focused-radio frame still showed a square native focus treatment even though computed outline was none and the circular shadow was present. That attempted fix was insufficient and its passing geometry check did not establish visual correctness. A further normal source/image snapshot preceded setting appearance:none on the existing radio input and drawing its circle/checked dot in CSS. The native input, label, radio group, checked state and Space/arrow semantics remain. This is a bounded Chromium visual repair, requiring another captured-frame check.

## Final bounded result

Final run `2026-10-29T10-59-15-342Z-3c50867a-8f95-4308-b420-9ff20cb35cef` passed all9 variant/width combinations at320/390/1440px and retained30 screenshots. The nine cases intentionally confirm BEFORE's missing Enter activation as a diagnostic contrast; AFTER and COUNTERCASE pass native keyboard detail/escape/return, explicit states, search/filter, and scoped choice preservation. It is not a claim that BEFORE is usable.

Directly inspected final frames: circular focused radio at320, rounded close focus in the390px dialog, and retained Personal scope after search at1440. Earlier initial nine frames and failed before/after-search frames were also inspected. Not every generated final PNG received separate visual review. The final runtime serves the same source bytes for all three pages, app.js and style.css; the container healthcheck uses /after.html. /health is not an endpoint on this static server. No human timing, user satisfaction, preference acceptance or prior-product application was measured.
