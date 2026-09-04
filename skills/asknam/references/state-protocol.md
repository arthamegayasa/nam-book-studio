# State protocol

The manifest at `.nam-book/project.json` is the durable control plane. AskNam is
its only writer. Specialist outputs are immutable inputs until AskNam registers a
new revision.

Resolve every helper path from the directory containing AskNam's `SKILL.md`.
The command examples below use `skills/asknam/` because they are runnable from a
repository checkout; in an installed copy, use the absolute path to the installed
AskNam directory.

AskNam's canonical runtime profiles and schemas live in `references/profiles/`
and `references/schemas/`. Top-level repository copies are publishing mirrors,
not runtime dependencies. Run
`python skills/asknam/scripts/validate_resources.py --require-mirrors` when
developing the repository; an installed AskNam skill can run the same command
without the flag to validate its self-contained bundle.

## Initialize

```bash
python skills/asknam/scripts/init_project.py \
  --project-dir . \
  --title "Working title" \
  --audience "Defined reader" \
  --reader-outcome "What the reader can do afterward" \
  --profile friendly-explainer \
  --source-locale id-ID \
  --risk-level R0 \
  --deliverable markdown \
  --deliverable pdf
```

Use `--medical`, `--jurisdiction`, `--evidence-cutoff`, and
`--revalidate-before-export` together for medical projects. Feature switches
accept `auto`, `yes`, or `no`; a locked profile requirement cannot be disabled.

## Validate and plan

```bash
python skills/asknam/scripts/validate_state.py --state .nam-book/project.json
python skills/asknam/scripts/update_state.py --state .nam-book/project.json refresh-staleness
python skills/asknam/scripts/plan_route.py --state .nam-book/project.json --intent resume
```

Validation is read-only. Planning and update commands write atomically. A
warning requires judgment; an error prevents dispatch.

For an illustration-direction-only request, plan with `--intent setup-illustration`.
The route contains only `nam-book-illustration-setup`, regardless of feature
switches or medical risk. Medical evidence checks still apply when content
production or publication resumes. Omitted nodes are retained as
`route.parked_nodes` and restored by later replanning; never manually clear them.

## Upgrade an existing visual project

Old manifests remain readable. When validation warns about legacy visual
ownership, run the explicit migration before the next setup or visual route:

```bash
python skills/asknam/scripts/update_state.py --state .nam-book/project.json migrate-illustration-setup
python skills/asknam/scripts/plan_route.py --state .nam-book/project.json --intent setup-illustration
```

Finish running stages first. Migration is idempotent and updates only the
manifest: it transfers the existing bible's producer to the setup skill while
preserving its stable ID, file path, bytes, revision snapshots, and provenance.
An adoption event records the prior owner. Existing `character-bible` decisions
remain historical decisions, not approval of the new setup. Visual planning,
media, and dependent integration/proof work become stale; research, architecture,
voice, and drafting are preserved.

To adopt the existing bible, inspect its assets and record the setup payload's
`adoption` object with `character_bible_artifact_id`, current `sha256`, prior
`approval_ids`, and a reason. Register a reviewed calibration bundle plus the new
setup; the adopted bible can remain byte-for-byte unchanged. A new-format bible
declares the same `mascot_mode` as the setup. Both are bound by a fresh
`illustration-setup` approval; migration alone grants no production approval.

## Approvals

```bash
python skills/asknam/scripts/update_state.py --state .nam-book/project.json approval \
  --id architecture --decision approved --by "Reviewer name" \
  --basis book-architecture --note "Scope and chapter graph accepted"
```

Approval basis hashes make decisions expire when the reviewed bytes change.
Project-brief approval may have no artifact basis because it approves the
manifest fields themselves.

For `illustration-setup`, complete the setup node first, then approve with both
`--basis illustration-setup` and `--basis character-bible` (use the actual IDs).
The helper inspects the real setup JSON: `mascot_mode` is `custom`, `supplied`,
`nam`, or `none`; `hand_drawn` is true; `calibration.status` is `passed`; and
`calibration.sample_artifact_ids` names at least one registered
`illustration_calibration` input. The sample slot is a directory bundle at
`visuals/calibration/{artifact_id}` inside the registry root. Keep inspected
PNG, JPEG, or SVG samples and their labels there in their real formats.
Tree hashing binds every file in the bundle. This checks recorded inspection
and fingerprints, not whether an image is aesthetically good or legally cleared.
Changing a setup, bible, or calibration input expires the paired decision and
invalidates visual descendants, including those parked by a focused route.

## Artifact report contract

Every specialist returns:

- artifact ID, kind, and registry-resolved relative path
- schema version, project ID, chapter ID when scoped, and locale
- producing skill and status
- every input artifact ID and hash
- producer-node ID and operation
- preserved claim, source, figure, item, objective, and semantic-block IDs
- blockers and unresolved questions
- origin, creator, license, source URL, and required notice path

`blockers` is an operational gate, not a notes field. A non-empty blocker list
requires artifact status `blocked`; `draft`, `review`, `approved`, and `locked`
artifacts must have no open blockers. Put non-blocking limitations in the
artifact's report content instead.

Register the file only after it exists:

```bash
python skills/asknam/scripts/update_state.py --state .nam-book/project.json register-artifact \
  --id book-architecture \
  --kind book_architecture \
  --path .nam-book/artifacts/architecture/book-architecture.json \
  --produced-by nam-book-architect \
  --status review \
  --locale id-ID \
  --input evidence-ledger \
  --objective-id objective-001 \
  --semantic-block-id block-001
```

The path must resolve exactly from the manifest's artifact slot. Registration
copies the bytes into an immutable `.nam-book/history/<artifact-id>/` snapshot;
later registrations append revisions and never replace a historical snapshot.
Imported
skills, templates, illustrations, fonts, references, and quotations need real
provenance and license values; project-generated work may use the defaults.

## Node transitions

```bash
python skills/asknam/scripts/update_state.py --state .nam-book/project.json transition \
  --node nam-book-research --status running
```

A node cannot run through dependency or approval blockers. It cannot complete
without a registered output. Validate after every batch of registrations and
transitions.

For publication, run `nam-book-publish-proof` first and register its bundle and
report with `--operation proof --status review`. After validation, approve
`final-proof` against the proof bundle hash. Then run
`nam-book-publish-release` and register its new artifacts with
`--operation release`; release inputs must include every proof in the approval
basis.

## Staleness

Use `refresh-staleness` to compare files with registered hashes, or mark an
artifact explicitly:

```bash
python skills/asknam/scripts/update_state.py --state .nam-book/project.json mark-stale \
  --artifact edited-id --reason "High-risk claim changed" --high-risk-change
```

Staleness propagates through the route, expires hash-based approvals, and reopens
research and validation for high-risk editorial or localization changes. After
producing and registering the replacement, replan rather than manually clearing
downstream blockers.

A stale node keeps its current dependency and approval blockers. Rerun only the
stale nodes with an empty blocker list; completing one unlocks the next affected
descendants. While rerunning, register every required output again so its
revision timestamp postdates the invalidation. The staleness record remains open
until all invalidated nodes are complete.
