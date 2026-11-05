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

## Layout vocabulary

**Placement**:
A hint about where an element's body sits on a fixed page: `inline`, `side-column`, `band`, `full-page`, `opener`, or `spread`. Callouts use the first five; planned visuals may use all six. Reflowable formats degrade it; the design spec owns the treatment.
_Avoid_: position, layout slot, margin, float
