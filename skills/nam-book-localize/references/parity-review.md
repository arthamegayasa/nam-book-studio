# Semantic parity review

Review source and target editions by stable semantic block ID. Back-translation may reveal problems but is not proof of equivalence.

## Block inventory

Account for every required heading, paragraph, list item, callout, table cell, footnote, caption, alt text, glossary entry, question, option, rationale, warning, and metadata field. Classify unmatched blocks as intentionally locale-specific, missing, stale, or erroneous.

## Meaning checks

For each aligned block, compare:

- proposition, subject, action, object, condition, and exception
- certainty, recommendation strength, negation, and causal wording
- scope, population, setting, jurisdiction, and evidence date
- names, chronology, numbers, ranges, equations, units, and statistical expressions
- `claim_id`, `source_id`, citations, quotations, and cross-references
- learning objective, cognitive demand, answer key, and distractor logic
- warning prominence and reader action

## Naturalness checks

Read the target without looking at the source. Check local syntax, information flow, register, terminology, pronoun/reference clarity, rhythm, and unnecessary code-switching. Naturalness edits still require a second parity check.

## Report

Record each block as aligned, adapted, review, missing, or stale within the localization report. For an adaptation, state the reason and how the same instructional function and factual meaning were preserved. Any unresolved R2 or R3 divergence is a blocker; it must return to verified evidence, and R3 content still requires `medical-expert-signoff`.
