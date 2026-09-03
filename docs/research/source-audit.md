# Source audit

Audit date: 2026-09-03.

This audit identifies the public projects described in the originating brief, verifies their licenses and current structures, and records what Nam Book Studio should learn from or avoid. Technical observations refer to immutable GitHub revisions.

## Audited sources

| Capability | Primary source | Revision | License |
| --- | --- | --- | --- |
| Academic book pipeline | [lensetek/Book-Author-Agent-Skills](https://github.com/lensetek/Book-Author-Agent-Skills/tree/0e8770a18c096e58ce81b6a31185e5f1dfbffbaf) | `0e8770a` | [MIT, Andy Ismail](https://github.com/lensetek/Book-Author-Agent-Skills/blob/0e8770a18c096e58ce81b6a31185e5f1dfbffbaf/LICENSE) |
| Quiz generation | [SkillMedev/skills](https://github.com/SkillMedev/skills/blob/a28c4ce9366b5a8540577bed8f70b6a60f8fde27/skills/quiz-generator/SKILL.md) | `a28c4ce` | [MIT, Alexander Ouellet](https://github.com/SkillMedev/skills/blob/a28c4ce9366b5a8540577bed8f70b6a60f8fde27/LICENSE) |
| Hand-drawn illustration | [tonykipkemboi/illustrations-codex-skill](https://github.com/tonykipkemboi/illustrations-codex-skill/tree/a08e9eb560f88867a5924582774c7f9ae9a91c0e) | `a08e9eb` | [MIT, Ian and Tony Kipkemboi](https://github.com/tonykipkemboi/illustrations-codex-skill/blob/a08e9eb560f88867a5924582774c7f9ae9a91c0e/LICENSE) |
| Diagram production | [openclaw/openclaw diagram-maker](https://github.com/openclaw/openclaw/tree/0591b31388342d00f9be1aec7e2f96ee96e7a96a/skills/diagram-maker) | `0591b31` | [MIT, OpenClaw Foundation](https://github.com/openclaw/openclaw/blob/0591b31388342d00f9be1aec7e2f96ee96e7a96a/LICENSE) |
| Voice revision | [blader/humanizer](https://github.com/blader/humanizer/tree/e2e92e7b4b8229253ed5c8e81dc65463fdeddda5) | `e2e92e7` | [MIT, Siqi Chen](https://github.com/blader/humanizer/blob/e2e92e7b4b8229253ed5c8e81dc65463fdeddda5/LICENSE) |
| Exam study planning | [microsoft/cat-agent-skills submission](https://github.com/microsoft/cat-agent-skills/tree/17aa9e5b88e9c98505a1e4ef84f2a4e1c883ba18/submissions/exam-prep-learning-plan-builder) | `17aa9e5` | [MIT, Microsoft](https://github.com/microsoft/cat-agent-skills/blob/17aa9e5b88e9c98505a1e4ef84f2a4e1c883ba18/LICENSE) |
| Router pattern | [mattpocock/skills Ask Matt](https://github.com/mattpocock/skills/blob/6654f6b60cd9d5be8b54c6fafe44346dabeb3b76/skills/engineering/ask-matt/SKILL.md) | `6654f6b` | [MIT, Matt Pocock](https://github.com/mattpocock/skills/blob/6654f6b60cd9d5be8b54c6fafe44346dabeb3b76/LICENSE) |

The name “Humanizer” was ambiguous in the source brief. Many unrelated repositories use it. `blader/humanizer` was selected as the most probable upstream and used only as a design study.

## Academic book pipeline

The inspected Book Author Agent Skills revision contains 26 skills, 24 OpenAI UI descriptors, eight Python helpers, and three orchestrator references. Its strongest patterns are:

- orchestration separated from specialist work;
- source-type routing for ideas, course plans, single studies, and corpora;
- explicit input and output envelopes;
- separate voice, citation, originality, academic review, editing, layout, and export roles;
- privacy checks at intake and before delivery.

Important limitations shaped this implementation:

- The public README still reports 24 skills while the inspected tree contains 26. A catalog must be validated against the filesystem.
- It has no dedicated illustration, assessment, or EPUB specialist.
- Several skills embed one Indonesian publisher's brand, URL, logo, dimensions, and typography as defaults. A general public suite must keep publisher presets configurable.
- It ships no dependency lock or repository CI for its helpers.
- [`fetch_evidence_snippet.py`](https://github.com/lensetek/Book-Author-Agent-Skills/blob/0e8770a18c096e58ce81b6a31185e5f1dfbffbaf/.codex/skills/scripts/fetch_evidence_snippet.py#L46-L72) queries only OpenAlex even though surrounding documentation names several providers. On a failed fetch, it writes a failure message but still records `VALIDATED_FACTUAL_GROUNDING` and `SUCCESS`.
- [`validate_references.py`](https://github.com/lensetek/Book-Author-Agent-Skills/blob/0e8770a18c096e58ce81b6a31185e5f1dfbffbaf/.codex/skills/scripts/validate_references.py#L42-L84) resolves DOI metadata; it does not establish that a source supports a manuscript claim.

Nam therefore uses explicit `unverified`, `unsupported`, `conflicting`, and `fetch_failed` states. A network failure cannot become validated evidence, and reference metadata cannot satisfy a claim-support gate by itself.

## Assessment

The Skill Me Quiz Generator is a focused, dependency-free skill. It gathers objectives and learner level, declares a Bloom-level distribution before writing, matches item types to cognitive demand, derives distractors from misconceptions, provides rationales, and reconciles the actual distribution.

That is a sound base, but a book system also needs stable item IDs, evidence links, versioning, duplicate checks, answer-position analysis, bias/accessibility review, student and instructor editions, and explicit human review for high-stakes content. Fixed percentages are useful defaults, not universal rules.

The Microsoft exam-plan submission separately contributes confidence-weighted scheduling, spaced revisits, checkpoint tests, and a triage mode when time is insufficient. Its HTML application is not part of this repository; the planning principles are represented as an optional assessment companion.

## Illustration

The audited illustration skill plans images around cognitive anchors, requires one clear visual idea per scene, uses exact label allowlists and restrained color roles, makes the mascot perform the explanatory action, and applies a post-generation QA pass.

Its notice identifies Xiaohei as part of Ian's recurring visual language. Nam Book Studio therefore includes no Xiaohei or Tony specifications, prompts, or calibration images. Nam was created from a new brief as a Bali-starling-inspired page spirit, then revised after user review to use friendly round charcoal eyes without blue eye fields.

The upstream workflow targets 16:9 article PNGs. A book workflow additionally needs trim-aware dimensions, print resolution, grayscale checks, captions, alt text, rights/provenance, bleed/safe zones, and a preference for typeset labels when exact text matters.

## Diagrams

The canonical diagram source is OpenClaw's repository; `c0ng-web/codex-skill`, which appeared in an early search, is a fork. The canonical skill routes between clean SVG/HTML, architecture SVG, and Excalidraw, selects layout before drawing, limits element density, and keeps connectors behind nodes.

Nam retains the useful format and layout separation while adding standalone SVG output, print-safe rendering, accessibility metadata, source/data IDs, grayscale verification, and raster-export checks. A diagram of a medical mechanism remains a claim-bearing artifact and must pass evidence review.

## Voice and editing

The audited Humanizer skill emphasizes preserving claims, letting a real author sample override generic style rules, checking apparent “AI tells” for false positives, and auditing the rewrite for altered names, numbers, quotations, citations, and claims.

Nam calls this capability voice fidelity and editorial revision. It never promises detector evasion. Its checklist is original; Wikipedia-derived wording and examples from upstream were not copied, avoiding an unnecessary CC BY-SA dependency inside an MIT repository.

## AskMatt and AskNam

Ask Matt is an explicit-only, hand-maintained map. It recommends a flow and stops; it neither discovers installed skills dynamically nor executes the recommendation. Its strongest contribution is cognitive: one memorable entry point, a main flow, on-ramps, standalone branches, and progressively disclosed detail.

AskNam keeps that human-friendly entry point but is an orchestrator rather than a static menu. Specialist skills remain model-invoked, allowing an explicitly selected AskNam to call them. A machine-readable catalog is checked against the installed directories. AskNam reads the selected specialist's authoritative `SKILL.md`, records a route receipt, executes the smallest sufficient dependency graph, validates every handoff, and updates durable state.

## Commercial names and cultural scope

The public modes use neutral names. Wiley describes its For Dummies brand and custom “dummification” service as licensed/proprietary on its [official custom-solutions page](https://www.dummies.com/custom-solutions/); the repository uses `friendly-explainer` and does not recreate that series' marks or trade dress.

The Nam character uses a biological and editorial cue from the Bali starling plus a restrained woven accent. It does not default to sacred symbols, ceremonial garments, temple imagery, or a tourism collage. Cultural review remains appropriate before adding context-specific Balinese religious or ceremonial material.

## Licensing decision

All audited code repositories use MIT licenses at the inspected revision, so an MIT implementation is feasible. This project uses original wording, schemas, scripts, and visual assets. If a future contributor copies or substantially adapts upstream material, they must preserve the relevant copyright and permission notice, identify exact files and modifications, and keep the license with the adapted material.
