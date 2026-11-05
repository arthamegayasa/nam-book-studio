# Architecture

## Design goal

Nam Book Studio must support a multi-month book without requiring one conversation to remember the project. The durable unit is an artifact with a stable ID, declared inputs, status, and dependency hashes. Conversation is a control surface; the project files are the memory.

## Coordinator and specialists

`AskNam` owns project-level routing and state. A specialist owns one kind of transformation and returns two things:

1. Its stage artifact, such as a chapter specification, evidence ledger, draft, visual plan, or build.
2. A stage result that states inputs, outputs, assumptions, findings, blockers, and recommended next skills.

Specialists never silently update global approval or release state. AskNam validates the stage result, records it, and marks only affected descendants stale.

## State transitions

```text
missing -> draft -> review -> approved
                    |          |
                    v          v
                 blocked     stale
```

`stale` can be cleared by regenerating or revalidating the artifact against current inputs. Marking an entry stale does not delete it. AskNam snapshots each registered revision under `.nam-book/history/`, while project backups or Git remain the disaster-recovery layer. Approval belongs to a particular artifact revision, hash, and input-hash set, not merely a path.

## Routing loop

1. Locate or initialize `.nam-book/project.json`.
2. Classify the supported route intent: start, resume, revise, audit, setup-illustration, design, illustrate, localize, or publish.
3. Resolve the target mode, locale, audience, content risk, and milestone.
4. Inspect required artifacts and select the smallest sufficient skill set.
5. Ask only for a decision whose alternatives materially change the book.
6. Run independent lanes in parallel when their inputs are approved.
7. Validate each handoff before recording state.
8. Continue until the requested milestone is complete or a genuine blocker needs user input.

## Project art direction before production

`nam-book-illustration-setup` owns the early `illustration_setup` and `character_bible` artifacts. It starts from the approved project brief and supplied references, independently of research and manuscript drafting. A project chooses a custom mascot, a supplied identity, the Nam preset, or an explicit mascot-free mode. Hand-drawn treatment remains the default across all four choices.

`nam-book-visuals` consumes this identity and style contract; it owns the later objective-linked figure inventory, not mascot creation. `nam-book-illustrate` follows the selected project's anchors, and `nam-book-diagram` applies the shared style while keeping exact geometry and labels editable. The `illustration-setup` human approval binds both setup artifacts before visual production. A changed style or identity reopens affected visual and integration work without requiring unrelated research or drafting to restart.

Existing Nam assets remain immutable calibration sources for the Nam preset. Legacy project character bibles can be adopted without changing their bytes or removing their approval history. Adoption does not silently approve new art direction: the new setup still needs its own review. See [illustration-setup.md](illustration-setup.md) for the user workflow and the AskNam state protocol for runtime details.

## Page design before typesetting

`nam-book-design` owns the project-level `design_spec` and the generated `design_assets` (CSS, Pandoc filter, reference DOCX, icon set). It starts from a mode preset, reads the approved illustration setup when the project has one so the icons follow the art direction, and renders a bundled sample chapter through the real publish build path into a `design_proof` bundle. The hash-bound `design` approval binds the spec and the assets and requires a fresh, passing proof rendered from exactly those bytes; `nam-book-publish-proof` depends on the design stage and that approval. Art identity stays with illustration setup: a design change never reopens the illustration approval, while a changed setup expires the design through the spec's registered input.

## Stable identifiers

Use human-readable, immutable identifiers:

- `chapter_id`: `ch-03`
- `objective_id`: `obj-ch03-02`
- `claim_id`: `clm-ch03-014`
- `source_id`: `src-doi-10-1234-example`
- `figure_id`: `fig-ch03-04`
- `callout_id`: `callout-ch03-02` (type-neutral: retyping a Warning as a Remember keeps the ID)
- `item_id`: `item-ch03-012`

Renaming a heading does not change its ID. When meaning changes substantially, create a new version and record the relationship.

## Book mode and risk are independent

Mode controls pedagogy and reader experience. Risk controls evidence and review. An accessible explainer can contain high-risk clinical statements; an exam-prep guide can cover a low-risk subject. Routing never treats mode as a proxy for risk.

## Release decision

The release validator reports findings as `blocker`, `major`, `minor`, or `info`. A project is release-ready only when:

- no blocker remains open;
- every required approval is recorded for the current artifact hashes;
- every requested build exists and passes its format-specific checks;
- claims, figures, questions, translations, and rights records have no orphan IDs.

Automated validation provides evidence for a release decision. It does not replace editorial, clinical, accessibility, legal, or printer review where those reviews are required.
