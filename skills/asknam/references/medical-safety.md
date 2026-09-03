# Medical safety gates

Medical publishing is an evidence and human-review workflow, not a guarantee of
clinical correctness.

## Risk levels

- `R0`: descriptive material with no health consequence.
- `R1`: low-consequence health education or historical context.
- `R2`: content that may influence clinical understanding, examination answers,
  or non-urgent decisions. Every material claim needs verified evidence.
- `R3`: diagnosis, treatment, dosing, contraindication, emergency, procedural,
  or patient-specific guidance. Evidence verification and named clinician review
  are mandatory before publication.

When uncertain, choose the higher level until a qualified reviewer resolves it.

## Evidence gate

For R2/R3 claims, metadata resolution alone is insufficient. The ledger must
separately record retrieval success, metadata verification, passage discovery,
claim support, contradiction, correction/retraction status, jurisdiction, and
freshness. A claim becomes `verified` only when an inspected passage supports
the exact scoped claim. Search snippets remain candidates.

Clinical algorithms, tables, callouts, assessment answers, and every rationale
carry their own claim and evidence IDs. Nearby chapter citations do not cover
them implicitly. Conflicting or inaccessible evidence remains visible as a
blocker.

## Publication gate

Before medical publication:

1. refresh the evidence ledger through the declared cutoff
2. check corrections, retractions, superseding guidance, and jurisdiction
3. rerun validation after editing, localization, and answer-key changes
4. for `R3`, obtain `medical-expert-signoff` from a named qualified reviewer
   against the exact validation/evidence artifact hashes
5. obtain final-proof approval against the rendered edition

Past-due revalidation, unresolved R2/R3 claims, a changed approval basis, or a
missing required clinician decision blocks publication. Report limitations
explicitly; never promise that hallucination or clinical error is impossible.

An R3 project must enable the medical workflow and provide jurisdiction,
evidence-cutoff, and revalidation dates. Evidence and validation artifacts stay
in `review` while the expert evaluates them. AskNam records the reviewer's name,
professional role, credentials, and hash-bound evidence/validation basis. No R3
artifact may become `approved` or `locked`, and no release may run, before that
signoff. Medical R0-R2 work still uses its declared evidence policy but does not
automatically require the R3 expert gate.
