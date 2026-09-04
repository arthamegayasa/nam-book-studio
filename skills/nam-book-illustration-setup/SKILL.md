---
name: nam-book-illustration-setup
description: Establish a book project's hand-drawn illustration direction and mascot from its brief and reference images. Use at project start, before visual production, or when changing the art style or character identity; chapter figure planning belongs to nam-book-visuals.
---

# Nam Book Illustration Setup

Make the art belong to this book before producing its illustrations. Hand-drawn
linework stays part of this workflow; the mascot, palette, cultural cues, and mood are
project-specific. Nam is an available preset, not a compulsory character.

## Start from the brief

Read the approved project brief, manifest, audience, locale, production targets,
user references, and any existing setup or character bible. This stage can run
before research and chapter architecture are finished. Ask only about choices
that materially change identity, permissions, or audience fit; carry reversible
stylistic assumptions as proposals for review.

Read [setup-contract.md](references/setup-contract.md) for the payload fields,
calibration checks, and revision handoff. Use the two JSON templates under
`assets/` when starting fresh; they are unapproved draft payloads, not registry
entries. Keep the [artifact registry envelope](../asknam/references/schemas/book-artifact.schema.json)
separate from the payload.

## Establish the direction

1. **Inspect references.** View every available image before describing it.
   Distinguish identity to preserve from style, composition, and contextual
   inspiration. Record each source, file hash, permission basis, and the traits
   the user wants carried forward. Read [reference-and-mascot-modes.md](references/reference-and-mascot-modes.md)
   when images are supplied, a mascot must be designed, or an old bible is adopted.
2. **Choose the project identity.** Use `custom`, `supplied`, `nam`, or `none`
   according to the brief. If the choice is open, propose a direction with its
   reason; do not silently inherit Nam from the package branding. In Nam mode,
   read the [Nam preset](../nam-book-visuals/references/nam-character-bible.md)
   and inspect its canonical assets. Other modes use their own approved anchors.
3. **Set visual tokens.** Define contour, simplified shapes, texture, palette
   roles, shading, background, proportions, expression, and editable-label
   treatment. Preserve a visibly hand-drawn character through restrained line
   variation and simple forms; adapt warmth and complexity to the audience.
   Cultural details come from this project's context, not a mandatory Balinese
   overlay. A request for a non-hand-drawn style needs a revised workflow rather
   than a bypass of this setup's hand-drawn contract.
4. **Calibrate before batching.** Produce or select a representative sample:
   a mascot pose/action sheet when a character exists, or a representative scene
   or diagram when it does not. Use the available image-generation/editing skill
   for raster work and editable drawing tools for exact diagrams. Inspect the
   actual sample at intended placement size against the contract. An existing,
   rights-cleared user reference can serve as calibration if it demonstrates the
   chosen direction; a text prompt alone cannot. Before research is complete,
   calibrate neutral identity, gesture, or simple object/line examples rather
   than unresolved clinical, anatomical, or quantitative content. Content-specific
   visual review still occurs later.
5. **Prepare approval.** Return the setup, versioned character bible, and sample
   with a short account of fixed traits, flexible traits, and unresolved choices.
   AskNam registers the samples before the dependent setup/bible and requests
   the `illustration-setup` approval against both artifacts' current hashes.
   Batch illustration and diagram production wait for that approval.

## Outputs and completion

Return `illustration_setup` at `visuals/illustration-setup.json`,
`character_bible` at `visuals/character-bible.json`, and optional
`illustration_calibration` assets at their catalog paths. New JSON artifacts
reference registered calibration inputs; a byte-preserved legacy bible is
adopted as described in the contract. A mascot-free bible explicitly records
`mascot_mode: none` and `identity: null`; it is not a missing deliverable.

Ready for review means the mode and tokens are coherent, references have usable
rights, a real calibration sample has passed inspection, and every fixed or
flexible identity trait is recorded. Return `review`, not self-granted approval.
If a required image, permission, cultural review, or tool is unavailable, retain
the useful draft, return `blocked` with the missing prerequisite, and state what
the user can provide. Do not invent a generated file or claim an unseen image
matches the design.

Only AskNam mutates global state or approval records. A changed setup triggers a
visual dependency review, preserving earlier assets and approvals as history.
Once approved, hand off to `$nam-book-visuals` for chapter-level figure planning.
