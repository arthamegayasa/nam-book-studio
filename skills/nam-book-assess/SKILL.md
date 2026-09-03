---
name: nam-book-assess
description: "Design and validate original formative or exam-preparation assessments from approved learning objectives and evidence. Use for blueprints, MCQs, cases, answer keys, and rationales; do not use to reproduce proprietary exam items."
---

# Nam Book Assess

Create assessments that measure the intended learning, not recognition tricks or unsupported trivia.

## Inputs and gate

Read the project manifest, chapter specification, objective map, selected mode profile, active locale, any approved terminology guidance, approved evidence, and any exam blueprint metadata. Preserve `chapter_id`, `objective_id`, `claim_id`, and `source_id` values.

Build the assessment blueprint before writing items. If exam-preparation coverage depends on a current official blueprint that has not been verified, stop that branch and request research rather than guessing its weighting.

## Workflow

1. Define purpose, audience, delivery context, feedback timing, item formats, and target count.
2. Build a blueprint crossing objective, content area, cognitive process, difficulty, and item format. Explain any intentionally uncovered objective.
3. Draft original items from the blueprint. Base distractors on documented or credible misconceptions, wrong reasoning steps, near-neighbor concepts, or incomplete rules.
4. Supply the correct answer, a concise rationale, and a separate explanation for every distractor. Attach the evidence IDs needed to verify each factual answer.
5. Run the item-level and set-level review in [references/item-quality.md](references/item-quality.md).
6. For medical or other high-stakes items, also apply [references/high-stakes-assessment.md](references/high-stakes-assessment.md).
7. Revise, retire, or block ambiguous items. Never force a key when more than one answer remains defensible.

## Outputs

Write the assessment blueprint and localized item-bank artifacts to their registered slots. Validate registry entries against [book-artifact.schema.json](../asknam/references/schemas/book-artifact.schema.json). Store blueprint reconciliation and review findings in the blueprint or item records defined by the project contract. Every item must have a stable `item_id`, objective mapping, cognitive level, difficulty, source/evidence links, key, rationales, status, and review findings. Record input artifact ID/hash pairs and do not update global project state.

The work is complete when blueprint totals reconcile with the item bank, required objectives and cognitive levels are represented, every distractor has a pedagogical rationale, the answer set passes quality checks, all items are original, and high-stakes items are supported or explicitly blocked.
