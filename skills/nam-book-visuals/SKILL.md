---
name: nam-book-visuals
description: "Plan a book's objective-linked visual system, visual inventory, and original Nam character bible. Use before creating illustrations or diagrams, or when visual density, format routing, accessibility, cultural treatment, or art direction must be decided."
---

# Nam Book Visuals

Turn the approved book architecture into a coherent visual teaching system. Every proposed visual must perform a learning job; decoration alone is not a reason to add an asset.

## Inputs and gate

Read the project manifest, book architecture, active profile and locales, voice profile, teaching plan, evidence ledger, production targets, and existing visual assets. Preserve all `project_id`, `chapter_id`, `objective_id`, `claim_id`, `source_id`, and `figure_id` values.

The architecture must define chapter objectives and planned visuals. Record unresolved content, rights, cultural, or production questions as blockers instead of resolving them through invented visual detail.

## Plan the system

1. Audit each chapter for a specific reader difficulty: spatial structure, sequence, comparison, mechanism, scale, memory, emotional orientation, or conceptual transfer.
2. Select the smallest useful form. Use an editable diagram for exact relationships and labels, a raster illustration for an expressive scene or metaphor, a table for compact comparison, and prose when a visual would duplicate the text. Read [references/visual-brief-contract.md](references/visual-brief-contract.md) for routing and specification fields.
3. Map every retained proposal to its objective, learning job, source location, insertion point, caption purpose, and accessibility treatment. Visual density is a ceiling, not a quota.
4. Define the shared visual language: line behavior, palette, typography, label density, page placement, color-independent meaning, and print/digital variants.
5. Create or revise the Nam character bible from [references/nam-character-bible.md](references/nam-character-bible.md). Use the supplied `nam-v1` assets as calibration sources and record their hashes; keep those source files unchanged.
6. Audit ownership, licenses, permissions, cultural references, model/tool provenance, and required notices for every source asset. A missing right or uncertain sacred or cultural use blocks that asset branch.
7. Route approved raster briefs to `$nam-book-illustrate` and exact relational briefs to `$nam-book-diagram`.

## Outputs

Write `visual_brief` and `character_bible` artifacts to their registry paths using the canonical artifact envelope. Include input artifact IDs and hashes, locale, visual tokens, figure inventory, objective/claim/source mappings, target formats, accessibility requirements, provenance, decisions, rejected proposals, status, and blockers. Do not mutate global project state or grant the `character-bible` approval.

The work is complete when every retained visual has a distinct learning job, a production route, traceable content, rights status, caption and alt-text intent, and a feasible trim-aware output specification; the character bible is internally consistent and ready for human approval.
