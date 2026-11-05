# Design contract

The design spec is the project-level description of how the book looks. Publish consumes it through the generated assets; the author approves it on a rendered sample chapter. Start from [design-spec.template.json](../assets/design-spec.template.json) and the mode preset in [presets/](../assets/presets/), and validate the result against [design-spec.schema.json](../../asknam/references/schemas/design-spec.schema.json). The registry envelope stays separate from the payload.

## Spec payload

| Field | Contract |
| --- | --- |
| `project_id`, `profile`, `design_version` | Match the manifest. `profile` must equal the manifest profile; the approval helper rejects a mismatch. Bump `design_version` when the look changes. |
| `preset` | The mode preset the spec started from (`friendly-explainer`, `textbook`, `exam-prep`). Deviations are listed in `decisions`. |
| `callout_catalog_version` | The catalog version the callout styles were written for. |
| `illustration_setup` | `{ "artifact_id", "sha256" }` of the approved setup whose `visual_tokens` govern the icons, or `null` for a text-only project. Register the setup as an input of the spec too, so a changed setup stales the design. |
| `trim` | `name`, `width_mm`, `height_mm`, `bleed_mm`. Unknown printer parameters stay `null`; never invent bleed. |
| `page` | `margins_mm` (`top`, `bottom`, `inner`, `outer`), `side_column_mm` (`0` disables side-column callouts; they degrade to `band`), `column_gap_mm`, `baseline_pt`. |
| `typography` | `body`, `headings`, `captions`, `labels`: `family`, `fallbacks`, `size_pt`, `leading_pt`, `weight`, and `license` for every named font. Fonts are referenced, not bundled, unless their license allows redistribution and the file is added to provenance. |
| `color` | Roles, not decoration: `ink`, `paper`, `accent`, `muted`, `rule`, and `callout_accent` keyed by `type_id`. Every role must keep meaning in grayscale. |
| `callouts` | One style object per placement token (`inline`, `side-column`, `band`, `full-page`, `opener`): `frame`, `background`, `icon_size_mm`, `label_style`, `max_width_mm`. Placement semantics come from the callout contract; this spec only styles them. |
| `icons` | `format` (`svg`), `source` (`bundled` or `project`), `directory`, and `style_note` describing how the hand-drawn tokens were applied. One icon per `type_id` the mode allows. |
| `chapter_opener` | `style` (`full-page`, `half-page`, `run-in`), ordered `elements` (`number`, `title`, `big-idea`, `objectives`, `figure`). |
| `figures`, `tables` | Caption position, frame, default placement, header rule, zebra, minimum caption size. |
| `running` | `head` (`chapter-title`, `book-title`, `none`) and `page_numbers` (`outer`, `center`, `none`). |
| `render` | Per format: `engine` and engine options. See [render-path.md](render-path.md) for the supported engines and their limitations. |
| `degradation` | Per reflowable or engine-limited format: how each placement token degrades (`side-column` → `inline`, `band` → `inline`, `full-page` → `page-break`). |
| `publisher_preset` | `null`, or the printer's named preset with its source document; keeps publisher specifics configurable instead of hard-coded. |
| `sample_chapter` | `source` (`bundled` or `chapter`), `artifact_id` when a registered chapter is used, `locale`. |
| `decisions`, `open_questions` | Choices with reasons, and prerequisites still unresolved. |

## Presets

A preset is a complete spec payload for one mode. `friendly-explainer` uses a side column for short callouts and bands for long ones with a high icon presence; `textbook` uses a quieter grid with band callouts, numbered figures, and evidence-note styling; `exam-prep` compresses margins, keeps side-column pearls and traps, and styles quick checks and answer keys prominently. Presets are starting points; the approved spec is the contract.

## Generated assets

`scripts/build_design_assets.py` turns the spec into `design/assets`:

- `print.css` for the HTML-to-PDF path (page size, margins, grid, callout styles per placement, icons, figures, tables).
- `epub.css` for reflowable output with the degradation rules applied.
- `callouts.lua`, a Pandoc filter that turns `.callout` divs into labeled, icon-bearing elements per format, with labels for both locales embedded from the catalog.
- `reference.docx`, derived from Pandoc's default reference document with the spec's fonts, sizes, colors, and `Callout Band`, `Callout Side`, `Callout Label`, `Callout Title` paragraph styles.
- `icons/<type_id>.svg`, the icon set in use.
- `assets-manifest.json` with the spec hash, catalog version, tool versions, and the list of generated files.

The bundle is tree-hashed on registration; regenerating it after a spec change produces a new revision.

## Approval basis

The `design` approval binds `design_spec` and `design_assets`. The helper refuses the decision unless the design stage is complete, both artifacts are fresh and still match their bytes, the spec's `profile` matches the manifest, and a fresh `design_proof` exists whose registered inputs name exactly those spec and asset revisions, whose node completed, and whose `report.json` has `status: pass` and covers every requested deliverable other than Markdown. The proof is the evidence shown to the author; the spec and assets are what publish consumes.

Changing the spec or the assets expires the approval and marks proofs and publication builds stale. Changing the illustration setup does the same through the spec's registered input. Changing the design leaves the illustration approval intact.
