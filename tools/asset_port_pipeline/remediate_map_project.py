from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent

import sys

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common import save_json  # noqa: E402
from linker_oracle import (  # noqa: E402
    append_zone_asset_lines,
    extract_missing_assets,
    infer_dependency_load_zones,
    parse_load_zones,
    run_linker,
    sanitize_name,
    stage_accuracy_graphs,
    stage_missing_assets,
)

COULD_NOT_LOAD_RE = re.compile(r'Could not load asset "([^"]+)" of type "([^"]+)"')
FAILED_TO_LOAD_RE = re.compile(r'Failed to load ([a-zA-Z0-9_]+) "([^"]+)"')
TECHSET_HASH_RE = re.compile(r"_[a-z0-9]{8}$", re.IGNORECASE)
TRAILING_INDEX_RE = re.compile(r"_\d+$")
MATERIAL_VARIANT_SUFFIX_RE = re.compile(r"_(cheap|noshadow|decal|overlay|detail|zonly)$", re.IGNORECASE)
STAGEABLE_TYPES = {
    "material",
    "image",
    "techset",
    "techniqueset",
    "technique",
    "xanim",
    "xanimparts",
    "xmodel",
    "xmodelalias",
    "rawfile",
    "script",
}
TEXT_SCAN_EXTENSIONS = {
    ".json",
    ".techset",
    ".tech",
    ".gsc",
    ".csc",
    ".csv",
    ".txt",
    ".cfg",
    ".vision",
}
DIR_TO_ASSET_TYPE = {
    "aitype": "aitype",
    "animstatedefs": "animstatedef",
    "animtrees": "animtree",
    "attachment": "attachment",
    "attachmentunique": "attachmentunique",
    "camo": "camo",
    "character": "character",
    "images": "image",
    "materials": "material",
    "physic": "physpreset",
    "rawfiles": "rawfile",
    "maps": "script",
    "clientscripts": "script",
    "soundbank": "soundbank",
    "stringtables": "stringtable",
    "techniques": "technique",
    "techsets": "techniqueset",
    "tracer": "tracer",
    "vehicle": "vehicle",
    "vehicles": "vehicle",
    "weapons": "weapon",
    "xanim": "xanim",
    "xanimparts": "xanimparts",
    "xmodel": "xmodel",
    "xmodelalias": "xmodelalias",
    "zbarrier": "zbarrier",
}
PREFERRED_DONOR_IMAGE_TOKENS = ("white", "black", "default", "identity", "neutral", "gradient")
PREFERRED_IMAGE_FALLBACKS = ("thermal_gradient2", "fx_shell_ir", "fx_shell_nml")


def zone_token(asset_type: str) -> str:
    normalized = asset_type.lower().strip()
    if normalized == "techset":
        return "techniqueset"
    if normalized == "xanimparts":
        return "xanim"
    if normalized == "xmodelalias":
        return "xmodel"
    return normalized


def asset_name_variants(value: str) -> List[str]:
    raw = value.strip().replace("\\", "/").strip("/")
    if not raw:
        return []
    parts = [raw]
    if "/" in raw:
        tail = raw.split("/")[-1]
        parts.append(tail)
    if "." in raw:
        parts.append(raw.rsplit(".", 1)[0])
    if raw.startswith("mc/"):
        parts.append(raw[3:])
    deduped: List[str] = []
    seen = set()
    for item in parts:
        key = item.lower().strip()
        if key and key not in seen:
            seen.add(key)
            deduped.append(key)
    return deduped


def extract_unresolved_assets(log_text: str) -> List[Tuple[str, str]]:
    out: List[Tuple[str, str]] = []
    seen = set()
    for match in COULD_NOT_LOAD_RE.finditer(log_text):
        key = (match.group(1).strip(), match.group(2).strip().lower())
        if key not in seen:
            seen.add(key)
            out.append(key)
    for match in FAILED_TO_LOAD_RE.finditer(log_text):
        key = (match.group(2).strip(), match.group(1).strip().lower())
        if key not in seen:
            seen.add(key)
            out.append(key)
    return out


def dedupe_assets(assets: Sequence[Tuple[str, str]]) -> List[Tuple[str, str]]:
    out: List[Tuple[str, str]] = []
    seen = set()
    for asset_name, asset_type in assets:
        name = asset_name.strip()
        kind = asset_type.strip().lower()
        if not name or not kind:
            continue
        key = (name.lower(), kind)
        if key in seen:
            continue
        seen.add(key)
        out.append((name, kind))
    return out


def stageable_assets(assets: Sequence[Tuple[str, str]]) -> List[Tuple[str, str]]:
    return [(name, kind) for name, kind in dedupe_assets(assets) if kind in STAGEABLE_TYPES]


def load_techset_names(project_zone_root: Path) -> List[str]:
    techset_root = project_zone_root / "techsets"
    if not techset_root.exists():
        return []
    names: set[str] = set()
    for path in techset_root.rglob("*.techset"):
        rel = path.relative_to(techset_root).with_suffix("").as_posix().lower()
        names.add(rel)
        names.add(Path(rel).name)
    return sorted(name for name in names if name)


def techset_family(name: str) -> str:
    return TECHSET_HASH_RE.sub("", name.strip().lower())


def longest_token_prefix_score(left: str, right: str) -> int:
    left_tokens = [token for token in left.split("_") if token]
    right_tokens = [token for token in right.split("_") if token]
    count = 0
    for ltok, rtok in zip(left_tokens, right_tokens):
        if ltok != rtok:
            break
        count += 1
    return count


def choose_techset_fallback(missing_name: str, available_names: Sequence[str]) -> str:
    normalized_missing = missing_name.strip().lower()
    if not normalized_missing or not available_names:
        return ""
    if normalized_missing in available_names:
        return normalized_missing

    missing_family = techset_family(normalized_missing)
    ranked: List[Tuple[int, int, str]] = []
    for candidate in available_names:
        candidate_family = techset_family(candidate)
        score = longest_token_prefix_score(missing_family, candidate_family)
        if candidate_family.startswith(missing_family) or missing_family.startswith(candidate_family):
            score += 2
        ranked.append((score, -len(candidate_family), candidate))
    ranked.sort(reverse=True)
    best_score, _, best_name = ranked[0]
    return best_name if best_score > 0 else ""


def rewrite_material_techsets(
    project_zone_root: Path,
    missing_techset_names: Sequence[str],
) -> List[Dict[str, str]]:
    targets = {name.strip().lower() for name in missing_techset_names if name.strip()}
    if not targets:
        return []

    materials_root = project_zone_root / "materials"
    if not materials_root.exists():
        return []

    available_techsets = load_techset_names(project_zone_root)
    if not available_techsets:
        return []

    rewrites: List[Dict[str, str]] = []
    for material_json in materials_root.rglob("*.json"):
        try:
            payload = json.loads(material_json.read_text(encoding="utf-8"))
        except Exception:
            continue
        old = str(payload.get("techniqueSet", "")).strip().lower()
        if old not in targets:
            continue
        fallback = choose_techset_fallback(old, available_techsets)
        if not fallback or fallback == old:
            continue
        payload["techniqueSet"] = fallback
        material_json.write_text(json.dumps(payload, indent=4) + "\n", encoding="utf-8")
        material_asset = material_json.relative_to(materials_root).with_suffix("").as_posix()
        rewrites.append(
            {
                "material": material_asset,
                "old_techset": old,
                "new_techset": fallback,
                "file": str(material_json),
            }
        )
    return rewrites


def extract_family_prefix(value: str) -> str:
    base = value.strip().replace("\\", "/").strip("/")
    if not base:
        return ""
    tail = Path(base).stem.lower()
    family = TRAILING_INDEX_RE.sub("", tail)
    if family == tail:
        return ""
    return family


def prune_related_xmodels(zone_path: Path, failed_xmodels: Sequence[str]) -> List[Dict[str, str]]:
    prefixes = {extract_family_prefix(name) for name in failed_xmodels}
    prefixes = {prefix for prefix in prefixes if prefix}
    if not prefixes:
        return []

    lines = zone_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    removed: List[Dict[str, str]] = []
    kept: List[str] = []
    for raw in lines:
        line = raw.strip()
        if line and not line.startswith("//") and not line.startswith(">"):
            token = line.split(",", 1)[0].strip().lower()
            name = line.split(",", 1)[1].strip() if "," in line else ""
            if token in {"xmodel", "xmodelalias"}:
                model_name = Path(name.strip().replace("\\", "/")).stem.lower()
                if any(model_name.startswith(prefix + "_") for prefix in prefixes):
                    removed.append({"asset_type": token, "asset_name": name})
                    continue
        kept.append(raw)
    if removed:
        zone_path.write_text("\n".join(kept).rstrip() + "\n", encoding="utf-8")
    return removed


def normalize_material_family(value: str) -> List[str]:
    raw = value.strip().replace("\\", "/").strip("/")
    if not raw:
        return []
    stem = Path(raw).stem.lower()
    if stem.startswith("mtl_"):
        stem = stem[4:]
    keys = [stem]
    trimmed = MATERIAL_VARIANT_SUFFIX_RE.sub("", stem)
    keys.append(trimmed)
    keys.append(TRAILING_INDEX_RE.sub("", trimmed))
    out: List[str] = []
    seen = set()
    for key in keys:
        token = key.strip("_")
        if len(token) < 6 or token in seen:
            continue
        seen.add(token)
        out.append(token)
    return out


def prune_related_material_chain(zone_path: Path, failed_materials: Sequence[str]) -> List[Dict[str, str]]:
    families = {item for name in failed_materials for item in normalize_material_family(name)}
    if not families:
        return []

    lines = zone_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    removed: List[Dict[str, str]] = []
    kept: List[str] = []
    for raw in lines:
        line = raw.strip()
        if line and not line.startswith("//") and not line.startswith(">"):
            token = line.split(",", 1)[0].strip().lower()
            name = line.split(",", 1)[1].strip() if "," in line else ""
            stem = Path(name.strip().replace("\\", "/")).stem.lower()
            if token == "material":
                mat_name = stem[4:] if stem.startswith("mtl_") else stem
                if any(mat_name.startswith(family) for family in families):
                    removed.append({"asset_type": token, "asset_name": name})
                    continue
            if token in {"xmodel", "xmodelalias"}:
                if any(stem.startswith(family) for family in families):
                    removed.append({"asset_type": token, "asset_name": name})
                    continue
        kept.append(raw)
    if removed:
        zone_path.write_text("\n".join(kept).rstrip() + "\n", encoding="utf-8")
    return removed


def zone_asset_from_file(project_zone_root: Path, file_path: Path) -> Tuple[str, str]:
    rel = file_path.relative_to(project_zone_root)
    if len(rel.parts) < 2:
        return ("", "")
    root_dir = rel.parts[0].lower()
    asset_type = DIR_TO_ASSET_TYPE.get(root_dir, "")
    if not asset_type:
        return ("", "")
    asset_rel = Path(*rel.parts[1:]).with_suffix("").as_posix()
    if not asset_rel:
        return ("", "")
    if asset_type == "material" and "/" in asset_rel and not asset_rel.startswith(("mc/", "mlv/")):
        material_family = rel.parts[1].lower()
        if material_family in {"mc", "mlv"}:
            asset_rel = f"{material_family}/{Path(*rel.parts[2:]).with_suffix('').as_posix()}"
    return (asset_type, asset_rel)


def find_referrer_assets(project_zone_root: Path, unresolved_names: Sequence[str]) -> List[Tuple[str, str]]:
    needles = sorted(
        {
            needle.strip().lower()
            for unresolved in unresolved_names
            for needle in asset_name_variants(unresolved)
            if needle.strip()
        },
        key=len,
        reverse=True,
    )
    if not needles:
        return []

    refs: List[Tuple[str, str]] = []
    seen = set()
    for file_path in project_zone_root.rglob("*"):
        if not file_path.is_file() or file_path.suffix.lower() not in TEXT_SCAN_EXTENSIONS:
            continue
        try:
            text = file_path.read_text(encoding="utf-8", errors="ignore").lower()
        except Exception:
            continue
        if not any(needle in text for needle in needles):
            continue
        asset_type, asset_name = zone_asset_from_file(project_zone_root, file_path)
        if not asset_type or not asset_name:
            continue
        key = (asset_name.lower(), asset_type.lower())
        if key in seen:
            continue
        seen.add(key)
        refs.append((asset_name, asset_type))
    return refs


def choose_donor_image(dependency_roots: Sequence[Path]) -> Path:
    candidates: List[Tuple[int, Path]] = []
    for root in dependency_roots:
        if not root.exists():
            continue
        for images_root in root.rglob("images"):
            if not images_root.is_dir():
                continue
            for image_path in images_root.rglob("*.dds"):
                stem = image_path.stem.lower()
                score = 0
                if any(token in stem for token in PREFERRED_DONOR_IMAGE_TOKENS):
                    score += 10
                if "nml" in stem or "normal" in stem:
                    score += 3
                score -= len(stem) // 40
                candidates.append((score, image_path))
    if not candidates:
        raise FileNotFoundError("No donor .dds found under dependency roots images folders.")
    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


def stage_placeholder_images(
    missing_assets: Sequence[Tuple[str, str]],
    dependency_roots: Sequence[Path],
    project_zone_root: Path,
) -> List[Dict[str, Any]]:
    missing_images = [name for name, kind in missing_assets if kind == "image" and name.strip()]
    if not missing_images:
        return []

    images_root = project_zone_root / "images"
    images_root.mkdir(parents=True, exist_ok=True)
    try:
        donor = choose_donor_image(dependency_roots)
    except Exception:
        return []

    staged: List[Dict[str, Any]] = []
    for image_name in missing_images:
        normalized = image_name.strip().replace("\\", "/").strip("/")
        if not normalized:
            continue
        rel = Path(normalized + ".dds")
        dst = images_root / rel
        if dst.exists():
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(donor.read_bytes())
        staged.append(
            {
                "asset_name": normalized,
                "asset_type": "image",
                "source": str(donor),
                "destination": str(dst),
                "copied": True,
                "source_zone": "",
                "placeholder": True,
            }
        )
    return staged


def list_project_images(project_zone_root: Path) -> List[str]:
    images_root = project_zone_root / "images"
    if not images_root.exists():
        return []
    out: set[str] = set()
    for image_path in images_root.rglob("*.dds"):
        rel = image_path.relative_to(images_root).with_suffix("").as_posix().lower()
        out.add(rel)
        out.add(Path(rel).name)
    return sorted(name for name in out if name)


def choose_image_fallback(missing_image: str, available_images: Sequence[str]) -> str:
    if not available_images:
        return ""
    missing = missing_image.strip().lower()
    for preferred in PREFERRED_IMAGE_FALLBACKS:
        if preferred in available_images:
            return preferred
    ranked: List[Tuple[int, str]] = []
    for candidate in available_images:
        score = 0
        if "gradient" in candidate:
            score += 10
        if "white" in candidate or "default" in candidate:
            score += 7
        if "normal" in candidate or "nml" in candidate:
            score += 3
        if "radiant" in missing and "radiant" in candidate:
            score += 6
        score -= len(candidate) // 30
        ranked.append((score, candidate))
    ranked.sort(reverse=True)
    return ranked[0][1]


def rewrite_material_missing_images(
    project_zone_root: Path,
    missing_image_names: Sequence[str],
) -> List[Dict[str, str]]:
    targets = {name.strip().lower() for name in missing_image_names if name.strip()}
    if not targets:
        return []
    materials_root = project_zone_root / "materials"
    if not materials_root.exists():
        return []
    available_images = list_project_images(project_zone_root)
    if not available_images:
        return []

    rewrites: List[Dict[str, str]] = []
    for material_json in materials_root.rglob("*.json"):
        try:
            payload = json.loads(material_json.read_text(encoding="utf-8"))
        except Exception:
            continue
        textures = payload.get("textures", [])
        if not isinstance(textures, list):
            continue
        changed = False
        for texture in textures:
            if not isinstance(texture, dict):
                continue
            image_name = str(texture.get("image", "")).strip().lower()
            if image_name not in targets:
                continue
            fallback = choose_image_fallback(image_name, available_images)
            if not fallback or fallback == image_name:
                continue
            texture["image"] = fallback
            rewrites.append(
                {
                    "material": material_json.relative_to(materials_root).with_suffix("").as_posix(),
                    "old_image": image_name,
                    "new_image": fallback,
                    "file": str(material_json),
                }
            )
            changed = True
        if changed:
            material_json.write_text(json.dumps(payload, indent=4) + "\n", encoding="utf-8")
    return rewrites


def prune_zone_asset_lines(zone_path: Path, assets: Sequence[Tuple[str, str]]) -> List[Dict[str, str]]:
    if not assets:
        return []
    lines = zone_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    targets_by_token: Dict[str, set[str]] = {}
    for asset_name, asset_type in assets:
        token = zone_token(asset_type)
        if not token or not asset_name:
            continue
        variants = asset_name_variants(asset_name)
        tokens = [token]
        if token == "xmodel":
            tokens.append("xmodelalias")
        if token == "xanim":
            tokens.append("xanimparts")
        for target_token in tokens:
            bucket = targets_by_token.setdefault(target_token, set())
            for variant in variants:
                bucket.add(variant)

    removed: List[Dict[str, str]] = []
    kept: List[str] = []
    for raw in lines:
        line = raw.strip()
        if line and not line.startswith("//") and not line.startswith(">"):
            token = line.split(",", 1)[0].strip().lower()
            name = line.split(",", 1)[1].strip() if "," in line else ""
            target_names = targets_by_token.get(token, set())
            if target_names:
                line_variants = set(asset_name_variants(name))
                if line_variants.intersection(target_names):
                    removed.append({"asset_type": token, "asset_name": name})
                    continue
        kept.append(raw)
    if removed:
        zone_path.write_text("\n".join(kept).rstrip() + "\n", encoding="utf-8")
    return removed


def prune_materials_by_techniqueset(
    project_zone_root: Path,
    zone_path: Path,
    techniqueset_names: Sequence[str],
) -> List[Dict[str, str]]:
    targets = {name.strip().lower() for name in techniqueset_names if name.strip()}
    if not targets:
        return []

    materials_root = project_zone_root / "materials"
    if not materials_root.exists():
        return []

    material_assets: List[Tuple[str, str]] = []
    for material_json in materials_root.rglob("*.json"):
        try:
            payload = json.loads(material_json.read_text(encoding="utf-8"))
        except Exception:
            continue
        technique_set = str(payload.get("techniqueSet", "")).strip().lower()
        if technique_set not in targets:
            continue

        rel = material_json.relative_to(materials_root).with_suffix("").as_posix()
        material_assets.append((rel, "material"))

    if not material_assets:
        return []
    return prune_zone_asset_lines(zone_path, material_assets)


def resolve_paths(items: List[str], base: Path) -> List[Path]:
    out: List[Path] = []
    for item in items:
        path = Path(item)
        if not path.is_absolute():
            path = (base / path).resolve()
        out.append(path)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Run linker remediation loop for map bootstrap project.")
    parser.add_argument("--project-root", required=True, help="Path to bootstrap project root.")
    parser.add_argument("--project-name", default="", help="Project/map name (defaults to project-root folder name).")
    parser.add_argument("--linker", default="tools/oat/Linker.exe", help="Path to Linker.exe")
    parser.add_argument(
        "--load-zones",
        nargs="*",
        default=["zone/all/common_zm.ff"],
        help="Base preload zones (supports semicolon-separated values).",
    )
    parser.add_argument(
        "--dependency-roots",
        nargs="*",
        default=["zone_dump/zone_raw", "_build/t6_asset_dump/zone_raw"],
        help="Roots scanned for missing assets (supports semicolon-separated values).",
    )
    parser.add_argument("--max-retries", type=int, default=8, help="Max retries for missing-asset remediation.")
    parser.add_argument("--prune-unresolved", action="store_true", help="Prune unresolved asset lines from zone when staging cannot fix them.")
    parser.add_argument(
        "--no-techset-fallback",
        action="store_true",
        help="Disable material techniqueset fallback rewrites when techniquesets are missing.",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose linker output.")
    parser.add_argument(
        "--output",
        default="_build/asset_port_pipeline/map_project_remediation_report.json",
        help="Output report path.",
    )
    args = parser.parse_args()

    repo_root = Path.cwd().resolve()

    project_root = Path(args.project_root)
    if not project_root.is_absolute():
        project_root = (repo_root / project_root).resolve()
    if not project_root.exists():
        raise FileNotFoundError(f"project-root not found: {project_root}")

    project_name = sanitize_name(args.project_name or project_root.name)
    zone_path = project_root / "zone_source" / f"{project_name}.zone"
    project_zone_root = project_root / "zone_raw" / project_name
    if not zone_path.exists():
        raise FileNotFoundError(f"Zone file not found: {zone_path}")
    if not project_zone_root.exists():
        raise FileNotFoundError(f"Project zone_raw root not found: {project_zone_root}")

    linker_path = Path(args.linker)
    if not linker_path.is_absolute():
        linker_path = (repo_root / linker_path).resolve()
    if not linker_path.exists():
        raise FileNotFoundError(f"Linker not found: {linker_path}")

    load_zone_items = parse_load_zones(args.load_zones)
    active_load_zones = resolve_paths(load_zone_items, base=repo_root)
    for path in active_load_zones:
        if not path.exists():
            raise FileNotFoundError(f"Missing load zone: {path}")

    dependency_root_items = parse_load_zones(args.dependency_roots)
    dependency_roots = [path for path in resolve_paths(dependency_root_items, base=repo_root) if path.exists()]
    if not dependency_roots:
        raise FileNotFoundError("No dependency roots found.")

    output_folder = project_root.parent / f"{project_name}_out"
    output_folder.mkdir(parents=True, exist_ok=True)

    attempts: List[Dict[str, Any]] = []
    max_attempts = max(1, int(args.max_retries) + 1)
    hard_attempt_limit = max_attempts + max(64, int(args.max_retries) * 6)

    for attempt in range(1, hard_attempt_limit + 1):
        result = run_linker(
            linker_path=linker_path,
            project_name=project_name,
            base_folder=project_root,
            output_folder=output_folder,
            load_zones=active_load_zones,
            verbose=args.verbose,
        )
        result["attempt"] = attempt
        result["load_zones_used"] = [str(path) for path in active_load_zones]
        missing_assets = dedupe_assets(extract_missing_assets(result.get("log", "")))
        unresolved_assets = dedupe_assets(extract_unresolved_assets(result.get("log", "")))
        result["missing_assets"] = [{"asset_name": name, "asset_type": asset_type} for name, asset_type in missing_assets]
        result["unresolved_assets"] = [{"asset_name": name, "asset_type": asset_type} for name, asset_type in unresolved_assets]

        staged = []
        staged_copied: List[Dict[str, Any]] = []
        added_loads: List[Path] = []
        pruned: List[Dict[str, str]] = []
        rewrites: List[Dict[str, str]] = []
        image_rewrites: List[Dict[str, str]] = []
        can_retry = attempt < hard_attempt_limit
        stage_candidates = stageable_assets([*missing_assets, *unresolved_assets])
        if result["status"] == "fail" and can_retry and stage_candidates:
            staged = stage_missing_assets(
                missing_assets=stage_candidates,
                dependency_roots=dependency_roots,
                project_zone_root=project_zone_root,
            )
            if missing_assets:
                placeholders = stage_placeholder_images(
                    missing_assets=missing_assets,
                    dependency_roots=dependency_roots,
                    project_zone_root=project_zone_root,
                )
                if placeholders:
                    staged.extend(placeholders)
            staged_copied = [item for item in staged if bool(item.get("copied"))]
            append_zone_asset_lines(zone_path, staged_copied)
            added_loads = infer_dependency_load_zones(staged_dependencies=staged_copied, active_load_zones=active_load_zones)
            active_load_zones.extend(added_loads)
            missing_techsets = [name for name, kind in missing_assets if kind in {"techniqueset", "techset"}]
            if missing_techsets and not args.no_techset_fallback:
                rewrites = rewrite_material_techsets(project_zone_root, missing_techsets)
                if rewrites:
                    append_zone_asset_lines(
                        zone_path,
                        [{"asset_type": "material", "asset_name": row["material"]} for row in rewrites],
                    )
            missing_images = [name for name, kind in missing_assets if kind == "image"]
            if missing_images:
                image_rewrites = rewrite_material_missing_images(project_zone_root, missing_images)
                if image_rewrites:
                    append_zone_asset_lines(
                        zone_path,
                        [{"asset_type": "material", "asset_name": row["material"]} for row in image_rewrites],
                    )
            if args.prune_unresolved and not staged_copied and not added_loads and not rewrites and not image_rewrites:
                pruned = prune_zone_asset_lines(zone_path, unresolved_assets)
                pruned.extend(prune_zone_asset_lines(zone_path, missing_assets))
                pruned.extend(prune_materials_by_techniqueset(project_zone_root, zone_path, missing_techsets))
                pruned.extend(
                    prune_related_material_chain(
                        zone_path,
                        [name for name, kind in unresolved_assets if kind == "material"],
                    )
                )
                pruned.extend(
                    prune_related_xmodels(
                        zone_path,
                        [name for name, kind in unresolved_assets if kind in {"xmodel", "xmodelalias"}],
                    )
                )
                referrers = find_referrer_assets(
                    project_zone_root,
                    [name for name, _ in unresolved_assets] + [name for name, _ in missing_assets],
                )
                if referrers:
                    pruned.extend(prune_zone_asset_lines(zone_path, referrers))
        elif result["status"] == "fail" and can_retry and args.prune_unresolved:
            pruned = prune_zone_asset_lines(zone_path, unresolved_assets)
            pruned.extend(prune_zone_asset_lines(zone_path, missing_assets))
            pruned.extend(
                prune_related_material_chain(
                    zone_path,
                    [name for name, kind in unresolved_assets if kind == "material"],
                )
            )
            pruned.extend(
                prune_related_xmodels(
                    zone_path,
                    [name for name, kind in unresolved_assets if kind in {"xmodel", "xmodelalias"}],
                )
            )
            referrers = find_referrer_assets(
                project_zone_root,
                [name for name, _ in unresolved_assets] + [name for name, _ in missing_assets],
            )
            if referrers:
                pruned.extend(prune_zone_asset_lines(zone_path, referrers))

        # Stage accuracy graph files from warnings (runs on every attempt, pass or fail).
        stage_accuracy_graphs(
            log_text=result.get("log", ""),
            dependency_roots=dependency_roots,
            project_zone_root=project_zone_root,
        )

        result["staged_dependencies"] = staged
        result["staged_dependencies_copied"] = staged_copied
        result["added_load_zones"] = [str(path) for path in added_loads]
        result["pruned_zone_assets"] = pruned
        result["rewritten_material_techsets"] = rewrites
        result["rewritten_material_images"] = image_rewrites
        attempts.append(result)

        if result["status"] == "pass":
            break
        if attempt >= max_attempts and not (staged_copied or added_loads or rewrites or image_rewrites or pruned):
            break
        if not (can_retry and (staged_copied or added_loads or rewrites or image_rewrites or pruned)):
            break

    report = {
        "generated_at_utc": dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "project_root": str(project_root),
        "project_name": project_name,
        "zone_file": str(zone_path),
        "output_folder": str(output_folder),
        "linker": str(linker_path),
        "dependency_roots": [str(path) for path in dependency_roots],
        "load_zones_final": [str(path) for path in active_load_zones],
        "attempts": attempts,
        "final": attempts[-1] if attempts else {},
    }

    output = Path(args.output)
    if not output.is_absolute():
        output = (repo_root / output).resolve()
    save_json(output, report)

    final = report["final"] if report["final"] else {"status": "error", "exit_code": -1, "errors": []}
    print(f"Saved map project remediation report: {output}")
    print(
        f"status={final.get('status', 'error')} "
        f"exit_code={final.get('exit_code', -1)} "
        f"errors={len(final.get('errors', []))} "
        f"attempts={len(attempts)}"
    )


if __name__ == "__main__":
    main()
