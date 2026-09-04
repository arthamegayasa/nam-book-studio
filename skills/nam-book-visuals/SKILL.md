---
name: nam-book-visuals
description: "Plan a book's objective-linked figure inventory using its established illustration setup. Use after architecture for visual density, format routing, accessibility, and placement; use nam-book-illustration-setup for initial art direction or mascot identity."
---

# Nam Book Visuals

Turn the approved book architecture into a coherent visual teaching system. Every proposed visual must perform a learning job; decoration alone is not a reason to add an asset.

## Inputs and gate

Read the project manifest, book architecture, active profile and locales, voice profile, evidence ledger, production targets, illustration setup, character bible, and existing visual assets. Read the teaching plan and completed chapter passages when available; planning can start from the approved architecture without them, and content details must be checked again before production. Preserve all `project_id`, `chapter_id`, `objective_id`, `claim_id`, `source_id`, and `figure_id` values.

The architecture must define chapter objectives and planned visuals. The current `illustration-setup` approval supplies the project's art direction and mascot choice, including an explicit mascot-free choice. If it is missing or the brief requires a different identity, route to `$nam-book-illustration-setup` rather than silently creating a new bible. Record unresolved content, rights, cultural, or production questions as blockers instead of resolving them through invented visual detail.

## Plan the system

1. Audit each chapter for a specific reader difficulty: spatial structure, sequence, comparison, mechanism, scale, memory, emotional orientation, or conceptual transfer.
2. Select the smallest useful form. Use an editable diagram for exact relationships and labels, a raster illustration for an expressive scene or metaphor, a table for compact comparison, and prose when a visual would duplicate the text. Read [references/visual-brief-contract.md](references/visual-brief-contract.md) for routing and specification fields.
3. Map every retained proposal to its objective, learning job, source location, insertion point, caption purpose, and accessibility treatment. Visual density is a ceiling, not a quota.
4. Apply the approved visual tokens to figure scale, label density, page placement, color-independent meaning, and print/digital variants. Keep exact relationships and labels editable even when their surrounding linework has a hand-drawn character.
5. Use the selected project identity only when it performs the learning job. In mascot-free mode, plan meaningful scenes, objects, or diagrams without inserting Nam. Report a need for new poses, proportions, or cultural treatment to the setup stage if it changes the approved identity; do not silently broaden its fixed anchors.
6. Audit ownership, licenses, permissions, cultural references, model/tool provenance, and required notices for every source asset. A missing right or uncertain sacred or cultural use blocks that asset branch.
7. Route approved raster briefs to `$nam-book-illustrate` and exact relational briefs to `$nam-book-diagram`.

## Outputs

Write only `visual_brief` to its registry path using the canonical artifact envelope. Include the setup and bible as input artifact IDs/revisions/hashes, locale, figure inventory, objective/claim/source mappings, target formats, accessibility requirements, provenance, decisions, rejected proposals, status, and blockers. Reference the approved visual tokens instead of maintaining a second art-direction source. Do not mutate global project state or grant approvals.

The work is complete when every retained visual has a distinct learning job, a production route, traceable content, rights status, caption and alt-text intent, and a feasible trim-aware output specification consistent with the approved project identity.
