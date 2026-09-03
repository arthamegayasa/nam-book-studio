---
name: nam-book-architect
description: Design or revise a book's reader promise, scope, learning objectives, chapter dependency graph, and planned evidence, visuals, and assessments. Use after a project brief exists and before drafting, or when structural changes invalidate downstream work.
---

# Nam Book Architect

Convert an approved project brief and evidence base into a book architecture that
downstream skills can execute without rediscovering scope.

## Inputs

Read the AskNam manifest, selected profile, artifact registry, approved brief,
and current research artifacts. Use the manifest's locale and paths. Preserve
existing `chapter_id`, `objective_id`, `claim_id`, `figure_id`, and `item_id`
values during revision unless the represented object is deliberately retired.

Read [mode-patterns.md](references/mode-patterns.md) for the selected profile.
For medical or R2/R3 material, also apply AskNam's medical-safety reference and
require evidence IDs before declaring the architecture ready.

## Build the architecture

1. State one testable reader promise and the prerequisites it assumes.
2. Draw a hard scope boundary: included outcomes, exclusions, depth, and
   jurisdiction where relevant.
3. Create a dependency-ordered chapter graph. Each chapter owns one necessary
   transformation in the reader's understanding.
4. Assign observable learning objectives and stable IDs.
5. Plan material claims with risk levels and required evidence IDs. Keep facts,
   assumptions, and interpretations distinguishable.
6. Plan each visual by its learning job, not decoration. Assign stable figure
   IDs and choose illustration, diagram, table, or no visual.
7. Plan assessment coverage against objective IDs; exam-prep requires blueprint
   coverage and item targets.
8. Check cumulative load, duplication, missing prerequisites, and chapter-length
   budget. Revise the graph until every chapter earns its place.

Detailed required fields and revision behavior live in
[architecture-contract.md](references/architecture-contract.md). Do not invent a
parallel format.

## Output

Write `book_architecture` to its artifact-registry path and validate it against
[book-architecture.schema.json](../asknam/references/schemas/book-architecture.schema.json). Return an artifact report to AskNam;
do not edit `.nam-book/project.json`.

Set output status to `blocked` when the reader promise is unresolved, required
evidence is missing or conflicting, an R2/R3 claim lacks evidence IDs, or a
chapter dependency cycles. Otherwise return `review`; AskNam obtains architecture
approval before drafting.

On revision, also write `architecture_change_report`. List retained, added,
retired, and meaning-changed IDs plus the downstream skills and approvals that
must become stale. Silence is not evidence of no impact.
