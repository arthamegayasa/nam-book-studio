# High-stakes drafting

Apply this reference when a project is medical or otherwise capable of affecting health, safety, legal rights, or significant financial decisions. Use the project's risk vocabulary and evidence policy when they differ from the labels below.

## Claim handling

- Apply the project levels explicitly: R2 and R3 claims require `evidence_status: verified` in the evidence ledger. R3 content also requires the project's `medical-expert-signoff` before it can leave review.
- Treat diagnostic criteria, treatment choices, dosing, contraindications, interactions, emergency actions, prognosis, and patient-management recommendations as high-risk claims.
- Draft high-risk material only from approved evidence records. Preserve the `claim_id`, `source_id`, exact scope, population, jurisdiction, evidence date, uncertainty, and exceptions.
- Keep disputed evidence visibly disputed. A fluent synthesis must not erase disagreement or low certainty.
- Do not infer a recommendation from mechanistic plausibility alone.
- Put an unsupported proposition in the draft's machine-readable blocker metadata and the stage result; do not create a placeholder citation that resembles a real source.
- Educational disclaimers may clarify scope but never lower the evidence requirement.

## Cases and people

Use synthetic or explicitly authorized, de-identified cases. Change enough interacting details to prevent reconstruction when using composites, while keeping the teaching point valid. Avoid demographic details that do not contribute to the reasoning task. Represent variation without encoding a stereotype as a diagnostic shortcut.

## Reader action

Keep educational explanation distinct from individualized advice. Make emergency or referral language match the approved evidence and jurisdiction. Preserve warning prominence during simplification and state who the recommendation applies to and when it does not apply.

## Handoff

Record every high-risk claim used, omitted, narrowed, or left unresolved. Content requiring named expert review cannot progress to release-ready status until that review is recorded by the project owner.
