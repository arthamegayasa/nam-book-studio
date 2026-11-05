# Render path

One semantic converter, three outputs. The sample-chapter proof and the full-book publish build use the same path, implemented in the publish skill's [build_deliverables.py](../../nam-book-publish/scripts/build_deliverables.py), so what the author approves is what the book is built with.

## Engines

| Format | Engine | Assets used | Known limitations |
| --- | --- | --- | --- |
| DOCX | Pandoc (`--reference-doc`, `callouts.lua`) | `reference.docx`, `callouts.lua`, icons | Side-column callouts degrade to band paragraphs; the word processor must update TOC fields after opening. |
| EPUB 3 | Pandoc (`--css`, `callouts.lua`) | `epub.css`, `callouts.lua`, icons | Reflowable: `side-column` and `band` become inline blocks, `full-page` becomes a page break. EPUBCheck still has to run. |
| PDF | Pandoc to standalone HTML, then a Chromium-family browser (`--headless --print-to-pdf`) | `print.css`, `callouts.lua`, icons | Chromium renders `@page` size and margins but no CSS margin boxes: running heads and page numbers are absent. Record this in the report. |
| PDF (alternative) | LibreOffice headless from the DOCX | `reference.docx` | Running heads and page numbers render; side-column callouts degrade as in DOCX. Choose with `render.pdf.engine: libreoffice`. |

Pandoc is the one required external tool; a Chromium-family browser (Microsoft Edge, Google Chrome, Chromium) or LibreOffice is required only for PDF. The build helper discovers them on `PATH` and in the usual install locations, records every tool and version in `build-manifest.json`, and reports a missing tool as a blocker rather than substituting a placeholder file.

## Degradation

Placement tokens are hints from the callout contract. The spec's `degradation` map says how each engine lowers them; the Lua filter applies the map per output format so the manuscript stays unchanged. A placement the engine cannot honor is never silently dropped: the callout still renders, inline, with its label and icon.

## Sample chapter

`assets/sample-chapter/` holds an original, non-medical chapter in `en-US` and `id-ID` that uses every catalog type, a figure placeholder, a table, a quick check with its answer key, and a chapter opener. `render_sample.py` keeps only the types the active mode allows, renders the requested formats, runs the publish skill's `inspect_deliverable.py` on each file in its default proof mode (hollow files fail; the release-only `--strict` promotions do not apply to a design proof), and writes `report.json`:

```json
{
  "status": "pass",
  "formats": ["pdf", "docx", "epub"],
  "checks": [{ "format": "pdf", "inspector": "pass", "warnings": [] }],
  "limitations": ["chromium: no running heads or page numbers"],
  "tools": { "pandoc": "3.9.0.2", "chromium": "Microsoft Edge 142.0" }
}
```

`status` is `pass` only when every requested format rendered and passed structural inspection. A proof of a registered chapter (`--manuscript`) follows the same rules; the manuscript must already pass `inspect_callouts.py`.
