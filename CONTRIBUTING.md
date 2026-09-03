# Contributing

Contributions should make a book workflow more reliable without turning a focused skill into a catch-all.

## Before opening a change

1. Choose the specialist that owns the behavior. Add a new skill only when it has a distinct trigger and artifact contract.
2. Keep shared fields in the schemas and catalog. Do not redefine them independently in several skills.
3. Put always-needed steps in `SKILL.md`; move branch-specific rules and large examples into a linked reference.
4. Use original prose and assets. Record copied or substantially adapted MIT material with its copyright notice and source revision.
5. Add or update a meaningful validator or behavior fixture when the change introduces a new invariant.

## Style

- Repository material is English. Manuscript examples may use another language when the locale is explicit.
- Use stable kebab-case skill names and stable artifact IDs.
- State inputs, outputs, completion criteria, and failure states.
- Prefer positive target behavior. Keep prohibitions for real safety, evidence, rights, or data-integrity boundaries.
- Do not make unsupported claims of accuracy, originality, accessibility, or publication readiness.

## Validation

Run:

```text
python scripts/validate_repository.py
python -m unittest discover -s tests -v
python skills/asknam/scripts/test_state_tools.py
python skills/asknam/scripts/validate_resources.py --require-mirrors
```

For visual changes, check the canonical character, print scale, grayscale legibility, caption, alt text, and provenance. For medical changes, include a fixture that demonstrates the correct blocking behavior for an unsupported `R3` claim.
