# SVG production

Use these rules for the editable master.

## Safe, portable file

- Use one standalone SVG with a numeric `viewBox` and SVG namespace.
- Include a nonempty `<title>` and `<desc>`, give them IDs, and connect them with `role="img"` and `aria-labelledby` on the root.
- Keep CSS and definitions inside the SVG. Use no scripts, event-handler attributes, `foreignObject`, remote fonts, remote styles, or external images.
- Prefer basic paths, lines, rectangles, circles, text, groups, markers, and patterns that survive office, browser, EPUB, and PDF conversion.
- Give every maintained node, connector, label, marker, and accessibility element a unique stable ID.
- Treat embedded raster images as separately licensed component artifacts and document them in the diagram specification.

Run `scripts/validate_svg.py` to check this structural subset. The script does not certify accessibility, browser compatibility, visual quality, or factual accuracy.

## Layout

Draw connectors before nodes so arrows sit behind shapes. Attach edges to node boundaries rather than running lines through labels. Use a consistent grid, generous internal padding, and enough separation to distinguish crossing lines.

Keep the normal reading direction of the active locale unless the content demands another path. Make the entry point and terminal states visible without a decorative title competing with the book caption.

Use semantic palette roles such as neutral, process, evidence, caution, risk, and outcome. Repeat each role with a label, icon, border, line pattern, or shape. Test in grayscale; two fills that collapse to the same tone cannot carry different meanings alone.

## Hand-drawn treatment

Take the contour, shape language, restrained texture, and palette from the approved project setup. Slightly irregular non-semantic outlines and sparse paper-like marks can retain the hand-drawn character in editable SVG. Keep arrow direction, data coordinates, anatomy, thresholds, and reading order exact. Texture must not compete with small labels or imply extra data. A precise diagram may use a quieter hand-drawn treatment than a scene illustration; record that choice in its specification.

Preserve live typeset labels and stable element IDs. The hand-drawn look does not require rasterizing the master or asking an image model to draw exact text. If a mascot is requested, use the selected project's approved identity rather than importing Nam by default.

## Text

Typeset exact labels in `<text>` elements. Use system-safe or explicitly licensed fonts and record the fallback stack. Preserve live text in the master even if a derivative converts glyphs to outlines.

Set type for its final physical placement, not for a zoomed browser canvas. Verify the project's minimum body and caption sizes after scaling. Expand boxes or revise wording for localization rather than compressing or clipping text.

Use units beside values and expand uncommon abbreviations in the figure, caption, or long description. Do not place a citation marker where conversion could detach it from the supported element.

## Accessibility

The title names the figure's subject. The description communicates its structure, reading order, and key conclusion. A complex diagram also needs a maintained long description in the manuscript or adjacent artifact.

DOM order should follow the intended reading order even when visible positions differ. Decorative background elements follow meaningful content or carry appropriate hidden semantics in the consuming format.

## Verification

1. Parse and structurally inspect the SVG.
2. Render in at least one browser and the actual publication conversion path.
3. Inspect at final print size, digital reading size, and grayscale.
4. Check crop, clipping, font substitution, connector direction, overlap, and contrast.
5. Compare every node, edge, label, number, and unit with the approved specification.
6. Recheck caption, alt text, and long description after the final visual revision.

Record what was not tested. A successful XML parse is not a successful diagram review.
