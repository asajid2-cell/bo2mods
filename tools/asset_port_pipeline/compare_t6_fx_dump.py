#!/usr/bin/env python
import argparse
import collections
import json
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _visual_signature(visuals: dict[str, Any] | None) -> list[str]:
    if not visuals:
        return []
    kind = visuals.get("kind")
    if kind == "instance":
        value = visuals.get("value") or {}
        for key in ("material", "effect", "model", "soundName", "spotLightEffectName"):
            if value.get(key):
                return [f"{kind}:{key}:{value[key]}"]
        return [kind]
    if kind == "mark_array":
        values = []
        for entry in visuals.get("values") or []:
            for material in entry.get("materials") or []:
                values.append(f"{kind}:material:{material}")
        return values or [kind]
    return [kind or "<none>"]


def _element_summary(element: dict[str, Any]) -> dict[str, Any]:
    life = (element.get("lifeSpanMsec") or {}).get("base", 0)
    fade_in = (element.get("fadeInRange") or {}).get("base", 0.0)
    fade_out = (element.get("fadeOutRange") or {}).get("base", 0.0)
    atlas = element.get("atlas") or {}
    return {
        "index": element.get("index"),
        "section": element.get("section"),
        "type": element.get("elemType"),
        "flagsHex": element.get("flagsHex"),
        "sortOrder": element.get("sortOrder"),
        "lifeBase": life,
        "fadeInBase": fade_in,
        "fadeOutBase": fade_out,
        "atlasBehavior": atlas.get("behavior"),
        "atlasEntryCountAndIndexRange": atlas.get("entryCountAndIndexRange"),
        "rotationAxisHex": element.get("rotationAxisHex"),
        "billboardPivot": element.get("billboardPivot"),
        "spawnLooping": (element.get("spawn") or {}).get("looping"),
        "spawnOneShotCount": (element.get("spawn") or {}).get("oneShotCount"),
        "visuals": _visual_signature(element.get("visuals")),
    }


def _effect_summary(data: dict[str, Any]) -> dict[str, Any]:
    elements = [_element_summary(element) for element in data.get("elements") or []]
    return {
        "name": data.get("name"),
        "path": data.get("_path"),
        "flagsHex": data.get("flagsHex"),
        "lifetimeMsec": data.get("lifetimeMsec"),
        "counts": data.get("counts"),
        "totalSize": data.get("totalSize"),
        "elementTypes": collections.Counter(element["type"] for element in elements),
        "elementFlags": collections.Counter(element["flagsHex"] for element in elements),
        "atlasBehaviors": collections.Counter(element["atlasBehavior"] for element in elements),
        "materials": collections.Counter(
            visual.split(":", 2)[2]
            for element in elements
            for visual in element["visuals"]
            if visual.startswith("instance:material:") or visual.startswith("mark_array:material:")
        ),
        "elements": elements,
    }


def _build_stock_index(stock_effects: list[dict[str, Any]]) -> dict[str, Any]:
    by_type: dict[str, dict[str, Any]] = {}
    effect_flags = set()

    for effect in stock_effects:
        effect_flags.add(effect["flagsHex"])
        for element in effect["elements"]:
            elem_type = element["type"]
            bucket = by_type.setdefault(
                elem_type,
                {
                    "flags": set(),
                    "atlasBehaviors": set(),
                    "rotationAxisHex": set(),
                    "sortOrders": set(),
                    "materials": set(),
                    "fadeInLifeRatios": [],
                },
            )
            bucket["flags"].add(element["flagsHex"])
            bucket["atlasBehaviors"].add(element["atlasBehavior"])
            bucket["rotationAxisHex"].add(element["rotationAxisHex"])
            bucket["sortOrders"].add(element["sortOrder"])
            for visual in element["visuals"]:
                bucket["materials"].add(visual)
            life = max(int(element["lifeBase"] or 0), 1)
            bucket["fadeInLifeRatios"].append(float(element["fadeInBase"] or 0.0) / float(life))

    for bucket in by_type.values():
        ratios = bucket["fadeInLifeRatios"]
        bucket["maxFadeInLifeRatio"] = max(ratios) if ratios else 0.0

    return {"effectFlags": effect_flags, "byType": by_type}


def _compare_effect(effect: dict[str, Any], stock_index: dict[str, Any]) -> dict[str, Any]:
    findings = []
    if effect["flagsHex"] not in stock_index["effectFlags"]:
        findings.append(
            {
                "level": "effect",
                "kind": "unseen_effect_flags",
                "message": f"Effect flags {effect['flagsHex']} do not appear in the stock reference set.",
            }
        )

    for element in effect["elements"]:
        elem_type = element["type"]
        stock_bucket = stock_index["byType"].get(elem_type)
        if not stock_bucket:
            findings.append(
                {
                    "level": "element",
                    "index": element["index"],
                    "kind": "unseen_elem_type",
                    "message": f"Element type {elem_type} does not appear in the stock reference set.",
                }
            )
            continue

        if element["flagsHex"] not in stock_bucket["flags"]:
            findings.append(
                {
                    "level": "element",
                    "index": element["index"],
                    "kind": "unseen_elem_flags",
                    "message": f"{elem_type} flags {element['flagsHex']} are unseen in the stock reference set for {elem_type}.",
                }
            )

        if element["atlasBehavior"] not in stock_bucket["atlasBehaviors"]:
            findings.append(
                {
                    "level": "element",
                    "index": element["index"],
                    "kind": "unseen_atlas_behavior",
                    "message": f"{elem_type} atlas behavior {element['atlasBehavior']} is unseen in the stock reference set for {elem_type}.",
                }
            )

        if element["rotationAxisHex"] not in stock_bucket["rotationAxisHex"]:
            findings.append(
                {
                    "level": "element",
                    "index": element["index"],
                    "kind": "unseen_rotation_axis",
                    "message": f"{elem_type} rotation axis {element['rotationAxisHex']} is unseen in the stock reference set for {elem_type}.",
                }
            )

        life = max(int(element["lifeBase"] or 0), 1)
        fade_ratio = float(element["fadeInBase"] or 0.0) / float(life)
        if fade_ratio > max(stock_bucket["maxFadeInLifeRatio"], 1.0) * 2.0:
            findings.append(
                {
                    "level": "element",
                    "index": element["index"],
                    "kind": "fade_in_ratio_outlier",
                    "message": (
                        f"{elem_type} fade-in/life ratio {fade_ratio:.2f} is far above the stock reference "
                        f"maximum {stock_bucket['maxFadeInLifeRatio']:.2f}."
                    ),
                }
            )

        if element["billboardPivot"] not in ([0.0, 0.0], [0.0, -0.0]) and elem_type.startswith("sprite"):
            findings.append(
                {
                    "level": "element",
                    "index": element["index"],
                    "kind": "non_default_pivot",
                    "message": f"{elem_type} uses non-default billboard pivot {element['billboardPivot']}.",
                }
            )

    return {
        "effect": effect["name"],
        "flagsHex": effect["flagsHex"],
        "topElementFlags": effect["elementFlags"].most_common(8),
        "topMaterials": effect["materials"].most_common(12),
        "findings": findings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare dumped native T6 FX JSON against stock references.")
    parser.add_argument("--stock", nargs="+", required=True, help="Stock T6 FX JSON files.")
    parser.add_argument("--candidate", nargs="+", required=True, help="Candidate / converted T6 FX JSON files.")
    parser.add_argument("--json-out", help="Optional output path for the full comparison report.")
    args = parser.parse_args()

    stock_effects = []
    for item in args.stock:
        path = Path(item)
        data = _load_json(path)
        data["_path"] = str(path)
        stock_effects.append(_effect_summary(data))

    candidate_effects = []
    for item in args.candidate:
        path = Path(item)
        data = _load_json(path)
        data["_path"] = str(path)
        candidate_effects.append(_effect_summary(data))

    stock_index = _build_stock_index(stock_effects)
    report = {
        "stock": [{"name": effect["name"], "path": effect["path"]} for effect in stock_effects],
        "candidateReports": [_compare_effect(effect, stock_index) for effect in candidate_effects],
    }

    if args.json_out:
        out_path = Path(args.json_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2)
            handle.write("\n")

    print("Stock reference set:")
    for effect in stock_effects:
        print(f"- {effect['name']} ({effect['path']})")

    print("\nCandidate mismatch summary:")
    for candidate in report["candidateReports"]:
        print(f"\n## {candidate['effect']}")
        print(f"effect flags: {candidate['flagsHex']}")
        if candidate["topElementFlags"]:
            print("top element flags:")
            for value, count in candidate["topElementFlags"]:
                print(f"  {value}: {count}")
        if candidate["topMaterials"]:
            print("top materials:")
            for value, count in candidate["topMaterials"]:
                print(f"  {value}: {count}")
        print("findings:")
        for finding in candidate["findings"][:20]:
            prefix = f"element[{finding['index']}]" if finding["level"] == "element" else "effect"
            print(f"  - {prefix}: {finding['message']}")
        if len(candidate["findings"]) > 20:
            print(f"  - ... {len(candidate['findings']) - 20} more")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
