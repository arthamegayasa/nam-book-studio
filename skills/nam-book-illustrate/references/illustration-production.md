# Illustration production

Read the sections relevant to the target placement and operation.

## Brief before prompt

An illustration brief must state:

- the `figure_id`, source block, objective IDs, and learning job;
- the single visual thesis and what a reader should understand;
- facts that may appear and details the image must leave unspecified;
- the selected mascot's action, gaze, emotional register, and relationship to the concept, or the scene's main action in mascot-free mode;
- composition, hierarchy, quiet space, crop-safe area, and binding side;
- master aspect ratio and each required placement size;
- locale, caption, alt-text intent, and any later typeset labels;
- setup, bible, and calibration asset IDs/revisions/hashes, reference rights status, cultural review, and reviewers.

Resolve contradictions in the brief before generation. The current approved setup, character bible, and visual brief outrank an older prompt or example. Book-facing labels, captions, and alt text follow the project locale; production instructions and provenance fields stay in English.

## Prompt construction

Describe the image in this order:

1. deliverable and exact composition;
2. learning job and one visual thesis;
3. approved project identity anchors and action, or mascot-free scene rules;
4. supported objects and relationships;
5. line, color, space, and mood;
6. crop, background, and label-safe zones;
7. explicit factual, cultural, and continuity constraints.

Use the selected project's approved calibration assets. In Nam mode, the `nam-v1` assets supply character calibration; other modes must not inherit them. Create a fresh composition for the current content. Translate style references into observable line, texture, palette, and shape attributes without importing another project's mascot or signature composition. Keep supplied asset usage within its recorded permission.

Maintain the approved hand-drawn character: controlled contour variation, clear simplified forms, and restrained texture. Match the project tokens rather than adding roughness indiscriminately. Exact data, geometry, warning cues, and labels remain precise and editable.

Generate without embedded explanatory prose when exact text matters. Store the approved label strings separately, then typeset them after generation or move the work to an editable SVG diagram.

## Page geometry and resolution

Derive the image box from the final trim, margins, columns, and bleed. Preserve a master large enough for the widest requested placement.

Effective PPI is pixel width divided by placed width in inches. Use the smaller result when both placed dimensions are constrained. Follow the printer's requirement; absent one, target at least 300 effective PPI for color or grayscale raster art. Pure one-bit line art may need a higher target, but do not claim a requirement without the printer specification.

Examples:

- 5-inch placement at 300 PPI requires at least 1500 pixels across.
- 120 mm placement is approximately 4.724 inches and requires at least 1418 pixels across at 300 PPI.

Do not upscale a small image and report the new pixel count as recovered detail. Record any resampling. Use `scripts/inspect_png.py` to verify structure and calculate effective PPI.

Keep important content inside the live area. Extend only expendable background into bleed. Test left- and right-hand placements when the binding edge matters.

## Master and derivatives

Retain one master and generate derivatives without overwriting it:

- print color at the printer-approved color space and placed size;
- digital color with suitable compression and metadata;
- grayscale when the edition or print route needs it;
- transparent-background cutout only when composition requires it;
- thumbnail for navigation or catalog use.

PNG supports RGB, grayscale, and alpha but not a complete print-conformance claim. Conversion to CMYK or a printer profile belongs in the controlled publication workflow.

## Factual and cultural review

Compare the image with the source passage and evidence, not just the prompt. Check anatomy, laterality, sequence, quantities, instruments, PPE, setting, and risk cues where they matter. A friendly style may simplify form but not reverse or invent a clinical fact.

Use the cultural rules from the approved character bible. Original geometric accents are preferable to unverified named motifs. A sacred or ceremonial reference requires authoritative context and appropriate human review.

## Visual QA

- The selected mascot matches its approved silhouette, face, proportions, palette, and fixed anchors; mascot-free scenes contain no accidental recurring guide.
- In Nam mode, check the [Nam preset anchors](../../nam-book-visuals/references/nam-character-bible.md), including the round charcoal eyes and absence of blue facial markings. These are Nam-specific, not universal mascot anatomy.
- The character or scene performs the learning action rather than functioning as a corner sticker.
- Linework, simplification, and texture match the approved hand-drawn tokens at final placement size.
- The illustration carries one main thesis and has a readable focal hierarchy.
- Unsupported labels, symbols, anatomical details, and cultural objects are absent.
- Text-safe zones are clean and the crop remains usable at final placement.
- Warnings remain identifiable without color and the grayscale version preserves hierarchy.
- The effective PPI meets the recorded target.
- Caption and alt text describe the delivered image rather than the rejected concept.

## Provenance record

For every generated or edited asset record: artifact and figure IDs, file hash, dimensions and color mode, date, prompt summary, tool and model when known, approved input hashes, reference images, generation count or edit history when known, human modifications, rights basis, applicable license, notice path, reviewers, and limitations.

Describe what is known. Do not infer exclusive rights, trademark availability, model-training provenance, or legal clearance from successful generation.
