# Research contract

The evidence ledger must validate against [evidence-ledger.schema.json](../../asknam/references/schemas/evidence-ledger.schema.json).

## Source record

Each source carries a stable `source_id`, source type, verified bibliographic or
issuer metadata, DOI/PMID/URL when real, publication or update date, access time,
retrieval status, metadata status, and correction/retraction status.

## Claim record

Each independently supportable proposition carries:

- stable `claim_id`, `chapter_id`, and `section_id`
- exact scoped claim text
- `fact`, `assumption`, or `interpretation`
- R0-R3 risk
- candidate, verified, conflicting, or missing status
- intended citation and verifier
- one or more evidence links

Each evidence link names its `source_id` and separately records passage status,
supporting passage or paraphrase, location, support judgment, and notes. A
verified claim has at least one accessible inspected passage whose support is
`supports`; R2/R3 claims should not rely on a lone weak source when stronger
current evidence is expected.

## Research brief

Alongside the ledger, provide a human-readable brief organized around the book's
decisions rather than search chronology:

1. conclusions safe to use
2. qualified or jurisdiction-limited conclusions
3. conflicts and their practical effect
4. missing evidence and blocked content
5. correction/retraction findings
6. cutoff and recommended revalidation date

## Refresh report

Compare claim and source identities, not merely citations. Report added,
superseded, corrected, retracted, strengthened, weakened, and meaning-changing
evidence. Name every downstream ID and approval that needs invalidation.
