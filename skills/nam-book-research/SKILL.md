---
name: nam-book-research
description: Build or refresh a claim-level evidence ledger for a book. Use for source discovery, citation verification, contradiction analysis, correction or retraction checks, and evidence freshness, especially for academic, exam, or medical content.
---

# Nam Book Research

Produce evidence that a writer can trace from each material claim to an inspected
source passage. Retrieval success and identifier resolution are intermediate
states, never proof that a claim is supported.

## Scope the research

Read the AskNam manifest, approved project brief, profile, architecture when it
exists, risk level, locale, jurisdiction, evidence cutoff, and artifact registry.
Inventory the claims and decisions that actually need research. Separate facts,
assumptions, and interpretations; do not manufacture factual claims merely to
fill a chapter.

Read [evidence-policy.md](references/evidence-policy.md) before searching. For
medical content or R2/R3 claims, also read AskNam's medical-safety reference.

## Build the ledger

1. Assign or preserve stable `claim_id` and `source_id` values.
2. Search authoritative primary sources and source-owning indexes. Prefer current
   guidelines, standards, systematic reviews, official data, and primary studies
   according to the claim.
3. Open the source. Verify identity, date, version, jurisdiction, and correction
   or retraction status.
4. Locate the passage that bears on the exact claim. Record its location and a
   short compliant excerpt or precise paraphrase.
5. Judge support: supports, partially supports, contradicts, not applicable, or
   unknown. Record conflicts rather than averaging them away.
6. Set claim status to `verified` only when an inspected passage supports its
   scoped wording. A search result, abstract-only guess, DOI resolution, or
   metadata match remains `candidate` or `missing`.
7. Capture the intended citation, limitations, unresolved gaps, research cutoff,
   and revalidation need.

For exam-prep, research every answer and rationale, including why distractors are
wrong. For clinical algorithms, tables, warnings, and callouts, create explicit
claim records rather than relying on a citation elsewhere in the chapter.

The exact field contract is in
[research-contract.md](references/research-contract.md).

## Output

Write `research_brief` and `evidence_ledger` to their artifact-registry paths.
Validate the ledger against [evidence-ledger.schema.json](../asknam/references/schemas/evidence-ledger.schema.json). Return an
artifact report to AskNam with input IDs/hashes, claim/source IDs, blockers, and
provenance; do not edit `.nam-book/project.json`.

Use `blocked` status when a material R2/R3 claim is missing, conflicting,
inaccessible, retracted without a replacement, outside the declared jurisdiction,
or past the freshness cutoff. Otherwise use `review`. Never label the book or
ledger hallucination-free.

On refresh, write `research_change_report` and identify claim meanings,
citations, assessments, figures, algorithms, chapters, and approvals invalidated
by new or changed evidence.
