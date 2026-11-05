---
status: accepted
date: 2026-11-05
---

# Callouts are Pandoc fenced divs with type-neutral IDs and their own registry field

Callout labels had drifted across five skill files, no Markdown syntax existed for a callout, and `docs/architecture.md` sketched `callout-ch03-warning-02`. We decided that a callout is written as a Pandoc fenced div (`::: {#callout-ch03-02 .callout type=warning objective=obj-ch03-01}`), that its ID is type-neutral (`callout-ch03-02`, parallel to `fig-ch03-04` and `item-ch03-012`), and that callout IDs are a first-class registry field (`callout_ids`) rather than prefixed entries inside `semantic_block_ids`.

## Considered options

- GitHub-style alerts (`> [!TIP]`): no ID slot, a fixed type set, GFM-only. Rejected.
- HTML `<aside>` blocks: hostile to editing and localization diffs. Rejected.
- Type inside the ID: more readable, but retyping a Warning as a Remember is a legitimate teach or edit action and would force either a new ID or a lying one. Rejected.
- Callouts as semantic blocks with a `callout-` prefix: publish and localize would filter by prefix and parity checks would be weaker. Rejected.

## Consequences

- A fenced-div-aware Markdown reader (Pandoc 3.x or equivalent) is the baseline parser for every manuscript.
- Changing a callout's type never changes its ID. IDs are assigned at creation, sequential per chapter, and never reused.
- The artifact registry schema, its mirrors, and the registration CLI gain `callout_ids`.
