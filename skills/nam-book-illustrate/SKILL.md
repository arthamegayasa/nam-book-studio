---
name: nam-book-illustrate
description: "Create or edit original raster illustrations for Nam books from approved visual briefs and the Nam character bible. Use for explanatory scenes, conceptual metaphors, chapter art, or mascot-led teaching images; use the diagram skill for exact editable relationships."
---

# Nam Book Illustrate

Create readable educational images in which composition, character action, and visual metaphor clarify one approved learning job.

## Inputs and gate

Read the project manifest, active mode and locale, approved visual brief, approved character bible, source passage, linked objectives and evidence, placement dimensions, and previous images in the same series. Preserve `figure_id`, objective, claim, and source mappings.

The `character-bible` approval must be current when Nam appears. If factual anatomy, sequence, labels, values, or relationships must be exact, route the asset to `$nam-book-diagram` or combine separately produced diagram and illustration layers without rasterizing the editable source.

The canonical calibration assets are `assets/nam-v1/nam-character-sheet.png` and `assets/nam-v1/nam-icon.png`. Inspect them before generating a new Nam image. Keep them unchanged unless the user explicitly requests a new version.

## Illustrate

1. Reduce the brief to one visual thesis and one main action. Define the scene, subject hierarchy, quiet space, label-free areas, crop safety, and continuity requirements.
2. Build a generation or editing prompt from the approved character bible and the relevant branch of [references/illustration-production.md](references/illustration-production.md). Use only content supported by the source passage and evidence mappings.
3. Generate each final image separately with the available raster image tool. Treat generated text as provisional; reserve clean label zones and add exact labels through a controlled typesetting step.
4. Compare Nam against the approved identity: Bali-starling page spirit, warm round charcoal eyes with tiny white catchlights, and no blue eye patches or facial markings. Nam must perform the teaching action rather than stand beside it.
5. Inspect composition, factual meaning, cultural treatment, series consistency, crop safety, effective print resolution, transparency, grayscale legibility, and color-independent warnings. Use `scripts/inspect_png.py` for structural PNG and effective-PPI checks.
6. Revise narrowly when a check fails. A changed fact, label, pose with cultural meaning, or clinical depiction requires the relevant content reviewer again.

## Outputs

Write an `illustration_brief` and `illustration_asset` to their registry paths using the canonical artifact envelope. Record prompt summary, tool/model when known, generation date, reference-asset hashes, dimensions, intended placed size, effective PPI, locale, caption, alt text, objective/claim/source IDs, modifications, rights/provenance, review status, and blockers. Do not claim trademark registration, exclusive character clearance, medical validation, or release approval.

The work is complete when the image teaches its assigned point without unsupported detail, matches the approved Nam identity, survives crop and grayscale checks, meets the target's effective resolution, has usable caption and alt text, and carries a complete provenance record.
