from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple


def resolve_path(path_value: str, repo_root: Path) -> Path:
    path = Path(path_value)
    if not path.is_absolute():
        path = (repo_root / path).resolve()
    return path


def sanitize_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_]+", "_", value).strip("_").lower()
    return cleaned or "material_auto"


def normalize_material_asset_name(value: str) -> str:
    raw = value.strip().replace("\\", "/").strip("/")
    if not raw:
        return ""
    raw = raw.rsplit(".", 1)[0]
    if raw.startswith("materials/"):
        raw = raw[len("materials/") :]
    if "/" not in raw and raw.startswith("mc_"):
        # Preserve legacy mc-prefixed ids as folder-form ids.
        raw = f"mc/{raw[3:]}"
    return raw


def choose_techset(material_name: str, default_techset: str, unlit_techset: str) -> str:
    lower = material_name.lower()
    if any(token in lower for token in ("unlit", "_ui", "hud", "scope", "reticle")):
        return unlit_techset
    return default_techset


def build_material_payload(material_name: str, techset_name: str, textures: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "$schema": "http://openassettools.dev/schema/material.v1.json",
        "_game": "t6",
        "_type": "material",
        "_version": 1,
        "cameraRegion": "none",
        "constants": [],
        "contents": 1,
        "gameFlags": [],
        "layeredSurfaceTypes": 0,
        "sortKey": 0,
        "stateBits": [],
        "stateBitsEntry": [-1] * 36,
        "stateFlags": 0,
        "surfaceFlags": 0,
        "surfaceTypeBits": 0,
        "techniqueSet": techset_name,
        "textureAtlas": {"columns": 1, "rows": 1},
        "textures": list(textures),
        "debugName": material_name,
    }


def collect_material_names(blender_report_path: Path) -> List[str]:
    payload = json.loads(blender_report_path.read_text(encoding="utf-8"))
    rows = payload.get("rows", [])
    names: List[str] = []
    seen = set()
    for row in rows:
        if row.get("status") != "ok":
            continue
        metadata = row.get("metadata") or {}
        for raw_name in metadata.get("material_names") or []:
            normalized = normalize_material_asset_name(str(raw_name))
            if not normalized:
                continue
            key = normalized.lower()
            if key in seen:
                continue
            seen.add(key)
            names.append(normalized)
    return sorted(names)


def normalize_ref(value: str) -> str:
    normalized = str(value).strip().replace("\\", "/")
    normalized = re.sub(r"/+", "/", normalized)
    return normalized.lstrip("/")


def parse_bool_flag(value: str) -> bool:
    lowered = str(value).strip().lower()
    return lowered in {"1", "true", "yes", "on", "enabled", "enable"}


def choose_texture_slot(material_props: Dict[str, Any]) -> Dict[str, str]:
    picks: Dict[str, str] = {}
    slot_candidates = {
        "colorMap": ("colorMap", "baseColorMap", "colorMap00"),
        "normalMap": ("normalMap", "normalDetailMap", "colorMap01"),
        "specularMap": ("specColorMap", "specMap", "cosinePowerMap"),
        "occlusionMap": ("occlusionMap", "aoMap", "colorMap03"),
        "revealMap": ("revealMap", "alphaRevealMap", "camoMaskMap"),
        "alphaMap": ("alphaMap", "opacityMap"),
    }
    for slot, keys in slot_candidates.items():
        for key in keys:
            raw = str(material_props.get(key, "")).strip()
            if not raw:
                continue
            if raw.startswith("$"):
                continue
            picks[slot] = raw
            break
    return picks


def resolve_bundle_context(bundle_report_path: Path) -> Dict[str, Any]:
    if not bundle_report_path.exists():
        return {}
    payload = json.loads(bundle_report_path.read_text(encoding="utf-8"))
    bundle_root = Path(str(payload.get("output_root", bundle_report_path.parent)))
    manifest_dir = bundle_root / "manifests"
    staged_root = bundle_root / "staged"
    out: Dict[str, Any] = {
        "bundle_root": bundle_root,
        "manifest_dir": manifest_dir,
        "staged_root": staged_root,
        "bundle_report": payload,
    }

    materials_manifest = manifest_dir / "materials.json"
    images_manifest = manifest_dir / "images.json"
    out["materials_manifest"] = materials_manifest
    out["images_manifest"] = images_manifest
    if materials_manifest.exists():
        out["materials_entries"] = json.loads(materials_manifest.read_text(encoding="utf-8"))
    else:
        out["materials_entries"] = []
    if images_manifest.exists():
        out["images_entries"] = json.loads(images_manifest.read_text(encoding="utf-8"))
    else:
        out["images_entries"] = []

    copied_by_rel: Dict[str, Path] = {}
    copied_by_name: Dict[str, Path] = {}
    for item in payload.get("copied_files", []):
        rel = normalize_ref(str(item.get("relative", "")))
        dst = Path(str(item.get("destination", "")))
        if rel and dst.exists():
            copied_by_rel[rel.lower()] = dst
            copied_by_name.setdefault(dst.name.lower(), dst)
    out["copied_by_rel"] = copied_by_rel
    out["copied_by_name"] = copied_by_name
    return out


def resolve_image_source(base_image: str, bundle_ctx: Dict[str, Any]) -> Path | None:
    if not base_image:
        return None
    normalized = normalize_ref(base_image)
    staged_root: Path = bundle_ctx.get("staged_root", Path(""))
    candidate = staged_root / normalized
    if candidate.exists():
        return candidate

    copied_by_rel: Dict[str, Path] = bundle_ctx.get("copied_by_rel", {})
    found = copied_by_rel.get(normalized.lower())
    if found and found.exists():
        return found

    copied_by_name: Dict[str, Path] = bundle_ctx.get("copied_by_name", {})
    by_name = copied_by_name.get(Path(normalized).name.lower())
    if by_name and by_name.exists():
        return by_name
    return None


def map_images(bundle_ctx: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    image_entries = bundle_ctx.get("images_entries", [])
    out: Dict[str, Dict[str, Any]] = {}
    for entry in image_entries:
        name = str(entry.get("name", "")).strip()
        if not name:
            continue
        props = entry.get("props", {}) if isinstance(entry.get("props"), dict) else {}
        base_image = str(props.get("baseImage", "")).strip()
        source = resolve_image_source(base_image=base_image, bundle_ctx=bundle_ctx)
        out[name] = {
            "name": name,
            "props": props,
            "base_image": base_image,
            "source": source,
        }
    return out


def map_materials(bundle_ctx: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    entries = bundle_ctx.get("materials_entries", [])
    out: Dict[str, Dict[str, Any]] = {}
    for entry in entries:
        name = normalize_material_asset_name(str(entry.get("name", "")))
        if not name:
            continue
        props = entry.get("props", {}) if isinstance(entry.get("props"), dict) else {}
        out[name.lower()] = {"name": name, "props": props}
    return out


def make_sampler_state(image_props: Dict[str, Any]) -> Dict[str, Any]:
    no_mips = parse_bool_flag(image_props.get("noMipMaps", "0"))
    clamp_u = parse_bool_flag(image_props.get("clampU", "0"))
    clamp_v = parse_bool_flag(image_props.get("clampV", "0"))
    return {
        "clampU": bool(clamp_u),
        "clampV": bool(clamp_v),
        "clampW": False,
        "filter": "aniso4x" if not no_mips else "linear",
        "mipMap": "disabled" if no_mips else "linear",
    }


def semantic_for_slot(slot: str, image_props: Dict[str, Any]) -> str:
    image_semantic = str(image_props.get("semantic", "")).strip()
    if image_semantic:
        lowered = image_semantic.lower()
        if lowered in {"diffusemap", "colormap", "normalmap", "specularmap", "occlusionmap", "revealmap", "alphamap"}:
            if lowered == "diffusemap":
                return "colorMap"
            return image_semantic
    mapping = {
        "colorMap": "colorMap",
        "normalMap": "normalMap",
        "specularMap": "specularMap",
        "occlusionMap": "occlusionMap",
        "revealMap": "revealMap",
        "alphaMap": "alphaMap",
    }
    return mapping.get(slot, "2D")


def choose_techset_for_material(
    material_name: str,
    texture_slots: Dict[str, str],
    default_techset: str,
    unlit_techset: str,
    lit_techset: str,
) -> str:
    lower = material_name.lower()
    if any(token in lower for token in ("unlit", "_ui", "hud", "scope", "reticle", "_glo", "_glow")):
        return unlit_techset
    has_color = "colorMap" in texture_slots
    has_lit_detail = any(slot in texture_slots for slot in ("normalMap", "specularMap", "occlusionMap"))
    if has_color and has_lit_detail:
        return lit_techset
    return choose_techset(material_name=material_name, default_techset=default_techset, unlit_techset=unlit_techset)


def _convert_to_iwi(
    source_path: Path,
    image_name: str,
    zone_raw_root: Path,
    image_converter: Path,
    texconv_path: Path,
) -> Path:
    image_name_clean = image_name.strip().replace("\\", "/").split("/")[-1]
    images_root = zone_raw_root / "images"
    images_root.mkdir(parents=True, exist_ok=True)
    iwi_dst = images_root / f"{image_name_clean}.iwi"
    if iwi_dst.exists():
        return iwi_dst

    if source_path.suffix.lower() == ".iwi":
        shutil.copy2(source_path, iwi_dst)
        return iwi_dst

    tmp_root = zone_raw_root / "_tmp_image_convert"
    tmp_root.mkdir(parents=True, exist_ok=True)
    dds_tmp = tmp_root / f"{image_name_clean}.dds"

    if source_path.suffix.lower() == ".dds":
        shutil.copy2(source_path, dds_tmp)
    else:
        if not texconv_path.exists():
            raise FileNotFoundError(f"texconv not found: {texconv_path}")
        source_tmp = tmp_root / f"{image_name_clean}{source_path.suffix.lower()}"
        shutil.copy2(source_path, source_tmp)
        proc_texconv = subprocess.run(
            [str(texconv_path), "-y", "-f", "DXT5", "-o", str(tmp_root), str(source_tmp)],
            capture_output=True,
            check=False,
            text=True,
        )
        if proc_texconv.returncode != 0 or not dds_tmp.exists():
            raise RuntimeError(
                "texconv failed for image "
                f"{image_name_clean} (source={source_path}). "
                f"stdout={proc_texconv.stdout[:300]} stderr={proc_texconv.stderr[:300]}"
            )

    proc = subprocess.run(
        [str(image_converter), str(dds_tmp)],
        input=b"5\n",
        capture_output=True,
        check=False,
    )
    iwi_tmp = dds_tmp.with_suffix(".iwi")
    if proc.returncode != 0 or not iwi_tmp.exists():
        err = proc.stderr.decode(errors="replace") if isinstance(proc.stderr, (bytes, bytearray)) else str(proc.stderr)
        out = proc.stdout.decode(errors="replace") if isinstance(proc.stdout, (bytes, bytearray)) else str(proc.stdout)
        raise RuntimeError(
            "ImageConverter failed for image "
            f"{image_name_clean} (source={source_path}). stdout={out[:300]} stderr={err[:300]}"
        )

    shutil.copy2(iwi_tmp, iwi_dst)
    return iwi_dst


def stage_image_asset(
    zone_raw_root: Path,
    image_name: str,
    image_info: Dict[str, Any],
    stage_as_iwi: bool,
    image_converter: Path,
    texconv_path: Path,
) -> Dict[str, Any] | None:
    source = image_info.get("source")
    if not source or not Path(source).exists():
        return None
    source_path = Path(source)
    if stage_as_iwi:
        dst = _convert_to_iwi(
            source_path=source_path,
            image_name=image_name,
            zone_raw_root=zone_raw_root,
            image_converter=image_converter,
            texconv_path=texconv_path,
        )
    else:
        ext = source_path.suffix.lower() or ".png"
        dst = zone_raw_root / "images" / f"{image_name}{ext}"
        dst.parent.mkdir(parents=True, exist_ok=True)
        if not dst.exists():
            shutil.copy2(source_path, dst)
    return {
        "image": image_name,
        "source": str(source_path),
        "destination": str(dst),
        "semantic": str((image_info.get("props") or {}).get("semantic", "")).strip(),
    }


def append_zone_lines(zone_file: Path, lines_to_add: Sequence[str]) -> int:
    if not lines_to_add:
        return 0
    lines = zone_file.read_text(encoding="utf-8", errors="ignore").splitlines() if zone_file.exists() else []
    seen = {line.strip().lower() for line in lines if line.strip()}
    appended = 0
    for line in lines_to_add:
        key = line.strip().lower()
        if key and key not in seen:
            seen.add(key)
            lines.append(line)
            appended += 1
    zone_file.parent.mkdir(parents=True, exist_ok=True)
    zone_file.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return appended


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate BO2-compatible material descriptors from converted BO3 metadata.")
    parser.add_argument("--project-root", required=True, help="Integration project root (contains zone_raw/<project>).")
    parser.add_argument("--project-name", required=True, help="Integration project name.")
    parser.add_argument("--blender-report", required=True, help="blender_convert report JSON path.")
    parser.add_argument("--default-techset", default="mc_lit_sm_b0c0_fw0jf955", help="Default BO2 techniqueset name.")
    parser.add_argument(
        "--lit-techset",
        default="mc_lit_sm_b0c0_fw0jf955",
        help="BO2 lit techniqueset name used when color+normal/spec/occlusion maps are available.",
    )
    parser.add_argument(
        "--unlit-techset",
        default="mc_lit_sm_b0c0_fw0jf955",
        help="BO2 techniqueset used for unlit/UI-like materials.",
    )
    parser.add_argument(
        "--bundle-report",
        default="",
        help="Optional transfer/t7_bundle_report.json for manifest-driven image/material mapping.",
    )
    parser.add_argument(
        "--stage-images",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Copy resolved image files into zone_raw/images and add image lines.",
    )
    parser.add_argument(
        "--stage-images-as-iwi",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Convert staged textures to T6 .iwi via ImageConverter (recommended for linker compatibility).",
    )
    parser.add_argument(
        "--image-converter",
        default="tools/oat/ImageConverter.exe",
        help="Path to OAT ImageConverter executable used when --stage-images-as-iwi is enabled.",
    )
    parser.add_argument(
        "--texconv",
        default="tools/texconv.exe",
        help="Path to texconv executable used to convert non-DDS textures before IWI conversion.",
    )
    parser.add_argument("--append-zone-lines", action="store_true", help="Append generated materials to zone source.")
    parser.add_argument(
        "--report",
        default="_build/asset_port_pipeline/material_translation_report.json",
        help="Output report JSON path.",
    )
    args = parser.parse_args()

    repo_root = Path.cwd().resolve()
    project_root = resolve_path(args.project_root, repo_root)
    blender_report = resolve_path(args.blender_report, repo_root)
    report_path = resolve_path(args.report, repo_root)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    image_converter = resolve_path(args.image_converter, repo_root)
    texconv_path = resolve_path(args.texconv, repo_root)
    if args.stage_images and args.stage_images_as_iwi and not image_converter.exists():
        raise FileNotFoundError(f"ImageConverter not found: {image_converter}")

    project_name = sanitize_name(args.project_name)
    zone_raw_root = project_root / "zone_raw" / project_name
    materials_root = zone_raw_root / "materials"
    zone_file = project_root / "zone_source" / f"{project_name}.zone"
    materials_root.mkdir(parents=True, exist_ok=True)
    (zone_raw_root / "images").mkdir(parents=True, exist_ok=True)

    material_names = collect_material_names(blender_report)
    bundle_ctx: Dict[str, Any] = {}
    image_index: Dict[str, Dict[str, Any]] = {}
    material_index: Dict[str, Dict[str, Any]] = {}
    if args.bundle_report:
        bundle_report_path = resolve_path(args.bundle_report, repo_root)
        bundle_ctx = resolve_bundle_context(bundle_report_path=bundle_report_path)
        image_index = map_images(bundle_ctx=bundle_ctx)
        material_index = map_materials(bundle_ctx=bundle_ctx)

    generated: List[Dict[str, str]] = []
    staged_images: List[Dict[str, Any]] = []
    used_image_names: List[str] = []

    for material_name in material_names:
        material_meta = material_index.get(material_name.lower(), {})
        material_props = material_meta.get("props", {}) if isinstance(material_meta.get("props"), dict) else {}
        texture_slots = choose_texture_slot(material_props=material_props)

        textures: List[Dict[str, Any]] = []
        for slot_name, image_name in texture_slots.items():
            image_info = image_index.get(image_name)
            if not image_info:
                continue
            image_props = image_info.get("props", {}) if isinstance(image_info.get("props"), dict) else {}
            if args.stage_images:
                staged = stage_image_asset(
                    zone_raw_root=zone_raw_root,
                    image_name=image_name,
                    image_info=image_info,
                    stage_as_iwi=bool(args.stage_images_as_iwi),
                    image_converter=image_converter,
                    texconv_path=texconv_path,
                )
                if staged:
                    staged_images.append(staged)
                    used_image_names.append(image_name)
            textures.append(
                {
                    "image": image_name,
                    "isMatureContent": parse_bool_flag(image_props.get("matureContent", "0")),
                    "name": slot_name,
                    "samplerState": make_sampler_state(image_props=image_props),
                    "semantic": semantic_for_slot(slot=slot_name, image_props=image_props),
                }
            )

        techset = choose_techset_for_material(
            material_name=material_name,
            texture_slots=texture_slots,
            default_techset=args.default_techset,
            unlit_techset=args.unlit_techset,
            lit_techset=args.lit_techset,
        )
        payload = build_material_payload(material_name=material_name, techset_name=techset, textures=textures)
        dst = materials_root / f"{material_name}.json"
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        generated.append(
            {
                "material": material_name,
                "techset": techset,
                "file": str(dst),
                "texture_slots": sorted(texture_slots.keys()),
                "resolved_textures": len(textures),
            }
        )

    appended_zone_lines = 0
    if args.append_zone_lines and generated:
        zone_lines = [f"material,{item['material']}" for item in generated]
        for image_name in sorted(set(used_image_names)):
            zone_lines.append(f"image,{image_name}")
        appended_zone_lines = append_zone_lines(zone_file=zone_file, lines_to_add=zone_lines)

    report = {
        "generated_at_utc": dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "project_root": str(project_root),
        "project_name": project_name,
        "zone_raw_root": str(zone_raw_root),
        "blender_report": str(blender_report),
        "counts": {
            "material_candidates": len(material_names),
            "generated_materials": len(generated),
            "resolved_material_manifest_entries": len(material_index),
            "resolved_image_manifest_entries": len(image_index),
            "staged_images": len({item["image"] for item in staged_images}),
            "staged_iwi_images": len({item["image"] for item in staged_images if str(item.get("destination", "")).lower().endswith(".iwi")}),
            "zone_lines_appended": int(appended_zone_lines),
        },
        "bundle_report": str(resolve_path(args.bundle_report, repo_root)) if args.bundle_report else "",
        "generated": generated,
        "staged_images": staged_images,
    }
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Saved material translation report: {report_path}")
    print(
        f"generated_materials={len(generated)} "
        f"staged_images={len({item['image'] for item in staged_images})} "
        f"zone_lines_appended={appended_zone_lines}"
    )


if __name__ == "__main__":
    main()
