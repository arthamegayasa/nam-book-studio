# DOCX production

Use this reference when an editable Microsoft Word or Google Docs handoff is requested. Office Open XML packaging and vocabulary are defined by [ECMA-376](https://ecma-international.org/publications-and-standards/standards/ecma-376/); a ZIP that merely opens is not necessarily a sound editorial deliverable.

## Build from semantics

- Map title, subtitle, headings, body, quotations, captions, callouts, lists, notes, bibliography, tables, and assessment elements to named paragraph or character styles.
- Preserve heading hierarchy. Use real list numbering, footnotes or endnotes, captions, bookmarks, and cross-references instead of visual imitations.
- Use native equations when the conversion path can preserve them. Retain the source equation representation and record any fallback to an image.
- Generate a real table-of-contents field from heading styles. Record that Word or a compatible processor may need to update fields after opening.
- Define sections for front matter, body, landscape material, appendices, and page-number changes. Use explicit odd-page chapter starts only when the approved layout requires them.

## Layout and assets

Set the approved trim size, margins, gutter or mirror margins, header and footer distances, baseline choices, and paragraph spacing. Avoid using blank paragraphs for layout.

Insert final-resolution images at their intended physical size. Preserve aspect ratio, captions, source credits, and alternative text. Verify floating objects, tables, equations, and callouts in the actual target editor; conversion between Word and Google Docs is not assumed lossless.

Use tables for tabular relationships, not page layout. Repeat header rows, avoid split rows when meaning would suffer, and ensure the same information remains intelligible without fill color.

## Accessibility and metadata

- Set document title, author or organization as approved, language for each edition and language runs, heading order, table headers, logical reading order, meaningful link text, and image alternative text.
- Remove comments, tracked changes, hidden text, personal paths, temporary relationships, and unwanted author metadata only after editorial approval and with an audit record.
- Preserve required rights, source, and contributor metadata. Privacy cleanup is not permission to erase attribution.

## Verification

1. Run structural ZIP/XML inspection.
2. Open in the primary target application and one fallback reader when required.
3. Update fields and inspect the TOC, cross-references, page numbers, notes, and bibliography.
4. Render every page and inspect chapter openings, blank pages, widows/orphans, overset content, clipped objects, table splits, and figure quality.
5. Reopen the saved file and compare hashes and visible content with the inspected proof.

Record application names and versions. Do not report Word, Google Docs, accessibility, or round-trip compatibility unless that path was actually tested.
