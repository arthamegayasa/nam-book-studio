---
name: nam-book-voice
description: "Calibrate an authorized author's reusable voice profile or diagnose voice drift in a book. Use before drafting or when voice guidance is missing; route manuscript-wide rewriting to the editing skill."
---

# Nam Book Voice

Make the manuscript sound intentionally authored through specificity, rhythm, stance, and editorial choice while preserving substance.

## Choose the operation

- **Calibrate:** derive a reusable voice profile from authorized samples.
- **Design:** create an aspirational profile from the user's stated preferences when representative samples do not exist.
- **Audit:** report drift across chapters or locales without rewriting the manuscript.

Read [references/voice-profile.md](references/voice-profile.md) when calibrating, designing, or auditing a profile.

## Rules

1. Confirm whose voice is being modeled and whether samples are user-owned, licensed, or supplied for this purpose.
2. Record observable tendencies separately from editorial choices. Do not treat accidental errors or one sample's topic as permanent voice.
3. When the requested reference is a third-party author, use high-level transferable traits instead of signature imitation or copied phrasing.
4. When auditing, cite semantic block IDs and distinguish voice drift from factual, structural, or localization problems.
5. Test proposed guidance against representative passages, but leave manuscript changes to `$nam-book-write` or `$nam-book-edit`.
6. Preserve claim/source IDs, quotations, citations, numbers, units, uncertainty, warnings, and locale-specific terminology in every example.

Optimize for authentic communication, clarity, and consistency. Detector scores are irrelevant: do not target, promise, test, or report AI-detector evasion.

## Outputs

For calibration or design, write a versioned voice profile containing provenance, confidence, audience relationship, tone boundaries, cadence, diction, technical density, rhetorical habits, humor, examples, and explicit exclusions. Validate its registry entry against [book-artifact.schema.json](../asknam/references/schemas/book-artifact.schema.json). For an audit-only request, report block-level findings and route any requested prose changes to the editing skill; revise the voice-profile artifact only when the guidance itself changes. Leave global state to AskNam.

The work is complete when the profile distinguishes observed evidence from chosen direction, its guidance permits purposeful variation, drift findings are traceable to block IDs, and no factual or evidentiary meaning has changed.
