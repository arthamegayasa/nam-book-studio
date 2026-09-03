---
name: nam-book-write
description: "Draft or revise book chapters from an approved chapter specification, evidence ledger, mode profile, and voice profile. Use for manuscript prose, examples, and cases; route structural changes or unsupported claims back to architecture or research."
---

# Nam Book Write

Produce accurate, teachable manuscript prose without weakening the project's evidence or artifact contracts.

## Inputs and gate

Within an AskNam project, read the project manifest, artifact registry, chapter specification, selected mode profile, `source_locale`, evidence ledger, voice profile, and any approved terminology guidance. Use only approved inputs. For a standalone request, use the supplied equivalents and state any assumptions.

A chapter is ready to draft when its `chapter_id`, learning `objective_id` values, scope, audience, locale, and required evidence are defined. Return a blocking requirement when a missing decision would materially change the chapter. Never fill an evidence gap with a plausible fact or citation.

## Draft the chapter

1. Map every planned section to at least one objective and map factual propositions to existing `claim_id` and `source_id` values.
2. Draft in the project locale. Keep stable semantic block IDs when revising, and preserve all incoming IDs exactly.
3. Follow the selected mode without treating the mode outline as a mandatory heading list. Read [references/drafting-by-mode.md](references/drafting-by-mode.md) for the active mode.
4. Apply the approved voice profile. If the voice is missing or contradictory, use `$nam-book-voice` before broad stylistic work.
5. Use examples and cases to clarify the objective. Mark synthetic or composite cases as such; never introduce identifiable personal information.
6. Record unsupported, disputed, or out-of-scope claims in the draft's machine-readable metadata and the stage result, then route them to `$nam-book-research`.
7. Check objective coverage, internal consistency, citation attachment, terminology, cross-references, and reading level before handing off.

For medical or other high-stakes content, also read [references/high-stakes-drafting.md](references/high-stakes-drafting.md).

## Outputs

Write only the chapter draft to its declared `chapter_draft` slot. Embed covered objective IDs, used claim/source IDs, blockers, and requested downstream work in YAML front matter within that draft, and repeat the same indexes in the stage result. Validate the draft's registry entry against [book-artifact.schema.json](../asknam/references/schemas/book-artifact.schema.json), including schema version, artifact ID, project and chapter IDs, locale, input artifact ID/hash pairs, producer, status, and blockers. Do not create an auxiliary artifact for these indexes.

Do not update global project state. AskNam owns state transitions. Do not mark a draft approved or release-ready.

The work is complete when every in-scope objective is covered or explicitly blocked, every high-stakes factual claim resolves to approved evidence, stable IDs remain intact, and the chapter artifact plus stage result satisfy the project contract.
