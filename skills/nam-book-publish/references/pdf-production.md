# PDF production

Use this reference for fixed-page digital or print proofs. PDF syntax is standardized in the ISO 32000 family; the active [PDF 2.0 specification is ISO 32000-2](https://www.iso.org/standard/75839.html). Select a printer, archive, or accessibility profile only from an explicit delivery requirement.

## Choose the target

- **Digital reading PDF:** prioritize selectable text, bookmarks, links, tagged structure when required, sensible reading order, alt text, small file size, and screen rendering.
- **Print interior PDF:** prioritize exact trim, page boxes, imposed or single-page form requested by the printer, font embedding, image resolution, overprint and color requirements, bleed where elements reach the trim, and binding-safe margins.
- **Cover PDF:** use the printer's spread, spine, flap, bleed, barcode, and color specification. Do not calculate spine width without the printer's paper and page-count formula.

Keep cover and interior separate when the printer requests separate files. PDF/X, PDF/A, PDF/UA, output-intent, CMYK, and tagged-PDF claims are distinct; one does not imply another.

## Build

- Preserve live, searchable text and embedded or appropriately substituted fonts.
- Retain headings, lists, tables, figures, captions, notes, links, language, and reading order in the tagged structure when accessibility is required.
- Place images at sufficient effective PPI and use the printer's color profile. Do not infer CMYK correctness from appearance on screen.
- Generate bookmarks and a linked TOC for digital editions when requested.
- Resolve comments, tracked changes, hidden layers, annotations, form fields, and metadata according to the approved release policy.

## Verification

1. Run structural inspection, then a dedicated PDF parser or repair checker when available.
2. Render every page to images and inspect trim, blank pages, chapter starts, clipping, transparency, line weight, table breaks, figure detail, and glyph substitution.
3. Extract text and compare section order, warnings, numbers, units, references, and assessment keys with the canonical source.
4. Inspect fonts, image effective resolution, page boxes, output intent, color separations, and ink limits with production-grade tools when the printer requires them.
5. Validate any named PDF/X, PDF/A, or PDF/UA claim with a validator that supports the exact profile, then record its version and report.
6. Test bookmarks, links, reading order, zoom, and assistive technology for the declared digital accessibility target.

A `%PDF-` header, successful render, or metadata conformance flag proves only that check. Report every untested profile requirement and obtain a physical proof for color- or binding-critical work.
