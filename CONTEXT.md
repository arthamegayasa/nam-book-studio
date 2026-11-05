# Nam Book Studio

Shared language for the book-authoring skill suite: an orchestrator (AskNam) and specialists that take a book from idea to DOCX, EPUB, and PDF with stable IDs, evidence ledgers, hand-drawn visuals, and bilingual editions. Terms here are the canonical vocabulary for skills, schemas, and tickets; implementation detail lives in the skills and schemas themselves.

## Modes and configuration

**Book mode**:
The pedagogical configuration of a book: `friendly-explainer`, `textbook`, or `exam-prep`. It governs reader experience, not evidence requirements.
_Avoid_: book type, genre, register

**Profile**:
The stored defaults of a book mode (features, word targets, chapter pattern). A profile implements a mode; a project selects one.
_Avoid_: preset (reserved for design presets), template

**Content risk**:
The `R0`-`R3` level of a claim or project that decides evidence and review requirements. Independent of book mode.
_Avoid_: difficulty, sensitivity

## Manuscript elements

**Callout**:
A typed, labeled, set-off element of a chapter (Tip, Warning, Reflection prompt, and so on) with a stable `callout_id`, exactly one callout type, one linked objective, and a placement hint.
_Avoid_: box, typed block, teaching block, admonition, aside, sidebar

**Callout type**:
The pedagogical kind of a callout, drawn from the callout catalog. It decides the displayed label per locale, the icon slot, the default placement, and which book modes may use it.
_Avoid_: callout kind, box style, callout class

**Callout catalog**:
The single registry of callout types with their labels in every supported locale, allowed modes, placements, and reveal rules.
_Avoid_: label table, callout list

**Reflection prompt**:
An unscored callout type that asks the reader an open question tied to an objective. It has no answer key; at most a discussion appears later.
_Avoid_: reflection question, discussion box, open item, think box

**Quick check**:
A callout type that places a retrieval prompt in the chapter. The stem lives in the manuscript; the key and rationale live in the linked assessment item.
_Avoid_: self-check, mini quiz, practice question (as type names)

**Reveal rule**:
Where a quick check's answer, or a reflection prompt's discussion, appears relative to the prompt: `none`, `inline`, `chapter-end`, or `book-end`.
_Avoid_: answer policy, key location

**Semantic block**:
An addressable unit of manuscript prose with a stable ID that editing and localization align on. Callouts are tracked by their own IDs and are not semantic blocks.
_Avoid_: block (unqualified), paragraph ID, chunk

**Figure reference**:
The in-text mention that points the reader to a figure or table.
_Avoid_: figure callout, table callout, figure call

## Page design

**Design spec**:
The project-level description of how the book looks: trim, page grid, typography, color roles, callout styles per placement, icon set, chapter opener, figure and table styles, running heads, and render engines. One per project, started from a mode preset.
_Avoid_: stylesheet, theme, template, layout file

**Design preset**:
A complete design spec for one book mode that a project starts from and then adapts. The approved spec, not the preset, is the contract.
_Avoid_: default design, profile (that is the mode's pedagogical defaults)

**Design assets**:
The files generated from the design spec that the build path consumes: print and EPUB stylesheets, the callout filter, the reference document, and the icon set. Derived, never hand-edited.
_Avoid_: theme files, templates

**Design proof**:
The sample chapter rendered through the real build path from a specific design spec and assets, with its report and build manifest. It is the evidence the author approves on; the spec and assets are what gets approved.
_Avoid_: preview, mock-up, draft layout

**Sample chapter**:
The bundled, original, non-medical chapter that exercises every callout type, a figure, a table, a quick check with its answer key, and the chapter opener; filtered to the active mode when rendered.
_Avoid_: demo chapter, lorem ipsum

**Render path**:
The single build pipeline shared by the design proof and publication: Pandoc for DOCX, EPUB, and HTML; a Chromium-family browser or LibreOffice for PDF.
_Avoid_: export, conversion script

## Layout vocabulary

**Placement**:
A hint about where an element's body sits on a fixed page: `inline`, `side-column`, `band`, `full-page`, `opener`, or `spread`. Callouts use the first five; planned visuals may use all six. Reflowable formats degrade it; the design spec owns the treatment.
_Avoid_: position, layout slot, margin, float
