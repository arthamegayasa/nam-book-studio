# High-stakes editing

An elegant edit can make an incorrect claim more dangerous. Treat meaning preservation as a release gate.

## Claim-sensitive diff

Compare the pre-edit and post-edit text for each high-risk `claim_id`. Flag changes to:

- population, setting, indication, timing, threshold, magnitude, frequency, or duration
- dose, route, unit, formulation, sequence, or monitoring
- negation, modality, certainty, recommendation strength, exception, or contraindication
- jurisdiction, guideline version, evidence date, or applicability
- causal versus associative wording

Preserve the citation with the exact proposition it supports. Moving a citation to the end of a broader paragraph must not imply support for additional claims.

## Required routing

- Editorial simplification that preserves verified meaning may proceed and remain reviewable.
- Any possible meaning change marks the affected claim and dependent artifacts stale and routes them to research or subject-matter review.
- R2 and R3 claims must return to `evidence_status: verified`; R3 content also requires a current `medical-expert-signoff` approval before release.
- Conflicting sources remain visible until the project's evidence owner resolves or characterizes the conflict.
- Unverified dosages, emergency instructions, contraindications, or individualized recommendations are blockers, not copyedits.

Record the old wording, new wording, claim ID, reason, evidence status, and required reviewer in the edit report. Do not mark your own substantive medical edit independently verified.
