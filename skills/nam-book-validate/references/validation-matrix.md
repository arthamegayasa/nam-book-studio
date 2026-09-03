# Validation matrix

Use this matrix to define a validation run before assigning outcomes. Add project-specific checks; do not delete applicable rows merely because a tool or reviewer is unavailable.

## Check record

Record these fields for every check:

- `check_id`, axis, and requirement
- applicability rule and why it applies
- outcome: `pass`, `fail`, `not-run`, or `not-applicable`
- method, tool and version, exact candidate artifact IDs and hashes
- observed evidence, including report path, page, figure, claim, or stable node ID
- finding severity and responsible owner when the outcome is not `pass`
- limitation, retest condition, reviewer, and timestamp

`Not-run` is never a pass. `Not-applicable` needs a reason tied to the project configuration. A check on a sample must say how the sample was selected and cannot establish whole-book conformance.

## Core matrix

| Axis | Minimum checks | Applies when |
| --- | --- | --- |
| Manifest and registry | Manifest shape and version; registered paths remain inside the artifact root; IDs and paths are unique; files exist; stored hashes match; input hashes resolve; blockers agree with status | Every run |
| Dependency freshness | Changed inputs are propagated; unresolved staleness is visible; approvals still match their recorded basis | Every run |
| Route and approvals | Required nodes are present; route status is internally consistent; human approvals were not synthesized; approver, decision time, and basis hashes are recorded | Every run |
| Evidence | Retrieval, metadata, passage, claim support, and correction state are distinct; citations resolve to the intended sources; verified claims have supporting passages; conflicts and gaps remain visible | Any factual content |
| Architecture | Reader outcome maps to chapter and section objectives; prerequisites and cross-references resolve; scope and sequence match the approved architecture | Every book |
| Manuscript | Objectives are taught, examples are accurate, terminology is consistent, headings and notes are semantic, citations and figure calls resolve | Every book |
| Teaching and assessment | Practice is aligned to objectives; answer keys are determinate; distractors and rationales are defensible; scoring and feedback do not reveal unsupported certainty | When teaching or assessments are enabled |
| Visuals and tables | Each item has a learning job; content matches the manuscript; caption and alt text agree; final-size labels are legible; non-color cues work; raster/vector routing is appropriate | When figures or tables exist |
| Character and culture | Approved character bible and source-asset hashes match; Nam has no prohibited drift; cultural references have sources, purpose, and review where needed | When Nam or cultural material appears |
| Localization | Source and target editions are complete; stable IDs align; numbers, units, examples, references, images, alt text, and warnings retain meaning | For every target locale |
| Rights and provenance | Text, images, fonts, quotations, and data have origin and license or permission records; required notices ship; privacy and releases are handled; no unsupported clearance claim is made | Every public or distributed release |
| Accessibility | Heading order, reading order, language metadata, links, table semantics, alt text, contrast, zoom/reflow, and document titles are tested in each format | Every deliverable; exact checks vary by format |
| Production parity | Canonical content, front matter, end matter, figures, tables, equations, notes, identifiers, and metadata match across requested formats | Multiple deliverables |
| DOCX | Package inspection passes; styles and structural objects are semantic; application open/save and rendered-page review are recorded | DOCX requested |
| EPUB | Package and navigation inspection passes; EPUBCheck result is recorded; reflow, reading order, links, images, and at least two reading systems are reviewed | EPUB requested |
| PDF | File opens; fonts, links, images, page boxes, metadata, output intent, and any claimed PDF/X, PDF/A, or PDF/UA conformance are checked with the appropriate validator; rendered pages and physical proof are reviewed as applicable | PDF requested |
| Release bundle | Build manifest lists exact inputs, tools, settings, outputs, hashes, notices, reports, and limitations; the approved final proof hashes equal the release candidate | Release validation |

## Severity and decision

- **Blocker:** unsafe or materially false content, unsupported required R2/R3 claim, invalid approval basis, corrupted or missing deliverable, unresolved rights prohibition, or a defect that prevents intended use.
- **Major:** substantial learning, accessibility, localization, evidence, or production failure that requires correction before release.
- **Minor:** bounded defect that does not alter safety, meaning, core learning, access to essential content, or package validity.
- **Note:** observation or improvement opportunity with no release requirement.

The overall decision follows the rules in `../SKILL.md`, not a numeric score. If a required external validator or human review did not run, keep it `not-run` and use `conditional` or `fail` according to its release criticality.

## Retest

Retest the changed artifact, the original failing check, and every downstream artifact whose recorded input hash changed. Preserve the earlier report; issue a new report revision that links findings to their disposition and records the new candidate hashes.
