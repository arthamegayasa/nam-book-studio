#!/usr/bin/env python3
"""Inspect PNG structure and calculate effective PPI without dependencies.

This is a structural preflight. It does not assess composition, actual visual
transparency, color accuracy, accessibility, cultural treatment, or rights.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
import zlib
from pathlib import Path


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
COLOR_TYPES = {
    0: "grayscale",
    2: "rgb",
    3: "indexed",
    4: "grayscale-alpha",
    6: "rgba",
}


def positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be greater than zero")
    return parsed


def inspect_png(path: Path) -> dict[str, object]:
    errors: list[str] = []
    warnings: list[str] = []
    chunks: list[str] = []
    result: dict[str, object] = {
        "file": str(path),
        "scope": "PNG structure, metadata, checksum, and effective-PPI arithmetic only",
        "errors": errors,
        "warnings": warnings,
    }

    try:
        payload = path.read_bytes()
    except OSError as exc:
        errors.append(f"cannot read file: {exc}")
        result["status"] = "fail"
        return result

    result["bytes"] = len(payload)
    result["sha256"] = hashlib.sha256(payload).hexdigest()
    if not payload.startswith(PNG_SIGNATURE):
        errors.append("invalid PNG signature")
        result["status"] = "fail"
        return result

    offset = len(PNG_SIGNATURE)
    ihdr: tuple[int, int, int, int, int, int, int] | None = None
    physical_ppi: tuple[float, float] | None = None
    has_trns = False
    saw_iend = False

    while offset < len(payload):
        if len(payload) - offset < 12:
            errors.append("truncated chunk header")
            break
        length = struct.unpack(">I", payload[offset : offset + 4])[0]
        chunk_type = payload[offset + 4 : offset + 8]
        data_start = offset + 8
        data_end = data_start + length
        crc_end = data_end + 4
        if crc_end > len(payload):
            errors.append("chunk extends beyond end of file")
            break
        chunk_data = payload[data_start:data_end]
        stored_crc = struct.unpack(">I", payload[data_end:crc_end])[0]
        actual_crc = zlib.crc32(chunk_type)
        actual_crc = zlib.crc32(chunk_data, actual_crc) & 0xFFFFFFFF
        name = chunk_type.decode("latin-1")
        chunks.append(name)
        if stored_crc != actual_crc:
            errors.append(f"CRC mismatch in {name} chunk")

        if name == "IHDR":
            if ihdr is not None:
                errors.append("multiple IHDR chunks")
            elif length != 13:
                errors.append("IHDR chunk must be 13 bytes")
            else:
                ihdr = struct.unpack(">IIBBBBB", chunk_data)
        elif name == "pHYs" and length == 9:
            x_ppm, y_ppm, unit = struct.unpack(">IIB", chunk_data)
            if unit == 1:
                physical_ppi = (x_ppm * 0.0254, y_ppm * 0.0254)
        elif name == "tRNS":
            has_trns = True
        elif name == "IEND":
            saw_iend = True
            offset = crc_end
            break
        offset = crc_end

    if not chunks or chunks[0] != "IHDR":
        errors.append("IHDR is missing or is not the first chunk")
    if "IDAT" not in chunks:
        errors.append("IDAT image data is missing")
    if not saw_iend:
        errors.append("IEND chunk is missing")
    elif offset < len(payload):
        warnings.append(f"{len(payload) - offset} trailing bytes follow IEND")

    if ihdr:
        width, height, bit_depth, color_type, compression, filtering, interlace = ihdr
        result.update(
            {
                "width_px": width,
                "height_px": height,
                "bit_depth": bit_depth,
                "color_type": color_type,
                "color_mode": COLOR_TYPES.get(color_type, "unknown"),
                "alpha_channel_or_trns": color_type in (4, 6) or has_trns,
                "interlaced": interlace == 1,
            }
        )
        if width == 0 or height == 0:
            errors.append("image dimensions must be positive")
        if color_type not in COLOR_TYPES:
            errors.append(f"unsupported or reserved PNG color type {color_type}")
        if compression != 0 or filtering != 0 or interlace not in (0, 1):
            errors.append("invalid PNG compression, filter, or interlace method")

    if physical_ppi:
        result["declared_ppi"] = {
            "x": round(physical_ppi[0], 2),
            "y": round(physical_ppi[1], 2),
        }
    else:
        result["declared_ppi"] = None
        warnings.append("no physical pixel density is declared in a pHYs chunk")

    if not any(name in chunks for name in ("iCCP", "sRGB")):
        warnings.append("no embedded ICC profile or sRGB declaration was found")

    result["chunks"] = chunks
    result["status"] = "fail" if errors else "pass"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect a PNG and optionally check effective PPI at placed size."
    )
    parser.add_argument("png", type=Path)
    parser.add_argument("--placed-width-in", type=positive_float)
    parser.add_argument("--placed-height-in", type=positive_float)
    parser.add_argument("--min-ppi", type=positive_float, default=300.0)
    parser.add_argument(
        "--expect-alpha", choices=("any", "required", "forbidden"), default="any"
    )
    args = parser.parse_args()

    report = inspect_png(args.png)
    errors = report["errors"]
    warnings = report["warnings"]

    width = report.get("width_px")
    height = report.get("height_px")
    effective: dict[str, float] = {}
    if isinstance(width, int) and args.placed_width_in:
        effective["x"] = round(width / args.placed_width_in, 2)
    if isinstance(height, int) and args.placed_height_in:
        effective["y"] = round(height / args.placed_height_in, 2)
    if effective:
        report["placed_size_in"] = {
            "width": args.placed_width_in,
            "height": args.placed_height_in,
        }
        report["effective_ppi"] = effective
        if min(effective.values()) < args.min_ppi:
            errors.append(
                f"effective PPI {min(effective.values()):.2f} is below target {args.min_ppi:.2f}"
            )
    else:
        report["effective_ppi"] = None
        warnings.append("effective PPI was not checked because no placed size was supplied")

    alpha = report.get("alpha_channel_or_trns")
    if args.expect_alpha == "required" and alpha is not True:
        errors.append("an alpha channel or tRNS chunk is required")
    if args.expect_alpha == "forbidden" and alpha is True:
        errors.append("alpha is forbidden for this target")

    report["minimum_ppi_target"] = args.min_ppi
    report["status"] = "fail" if errors else "pass"
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
