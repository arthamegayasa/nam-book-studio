# Domain docs

How the engineering skills should consume this repo's domain documentation when exploring the codebase. This repo is single-context: one glossary and one ADR directory at the root.

## Before exploring, read these

- **`CONTEXT.md`** at the repo root. It is this repo's glossary: the canonical vocabulary for modes, manuscript elements, page design, and layout. Wherever a skill says `GLOSSARY.md`, read `CONTEXT.md`.
- **`docs/adr/`**: read the ADRs that touch the area you are about to work in (`0001` callout contract, `0002` design specialist and render path, and later entries).
- **`AGENTS.md`**: the sources of truth and invariants; it names which file owns each contract.

If a file is missing, proceed silently. `/domain-modeling` (reached through `/grill-with-docs` and `/improve-codebase-architecture`) creates terms and ADRs lazily when they are actually resolved.

## File structure

```text
/
├── CONTEXT.md            <- glossary (shared language)
├── AGENTS.md             <- sources of truth, invariants, pre-finish gate
├── docs/adr/
│   ├── 0001-callout-contract-identity-and-syntax.md
│   └── 0002-design-specialist-and-render-path.md
├── docs/agents/          <- this folder: tracker, labels, domain layout
└── skills/               <- one directory per skill; contracts live in references/
```

## Use the glossary's vocabulary

When your output names a domain concept (in an issue title, a test name, a schema field, a refactor proposal), use the term as defined in `CONTEXT.md` and avoid the synonyms it lists under _Avoid_. Identifiers in code and schemas follow the same words (`callout`, `placement`, `design_spec`, `reveal`).

If the concept you need is not in the glossary yet, that is a signal: either you are inventing language the project does not use (reconsider) or there is a real gap (note it for `/domain-modeling`).

## Flag ADR conflicts

If your output contradicts an existing ADR, surface it explicitly rather than silently overriding:

> _Contradicts ADR-0002 (Pandoc as the single semantic converter), but worth reopening because..._
