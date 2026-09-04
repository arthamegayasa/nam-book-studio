# Illustration setup contract

Use this reference for every setup artifact and its completion review. The
templates are editable payload starters; AskNam separately registers files using
the canonical [artifact envelope](../../asknam/references/schemas/book-artifact.schema.json).
Registry status and hash-bound approval remain authoritative.

## Setup payload

Start with [illustration-setup.template.json](../assets/illustration-setup.template.json).
Replace empty identity/project values and resolve each draft decision before
requesting approval. Preserve these fields across revisions:

| Field | Contract |
| --- | --- |
| `project_id`, `locale`, `setup_version` | Match the manifest; version changes when the visual contract changes. |
| `brief` | Record the reader, subject, tone, intended placements, and the visual promise. Retain the approved brief's artifact/hash when one exists; a manifest-bound brief can be identified by its approval ID. |
| `mascot_mode` | Exactly `custom`, `supplied`, `nam`, or `none`. |
| `hand_drawn` | `true` for this workflow. Palette, contour, and texture adapt per project while retaining a hand-drawn character. A non-hand-drawn request requires a revised workflow, not a bypass flag. |
| `visual_tokens` | Observable contour, shape language, palette roles/values, texture, shading, backgrounds, and typography/label treatment. State where line variation is allowed and where precision must be retained. |
| `references` | Image IDs, source/path, inspected hash, reference role, permission basis, review status, traits to retain, and traits to exclude. |
| `calibration` | `status` is `pending`, `passed`, or `failed`; `sample_artifact_ids` names registered assets. `checks` identifies actual observations/reviewer and result; `limitations` identifies untested placements or variants. |
| `production` | Intended raster/vector/hybrid outputs, trim/live area if known, label strategy, color-independent meaning, and consistency checks. Unknown printer parameters remain unknown. |
| `decisions`, `open_questions` | User choices, proposed assumptions, their rationale, and unresolved prerequisites. |
| `adoption` | When reusing a legacy bible: `character_bible_artifact_id`, `sha256`, `approval_ids`, and `reason`; otherwise `null`. Retain its recorded migration provenance. |

Each reference records `role` as `identity`, `style`, `composition`, or `context`.
The same image can have multiple separately explained roles. Record
`rights_status` as `cleared`, `restricted`, or `unresolved` with a concrete basis.
Restricted assets may be used only within their recorded permission. A claim of
ownership from the user is attributable permission information, not a legal
clearance finding.

## Character bible payload

Start with [character-bible.template.json](../assets/character-bible.template.json).
Use the same `project_id`, `locale`, and `mascot_mode` as the setup. Set
`identity_version`, link the setup artifact ID, and record:

- `identity`: name, purpose, silhouette, body/proportion rules, facial/eye rules,
  fixed anchors, flexible traits, and prohibited drift. For `none`, use `null`.
- `palette`: concrete sampled/approved values and their roles, not newly guessed
  colors per scene.
- `action_library`: purposeful poses or actions appropriate for this book; empty
  when there is no mascot.
- `cultural_context`: intended cues, source/reference IDs, limits of use, and
  review status. An empty list is valid when the project has no cultural motif.
- `canonical_asset_ids`: calibration identity assets to inspect on every new
  batch. For `none`, these can be scene calibration assets rather than characters.
- `consistency_checks`: observable visual tests, linked to sample observations.
- `change_history`: prior version, retained/changed anchors, reason, and affected
  downstream assets. Record source approval IDs when adopting existing work.

The Nam preset provides Nam's fixed anchors; it does not define every project's
bible. A supplied mascot's distinctive anchors remain intact unless the user
requests redesign. A custom mascot needs its own repeatable silhouette and
facial rules. `none` keeps the scene and style rules while explicitly disabling
recurring-character requirements.

## Calibration review

Prefer the smallest sample that tests the decisions at risk. A compact sheet can
show neutral identity plus one teaching action; add a second scale, angle, or
expression only if it tests likely drift. A scene-only project needs a scene,
and an exact-diagram project needs a representative editable diagram. Existing
approved assets may satisfy calibration without another generation call.

Record the following observations as passed, failed, or untested:

- **Identity:** silhouette, face, palette, proportions, and anchors agree with
  the bible; no mascot appears in `none` mode.
- **Hand-drawn character:** readable irregular contour and restrained texture
  survive final size; they do not become visual noise or obscure meaning.
- **Project fit:** age, subject, tone, and cultural context fit the approved brief.
- **Reusability:** the design remains recognizable at its smallest expected
  placement and can perform a typical learning action without excess detail.
- **Production:** crop safety, background/alpha, grayscale hierarchy, and intended
  dimensions work for the tested use. Separate exact labels remain editable.
- **Rights and accuracy:** used references have a permission basis; invented
  cultural or factual details are not presented as authoritative.

`calibration.status: passed` means the required checks for the selected mode and
placement have been inspected and passed, not that a human approved production.
Record the actual reviewer and asset IDs. Untested optional variants remain
limitations; a failed required check blocks readiness. A missing image or tool
leaves calibration pending and the setup blocked for production.

## Registration and approval

Register each calibration bundle as `illustration_calibration` at
`visuals/calibration/{artifact_id}`. Keep the original file format (PNG, JPEG,
editable SVG, or other supported format) and its provenance inside the bundle;
a format change solely to fit a file extension is unnecessary. Copying a
retained reference preserves its bytes and does not imply public permission.
Then register the setup and bible with those asset IDs/revisions/hashes in their registry
`inputs`. Put `sample_artifact_ids` in the payload too for inspection. Use fresh
paths or revisions for new files; preserve the original master. Avoid a cycle:
the bible may name the setup ID in its payload, but setup and bible do not need
mutual registry-input dependencies.

Return both JSON artifacts with `review` status only after required checks pass.
AskNam obtains `illustration-setup` approval bound to the setup and bible. The
agent's calibration inspection is not the user's approval. A descriptive prompt,
file path, or “approved” string inside payload JSON cannot substitute for the
registered, hash-bound approval record.

## Revision and adoption

Report what changed: identity, tokens, rights, sample, production target, or
reference interpretation. A content change that does not alter art identity can
reuse the current setup; a mascot/style change returns to this stage. AskNam
expires approvals on changed dependencies and marks affected visual briefs,
illustrations, diagrams, and composed publications stale, retaining originals.

For a legacy Nam bible, preserve its original bytes, ID, revisions, snapshots,
and approval history. AskNam's explicit `migrate-illustration-setup` operation
adopts its registry ownership. Create the new setup with adoption provenance and
inspect the retained assets. A legacy `character-bible` approval is useful
history, but does not approve the new project setup. If the adopted bible lacks
the new payload fields, record the mode and `adoption` mapping in the setup rather
than rewriting the approved file merely to reformat it. Return the accepted
existing artifact reference to AskNam; specialists do not rewrite its registry.
The new setup binds the calibration inputs; an adopted legacy bible can retain
its earlier registry inputs rather than acquiring a cosmetic new revision.
Request a new joint `illustration-setup` approval before further production.
