# Diagram specification

Write and approve this specification before drawing. It is the source of truth for the SVG.

## Required identity and purpose

- `figure_id`, revision, locale, chapter and insertion block;
- linked objective, claim, source, and evidence IDs;
- diagnosed reader difficulty and one `learning_job`;
- diagram structure and why it is preferable to prose, a table, or an illustration;
- expected reader path and the conclusion the figure may support;
- details that must remain absent because they are unknown or out of scope.

## Content model

Define each element before laying it out:

```text
node_id | label_id | meaning | shape_role | evidence_ids | accessibility_order
edge_id | from | to | relation | direction | label_id | evidence_ids
label_id | source_text | locale_text | unit | abbreviation_expansion
```

Every causal edge must be supported as a causal relation. Use a different line style and explicit wording for association, sequence, possibility, uncertainty, inhibition, or contradiction. A nearby citation does not turn correlation into causation.

For values, record the number, unit, range or uncertainty, population, date, jurisdiction, and evidence ID when applicable. For anatomy, record orientation, laterality, viewing plane, simplifications, and omitted structures. For clinical decision paths, record eligibility, exclusions, red flags, stopping points, and where professional judgment remains necessary.

## Structure selection

- **Process:** ordered transformation with a defined start and outcome.
- **Hierarchy:** containment or level relationships; avoid implying time.
- **Comparison:** parallel structures sharing the same criteria.
- **Timeline:** dated or ordered events on one scale.
- **Cycle:** a genuinely repeating process with no misleading terminal arrow.
- **Spatial map:** position or anatomy where orientation is meaningful.
- **Mechanism:** supported interactions with distinct causal and noncausal relations.
- **Decision path:** explicit conditions, branches, outcomes, and exit states.

Use one dominant structure. When the content needs two independent reading rules, split it into coordinated figures.

## Visual and production contract

Specify:

- viewBox, aspect ratio, target placed width and height, trim, and live area;
- minimum final type size and line weight;
- palette roles and non-color equivalents;
- node groups, edge routing, reading order, and whitespace zones;
- caption, concise alt text, and long description when required;
- master SVG path and requested PNG/PDF derivatives;
- font strategy, embedding or conversion policy, and locale expansion allowance;
- grayscale, low-vision, and small-screen test sizes.

Do not hard-code line breaks until the target locale and final placement are known. Keep labels in identifiable `<text>` elements and use stable IDs so localization can replace text without reconstructing the diagram.

## Review record

Record content reviewer, visual reviewer, accessibility reviewer when required, validators run, render sizes inspected, findings, fixes, input hashes, final hash, status, and blockers. A validator result proves only its declared scope.
