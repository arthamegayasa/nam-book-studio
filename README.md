# Nam Book Studio

![Nam, the friendly Bali-starling page guide](assets/nam-icon.png)

Nam Book Studio is an open, modular skill suite for creating complete books with Codex and other Agent Skills-compatible hosts. It covers the whole path from a rough idea to researched chapters, instructional features, original illustrations, assessments, bilingual editions, and production-ready files.

`AskNam` is the single front door. It inspects the request and saved project state, selects the smallest useful set of specialist skills, coordinates safe parallel work, validates handoffs, and resumes long projects without regenerating approved material.

The repository and runtime instructions are English. Book projects currently support `en-US` and `id-ID` as source or target locales, with explicit terminology and parity guidance in both directions.

## What makes this different

- One explicit orchestrator and fourteen independently invokable specialists inside the installed suite.
- Three genuinely different modes: `friendly-explainer`, `textbook`, and `exam-prep`.
- Stable artifact IDs, saved state, approvals, and dependency-aware staleness.
- Evidence ledgers that distinguish discovery, metadata checks, claim support, and expert review.
- Upfront, project-specific hand-drawn art setup: custom mascot, supplied identity, original Nam preset, or no mascot.
- Separate raster-illustration and editable-diagram workflows with an approved shared visual direction.
- Objective-linked callouts, visuals, examples, and assessment items.
- English-Indonesian localization with semantic parity checks.
- Release gates for evidence, pedagogy, assessment, rights, accessibility, and builds.
- Medical risk levels that prevent unreviewed clinical guidance from being labeled release-ready.

The `friendly-explainer` mode uses approachable explanations, visual anchors, tips, warnings, and analogies without copying the name, trade dress, or proprietary system of any commercial book series.

## Skill map

| Skill | Responsibility |
| --- | --- |
| `$asknam` | Route, initialize, resume, coordinate, and report book-project state |
| `$nam-book-architect` | Define audience, promise, outcomes, scope, structure, and chapter specifications |
| `$nam-book-research` | Discover and verify sources; maintain source and claim-evidence ledgers |
| `$nam-book-write` | Draft source-grounded chapters from approved specifications |
| `$nam-book-teach` | Add purposeful explanations, examples, callouts, recaps, and misconception repair |
| `$nam-book-assess` | Build blueprints, original questions, rationales, and item-quality reviews |
| `$nam-book-illustration-setup` | Set project art direction, inspect references, define a mascot or mascot-free system, and prepare calibration for approval |
| `$nam-book-visuals` | Plan visual coverage and choose illustration, diagram, table, or data graphic |
| `$nam-book-illustrate` | Create hand-drawn raster illustrations using the project's approved style and selected identity |
| `$nam-book-diagram` | Produce editable, accessible SVG mechanisms, algorithms, and comparisons |
| `$nam-book-voice` | Build an authorized voice profile or audit drift; writing and editing apply the profile |
| `$nam-book-edit` | Perform developmental, line, copy, consistency, and integration edits |
| `$nam-book-localize` | Create aligned locale editions and verify semantic parity |
| `$nam-book-publish` | Design and build DOCX, EPUB, screen PDF, and print PDF deliverables |
| `$nam-book-validate` | Run independent quality gates and issue a release decision |

## Workflow

```text
Approved project brief
       |                                  |
       v                                  v
Research -> Architecture -> Voice     Illustration setup
                |             |      references, style, mascot
                v             v           |
           Assessment       Draft     Human art approval
                              |           |
                           Teaching       |
                              |           |
                              +---> Visual plan <--- Architecture + Voice
                                       |
                              Illustration / Diagram
                                       |
Teaching + Assessment + Visuals -> Voice-aware edit
                                       |
                              Optional localization
                                       |
                                  Proof build
                                       |
                               Release validation
                                       |
                              Final-proof approval
                                       |
                                     Release
```

This is a workflow overview; the [routing contract](skills/asknam/references/routing.md) defines the exact dependency graph. Illustration setup can start alongside research once the project brief is approved. It does not wait for chapters to be drafted. AskNam can route a focused request directly to one specialist, resume from an approved stage, or rerun only artifacts made stale by an upstream change. Projects without illustrations or diagrams omit the visual lane.

## Install

### Through Codex

Ask the built-in skill installer to install every skill path from this repository:

```text
Use $skill-installer to install these paths from arthamegayasa/nam-book-studio:
skills/asknam, skills/nam-book-architect, skills/nam-book-research,
skills/nam-book-write, skills/nam-book-teach, skills/nam-book-assess,
skills/nam-book-illustration-setup, skills/nam-book-visuals,
skills/nam-book-illustrate, skills/nam-book-diagram,
skills/nam-book-voice, skills/nam-book-edit, skills/nam-book-localize,
skills/nam-book-publish, and skills/nam-book-validate.
```

Codex discovers user skills under `~/.agents/skills`. If an installation does not appear immediately, restart Codex. See the [official OpenAI skill documentation](https://learn.chatgpt.com/docs/build-skills) for current locations and invocation behavior.

### Manual installation

Clone the repository and copy every directory under `skills/` into your host's skills directory. Keep the suite together: AskNam carries the shared profiles and schemas, and specialists resolve those resources from their sibling AskNam installation.

The root `.codex-plugin/plugin.json` also packages the suite as one Codex plugin for hosts and marketplaces that support plugin installation.

## Start with AskNam

Explicit invocation keeps the router easy to remember and prevents it from intercepting unrelated writing tasks:

```text
Use $asknam to create a friendly-explainer book about personal finance for first-time workers.
Write it in Indonesian, plan an English edition, use frequent purposeful visuals,
and prepare DOCX, EPUB, and screen PDF outputs.
```

```text
Use $asknam to design a medical exam-prep book from the official blueprint and my notes.
Require verified evidence for clinical claims, original MCQs with distractor rationales,
and clinician review before release.
```

```text
Use $asknam to resume the book project in this directory and complete the next unblocked milestone.
```

AskNam asks only for decisions that materially change the result. It records assumptions for everything else.

## Set up illustrations first

```text
Use $asknam to set up the illustrations before writing this book.
It is an Indonesian guide to ocean conservation for teenagers.
Use my attached turtle drawing as the mascot identity and the second image
only as a line-and-texture reference. Keep a simple, friendly hand-drawn look.
Show me a calibration sample before producing chapter illustrations.
```

AskNam selects `$nam-book-illustration-setup` for this request. The specialist separates identity references from style references, records project-specific anchors, and prepares a small calibration sample for human approval. Nam is a selectable preset, not a requirement. A mascot-free book still receives a coherent hand-drawn style contract.

The setup records visual tokens, mascot choice, reference hashes, rights status, cultural context, permitted variations, and continuity checks. Missing reference files or image tools are reported honestly; a written prompt is not presented as a rendered sample. Only approved setup artifacts unlock production. See the [illustration setup guide](docs/illustration-setup.md) for the four modes, examples, and existing-project upgrades.

## Book modes

| Mode | Reader experience | Typical elements |
| --- | --- | --- |
| `friendly-explainer` | Motivation first, defined jargon, short conceptual chunks, warm adult voice | Big Idea, Why It Matters, Tip, Remember, Warning, Myth vs Fact, Technical Corner, quick check |
| `textbook` | Systematic progression, terminology discipline, evidence-rich teaching | Objectives, key terms, mechanisms, applications, cases, figures, tables, summary, self-assessment |
| `exam-prep` | Blueprint-aligned retrieval and decision practice | Must Know, High-Yield, Exam Trap, Clinical Pearl where appropriate, algorithms, rapid review, original practice items |

Element density is a design decision, not a quota. The suite places a visual or callout when it reduces cognitive load or repairs a likely misconception, rather than mechanically adding one every few pages.

## Evidence and medical safety

The evidence workflow uses separate records for sources and claims. Metadata resolution confirms that a publication exists; it does not confirm that the publication supports a sentence. Each higher-risk claim carries a locator, support status, currency review, jurisdiction where relevant, and review state.

Medical content uses four risk levels:

- `R0`: ordinary nonclinical description.
- `R1`: educational factual content.
- `R2`: clinical or diagnostic content requiring authoritative, retrievable support.
- `R3`: dosing, contraindications, emergency action, treatment, or patient-management guidance requiring authoritative support and named expert sign-off.

No disclaimer substitutes for evidence. Without required review, high-risk output remains clearly marked as draft and cannot pass the release gate.

## Nam preset identity

When a project chooses the Nam preset, Nam is an original Bali-starling-inspired page spirit: a compact white paper-like bird, a charcoal folded-page wing, a small swept crest, warm terracotta feet, a restrained geometric sash accent, and simple round charcoal eyes without blue facial markings. The character is designed to remain recognizable at small sizes and to participate in the concept rather than stand beside it as decoration. These anchors belong to Nam; they are not imposed on a custom mascot.

Balinese cues remain subtle and respectful. Sacred symbols, ceremonial clothing, and religious objects are outside the default visual vocabulary. The canonical model sheet, transparent icon, prompt fragments, provenance, and consistency rules live in `skills/nam-book-illustrate/assets/nam-v1/` and that skill's references.

## Project artifacts

A project initialized by AskNam stores its control plane at `.nam-book/project.json` and registry-backed outputs under `.nam-book/artifacts/`. Slots appear when their producing skills run:

```text
.nam-book/
|-- project.json
|-- history/<artifact_id>/r<revision>...
`-- artifacts/
    |-- research/
    |   |-- research-brief.json
    |   |-- evidence-ledger.json
    |   `-- change-reports/<artifact_id>.json
    |-- architecture/
    |   |-- book-architecture.json
    |   `-- change-reports/<artifact_id>.json
    |-- voice-profile.yaml
    |-- chapters/<chapter_id>/
    |   |-- draft.<locale>.md
    |   `-- enriched.<locale>.md
    |-- teaching-plan.yaml
    |-- assessment-blueprint.yaml
    |-- items.<locale>.yaml
    |-- visuals/
    |   |-- illustration-setup.json
    |   |-- calibration/<artifact_id>/
    |   |-- visual-brief.json
    |   |-- character-bible.json
    |   |-- diagrams/specs/<artifact_id>.json
    |   |-- diagrams/assets/<artifact_id>.svg
    |   |-- illustrations/briefs/<artifact_id>.json
    |   `-- illustrations/assets/<artifact_id>.png
    |-- edited.<locale>.md
    |-- edit-report.yaml
    |-- localized/<locale>.md
    |-- localization-report.yaml
    |-- validation/validation-report.json
    `-- publication/
        |-- <artifact_id>/
        `-- reports/<artifact_id>.json
```

Stable IDs connect objectives, claims, sources, figures, callouts, questions, and translations. A changed dependency marks affected registry entries `stale`. AskNam snapshots every registered artifact revision under `.nam-book/history/`; normal project backups or Git remain recommended for disaster recovery.

## Validate this repository

The project uses Python's standard library only for structural checks:

```bash
python scripts/validate_repository.py
python -m unittest discover -s tests -v
python skills/asknam/scripts/test_state_tools.py
python skills/asknam/scripts/validate_resources.py --require-mirrors
```

Each skill should also pass OpenAI's `quick_validate.py` from the built-in `skill-creator` skill. The plugin manifest should pass `validate_plugin.py` from the built-in `plugin-creator` skill.

## Research, attribution, and originality

This suite was designed after auditing several MIT-licensed public skill projects. Their useful architectural ideas, limitations, exact revisions, and licensing details are documented in [the source audit](docs/research/source-audit.md) and [third-party notices](THIRD_PARTY_NOTICES.md).

No upstream mascot images are included. The Nam assets were generated from a new character brief and revised to the user's approved round-eye design. No affiliation with the audited projects, their authors, publishers, or commercial book brands is claimed.

## License

Code, skill instructions, and project-owned assets are released under the [MIT License](LICENSE), subject to the provenance and third-party notes recorded in the repository. Generated imagery remains subject to applicable platform terms and any rights that may apply in your jurisdiction.
