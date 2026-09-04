# Illustration setup

Set the visual identity before producing chapter images. Version 0.2.0 adds `$nam-book-illustration-setup` as an early specialist that AskNam can select automatically. It keeps hand-drawn treatment while fitting each project's subject, readers, references, and mascot choice.

## Choose what belongs to this project

| Choice | Starting material | Result |
| --- | --- | --- |
| Custom mascot | Audience, book theme, and desired personality | An original, project-specific identity with fixed anchors and approved calibration |
| Supplied identity | Your mascot drawing or rights-cleared character sheet | A continuity contract that preserves the selected identity while adapting agreed presentation details |
| Nam preset | The suite's original Nam assets | The approved friendly round-eye Nam identity, with project-specific scenes and teaching actions |
| No mascot | Subject matter and style references, if any | A hand-drawn scene/object system without a recurring character |

The skill asks only about choices that would materially change the result. A supplied image does not automatically become a mascot reference: it may be a line, palette, composition, or subject reference instead. When intent is ambiguous, settle that distinction before generation.

## What happens before chapter production

1. Inspect the brief and accessible reference images. Record each image's purpose, hash, provenance, and rights status; request missing files instead of describing unseen images.
2. Define the visual language: line irregularity, simplified forms, texture, palette roles, negative space, expression, and final-size readability. Use project-appropriate cultural cues only when requested or justified by the subject.
3. Record fixed identity anchors and permitted variations, or an explicit no-mascot choice. Nam's white bird body and round charcoal eyes apply only to the Nam preset.
4. Produce or inspect a small representative calibration sample using the available image tools. A mascot needs identity/pose checks; a mascot-free project needs representative objects or scenes. Review at intended placement size and in grayscale.
5. Present the setup and character contract for human approval before batch production. Keep rejected alternatives and source assets intact; new choices become new revisions.

The two registered outputs are `visuals/illustration-setup.json` and `visuals/character-bible.json`. For a mascot-free project, the latter explicitly records that no recurring mascot is allowed; it does not invent a character to fill a slot. The new skill's [contract and templates](../skills/nam-book-illustration-setup/SKILL.md) define the detailed handoff.

Calibration assets are registered separately under `visuals/calibration/<artifact_id>/`. A bundle can retain a supplied image in its original format, an editable SVG sample, or a generated sheet. The setup records these bundles as versioned inputs, so changing the sample also invalidates the approval that depended on it.

The skill does not promise exact text inside generated images. Diagrams retain editable labels, geometry, and factual relationships even when their surrounding visual language is hand-drawn. Missing rights or reference images block the affected branch. Without an image tool or a suitable supplied calibration asset, setup remains provisional rather than claiming a sample exists.

## Example requests

Custom identity:

```text
Use $asknam to set up the art for a friendly-explainer book about astronomy
for teenagers. Design an original little comet guide, not Nam. Keep irregular
ink contours, sparse texture, simple friendly eyes, and a restrained palette.
Show a calibration sheet before any chapter illustrations.
```

Supplied mascot:

```text
Use $nam-book-illustration-setup with my attached mascot drawing.
Preserve its silhouette, face, and proportions. Use the second reference only
for pencil texture. This book is for adult gardening beginners in Indonesian.
Ask before changing the mascot's identity or adding cultural accessories.
```

Mascot-free:

```text
Use $asknam to set up a hand-drawn visual system for this engineering textbook.
No mascot. Use simple ink sketches and quiet neutral colors. Keep all formulas,
labels, measurements, and diagram relationships editable and exact.
```

Existing Nam project:

```text
Use $asknam to add the new illustration setup to this existing book.
Adopt my approved Nam character bible without redesigning the face or
overwriting the old assets. Show what needs fresh approval before continuing.
```

## Upgrade an existing project

Update the entire installed suite together so the router, catalog, schemas, and specialists agree. The repository update does not itself replace a previously installed copy.

AskNam validates the existing manifest and uses the `setup-illustration` route for a focused setup. The runtime preserves legacy character-bible records and approval history while adding the new setup stage. An old `character-bible` approval is not silently converted into `illustration-setup` approval. The user reviews the adopted or revised setup and its current artifact hashes before new production.

For a legacy manifest, AskNam performs the explicit migration before planning the new stage. From a repository checkout, the commands are:

```bash
python skills/asknam/scripts/update_state.py --state /path/to/book/.nam-book/project.json migrate-illustration-setup
python skills/asknam/scripts/plan_route.py --state /path/to/book/.nam-book/project.json --intent setup-illustration
```

Replace the manifest path with the actual book path; for a sibling-skill installation, use the installed AskNam script paths. Migration is idempotent and does not rewrite the old image or bible files. It changes registry ownership and requests the new review.

After a style or mascot change, affected visual outputs and their integration/release dependents become stale. They remain on disk and in revision history. Unrelated research and chapter drafting need not be regenerated. Reuse the same stable figure IDs when the teaching job has not changed.

## Scope of verification

The repository tests check routing, gates, artifact ownership, resource portability, and legacy-state behavior. They do not certify an image's artistic quality, legal clearance, or cultural accuracy. Those require inspecting the actual project assets and the relevant human review.
