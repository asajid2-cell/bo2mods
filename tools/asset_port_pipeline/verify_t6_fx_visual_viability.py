#!/usr/bin/env python3
"""Assess whether compiled native T6 FX JSON is likely to be visibly renderable.

This does not try to predict exact artistic quality. It answers a narrower and
more useful question for the T7->T6 port:

Does this compiled T6 effect contain at least one element with a meaningful
standalone visible footprint, or is it composed only of micro-lifespan /
tiny-size support layers that will be effectively invisible in world probes?
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _iter_vis_samples(element: dict[str, Any]) -> list[dict[str, Any]]:
    return list(element.get("visSamples") or [])


def _sample_color(sample: dict[str, Any]) -> tuple[int, int, int, int]:
    base = sample.get("base") or {}
    color = base.get("color") or [0, 0, 0, 0]
    padded = list(color[:4]) + [0] * max(0, 4 - len(color))
    return int(padded[0]), int(padded[1]), int(padded[2]), int(padded[3])


def _sample_size(sample: dict[str, Any]) -> tuple[float, float]:
    base = sample.get("base") or {}
    size = base.get("size") or [0.0, 0.0]
    padded = list(size[:2]) + [0.0] * max(0, 2 - len(size))
    return float(padded[0]), float(padded[1])


def _sample_scale(sample: dict[str, Any]) -> float:
    base = sample.get("base") or {}
    return float(base.get("scale") or 0.0)


def _element_material(element: dict[str, Any]) -> str:
    visuals = element.get("visuals") or {}
    if visuals.get("kind") != "instance":
        return ""
    value = visuals.get("value") or {}
    return str(value.get("material") or "")


def _material_family(material: str) -> str:
    lowered = material.lower()
    if "glow" in lowered or "light" in lowered or "ember" in lowered:
        return "glow"
    if "dust" in lowered or "smoke" in lowered or "fog" in lowered:
        return "dust_smoke"
    if "distort" in lowered:
        return "distortion"
    if "decal" in lowered:
        return "decal"
    return "other"


def _element_metrics(element: dict[str, Any]) -> dict[str, Any]:
    vis_samples = _iter_vis_samples(element)
    alphas: list[int] = []
    rgb_maxes: list[int] = []
    max_dim = 0.0
    max_area = 0.0
    max_scale = 0.0
    for sample in vis_samples:
        r, g, b, a = _sample_color(sample)
        sx, sy = _sample_size(sample)
        scale = _sample_scale(sample)
        alphas.append(a)
        rgb_maxes.append(max(r, g, b))
        max_dim = max(max_dim, sx, sy)
        max_area = max(max_area, sx * sy)
        max_scale = max(max_scale, scale)

    life = float((element.get("lifeSpanMsec") or {}).get("base") or 0.0)
    fade_in = float((element.get("fadeInRange") or {}).get("base") or 0.0)
    fade_out = float((element.get("fadeOutRange") or {}).get("base") or 0.0)
    spawn_range = float((element.get("spawnRange") or {}).get("base") or 0.0)
    looping = (element.get("spawn") or {}).get("looping") or {}
    loop_interval = int(looping.get("intervalMsec") or 0)
    loop_count = int(looping.get("count") or 0)
    material = _element_material(element)

    issues: list[str] = []
    if life <= 16:
        issues.append("micro_lifespan")
    if max_dim < 4.0:
        issues.append("tiny_size")
    if (max(alphas) if alphas else 0) < 64:
        issues.append("subtle_alpha")
    if (max(rgb_maxes) if rgb_maxes else 0) < 32:
        issues.append("dark_color")
    if spawn_range > max(64.0, max_dim * 4.0):
        issues.append("wide_spawn_dispersion")
    if fade_in > max(life, 1.0):
        issues.append("fade_in_exceeds_life")
    if fade_out > max(life, 1.0):
        issues.append("fade_out_exceeds_life")

    family = _material_family(material)
    if family == "dust_smoke" and max_dim < 8.0:
        issues.append("dust_support_layer")

    strong_visible = (
        max_dim >= 32.0
        and max(alphas or [0]) >= 96
        and max(rgb_maxes or [0]) >= 64
        and life >= 100.0
    )
    moderate_visible = (
        max_dim >= 16.0
        and max(alphas or [0]) >= 64
        and max(rgb_maxes or [0]) >= 48
        and life >= 33.0
    )

    return {
        "index": element.get("index"),
        "elemType": element.get("elemType"),
        "material": material,
        "materialFamily": family,
        "lifeBase": life,
        "fadeInBase": fade_in,
        "fadeOutBase": fade_out,
        "spawnRangeBase": spawn_range,
        "loopIntervalMsec": loop_interval,
        "loopCount": loop_count,
        "maxAlpha": max(alphas or [0]),
        "maxRgb": max(rgb_maxes or [0]),
        "maxDim": max_dim,
        "maxArea": max_area,
        "maxScale": max_scale,
        "strongVisibleCandidate": strong_visible,
        "moderateVisibleCandidate": moderate_visible,
        "issues": issues,
    }


def _effect_viability(effect: dict[str, Any]) -> dict[str, Any]:
    elements = [_element_metrics(element) for element in effect.get("elements") or []]
    strong = [element for element in elements if element["strongVisibleCandidate"]]
    moderate = [element for element in elements if element["moderateVisibleCandidate"]]

    if strong:
        bucket = "standalone_viable"
    elif moderate:
        bucket = "support_visible_only"
    else:
        bucket = "likely_inert"

    failure_reasons: list[str] = []
    if not strong:
        if all("micro_lifespan" in element["issues"] for element in elements if element["materialFamily"] == "glow"):
            failure_reasons.append("all_glow_layers_are_micro_lifespan")
        if all("tiny_size" in element["issues"] for element in elements):
            failure_reasons.append("all_layers_tiny")
        if all(
            element["materialFamily"] == "dust_smoke" or "dark_color" in element["issues"]
            for element in elements
        ):
            failure_reasons.append("no_bright_primary_layer")
        if not any(element["lifeBase"] >= 33.0 and element["maxDim"] >= 16.0 for element in elements):
            failure_reasons.append("no_persistent_visible_footprint")

    return {
        "name": effect.get("name") or "",
        "counts": effect.get("counts") or {},
        "bucket": bucket,
        "strongVisibleElements": [element["index"] for element in strong],
        "moderateVisibleElements": [element["index"] for element in moderate if element["index"] not in {item["index"] for item in strong}],
        "failureReasons": failure_reasons,
        "elements": elements,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Assess compiled native T6 FX JSON for standalone visual viability.")
    parser.add_argument("--fx", nargs="+", required=True, help="One or more compiled T6 FX JSON files.")
    parser.add_argument("--json-out", help="Optional JSON output report.")
    args = parser.parse_args()

    reports = []
    for item in args.fx:
        path = Path(item)
        effect = _load_json(path)
        report = _effect_viability(effect)
        report["path"] = str(path)
        reports.append(report)

    if args.json_out:
        out_path = Path(args.json_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps({"effects": reports}, indent=2) + "\n", encoding="utf-8")

    for report in reports:
        print(f"{report['name'] or Path(report['path']).stem}: {report['bucket']}")
        if report["failureReasons"]:
            for reason in report["failureReasons"]:
                print(f"  reason: {reason}")
        for element in report["elements"]:
            flags = []
            if element["strongVisibleCandidate"]:
                flags.append("strong")
            elif element["moderateVisibleCandidate"]:
                flags.append("moderate")
            if element["issues"]:
                flags.extend(element["issues"])
            issue_summary = ",".join(flags) or "none"
            print(
                "  elem[{index}] {elemType} material={material} "
                "life={lifeBase:g} maxDim={maxDim:g} alpha={maxAlpha} rgb={maxRgb} "
                "loop={loopIntervalMsec} issues={issue_summary}".format(**element, issue_summary=issue_summary)
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
