# EPUB production

Use this reference for reflowable ebook output. Target [EPUB 3.3](https://www.w3.org/TR/epub-33/) unless the distributor requires another documented profile, and assess accessibility against the project's declared level and [EPUB Accessibility 1.1](https://www.w3.org/TR/epub-a11y-11/).

## Package

- Store the exact `application/epub+zip` mimetype entry first and without compression.
- Include `META-INF/container.xml`, one package document, an explicit manifest, a complete spine, and an EPUB navigation document with one table-of-contents navigation element.
- Supply approved title, language, identifier, contributors, rights, modification date, cover metadata, and accessibility discoverability metadata.
- Package every required resource or document an intentional remote dependency and its offline behavior. Avoid scripts unless the requirement, reader support, security review, and fallback are explicit.

Use the official [EPUBCheck](https://github.com/w3c/epubcheck) release appropriate to the target specification. Record its version and full result; this skill's structural inspector is not a substitute.

## Content

- Use semantic XHTML headings, paragraphs, lists, tables, figures, captions, notes, code, quotations, and landmarks.
- Preserve one logical heading sequence and reading order. The navigation document must agree with the spine and visible headings.
- Keep internal links and note backlinks resolvable. Use stable fragment IDs across revisions when possible.
- Use relative dimensions and a reflowable layout by default. Fixed layout requires a real design need, target-reader testing, and an accessibility plan.
- Declare the language of the publication and any language changes within content.

## Visuals, math, and accessibility

Provide meaningful `alt` text for informative images, empty alternatives for genuinely decorative images, and long descriptions or equivalent nearby text for complex figures. Captions and source credits remain visible where required.

Keep text as text. Use SVG or MathML only when the reading-system matrix supports the chosen path, and supply the fallback needed by the project. Avoid communicating a warning, key, or assessment state by color alone.

Add the accessibility metadata required by the declared conformance claim. A metadata claim is not proof; retain the evaluator, date, report, reading-system tests, and known limitations.

## Verification

1. Run structural inspection and EPUBCheck.
2. Test navigation, notes, links, search, selection, font scaling, reflow, dark/light themes, and orientation.
3. Test the target English or Indonesian edition with representative reading systems and assistive technology required by the project.
4. Inspect images, tables, code, equations, callouts, and assessment answers at narrow and wide viewports.
5. Compare visible content and ordering with the canonical source.

List untested reading systems and accessibility criteria. Passing EPUBCheck establishes format conformance within its scope, not visual parity or complete accessibility.
