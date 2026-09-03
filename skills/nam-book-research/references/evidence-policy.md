# Evidence policy

## Source selection

Use the source that owns the claim whenever possible: an issuing body for a
guideline or standard, an official dataset for its measurements, and the original
paper for study findings. Reviews can establish a landscape but do not erase the
need to inspect a pivotal source when exact methods or results matter.

Match evidence strength and freshness to consequence. Medical material should
prefer current authoritative guidance and systematic evidence, then relevant
primary studies. Record applicable population, jurisdiction, date, and study
design. Popular summaries may help discover a source but do not verify a claim.

## Verification ladder

Track these independently:

1. `retrieval_status`: whether the source was fetched
2. `metadata_status`: whether title, authors or issuer, identifier, and version
   match
3. `passage_status`: whether relevant text was inspected
4. `claim_support`: what that passage says about the scoped claim
5. `correction_status`: whether corrections, retraction, or concern affect use
6. `evidence_status`: the resulting claim-level judgment

Success at an earlier rung never implies success at a later one. In particular,
a resolvable DOI proves neither passage access nor claim support.

## Citation integrity

Never invent a DOI, PMID, URL, author, title, date, quotation, or page location.
Use `null`, `unknown`, or an unresolved gap when a value cannot be verified.
Quote minimally; prefer a precise paraphrase and location. Preserve enough detail
for an independent reviewer to repeat the check.

## Conflicts and uncertainty

Record contradictory sources with their scope and quality. Narrow the claim when
the evidence supports a narrower statement. Keep assumptions and interpretations
visible. If resolution requires author or expert judgment, return a blocker and
the exact decision needed.
