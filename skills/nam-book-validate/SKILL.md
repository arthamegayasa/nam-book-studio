---
name: nam-book-validate
description: "Audit a Nam book's proof artifacts, evidence, instruction, assessments, visuals, localization, rights, accessibility, and production readiness. Use after proof generation, after material revisions, and before release; report honest pass, conditional, or fail decisions without self-approval."
---

# Nam Book Validate

Issue an independent, reproducible readiness decision. Validation records what was actually checked; it never converts missing evidence or an unrun tool into success.

## Inputs and scope

Run after route node `nam-book-publish-proof` (`operation=proof`) and before `nam-book-publish-release` (`operation=release`). Read the project manifest, artifact registry, route, approvals, staleness records, evidence ledger, architecture, current manuscript editions, teaching and assessment artifacts, proof deliverables, visuals, provenance, and requested formats. Preserve all IDs and hashes.

Declare the candidate scope and exact input hashes before checking it. Read [references/validation-matrix.md](references/validation-matrix.md) and mark every applicable check `pass`, `fail`, `not-run`, or `not-applicable` with evidence. For medical or other R2/R3 work, also read [references/high-stakes-validation.md](references/high-stakes-validation.md).

## Validate

1. Run `scripts/preflight_project.py` for structural, path, hash, dependency, approval, and evidence-state checks. Treat its output as one input, not the whole audit.
2. Check claim support separately from source retrieval and metadata. A DOI that resolves proves only metadata resolution. A fetched abstract proves only retrieval. A claim becomes verified only when an identified passage supports it and the required human or expert review is recorded.
3. Audit objective coverage, pedagogy, answer-key uniqueness, distractor rationales, cross-references, terminology, and semantic parity across locales.
4. Audit every figure and table for factual fidelity, caption and alt-text agreement, legibility, cultural respect, rights and provenance, and final-size color or grayscale behavior.
5. Inspect each requested production format structurally and by rendering. Record unavailable validators and unperformed manual checks explicitly.
6. Classify findings as blocker, major, minor, or note. Trace each finding to an artifact, stable IDs, evidence, required owner, and retest condition.
7. Identify downstream artifacts made stale by any failed or changed input. Do not repair content during the independent validation pass.

## Decision rules

- **Fail:** at least one blocker is open, an approval or hash basis is invalid, or a required high-stakes claim is unsupported.
- **Conditional:** no blocker is open, but a major finding, required manual review, or required external validator remains incomplete.
- **Pass:** every applicable release check ran and no blocker or major finding remains. Minor findings and limitations stay visible.

Human approval remains human: this skill may verify that a recorded approval matches its basis, but it cannot create `medical-expert-signoff`, `character-bible`, or `final-proof` approval.

## Output

Write one `validation_report` to its registry path using the canonical artifact envelope. Include scope, candidate hashes, check matrix, tool versions, findings, evidence and approval decisions, not-run checks, limitations, stale dependencies, overall decision, required remediations, retest plan, status, and blockers. Do not mutate project state or mark any input approved.

The work is complete when every applicable axis has an explicit outcome and evidence, all omissions are visible, the overall decision follows the stated rules, and another reviewer can reproduce the decision from the recorded hashes and tools.
