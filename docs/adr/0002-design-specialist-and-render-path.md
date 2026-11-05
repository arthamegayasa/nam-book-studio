---
status: accepted
date: 2026-11-05
---

# Page design is its own specialist, approved on a rendered sample, built on Pandoc plus a browser

Publish had no builder, template, or design artifact, and the first rendered output of a project was the full-book proof. We added `nam-book-design` as a sixteenth skill that writes a project-level `design_spec`, generates `design_assets`, and renders a bundled sample chapter through the real build path; the hash-bound `design` approval binds the spec and assets and refuses a decision without a fresh, passing proof. The build path is Pandoc (DOCX via a patched reference document and a generated Lua filter, EPUB via CSS, standalone HTML) with PDF printed by a Chromium-family browser, or by LibreOffice from the DOCX when the spec asks for it.

## Considered options

- Extend `nam-book-illustration-setup` with typography and grid: a font change would have reopened illustration approval, and image identity would have mixed with page design. Rejected.
- Design presets inside the mode profiles only: nothing per project, no approval, no staleness, and the author never approves the look. Rejected.
- Gate publish on design statically for every manifest: would have blocked `publish` and `revise` on books created before the stage existed. Instead the gate applies once the `design` approval record exists, which `start`, `resume`, and `design` routes add.
- A real enriched chapter as the mandatory sample: forces drafting before the look can be approved, which is the late surprise the stage exists to prevent. The bundled sample is the default; a registered chapter can be substituted.
- Typst, WeasyPrint, or Prince for PDF: better paged media (running heads, page numbers), but a new runtime dependency with no presence on the author's machines or the CI image. Chromium's missing running heads are recorded as a limitation; a paged-media engine can be added behind `render.pdf.engine` later.

## Consequences

- Pandoc 3.x is a documented external dependency of the suite; a browser or LibreOffice is needed only for PDF. CI installs Pandoc and uses the image's Chrome.
- Microsoft Edge in headless mode was observed to exit 0 without writing a PDF; the builder tries Chrome and Chromium first and records every browser it skipped.
- A re-rendered proof is a new revision of the same proof artifact; stale proofs under a different ID would block the proof node from completing.
- Two latent state-tool defects surfaced by the design tests were fixed: a node re-registering two outputs in sequence can complete, and a node invalidated again is dropped from the `resolved_nodes` of older open staleness records.
