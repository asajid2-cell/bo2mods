#!/usr/bin/env python3
"""Build a minimal set of T6 fastfiles to isolate custom-writer failures.

This harness intentionally avoids gameplay/runtime complexity and focuses on the
smallest possible question:

1. Can the release linker emit a tiny stock-only FF that the stable Unlinker
   can parse?
2. Can the custom/dev linker emit the same tiny stock-only FF safely?
3. Can the custom/dev linker emit a tiny custom raw-FX FF safely when that FX
   references only stock surfaces?

The answers tell us whether the current blocker is:
- writer/block layout in the custom linker
- the raw custom asset path
- or something later at runtime
"""

from __future__ import annotations

import argparse
import hashlib
import os
import json
import re
import shutil
import struct
import subprocess
import sys
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "_build" / "ff_contract_probe"
OUTPUT = WORK / "output"
ZONE_SOURCE = WORK / "zone_source"
FX_DIR = WORK / "fx" / "zombie"
MATERIALS_DIR = WORK / "materials"
IMAGES_DIR = WORK / "images"
REPORT_PATH = WORK / "ff_contract_probe_report.json"

OAT_RELEASE_DIR = ROOT / "_build" / "oat_release" / "unzipped"
RELEASE_LINKER = OAT_RELEASE_DIR / "Linker.exe"
RELEASE_UNLINKER = OAT_RELEASE_DIR / "Unlinker.exe"
DEV_LINKER = ROOT / "tools" / "oat" / "Linker.exe"
DEV_UNLINKER = ROOT / "tools" / "oat" / "Unlinker.exe"

PE_MACHINE_X86 = 0x14C
PE_MACHINE_X64 = 0x8664

STOCK_LOAD_FFS = [
    ROOT / "zone" / "all" / "patch_zm.ff",
    ROOT / "zone" / "all" / "code_post_gfx_zm.ff",
    ROOT / "zone" / "all" / "zm_transit.ff",
    ROOT / "zone" / "english" / "en_zm_transit.ff",
    ROOT / "zone" / "all" / "dlc4_load_zm.ff",
    ROOT / "zone" / "english" / "en_dlc4_load_zm.ff",
    ROOT / "zone" / "all" / "zm_tomb_patch.ff",
    ROOT / "zone" / "all" / "zm_tomb.ff",
    ROOT / "zone" / "all" / "common_zm.ff",
    ROOT / "_build" / "ff_backup" / "20260213-123213" / "so_zsurvival_zm_transit.ff",
]

SUPPORT_ROOTS = [
    ROOT / "zone_dump",
    ROOT / "_build" / "runtime_unlink_debug",
    ROOT / "_build" / "runtime_unlink_zm_transit_clean2",
    ROOT / "_build" / "runtime_unlink_zm_transit_patch_2",
]

SOURCE_DEBUG_ORB = ROOT / "_build" / "bo3_rev_idg_probe" / "fx" / "zombie" / "fx_bo3_rev_debug_orb_stock.efx"
SOURCE_STOCK_GLOW_MATERIAL = ROOT / "zone_dump" / "materials" / "gfx_fxt_light_glow_square_gr.json"
SOURCE_STOCK_GLOW_IMAGE_IWI = ROOT / "_build" / "stock_iwi_dump" / "images" / "fxt_light_glow_square.iwi"
SOURCE_STOCK_FMT0D_IMAGE_IWI = ROOT / "_build" / "stock_iwi_dump" / "images" / "fxt_debris_fire_ember_cloud_01.iwi"
STOCK_FMT0D_IMAGE_NAME = "fxt_debris_fire_ember_cloud_01"
STOCK_FMT0D_GLOW_MATERIAL = "ffprobe_stock_fmt0d_glow"
CUSTOM_ORB_ASSET = "zombie/fx_ffprobe_debug_orb_stock"
STOCK_MARKER_ASSET = "maps/zombie/fx_zmb_tranzit_marker_glow"
BO3_PROBE_ROOT = ROOT / "_build" / "bo3_rev_idg_probe"
BO3_HOLE_MD_ASSET = "zombie/fx_idgun_hole_md_zod_zmb"

BUILD_FAILURE_PATTERNS = (
    "Loading fastfile failed:",
    "Failed to load zone ",
    "Missing asset ",
    "Could not load asset ",
    "Failed to load material ",
    "Cannot load material ",
    "Missing material dependency ",
)


def read_pe_machine(path: Path) -> int:
    with path.open("rb") as handle:
        mz_header = handle.read(64)
        if len(mz_header) < 64:
            raise RuntimeError(f"PE header too small: {path}")
        pe_offset = struct.unpack_from("<I", mz_header, 0x3C)[0]
        handle.seek(pe_offset + 4)
        machine_bytes = handle.read(2)
        if len(machine_bytes) < 2:
            raise RuntimeError(f"PE machine field missing: {path}")
        return struct.unpack("<H", machine_bytes)[0]


def pe_machine_label(machine: int) -> str:
    if machine == PE_MACHINE_X86:
        return "x86"
    if machine == PE_MACHINE_X64:
        return "x64"
    return hex(machine)


def verify_t6_oat_binary_architectures() -> dict[str, str]:
    """T6 DB asset layouts are 32-bit; the custom OAT runtime lane must stay x86."""
    tools = {
        "release_linker": RELEASE_LINKER,
        "release_unlinker": RELEASE_UNLINKER,
        "dev_linker": DEV_LINKER,
        "dev_unlinker": DEV_UNLINKER,
    }
    out: dict[str, str] = {}
    for label, path in tools.items():
        if not path.exists():
            raise RuntimeError(f"Missing required OAT binary for {label}: {path}")
        machine = read_pe_machine(path)
        out[label] = pe_machine_label(machine)
        if machine != PE_MACHINE_X86:
            raise RuntimeError(
                f"T6 FF probe requires x86 OAT binaries for 32-bit DB asset layouts; "
                f"{label} is {pe_machine_label(machine)} at {path}"
            )
    return out


@dataclass
class ProbeCase:
    name: str
    linker: Path
    zone_name: str
    fx_assets: list[str]
    use_stock_loads: bool
    techniqueset_assets: list[str] | None = None
    material_assets: list[str] | None = None
    image_assets: list[str] | None = None
    stage_custom_orb: bool = False
    stage_stock_glow_surface: bool = False
    stage_stock_fmt0d_surface: bool = False
    custom_orb_asset: str | None = None
    custom_orb_material: str | None = None
    extra_search_roots: list[Path] | None = None
    load_case_names: list[str] | None = None


CASES = [
    ProbeCase(
        name="release_stock_marker",
        linker=RELEASE_LINKER,
        zone_name="ffprobe_release_stock_marker",
        fx_assets=[STOCK_MARKER_ASSET],
        material_assets=[],
        image_assets=[],
        use_stock_loads=True,
    ),
    ProbeCase(
        name="dev_load_release_stock_marker",
        linker=DEV_LINKER,
        zone_name="ffprobe_dev_load_release_stock_marker",
        fx_assets=[STOCK_MARKER_ASSET],
        material_assets=[],
        image_assets=[],
        use_stock_loads=False,
        load_case_names=["release_stock_marker"],
    ),
    ProbeCase(
        name="dev_stock_marker",
        linker=DEV_LINKER,
        zone_name="ffprobe_dev_stock_marker",
        fx_assets=[STOCK_MARKER_ASSET],
        material_assets=[],
        image_assets=[],
        use_stock_loads=True,
    ),
    ProbeCase(
        name="release_techset_stock_surface",
        linker=RELEASE_LINKER,
        zone_name="ffprobe_release_techset_stock_surface",
        fx_assets=[],
        techniqueset_assets=["effect_26z423jf"],
        material_assets=[],
        image_assets=[],
        use_stock_loads=False,
        extra_search_roots=SUPPORT_ROOTS,
    ),
    ProbeCase(
        name="dev_load_release_techset_stock_surface",
        linker=DEV_LINKER,
        zone_name="ffprobe_dev_load_release_techset_stock_surface",
        fx_assets=[],
        techniqueset_assets=[],
        material_assets=[],
        image_assets=[],
        use_stock_loads=False,
        load_case_names=["release_techset_stock_surface"],
    ),
    ProbeCase(
        name="release_material_stock_surface",
        linker=RELEASE_LINKER,
        zone_name="ffprobe_release_material_stock_surface",
        fx_assets=[],
        material_assets=["gfx_fxt_light_glow_square_gr"],
        image_assets=["fxt_light_glow_square"],
        use_stock_loads=False,
        stage_stock_glow_surface=True,
        extra_search_roots=SUPPORT_ROOTS,
    ),
    ProbeCase(
        name="dev_load_release_material_stock_surface",
        linker=DEV_LINKER,
        zone_name="ffprobe_dev_load_release_material_stock_surface",
        fx_assets=[],
        techniqueset_assets=[],
        material_assets=[],
        image_assets=[],
        use_stock_loads=False,
        load_case_names=["release_material_stock_surface"],
    ),
    ProbeCase(
        name="release_custom_orb_stock_surface",
        linker=RELEASE_LINKER,
        zone_name="ffprobe_release_custom_orb_stock_surface",
        fx_assets=[CUSTOM_ORB_ASSET],
        material_assets=["gfx_fxt_light_glow_square_gr"],
        image_assets=["fxt_light_glow_square"],
        use_stock_loads=False,
        stage_custom_orb=True,
        stage_stock_glow_surface=True,
        extra_search_roots=SUPPORT_ROOTS,
    ),
    ProbeCase(
        name="dev_image_only_stock_surface",
        linker=DEV_LINKER,
        zone_name="ffprobe_dev_image_only_stock_surface",
        fx_assets=[],
        material_assets=[],
        image_assets=["fxt_light_glow_square"],
        use_stock_loads=False,
        stage_stock_glow_surface=True,
    ),
    ProbeCase(
        name="dev_techset_stock_surface",
        linker=DEV_LINKER,
        zone_name="ffprobe_dev_techset_stock_surface",
        fx_assets=[],
        techniqueset_assets=["effect_26z423jf"],
        material_assets=[],
        image_assets=[],
        use_stock_loads=False,
        extra_search_roots=SUPPORT_ROOTS,
    ),
    ProbeCase(
        name="dev_material_stock_surface",
        linker=DEV_LINKER,
        zone_name="ffprobe_dev_material_stock_surface",
        fx_assets=[],
        material_assets=["gfx_fxt_light_glow_square_gr"],
        image_assets=["fxt_light_glow_square"],
        use_stock_loads=False,
        stage_stock_glow_surface=True,
        extra_search_roots=SUPPORT_ROOTS,
    ),
    ProbeCase(
        name="dev_custom_orb_stock_surface",
        linker=DEV_LINKER,
        zone_name="ffprobe_dev_custom_orb_stock_surface",
        fx_assets=[CUSTOM_ORB_ASSET],
        material_assets=["gfx_fxt_light_glow_square_gr"],
        image_assets=["fxt_light_glow_square"],
        use_stock_loads=False,
        stage_custom_orb=True,
        stage_stock_glow_surface=True,
        extra_search_roots=SUPPORT_ROOTS,
    ),
    ProbeCase(
        name="dev_custom_orb_phosphorous_surface",
        linker=DEV_LINKER,
        zone_name="ffprobe_dev_custom_orb_phosphorous_surface",
        fx_assets=["zombie/fx_ffprobe_debug_orb_phosphorous"],
        material_assets=["gfx_light_phosphorous_em"],
        image_assets=["fxt_light_phosphorous"],
        use_stock_loads=False,
        stage_custom_orb=True,
        custom_orb_asset="zombie/fx_ffprobe_debug_orb_phosphorous",
        custom_orb_material="gfx_light_phosphorous_em",
        extra_search_roots=[BO3_PROBE_ROOT, *SUPPORT_ROOTS],
    ),
    ProbeCase(
        name="dev_custom_orb_fog_surface",
        linker=DEV_LINKER,
        zone_name="ffprobe_dev_custom_orb_fog_surface",
        fx_assets=["zombie/fx_ffprobe_debug_orb_fog"],
        material_assets=["gfx_fog_slow_lg_anim_em_i1024"],
        image_assets=["fxt_fog_slow_lg_anim"],
        use_stock_loads=False,
        stage_custom_orb=True,
        custom_orb_asset="zombie/fx_ffprobe_debug_orb_fog",
        custom_orb_material="gfx_fog_slow_lg_anim_em_i1024",
        extra_search_roots=[BO3_PROBE_ROOT, *SUPPORT_ROOTS],
    ),
    ProbeCase(
        name="dev_custom_orb_custom_stockglow_surface",
        linker=DEV_LINKER,
        zone_name="ffprobe_dev_custom_orb_custom_stockglow_surface",
        fx_assets=["zombie/fx_ffprobe_debug_orb_custom_stockglow"],
        material_assets=["bo3_rev_debug_stock_glow"],
        image_assets=["fxt_light_glow_square"],
        use_stock_loads=False,
        stage_custom_orb=True,
        custom_orb_asset="zombie/fx_ffprobe_debug_orb_custom_stockglow",
        custom_orb_material="bo3_rev_debug_stock_glow",
        extra_search_roots=[BO3_PROBE_ROOT, *SUPPORT_ROOTS],
    ),
    ProbeCase(
        name="dev_custom_orb_stock_fmt0d_surface",
        linker=DEV_LINKER,
        zone_name="ffprobe_dev_custom_orb_stock_fmt0d_surface",
        fx_assets=["zombie/fx_ffprobe_debug_orb_stock_fmt0d"],
        material_assets=[STOCK_FMT0D_GLOW_MATERIAL],
        image_assets=[STOCK_FMT0D_IMAGE_NAME],
        use_stock_loads=False,
        stage_custom_orb=True,
        stage_stock_fmt0d_surface=True,
        custom_orb_asset="zombie/fx_ffprobe_debug_orb_stock_fmt0d",
        custom_orb_material=STOCK_FMT0D_GLOW_MATERIAL,
        extra_search_roots=[BO3_PROBE_ROOT, *SUPPORT_ROOTS],
    ),
    ProbeCase(
        name="dev_bo3_hole_md_surface",
        linker=DEV_LINKER,
        zone_name="ffprobe_dev_bo3_hole_md_surface",
        fx_assets=[BO3_HOLE_MD_ASSET],
        material_assets=["gfx_fxt_light_glow_square_gr", "gfx_fxt_env_dust_mote_add"],
        image_assets=["fxt_light_glow_square", "fxt_env_dust_mote_atlas"],
        use_stock_loads=False,
        stage_stock_glow_surface=True,
        extra_search_roots=[BO3_PROBE_ROOT, *SUPPORT_ROOTS],
    ),
]


def reset_dirs() -> None:
    if WORK.exists():
        shutil.rmtree(WORK)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    ZONE_SOURCE.mkdir(parents=True, exist_ok=True)
    FX_DIR.mkdir(parents=True, exist_ok=True)
    MATERIALS_DIR.mkdir(parents=True, exist_ok=True)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run_capture(args: list[str], cwd: Path | None = None, env: dict[str, str] | None = None) -> tuple[int, str]:
    result = subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        env=env,
    )
    stdout = (result.stdout or b"").decode("utf-8", errors="replace")
    stderr = (result.stderr or b"").decode("utf-8", errors="replace")
    text = stdout + stderr
    return result.returncode, text


def parse_unlinker_list(text: str) -> list[str]:
    lines: list[str] = []
    in_content = False
    for raw in text.splitlines():
        line = raw.strip()
        if line == "Content:":
            in_content = True
            continue
        if not in_content or not line:
            continue
        lines.append(line)
    return lines


def read_head_hex(path: Path, count: int = 32) -> str:
    with path.open("rb") as handle:
        return handle.read(count).hex(" ")


def extract_build_problems(text: str) -> list[str]:
    problems: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if any(pattern in line for pattern in BUILD_FAILURE_PATTERNS):
            problems.append(line)
    return problems


def write_zone_source(
    zone_name: str,
    fx_assets: list[str],
    techniqueset_assets: list[str] | None = None,
    material_assets: list[str] | None = None,
    image_assets: list[str] | None = None,
) -> Path:
    zone_path = ZONE_SOURCE / f"{zone_name}.zone"
    include_ipak = bool(image_assets)
    lines = [
        "// Call Of Duty: Black Ops II",
        ">game,T6",
        *( [f">ipak,{zone_name}"] if include_ipak else [] ),
        "",
        "// Auto-generated minimal FF contract probe",
        *[f"fx,{name}" for name in fx_assets],
        *[f"techniqueset,{name}" for name in (techniqueset_assets or [])],
        *[f"material,{name}" for name in (material_assets or [])],
        *[f"image,{name}" for name in (image_assets or [])],
        "",
    ]
    zone_path.write_text("\n".join(lines), encoding="utf-8")
    return zone_path


def stage_custom_orb(asset_name: str = CUSTOM_ORB_ASSET, material_name: str = "gfx_fxt_light_glow_square_gr") -> Path:
    if not SOURCE_DEBUG_ORB.exists():
        raise FileNotFoundError(f"Missing source custom orb template: {SOURCE_DEBUG_ORB}")
    asset_basename = asset_name.split("/", 1)[-1].strip()
    editor_name = asset_basename
    dst = FX_DIR / f"{asset_basename}.efx"
    text = SOURCE_DEBUG_ORB.read_text(encoding="utf-8", errors="replace")
    text = re.sub(r'name\s+"[^"]+";', f'name "{editor_name}";', text, count=1)
    text = re.sub(r'"gfx_fxt_light_glow_square_gr"', f'"{material_name}"', text, count=1)
    dst.write_text(text, encoding="utf-8")
    return dst


def stage_stock_glow_surface_deps() -> None:
    if not SOURCE_STOCK_GLOW_MATERIAL.exists():
        raise FileNotFoundError(f"Missing stock glow material source: {SOURCE_STOCK_GLOW_MATERIAL}")
    if not SOURCE_STOCK_GLOW_IMAGE_IWI.exists():
        raise FileNotFoundError(f"Missing stock glow image source: {SOURCE_STOCK_GLOW_IMAGE_IWI}")
    shutil.copy2(SOURCE_STOCK_GLOW_MATERIAL, MATERIALS_DIR / SOURCE_STOCK_GLOW_MATERIAL.name)
    shutil.copy2(SOURCE_STOCK_GLOW_IMAGE_IWI, IMAGES_DIR / SOURCE_STOCK_GLOW_IMAGE_IWI.name)


def stage_stock_fmt0d_surface_deps() -> None:
    if not SOURCE_STOCK_GLOW_MATERIAL.exists():
        raise FileNotFoundError(f"Missing stock glow material source: {SOURCE_STOCK_GLOW_MATERIAL}")
    if not SOURCE_STOCK_FMT0D_IMAGE_IWI.exists():
        raise FileNotFoundError(f"Missing stock fmt0d image source: {SOURCE_STOCK_FMT0D_IMAGE_IWI}")
    material_json = json.loads(SOURCE_STOCK_GLOW_MATERIAL.read_text(encoding="utf-8"))
    material_json["debugName"] = STOCK_FMT0D_GLOW_MATERIAL
    if material_json.get("textures"):
        material_json["textures"][0]["image"] = STOCK_FMT0D_IMAGE_NAME
    out_path = MATERIALS_DIR / f"{STOCK_FMT0D_GLOW_MATERIAL}.json"
    out_path.write_text(json.dumps(material_json, indent=2) + "\n", encoding="utf-8")
    shutil.copy2(SOURCE_STOCK_FMT0D_IMAGE_IWI, IMAGES_DIR / SOURCE_STOCK_FMT0D_IMAGE_IWI.name)


def find_material_json(material_name: str, roots: list[Path]) -> Path | None:
    rel = Path("materials") / f"{material_name}.json"
    for root in roots:
        candidate = root / rel
        if candidate.exists():
            return candidate
    return None


def find_image_iwi(image_name: str, roots: list[Path]) -> Path | None:
    rel = Path("images") / f"{image_name}.iwi"
    for root in roots:
        candidate = root / rel
        if candidate.exists():
            return candidate
    return None


def find_techset_file(techset_name: str, roots: list[Path]) -> Path | None:
    rel = Path("techsets") / f"{techset_name}.techset"
    for root in roots:
        candidate = root / rel
        if candidate.exists():
            return candidate
    return None


def verify_techset_dependency_closure(case: ProbeCase, search_roots: list[Path]) -> dict[str, Any]:
    techset_reports: list[dict[str, Any]] = []
    ok = True
    for techset_name in case.techniqueset_assets or []:
        techset_path = find_techset_file(techset_name, search_roots)
        report = {
            "techniqueset": techset_name,
            "techniqueset_found": bool(techset_path),
            "techniqueset_path": str(techset_path) if techset_path else "",
        }
        if not techset_path:
            ok = False
        techset_reports.append(report)
    return {"ok": ok, "techsets": techset_reports}


def verify_material_dependency_closure(case: ProbeCase, search_roots: list[Path]) -> dict[str, Any]:
    material_reports: list[dict[str, Any]] = []
    ok = True
    for material_name in case.material_assets or []:
        material_path = find_material_json(material_name, search_roots)
        report: dict[str, Any] = {
            "material": material_name,
            "material_found": bool(material_path),
            "material_path": str(material_path) if material_path else "",
            "technique_set": "",
            "technique_set_found": False,
            "technique_set_path": "",
            "textures": [],
        }
        if not material_path:
            ok = False
            material_reports.append(report)
            continue

        try:
            material_json = json.loads(material_path.read_text(encoding="utf-8"))
        except Exception as exc:  # pragma: no cover - defensive in tooling
            report["parse_error"] = str(exc)
            ok = False
            material_reports.append(report)
            continue

        techset_name = str(material_json.get("techniqueSet") or "")
        report["technique_set"] = techset_name
        if techset_name:
            techset_path = find_techset_file(techset_name, search_roots)
            report["technique_set_found"] = bool(techset_path)
            report["technique_set_path"] = str(techset_path) if techset_path else ""
            if not techset_path:
                ok = False

        for texture in material_json.get("textures", []):
            image_name = texture.get("image", "")
            image_path = find_image_iwi(image_name, search_roots) if image_name else None
            report["textures"].append(
                {
                    "image": image_name,
                    "image_found": bool(image_path),
                    "image_path": str(image_path) if image_path else "",
                }
            )
            if image_name and not image_path:
                ok = False

        material_reports.append(report)

    return {"ok": ok, "materials": material_reports}


def build_case(case: ProbeCase, prior_results: dict[str, dict[str, object]]) -> dict[str, object]:
    if not case.linker.exists():
        raise FileNotFoundError(f"Missing linker for case {case.name}: {case.linker}")
    if not RELEASE_UNLINKER.exists():
        raise FileNotFoundError(f"Missing stable Unlinker: {RELEASE_UNLINKER}")
    if not DEV_UNLINKER.exists():
        raise FileNotFoundError(f"Missing dev Unlinker: {DEV_UNLINKER}")

    if case.stage_stock_glow_surface:
        stage_stock_glow_surface_deps()
    if case.stage_stock_fmt0d_surface:
        stage_stock_fmt0d_surface_deps()
    if case.stage_custom_orb:
        stage_custom_orb(case.custom_orb_asset or CUSTOM_ORB_ASSET, case.custom_orb_material or "gfx_fxt_light_glow_square_gr")

    zone_path = write_zone_source(
        case.zone_name,
        case.fx_assets,
        case.techniqueset_assets,
        case.material_assets,
        case.image_assets,
    )
    args = [
        str(case.linker),
        "--verbose",
        "--base-folder",
        str(WORK),
        "--add-asset-search-path",
        str(WORK),
        "--add-source-search-path",
        str(WORK),
        "--output-folder",
        str(OUTPUT),
    ]
    for load_case_name in case.load_case_names or []:
        prior_case = prior_results.get(load_case_name)
        if not prior_case:
            raise RuntimeError(f"Case {case.name} depends on missing prior case {load_case_name}")
        prior_ff = Path(str(prior_case["ff"]["path"]))
        if not prior_ff.exists():
            raise RuntimeError(f"Case {case.name} depends on missing FF from {load_case_name}: {prior_ff}")
        args.extend(["--load", str(prior_ff)])
    for root in case.extra_search_roots or []:
        if not root.exists():
            continue
        args.extend(
            [
                "--add-asset-search-path",
                str(root),
                "--add-source-search-path",
                str(root),
            ]
        )
    if case.use_stock_loads:
        for ff in STOCK_LOAD_FFS:
            args.extend(["--load", str(ff)])
    args.append(case.zone_name)

    search_roots = [WORK]
    for root in case.extra_search_roots or []:
        if root.exists():
            search_roots.append(root)
    dependency_report = verify_material_dependency_closure(case, search_roots)
    techset_dependency_report = verify_techset_dependency_closure(case, search_roots)

    debug_dump_dir = WORK / "debug" / case.name
    build_env = os.environ.copy()
    build_env["OAT_T6_TECHSET_DEBUG_DIR"] = str(debug_dump_dir)

    build_rc, build_text = run_capture(args, cwd=ROOT, env=build_env)
    build_problems = extract_build_problems(build_text)
    ff_path = OUTPUT / f"{case.zone_name}.ff"
    ff_exists = ff_path.exists()
    ff_meta = {
        "path": str(ff_path),
        "exists": ff_exists,
        "size": ff_path.stat().st_size if ff_exists else 0,
        "sha256": sha256(ff_path) if ff_exists else "",
        "head_hex_32": read_head_hex(ff_path, 32) if ff_exists else "",
    }

    unlink_args = [str(RELEASE_UNLINKER), "--list", str(ff_path)]
    unlink_rc, unlink_text = run_capture(unlink_args, cwd=ROOT) if ff_exists else (1, "ff missing")
    unlink_assets = parse_unlinker_list(unlink_text) if unlink_rc == 0 else []

    dev_unlink_args = [str(DEV_UNLINKER), "--list", str(ff_path)]
    dev_unlink_rc, dev_unlink_text = run_capture(dev_unlink_args, cwd=ROOT) if ff_exists else (1, "ff missing")
    dev_unlink_assets = parse_unlinker_list(dev_unlink_text) if dev_unlink_rc == 0 else []

    return {
        "name": case.name,
        "zone_name": case.zone_name,
        "linker": str(case.linker),
        "techset_debug_dir": str(debug_dump_dir),
        "fx_assets": case.fx_assets,
        "zone_source": str(zone_path),
        "build_returncode": build_rc,
        "build_ok": (
            build_rc == 0
            and ff_exists
            and dependency_report["ok"]
            and techset_dependency_report["ok"]
            and not build_problems
        ),
        "build_output": build_text,
        "build_problems": build_problems,
        "dependency_closure": dependency_report,
        "techset_dependency_closure": techset_dependency_report,
        "ff": ff_meta,
        "unlink_returncode": unlink_rc,
        "unlink_ok": unlink_rc == 0,
        "unlink_output": unlink_text,
        "unlink_assets": unlink_assets,
        "dev_unlink_returncode": dev_unlink_rc,
        "dev_unlink_ok": dev_unlink_rc == 0,
        "dev_unlink_output": dev_unlink_text,
        "dev_unlink_assets": dev_unlink_assets,
    }


def compare_cases(cases: list[dict[str, object]]) -> dict[str, object]:
    by_name = {case["name"]: case for case in cases}
    out: dict[str, object] = {}

    release_stock = by_name.get("release_stock_marker")
    dev_stock = by_name.get("dev_stock_marker")
    dev_load_release = by_name.get("dev_load_release_stock_marker")
    release_custom = by_name.get("release_custom_orb_stock_surface")
    release_techset = by_name.get("release_techset_stock_surface")
    dev_load_release_techset = by_name.get("dev_load_release_techset_stock_surface")
    release_material = by_name.get("release_material_stock_surface")
    dev_load_release_material = by_name.get("dev_load_release_material_stock_surface")
    dev_image = by_name.get("dev_image_only_stock_surface")
    dev_techset = by_name.get("dev_techset_stock_surface")
    dev_material = by_name.get("dev_material_stock_surface")
    dev_custom = by_name.get("dev_custom_orb_stock_surface")
    dev_bo3_hole_md = by_name.get("dev_bo3_hole_md_surface")

    if release_stock and dev_stock:
        out["release_vs_dev_stock"] = {
            "both_build_ok": bool(release_stock["build_ok"] and dev_stock["build_ok"]),
            "both_unlink_ok": bool(release_stock["unlink_ok"] and dev_stock["unlink_ok"]),
            "release_dev_unlink_ok": bool(release_stock["dev_unlink_ok"]),
            "same_size": release_stock["ff"]["size"] == dev_stock["ff"]["size"],
            "same_hash": release_stock["ff"]["sha256"] == dev_stock["ff"]["sha256"],
            "same_asset_list": release_stock["unlink_assets"] == dev_stock["unlink_assets"],
        }

    if dev_stock and dev_custom:
        out["dev_stock_vs_dev_custom"] = {
            "stock_build_ok": bool(dev_stock["build_ok"]),
            "custom_build_ok": bool(dev_custom["build_ok"]),
            "stock_unlink_ok": bool(dev_stock["unlink_ok"]),
            "custom_unlink_ok": bool(dev_custom["unlink_ok"]),
            "custom_dev_unlink_ok": bool(dev_custom["dev_unlink_ok"]),
            "stock_hash": dev_stock["ff"]["sha256"],
            "custom_hash": dev_custom["ff"]["sha256"],
        }

    if dev_material and dev_custom:
        out["dev_material_vs_dev_custom"] = {
            "material_build_ok": bool(dev_material["build_ok"]),
            "material_unlink_ok": bool(dev_material["unlink_ok"]),
            "material_dev_unlink_ok": bool(dev_material["dev_unlink_ok"]),
            "custom_build_ok": bool(dev_custom["build_ok"]),
            "custom_unlink_ok": bool(dev_custom["unlink_ok"]),
            "custom_dev_unlink_ok": bool(dev_custom["dev_unlink_ok"]),
            "material_hash": dev_material["ff"]["sha256"],
            "custom_hash": dev_custom["ff"]["sha256"],
        }

    if dev_image and dev_techset and dev_material:
        out["dev_surface_chain"] = {
            "image_build_ok": bool(dev_image["build_ok"]),
            "image_unlink_ok": bool(dev_image["unlink_ok"]),
            "image_dev_unlink_ok": bool(dev_image["dev_unlink_ok"]),
            "techset_build_ok": bool(dev_techset["build_ok"]),
            "techset_unlink_ok": bool(dev_techset["unlink_ok"]),
            "techset_dev_unlink_ok": bool(dev_techset["dev_unlink_ok"]),
            "material_build_ok": bool(dev_material["build_ok"]),
            "material_unlink_ok": bool(dev_material["unlink_ok"]),
            "material_dev_unlink_ok": bool(dev_material["dev_unlink_ok"]),
        }

    if release_stock and dev_load_release:
        out["release_ff_loaded_by_dev"] = {
            "dev_load_build_ok": bool(dev_load_release["build_ok"]),
            "dev_load_unlink_ok": bool(dev_load_release["unlink_ok"]),
            "dev_load_dev_unlink_ok": bool(dev_load_release["dev_unlink_ok"]),
            "dev_load_build_problems": dev_load_release["build_problems"],
        }

    if release_techset and dev_load_release_techset:
        out["release_techset_ff_loaded_by_dev"] = {
            "release_build_ok": bool(release_techset["build_ok"]),
            "release_unlink_ok": bool(release_techset["unlink_ok"]),
            "release_dev_unlink_ok": bool(release_techset["dev_unlink_ok"]),
            "dev_load_build_ok": bool(dev_load_release_techset["build_ok"]),
            "dev_load_unlink_ok": bool(dev_load_release_techset["unlink_ok"]),
            "dev_load_dev_unlink_ok": bool(dev_load_release_techset["dev_unlink_ok"]),
            "dev_load_build_problems": dev_load_release_techset["build_problems"],
        }

    if release_material and dev_load_release_material:
        out["release_material_ff_loaded_by_dev"] = {
            "release_build_ok": bool(release_material["build_ok"]),
            "release_unlink_ok": bool(release_material["unlink_ok"]),
            "release_dev_unlink_ok": bool(release_material["dev_unlink_ok"]),
            "dev_load_build_ok": bool(dev_load_release_material["build_ok"]),
            "dev_load_unlink_ok": bool(dev_load_release_material["unlink_ok"]),
            "dev_load_dev_unlink_ok": bool(dev_load_release_material["dev_unlink_ok"]),
            "dev_load_build_problems": dev_load_release_material["build_problems"],
        }

    if release_custom and dev_custom:
        out["custom_orb_capability_matrix"] = {
            "release_custom_build_ok": bool(release_custom["build_ok"]),
            "release_custom_unlink_ok": bool(release_custom["unlink_ok"]),
            "dev_custom_build_ok": bool(dev_custom["build_ok"]),
            "dev_custom_unlink_ok": bool(dev_custom["unlink_ok"]),
            "dev_custom_dev_unlink_ok": bool(dev_custom["dev_unlink_ok"]),
        }

    if dev_custom and dev_bo3_hole_md:
        out["custom_orb_vs_bo3_hole_md"] = {
            "dev_custom_build_ok": bool(dev_custom["build_ok"]),
            "dev_custom_unlink_ok": bool(dev_custom["unlink_ok"]),
            "dev_custom_dev_unlink_ok": bool(dev_custom["dev_unlink_ok"]),
            "dev_bo3_hole_md_build_ok": bool(dev_bo3_hole_md["build_ok"]),
            "dev_bo3_hole_md_unlink_ok": bool(dev_bo3_hole_md["unlink_ok"]),
            "dev_bo3_hole_md_dev_unlink_ok": bool(dev_bo3_hole_md["dev_unlink_ok"]),
            "dev_custom_hash": dev_custom["ff"]["sha256"],
            "dev_bo3_hole_md_hash": dev_bo3_hole_md["ff"]["sha256"],
        }

    return out


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build the T6 FF contract probe matrix, or emit a single runtime-targeted "
            "probe case for deterministic online testing."
        )
    )
    parser.add_argument(
        "--case",
        help=(
            "Optional single probe case name to build instead of the full matrix. "
            "Useful when preparing one minimal runtime repro."
        ),
    )
    parser.add_argument(
        "--zone-name",
        help=(
            "Optional override for the output zone/FF name when --case is used. "
            "Example: --case dev_bo3_hole_md_surface --zone-name mod_load"
        ),
    )
    parser.add_argument(
        "--report-path",
        default=str(REPORT_PATH),
        help="Override the JSON report output path.",
    )
    parser.add_argument(
        "--custom-fx-asset",
        help=(
            "Build one ad-hoc probe case for the given fx asset instead of using the "
            "predefined matrix."
        ),
    )
    parser.add_argument(
        "--custom-case-name",
        help="Optional logical case name for --custom-fx-asset.",
    )
    parser.add_argument(
        "--custom-techsets",
        nargs="*",
        default=None,
        help="Optional techniqueset assets to include with --custom-fx-asset.",
    )
    parser.add_argument(
        "--custom-materials",
        nargs="*",
        default=None,
        help="Optional material assets to include with --custom-fx-asset.",
    )
    parser.add_argument(
        "--custom-images",
        nargs="*",
        default=None,
        help="Optional image assets to include with --custom-fx-asset.",
    )
    parser.add_argument(
        "--custom-extra-search-root",
        action="append",
        default=None,
        help=(
            "Optional extra source/asset roots for --custom-fx-asset. Can be passed "
            "multiple times."
        ),
    )
    return parser.parse_args(argv)


def _custom_case_from_args(args: argparse.Namespace) -> ProbeCase:
    asset_name = str(args.custom_fx_asset or "").strip()
    if not asset_name:
        raise RuntimeError("Missing --custom-fx-asset")

    asset_stem = asset_name.split("/", 1)[-1].strip().replace("/", "_")
    case_name = str(args.custom_case_name or f"custom_{asset_stem}").strip()
    zone_name = str(args.zone_name or f"ffprobe_{case_name}").strip()
    extra_search_roots = (
        [Path(item).resolve() for item in args.custom_extra_search_root]
        if args.custom_extra_search_root
        else [BO3_PROBE_ROOT, *SUPPORT_ROOTS]
    )
    return ProbeCase(
        name=case_name,
        linker=DEV_LINKER,
        zone_name=zone_name,
        fx_assets=[asset_name],
        techniqueset_assets=list(args.custom_techsets or []),
        material_assets=list(args.custom_materials or []),
        image_assets=list(args.custom_images or []),
        use_stock_loads=False,
        extra_search_roots=extra_search_roots,
    )


def selected_cases(args: argparse.Namespace) -> list[ProbeCase]:
    if args.custom_fx_asset:
        if args.case:
            raise RuntimeError("--custom-fx-asset cannot be combined with --case")
        return [_custom_case_from_args(args)]

    if not args.case:
        return CASES

    by_name = {case.name: case for case in CASES}
    if args.case not in by_name:
        raise RuntimeError(
            f"Unknown probe case '{args.case}'. Available cases: "
            + ", ".join(sorted(by_name))
        )

    case = by_name[args.case]
    if args.zone_name:
        case = replace(case, zone_name=args.zone_name)
    return [case]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    reset_dirs()
    tool_architectures = verify_t6_oat_binary_architectures()
    results: list[dict[str, object]] = []
    by_name: dict[str, dict[str, object]] = {}
    cases = selected_cases(args)
    for case in cases:
        result = build_case(case, by_name)
        results.append(result)
        by_name[case.name] = result
    report = {
        "work_dir": str(WORK),
        "output_dir": str(OUTPUT),
        "selected_case": args.case or "",
        "selected_zone_name_override": args.zone_name or "",
        "stable_unlinker": str(RELEASE_UNLINKER),
        "dev_unlinker": str(DEV_UNLINKER),
        "tool_architectures": tool_architectures,
        "cases": results,
        "comparisons": compare_cases(results),
        "success_criteria": {
            "release_stock_marker": "must build and stable-unlink cleanly",
            "dev_load_release_stock_marker": "must build and stable-unlink cleanly to prove the dev linker can safely consume at least a minimal release-built FF",
            "dev_stock_marker": "must build and stable-unlink cleanly to prove the custom writer is not inherently unsafe",
            "release_techset_stock_surface": "must build and stable-unlink cleanly to prove a bare stock techniqueset FF is structurally valid in the stable toolchain",
            "dev_load_release_techset_stock_surface": "must build and stable-unlink cleanly to prove the dev linker can safely consume a release-built techniqueset FF",
            "release_material_stock_surface": "must build and stable-unlink cleanly to prove a minimal stock material+techset+image FF is structurally valid in the stable toolchain",
            "dev_load_release_material_stock_surface": "must build and stable-unlink cleanly to prove the dev linker can safely consume a release-built material FF",
            "release_custom_orb_stock_surface": "documents whether the release linker can ingest the custom raw-FX lane at all",
            "dev_custom_orb_stock_surface": "must resolve all transitive deps, build, and stable-unlink cleanly to prove the raw custom FX lane is structurally safe",
            "dev_custom_orb_stock_fmt0d_surface": "must prove the same stock-safe orb shell works with a native stock 0x0D sprite image payload",
            "dev_bo3_hole_md_surface": "must resolve the real BO3-derived hole_md FX chain, build, and stable-unlink cleanly before we trust larger Servant runtime tests again",
        },
    }
    report_path = Path(args.report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
