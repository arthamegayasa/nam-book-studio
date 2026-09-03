# High-stakes validation

Apply this reference to R2/R3 claims and to medical, legal, safety, financial, or similarly consequential content. It adds gates; it does not turn the system into an expert, regulator, or clinician.

## Context gate

Record the intended audience, use context, applicable jurisdiction, research cutoff, and revalidation deadline. A medical project needs non-null jurisdiction, evidence cutoff, and `revalidate_before_export`. Stop release validation when the revalidation date has passed or when the content is being reused in a materially different population, jurisdiction, or care setting.

Separate general education from individualized advice. Prominently preserve emergency escalation language, contraindications, referral thresholds, and limitations where the approved source material requires them. Do not invent a universal disclaimer as a substitute for accurate content and expert review.

## Evidence gate

For every R2/R3 claim:

1. Locate the claim by stable chapter and section IDs.
2. Prefer current, jurisdiction-relevant official guidance, standards, systematic reviews, and primary studies appropriate to the claim. Record why a source is fit for this population and use.
3. Keep retrieval, metadata verification, correction checking, passage finding, and claim support as separate fields. A successful URL, DOI, PMID, title match, or abstract fetch does not verify a claim.
4. Record the exact supporting or contradicting passage and its location. `Partially-supports` is not sufficient for a claim marked `verified` unless the claim is narrowed and re-reviewed.
5. Recheck errata, withdrawals, retractions, expressions of concern, and superseding guidance close to release. A used source with unknown or unperformed correction status remains an explicit release limitation.
6. Preserve conflicting evidence and uncertainty. Do not average incompatible guidance or silently select the convenient source.

Check every number, unit, range, denominator, dose, timing, age band, laterality, sign, threshold, table cell, algorithm branch, caption, and figure label against its evidence and context. Verify that citations and explanatory rationales support the exact nearby sentence rather than merely the topic.

## Expert gate

A qualified human reviews the complete rendered candidate in context, not an isolated claim list. The recorded `medical-expert-signoff` or equivalent approval must identify the reviewer, decision time, scope, limitations, and exact artifact hashes. The validation skill may check that record; it cannot issue or infer the approval.

Any later change to a signed-off claim, citation, calculation, algorithm, figure, warning, translation, or layout that may affect meaning invalidates the affected basis and downstream final-proof approval. Route it back to the appropriate expert before release.

## Medical-specific checks

- Terminology, risk statements, and recommended actions match the named jurisdiction and evidence cutoff.
- Triage and red-flag language does not delay urgent care or create false reassurance.
- Benefits, harms, uncertainty, and alternatives are presented proportionately.
- Medication and procedure content preserves units, routes, timing, contraindications, and monitoring requirements from the approved evidence; individualized prescribing remains out of scope unless explicitly governed and reviewed.
- Diagnostic or treatment diagrams do not imply a deterministic pathway where professional judgment or local protocol is required.
- Cases are documented as synthetic or used with appropriate consent and de-identification. Remove hidden identifiers from document metadata and media.
- Accessibility and translation reviews include warnings, units, abbreviations, tables, algorithms, and image alternatives, not just running prose.

## Release outcome

Fail when a required R2/R3 claim is missing, conflicting without an approved resolution, unsupported by an identified passage, based on a retracted or superseded source, outside the approved context, or missing the required expert approval. Keep unrun correction, rendering, or jurisdictional review visible; never relabel it as a successful automated check.
