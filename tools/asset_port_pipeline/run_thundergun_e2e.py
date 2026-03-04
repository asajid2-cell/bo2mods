from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

try:
    from retarget_xanim_exports import parse_xanim_export, write_xanim_export
except Exception:
    parse_xanim_export = None
    write_xanim_export = None


SUPPORTED_MESH_EXTS = {".fbx", ".obj", ".glb", ".gltf", ".dae"}
RESERVED_RUNTIME_ZONE_NAMES = {"mod", "mod_load", "mod_patch"}
DEFAULT_PINNED_TECHSET = "mc_lit_sm_b0c0_fw0jf955"
PINNED_TECHSET_SOURCE_HINTS = [
    "_build/dump_patch_test",
    "_build/runtime_unlink_zm_transit_patch_2",
    "_build/panzer_dump/zm_transit_patch_zoneonly",
]
DEFAULT_REQUIRED_UTILITY_XMODELS = ["viewmodel_hands_no_model"]
DEFAULT_REQUIRED_FALLBACK_MATERIALS = ["mc/mtl_default", "reticle_side_small", "hud_icon_thundergun"]
DEFAULT_WEAPON_HUD_ICON_MATERIAL = "hud_icon_thundergun"
DEFAULT_WEAPON_KILL_ICON_MATERIAL = "hud_icon_thundergun"
UTILITY_XMODEL_SOURCE_HINTS = [
    "_build/dump_patch_test",
    "_build/runtime_unlink_zm_transit_patch_2",
    "_build/panzer_dump/zm_transit_patch_zoneonly",
    "zone_dump/zone_raw/so_zsurvival_zm_transit",
]
RAYGUN_ANIM_RE = re.compile(r"viewmodel_raygun_t6_[A-Za-z0-9_]+")
RAYGUN_TO_THUNDER_ANIM_MAP: List[Tuple[str, str]] = [
    # Keep more specific keys earlier to avoid partial-replace conflicts.
    ("viewmodel_raygun_t6_fire_ads", "vm_thunder_gun_fire_ads"),
    ("viewmodel_raygun_t6_pullout_quick", "vm_thunder_gun_pullout_quick"),
    ("viewmodel_raygun_t6_putaway_quick", "vm_thunder_gun_putaway_quick"),
    ("viewmodel_raygun_t6_crawl_forward", "vm_thunder_gun_crawl_f"),
    ("viewmodel_raygun_t6_crawl_back", "vm_thunder_gun_crawl_b"),
    ("viewmodel_raygun_t6_crawl_right", "vm_thunder_gun_crawl_r"),
    ("viewmodel_raygun_t6_crawl_left", "vm_thunder_gun_crawl_l"),
    ("viewmodel_raygun_t6_crawl_in", "vm_thunder_gun_crawl_in"),
    ("viewmodel_raygun_t6_crawl_out", "vm_thunder_gun_crawl_out"),
    ("viewmodel_raygun_t6_first_raise", "vm_thunder_gun_first_raise"),
    ("viewmodel_raygun_t6_sprint_in", "vm_thunder_gun_sprint_in"),
    ("viewmodel_raygun_t6_sprint_loop", "vm_thunder_gun_sprint_loop"),
    ("viewmodel_raygun_t6_sprint_out", "vm_thunder_gun_sprint_out"),
    ("viewmodel_raygun_t6_ads_up", "vm_thunder_gun_ads_base_up"),
    ("viewmodel_raygun_t6_ads_down", "vm_thunder_gun_ads_base_down"),
    ("viewmodel_raygun_t6_d2p_in", "vm_thunder_gun_slide_in"),
    ("viewmodel_raygun_t6_d2p_loop", "vm_thunder_gun_slide_loop"),
    ("viewmodel_raygun_t6_d2p_out", "vm_thunder_gun_slide_out"),
    ("viewmodel_raygun_t6_idle", "vm_thunder_gun_idle"),
    ("viewmodel_raygun_t6_fire", "vm_thunder_gun_fire"),
    ("viewmodel_raygun_t6_reload", "vm_thunder_gun_reload_empty"),
    ("viewmodel_raygun_t6_pullout", "vm_thunder_gun_pullout"),
    ("viewmodel_raygun_t6_putaway", "vm_thunder_gun_putaway"),
]


def sanitize_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_]+", "_", value).strip("_").lower()
    return cleaned or "asset"


def resolve_path(path_value: str, repo_root: Path) -> Path:
    path = Path(path_value)
    if not path.is_absolute():
        path = (repo_root / path).resolve()
    return path


def parse_csv_names(value: str) -> List[str]:
    out: List[str] = []
    seen = set()
    for raw in str(value).split(","):
        token = raw.strip().replace("\\", "/")
        if not token:
            continue
        key = token.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(token)
    return out


def run_cmd(cmd: Sequence[str], cwd: Path, verbose: bool = False) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(list(cmd), cwd=cwd, capture_output=True, text=True, check=False)
    if verbose:
        print("[cmd]", " ".join(str(item) for item in cmd))
        if proc.stdout:
            print(proc.stdout.rstrip())
        if proc.stderr:
            print(proc.stderr.rstrip())
    return proc


def run_shell(cmd: str, cwd: Path, verbose: bool = False) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False, shell=True)
    if verbose:
        print("[shell]", cmd)
        if proc.stdout:
            print(proc.stdout.rstrip())
        if proc.stderr:
            print(proc.stderr.rstrip())
    return proc


def collect_files(root: Path, exts: Sequence[str]) -> List[Path]:
    allowed = {ext.lower() for ext in exts}
    files = [p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in allowed]
    return sorted(files)


def collect_thundergun_meshes(root: Path) -> List[Path]:
    meshes = collect_files(root, sorted(SUPPORTED_MESH_EXTS))
    out = [p for p in meshes if "thunder" in p.name.lower() and "gun" in p.name.lower()]
    return sorted(out)


def choose_view_world(meshes: Sequence[Path]) -> Tuple[Path, Path]:
    if len(meshes) < 2:
        raise RuntimeError(f"Need at least 2 converted mesh files; found {len(meshes)}")
    view = next((m for m in meshes if "view" in m.name.lower()), None)
    world = next((m for m in meshes if "world" in m.name.lower()), None)
    if view is None:
        view = meshes[0]
    if world is None:
        world = next((m for m in meshes if m != view), meshes[1])
    return view, world


def patch_weapon_model_fields(path: Path, gun_model: str, world_model: str) -> None:
    text = path.read_text(encoding="utf-8", errors="ignore")
    text = re.sub(r"gunModel\\[^\\]*", lambda _: f"gunModel\\{gun_model}", text, count=1)
    text = re.sub(r"worldModel\\[^\\]*", lambda _: f"worldModel\\{world_model}", text, count=1)
    path.write_text(text, encoding="utf-8")


def patch_weapon_anim_fields(path: Path, auto_patch_raygun_anims: bool) -> Dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    original = text
    unresolved_before = sorted(set(RAYGUN_ANIM_RE.findall(text)))
    replacements = 0

    if auto_patch_raygun_anims:
        for old_name, new_name in RAYGUN_TO_THUNDER_ANIM_MAP:
            count = text.count(old_name)
            if count > 0:
                text = text.replace(old_name, new_name)
                replacements += count

    unresolved_after = sorted(set(RAYGUN_ANIM_RE.findall(text)))
    if text != original:
        path.write_text(text, encoding="utf-8")

    return {
        "replacements": int(replacements),
        "changed": bool(text != original),
        "raygun_refs_before": unresolved_before,
        "raygun_refs_after": unresolved_after,
    }


def patch_weapon_icon_fields(path: Path, hud_icon_material: str, kill_icon_material: str) -> Dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    original = text
    hud = str(hud_icon_material).strip()
    kill = str(kill_icon_material).strip()
    hud_replaced = 0
    kill_replaced = 0

    if hud:
        text, hud_replaced = re.subn(
            r"hudIcon\\[^\\]*",
            lambda _: f"hudIcon\\{hud}",
            text,
            count=1,
        )
    if kill:
        text, kill_replaced = re.subn(
            r"killIcon\\[^\\]*",
            lambda _: f"killIcon\\{kill}",
            text,
            count=1,
        )

    if text != original:
        path.write_text(text, encoding="utf-8")
    return {
        "changed": bool(text != original),
        "hud_icon_material": hud,
        "kill_icon_material": kill,
        "hud_replaced": int(hud_replaced),
        "kill_replaced": int(kill_replaced),
    }


def patch_weapon_camo_field(path: Path, camo_name: str) -> Dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    original = text
    camo = str(camo_name).strip()
    replaced = 0
    text, replaced = re.subn(
        r"camo\\[^\\]*",
        lambda _: f"camo\\{camo}" if camo else "camo\\",
        text,
        count=1,
    )
    if text != original:
        path.write_text(text, encoding="utf-8")
    return {
        "changed": bool(text != original),
        "camo_name": camo,
        "camo_replaced": int(replaced),
    }


def write_zone(zone_path: Path, xmodels: Sequence[str], xanims: Sequence[str] | None = None) -> None:
    xanim_lines = sorted(set(xanims or []))
    lines = [
        "// Auto-generated by run_thundergun_e2e.py",
        ">game,T6",
        "",
    ]
    for x in xmodels:
        lines.append(f"xmodel,{x}")
    for x in xanim_lines:
        lines.append(f"xanim,{x}")
    lines.extend(
        [
            "script,maps/mp/zombies/_zm_weap_thundergun.gsc",
            "script,clientscripts/mp/zombies/_zm_weap_thundergun.csc",
            "weapon,thundergun_zm",
            "weapon,thundergun_upgraded_zm",
        ]
    )
    zone_path.parent.mkdir(parents=True, exist_ok=True)
    zone_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def append_unique_zone_lines(zone_path: Path, lines_to_add: Sequence[str]) -> int:
    if not lines_to_add:
        return 0
    lines = zone_path.read_text(encoding="utf-8", errors="ignore").splitlines() if zone_path.exists() else []
    seen = {line.strip().lower() for line in lines if line.strip()}
    appended = 0
    for line in lines_to_add:
        key = line.strip().lower()
        if key and key not in seen:
            lines.append(line)
            seen.add(key)
            appended += 1
    zone_path.parent.mkdir(parents=True, exist_ok=True)
    zone_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return appended


def remove_zone_lines_with_prefix(zone_path: Path, prefixes: Sequence[str]) -> int:
    if not zone_path.exists():
        return 0
    normalized = tuple(p.strip().lower() for p in prefixes if p and p.strip())
    if not normalized:
        return 0
    lines = zone_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    kept: List[str] = []
    removed = 0
    for line in lines:
        token = line.strip().lower()
        if token and any(token.startswith(prefix) for prefix in normalized):
            removed += 1
            continue
        kept.append(line)
    if removed:
        zone_path.write_text("\n".join(kept).rstrip() + "\n", encoding="utf-8")
    return removed


def collect_material_techsets(materials_root: Path) -> Dict[str, Any]:
    techsets: Dict[str, int] = {}
    unreadable: List[str] = []
    if not materials_root.exists():
        return {"counts": techsets, "unreadable": unreadable}
    for mat_file in sorted(materials_root.glob("*.json")):
        try:
            payload = json.loads(mat_file.read_text(encoding="utf-8"))
            techset = str(payload.get("techniqueSet", "")).strip()
            if techset:
                techsets[techset] = techsets.get(techset, 0) + 1
        except Exception:
            unreadable.append(str(mat_file))
    return {"counts": techsets, "unreadable": unreadable}


def sync_zone_techset_lines(zone_path: Path, techsets: Sequence[str]) -> Dict[str, Any]:
    removed = remove_zone_lines_with_prefix(zone_path, prefixes=("techniqueset,",))
    ordered = []
    seen = set()
    for name in techsets:
        token = str(name).strip()
        key = token.lower()
        if token and key not in seen:
            seen.add(key)
            ordered.append(token)
    appended = append_unique_zone_lines(zone_path=zone_path, lines_to_add=[f"techniqueset,{name}" for name in ordered])
    return {"removed": removed, "appended": appended, "final": ordered}


def resolve_utility_xmodel_source_root(repo_root: Path, xmodel_name: str, source_hint: str) -> Path:
    candidates: List[Path] = []
    if source_hint:
        candidates.append(resolve_path(source_hint, repo_root))
    candidates.extend(resolve_path(item, repo_root) for item in UTILITY_XMODEL_SOURCE_HINTS)

    for root in candidates:
        if (root / "xmodel" / f"{xmodel_name}.json").exists():
            return root
        if root.name.lower() == "xmodel" and (root / f"{xmodel_name}.json").exists():
            return root.parent
    raise FileNotFoundError(
        f"Could not resolve source root for utility xmodel '{xmodel_name}'. "
        f"Tried: {[str(path) for path in candidates]}"
    )


def stage_required_utility_xmodels(
    repo_root: Path,
    zone_raw_root: Path,
    xmodel_names: Sequence[str],
    source_hint: str,
) -> Dict[str, Any]:
    staged_xmodels: List[str] = []
    staged_model_exports: List[str] = []
    details: List[Dict[str, Any]] = []

    for xmodel_name in xmodel_names:
        source_root = resolve_utility_xmodel_source_root(
            repo_root=repo_root,
            xmodel_name=xmodel_name,
            source_hint=source_hint,
        )
        src_xmodel = source_root / "xmodel" / f"{xmodel_name}.json"
        if not src_xmodel.exists():
            raise FileNotFoundError(f"Utility xmodel source json missing: {src_xmodel}")
        payload = json.loads(src_xmodel.read_text(encoding="utf-8"))

        dst_xmodel = zone_raw_root / "xmodel" / src_xmodel.name
        dst_xmodel.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_xmodel, dst_xmodel)
        staged_xmodels.append(xmodel_name)

        missing_lods: List[str] = []
        copied_lods: List[str] = []
        for lod in payload.get("lods", []):
            if not isinstance(lod, dict):
                continue
            lod_rel = str(lod.get("file", "")).strip().replace("\\", "/")
            if not lod_rel:
                continue
            src_lod = source_root / Path(lod_rel)
            dst_lod = zone_raw_root / Path(lod_rel)
            if not src_lod.exists():
                missing_lods.append(lod_rel)
                continue
            dst_lod.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_lod, dst_lod)
            copied_lods.append(lod_rel)
            staged_model_exports.append(lod_rel)

        if missing_lods:
            raise FileNotFoundError(
                f"Utility xmodel '{xmodel_name}' missing LOD payloads in source root {source_root}: {missing_lods}"
            )

        details.append(
            {
                "xmodel": xmodel_name,
                "source_root": str(source_root),
                "source_xmodel": str(src_xmodel),
                "staged_xmodel": str(dst_xmodel),
                "lods_copied": copied_lods,
            }
        )

    return {
        "status": "ok",
        "requested_xmodels": list(xmodel_names),
        "staged_xmodels": sorted(set(staged_xmodels)),
        "staged_model_exports": sorted(set(staged_model_exports)),
        "details": details,
    }


def ensure_minimal_material(zone_raw_root: Path, material_name: str, techset_name: str) -> Dict[str, Any]:
    material = str(material_name).strip().replace("\\", "/")
    if not material:
        raise RuntimeError("ensure_minimal_material requires a non-empty material_name")
    techset = str(techset_name).strip()
    if not techset:
        raise RuntimeError("ensure_minimal_material requires a non-empty techset_name")
    material_path = zone_raw_root / "materials" / Path(f"{material}.json")
    material_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
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
        "techniqueSet": techset,
        "textureAtlas": {"columns": 1, "rows": 1},
        "textures": [],
        "debugName": material,
    }
    material_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return {
        "material": material,
        "techset": techset,
        "file": str(material_path),
    }


def ensure_minimal_mc_mtl_default_material(zone_raw_root: Path, techset_name: str) -> Dict[str, Any]:
    return ensure_minimal_material(
        zone_raw_root=zone_raw_root,
        material_name="mc/mtl_default",
        techset_name=techset_name,
    )


def parse_techset_technique_names(techset_path: Path) -> List[str]:
    names: List[str] = []
    seen = set()
    for raw in techset_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("//"):
            continue
        match = re.search(r"([A-Za-z0-9_]+)\s*;\s*$", line)
        if not match:
            continue
        name = match.group(1).strip()
        if name and name not in seen:
            seen.add(name)
            names.append(name)
    return names


def resolve_techset_source_root(repo_root: Path, techset_name: str, source_hint: str) -> Path:
    candidates: List[Path] = []
    if source_hint:
        candidates.append(resolve_path(source_hint, repo_root))
    candidates.extend(resolve_path(item, repo_root) for item in PINNED_TECHSET_SOURCE_HINTS)

    for root in candidates:
        techset_path = root / "techsets" / f"{techset_name}.techset"
        if techset_path.exists() and (root / "techniques").exists():
            return root
    raise FileNotFoundError(
        f"Could not resolve source root for techniqueset '{techset_name}'. "
        f"Tried: {[str(path) for path in candidates]}"
    )


def stage_pinned_techset_bundle(
    repo_root: Path,
    zone_raw_root: Path,
    zone_file: Path,
    techset_name: str,
    source_hint: str,
) -> Dict[str, Any]:
    source_root = resolve_techset_source_root(
        repo_root=repo_root,
        techset_name=techset_name,
        source_hint=source_hint,
    )
    source_techset = source_root / "techsets" / f"{techset_name}.techset"
    source_techniques_root = source_root / "techniques"
    technique_names = parse_techset_technique_names(source_techset)
    if not technique_names:
        raise RuntimeError(f"No techniques parsed from techset: {source_techset}")

    missing: List[str] = []
    copied_techniques = 0
    dst_techset_root = zone_raw_root / "techsets"
    dst_techniques_root = zone_raw_root / "techniques"
    dst_techset_root.mkdir(parents=True, exist_ok=True)
    dst_techniques_root.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_techset, dst_techset_root / source_techset.name)

    for name in technique_names:
        src = source_techniques_root / f"{name}.tech"
        if not src.exists():
            missing.append(name)
            continue
        shutil.copy2(src, dst_techniques_root / src.name)
        copied_techniques += 1

    if missing:
        raise FileNotFoundError(
            f"Pinned techset '{techset_name}' missing {len(missing)} technique files in source root {source_root}: {missing[:8]}"
        )

    # T6 linker zone parser does not accept "technique,<name>" asset tokens.
    # Keep .tech payloads staged in zone_raw/techniques, but only declare the techniqueset in zone_source.
    removed_invalid = remove_zone_lines_with_prefix(zone_file, prefixes=("technique,",))
    zone_lines = [f"techniqueset,{techset_name}"]
    appended = append_unique_zone_lines(zone_path=zone_file, lines_to_add=zone_lines)
    return {
        "status": "ok",
        "techset": techset_name,
        "source_root": str(source_root),
        "source_techset": str(source_techset),
        "technique_count": len(technique_names),
        "copied_techniques": copied_techniques,
        "removed_invalid_zone_lines": removed_invalid,
        "zone_lines_appended": appended,
    }


def parse_blender_report(report_path: Path) -> Dict[str, Any]:
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    rows = payload.get("rows", [])
    ok_rows = [row for row in rows if row.get("status") == "ok"]
    if not ok_rows:
        raise RuntimeError(f"No successful rows in blender report: {report_path}")
    return payload


def find_xmodel_name_for_source(rows: Sequence[Dict[str, Any]], source_hint: str) -> str:
    hint = source_hint.lower()
    for row in rows:
        source = str(row.get("source", "")).lower()
        if hint in source:
            xmodel_json = Path(str(row.get("xmodel_json", "")))
            if xmodel_json.name:
                return xmodel_json.stem
    # Fallback: first successful row
    xmodel_json = Path(str(rows[0].get("xmodel_json", "")))
    return xmodel_json.stem


def run_transfer_step(
    repo_root: Path,
    t7_root: Path,
    source_mod: Path,
    transfer_root: Path,
    transfer_report: Path,
) -> Dict[str, Any]:
    cmd = [
        sys.executable,
        str(repo_root / "tools" / "asset_port_pipeline" / "transfer_thundergun_to_bo2.py"),
        "--t7-root",
        str(t7_root),
        "--source-mod",
        str(source_mod),
        "--output-root",
        str(transfer_root),
        "--report",
        str(transfer_report),
    ]
    proc = run_cmd(cmd, cwd=repo_root)
    if proc.returncode != 0:
        raise RuntimeError(f"transfer_thundergun_to_bo2 failed:\n{proc.stdout}\n{proc.stderr}")
    return json.loads(transfer_report.read_text(encoding="utf-8"))


def run_custom_converter(
    repo_root: Path,
    inputs: Sequence[Path],
    output_dir: Path,
    command_template: str,
    default_ext: str,
    asset_kind: str,
    verbose: bool = False,
) -> List[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    converted: List[Path] = []
    for src in inputs:
        out_file = output_dir / f"{sanitize_name(src.stem)}{default_ext}"
        cmd = command_template.format(
            input_file=str(src),
            input_stem=src.stem,
            input_ext=src.suffix,
            output_file=str(out_file),
            output_dir=str(output_dir),
            asset_kind=asset_kind,
        )
        proc = run_shell(cmd, cwd=repo_root, verbose=verbose)
        if proc.returncode != 0:
            raise RuntimeError(f"Converter command failed for {src}:\n{cmd}\n{proc.stdout}\n{proc.stderr}")
        if not out_file.exists():
            raise RuntimeError(
                f"Converter did not write expected output: {out_file}\nCommand: {cmd}"
            )
        converted.append(out_file)
    return converted


def run_blender_convert_step(
    repo_root: Path,
    input_root: Path,
    output_root: Path,
    project_name: str,
    blender_exe: str,
    copy_glb_without_blender: bool,
    report_path: Path,
    verbose_worker: bool,
    max_submesh_vertices: int,
    verbose: bool = False,
) -> Dict[str, Any]:
    cmd = [
        sys.executable,
        str(repo_root / "tools" / "asset_port_pipeline" / "blender_convert.py"),
        "--input",
        str(input_root),
        "--output-root",
        str(output_root),
        "--project-name",
        project_name,
        "--blender-exe",
        blender_exe,
        "--max-submesh-vertices",
        str(max_submesh_vertices),
        "--report",
        str(report_path),
    ]
    if copy_glb_without_blender:
        cmd.append("--copy-glb-without-blender")
    if verbose_worker:
        cmd.append("--verbose-worker")
    proc = run_cmd(cmd, cwd=repo_root, verbose=verbose)
    if proc.returncode != 0:
        raise RuntimeError(f"blender_convert failed:\n{proc.stdout}\n{proc.stderr}")
    return parse_blender_report(report_path)


def build_integration_project(
    output_root: Path,
    integration_project_name: str,
    blender_project_root: Path,
    transfer_root: Path,
    view_xmodel: str,
    world_xmodel: str,
    converted_anims: Sequence[Path],
    auto_patch_raygun_anims: bool,
    weapon_hud_icon_material: str,
    weapon_kill_icon_material: str,
    weapon_camo: str,
) -> Tuple[Path, Dict[str, Any]]:
    project_root = output_root / "integration_project" / integration_project_name
    zone_raw_root = project_root / "zone_raw" / integration_project_name
    zone_source_root = project_root / "zone_source"
    if project_root.exists():
        shutil.rmtree(project_root)
    zone_raw_root.mkdir(parents=True, exist_ok=True)
    zone_source_root.mkdir(parents=True, exist_ok=True)

    # model/xmodel payload from blender conversion project
    for rel in ("xmodel", "model_export"):
        src = blender_project_root / rel
        dst = zone_raw_root / rel
        if not src.exists():
            raise FileNotFoundError(f"Missing expected blender output folder: {src}")
        shutil.copytree(src, dst)

    # script + weapon logic payload
    mod_raw = transfer_root / "mod_raw"
    if not mod_raw.exists():
        raise FileNotFoundError(f"Missing transfer mod_raw folder: {mod_raw}")
    for src in mod_raw.rglob("*"):
        if not src.is_file():
            continue
        rel = src.relative_to(mod_raw)
        dst = zone_raw_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    # Patch model names into both weapon defs.
    weapon_anim_patch: Dict[str, Any] = {}
    for rel in ("weapons/thundergun_zm", "weapons/thundergun_upgraded_zm"):
        weapon_path = zone_raw_root / rel
        patch_weapon_model_fields(weapon_path, gun_model=view_xmodel, world_model=world_xmodel)
        anim_data = patch_weapon_anim_fields(
            weapon_path,
            auto_patch_raygun_anims=auto_patch_raygun_anims,
        )
        icon_data = patch_weapon_icon_fields(
            weapon_path,
            hud_icon_material=weapon_hud_icon_material,
            kill_icon_material=weapon_kill_icon_material,
        )
        camo_data = patch_weapon_camo_field(
            weapon_path,
            camo_name=weapon_camo,
        )
        weapon_anim_patch[rel] = {
            **anim_data,
            "icons": icon_data,
            "camo": camo_data,
        }

    xanim_names = stage_xanim_descriptors(zone_raw_root, converted_anims=converted_anims)
    xmodels = sorted([p.stem for p in (zone_raw_root / "xmodel").glob("*.json")])
    write_zone(zone_source_root / f"{integration_project_name}.zone", xmodels=xmodels, xanims=xanim_names)
    return project_root, weapon_anim_patch


def validate_rig_from_blender_rows(rows: Sequence[Dict[str, Any]], required_tags: Sequence[str]) -> List[str]:
    warnings: List[str] = []
    for row in rows:
        metadata = row.get("metadata") or {}
        source = str(row.get("source", ""))
        has_armature = bool(metadata.get("has_armature", False))
        bones = [str(x) for x in (metadata.get("kept_bones") or [])]
        if not has_armature:
            warnings.append(f"{source}: has_armature=false")
        if bones:
            missing = [tag for tag in required_tags if tag not in bones]
            if missing:
                warnings.append(f"{source}: missing tags/bones {missing}")
        else:
            warnings.append(f"{source}: no kept_bones in metadata")
    return warnings


def stage_xanim_descriptors(zone_raw_root: Path, converted_anims: Sequence[Path]) -> List[str]:
    """
    Stage converted xanim descriptor files into the integration project.
    Only json descriptors are linked in zone_source via xanim lines.
    """
    if not converted_anims:
        return []
    xanim_root = zone_raw_root / "xanim"
    xanim_export_root = zone_raw_root / "xanim_export"
    xanim_root.mkdir(parents=True, exist_ok=True)
    xanim_export_root.mkdir(parents=True, exist_ok=True)
    staged_xanim_names: List[str] = []
    for src in converted_anims:
        stem = sanitize_name(src.stem)
        if stem.startswith("vm_") or "view" in stem:
            bucket = "viewmodel"
        elif stem.startswith("wm_") or "world" in stem:
            bucket = "worldmodel"
        else:
            bucket = "misc"
        if src.suffix.lower() == ".json":
            dst = xanim_root / bucket / f"{stem}.json"
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            staged_xanim_names.append(dst.relative_to(xanim_root).with_suffix("").as_posix())
        else:
            # Keep non-json outputs for traceability/debug, but do not emit zone xanim lines.
            dst = xanim_export_root / bucket / src.name
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    return sorted(set(staged_xanim_names))


def set_option_values(cmd: Sequence[str], option: str, values: Sequence[str]) -> List[str]:
    """
    Replace an existing multi-value option in an argv list.
    Expects values to not start with '--'.
    """
    out: List[str] = []
    i = 0
    while i < len(cmd):
        token = cmd[i]
        if token == option:
            i += 1
            while i < len(cmd) and not str(cmd[i]).startswith("--"):
                i += 1
            continue
        out.append(token)
        i += 1
    if values:
        out.extend([option, *values])
    return out


def preflight_validate_outputs(
    blender_rows: Sequence[Dict[str, Any]],
    zone_raw_root: Path,
    view_xmodel: str,
    world_xmodel: str,
    min_view_glb_bytes: int,
    min_world_glb_bytes: int,
    require_no_raygun_anims: bool,
) -> Dict[str, Any]:
    warnings: List[str] = []
    errors: List[str] = []
    for row in blender_rows:
        metadata = row.get("metadata") or {}
        src = str(row.get("source", ""))
        glb_path = Path(str(row.get("glb", "")))
        if bool(metadata.get("fallback_copy_mode", False)):
            warnings.append(f"{src}: fallback_copy_mode used (no mesh/rig verification from blender worker)")
        if glb_path.exists():
            size = glb_path.stat().st_size
            if "view" in glb_path.name.lower() and size < max(1, int(min_view_glb_bytes)):
                warnings.append(f"{src}: view mesh appears too small ({size} bytes)")
            if "world" in glb_path.name.lower() and size < max(1, int(min_world_glb_bytes)):
                warnings.append(f"{src}: world mesh appears too small ({size} bytes)")
        else:
            errors.append(f"{src}: missing converted glb path {glb_path}")

        if bool(metadata.get("potential_unit_scale_issue", False)):
            warnings.append(f"{src}: potential unit/scale mismatch detected by worker")
        split_stats = metadata.get("split_stats") or {}
        if int(split_stats.get("submesh_over_limit", 0) or 0) > 0:
            errors.append(f"{src}: submesh vertex-limit overflow remains after split pass")
        if bool(metadata.get("source_has_armature", False)) and not bool(metadata.get("has_armature", False)):
            errors.append(f"{src}: source had armature but converted output does not")

    for rel in ("weapons/thundergun_zm", "weapons/thundergun_upgraded_zm"):
        path = zone_raw_root / rel
        text = path.read_text(encoding="utf-8", errors="ignore")
        if f"gunModel\\{view_xmodel}" not in text:
            errors.append(f"{path}: gunModel is not patched to {view_xmodel}")
        if f"worldModel\\{world_xmodel}" not in text:
            errors.append(f"{path}: worldModel is not patched to {world_xmodel}")
        raygun_hits = sorted(set(RAYGUN_ANIM_RE.findall(text)))
        if raygun_hits:
            msg = f"{path}: unresolved raygun anim refs remain ({len(raygun_hits)})"
            if require_no_raygun_anims:
                errors.append(msg)
            else:
                warnings.append(msg)

    xmodel_dir = zone_raw_root / "xmodel"
    for xmodel_json in xmodel_dir.glob("*.json"):
        try:
            payload = json.loads(xmodel_json.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"{xmodel_json}: invalid json ({exc})")
            continue
        lods = payload.get("lods") or []
        if not lods:
            errors.append(f"{xmodel_json}: missing lods")
            continue
        for lod in lods:
            lod_file = str(lod.get("file", "")).strip()
            if not lod_file.startswith("model_export/"):
                warnings.append(f"{xmodel_json}: lod file does not use model_export/ path ({lod_file})")

    return {"warnings": warnings, "errors": errors, "status": "pass" if not errors else "fail"}


def run_fidelity_audit_step(repo_root: Path, blender_report: Path, output_report: Path, verbose: bool = False) -> Dict[str, Any]:
    cmd = [
        sys.executable,
        str(repo_root / "tools" / "asset_port_pipeline" / "fidelity_audit.py"),
        "--blender-report",
        str(blender_report),
        "--output",
        str(output_report),
    ]
    proc = run_cmd(cmd, cwd=repo_root, verbose=verbose)
    if proc.returncode != 0:
        raise RuntimeError(f"fidelity_audit failed:\n{proc.stdout}\n{proc.stderr}")
    return json.loads(output_report.read_text(encoding="utf-8"))


def run_material_translate_step(
    repo_root: Path,
    project_root: Path,
    project_name: str,
    blender_report: Path,
    output_report: Path,
    material_default_techset: str,
    material_lit_techset: str,
    material_unlit_techset: str,
    bundle_report: Path | None = None,
    verbose: bool = False,
) -> Dict[str, Any]:
    cmd = [
        sys.executable,
        str(repo_root / "tools" / "asset_port_pipeline" / "translate_bo3_materials_to_bo2.py"),
        "--project-root",
        str(project_root),
        "--project-name",
        project_name,
        "--blender-report",
        str(blender_report),
        "--default-techset",
        str(material_default_techset),
        "--lit-techset",
        str(material_lit_techset),
        "--unlit-techset",
        str(material_unlit_techset),
        "--append-zone-lines",
        "--report",
        str(output_report),
    ]
    if bundle_report is not None:
        cmd.extend(["--bundle-report", str(bundle_report)])
    proc = run_cmd(cmd, cwd=repo_root, verbose=verbose)
    if proc.returncode != 0:
        raise RuntimeError(f"translate_bo3_materials_to_bo2 failed:\n{proc.stdout}\n{proc.stderr}")
    return json.loads(output_report.read_text(encoding="utf-8"))


def run_xanim_retarget_step(
    repo_root: Path,
    input_files: Sequence[Path],
    donor: Path,
    output_root: Path,
    skeleton_map: Path,
    min_match_ratio: float,
    strict: bool,
    verbose: bool = False,
) -> Dict[str, Any]:
    if not input_files:
        return {"status": "skipped", "reason": "no input xanim files"}
    stage_input = output_root / "input_stage"
    if stage_input.exists():
        shutil.rmtree(stage_input)
    stage_input.mkdir(parents=True, exist_ok=True)
    for src in input_files:
        shutil.copy2(src, stage_input / src.name)
    report_path = output_root / "retarget_xanim_report.json"
    cmd = [
        sys.executable,
        str(repo_root / "tools" / "asset_port_pipeline" / "retarget_xanim_exports.py"),
        "--input-root",
        str(stage_input),
        "--donor",
        str(donor),
        "--output-root",
        str(output_root / "retargeted"),
        "--skeleton-map",
        str(skeleton_map),
        "--min-match-ratio",
        str(float(min_match_ratio)),
        "--report",
        str(report_path),
    ]
    if strict:
        cmd.append("--strict")
    proc = run_cmd(cmd, cwd=repo_root, verbose=verbose)
    if proc.returncode != 0:
        raise RuntimeError(f"retarget_xanim_exports failed:\n{proc.stdout}\n{proc.stderr}")
    data = json.loads(report_path.read_text(encoding="utf-8"))
    retargeted = sorted((output_root / "retargeted").glob("*.xanim_export"))
    data["retargeted_files"] = [str(path) for path in retargeted]
    return data


def viewmodel_kept_bones_from_blender_report(blender_report: Dict[str, Any]) -> List[str]:
    rows = [row for row in blender_report.get("rows", []) if row.get("status") == "ok"]
    view_row = next(
        (row for row in rows if "thundergun_view" in str(row.get("source", "")).lower()),
        rows[0] if rows else None,
    )
    if not view_row:
        return []
    metadata = view_row.get("metadata") or {}
    bones = [str(item).strip() for item in (metadata.get("kept_bones") or []) if str(item).strip()]
    seen = set()
    out: List[str] = []
    for bone in bones:
        key = bone.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(bone)
    return out


def build_auto_xanim_donor(
    source_xanim: Path,
    output_path: Path,
    allowed_bones: Sequence[str],
) -> Dict[str, Any]:
    if parse_xanim_export is None or write_xanim_export is None:
        raise RuntimeError("retarget_xanim_exports parser/writer is unavailable in this runtime")
    parsed = parse_xanim_export(source_xanim)
    source_parts = [str(part) for part in (parsed.get("parts") or [])]
    allowed = {str(b).strip().lower() for b in allowed_bones if str(b).strip()}
    if not source_parts:
        raise RuntimeError(f"Source donor xanim has no parts: {source_xanim}")
    selected_old_indices: List[int] = []
    selected_parts: List[str] = []
    for old_idx, part_name in enumerate(source_parts):
        if part_name.lower() in allowed:
            selected_old_indices.append(old_idx)
            selected_parts.append(part_name)
    if not selected_parts:
        raise RuntimeError(
            f"Auto donor produced 0 shared bones. source_parts={len(source_parts)} allowed_bones={len(allowed)}"
        )

    frames_in = parsed.get("frames") or {}
    frame_keys = sorted(frames_in.keys())
    frame0 = frames_in.get(frame_keys[0], {}) if frame_keys else {}
    donor_frames: Dict[int, Dict[int, Dict[str, Any]]] = {0: {}}
    for new_idx, old_idx in enumerate(selected_old_indices):
        src = frame0.get(old_idx) if isinstance(frame0, dict) else None
        if src:
            donor_frames[0][new_idx] = {
                "offset": [float(v) for v in src.get("offset", [0.0, 0.0, 0.0])],
                "rot": [[float(v) for v in row] for row in src.get("rot", [[1, 0, 0], [0, 1, 0], [0, 0, 1]])],
            }
        else:
            donor_frames[0][new_idx] = {
                "offset": [0.0, 0.0, 0.0],
                "rot": [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
            }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    write_xanim_export(
        path=output_path,
        anim_name=output_path.stem,
        framerate=int(parsed.get("framerate", 30) or 30),
        parts=selected_parts,
        frames=donor_frames,
    )
    return {
        "source_xanim": str(source_xanim),
        "donor_xanim": str(output_path),
        "source_parts": len(source_parts),
        "selected_parts": len(selected_parts),
    }


def pick_best_xanim_donor(xanim_exports: Sequence[Path]) -> Tuple[Path, Dict[str, Any]]:
    if not xanim_exports:
        raise RuntimeError("pick_best_xanim_donor received empty list")
    if parse_xanim_export is None:
        return xanim_exports[0], {"reason": "parser_unavailable", "parts": 0, "frames": 0}

    best_path = xanim_exports[0]
    best_parts = -1
    best_frames = -1
    for candidate in xanim_exports:
        try:
            parsed = parse_xanim_export(candidate)
            parts = len(parsed.get("parts") or [])
            frames = int(parsed.get("numframes", 0) or 0)
        except Exception:
            parts = 0
            frames = 0
        if parts > best_parts or (parts == best_parts and frames > best_frames):
            best_path = candidate
            best_parts = parts
            best_frames = frames
    return best_path, {"reason": "max_parts_then_frames", "parts": best_parts, "frames": best_frames}


def summarize_xanim_exports(xanim_exports: Sequence[Path], low_parts_threshold: int) -> Dict[str, Any]:
    summary: Dict[str, Any] = {
        "count": len(xanim_exports),
        "min_parts": 0,
        "max_parts": 0,
        "min_frames": 0,
        "max_frames": 0,
        "low_parts_threshold": int(max(1, low_parts_threshold)),
        "low_parts_files": [],
        "parse_errors": [],
    }
    if not xanim_exports or parse_xanim_export is None:
        return summary

    min_parts: int | None = None
    max_parts = 0
    min_frames: int | None = None
    max_frames = 0
    low_parts: List[str] = []
    parse_errors: List[str] = []

    for path in xanim_exports:
        try:
            parsed = parse_xanim_export(path)
            parts = int(len(parsed.get("parts") or []))
            frames = int(parsed.get("numframes", 0) or 0)
        except Exception as exc:
            parse_errors.append(f"{path.name}: {exc}")
            continue
        min_parts = parts if min_parts is None else min(min_parts, parts)
        max_parts = max(max_parts, parts)
        min_frames = frames if min_frames is None else min(min_frames, frames)
        max_frames = max(max_frames, frames)
        if parts < int(max(1, low_parts_threshold)):
            low_parts.append(path.name)

    summary["min_parts"] = int(min_parts or 0)
    summary["max_parts"] = int(max_parts)
    summary["min_frames"] = int(min_frames or 0)
    summary["max_frames"] = int(max_frames)
    summary["low_parts_files"] = sorted(low_parts)
    summary["parse_errors"] = parse_errors
    return summary


def run_custom_xanim_zone_compile(
    repo_root: Path,
    xanim_dir: Path,
    output_dir: Path,
    zone_name: str,
    xanim_pattern: str,
    compiler_script: Path,
    stub_numframes: int,
    stub_is_default: bool,
    bone_count_profile: str,
    emit_mode: str,
    ensure_bones: Sequence[str],
    verbose: bool = False,
) -> Dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        str(compiler_script),
        "--xanim-dir",
        str(xanim_dir),
        "--pattern",
        str(xanim_pattern),
        "--output-dir",
        str(output_dir),
        "--zone-name",
        zone_name,
        "--emit-mode",
        str(emit_mode),
        "--stub-numframes",
        str(max(0, int(stub_numframes))),
        "--bone-count-profile",
        str(bone_count_profile),
    ]
    if ensure_bones:
        cmd.extend(["--ensure-bones", *[str(item) for item in ensure_bones if str(item).strip()]])
    cmd.append("--stub-is-default" if stub_is_default else "--no-stub-is-default")
    proc = run_cmd(cmd, cwd=repo_root, verbose=verbose)
    ff_path = output_dir / f"{zone_name}.ff"
    result: Dict[str, Any] = {
        "status": "ok" if proc.returncode == 0 and ff_path.exists() else "error",
        "command": cmd,
        "ff_path": str(ff_path),
        "stdout_tail": (proc.stdout or "")[-4000:],
        "stderr_tail": (proc.stderr or "")[-4000:],
    }
    if ff_path.exists():
        result["ff_size"] = ff_path.stat().st_size
    return result


def run_xanim_normalize_step(
    repo_root: Path,
    input_files: Sequence[Path],
    output_root: Path,
    donor: Path | None,
    skeleton_map: Path | None,
    fill_mode: str,
    max_offset: float,
    orthonormalize: bool,
    verbose: bool = False,
) -> Dict[str, Any]:
    if not input_files:
        return {"status": "skipped", "reason": "no input xanim files"}
    stage_input = output_root / "input_stage"
    if stage_input.exists():
        shutil.rmtree(stage_input)
    stage_input.mkdir(parents=True, exist_ok=True)
    for src in input_files:
        shutil.copy2(src, stage_input / src.name)

    report_path = output_root / "normalize_xanim_report.json"
    cmd = [
        sys.executable,
        str(repo_root / "tools" / "asset_port_pipeline" / "normalize_xanim_exports.py"),
        "--input-root",
        str(stage_input),
        "--output-root",
        str(output_root / "normalized"),
        "--pattern",
        "*.xanim_export",
        "--fill-mode",
        str(fill_mode),
        "--max-offset",
        str(float(max_offset)),
        "--report",
        str(report_path),
    ]
    if donor is not None:
        cmd.extend(["--donor", str(donor)])
    if skeleton_map is not None:
        cmd.extend(["--skeleton-map", str(skeleton_map)])
    if not orthonormalize:
        cmd.append("--no-orthonormalize")

    proc = run_cmd(cmd, cwd=repo_root, verbose=verbose)
    if proc.returncode != 0:
        raise RuntimeError(f"normalize_xanim_exports failed:\n{proc.stdout}\n{proc.stderr}")
    data = json.loads(report_path.read_text(encoding="utf-8"))
    normalized = sorted((output_root / "normalized").glob("*.xanim_export"))
    data["normalized_files"] = [str(path) for path in normalized]
    return data


def main() -> None:
    parser = argparse.ArgumentParser(description="End-to-end Thundergun BO3->BO2 integration pipeline.")
    parser.add_argument("--t7-root", required=True, help="Root path of dumped T7 assets.")
    parser.add_argument("--source-mod", default="mods/zm_roguelike_panzer", help="Source BO2 mod for logic files.")
    parser.add_argument("--output-root", default="_build/asset_port_pipeline/thundergun_e2e", help="Pipeline output root.")
    parser.add_argument("--integration-project-name", default="thundergun_town_full", help="Integration project name.")
    parser.add_argument("--model-bin-pattern", default="*thundergun*LOD0.XMODEL_BIN", help="Glob pattern for staged model BIN discovery.")
    parser.add_argument("--anim-bin-pattern", default="vm_thunder_gun_*.xanim_bin", help="Glob pattern for staged xanim BIN discovery.")
    parser.add_argument("--view-source-hint", default="thundergun_view", help="Hint for selecting converted viewmodel xmodel row.")
    parser.add_argument("--world-source-hint", default="thundergun_world", help="Hint for selecting converted worldmodel xmodel row.")

    parser.add_argument(
        "--converter-mode",
        choices=["none", "mesh-folder", "command"],
        default="none",
        help="Model conversion source mode.",
    )
    parser.add_argument("--mesh-input-root", default="", help="Folder with pre-converted model meshes.")
    parser.add_argument(
        "--model-converter-cmd",
        default="",
        help=(
            "Shell command template used in command mode. Tokens: "
            "{input_file} {input_stem} {input_ext} {output_file} {output_dir} {asset_kind}"
        ),
    )
    parser.add_argument(
        "--anim-converter-cmd",
        default="",
        help="Optional shell command template for xanim conversion (same tokens as model converter).",
    )
    parser.add_argument(
        "--auto-codbin-converter",
        action="store_true",
        help=(
            "Auto-wire converter commands that use tools/asset_port_pipeline/convert_cod_bin_with_blender.py "
            "for both xmodel and xanim BIN assets."
        ),
    )
    parser.add_argument(
        "--converter-blender-exe",
        default="",
        help="Optional Blender executable for --auto-codbin-converter.",
    )
    parser.add_argument(
        "--converter-blender-cod-root",
        default="",
        help="Optional blender-cod package root for --auto-codbin-converter.",
    )
    parser.add_argument("--model-output-ext", default=".glb", help="Expected model output extension in command mode.")
    parser.add_argument("--anim-output-ext", default=".json", help="Expected animation output extension in command mode.")
    parser.add_argument(
        "--auto-patch-raygun-anims",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Auto-rewrite lingering raygun viewmodel anim refs to vm_thunder_gun_* in copied weapon defs.",
    )
    parser.add_argument(
        "--allow-raygun-anims",
        action="store_true",
        help="Do not fail preflight when raygun anim refs remain in thundergun weapon defs.",
    )
    parser.add_argument(
        "--retarget-xanims",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Retarget converted xanim_export files onto a donor skeleton/order.",
    )
    parser.add_argument("--xanim-donor", default="", help="Donor xanim_export path used by --retarget-xanims.")
    parser.add_argument(
        "--xanim-auto-donor-from-viewmodel",
        action="store_true",
        help="Build donor xanim from converted viewmodel kept bones when --xanim-donor is not provided.",
    )
    parser.add_argument(
        "--xanim-auto-donor-min-bones",
        type=int,
        default=8,
        help="Minimum viewmodel kept bones required to auto-build donor xanim.",
    )
    parser.add_argument(
        "--xanim-skeleton-map",
        default="tools/asset_port_pipeline/skeleton_map_bo3_to_bo2.json",
        help="Skeleton remap JSON used during xanim retargeting.",
    )
    parser.add_argument("--xanim-retarget-min-match-ratio", type=float, default=0.35, help="Minimum retarget match ratio before warning/fail.")
    parser.add_argument("--xanim-retarget-strict", action="store_true", help="Fail pipeline when retarget match ratio is below threshold.")
    parser.add_argument(
        "--xanim-low-parts-threshold",
        type=int,
        default=8,
        help="Warn when converted xanim_export files have fewer PART entries than this value.",
    )
    parser.add_argument(
        "--normalize-xanims",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Normalize/bake xanim_export files before staging.",
    )
    parser.add_argument(
        "--xanim-normalize-fill-mode",
        choices=["identity", "hold_previous"],
        default="hold_previous",
        help="Missing-part fill strategy used by xanim normalization pass.",
    )
    parser.add_argument("--xanim-normalize-max-offset", type=float, default=4096.0, help="Max abs offset clamp during xanim normalization.")
    parser.add_argument(
        "--xanim-normalize-orthonormalize",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Orthonormalize rotation bases during xanim normalization.",
    )
    parser.add_argument(
        "--compile-custom-xanim-zone",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Compile staged xanim_export files into a standalone xanim fastfile.",
    )
    parser.add_argument("--custom-xanim-zone-name", default="thundergun_xanims", help="Fastfile name for --compile-custom-xanim-zone.")
    parser.add_argument("--custom-xanim-compiler", default="_build/compile_xanim_zone.py", help="Path to custom xanim compiler script.")
    parser.add_argument("--custom-xanim-pattern", default="**/vm_thunder_gun_*.xanim_export", help="Glob pattern for custom xanim zone compiler input.")
    parser.add_argument("--custom-xanim-stub-numframes", type=int, default=0, help="Stub numframes passed to custom xanim compiler.")
    parser.add_argument(
        "--custom-xanim-stub-is-default",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Emit isDefault=1 in custom xanim compiler output.",
    )
    parser.add_argument(
        "--custom-xanim-bone-count-profile",
        choices=["split_none", "cumulative_none", "zero"],
        default="cumulative_none",
        help="boneCount profile forwarded to custom xanim compiler.",
    )
    parser.add_argument(
        "--custom-xanim-emit-mode",
        choices=["static_pose", "stub"],
        default="static_pose",
        help="Emit mode forwarded to custom xanim compiler.",
    )
    parser.add_argument(
        "--custom-xanim-ensure-bones",
        default="tag_view,tag_camera,tag_player,tag_origin",
        help="Comma-separated bones to force-inject into custom xanim source before compile.",
    )

    parser.add_argument("--blender-exe", default="blender", help="Blender executable path or command.")
    parser.add_argument("--copy-glb-without-blender", action="store_true", help="Allow GLB passthrough when blender is unavailable.")
    parser.add_argument("--required-tags", default="tag_weapon_right,tag_flash", help="Comma-separated tag/bone checks for converted rigs.")
    parser.add_argument("--max-submesh-vertices", type=int, default=2400, help="Target submesh vertex cap used by blender worker.")
    parser.add_argument("--verbose-converter", action="store_true", help="Stream converter/blender raw output.")
    parser.add_argument("--strict-preflight", action="store_true", help="Fail before compile if preflight detects hard errors.")
    parser.add_argument("--min-view-glb-bytes", type=int, default=32768, help="Heuristic minimum size for viewmodel GLB.")
    parser.add_argument("--min-world-glb-bytes", type=int, default=16384, help="Heuristic minimum size for worldmodel GLB.")
    parser.add_argument("--run-fidelity-audit", action="store_true", help="Run fidelity audit report after conversion.")
    parser.add_argument(
        "--material-default-techset",
        default=DEFAULT_PINNED_TECHSET,
        help="Deterministic default techniqueset passed to material translator.",
    )
    parser.add_argument(
        "--material-lit-techset",
        default=DEFAULT_PINNED_TECHSET,
        help="Deterministic lit techniqueset passed to material translator.",
    )
    parser.add_argument(
        "--material-unlit-techset",
        default=DEFAULT_PINNED_TECHSET,
        help="Deterministic unlit techniqueset passed to material translator.",
    )
    parser.add_argument(
        "--pinned-techset",
        default=DEFAULT_PINNED_TECHSET,
        help="Techset baked into integration zone_source/zone_raw to avoid donor-map dependency.",
    )
    parser.add_argument(
        "--pinned-techset-source-root",
        default="",
        help="Optional root containing techsets/ + techniques/ used to source --pinned-techset files.",
    )
    parser.add_argument(
        "--stage-pinned-techset",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Stage pinned techniqueset and all required techniques into integration project.",
    )
    parser.add_argument(
        "--stage-utility-xmodels",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Stage required utility xmodels (e.g. viewmodel_hands_no_model) into integration project.",
    )
    parser.add_argument(
        "--required-utility-xmodels",
        default=",".join(DEFAULT_REQUIRED_UTILITY_XMODELS),
        help="Comma-separated utility xmodel names staged into integration project.",
    )
    parser.add_argument(
        "--utility-xmodel-source-root",
        default="",
        help="Optional root containing xmodel/ + model_export/ used to source required utility xmodels.",
    )
    parser.add_argument(
        "--required-fallback-materials",
        default=",".join(DEFAULT_REQUIRED_FALLBACK_MATERIALS),
        help="Comma-separated fallback material names staged as minimal deterministic descriptors.",
    )
    parser.add_argument(
        "--weapon-hud-icon-material",
        default=DEFAULT_WEAPON_HUD_ICON_MATERIAL,
        help="Material name injected into thundergun weapon hudIcon field.",
    )
    parser.add_argument(
        "--weapon-kill-icon-material",
        default=DEFAULT_WEAPON_KILL_ICON_MATERIAL,
        help="Material name injected into thundergun weapon killIcon field.",
    )
    parser.add_argument(
        "--weapon-camo",
        default="",
        help="Camo name injected into thundergun weapon camo field (empty clears camo dependency).",
    )

    parser.add_argument("--compile", action="store_true", help="Compile final integration project with linker.")
    parser.add_argument("--linker", default="tools/oat/Linker.exe", help="Path to Linker.exe.")
    parser.add_argument("--load-zones", nargs="*", default=["zone/all/common_zm.ff"], help="Load zones for compile.")
    parser.add_argument("--install-zone-dir", default="", help="Optional install destination mods/<mod>/zone/all.")
    parser.add_argument(
        "--allow-reserved-zone-names",
        action="store_true",
        help=(
            "Allow output fastfile names that collide with Plutonium core mod zones "
            "(mod/mod_load/mod_patch). Disabled by default for runtime safety."
        ),
    )
    parser.add_argument("--remediate-on-fail", action="store_true", help="Run remediation loop when first compile fails.")
    parser.add_argument("--remediate-retries", type=int, default=8, help="Max remediation retries.")
    parser.add_argument(
        "--allow-remediation-load-zone-drift",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Allow remediation to mutate compile load-zones (disabled by default for deterministic runs).",
    )
    parser.add_argument("--remediate-prune-unresolved", action="store_true", help="Allow unresolved zone-asset pruning during remediation.")
    parser.add_argument(
        "--dependency-roots",
        nargs="*",
        default=[],
        help="Optional dependency roots for remediation staging.",
    )

    parser.add_argument("--dry-run", action="store_true", help="Run transfer + planning only; skip convert/compile.")
    parser.add_argument("--report", default="_build/asset_port_pipeline/thundergun_e2e_report.json", help="Output report JSON path.")
    args = parser.parse_args()

    repo_root = Path.cwd().resolve()
    t7_root = resolve_path(args.t7_root, repo_root)
    source_mod = resolve_path(args.source_mod, repo_root)
    output_root = resolve_path(args.output_root, repo_root)
    report_path = resolve_path(args.report, repo_root)
    output_root.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    integration_zone_name = sanitize_name(args.integration_project_name)
    custom_xanim_zone_name = sanitize_name(args.custom_xanim_zone_name)
    reserved_hits = sorted(
        {
            name
            for name in (integration_zone_name, custom_xanim_zone_name)
            if name in RESERVED_RUNTIME_ZONE_NAMES
        }
    )
    if args.install_zone_dir and reserved_hits and not args.allow_reserved_zone_names:
        raise RuntimeError(
            "Refusing runtime install with reserved zone name(s): "
            + ", ".join(reserved_hits)
            + ". These names override Plutonium core mod fastfiles and can break weapon registration. "
              "Use --allow-reserved-zone-names to override deliberately."
        )

    if args.auto_codbin_converter:
        converter_script = repo_root / "tools" / "asset_port_pipeline" / "convert_cod_bin_with_blender.py"
        quoted_py = f"\"{sys.executable}\""
        quoted_script = f"\"{converter_script}\""

        model_cmd = (
            f"{quoted_py} {quoted_script} --asset-kind xmodel "
            "--input \"{input_file}\" --output \"{output_file}\""
        )
        anim_cmd = (
            f"{quoted_py} {quoted_script} --asset-kind xanim "
            "--input \"{input_file}\" --output \"{output_file}\""
        )
        if args.converter_blender_exe:
            model_cmd += f" --blender-exe \"{args.converter_blender_exe}\""
            anim_cmd += f" --blender-exe \"{args.converter_blender_exe}\""
        if args.converter_blender_cod_root:
            model_cmd += f" --blender-cod-root \"{args.converter_blender_cod_root}\""
            anim_cmd += f" --blender-cod-root \"{args.converter_blender_cod_root}\""
        if args.verbose_converter:
            model_cmd += " --verbose"
            anim_cmd += " --verbose"

        args.converter_mode = "command"
        args.model_converter_cmd = model_cmd
        if not args.anim_converter_cmd:
            args.anim_converter_cmd = anim_cmd
        args.model_output_ext = ".glb"
        args.anim_output_ext = ".xanim_export"
        if args.converter_blender_exe and args.blender_exe == "blender":
            args.blender_exe = args.converter_blender_exe
        elif args.blender_exe == "blender":
            for candidate in (
                Path(r"C:\Program Files\Blender Foundation\Blender 5.0\blender.exe"),
                Path(r"C:\Program Files\Blender Foundation\Blender 4.1\blender.exe"),
                Path(r"C:\Program Files\Blender Foundation\Blender 4.0\blender.exe"),
                Path(r"C:\Program Files\Blender Foundation\Blender 3.6\blender.exe"),
            ):
                if candidate.exists():
                    args.blender_exe = str(candidate)
                    break

    transfer_root = output_root / "transfer"
    transfer_report = output_root / "transfer_report.json"

    report: Dict[str, Any] = {
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "inputs": {
            "t7_root": str(t7_root),
            "source_mod": str(source_mod),
            "converter_mode": args.converter_mode,
            "auto_codbin_converter": bool(args.auto_codbin_converter),
            "model_bin_pattern": str(args.model_bin_pattern),
            "anim_bin_pattern": str(args.anim_bin_pattern),
            "max_submesh_vertices": int(args.max_submesh_vertices),
            "strict_preflight": bool(args.strict_preflight),
            "retarget_xanims": bool(args.retarget_xanims),
            "xanim_auto_donor_from_viewmodel": bool(args.xanim_auto_donor_from_viewmodel),
            "normalize_xanims": bool(args.normalize_xanims),
            "xanim_normalize_fill_mode": str(args.xanim_normalize_fill_mode),
            "xanim_normalize_max_offset": float(args.xanim_normalize_max_offset),
            "compile_custom_xanim_zone": bool(args.compile_custom_xanim_zone),
            "custom_xanim_pattern": str(args.custom_xanim_pattern),
            "custom_xanim_bone_count_profile": str(args.custom_xanim_bone_count_profile),
            "custom_xanim_emit_mode": str(args.custom_xanim_emit_mode),
            "custom_xanim_ensure_bones": parse_csv_names(str(args.custom_xanim_ensure_bones)),
            "allow_reserved_zone_names": bool(args.allow_reserved_zone_names),
            "integration_zone_name": integration_zone_name,
            "custom_xanim_zone_name": custom_xanim_zone_name,
            "auto_patch_raygun_anims": bool(args.auto_patch_raygun_anims),
            "allow_raygun_anims": bool(args.allow_raygun_anims),
            "material_default_techset": str(args.material_default_techset),
            "material_lit_techset": str(args.material_lit_techset),
            "material_unlit_techset": str(args.material_unlit_techset),
            "pinned_techset": str(args.pinned_techset),
            "pinned_techset_source_root": str(args.pinned_techset_source_root),
            "stage_pinned_techset": bool(args.stage_pinned_techset),
            "stage_utility_xmodels": bool(args.stage_utility_xmodels),
            "required_utility_xmodels": parse_csv_names(str(args.required_utility_xmodels)),
            "utility_xmodel_source_root": str(args.utility_xmodel_source_root),
            "required_fallback_materials": parse_csv_names(str(args.required_fallback_materials)),
            "weapon_hud_icon_material": str(args.weapon_hud_icon_material),
            "weapon_kill_icon_material": str(args.weapon_kill_icon_material),
            "weapon_camo": str(args.weapon_camo),
            "allow_remediation_load_zone_drift": bool(args.allow_remediation_load_zone_drift),
        },
        "steps": {},
        "warnings": [],
    }

    transfer_data = run_transfer_step(
        repo_root=repo_root,
        t7_root=t7_root,
        source_mod=source_mod,
        transfer_root=transfer_root,
        transfer_report=transfer_report,
    )
    report["steps"]["transfer"] = {
        "status": "ok",
        "report": str(transfer_report),
        "counts": transfer_data.get("counts", {}),
    }

    staged_root = transfer_root / "t7_bundle" / "staged"
    model_bins = sorted(staged_root.rglob(str(args.model_bin_pattern)))
    anim_bins = sorted(staged_root.rglob(str(args.anim_bin_pattern)))
    report["steps"]["discover_bins"] = {
        "status": "ok",
        "model_bins": [str(p) for p in model_bins],
        "anim_bins_count": len(anim_bins),
    }
    if not model_bins:
        raise RuntimeError(
            f"No model bins found under: {staged_root} (pattern={args.model_bin_pattern})"
        )

    if args.dry_run or args.converter_mode == "none":
        report["steps"]["convert"] = {
            "status": "skipped",
            "reason": "dry_run or converter_mode=none",
        }
        report["next_required"] = [
            "Provide --converter-mode mesh-folder with converted thundergun meshes, OR",
            "Provide --converter-mode command with --model-converter-cmd.",
        ]
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Saved E2E report: {report_path}")
        print("Stopped before conversion stage (converter not configured).")
        return

    converted_models_dir = output_root / "converted_models"
    converted_anims_dir = output_root / "converted_anims"
    converted_models: List[Path] = []
    converted_anims: List[Path] = []

    if args.converter_mode == "mesh-folder":
        if not args.mesh_input_root:
            raise RuntimeError("--mesh-input-root is required for converter-mode=mesh-folder")
        mesh_root = resolve_path(args.mesh_input_root, repo_root)
        if not mesh_root.exists():
            raise FileNotFoundError(f"mesh-input-root not found: {mesh_root}")
        converted_models = collect_thundergun_meshes(mesh_root)
        if not converted_models:
            raise RuntimeError(f"No thundergun meshes found under: {mesh_root}")
    else:
        if not args.model_converter_cmd:
            raise RuntimeError("--model-converter-cmd is required for converter-mode=command")
        converted_models = run_custom_converter(
            repo_root=repo_root,
            inputs=model_bins,
            output_dir=converted_models_dir,
            command_template=args.model_converter_cmd,
            default_ext=args.model_output_ext,
            asset_kind="xmodel",
            verbose=args.verbose_converter,
        )
        if args.anim_converter_cmd:
            try:
                converted_anims = run_custom_converter(
                    repo_root=repo_root,
                    inputs=anim_bins,
                    output_dir=converted_anims_dir,
                    command_template=args.anim_converter_cmd,
                    default_ext=args.anim_output_ext,
                    asset_kind="xanim",
                    verbose=args.verbose_converter,
                )
            except RuntimeError as exc:
                report["warnings"].append(
                    "xanim conversion failed; continuing with models only: "
                    + str(exc).splitlines()[0]
                )
                converted_anims = []

    view_mesh, world_mesh = choose_view_world(converted_models)
    blender_input = output_root / "blender_input"
    if blender_input.exists():
        shutil.rmtree(blender_input)
    blender_input.mkdir(parents=True, exist_ok=True)
    view_copy = blender_input / f"thundergun_view{view_mesh.suffix.lower()}"
    world_copy = blender_input / f"thundergun_world{world_mesh.suffix.lower()}"
    shutil.copy2(view_mesh, view_copy)
    shutil.copy2(world_mesh, world_copy)

    blender_output_root = output_root / "converted_zone_raw"
    blender_project_name = sanitize_name(args.integration_project_name) + "_models"
    blender_report_path = output_root / "blender_convert_report.json"
    blender_report = run_blender_convert_step(
        repo_root=repo_root,
        input_root=blender_input,
        output_root=blender_output_root,
        project_name=blender_project_name,
        blender_exe=args.blender_exe,
        copy_glb_without_blender=args.copy_glb_without_blender,
        report_path=blender_report_path,
        verbose_worker=args.verbose_converter,
        max_submesh_vertices=max(64, int(args.max_submesh_vertices)),
        verbose=args.verbose_converter,
    )

    ok_rows = [row for row in blender_report.get("rows", []) if row.get("status") == "ok"]
    view_xmodel = find_xmodel_name_for_source(ok_rows, str(args.view_source_hint))
    world_xmodel = find_xmodel_name_for_source(ok_rows, str(args.world_source_hint))
    required_tags = [x.strip() for x in args.required_tags.split(",") if x.strip()]
    rig_warnings = validate_rig_from_blender_rows(ok_rows, required_tags=required_tags)
    report["warnings"].extend(rig_warnings)

    retarget_donor_used: Path | None = None
    skeleton_map_path = resolve_path(args.xanim_skeleton_map, repo_root) if args.xanim_skeleton_map else None
    xanim_exports_pre = [path for path in converted_anims if path.suffix.lower() == ".xanim_export"]
    if xanim_exports_pre:
        xanim_health = summarize_xanim_exports(
            xanim_exports=xanim_exports_pre,
            low_parts_threshold=int(args.xanim_low_parts_threshold),
        )
        report["steps"]["xanim_health_pre_retarget"] = {"status": "ok", **xanim_health}
        if xanim_health.get("low_parts_files"):
            report["warnings"].append(
                f"low-part xanim exports detected before retarget: {len(xanim_health['low_parts_files'])}"
            )

    if args.retarget_xanims:
        xanim_exports = [path for path in converted_anims if path.suffix.lower() == ".xanim_export"]
        if xanim_exports:
            retarget_root = output_root / "retarget_xanim"
            donor_seed, donor_seed_meta = pick_best_xanim_donor(xanim_exports)
            donor_path = resolve_path(args.xanim_donor, repo_root) if args.xanim_donor else None
            auto_donor_data: Dict[str, Any] | None = None
            if donor_path is None and args.xanim_auto_donor_from_viewmodel:
                view_kept_bones = viewmodel_kept_bones_from_blender_report(blender_report)
                if len(view_kept_bones) >= max(1, int(args.xanim_auto_donor_min_bones)):
                    auto_donor_path = retarget_root / "auto_donor" / "vm_thunder_gun_auto_donor.xanim_export"
                    auto_donor_data = build_auto_xanim_donor(
                        source_xanim=donor_seed,
                        output_path=auto_donor_path,
                        allowed_bones=view_kept_bones,
                    )
                    donor_path = auto_donor_path
                else:
                    report["warnings"].append(
                        f"auto donor skipped: kept_bones={len(view_kept_bones)} below min={int(args.xanim_auto_donor_min_bones)}"
                    )
            if donor_path is None:
                donor_path = donor_seed

            retarget_donor_used = donor_path
            retarget_data = run_xanim_retarget_step(
                repo_root=repo_root,
                input_files=xanim_exports,
                donor=donor_path,
                output_root=retarget_root,
                skeleton_map=skeleton_map_path or resolve_path(args.xanim_skeleton_map, repo_root),
                min_match_ratio=float(args.xanim_retarget_min_match_ratio),
                strict=bool(args.xanim_retarget_strict),
                verbose=args.verbose_converter,
            )
            retargeted_files = [Path(path) for path in retarget_data.get("retargeted_files", [])]
            if retargeted_files:
                passthrough = [path for path in converted_anims if path.suffix.lower() != ".xanim_export"]
                converted_anims = passthrough + retargeted_files
            report["steps"]["xanim_retarget"] = {
                "status": "ok",
                "report": str(retarget_root / "retarget_xanim_report.json"),
                "donor": str(donor_path),
                "donor_seed": str(donor_seed),
                "donor_seed_meta": donor_seed_meta,
                "retargeted_count": len(retargeted_files),
                "warn_count": retarget_data.get("counts", {}).get("warn", 0),
                "final_status": retarget_data.get("final_status", "unknown"),
            }
            if auto_donor_data:
                report["steps"]["xanim_retarget"]["auto_donor"] = auto_donor_data
        else:
            report["steps"]["xanim_retarget"] = {"status": "skipped", "reason": "no xanim_export files to retarget"}

    if args.normalize_xanims:
        xanim_exports = [path for path in converted_anims if path.suffix.lower() == ".xanim_export"]
        if xanim_exports:
            normalize_root = output_root / "normalize_xanim"
            normalize_data = run_xanim_normalize_step(
                repo_root=repo_root,
                input_files=xanim_exports,
                output_root=normalize_root,
                donor=retarget_donor_used,
                skeleton_map=skeleton_map_path,
                fill_mode=str(args.xanim_normalize_fill_mode),
                max_offset=float(args.xanim_normalize_max_offset),
                orthonormalize=bool(args.xanim_normalize_orthonormalize),
                verbose=args.verbose_converter,
            )
            normalized_files = [Path(path) for path in normalize_data.get("normalized_files", [])]
            if normalized_files:
                passthrough = [path for path in converted_anims if path.suffix.lower() != ".xanim_export"]
                converted_anims = passthrough + normalized_files
            report["steps"]["xanim_normalize"] = {
                "status": "ok",
                "report": str(normalize_root / "normalize_xanim_report.json"),
                "normalized_count": len(normalized_files),
                "final_status": normalize_data.get("final_status", "unknown"),
                "fill_mode": str(args.xanim_normalize_fill_mode),
                "max_offset": float(args.xanim_normalize_max_offset),
                "orthonormalize": bool(args.xanim_normalize_orthonormalize),
            }
        else:
            report["steps"]["xanim_normalize"] = {"status": "skipped", "reason": "no xanim_export files to normalize"}

    blender_project_root = blender_output_root / blender_project_name
    integration_project_name = integration_zone_name
    integration_project_root, weapon_anim_patch = build_integration_project(
        output_root=output_root,
        integration_project_name=integration_project_name,
        blender_project_root=blender_project_root,
        transfer_root=transfer_root,
        view_xmodel=view_xmodel,
        world_xmodel=world_xmodel,
        converted_anims=converted_anims,
        auto_patch_raygun_anims=bool(args.auto_patch_raygun_anims),
        weapon_hud_icon_material=str(args.weapon_hud_icon_material),
        weapon_kill_icon_material=str(args.weapon_kill_icon_material),
        weapon_camo=str(args.weapon_camo),
    )
    report["steps"]["weapon_anim_patch"] = {
        "status": "ok",
        "files": weapon_anim_patch,
    }
    remaining_raygun = [
        rel
        for rel, info in weapon_anim_patch.items()
        if (info.get("raygun_refs_after") or [])
    ]
    if remaining_raygun:
        report["warnings"].append(
            f"raygun anim refs still present after patch step: {remaining_raygun}"
        )
    custom_xanim_zone_ff: Path | None = None
    if args.compile_custom_xanim_zone:
        staged_xanim_root = integration_project_root / "zone_raw" / integration_project_name / "xanim_export"
        compiler_script = resolve_path(args.custom_xanim_compiler, repo_root)
        if not compiler_script.exists():
            raise FileNotFoundError(f"custom xanim compiler not found: {compiler_script}")
        compile_result = run_custom_xanim_zone_compile(
            repo_root=repo_root,
            xanim_dir=staged_xanim_root,
            output_dir=output_root / "custom_xanim_zone",
            zone_name=custom_xanim_zone_name,
            xanim_pattern=str(args.custom_xanim_pattern),
            compiler_script=compiler_script,
            stub_numframes=int(args.custom_xanim_stub_numframes),
            stub_is_default=bool(args.custom_xanim_stub_is_default),
            bone_count_profile=str(args.custom_xanim_bone_count_profile),
            emit_mode=str(args.custom_xanim_emit_mode),
            ensure_bones=parse_csv_names(str(args.custom_xanim_ensure_bones)),
            verbose=args.verbose_converter,
        )
        if compile_result.get("status") == "ok":
            custom_xanim_zone_ff = Path(str(compile_result.get("ff_path", "")))
        report["steps"]["custom_xanim_zone"] = compile_result
    else:
        report["steps"]["custom_xanim_zone"] = {"status": "skipped", "reason": "compile_custom_xanim_zone not enabled"}

    report["steps"]["convert"] = {
        "status": "ok",
        "mode": args.converter_mode,
        "converted_models": [str(p) for p in converted_models],
        "converted_anims": [str(p) for p in converted_anims],
    }
    report["steps"]["blender_convert"] = {
        "status": "ok",
        "report": str(blender_report_path),
        "view_xmodel": view_xmodel,
        "world_xmodel": world_xmodel,
    }
    report["steps"]["integration_project"] = {
        "status": "ok",
        "project_root": str(integration_project_root),
        "zone_file": str(integration_project_root / "zone_source" / f"{integration_project_name}.zone"),
        "xanim_inputs": len(converted_anims),
    }

    integration_zone_file = integration_project_root / "zone_source" / f"{integration_project_name}.zone"
    integration_zone_raw_root = integration_project_root / "zone_raw" / integration_project_name
    if args.stage_utility_xmodels:
        utility_names = parse_csv_names(str(args.required_utility_xmodels))
        if not utility_names:
            raise RuntimeError("stage_utility_xmodels=true but required_utility_xmodels resolved to empty list")
        utility_data = stage_required_utility_xmodels(
            repo_root=repo_root,
            zone_raw_root=integration_zone_raw_root,
            xmodel_names=utility_names,
            source_hint=str(args.utility_xmodel_source_root),
        )
        fallback_materials = parse_csv_names(str(args.required_fallback_materials))
        for extra_material in (
            str(args.weapon_hud_icon_material).strip(),
            str(args.weapon_kill_icon_material).strip(),
        ):
            if extra_material and extra_material not in fallback_materials:
                fallback_materials.append(extra_material)
        utility_materials: List[Dict[str, Any]] = []
        chosen_techset = str(args.pinned_techset if args.stage_pinned_techset else args.material_default_techset)
        for material_name in fallback_materials:
            utility_materials.append(
                ensure_minimal_material(
                    zone_raw_root=integration_zone_raw_root,
                    material_name=material_name,
                    techset_name=chosen_techset,
                )
            )
        zone_added_xmodels = append_unique_zone_lines(
            zone_path=integration_zone_file,
            lines_to_add=[f"xmodel,{name}" for name in utility_data.get("staged_xmodels", [])],
        )
        zone_added_materials = append_unique_zone_lines(
            zone_path=integration_zone_file,
            lines_to_add=[f"material,{item.get('material', '')}" for item in utility_materials if item.get("material")],
        )
        utility_data["utility_materials"] = utility_materials
        utility_data["zone_lines_appended_xmodels"] = int(zone_added_xmodels)
        utility_data["zone_lines_appended_materials"] = int(zone_added_materials)
        utility_data["zone_lines_appended"] = int(zone_added_xmodels) + int(zone_added_materials)
        report["steps"]["utility_xmodels"] = utility_data
    else:
        report["steps"]["utility_xmodels"] = {
            "status": "skipped",
            "reason": "stage_utility_xmodels disabled",
        }

    if args.stage_pinned_techset:
        pinned_data = stage_pinned_techset_bundle(
            repo_root=repo_root,
            zone_raw_root=integration_zone_raw_root,
            zone_file=integration_zone_file,
            techset_name=str(args.pinned_techset),
            source_hint=str(args.pinned_techset_source_root),
        )
        report["steps"]["pinned_techset"] = pinned_data
    else:
        report["steps"]["pinned_techset"] = {
            "status": "skipped",
            "reason": "stage_pinned_techset disabled",
        }

    material_report_path = output_root / "material_translation_report.json"
    material_data = run_material_translate_step(
        repo_root=repo_root,
        project_root=integration_project_root,
        project_name=integration_project_name,
        blender_report=blender_report_path,
        output_report=material_report_path,
        material_default_techset=str(args.material_default_techset),
        material_lit_techset=str(args.material_lit_techset),
        material_unlit_techset=str(args.material_unlit_techset),
        bundle_report=(transfer_root / "t7_bundle_report.json"),
        verbose=args.verbose_converter,
    )
    report["steps"]["material_translate"] = {
        "status": "ok",
        "report": str(material_report_path),
        "default_techset": str(args.material_default_techset),
        "lit_techset": str(args.material_lit_techset),
        "unlit_techset": str(args.material_unlit_techset),
        "generated_materials": material_data.get("counts", {}).get("generated_materials", 0),
        "staged_images": material_data.get("counts", {}).get("staged_images", 0),
        "zone_lines_appended": material_data.get("counts", {}).get("zone_lines_appended", 0),
    }
    material_techsets = collect_material_techsets(integration_zone_raw_root / "materials")
    techset_counts = material_techsets.get("counts", {})
    unreadable_materials = material_techsets.get("unreadable", [])
    report["steps"]["material_techset_guard"] = {
        "status": "ok",
        "counts": techset_counts,
        "unreadable_files": unreadable_materials,
    }
    if unreadable_materials:
        raise RuntimeError(f"Unreadable material JSON files: {unreadable_materials[:8]}")
    if args.stage_pinned_techset:
        pinned = str(args.pinned_techset).strip()
        unexpected = sorted(name for name in techset_counts.keys() if name.strip().lower() != pinned.lower())
        if unexpected:
            raise RuntimeError(
                "Material techniqueset drift detected while stage_pinned_techset=true. "
                f"Expected only '{pinned}', found: {unexpected}"
            )
        zone_sync = sync_zone_techset_lines(zone_path=integration_zone_file, techsets=[pinned])
        report["steps"]["material_techset_guard"]["zone_sync"] = zone_sync

    preflight = preflight_validate_outputs(
        blender_rows=ok_rows,
        zone_raw_root=integration_project_root / "zone_raw" / integration_project_name,
        view_xmodel=view_xmodel,
        world_xmodel=world_xmodel,
        min_view_glb_bytes=max(1, int(args.min_view_glb_bytes)),
        min_world_glb_bytes=max(1, int(args.min_world_glb_bytes)),
        require_no_raygun_anims=not bool(args.allow_raygun_anims),
    )
    report["steps"]["preflight"] = preflight
    report["warnings"].extend(preflight.get("warnings", []))

    if args.run_fidelity_audit:
        fidelity_report_path = output_root / "fidelity_audit_report.json"
        fidelity_data = run_fidelity_audit_step(
            repo_root=repo_root,
            blender_report=blender_report_path,
            output_report=fidelity_report_path,
            verbose=args.verbose_converter,
        )
        report["steps"]["fidelity_audit"] = {
            "status": "ok",
            "report": str(fidelity_report_path),
            "final_status": fidelity_data.get("final_status", "unknown"),
            "issues_total": fidelity_data.get("counts", {}).get("issues_total", 0),
            "fail": fidelity_data.get("counts", {}).get("fail", 0),
            "warn": fidelity_data.get("counts", {}).get("warn", 0),
        }
        if fidelity_data.get("final_status") == "fail":
            report["warnings"].append("fidelity_audit reported fail status")
            if args.strict_preflight:
                report["steps"]["compile"] = {
                    "status": "skipped",
                    "reason": "strict_preflight blocked compile due to fidelity_audit fail",
                }
                report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
                print(f"Saved E2E report: {report_path}")
                print(
                    f"project={integration_project_name} "
                    f"view_xmodel={view_xmodel} "
                    f"world_xmodel={world_xmodel} "
                    "compile=skipped(preflight)"
                )
                return

    if args.strict_preflight and preflight.get("status") != "pass":
        report["steps"]["compile"] = {
            "status": "skipped",
            "reason": "strict_preflight blocked compile due to preflight errors",
            "preflight_errors": preflight.get("errors", []),
        }
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Saved E2E report: {report_path}")
        print(
            f"project={integration_project_name} "
            f"view_xmodel={view_xmodel} "
            f"world_xmodel={world_xmodel} "
            "compile=skipped(preflight)"
        )
        return

    if args.compile:
        finalize_report = output_root / "finalize_integration_report.json"
        runtime_load_zones = [str(item) for item in (args.load_zones or [])]
        if custom_xanim_zone_ff and custom_xanim_zone_ff.exists():
            if str(custom_xanim_zone_ff) not in runtime_load_zones:
                runtime_load_zones.append(str(custom_xanim_zone_ff))
        finalize_cmd = [
            sys.executable,
            str(repo_root / "tools" / "asset_port_pipeline" / "finalize_bo2_integration.py"),
            "--project-root",
            str(integration_project_root),
            "--project-name",
            integration_project_name,
            "--output-root",
            str(output_root / "integration_ready"),
            "--bundle-name",
            integration_project_name,
            "--compile",
            "--linker",
            str(resolve_path(args.linker, repo_root)),
            "--output-report",
            str(finalize_report),
        ]
        if runtime_load_zones:
            finalize_cmd.extend(["--load-zones", *runtime_load_zones])
        if args.install_zone_dir:
            finalize_cmd.extend(["--install-zone-dir", str(resolve_path(args.install_zone_dir, repo_root))])

        proc = run_cmd(finalize_cmd, cwd=repo_root)
        if proc.returncode != 0:
            report["steps"]["compile"] = {
                "status": "error",
                "stdout": proc.stdout[-4000:],
                "stderr": proc.stderr[-4000:],
                "report": str(finalize_report),
            }
        else:
            final_data = json.loads(finalize_report.read_text(encoding="utf-8"))
            compile_status = (
                final_data.get("compile", {}).get("linker_result", {}).get("status", "unknown")
            )
            report["steps"]["compile"] = {
                "status": "ok" if compile_status == "pass" else "fail",
                "compile_status": compile_status,
                "report": str(finalize_report),
                "load_zones": runtime_load_zones,
            }

            if compile_status != "pass" and args.remediate_on_fail:
                remediation_report = output_root / "remediate_report.json"
                dep_roots = [resolve_path(item, repo_root) for item in args.dependency_roots]
                if not dep_roots:
                    dep_roots = [
                        repo_root / "zone_dump" / "zone_raw",
                        repo_root / "_build" / "t6_asset_dump" / "zone_raw",
                        transfer_root / "t7_bundle" / "staged",
                    ]

                remediate_cmd = [
                    sys.executable,
                    str(repo_root / "tools" / "asset_port_pipeline" / "remediate_map_project.py"),
                    "--project-root",
                    str(integration_project_root),
                    "--project-name",
                    integration_project_name,
                    "--linker",
                    str(resolve_path(args.linker, repo_root)),
                    "--max-retries",
                    str(max(1, int(args.remediate_retries))),
                    "--output",
                    str(remediation_report),
                ]
                if runtime_load_zones:
                    remediate_cmd.extend(["--load-zones", *runtime_load_zones])
                if dep_roots:
                    remediate_cmd.append("--dependency-roots")
                    remediate_cmd.extend([str(path) for path in dep_roots])
                if args.remediate_prune_unresolved:
                    remediate_cmd.append("--prune-unresolved")

                rem_proc = run_cmd(remediate_cmd, cwd=repo_root)
                rem_data: Dict[str, Any] = {}
                rem_step: Dict[str, Any] = {
                    "status": "error" if rem_proc.returncode != 0 else "ok",
                    "report": str(remediation_report),
                }
                if rem_proc.returncode != 0:
                    rem_step["stdout"] = rem_proc.stdout[-4000:]
                    rem_step["stderr"] = rem_proc.stderr[-4000:]
                else:
                    rem_data = json.loads(remediation_report.read_text(encoding="utf-8"))
                    rem_step["final_status"] = rem_data.get("final", {}).get("status", "unknown")
                    rem_step["attempts"] = len(rem_data.get("attempts", []))
                    rem_step["load_zones_used"] = rem_data.get("final", {}).get("load_zones_used", [])
                report["steps"]["remediation"] = rem_step

                # Re-run finalize compile after remediation edits.
                finalize_report_after = output_root / "finalize_integration_after_remediation_report.json"
                finalize_cmd_after = list(finalize_cmd)
                rem_final_load_zones = [str(x) for x in (rem_data.get("final", {}).get("load_zones_used") or [])]
                if rem_final_load_zones and bool(args.allow_remediation_load_zone_drift):
                    finalize_cmd_after = set_option_values(finalize_cmd_after, "--load-zones", rem_final_load_zones)
                elif rem_final_load_zones and not bool(args.allow_remediation_load_zone_drift):
                    report["warnings"].append(
                        "remediation suggested load-zone drift, but it was blocked by allow-remediation-load-zone-drift=false"
                    )
                try:
                    idx = finalize_cmd_after.index("--output-report")
                    finalize_cmd_after[idx + 1] = str(finalize_report_after)
                except Exception:
                    finalize_cmd_after.extend(["--output-report", str(finalize_report_after)])
                proc_after = run_cmd(finalize_cmd_after, cwd=repo_root)
                if proc_after.returncode == 0 and finalize_report_after.exists():
                    final_after_data = json.loads(finalize_report_after.read_text(encoding="utf-8"))
                    compile_status_after = final_after_data.get("compile", {}).get("linker_result", {}).get("status", "unknown")
                    report["steps"]["compile_after_remediation"] = {
                        "status": "ok" if compile_status_after == "pass" else "fail",
                        "compile_status": compile_status_after,
                        "report": str(finalize_report_after),
                        "load_zones": final_after_data.get("compile", {}).get("load_zones", []),
                    }
                else:
                    report["steps"]["compile_after_remediation"] = {
                        "status": "error",
                        "stdout": proc_after.stdout[-4000:],
                        "stderr": proc_after.stderr[-4000:],
                        "report": str(finalize_report_after),
                    }
    else:
        report["steps"]["compile"] = {"status": "skipped", "reason": "compile flag not set"}

    if args.install_zone_dir and custom_xanim_zone_ff and custom_xanim_zone_ff.exists():
        install_dir = resolve_path(args.install_zone_dir, repo_root)
        install_dir.mkdir(parents=True, exist_ok=True)
        dst = install_dir / custom_xanim_zone_ff.name
        shutil.copy2(custom_xanim_zone_ff, dst)
        report["steps"]["install_custom_xanim_zone"] = {
            "status": "ok",
            "source": str(custom_xanim_zone_ff),
            "destination": str(dst),
        }
    elif args.compile_custom_xanim_zone:
        report["steps"]["install_custom_xanim_zone"] = {
            "status": "skipped",
            "reason": "no install-zone-dir or custom xanim ff missing",
        }

    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Saved E2E report: {report_path}")
    final_compile_state = report["steps"].get("compile_after_remediation", report["steps"].get("compile", {}))
    print(
        f"project={integration_project_name} "
        f"view_xmodel={view_xmodel} "
        f"world_xmodel={world_xmodel} "
        f"compile={final_compile_state.get('status', 'unknown')}"
    )


if __name__ == "__main__":
    main()
