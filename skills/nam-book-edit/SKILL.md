---
name: nam-book-edit
description: "Developmentally edit, line edit, copyedit, or integrate an evidence-grounded book manuscript. Use after drafting or teaching enhancement to improve structure, consistency, clarity, and voice while preserving IDs, citations, and safety claims."
---

# Nam Book Edit

Resolve the highest-impact editorial problems first and leave an auditable account of every substantive change.

## Inputs and gate

Read the project manifest, requested edit scope, chapter specifications, selected mode profile, active locale, voice profile, current manuscript, evidence ledger, any approved terminology guidance, teaching plan, assessment links, and visual references that exist. Preserve all stable artifact, block, objective, claim, source, figure, and item IDs.

Do not start line editing while unresolved developmental changes would discard the same prose. If the user requested a narrow pass, stay within it and report rather than silently fix out-of-scope findings.

## Edit

1. Establish the pass and acceptance criteria. Read [references/editing-passes.md](references/editing-passes.md) for the requested pass.
2. Diagnose before rewriting. Record structural moves, cuts, merges, factual queries, terminology conflicts, continuity problems, and missing transitions.
3. Apply changes in descending order of impact: development, content/consistency, integration, line, then copy.
4. Preserve citations with their supported claims and preserve uncertainty, exceptions, warnings, numbers, and units.
5. Integrate approved callouts, figure/table references, and assessment links without duplicating their content.
6. Apply the approved voice profile. Route voice calibration or drift analysis to `$nam-book-voice`.
7. Run a post-edit claim diff. For high-stakes content, apply [references/high-stakes-editing.md](references/high-stakes-editing.md).

## Outputs

Write the edited manuscript and edit report to artifact-registry paths. Validate registry entries against [book-artifact.schema.json](../asknam/references/schemas/book-artifact.schema.json). The report must identify the pass, locale, input artifact ID/hash pairs, changed semantic blocks, moved or retired IDs, substantive changes, evidence queries, downstream artifacts made stale, unresolved author queries, status, and blockers. Do not mutate global state or self-approve the manuscript.

The work is complete when the requested pass has covered every in-scope block, supported claims remain attached to their evidence, cross-references remain resolvable, high-stakes meaning changes are blocked for review, and both outputs satisfy the project contract.
