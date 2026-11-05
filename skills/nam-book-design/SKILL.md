---
name: nam-book-design
description: "Define a book project's page design (trim, grid, typography, callout styles, icon set, chapter opener, figure and table styles) as a design spec with stylesheet assets, then render a sample chapter through the real build path for hash-bound approval. Use after the project brief, before chapters are mass-produced, or when the look changes; art identity belongs to nam-book-illustration-setup and full-book builds to nam-book-publish."
---

# Nam Book Design

Make the author approve the look of the book on one rendered sample chapter before any chapter is typeset, and give publish an approved spec instead of improvisation.

## Inputs and gate

Read the project manifest (profile, locales, deliverables, `visual_density`), the approved project brief, the [callout catalog](../asknam/references/callout-catalog.json), the mode preset under `assets/presets/`, and, when the project has one, the approved `illustration_setup` with its `visual_tokens`; the icon set follows that art direction. For a text-only project the typographic fallback applies and no icons are drawn.

Read [references/design-contract.md](references/design-contract.md) for the spec fields and the approval basis, and [references/render-path.md](references/render-path.md) for the build path, tool discovery, and format degradation.

## Design the system

1. Start from the mode preset and record every deviation as a decision with its reason: trim, margins, side column, baseline, body and heading typography with font licenses, color roles that survive grayscale, callout styles per placement token, icon set, chapter opener, figure and table styles, running heads.
2. Ask only about choices that materially change the reader's experience: trim size, side column versus band-only callouts, serif versus sans body, publisher preset. Carry the rest as proposals in `decisions`.
3. Write `design_spec` at `design/design-spec.json` with `profile` equal to the manifest profile and the `illustration_setup` artifact as a registry input when it exists.
4. Run `scripts/build_design_assets.py --spec <spec> --out design/assets` to generate `print.css`, `epub.css`, `callouts.lua`, `reference.docx`, the icon set, and `assets-manifest.json`. The assets are derived from the spec; edit the spec, never the generated files.
5. Return `review`. AskNam registers the spec and the assets bundle and runs the proof node.

## Prove the design

6. In node `nam-book-design-proof`, run `scripts/render_sample.py --spec <spec> --assets design/assets --out design/proofs/<artifact_id> --locale <source locale> --formats <requested deliverables>`. The bundled sample chapter exercises every callout type the mode allows, a figure, a table, a quick check with its answer key, and the chapter opener; pass `--manuscript` to render a registered enriched chapter instead when one exists.
7. Inspect the rendered files yourself: open the PDF pages, the DOCX in a word processor when available, and the EPUB in a reader. `report.json` records structural checks and tool versions; it proves rendering happened, not that the design is right.
8. Return the proof bundle as `review` with the limitations the renderer recorded (for example, no running heads in the Chromium PDF path). AskNam requests the `design` approval against the spec and assets hashes; the approval helper requires a fresh, passing proof rendered from exactly those bytes.

## Outputs and completion

`design_spec` at `design/design-spec.json`, `design_assets` at `design/assets` (tree-hashed), and `design_proof` bundles at `design/proofs/{artifact_id}` containing the rendered sample, `report.json`, and `build-manifest.json`.

Ready for review means the spec validates against the design contract, every requested deliverable format rendered from the current assets, the report status is `pass`, and every known limitation is written down. A missing tool (Pandoc, a Chromium-family browser, LibreOffice) leaves the proof `blocked` with the named prerequisite; a prose description of a layout is not a proof.

Only AskNam mutates global state or approval records. A changed spec or asset expires the design approval and marks proofs and publication builds stale; a changed illustration setup does the same through the spec's registered input. Changing the design never reopens illustration approval.
