# Architecture contract

The architecture is a decision artifact, not a prose outline. It must satisfy
[book-architecture.schema.json](../../asknam/references/schemas/book-architecture.schema.json) and include the following semantics.

## Stable identity

- `chapter_id`: one enduring reader transformation
- `objective_id`: one observable learning outcome
- `claim_id`: one independently supportable proposition
- `figure_id`: one visual with a defined learning job
- `item_id`: one planned assessment item or item family

Titles and wording may change without changing identity. Reuse an ID only while
the underlying meaning remains the same. Retire rather than recycle changed IDs.

## Chapter record

Each chapter records:

- purpose and prerequisites through `depends_on`
- word target and profile-specific chapter pattern
- objectives with coverage sufficient to test the reader promise
- planned claims, risk, and required evidence IDs
- planned visuals with `kind`, `learning_job`, `structure` for diagrams and
  hybrids, and an optional `placement` hint
- planned assessments mapped to objective IDs

The chapter graph must be acyclic. Every dependency must appear earlier in a
valid topological order, though the stored chapter list may be regrouped for
parts after validation.

## Planned visuals

Each `planned_visuals` entry carries the shared visual vocabulary so the visual
brief, the diagram skill, and publish inherit one plan instead of rediscovering
it:

- `kind`: `illustration`, `diagram`, `table`, `data-graphic`, `photograph`,
  `hybrid`, or `other`, matching the visual brief's routing table.
- `structure`: the reading rule of the visual: `process`, `hierarchy`,
  `comparison`, `timeline`, `cycle`, `spatial`, `mechanism`, `decision-path`,
  or `scene`. Required for `diagram` and `hybrid`; optional for other kinds.
  `mechanism` covers pathophysiology and pathogenesis, `decision-path` covers
  algorithms and clinical pathways, `spatial` covers anatomy and maps, and
  `scene` marks an expressive illustration with no exact geometry.
- `placement`: where the visual's body sits on a fixed page: `inline`,
  `side-column`, `band`, `full-page`, `opener`, or `spread`, the same tokens
  callouts and the design spec use. Absent means the design spec's
  `figures.default_placement`. It is a planning hint: the visual brief may
  refine it and publish may override it by page geometry, and both report the
  change rather than silently moving the figure.

## Evidence readiness

R0/R1 claims may be planned before evidence is complete when explicitly marked.
R2/R3 claims retain evidence IDs from the ledger. A metadata match or search
snippet is not evidence. Missing, conflicting, inaccessible, corrected, or
retracted support blocks the affected chapter rather than disappearing from the
architecture.

## Change report

For revisions, compare identities and meanings, then report:

- IDs retained without semantic change
- IDs added or retired
- IDs whose meaning, risk, evidence, objective coverage, or dependencies changed
- affected chapter drafts, teaching blocks, assessment items, figures, edits,
  localizations, and approvals

Meaning changes invalidate descendants even when filenames remain unchanged.
