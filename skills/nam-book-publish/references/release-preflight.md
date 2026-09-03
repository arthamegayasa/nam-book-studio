# Release preflight

Use this checklist after format generation. Apply only requirements relevant to the requested proof or release, and record every omitted check as `not-run` or `not-applicable` with a reason.

## Identity and inputs

- Candidate project, edition, locale, version, and output filenames are unambiguous.
- Every input artifact ID and SHA-256 matches the current registry.
- No input or dependency is marked stale or blocked.
- Proof mode is clearly labeled and records any optional earlier validation report only as context.
- Release mode has a passing validation report that covers these exact proof hashes and requested formats, plus current rights, final-proof, and R3 expert approvals where required.

## Content parity

- Front matter, chapters, appendices, glossary, references, index, and back matter are complete and ordered.
- Heading, figure, table, example, callout, equation, note, and assessment IDs resolve.
- Captions, alt text, long descriptions, source notes, and cross-references match the final assets.
- Warnings, uncertainty, numbers, units, jurisdictions, evidence dates, citations, and answer keys match the approved source.
- English and Indonesian files use the intended locale and approved termbase.

## Visual proof

- Every page, screen, or spine item was rendered through the actual conversion path.
- No clipping, overflow, missing glyph, font substitution, broken image, accidental blank page, orphan heading, or unreadable table remains.
- Raster assets meet effective-PPI targets at placement; vector assets render with correct labels and line weights.
- Color-independent meaning and grayscale behavior were checked where relevant.
- Trim, margins, binding side, bleed, page boxes, and cover geometry match the documented target rather than an assumed preset.

## Navigation and accessibility

- TOC, bookmarks, page list, landmarks, internal links, external links, note backlinks, and index links work where applicable.
- Language, heading hierarchy, reading order, table headers, link purpose, alt text, captions, and long descriptions were reviewed.
- Required format validators and assistive-technology tests ran; versions and results are retained.
- Accessibility claims state the exact standard and level, evaluator, date, report, and known limitations.

## Rights, privacy, and security

- Copyright, license, permission, attribution, and third-party notices accompany every reused component.
- Generated and edited asset provenance is included without claiming exclusive clearance.
- Restricted source material, credentials, private URLs, personal data, tracked changes, comments, temporary files, and unintended metadata are absent.
- Embedded scripts, macros, attachments, remote resources, fonts, and links are expected, licensed, and reviewed.

## Bundle and reproducibility

- The bundle includes deliverables, checksums, build manifest, tool versions, validation report, notices, and concise opening or printing instructions.
- Files open from a clean copy of the bundle without relying on the build directory.
- Output hashes are recorded after the final inspected save.
- The final-proof approval basis matches those output hashes. Any later byte or content change creates a new proof revision and requires renewed approval.
