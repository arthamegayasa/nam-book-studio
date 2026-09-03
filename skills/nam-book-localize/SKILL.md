---
name: nam-book-localize
description: "Create or maintain semantically aligned English and Indonesian editions of a book. Use after source-language content is locked to translate prose, callouts, assessments, captions, and metadata while preserving IDs, evidence, numbers, and safety meaning."
---

# Nam Book Localize

Produce a natural target-language edition whose instructional and factual meaning can be traced block by block to the source edition.

## Inputs and gate

Read the project manifest's `source_locale` and requested `target_locales`, content-lock status, source manuscript, semantic block map, voice profile, evidence ledger, assessment bank, visual label/caption inventory, and the terminology ledger in any current localization report. Preserve every stable ID across locales.

Localization begins after the source artifact is content-locked. A source change makes dependent localized blocks stale. If both English and Indonesian are being authored independently rather than translated, designate one canonical evidence-bearing edition and still maintain parity records.

## Localize

1. Inventory semantic blocks and classify each as translate, locale-adapt, retain, or recreate-with-review.
2. Resolve terminology, form of address, English variant, acronym handling, and numeric/date conventions before bulk translation. Store those decisions in the localization report's terminology ledger. Read [references/en-id-localization.md](references/en-id-localization.md) for either English-to-Indonesian or Indonesian-to-English work.
3. Translate by block, retaining IDs, citations, quotations, equations, evidence status, warnings, uncertainty, and cross-references.
4. Localize callout labels, captions, alt text, glossary entries, metadata, and figure label manifests. Do not destructively edit source artwork.
5. Revalidate each localized assessment item: the key must remain uniquely correct and distractors must remain plausible without new linguistic clues.
6. Run the semantic parity review in [references/parity-review.md](references/parity-review.md). Route changed high-stakes meaning to research and expert review.

## Outputs

Write only the localized manuscript and localization report to their declared artifact-registry slots. Keep approved terms, prohibited translations, context notes, and unresolved terminology in a versioned terminology ledger inside the localization report; do not create a separate terminology artifact. Validate both registry entries against [book-artifact.schema.json](../asknam/references/schemas/book-artifact.schema.json). Record source and target locales, input artifact ID/hash pairs, aligned block IDs, adaptation decisions, changed high-stakes claims, assessment re-review results, stale dependencies, status, and blockers. Do not mutate global project state.

The work is complete when all required blocks align, numbers/units/citations and safety meaning match, localized prose is natural in context, assessments remain valid, and every deviation from literal equivalence is documented and justified.
