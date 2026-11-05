# Callout contract

A **callout** is a typed, labeled, set-off element of a chapter: Tip, Warning, Myth vs Fact, a reflection prompt, a quick check, and so on. Every callout has a stable `callout_id`, exactly one callout type from the shared catalog, one linked objective, and a placement hint. This contract defines the one Markdown form that `nam-book-write`, `nam-book-teach`, `nam-book-edit`, `nam-book-localize`, `nam-book-design`, and `nam-book-publish` all read. The type list itself lives in the [callout catalog](../../asknam/references/callout-catalog.json), validated by its [schema](../../asknam/references/schemas/callout-catalog.schema.json).

Vocabulary: a callout is not a *semantic block* (the prose unit that editing and localization align on) and not a *figure reference* (the in-text pointer to a figure or table). Avoid "box", "typed block", "teaching block", "admonition", and "aside" in skill prose and reports.

## Syntax

A callout is a Pandoc fenced div carrying the `.callout` class:

```markdown
::: {#callout-ch03-02 .callout type=warning placement=band objective=obj-ch03-01}
Oven doors vent steam at face height. Open them from the side.
:::
```

| Attribute | Required | Meaning |
| --- | --- | --- |
| `#callout-chNN-NN` | yes | Stable callout ID, type-neutral, assigned at creation, never reused. |
| `.callout` | yes | Marks the div as a callout. No other class is expected. |
| `type` | yes | A `type_id` from the catalog that the active book mode allows. |
| `objective` | yes, except `answer-key` | Exactly one `objective_id` from the approved architecture. |
| `placement` | no | A placement hint from the catalog's allowed list for the type; the catalog default applies when omitted. |
| `title` | no | A supplementary heading inside the callout. It never replaces the catalog label. |
| `reveal` | types with reveal rules | Where the answer or discussion appears: `none`, `inline`, `chapter-end`, or `book-end`. |
| `item` | `quick-check` only | The `item_id` whose key and rationale live in the assessment bank. |
| `for` | `answer-key` only | `ch-NN` for a chapter's keys or `book` for the book-end collection. |

Rules:

- The body is ordinary Markdown in the manuscript locale: paragraphs, lists, one small table. A callout cannot contain another fenced div.
- The displayed label comes from the catalog for the active locale (`Warning` / `Peringatan`). Do not write the label into the body; use `title` for an additional heading.
- The icon slot is the `type_id`; the design spec resolves it to an asset.
- Attribute values with spaces must be quoted (`title="Why ATP matters"`).

## Identity

- Pattern: `callout-ch<chapter number>-<sequence>`, for example `callout-ch03-02`, parallel to `fig-ch03-04` and `item-ch03-012`.
- The ID encodes the chapter, not the type. Changing a Warning into a Remember keeps its ID.
- IDs are sequential per chapter at creation. A removed callout's number is never reused; a new callout takes the next number.
- A chapter manuscript carries only its own chapter's callout IDs; a whole-book manuscript carries every chapter's.

## Catalog

Each type records `type_id`, labels for `en-US` and `id-ID`, the modes that allow it, `default_placement` and `allowed_placements`, its reveal rules when it has any, and a one-line purpose. `requires_item` marks `quick-check`; `requires_for` marks `answer-key`. The catalog is additive: a new type is a minor `catalog_version` change, a `type_id` is never renamed, and a retired type keeps its entry with `deprecated: true` so earlier manuscripts still validate (with a warning).

Types that are **not** callouts because they are chapter sections: recap, summary, synthesis, rapid review, practice set, references, self-assessment. Comparisons are tables and belong to the visual plan; mechanisms are prose or diagrams.

## Placement

Placement is a shared vocabulary with planned visuals and the design spec: `inline`, `side-column`, `band`, `full-page`, `opener`, and (for visuals only) `spread`. A callout may use the first five, restricted per type by the catalog.

Placement is a hint about where the body sits on a fixed page. Reflowable formats degrade it: `side-column` and `band` become `inline`, `full-page` becomes a page break. Publish may override a hint because of page geometry. The design spec owns the visual treatment of each placement; this contract only names it.

## Reflection prompts and quick checks

- `reflect` asks an open, unscored question tied to an objective. It has no key and no `item`. `reveal=none` is the default; `reveal=chapter-end` means a *discussion*, not an answer, appears in that chapter's `answer-key`.
- `quick-check` places a retrieval prompt. The stem is written in the body; the key and rationales stay in `items.{locale}.yaml`, linked by `item=`. `reveal` defaults per mode (`friendly-explainer`: `inline`; `textbook` and `exam-prep`: `chapter-end`) and must be one of `inline`, `chapter-end`, `book-end`.
- `answer-key` collects the keys that `chapter-end` or `book-end` point to. Every chapter with a `chapter-end` quick check needs an `answer-key` with `for=` that chapter; a book with a `book-end` quick check needs `for=book` in the book manuscript. The integration edit places the keys; this contract defines the slot.

## Who writes callouts

- `nam-book-write` may author content-bearing callouts in the draft (a safety `warning`, a `definition`) with this syntax.
- `nam-book-teach` adds pedagogical callouts in the enriched draft, owns the catalog, and keeps the density readable.
- `nam-book-edit` may retype, move, or remove a callout. It never renumbers and never reuses an ID.
- `nam-book-localize` translates bodies and `title`; labels come from the catalog per locale; IDs, types, and attributes stay unchanged.
- `nam-book-publish` styles callouts through the approved design spec. It does not invent types.

## Density

The project's `features.visual_density` is also the callout ceiling. The catalog records the minimum average prose words per callout for each level (`high` 250, `medium` 400, `low` 700). Falling below it, two callouts with no prose between them, and more than one `opener` callout per chapter are warnings for editorial judgment, not errors.

## Inspection and registration

Run the deterministic helper before handing a manuscript to AskNam:

```bash
python skills/nam-book-teach/scripts/inspect_callouts.py \
  --manuscript .nam-book/artifacts/chapters/ch-03/enriched.id-ID.md \
  --mode friendly-explainer --locale id-ID --chapter-id ch-03 --density high \
  --architecture .nam-book/artifacts/architecture/book-architecture.json
```

Errors (unknown or disallowed type, bad or duplicate ID, disallowed placement, missing objective, missing `item` or `reveal`, missing `answer-key` target, nesting, empty body) make the manuscript unfit for registration. Add `--print-ids` to list the callout IDs for AskNam's `register-artifact --callout-id` flags. `chapter_draft`, `enriched_draft`, `edited_manuscript`, and `localized_manuscript` entries carry `callout_ids`; AskNam warns when a localized edition omits an ID present in its source.
