---
name: nam-book-teach
description: "Turn an accurate chapter draft into instructionally effective material with scaffolding, analogies, callouts, examples, misconception repair, and retrieval prompts. Use after drafting; use the assessment skill for scored item banks."
---

# Nam Book Teach

Strengthen learning without changing the chapter's factual meaning or turning it into a collage of boxes.

## Inputs and gate

Read the approved chapter specification, current draft, selected mode profile, active locale, objective map, evidence ledger, any approved terminology guidance, and any visual plan. Preserve every `chapter_id`, `objective_id`, `claim_id`, `source_id`, and semantic block ID.

The draft must already be factually usable. Route missing evidence to `$nam-book-research` and structural scope changes to `$nam-book-architect`; pedagogical polish cannot repair either problem.

## Instructional pass

1. Diagnose learner friction: missing prerequisites, abstraction jumps, high intrinsic load, likely misconceptions, weak transfer, or long stretches without retrieval.
2. Create a teaching plan. Give each proposed enhancement a stable ID, source block, objective ID, purpose, mode fit, and insertion point.
3. Select the smallest pattern that addresses each problem. Read [references/pedagogy-patterns.md](references/pedagogy-patterns.md) and use only the active mode's branch.
4. Integrate the selected enhancements into an enriched draft while preserving claim meaning, citations, and semantic block IDs. New facts require evidence; new factual claims are not an instructional device.
5. Coordinate visual opportunities through `figure_id` requests for `$nam-book-visuals`. Coordinate scored questions through `$nam-book-assess`.
6. Re-read the chapter as a learner. Remove redundant callouts, decorative mnemonics, repeated summaries, and analogies whose limitations outweigh their value.

## Invariants

- Link each enhancement to a learning objective and a diagnosed learning need.
- State where an analogy stops working.
- Prefer explicit labels over icon-only meaning.
- Keep warnings and safety qualifications prominent after simplification.
- Preserve uncertainty, exceptions, numbers, units, and jurisdictional scope.
- Use humor only where it cannot trivialize patients, cultures, disabilities, or safety.

## Outputs

Write a teaching plan and enriched draft to artifact-registry paths. Validate registry entries against [book-artifact.schema.json](../asknam/references/schemas/book-artifact.schema.json) and record input artifact ID/hash pairs, locale, enhancement IDs, affected block/objective IDs, requested visuals or assessments, removed proposals, status, and blockers. Do not mutate global state or mark the chapter approved.

The work is complete when every inserted element has an instructional purpose, all source IDs and claim meanings survive, the callout load remains readable, and outputs satisfy the project contract.
