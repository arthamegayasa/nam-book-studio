# Repository instructions

This repository packages a coordinated set of book-authoring skills. Keep the runtime system small, explicit, and testable.

## Sources of truth

- `skills/asknam/references/skill-catalog.json` owns the skill inventory and routing metadata.
- `skills/asknam/references/profiles/` and `skills/asknam/references/schemas/` are the install-portable runtime sources; top-level `profiles/` and `schemas/` are exact publishing mirrors.
- The project contract and schemas own artifact fields and state transitions.
- Each specialist `SKILL.md` owns only its stage. Put branch-specific detail in that skill's `references/` folder.
- `scripts/validate_repository.py` defines structural repository checks.

## Invariants

- Write repository instructions, metadata, schemas, code, and examples in English. A generated manuscript follows its declared locale, including `id-ID`.
- Preserve stable IDs for chapters, objectives, claims, sources, figures, callouts, and assessment items.
- Only AskNam updates global project state. Specialists return artifacts and a stage result.
- Treat `friendly-explainer`, `textbook`, and `exam-prep` as book modes. Keep content risk separate from mode.
- Never turn a failed lookup into a successful evidence status. A DOI resolving does not prove that a source supports a claim.
- A medical `R3` claim remains blocked until its authoritative evidence and required expert review are recorded.
- Keep Nam original. Do not add third-party mascot assets, imitate a named character, or add sacred Balinese symbols as decoration.
- For the Nam preset, preserve the approved face design: small round charcoal eyes with tiny white catchlights and no blue eye markings. Other mascots follow their project's approved anchors, not Nam's anatomy or palette.
- Illustration setup owns project art direction and character identity; visual planning consumes them. Keep hand-drawn treatment by default, including mascot-free projects, and require hash-bound setup approval before visual production.
- Preserve approved work when dependencies change. Mark downstream artifacts stale rather than deleting them.
- Keep every specialist's shared-schema links resolvable from a normal sibling-skill installation.

## Before finishing a change

Run:

```text
python scripts/validate_repository.py
python -m unittest discover -s tests -v
python skills/asknam/scripts/test_state_tools.py
python skills/asknam/scripts/validate_resources.py --require-mirrors
```

Also run the relevant skill's deterministic helper when one changed. Record new external source material in `THIRD_PARTY_NOTICES.md` only when it informed or was incorporated into the implementation.
