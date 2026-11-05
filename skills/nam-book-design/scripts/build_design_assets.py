#!/usr/bin/env python3
"""Generate the design assets that publish consumes from a design spec.

Outputs into the assets directory:

- ``print.css``        page size, margins, side column, typography, callout styles for HTML-to-PDF
- ``epub.css``         the reflowable variant with the spec's degradation rules applied
- ``callouts.lua``     a Pandoc filter that renders ``.callout`` divs per output format,
                       with catalog labels for both locales embedded
- ``reference.docx``   Pandoc's default reference document patched with the spec's fonts,
                       sizes, and the Callout paragraph styles (requires Pandoc)
- ``icons/<type>.svg`` the icon set in use
- ``assets-manifest.json``

Edit the spec, never the generated files: the bundle is tree-hashed on registration.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any

PLACEMENTS = ("inline", "side-column", "band", "full-page", "opener")
REQUIRED_KEYS = (
    "profile", "design_version", "trim", "page", "typography", "color", "callouts",
    "icons", "render", "degradation", "figures", "tables",
)
FONT_ROLES = ("body", "headings", "captions", "labels")
COLOR_ROLES = ("ink", "paper", "accent", "muted", "rule")
DOCX_STYLES = {
    "inline": "Callout Inline",
    "side-column": "Callout Side",
    "band": "Callout Band",
    "full-page": "Callout Full Page",
    "opener": "Callout Opener",
    "page-break": "Callout Full Page",
}


def default_catalog_path() -> Path:
    return Path(__file__).resolve().parents[2] / "asknam" / "references" / "callout-catalog.json"


def default_icon_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "assets" / "icons"


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_spec(spec: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in REQUIRED_KEYS:
        if key not in spec:
            errors.append(f"design spec lacks {key}")
    if errors:
        return errors
    if spec["profile"] not in {"friendly-explainer", "textbook", "exam-prep"}:
        errors.append(f"design spec profile {spec['profile']!r} is not a book mode")
    for role in FONT_ROLES:
        font = spec["typography"].get(role)
        if not isinstance(font, dict) or not font.get("family") or not font.get("size_pt"):
            errors.append(f"typography.{role} needs family and size_pt")
    for role in COLOR_ROLES:
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", str(spec["color"].get(role, ""))):
            errors.append(f"color.{role} must be a #rrggbb value")
    for placement in PLACEMENTS:
        if placement not in spec["callouts"]:
            errors.append(f"callouts lacks a style for {placement}")
    trim = spec["trim"]
    if not trim.get("width_mm") or not trim.get("height_mm"):
        errors.append("trim needs width_mm and height_mm")
    margins = spec["page"].get("margins_mm", {})
    if any(key not in margins for key in ("top", "bottom", "inner", "outer")):
        errors.append("page.margins_mm needs top, bottom, inner, outer")
    if spec["render"].get("pdf", {}).get("engine") not in {"chromium", "libreoffice"}:
        errors.append("render.pdf.engine must be chromium or libreoffice")
    return errors


def pandoc_path() -> str | None:
    return shutil.which("pandoc")


def pandoc_version() -> str | None:
    executable = pandoc_path()
    if not executable:
        return None
    try:
        result = subprocess.run([executable, "--version"], capture_output=True, text=True, check=False, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    first = (result.stdout or "").splitlines()[:1]
    return first[0].split()[-1] if first else None


def font_stack(font: dict[str, Any]) -> str:
    families = [font["family"], *font.get("fallbacks", [])]
    return ", ".join(name if name in {"serif", "sans-serif", "monospace"} else f'"{name}"' for name in families)


def hex_no_hash(value: str) -> str:
    return value.lstrip("#").upper()


def frame_css(style: dict[str, Any], color_var: str) -> str:
    frame = style.get("frame", "none")
    if frame == "rule-left":
        return f"border-left: 2.5px solid {color_var}; padding-left: 0.9em;"
    if frame == "rule-top":
        return f"border-top: 2px solid {color_var}; padding-top: 0.6em;"
    if frame == "box":
        return "border: 1.5px solid var(--rule); padding: 0.9em 1.1em;"
    if frame == "hand-drawn":
        return (
            f"border: 2px solid {color_var}; padding: 0.9em 1.1em; "
            "border-radius: 255px 15px 225px 15px / 15px 225px 15px 255px;"
        )
    return ""


def background_css(style: dict[str, Any]) -> str:
    background = style.get("background", "none")
    if background == "tint":
        return "background: var(--tint);"
    if background == "paper":
        return "background: var(--paper);"
    return ""


def common_css(spec: dict[str, Any], catalog: dict[str, Any]) -> str:
    typography = spec["typography"]
    color = spec["color"]
    body, headings, captions, labels = (typography[role] for role in FONT_ROLES)
    accents = color.get("callout_accent", {})
    tables = spec["tables"]
    figures = spec["figures"]
    lines = [
        "/* Generated from design-spec.json by build_design_assets.py. Edit the spec, not this file. */",
        ":root {",
        f"  --ink: {color['ink']};",
        f"  --paper: {color['paper']};",
        f"  --accent: {color['accent']};",
        f"  --muted: {color['muted']};",
        f"  --rule: {color['rule']};",
        f"  --tint: {color.get('tint', '#f5f5f4')};",
        f"  --side-column: {spec['page'].get('side_column_mm', 0)}mm;",
        f"  --column-gap: {spec['page'].get('column_gap_mm', 5)}mm;",
    ]
    lines.extend(f"  --callout-accent-{type_id}: {value};" for type_id, value in sorted(accents.items()))
    lines.append("}")
    lines.extend([
        "html {",
        f"  font-family: {font_stack(body)};",
        f"  font-size: {body['size_pt']}pt;",
        f"  line-height: {round(body['leading_pt'] / body['size_pt'], 3)};",
        f"  font-weight: {body.get('weight', 400)};",
        "  color: var(--ink);",
        "  background: var(--paper);",
        "}",
        "h1, h2, h3, h4, h5, h6 {",
        f"  font-family: {font_stack(headings)};",
        f"  font-weight: {headings.get('weight', 700)};",
        "  color: var(--ink);",
        "  break-after: avoid;",
        "  margin: 1.4em 0 0.5em;",
        "}",
        f"h1 {{ font-size: {headings['size_pt']}pt; line-height: {round(headings['leading_pt'] / headings['size_pt'], 3)}; margin-top: 0; }}",
        f"h2 {{ font-size: {round(headings['size_pt'] * 0.78, 2)}pt; }}",
        f"h3 {{ font-size: {round(headings['size_pt'] * 0.62, 2)}pt; }}",
        "p { margin: 0 0 0.65em; orphans: 2; widows: 2; }",
        "ul, ol { margin: 0 0 0.8em 1.2em; padding: 0; }",
        "figure { margin: 1.2em 0; break-inside: avoid; }",
        f"figure img {{ max-width: 100%; height: auto; {'border: 0.5px solid var(--rule);' if figures.get('frame') == 'hairline' else ''} }}",
        "figcaption, caption {",
        f"  font-family: {font_stack(captions)};",
        f"  font-size: {captions['size_pt']}pt;",
        f"  line-height: {round(captions['leading_pt'] / captions['size_pt'], 3)};",
        f"  font-style: {captions.get('style', 'normal')};",
        "  color: var(--muted);",
        "  text-align: left;",
        "  margin: 0.4em 0 0;",
        "}",
        f"caption {{ caption-side: {'top' if tables.get('caption_position', 'above') == 'above' else 'bottom'}; margin: 0 0 0.4em; }}",
        f"table {{ border-collapse: collapse; width: 100%; font-size: {tables.get('font_scale', 0.9)}em; break-inside: avoid; margin: 1em 0; }}",
        f"th {{ text-align: left; vertical-align: bottom; padding: 0.3em 0.5em; {'border-bottom: 1.5px solid var(--ink);' if tables.get('header_rule', True) else ''} }}",
        "td { vertical-align: top; padding: 0.3em 0.5em; border-bottom: 0.5px solid var(--rule); }",
    ])
    if tables.get("zebra"):
        lines.append("tbody tr:nth-child(even) { background: var(--tint); }")
    lines.extend([
        ".callout { break-inside: avoid; margin: 1em 0; --callout-color: var(--accent); }",
        ".callout-label {",
        "  display: flex; align-items: center; gap: 0.45em;",
        f"  font-family: {font_stack(labels)};",
        f"  font-size: {labels['size_pt']}pt;",
        f"  font-weight: {labels.get('weight', 700)};",
        "  letter-spacing: 0.06em; text-transform: uppercase;",
        "  color: var(--callout-color); margin: 0 0 0.35em;",
        "}",
        ".callout-label p { margin: 0; display: flex; align-items: center; gap: 0.45em; }",
        f".callout-title {{ font-family: {font_stack(headings)}; font-weight: 600; margin: 0 0 0.3em; }}",
        ".callout-title p { margin: 0; }",
        ".callout > p:last-child, .callout > div:last-child > p:last-child { margin-bottom: 0; }",
    ])
    for type_id in sorted(accents):
        lines.append(f".callout-{type_id} {{ --callout-color: var(--callout-accent-{type_id}); }}")
    return "\n".join(lines) + "\n"


def placement_css(spec: dict[str, Any], placement: str, *, reflowable: bool) -> str:
    style = spec["callouts"][placement]
    icon = style.get("icon_size_mm", 7)
    scale = style.get("font_scale", 1.0)
    rules = [f"font-size: {scale}em;", frame_css(style, "var(--callout-color)"), background_css(style)]
    if placement == "side-column" and not reflowable and spec["page"].get("side_column_mm", 0) > 0:
        rules.append(
            "float: right; clear: right; width: var(--side-column); "
            "margin: 0 calc(-1 * (var(--side-column) + var(--column-gap))) 0.8em 0;"
        )
    elif placement == "side-column":
        rules.append("padding: 0.6em 0.8em;")
    if placement == "band" and not style.get("frame", "none") in {"box", "hand-drawn", "rule-left"}:
        rules.append("padding: 0.8em 1em;")
    if placement == "full-page" and not reflowable:
        rules.append("break-before: page; break-after: page;")
    if placement == "opener":
        rules.append("margin: 0 0 1.6em; padding-bottom: 0.8em; border-bottom: 1px solid var(--rule);")
    body = " ".join(rule for rule in rules if rule)
    icon_rule = f".placement-{placement} .callout-icon {{ width: {icon}mm; height: {icon}mm; flex: none; }}"
    return f".placement-{placement} {{ {body} }}\n{icon_rule}\n"


def build_print_css(spec: dict[str, Any], catalog: dict[str, Any]) -> str:
    trim = spec["trim"]
    margins = spec["page"]["margins_mm"]
    side = spec["page"].get("side_column_mm", 0)
    gap = spec["page"].get("column_gap_mm", 5)
    parts = [
        common_css(spec, catalog),
        f"@page {{ size: {trim['width_mm']}mm {trim['height_mm']}mm; margin: {margins['top']}mm {margins['outer']}mm {margins['bottom']}mm {margins['inner']}mm; }}",
        f"@page :left {{ margin-left: {margins['outer']}mm; margin-right: {margins['inner']}mm; }}",
        f"@page :right {{ margin-left: {margins['inner']}mm; margin-right: {margins['outer']}mm; }}",
        f"body {{ margin: 0; {'padding-right: calc(var(--side-column) + var(--column-gap));' if side > 0 else ''} }}",
        ".callout-icon { width: 7mm; height: 7mm; }",
        ".placement-page-break { break-before: page; }",
        "h1 { break-before: page; }",
        "h1:first-of-type { break-before: auto; }",
    ]
    parts.extend(placement_css(spec, placement, reflowable=False) for placement in PLACEMENTS)
    del gap
    return "\n".join(parts) + "\n"


def build_epub_css(spec: dict[str, Any], catalog: dict[str, Any]) -> str:
    parts = [
        common_css(spec, catalog),
        "body { margin: 0 4%; }",
        "img { max-width: 100%; height: auto; }",
        ".callout-icon { width: 1.4em; height: 1.4em; vertical-align: middle; }",
        ".placement-page-break { break-before: page; page-break-before: always; }",
    ]
    parts.extend(placement_css(spec, placement, reflowable=True) for placement in PLACEMENTS)
    return "\n".join(parts) + "\n"


def lua_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def lua_table(mapping: dict[str, Any], indent: str = "  ") -> str:
    lines = ["{"]
    for key in sorted(mapping):
        value = mapping[key]
        rendered = lua_table(value, indent + "  ") if isinstance(value, dict) else lua_string(str(value))
        lines.append(f"{indent}[{lua_string(key)}] = {rendered},")
    lines.append(indent[:-2] + "}")
    return "\n".join(lines)


def build_lua_filter(spec: dict[str, Any], catalog: dict[str, Any]) -> str:
    labels = {item["type_id"]: dict(item["labels"]) for item in catalog["types"]}
    defaults = {item["type_id"]: item["default_placement"] for item in catalog["types"]}
    degradation = {key: dict(value) for key, value in spec["degradation"].items()}
    html_rules = dict(degradation.get("html", {}))
    if spec["page"].get("side_column_mm", 0) <= 0:
        html_rules.setdefault("side-column", "band")
    degradation["html"] = html_rules
    icon_dir = spec["icons"].get("directory", "icons")
    return f"""-- Generated from design-spec.json by build_design_assets.py. Edit the spec, not this file.
-- Renders `.callout` fenced divs per output format with catalog labels for every locale.

local labels = {lua_table(labels)}

local defaults = {lua_table(defaults)}

local degradation = {lua_table(degradation)}

local docx_styles = {lua_table(DOCX_STYLES)}

local icon_dir = {lua_string(icon_dir)}
local locale = "en-US"

local function target_format()
  if FORMAT:match("epub") then return "epub" end
  if FORMAT:match("docx") then return "docx" end
  if FORMAT:match("html") then return "html" end
  return FORMAT
end

local function degrade(placement)
  local map = degradation[target_format()] or {{}}
  return map[placement] or placement
end

local function label_for(type_id)
  local entry = labels[type_id]
  if entry then return entry[locale] or entry["en-US"] or type_id end
  return type_id
end

local function read_locale(meta)
  if meta.lang then locale = pandoc.utils.stringify(meta.lang) end
  -- The HTML-to-PDF path renders body matter: chapters open with their own H1,
  -- so the document title only feeds <title>, never a duplicate heading.
  if target_format() == "html" and meta.title then
    meta.pagetitle = meta.title
    meta.title = nil
  end
  return meta
end

local function render_callout(el)
  if not el.classes:includes("callout") then return nil end
  local type_id = el.attributes["type"] or "note"
  local placement = degrade(el.attributes["placement"] or defaults[type_id] or "band")
  local title = el.attributes["title"]
  local label = label_for(type_id)
  if target_format() == "docx" then
    local blocks = pandoc.List()
    if placement == "page-break" then
      blocks:insert(pandoc.RawBlock("openxml", '<w:p><w:r><w:br w:type="page"/></w:r></w:p>'))
    end
    blocks:insert(pandoc.Div({{ pandoc.Para({{ pandoc.Str(label) }}) }}, pandoc.Attr("", {{}}, {{{{"custom-style", "Callout Label"}}}})))
    if title then
      blocks:insert(pandoc.Div({{ pandoc.Para({{ pandoc.Str(title) }}) }}, pandoc.Attr("", {{}}, {{{{"custom-style", "Callout Title"}}}})))
    end
    local style = docx_styles[placement] or "Callout Band"
    blocks:insert(pandoc.Div(el.content, pandoc.Attr("", {{}}, {{{{"custom-style", style}}}})))
    return blocks
  end
  local icon = pandoc.Image({{}}, icon_dir .. "/" .. type_id .. ".svg", "", pandoc.Attr("", {{"callout-icon"}}, {{{{"role", "presentation"}}}}))
  local label_block = pandoc.Div(
    {{ pandoc.Para({{ icon, pandoc.Space(), pandoc.Span({{ pandoc.Str(label) }}, pandoc.Attr("", {{"callout-label-text"}})) }}) }},
    pandoc.Attr("", {{"callout-label"}})
  )
  local content = pandoc.List()
  content:insert(label_block)
  if title then
    content:insert(pandoc.Div({{ pandoc.Para({{ pandoc.Str(title) }}) }}, pandoc.Attr("", {{"callout-title"}})))
  end
  content:extend(el.content)
  local attributes = {{ {{"data-type", type_id}}, {{"data-placement", placement}} }}
  if el.attributes["objective"] then table.insert(attributes, {{"data-objective", el.attributes["objective"]}}) end
  if el.attributes["reveal"] then table.insert(attributes, {{"data-reveal", el.attributes["reveal"]}}) end
  if el.attributes["item"] then table.insert(attributes, {{"data-item", el.attributes["item"]}}) end
  if el.attributes["for"] then table.insert(attributes, {{"data-for", el.attributes["for"]}}) end
  local classes = {{"callout", "callout-" .. type_id, "placement-" .. placement}}
  return pandoc.Div(content, pandoc.Attr(el.identifier, classes, attributes))
end

return {{ {{ Meta = read_locale }}, {{ Div = render_callout }} }}
"""


def patch_styles_xml(styles: str, spec: dict[str, Any]) -> str:
    typography = spec["typography"]
    color = spec["color"]
    body = typography["body"]
    headings = typography["headings"]
    labels = typography["labels"]
    accents = color.get("callout_accent", {})

    def fonts(font: dict[str, Any]) -> str:
        family = font["family"]
        return f'<w:rFonts w:ascii="{family}" w:hAnsi="{family}" w:cs="{family}" w:eastAsia="{family}"/>'

    def half_points(value: float) -> int:
        return int(round(value * 2))

    def replace_defaults(match: re.Match[str]) -> str:
        block = match.group(0)
        block = re.sub(r"<w:rFonts[^>]*/>", fonts(body), block, count=1)
        block = re.sub(r'<w:sz w:val="\d+"\s*/>', f'<w:sz w:val="{half_points(body["size_pt"])}"/>', block, count=1)
        block = re.sub(r'<w:szCs w:val="\d+"\s*/>', f'<w:szCs w:val="{half_points(body["size_pt"])}"/>', block, count=1)
        return block

    styles = re.sub(r"<w:rPrDefault>.*?</w:rPrDefault>", replace_defaults, styles, count=1, flags=re.S)

    for level, scale in (("Heading1", 1.0), ("Heading2", 0.78), ("Heading3", 0.62)):
        pattern = re.compile(rf'<w:style w:type="paragraph" w:styleId="{level}">.*?</w:style>', re.S)

        def replace_heading(match: re.Match[str], scale: float = scale) -> str:
            block = match.group(0)
            size = half_points(headings["size_pt"] * scale)
            if "<w:rFonts" in block:
                block = re.sub(r"<w:rFonts[^>]*/>", fonts(headings), block, count=1)
            else:
                block = block.replace("<w:rPr>", "<w:rPr>" + fonts(headings), 1)
            block = re.sub(r'<w:sz w:val="\d+"\s*/>', f'<w:sz w:val="{size}"/>', block, count=1)
            block = re.sub(r'<w:szCs w:val="\d+"\s*/>', f'<w:szCs w:val="{size}"/>', block, count=1)
            block = re.sub(r"<w:color [^>]*/>", f'<w:color w:val="{hex_no_hash(color["ink"])}"/>', block, count=1)
            return block

        styles = pattern.sub(replace_heading, styles, count=1)

    accent = hex_no_hash(color["accent"])
    tint = hex_no_hash(color.get("tint", "#F5F5F4"))
    rule = hex_no_hash(color["rule"])
    warning = hex_no_hash(accents.get("warning", color["accent"]))
    label_size = half_points(labels["size_pt"])
    side_size = half_points(body["size_pt"] * spec["callouts"]["side-column"].get("font_scale", 0.86))
    band_size = half_points(body["size_pt"] * spec["callouts"]["band"].get("font_scale", 0.95))

    def paragraph_style(style_id: str, name: str, ppr: str, rpr: str, based_on: str = "Normal") -> str:
        return (
            f'<w:style w:type="paragraph" w:customStyle="1" w:styleId="{style_id}">'
            f'<w:name w:val="{name}"/><w:basedOn w:val="{based_on}"/><w:qFormat/>'
            f"<w:pPr>{ppr}</w:pPr><w:rPr>{rpr}</w:rPr></w:style>"
        )

    border_left = f'<w:pBdr><w:left w:val="single" w:sz="12" w:space="8" w:color="{accent}"/></w:pBdr>'
    border_top = f'<w:pBdr><w:top w:val="single" w:sz="8" w:space="4" w:color="{accent}"/></w:pBdr>'
    border_box = (
        f'<w:pBdr><w:top w:val="single" w:sz="6" w:space="6" w:color="{rule}"/>'
        f'<w:left w:val="single" w:sz="6" w:space="6" w:color="{rule}"/>'
        f'<w:bottom w:val="single" w:sz="6" w:space="6" w:color="{rule}"/>'
        f'<w:right w:val="single" w:sz="6" w:space="6" w:color="{rule}"/></w:pBdr>'
    )
    shading = f'<w:shd w:val="clear" w:color="auto" w:fill="{tint}"/>'
    new_styles = [
        paragraph_style(
            "CalloutLabel", "Callout Label",
            '<w:keepNext/><w:spacing w:before="200" w:after="40"/>',
            f'{fonts(labels)}<w:b/><w:caps/><w:color w:val="{accent}"/><w:sz w:val="{label_size}"/><w:szCs w:val="{label_size}"/>',
        ),
        paragraph_style(
            "CalloutTitle", "Callout Title",
            '<w:keepNext/><w:spacing w:before="0" w:after="60"/>',
            f'{fonts(headings)}<w:b/><w:sz w:val="{half_points(body["size_pt"] * 1.05)}"/>',
        ),
        paragraph_style(
            "CalloutBand", "Callout Band",
            f'{border_left}{shading}<w:ind w:left="284" w:right="284"/><w:spacing w:before="60" w:after="120"/>',
            f'<w:sz w:val="{band_size}"/><w:szCs w:val="{band_size}"/>',
        ),
        paragraph_style(
            "CalloutSide", "Callout Side",
            f'{border_left}<w:ind w:left="567"/><w:spacing w:before="40" w:after="100"/>',
            f'<w:sz w:val="{side_size}"/><w:szCs w:val="{side_size}"/>',
        ),
        paragraph_style(
            "CalloutInline", "Callout Inline",
            f'{border_left}<w:ind w:left="284"/><w:spacing w:before="40" w:after="100"/>',
            "",
        ),
        paragraph_style(
            "CalloutFullPage", "Callout Full Page",
            f'{border_box}<w:ind w:left="284" w:right="284"/><w:spacing w:before="120" w:after="120"/>',
            f'<w:sz w:val="{band_size}"/><w:szCs w:val="{band_size}"/>',
        ),
        paragraph_style(
            "CalloutOpener", "Callout Opener",
            f'{border_top}<w:spacing w:before="120" w:after="240"/>',
            f'<w:sz w:val="{half_points(body["size_pt"] * spec["callouts"]["opener"].get("font_scale", 1.1))}"/>',
        ),
        paragraph_style(
            "CalloutWarning", "Callout Warning",
            f'<w:pBdr><w:left w:val="single" w:sz="12" w:space="8" w:color="{warning}"/></w:pBdr>{shading}<w:ind w:left="284" w:right="284"/>',
            "",
        ),
    ]
    return styles.replace("</w:styles>", "".join(new_styles) + "</w:styles>", 1)


def build_reference_docx(spec: dict[str, Any], destination: Path) -> list[str]:
    """Derive reference.docx from Pandoc's default data file; return limitations."""
    executable = pandoc_path()
    if not executable:
        return ["reference.docx skipped: pandoc is not installed"]
    try:
        result = subprocess.run(
            [executable, "--print-default-data-file", "reference.docx"],
            capture_output=True, check=False, timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return [f"reference.docx skipped: pandoc failed ({exc})"]
    if result.returncode != 0 or not result.stdout:
        return ["reference.docx skipped: pandoc returned no default reference document"]
    source = zipfile.ZipFile(__import__("io").BytesIO(result.stdout))
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as target:
        for info in source.infolist():
            payload = source.read(info.filename)
            if info.filename == "word/styles.xml":
                payload = patch_styles_xml(payload.decode("utf-8"), spec).encode("utf-8")
            target.writestr(info, payload)
    return []


def copy_icons(spec: dict[str, Any], catalog: dict[str, Any], source_dir: Path, out_dir: Path) -> tuple[list[str], list[str]]:
    icon_dir = out_dir / spec["icons"].get("directory", "icons")
    icon_dir.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    limitations: list[str] = []
    for entry in catalog["types"]:
        type_id = entry["type_id"]
        source = source_dir / f"{type_id}.svg"
        if source.is_file():
            shutil.copyfile(source, icon_dir / f"{type_id}.svg")
            copied.append(f"{spec['icons'].get('directory', 'icons')}/{type_id}.svg")
        elif spec["profile"] in entry["modes"]:
            limitations.append(f"no icon for callout type {type_id}; the label renders without one")
    return copied, limitations


def build_assets(
    spec_path: Path, out_dir: Path, *, catalog_path: Path | None = None, icons_dir: Path | None = None,
) -> dict[str, Any]:
    spec = load_json(spec_path)
    errors = validate_spec(spec)
    if errors:
        raise ValueError("; ".join(errors))
    catalog = load_json(catalog_path or default_catalog_path())
    out_dir.mkdir(parents=True, exist_ok=True)
    generated: list[str] = []
    limitations: list[str] = []

    (out_dir / "print.css").write_text(build_print_css(spec, catalog), encoding="utf-8", newline="\n")
    generated.append("print.css")
    (out_dir / "epub.css").write_text(build_epub_css(spec, catalog), encoding="utf-8", newline="\n")
    generated.append("epub.css")
    (out_dir / "callouts.lua").write_text(build_lua_filter(spec, catalog), encoding="utf-8", newline="\n")
    generated.append("callouts.lua")
    docx_limitations = build_reference_docx(spec, out_dir / "reference.docx")
    if not docx_limitations:
        generated.append("reference.docx")
    limitations.extend(docx_limitations)
    icons, icon_limitations = copy_icons(spec, catalog, icons_dir or default_icon_dir(), out_dir)
    generated.extend(icons)
    limitations.extend(icon_limitations)
    limitations.append("docx: callout icons are not embedded; labels carry the meaning")

    manifest = {
        "generator": "build_design_assets.py",
        "spec_path": str(spec_path),
        "spec_sha256": sha256_file(spec_path),
        "profile": spec["profile"],
        "design_version": spec["design_version"],
        "catalog_version": catalog.get("catalog_version"),
        "tools": {"pandoc": pandoc_version()},
        "generated": generated,
        "limitations": limitations,
    }
    (out_dir / "assets-manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n",
    )
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--spec", type=Path, required=True, help="design-spec.json")
    parser.add_argument("--out", type=Path, required=True, help="assets directory to (re)generate")
    parser.add_argument("--catalog", type=Path, default=None, help="callout catalog (default: sibling AskNam)")
    parser.add_argument("--icons", type=Path, default=None, help="icon source directory (default: bundled set)")
    args = parser.parse_args(argv)
    try:
        manifest = build_assets(args.spec, args.out, catalog_path=args.catalog, icons_dir=args.icons)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "fail", "errors": [str(exc)]}, indent=2))
        return 1
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
