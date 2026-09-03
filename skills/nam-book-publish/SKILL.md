---
name: nam-book-publish
description: "Build and inspect publication proofs or release bundles in DOCX, EPUB, and PDF from approved book artifacts. Use for layout, conversion, packaging, format-specific accessibility, print preparation, or final deliverables; external distribution requires a separate explicit request."
---

# Nam Book Publish

Render reproducible book deliverables without weakening evidence, accessibility, rights, or approval state.

## Choose the operation

- **Proof:** run route node `nam-book-publish-proof` with `operation=proof`. Build reviewable files from current approved content inputs before independent validation. This node has no prior validation or approval gate; proofs remain `review` artifacts and may be regenerated without publishing them externally.
- **Release:** run route node `nam-book-publish-release` with `operation=release`. It depends on `nam-book-validate` and promotes the exact proof approved by the user. Release requires a current passing validation report for the candidate, a `final-proof` approval whose basis hashes match the proof files, and `medical-expert-signoff` when the route requires it for R3.

Creating a file is not authorization to upload, submit, sell, or distribute it. Perform an external publication action only when the user explicitly requests that destination and action.

## Inputs and gate

Read the project manifest, artifact registry, approved source or localized manuscript, visual and assessment assets, metadata, rights/provenance records, requested formats, and publisher or printer specification. A validation report is optional context for a proof and required for a release. Reject stale inputs and preserve all stable IDs and cross-references.

A proof build requires no known content, evidence, safety, or rights blocker in the approved content inputs; it does not require a prior validation report. A release requires every mandatory validation axis to pass for the exact proof hashes, all required rights notices, current high-stakes approvals, and the hash-bound final-proof approval.

## Produce

1. Create a build manifest containing input artifact IDs and hashes, locale, tool names and versions, deterministic options where available, output targets, and known nondeterministic fields.
2. Prepare one canonical semantic source and map its headings, captions, callouts, references, equations, alt text, links, and page-break intent into each requested format.
3. Read only the requested format guidance: [DOCX](references/docx-production.md), [EPUB](references/epub-production.md), or [PDF](references/pdf-production.md). Use the environment's supported document or PDF tooling and record the actual path taken.
4. Build into a new staging directory. Preserve prior proofs and release files; a rebuild receives a new revision and hashes.
5. Run `scripts/inspect_deliverable.py` for structural checks, then perform the render-based and format-specific checks in [references/release-preflight.md](references/release-preflight.md). Structural inspection alone never proves visual correctness, PDF conformance, accessibility, or medical accuracy.
6. Compare the rendered outputs with the canonical source: page and section order, figures, captions, links, notes, references, assessment keys, warnings, numbers, units, and locale.
7. Package licenses, third-party notices, provenance, build manifest, validation report, checksums, and usage notes with each release bundle.

## Outputs

Write a versioned `publication_bundle` and `publish_report` to registry paths using the canonical artifact envelope. Report proof or release mode, input and output hashes, tools, checks performed, results, limitations, notices, approvals checked, status, and blockers. AskNam owns state changes.

The work is complete when every requested format opens, renders, and matches the approved source; navigation and accessibility work at the requested level; print specifications are verified rather than inferred; the bundle is attributable and reproducible; and release files match the approval hashes exactly.
