# Routing

AskNam compiles a route from project intent, profile, features, risk, existing
artifacts, approvals, and staleness. A bundle can contain every specialist while
one project uses only the smallest sufficient subset.

## Intent boundary

| Intent | Starting route | Additions |
| --- | --- | --- |
| `start` | Profile's full creation route | Localization when target locales exist |
| `resume` | Same capability set as start | Fresh completed nodes remain complete; stale descendants reopen |
| `revise` | Edit → proof → validate → release | Research and invalidated descendants when risk or changed inputs require them |
| `audit` | Validate | Research for medical or R2/R3 evidence |
| `illustrate` | Visual direction → requested media → validate | Illustration and diagram lanes follow feature switches |
| `localize` | Localize → proof → validate → release | Research when high-risk meaning changes |
| `publish` | Proof → validate → release | Research when medical evidence is stale |

Use `revise` when content changes. Use `audit` for a read-only quality finding.
Use `publish` only for rendering an already integrated edition.

## Profile boundary

- `friendly-explainer` prioritizes approachable sequencing, bounded analogies,
  frequent visuals, and lightweight retrieval checks.
- `textbook` prioritizes a cumulative conceptual model, explicit objectives,
  formal evidence, applications, figures, references, and self-assessment.
- `exam-prep` requires assessment. It prioritizes blueprint coverage,
  discrimination, plausible misconception-based distractors, rationales, exam
  traps, and rapid review.

Profiles are original pedagogical configurations. They do not authorize copying
another publisher's text, character, page design, or trade dress.

## Core creation DAG

```text
research → architecture → voice → writing → teaching ─┬→ diagrams ───┐
          architecture + research ───────→ assessment ─┤              │
          architecture + voice ──────────→ visuals ────┴→ illustration│
                                                                     ↓
                                                                   editing
                                                                     ↓
                                         optional localization → proof build
                                                                     ↓
                                                                 validation
                                                                     ↓
                                                           approved release
```

Only selected nodes appear in the compiled DAG. Dependencies on omitted nodes
must already be satisfied by fresh registered artifacts; otherwise replan to
include the producer.

Both publication nodes invoke `nam-book-publish`, but with different operations.
`nam-book-publish-proof` is ungated and creates `review` artifacts.
`nam-book-publish-release` depends on validation and requires `final-proof`; R3
also requires `medical-expert-signoff`. Use exact node IDs for transitions.

## Parallel lanes

After approved architecture and evidence, assessment can run independently of
chapter drafting. After an enriched draft and approved visual system, diagrams
and illustrations may run concurrently when they use disjoint figure IDs. Voice,
architecture decisions, final integration, validation, approvals, and global
state updates remain coordinated.

## Route receipt

Before dispatch, expose:

1. intent, profile, source and target locales, risk
2. selected skills in dependency order
3. omitted optional skills and the reason
4. completed, ready, stale, and blocked nodes
5. human gates and the artifact hashes they will approve
6. which ready nodes may run concurrently

The receipt explains the route; `project.json` is the source of truth.
