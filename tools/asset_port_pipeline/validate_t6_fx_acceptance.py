#!/usr/bin/env python
import argparse
import collections
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def bit_count(value: int) -> int:
    return value.bit_count()


def parse_hex(value: str | None) -> int:
    if not value:
        return 0
    return int(value, 16)


def visual_signature(visuals: dict[str, Any] | None) -> list[str]:
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


def element_summary(element: dict[str, Any]) -> dict[str, Any]:
    atlas = element.get("atlas") or {}
    shape = ((element.get("shape") or {}).get("value")) or {}
    return {
        "index": element.get("index"),
        "section": element.get("section"),
        "type": element.get("elemType"),
        "flagsHex": element.get("flagsHex"),
        "flagsInt": parse_hex(element.get("flagsHex")),
        "sortOrder": element.get("sortOrder"),
        "lifeBase": (element.get("lifeSpanMsec") or {}).get("base", 0),
        "fadeInBase": (element.get("fadeInRange") or {}).get("base", 0.0),
        "fadeOutBase": (element.get("fadeOutRange") or {}).get("base", 0.0),
        "atlasBehavior": atlas.get("behavior"),
        "atlasEntryCountAndIndexRange": atlas.get("entryCountAndIndexRange"),
        "rotationAxisHex": element.get("rotationAxisHex"),
        "billboardPivot": element.get("billboardPivot"),
        "billboardTopWidth": shape.get("topWidth"),
        "billboardBottomWidth": shape.get("bottomWidth"),
        "spawnLooping": (element.get("spawn") or {}).get("looping"),
        "spawnOneShotCount": (element.get("spawn") or {}).get("oneShotCount"),
        "visuals": visual_signature(element.get("visuals")),
    }


def effect_summary(data: dict[str, Any], path: Path) -> dict[str, Any]:
    elements = [element_summary(element) for element in data.get("elements") or []]
    return {
        "name": data.get("name"),
        "path": str(path),
        "flagsHex": data.get("flagsHex"),
        "flagsInt": parse_hex(data.get("flagsHex")),
        "elements": elements,
    }


def build_stock_index(stock_effects: list[dict[str, Any]]) -> dict[str, Any]:
    by_type: dict[str, dict[str, Any]] = {}
    effect_flags = set()

    for effect in stock_effects:
        effect_flags.add(effect["flagsInt"])
        for element in effect["elements"]:
            elem_type = element["type"]
            bucket = by_type.setdefault(
                elem_type,
                {
                    "flags": set(),
                    "flags_masked_loop": set(),
                    "atlas": set(),
                    "rotation": set(),
                    "materials": collections.Counter(),
                },
            )
            bucket["flags"].add(element["flagsInt"])
            bucket["flags_masked_loop"].add(element["flagsInt"] & ~0x1)
            bucket["atlas"].add(element["atlasBehavior"])
            bucket["rotation"].add(element["rotationAxisHex"])
            for visual in element["visuals"]:
                bucket["materials"][visual] += 1

    return {"effect_flags": effect_flags, "by_type": by_type}


def nearest_flag(target: int, choices: set[int]) -> dict[str, Any] | None:
    if not choices:
        return None
    best = None
    for choice in choices:
        distance = bit_count(target ^ choice)
        if best is None or distance < best["distance"] or (distance == best["distance"] and choice < best["value"]):
            best = {"value": choice, "distance": distance}
    return best


def classify_candidate(effect: dict[str, Any], stock_index: dict[str, Any]) -> dict[str, Any]:
    findings = []
    counts = collections.Counter()

    if effect["flagsInt"] not in stock_index["effect_flags"]:
        counts["effect_flags_unseen"] += 1
        findings.append(
            {
                "level": "effect",
                "kind": "effect_flags_unseen",
                "message": f"Effect flags {effect['flagsHex']} are unseen in the stock corpus.",
            }
        )

    for element in effect["elements"]:
        elem_type = element["type"]
        bucket = stock_index["by_type"].get(elem_type)
        if not bucket:
            counts["unseen_elem_type"] += 1
            findings.append(
                {
                    "level": "element",
                    "index": element["index"],
                    "kind": "unseen_elem_type",
                    "message": f"Element type {elem_type} does not appear in the stock corpus.",
                }
            )
            continue

        if element["flagsInt"] in bucket["flags"]:
            counts["flags_exact_match"] += 1
        elif (element["flagsInt"] & ~0x1) in bucket["flags_masked_loop"]:
            counts["flags_match_ignoring_loop_bit"] += 1
            nearest = nearest_flag(element["flagsInt"] & ~0x1, bucket["flags_masked_loop"])
            findings.append(
                {
                    "level": "element",
                    "index": element["index"],
                    "kind": "flags_near_match_loop_bit",
                    "message": (
                        f"{elem_type} flags {element['flagsHex']} are not an exact stock match, "
                        f"but match stock after masking loop bit to 0x{(element['flagsInt'] & ~0x1):08X}."
                    ),
                    "nearestMaskedFlagsHex": f"0x{nearest['value']:08X}" if nearest else None,
                }
            )
        else:
            counts["flags_unseen"] += 1
            nearest = nearest_flag(element["flagsInt"], bucket["flags"])
            findings.append(
                {
                    "level": "element",
                    "index": element["index"],
                    "kind": "flags_unseen",
                    "message": f"{elem_type} flags {element['flagsHex']} are unseen in the stock corpus.",
                    "nearestFlagsHex": f"0x{nearest['value']:08X}" if nearest else None,
                    "distance": nearest["distance"] if nearest else None,
                }
            )

        if element["atlasBehavior"] in bucket["atlas"]:
            counts["atlas_exact_match"] += 1
        else:
            counts["atlas_unseen"] += 1
            findings.append(
                {
                    "level": "element",
                    "index": element["index"],
                    "kind": "atlas_unseen",
                    "message": f"{elem_type} atlas behavior {element['atlasBehavior']} is unseen in the stock corpus.",
                }
            )

        if elem_type.startswith("sprite") and (element["flagsInt"] & 0x1):
            counts["editor_loop_bit_leak"] += 1
            findings.append(
                {
                    "level": "element",
                    "index": element["index"],
                    "kind": "editor_loop_bit_leak",
                    "message": f"{elem_type} runtime flags {element['flagsHex']} still carry the authoring loop bit (0x1).",
                }
            )

        top_width = element.get("billboardTopWidth")
        bottom_width = element.get("billboardBottomWidth")
        if elem_type.startswith("sprite") and top_width == 0.0 and bottom_width == 0.0:
            counts["zero_billboard_width"] += 1
            findings.append(
                {
                    "level": "element",
                    "index": element["index"],
                    "kind": "zero_billboard_width",
                    "message": f"{elem_type} compiles with zero billboard width (top={top_width}, bottom={bottom_width}).",
                }
            )

    return {
        "effect": effect["name"],
        "flagsHex": effect["flagsHex"],
        "counts": dict(counts),
        "findings": findings,
        "acceptedLikeStock": (
            counts["unseen_elem_type"] == 0
            and counts["flags_unseen"] == 0
            and counts["atlas_unseen"] == 0
            and counts["editor_loop_bit_leak"] == 0
            and counts["zero_billboard_width"] == 0
        ),
    }


def dump_fx_from_ff(unlinker: Path, ff: Path, dump_root: Path) -> None:
    if dump_root.exists():
        shutil.rmtree(dump_root)
    cmd = [str(unlinker), "--include-assets", "fx", "--output-folder", str(dump_root), str(ff)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Unlinker failed with code {result.returncode}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")


def collect_effects(fx_root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    stock = []
    candidates = []
    for path in sorted(fx_root.rglob("*.json")):
        summary = effect_summary(load_json(path), path)
        name = summary["name"] or ""
        if name.startswith("zombie/fx_idgun_"):
            candidates.append(summary)
            continue
        if name.startswith("zombie/fx_bo3_rev_"):
            continue
        stock.append(summary)
    return stock, candidates


def main() -> int:
    parser = argparse.ArgumentParser(description="Dump a built FF and validate converted BO3 FX against the broader stock T6 FX corpus.")
    parser.add_argument("--ff", required=True, help="Fastfile to dump and validate.")
    parser.add_argument("--unlinker", default="tools/oat/Unlinker.exe", help="Path to Unlinker.exe.")
    parser.add_argument("--dump-root", default="_build/t6_fx_validation_dump", help="Dump output root.")
    parser.add_argument("--json-out", default="_build/fx_compare/t6_fx_acceptance_report.json", help="Validation report output path.")
    args = parser.parse_args()

    root = Path.cwd()
    ff_path = (root / args.ff).resolve()
    unlinker_path = (root / args.unlinker).resolve()
    dump_root = (root / args.dump_root).resolve()
    json_out = (root / args.json_out).resolve()

    dump_fx_from_ff(unlinker_path, ff_path, dump_root)
    fx_root = dump_root / "fx"
    stock_effects, candidate_effects = collect_effects(fx_root)
    stock_index = build_stock_index(stock_effects)
    reports = [classify_candidate(effect, stock_index) for effect in candidate_effects]

    report = {
        "ff": str(ff_path),
        "dump_root": str(dump_root),
        "stockCount": len(stock_effects),
        "candidateCount": len(candidate_effects),
        "candidateReports": reports,
    }

    json_out.parent.mkdir(parents=True, exist_ok=True)
    with json_out.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")

    print(f"Stock effects indexed: {len(stock_effects)}")
    print(f"Candidate effects analyzed: {len(candidate_effects)}")
    print(f"Report: {json_out}")
    for candidate in reports:
        counts = candidate["counts"]
        print()
        print(candidate["effect"])
        print(f"  acceptedLikeStock={candidate['acceptedLikeStock']}")
        print(f"  flags_exact_match={counts.get('flags_exact_match', 0)}")
        print(f"  flags_match_ignoring_loop_bit={counts.get('flags_match_ignoring_loop_bit', 0)}")
        print(f"  flags_unseen={counts.get('flags_unseen', 0)}")
        print(f"  atlas_exact_match={counts.get('atlas_exact_match', 0)}")
        print(f"  atlas_unseen={counts.get('atlas_unseen', 0)}")
        print(f"  editor_loop_bit_leak={counts.get('editor_loop_bit_leak', 0)}")
        print(f"  zero_billboard_width={counts.get('zero_billboard_width', 0)}")
        print(f"  unseen_elem_type={counts.get('unseen_elem_type', 0)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
