---
name: nam-book-illustrate
description: "Create or edit raster book illustrations from approved visual briefs and project-specific illustration setup. Use for explanatory scenes, conceptual metaphors, chapter art, or mascot-led teaching images; use the diagram skill for exact editable relationships."
---

# Nam Book Illustrate

Create readable educational images in which composition, character action, and visual metaphor clarify one approved learning job.

## Inputs and gate

Read the project manifest, active mode and locale, approved visual brief, illustration setup, character bible, source passage, linked objectives and evidence, placement dimensions, and previous images in the same series. Preserve `figure_id`, objective, claim, and source mappings.

The `illustration-setup` approval must be current for both the setup and bible before production, including mascot-free books. A legacy `character-bible` approval does not satisfy this gate. Missing or changed art direction returns to `$nam-book-illustration-setup`. If factual anatomy, sequence, labels, values, or relationships must be exact, route the asset to `$nam-book-diagram` or combine separately produced diagram and illustration layers without rasterizing the editable source.

Inspect the selected project's canonical calibration assets before generating a new batch. Only in Nam mode, use `assets/nam-v1/nam-character-sheet.png` and `assets/nam-v1/nam-icon.png` with the [Nam preset](../nam-book-visuals/references/nam-character-bible.md). Keep source assets unchanged unless the user explicitly requests a new version. Package artwork does not override a custom, supplied, or mascot-free choice.

## Illustrate

1. Reduce the brief to one visual thesis and one main action. Define the scene, subject hierarchy, quiet space, label-free areas, crop safety, and continuity requirements.
2. Build a generation or editing prompt from the approved setup, character bible, and relevant branch of [references/illustration-production.md](references/illustration-production.md). Use only content supported by the source passage and evidence mappings.
3. Generate each final image separately with the available raster image tool, following its image-editing/reference requirements. Treat generated text as provisional; reserve clean label zones and add exact labels through a controlled typesetting step. If the tool is unavailable, return the brief with a blocker instead of claiming a delivered asset.
4. Compare the result against the selected identity and hand-drawn tokens. A mascot must participate in the teaching action; in mascot-free mode, the scene carries that action. Apply Nam's protected face and body rules only when Nam is selected.
5. Inspect composition, factual meaning, cultural treatment, series consistency, crop safety, effective print resolution, transparency, grayscale legibility, and color-independent warnings. Use `scripts/inspect_png.py` for structural PNG and effective-PPI checks.
6. Revise narrowly when a check fails. A changed fact, label, pose with cultural meaning, or clinical depiction requires the relevant content reviewer again.

## Outputs

Write an `illustration_brief` and `illustration_asset` to their registry paths using the canonical artifact envelope. Record setup/bible/calibration input IDs and hashes, prompt summary, tool/model when known, generation date, reference-asset hashes, dimensions, intended placed size, effective PPI, locale, caption, alt text, objective/claim/source IDs, modifications, rights/provenance, review status, and blockers. Do not claim trademark registration, exclusive character clearance, medical validation, or release approval.

The work is complete when the image teaches its assigned point without unsupported detail, matches the approved project identity and hand-drawn direction, survives crop and grayscale checks, meets the target's effective resolution, has usable caption and alt text, and carries a complete provenance record.
