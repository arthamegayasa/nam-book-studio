---
name: nam-book-diagram
description: "Design and verify editable SVG diagrams for book mechanisms, processes, comparisons, anatomy, timelines, and decision paths. Use when relationships, labels, units, reading order, or localization must remain exact; use the illustration skill for expressive raster scenes."
---

# Nam Book Diagram

Produce source-traceable diagrams whose structure remains editable, localizable, accessible, and legible in print.

## Inputs and gate

Read the approved diagram request, project and locale profiles, objective map, source passage, evidence ledger, visual brief, caption plan, and final placed dimensions. Preserve all `figure_id`, `objective_id`, `claim_id`, and `source_id` values.

Exact numbers, units, anatomy, clinical pathways, thresholds, and causal arrows require approved evidence. A missing or conflicting value blocks the affected element; visual neatness never resolves factual uncertainty.

## Build the diagram

1. Write a diagram specification before drawing. Use [references/diagram-specification.md](references/diagram-specification.md) for the node, edge, label, evidence, reading-order, and localization contract.
2. Choose one dominant structure: process, hierarchy, comparison, timeline, cycle, spatial map, mechanism, or decision path. Split dense content rather than shrinking type below the target format's readable size.
3. Draw connectors before nodes, group related elements semantically, use stable element IDs, and encode meaning with labels or shapes as well as color. Typeset exact labels in SVG; do not ask an image model to spell them.
4. Follow [references/svg-production.md](references/svg-production.md). Start from `assets/diagram-template.svg` when useful, while replacing all example content and accessibility text.
5. Validate the SVG with `scripts/validate_svg.py`, then render it at final size and visually inspect clipping, overlaps, arrow direction, line weight, grayscale distinction, caption agreement, and reading order.
6. Recheck every factual element against its claim/source mapping. Localized diagrams keep the same `figure_id` and element IDs while storing locale as a distinct artifact revision.

## Outputs

Write `diagram_spec` and editable `diagram_asset` artifacts to the declared registry paths using the canonical artifact envelope. Record source and input hashes, objective/claim/source mappings, locale, viewBox, intended placed size, font and color decisions, caption, alt text or long description, validation results, provenance, status, and blockers. Do not mutate global state or approve the diagram on behalf of a content expert.

The work is complete when every node, edge, label, number, and unit traces to the specification; the SVG parses safely; the final-size render is readable in color and grayscale; accessibility text matches the diagram; and unresolved evidence is visibly blocked rather than presented as fact.
