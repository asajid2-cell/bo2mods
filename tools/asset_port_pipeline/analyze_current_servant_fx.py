#!/usr/bin/env python3
"""Build and analyze the current staged BO3 Servant FX set one effect at a time.

This is an understanding-first diagnostic. It answers:

1. Which current staged Servant effects compile cleanly through the custom T6
   raw-FX path when isolated?
2. Which compiled native effects are likely to be visibly renderable on their
   own?
3. Which effects were already support-only / inert in the staged raw .efx, and
   which ones became inert only after translation?

That lets us distinguish:
- bad render probes (support-only effects like hole_md)
- real translation regressions
- strong candidates for the next minimal runtime render check
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / "_build" / "fx_current_servant_analysis"
REPORT_PATH = WORK / "current_servant_fx_report.json"
PROBE_BUILDER = ROOT / "_build" / "build_t6_ff_contract_probe.py"
BO3_BUILD_ROOT = ROOT / "_build" / "bo3_rev_idg_probe"
MOD_LOAD_ZONE = BO3_BUILD_ROOT / "zone_source" / "mod_load.zone"
STABLE_UNLINKER = ROOT / "_build" / "oat_release" / "unzipped" / "Unlinker.exe"
DEV_UNLINKER = ROOT / "tools" / "oat" / "Unlinker.exe"
VIABILITY_MODULE = ROOT / "tools" / "asset_port_pipeline" / "verify_t6_fx_visual_viability.py"


def _load_viability_module():
    spec = importlib.util.spec_from_file_location("verify_t6_fx_visual_viability", VIABILITY_MODULE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load viability module: {VIABILITY_MODULE}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run_checked(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "Command failed:\n"
            + " ".join(args)
            + "\nstdout:\n"
            + result.stdout
            + "\nstderr:\n"
            + result.stderr
        )
    return result


def _parse_zone_manifest(zone_path: Path) -> dict[str, list[str]]:
    fx: list[str] = []
    materials: list[str] = []
    images: list[str] = []
    for raw in zone_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("//") or line.startswith(">"):
            continue
        asset_type, _, asset_name = line.partition(",")
        asset_name = asset_name.strip()
        if asset_type == "fx":
            fx.append(asset_name)
        elif asset_type == "material":
            materials.append(asset_name)
        elif asset_type == "image":
            images.append(asset_name)
    return {"fx": fx, "materials": materials, "images": images}


def _raw_split_top_level_blocks(text: str) -> tuple[str, list[str]]:
    header_end = 0
    blocks: list[str] = []
    depth = 0
    block_start: int | None = None
    for index, char in enumerate(text):
        if char == "{":
            if depth == 0:
                block_start = index
                if not blocks:
                    header_end = index
            depth += 1
        elif char == "}":
            if depth > 0:
                depth -= 1
                if depth == 0 and block_start is not None:
                    blocks.append(text[block_start : index + 1])
                    block_start = None
    return text[:header_end], blocks


def _raw_extract_pair(block: str, key: str) -> tuple[float, float] | None:
    match = re.search(
        rf"^\s*{re.escape(key)}\s+([-\d\.]+)\s+([-\d\.]+);",
        block,
        flags=re.MULTILINE,
    )
    if not match:
        return None
    return float(match.group(1)), float(match.group(2))


def _raw_extract_scalar(block: str, key: str) -> float | None:
    match = re.search(
        rf"^\s*{re.escape(key)}\s+([-\d\.]+)",
        block,
        flags=re.MULTILINE,
    )
    if not match:
        return None
    return float(match.group(1))


def _raw_extract_statement_block(block: str, key: str) -> str | None:
    match = re.search(rf"^\s*{re.escape(key)}\b.*?$", block, flags=re.MULTILINE)
    if not match:
        return None
    start = block.find("{", match.end())
    if start < 0:
        return None
    depth = 0
    for index in range(start, len(block)):
        char = block[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return block[start : index + 1]
    return None


def _raw_material(block: str) -> tuple[str, str]:
    visual_types = [
        "billboardSprite",
        "orientedSprite",
        "rotatedSprite",
        "cloud",
        "line",
        "tail",
        "trail",
        "decal",
    ]
    for visual_type in visual_types:
        match = re.search(
            rf"{re.escape(visual_type)}\s*\{{\s*\"([^\"]+)\"",
            block,
            flags=re.DOTALL,
        )
        if match:
            return visual_type, match.group(1).strip()
    return "", ""


def _raw_material_family(material: str) -> str:
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


def _raw_extract_alpha(block: str) -> int:
    graph = _raw_extract_statement_block(block, "alphaGraph")
    if not graph:
        return 0
    samples = re.findall(r"([-\d\.]+)\s+([-\d\.]+)", graph)
    if not samples:
        return 0
    alpha_values = [float(value) for _time, value in samples]
    return max(0, min(255, round(max(alpha_values or [0.0]) * 255.0)))


def _raw_extract_rgb(block: str) -> int:
    graph = _raw_extract_statement_block(block, "colorGraph")
    if not graph:
        return 0
    max_rgb = 0.0
    for match in re.finditer(
        r"([-\d\.]+)\s+([-\d\.]+)\s+([-\d\.]+)\s+([-\d\.]+)\s+([-\d\.]+)",
        graph,
    ):
        try:
            _time, r, g, b, _a = (float(item) for item in match.groups())
        except ValueError:
            continue
        max_rgb = max(max_rgb, r, g, b)
    return max(0, min(255, round(max_rgb * 255.0)))


def _raw_effect_viability(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    _header, blocks = _raw_split_top_level_blocks(text)
    elements: list[dict[str, Any]] = []
    for index, block in enumerate(blocks):
        elem_type, material = _raw_material(block)
        size0 = _raw_extract_scalar(block, "sizeGraph0") or 0.0
        size1 = _raw_extract_scalar(block, "sizeGraph1") or 0.0
        max_dim = max(size0, size1)
        life = _raw_extract_pair(block, "lifeSpanMsec") or (0.0, 0.0)
        fade_in = _raw_extract_pair(block, "fadeInRange") or (0.0, 0.0)
        fade_out = _raw_extract_pair(block, "fadeOutRange") or (0.0, 0.0)
        spawn_range = _raw_extract_pair(block, "spawnRange") or (0.0, 0.0)
        spawn_looping = _raw_extract_pair(block, "spawnLooping") or (0.0, 0.0)
        issues: list[str] = []
        life_base = life[0]
        fade_in_base = fade_in[0]
        fade_out_base = fade_out[0]
        spawn_range_base = spawn_range[1]
        max_alpha = _raw_extract_alpha(block)
        max_rgb = _raw_extract_rgb(block)
        if life_base <= 16.0:
            issues.append("micro_lifespan")
        if max_dim < 4.0:
            issues.append("tiny_size")
        if max_alpha < 64:
            issues.append("subtle_alpha")
        if max_rgb < 32:
            issues.append("dark_color")
        if fade_in_base > max(life_base, 1.0):
            issues.append("fade_in_exceeds_life")
        if fade_out_base > max(life_base, 1.0):
            issues.append("fade_out_exceeds_life")
        family = _raw_material_family(material)
        if family == "dust_smoke" and max_dim < 8.0:
            issues.append("dust_support_layer")
        strong_visible = (
            max_dim >= 32.0 and max_alpha >= 96 and max_rgb >= 64 and life_base >= 100.0
        )
        moderate_visible = (
            max_dim >= 16.0 and max_alpha >= 64 and max_rgb >= 48 and life_base >= 33.0
        )
        elements.append(
            {
                "index": index,
                "name": (re.search(r'name\s+"([^"]+)"', block) or [None, ""])[1],
                "elemType": elem_type,
                "material": material,
                "materialFamily": family,
                "lifeBase": life_base,
                "fadeInBase": fade_in_base,
                "fadeOutBase": fade_out_base,
                "spawnRangeBase": spawn_range_base,
                "loopIntervalMsec": int(spawn_looping[0]),
                "loopCount": int((_raw_extract_pair(block, "spawnLoopingSpawnCount") or (0.0, 0.0))[0]),
                "maxAlpha": max_alpha,
                "maxRgb": max_rgb,
                "maxDim": max_dim,
                "strongVisibleCandidate": strong_visible,
                "moderateVisibleCandidate": moderate_visible,
                "issues": issues,
            }
        )

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
        glow_elements = [element for element in elements if element["materialFamily"] == "glow"]
        if glow_elements and all("micro_lifespan" in element["issues"] for element in glow_elements):
            failure_reasons.append("all_glow_layers_are_micro_lifespan")
        if not any(element["lifeBase"] >= 33.0 and element["maxDim"] >= 16.0 for element in elements):
            failure_reasons.append("no_persistent_visible_footprint")
        if all(
            element["materialFamily"] == "dust_smoke" or "dark_color" in element["issues"]
            for element in elements
        ):
            failure_reasons.append("no_bright_primary_layer")

    return {
        "name": f"zombie/{path.stem}",
        "path": str(path),
        "bucket": bucket,
        "failureReasons": failure_reasons,
        "elements": elements,
    }


def _classification(raw_bucket: str, native_bucket: str) -> str:
    if raw_bucket == "likely_inert" and native_bucket == "likely_inert":
        return "support_only_source_effect"
    if raw_bucket != "likely_inert" and native_bucket == "likely_inert":
        return "translation_regression"
    if raw_bucket == "likely_inert" and native_bucket != "likely_inert":
        return "translation_upgrade"
    return "stable_viable"


def _effect_score(report: dict[str, Any]) -> float:
    score = 0.0
    for element in report.get("elements", []):
        if element.get("strongVisibleCandidate"):
            score += float(element.get("maxDim", 0.0)) * 4.0
            score += float(element.get("maxAlpha", 0)) * 2.0
            score += float(element.get("lifeBase", 0.0)) * 0.5
        elif element.get("moderateVisibleCandidate"):
            score += float(element.get("maxDim", 0.0)) * 2.0
            score += float(element.get("maxAlpha", 0))
            score += float(element.get("lifeBase", 0.0)) * 0.25
    return score


def _dump_native_fx(ff_path: Path, output_dir: Path) -> None:
    _run_checked(
        [
            str(DEV_UNLINKER),
            "--include-assets",
            "fx",
            "--output-folder",
            str(output_dir),
            str(ff_path),
        ],
        cwd=ROOT,
    )


def _case_report_path(effect_name: str) -> Path:
    stem = effect_name.split("/", 1)[-1].replace("/", "_")
    return WORK / "reports" / f"{stem}.json"


def _case_dump_dir(effect_name: str) -> Path:
    stem = effect_name.split("/", 1)[-1].replace("/", "_")
    return WORK / "dumps" / stem


def _build_case(effect_name: str, materials: list[str], images: list[str]) -> dict[str, Any]:
    case_name = effect_name.split("/", 1)[-1].replace("/", "_")
    report_path = _case_report_path(effect_name)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    args = [
        sys.executable,
        "-u",
        str(PROBE_BUILDER),
        "--custom-fx-asset",
        effect_name,
        "--custom-case-name",
        case_name,
        "--zone-name",
        "mod_load",
        "--report-path",
        str(report_path),
    ]
    if materials:
        args.extend(["--custom-materials", *materials])
    if images:
        args.extend(["--custom-images", *images])
    _run_checked(args, cwd=ROOT)
    return json.loads(report_path.read_text(encoding="utf-8"))


def analyze() -> dict[str, Any]:
    viability = _load_viability_module()
    manifest = _parse_zone_manifest(MOD_LOAD_ZONE)
    fx_assets = manifest["fx"]
    materials = manifest["materials"]
    images = manifest["images"]
    cases: list[dict[str, Any]] = []
    for effect_name in fx_assets:
        build_report = _build_case(effect_name, materials, images)
        case = build_report["cases"][0]
        ff_path = Path(case["ff"]["path"])
        dump_dir = _case_dump_dir(effect_name)
        if dump_dir.exists():
            for item in dump_dir.iterdir():
                if item.is_dir():
                    import shutil

                    shutil.rmtree(item)
                else:
                    item.unlink()
        dump_dir.mkdir(parents=True, exist_ok=True)
        _dump_native_fx(ff_path, dump_dir)
        native_json = dump_dir / "fx" / effect_name.split("/", 1)[0] / (effect_name.split("/", 1)[1] + ".json")
        staged_raw = BO3_BUILD_ROOT / "fx" / effect_name.split("/", 1)[0] / (effect_name.split("/", 1)[1] + ".efx")
        native_effect = viability._load_json(native_json)
        native_report = viability._effect_viability(native_effect)
        native_report["path"] = str(native_json)
        raw_report = _raw_effect_viability(staged_raw)
        classification = _classification(raw_report["bucket"], native_report["bucket"])
        cases.append(
            {
                "effect": effect_name,
                "build_case": case["name"],
                "ff": case["ff"],
                "build_ok": case["build_ok"],
                "unlink_ok": case["unlink_ok"],
                "dev_unlink_ok": case["dev_unlink_ok"],
                "build_problems": case["build_problems"],
                "raw": raw_report,
                "native": native_report,
                "classification": classification,
                "native_score": _effect_score(native_report),
            }
        )

    probe_candidates = sorted(
        [
            {
                "effect": case["effect"],
                "classification": case["classification"],
                "native_bucket": case["native"]["bucket"],
                "raw_bucket": case["raw"]["bucket"],
                "native_score": case["native_score"],
            }
            for case in cases
            if case["native"]["bucket"] == "standalone_viable"
        ],
        key=lambda item: item["native_score"],
        reverse=True,
    )
    inert_candidates = [
        {
            "effect": case["effect"],
            "classification": case["classification"],
            "raw_bucket": case["raw"]["bucket"],
            "native_bucket": case["native"]["bucket"],
            "raw_failure_reasons": case["raw"]["failureReasons"],
            "native_failure_reasons": case["native"]["failureReasons"],
        }
        for case in cases
        if case["native"]["bucket"] == "likely_inert"
    ]
    return {
        "mod_load_zone": str(MOD_LOAD_ZONE),
        "manifest": manifest,
        "effects": cases,
        "summary": {
            "total_effects": len(cases),
            "stable_viable": sum(case["classification"] == "stable_viable" for case in cases),
            "support_only_source_effect": sum(case["classification"] == "support_only_source_effect" for case in cases),
            "translation_regression": sum(case["classification"] == "translation_regression" for case in cases),
            "translation_upgrade": sum(case["classification"] == "translation_upgrade" for case in cases),
        },
        "probe_candidates": probe_candidates,
        "bad_probe_candidates": inert_candidates,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Analyze the current staged BO3 Servant FX set effect-by-effect.")
    parser.add_argument("--report-path", default=str(REPORT_PATH), help="JSON report output path.")
    args = parser.parse_args(argv)

    WORK.mkdir(parents=True, exist_ok=True)
    report = analyze()
    report_path = Path(args.report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote {report_path}")
    print("Summary:")
    for key, value in report["summary"].items():
        print(f"  {key}={value}")
    print("Top probe candidates:")
    for item in report["probe_candidates"][:5]:
        print(
            f"  {item['effect']} native={item['native_bucket']} raw={item['raw_bucket']} "
            f"class={item['classification']} score={item['native_score']:.1f}"
        )
    print("Likely inert / bad standalone probes:")
    for item in report["bad_probe_candidates"]:
        print(
            f"  {item['effect']} class={item['classification']} "
            f"raw={item['raw_bucket']} native={item['native_bucket']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
