---
name: asknam
description: Route and run a Nam Book Studio project. Invoke explicitly to start, resume, revise, audit, illustrate, localize, or publish a book through the smallest sufficient specialist workflow.
---

# AskNam

AskNam is the state-owning coordinator. It chooses and invokes model-invoked
specialists; it does not ask the user to remember the pipeline. Specialists may
write their declared artifacts, but only AskNam changes `.nam-book/project.json`.
Its required profiles and shared JSON Schemas are bundled under `references/`,
so initialization does not depend on the source repository layout.

## Establish the project

Locate the manifest supplied by the user or `.nam-book/project.json` beneath the
book project root.

For a new project, settle only decisions that change the route:

- working title, audience, and concrete reader outcome
- `friendly-explainer`, `textbook`, or `exam-prep`
- source locale and optional target locale: `en-US` or `id-ID`
- requested deliverables
- assessment, illustration, and diagram needs
- whether the subject is medical and its `R0`-`R3` risk

Medical work also requires jurisdiction, evidence cutoff, and a
revalidation-before-export date. Summarize these decisions and obtain the
project-brief approval before starting specialists.

Initialize state with `scripts/init_project.py`. It refuses to overwrite an
existing manifest. Then record the approval with `scripts/update_state.py`.
Read [state-protocol.md](references/state-protocol.md) before the first state
mutation or whenever resuming an existing project.

## Route

Run `scripts/validate_state.py` before planning. Refresh file staleness before a
resume, revision, localization, or publication. Resolve validation errors before
dispatch; surface warnings that affect a decision.

Run `scripts/plan_route.py` with the user's intent. Read
[routing.md](references/routing.md) when selecting an intent, explaining a
branch, or deciding whether ready nodes can run concurrently. The generated DAG
and [skill-catalog.json](references/skill-catalog.json) are authoritative; do
not replace them with a remembered pipeline.

Report the route briefly: selected specialists, deliberate omissions, current
blockers, approval gates, and the next ready nodes.

## Execute

For each ready node, or stale node whose live dependency and approval blockers
are empty:

1. Transition its exact route-node ID to `running` with
   `scripts/update_state.py`. Publication has separate proof and release nodes.
2. Call the Skill tool with that node's exact `skill` value. Pass the manifest
   path, selected profile, locale, relevant artifact IDs and hashes, and the
   registry slots it may write. Invoke one skill per call.
3. Require the specialist to return an artifact report. It must not edit the
   global manifest.
4. Inspect each returned file, then register it with `register-artifact`. Include
   its input artifacts; claim, source, objective, figure, item, and semantic-block
   IDs; returned blockers; provenance; operation; and producer-node ID. AskNam
   snapshots every revision before updating the current registry view.
5. Validate state and transition the node to `complete` only after its required
   output exists and its blockers are clear.

Ready nodes may run in parallel only when the DAG has no path between them and
they write disjoint artifact slots. Give each subagent a bounded specialist call;
serialize every state update through AskNam after the results return.

At an approval gate, show the actual artifact or validation report being
approved. Record the decision maker and artifact hashes as the approval basis.
Continue automatically after approval; stop on rejection, unresolved evidence,
rights uncertainty, or a specialist failure that changes the route.

For medical content or any `R2`/`R3` claim, read
[medical-safety.md](references/medical-safety.md) before dispatch and before
publication.

Publication is two-phase. Run `nam-book-publish-proof` without final-proof
approval, validate that exact versioned proof, obtain hash-bound approvals, then
run `nam-book-publish-release`. Never treat proof generation as release.

## Revisions and staleness

Treat a changed input hash as an invalidation, not a cosmetic edit. Register a
new revision or mark the artifact stale, expire approvals whose basis changed,
replan, and rerun every invalidated descendant. Changes to `R2`/`R3` claims in
editing or localization reopen research and validation.

Never infer that a skill is absent merely because an explicit-only skill is not
visible to the model. The catalog records the bundle; a failed explicit call is
the evidence that execution is unavailable.

## Completion

The project is complete only when all selected nodes are complete, no open
staleness records or blocking validation findings remain, required approvals are
current, medical evidence is within its freshness window, and every requested
deliverable has a verified publication artifact. Return paths to the manifest,
final validation report, deliverables, and any residual limitations.
