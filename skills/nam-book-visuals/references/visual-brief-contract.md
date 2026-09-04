# Visual brief contract

Use this reference when selecting visual formats or writing the project-level visual brief. The approved illustration setup and character bible own art direction and identity; this brief applies them to content and placement.

## Start with the learning job

Retain a visual only when it reduces a named reader difficulty. Useful learning jobs include:

- reveal a spatial or part-to-whole relationship;
- make a sequence, decision, feedback loop, or causal model inspectable;
- compare alternatives across the same attributes;
- show scale, distribution, trend, or uncertainty;
- provide a memorable but bounded metaphor;
- demonstrate an action or worked transformation;
- orient the reader emotionally before difficult material;
- support retrieval without disclosing an assessment answer.

State the difficulty and expected reader action. “Break up the page” is not a learning job.

## Route the asset

| Content need | Primary form | Reason |
| --- | --- | --- |
| Exact nodes, arrows, labels, values, anatomy, chronology, or localization | Editable SVG diagram | Relationships and text remain inspectable and revisable. |
| Expressive scene, conceptual metaphor, chapter atmosphere, or the selected mascot performing a teaching action | Raster illustration | Composition and gesture carry meaning that exact geometry does not. |
| Repeated comparison across shared fields | Semantic table | Readers can scan values without decoding a picture. |
| Quantitative values or trends | Data graphic generated from retained data | The data, transformation, and axes remain reproducible. |
| Documentary subject | Rights-cleared photograph or source figure | A generated substitute could falsely imply evidence. |
| Simple statement already clear in prose | No visual | Duplication adds load without adding understanding. |

A hybrid asset keeps its exact diagram layer editable and its illustration layer replaceable. Record both component artifact IDs and their composition method. Hand-drawn tokens govern appearance, not factual precision or format: they do not justify baking exact labels into a generated bitmap. In mascot-free mode, plan scenes or relationships without a recurring guide.

## Figure inventory fields

Each retained entry should include:

- `figure_id`, `chapter_id`, insertion block, locale, and revision;
- approved setup and bible artifact IDs/revisions/hashes, plus the relevant visual-token references;
- linked `objective_ids`, `claim_ids`, and `source_ids`;
- diagnosed reader difficulty, `learning_job`, and expected reader action;
- chosen kind, routing rationale, and rejected alternatives;
- factual payload and an explicit list of details that must not be inferred;
- caption purpose, short alt-text intent, and long-description need;
- labels, units, reading order, and localization strategy;
- composition, hierarchy, palette role, and color-independent cues;
- trim size, live area, orientation, placed width and height, bleed, crop safety, and binding side;
- master format plus print, digital, grayscale, and thumbnail derivatives;
- owner, origin, license or permission, notice path, and cultural review status;
- producer, reviewer, input hashes, status, blockers, and downstream dependencies.

## Density and rhythm

Treat the profile's `visual_density` as an upper bound.

- **Low:** include only visuals required to understand a relationship that prose cannot carry efficiently.
- **Medium:** add worked or comparative visuals at genuine conceptual turns.
- **High:** provide frequent anchors, while giving each spread a clear focal hierarchy and keeping redundant callouts out.

Evaluate rhythm by chapter purpose and page geometry, not by a fixed “one image every N pages” rule. A cluster of related visuals may be correct; evenly spaced decoration is not.

## Captions and accessibility

The caption explains why the figure matters in context and carries source or adaptation credit when needed. Alt text conveys the figure's purpose and essential information without repeating the caption word for word. Complex diagrams also need a long description or equivalent nearby prose.

Color may reinforce meaning but cannot be its only carrier. Pair it with labels, line styles, shapes, patterns, or position. Verify reading order at final placement size.

## Production feasibility

Specify dimensions from the target trim and live area before generation. Raster briefs state the minimum effective PPI at placed size. Diagram briefs state a viewBox and minimum final text size. If publisher or printer requirements are unknown, mark them unresolved; do not invent bleed, color-space, PDF standard, or binding values.
