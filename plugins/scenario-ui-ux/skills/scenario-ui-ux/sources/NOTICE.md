# Source and adaptation boundaries

The active orchestration is the local scenario-ui-ux SKILL.md. Selected source documents are reference material, not automatically installed instructions. Current user requirements and scoped accepted judgments take precedence over source authors' stylistic defaults.

- Anthropic frontend-design: Apache-2.0, skills/frontend-design at dbd4588f9e1033efb41dad4bef2f7947c8993d44. The source document is preserved under selected/anthropic-frontend/frontend-design.md, with its LICENSE.txt. Renamed only to keep it out of skill discovery. No NOTICE file was present in that upstream skill directory.
- Taste Skill, Emil Kowalski and Impeccable: file-level provenance and adaptation notes are in design-research.json. Their MIT/Apache-2.0 licenses and Impeccable NOTICE are retained with the selected documents.
- Addy, Vercel and Remotion: see engineering-research.json for each repository's verified source paths, pin, reuse status and limitations. Missing license text is not replaced by an assumption.
- UI/UX Pro Max: pinned search code/data and MIT license remain under ../upstream/ui-ux-pro-max; ../upstream/NOTICE.md describes that snapshot.
- MengTo Skills: MIT, selected design-first prompting and reference-originality documents with LICENSE under selected/mengto-skills. ThreeUI source/asset boundaries and the inspected pin are recorded in mengto-research.json; no Community runtime has been applied to a product yet.
- The official component catalog is links plus original adaptation notes. Component implementations, brands, paid fonts and proprietary designer books are not included.

Upstream installers, scripts and hooks from the newly selected sources are not executed. The local hook implementation is independently written for the existing development harness; it does not recursively activate source skills or authorize deployment.
