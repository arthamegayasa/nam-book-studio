# Illustration production

Read the sections relevant to the target placement and operation.

## Brief before prompt

An illustration brief must state:

- the `figure_id`, source block, objective IDs, and learning job;
- the single visual thesis and what a reader should understand;
- facts that may appear and details the image must leave unspecified;
- Nam's action, gaze, emotional register, and relationship to the concept;
- composition, hierarchy, quiet space, crop-safe area, and binding side;
- master aspect ratio and each required placement size;
- locale, caption, alt-text intent, and any later typeset labels;
- reference asset IDs and hashes, rights status, cultural review, and reviewers.

Resolve contradictions in the brief before generation. The latest approved visual brief and character bible outrank an older prompt or example.

## Prompt construction

Describe the image in this order:

1. deliverable and exact composition;
2. learning job and one visual thesis;
3. approved Nam anchors and action;
4. supported objects and relationships;
5. line, color, space, and mood;
6. crop, background, and label-safe zones;
7. explicit factual, cultural, and continuity constraints.

Use the `nam-v1` assets only as character calibration. Create a fresh composition for the current content. Avoid another project's mascot, signature composition, publisher trade dress, or named living artist style.

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

- Nam matches the approved silhouette, page-white body, charcoal features, crest, books, sash, and orange feet.
- Eyes are small, round, charcoal, and warm with tiny white catchlights; no blue facial marking appears.
- Nam performs the teaching action and does not function as a corner sticker.
- The illustration carries one main thesis and has a readable focal hierarchy.
- Unsupported labels, symbols, anatomical details, and cultural objects are absent.
- Text-safe zones are clean and the crop remains usable at final placement.
- Warnings remain identifiable without color and the grayscale version preserves hierarchy.
- The effective PPI meets the recorded target.
- Caption and alt text describe the delivered image rather than the rejected concept.

## Provenance record

For every generated or edited asset record: artifact and figure IDs, file hash, dimensions and color mode, date, prompt summary, tool and model when known, approved input hashes, reference images, generation count or edit history when known, human modifications, rights basis, applicable license, notice path, reviewers, and limitations.

Describe what is known. Do not infer exclusive rights, trademark availability, model-training provenance, or legal clearance from successful generation.
