# Attribution and redistribution

This distribution combines new orchestration, modified skills and existing reusable plugins. It does not claim all bundled work as newly authored.

- The base plugin collection is [COSMAX-DA/DA_Plugin_Sets](https://github.com/COSMAX-DA/DA_Plugin_Sets), revision `0b00c39d5129c653c1fae83efff2cd315311b088` plus the local development changes described in this repository. Its original MIT copyright notice is retained in [licenses/DA_Plugin_Sets-MIT.txt](licenses/DA_Plugin_Sets-MIT.txt).
- `live-browser-session`, `plain-writing` and `unbox-ui` are reused plugins. `text-wireframe-planner` and `craft-ui-motion` were revised. `da-development-method` and `scenario-ui-ux` were added in the development work.
- Selected Anthropic, Taste, Emil Kowalski, Impeccable, Addy Osmani and MengTo documents retain their individual licenses and notices inside `plugins/scenario-ui-ux/skills/scenario-ui-ux/sources/selected/`. Their exact pins and adaptation boundaries are in that directory's parent [NOTICE](plugins/scenario-ui-ux/skills/scenario-ui-ux/sources/NOTICE.md) and research JSON files.
- UI/UX Pro Max's pinned MIT search code and data retain their [NOTICE](plugins/scenario-ui-ux/skills/scenario-ui-ux/upstream/NOTICE.md) and license. Search results are candidates, never automatically adopted designs.
- gstack is installed from its pinned upstream by `scripts/setup-gstack.sh`; its runtime and repository are not bundled. Superpowers contributes the documented TDD practice, not a second mandatory workflow.
- Vercel, Remotion, ThreeUI and other sources represented by links or source pointers remain links or pointers. This distribution adds no missing-license source copy, paid assets, proprietary books or designer branding.

Public-distribution changes: repository/maintainer metadata, a filtered seven-plugin marketplace, private-policy placeholders, packaging paths, independent local service configuration and distribution documentation. Original private databases, user decisions and reasons, screenshots supplied by the user, authentication, native sessions and runtime dumps are excluded. Generalized assistant engineering cases are explicitly labeled as such.

## 0.5.0 verification labs

The labs contain independently written fixtures and pinned npm dependencies, with their actual notices in each lab. Motion, Anime.js and Motion Canvas were checked against their pinned licenses. The built animate.css@4.1.1 npm artifact includes its MIT2020 license; the separately inspected current upstream uses Hippocratic2.1. They are separate artifacts and are documented separately. GSAP3.15.0 has its own terms; its original notice is retained in the served production bundle. This is a fixed local comparison fixture, not a visual animation authoring product. No paid Motion+ assets are bundled. Next/React/Tailwind official-document summaries do not claim a jointly authored official skill.
