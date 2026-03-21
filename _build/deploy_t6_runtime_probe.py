#!/usr/bin/env python3
"""Build and deploy a minimal runtime probe without the full Servant stack.

This helper exists to answer one precise runtime question:

Does a *verified* minimal custom ``mod_load.ff`` survive the retail runtime
when the stock survival fastfile and loose mod overrides are restored?

It intentionally avoids the main Servant build path so we can stop attributing
crashes to the BO3 FX payload when the runtime lane itself is polluted.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "_build" / "ff_contract_probe"
OUTPUT = WORK / "output"
REPORTS = WORK / "runtime_deploy_reports"
ARCHIVE_ROOT = WORK / "runtime_deploy_archive"
IMAGE_META_VALIDATION_DIR = WORK / "image_meta_validation"

PROBE_BUILD_SCRIPT = ROOT / "_build" / "build_t6_ff_contract_probe.py"
PROBE_REPORT = REPORTS / "probe_build_report.json"
DEPLOY_REPORT = REPORTS / "runtime_probe_deploy_report.json"
CURRENT_ANALYSIS_REPORT = ROOT / "_build" / "fx_current_servant_analysis" / "current_servant_fx_report.json"
CURRENT_MOD_LOAD_ZONE = ROOT / "_build" / "bo3_rev_idg_probe" / "zone_source" / "mod_load.zone"

MOD_NAME = "bo3_rev"
RUNTIME_ZONE_NAME = "so_zsurvival_zm_transit"
RUNTIME_FF_NAME = f"{RUNTIME_ZONE_NAME}.ff"
RUNTIME_IPAK_NAME = f"{RUNTIME_ZONE_NAME}.ipak"
PROBE_ZONE_NAME = "mod_load"
PROBE_FF_NAME = f"{PROBE_ZONE_NAME}.ff"
PROBE_IPAK_NAME = f"{PROBE_ZONE_NAME}.ipak"
PROBE_SCRIPT_NAME = "mod_i_am_mod.gsc"
CLIENT_PROBE_ZM_TRANSIT_NAME = "zm_transit.csc"
CLIENT_PROBE_HELPER_REL = Path("zombies") / "_ffprobe_fx.csc"
BO3_WORLD_PROBE_ASSET = "zombie/fx_idgun_hole_md_zod_zmb"
CUSTOM_RAW_WORLD_PROBE_ASSET = "zombie/fx_ffprobe_debug_orb_stock"
STOCK_WORLD_PROBE_ASSET = "maps/zombie/fx_zmb_tranzit_marker_glow"
STOCK_ZM_TRANSIT_CSC = ROOT / "t6-scripts-official" / "ZM1" / "Maps" / "Tranzit" / "clientscripts" / "mp" / "zm_transit.csc"

BASELINE_RUNTIME_FF = ROOT / "_build" / "ff_backup" / "20260213-123213" / RUNTIME_FF_NAME

BASE_ZONE_DIR = ROOT / "zone" / "all"
GAME_MOD_ROOT = ROOT / "mods" / MOD_NAME
GAME_MOD_ZONE_DIR = GAME_MOD_ROOT / "zone" / "all"
GAME_MOD_SCRIPT_DIR = GAME_MOD_ROOT / "scripts"
GAME_MOD_CLIENTSCRIPT_DIR = GAME_MOD_ROOT / "clientscripts" / "mp"

STORAGE_MOD_ROOT = Path.home() / "AppData" / "Local" / "Plutonium" / "storage" / "t6" / "mods" / MOD_NAME
STORAGE_MOD_ZONE_DIR = STORAGE_MOD_ROOT / "zone" / "all"
STORAGE_MOD_SCRIPT_DIR = STORAGE_MOD_ROOT / "scripts"
STORAGE_MOD_CLIENTSCRIPT_DIR = STORAGE_MOD_ROOT / "clientscripts" / "mp"
DEV_UNLINKER = ROOT / "tools" / "oat" / "Unlinker.exe"
RELEASE_LINKER = ROOT / "_build" / "oat_release" / "unzipped" / "Linker.exe"
RELEASE_UNLINKER = ROOT / "_build" / "oat_release" / "unzipped" / "Unlinker.exe"
ENGLISH_ZONE_DIR = ROOT / "zone" / "english"
SCRIPT_PATCH_WORK = WORK / "script_patch_probe"
RUNTIME_SCRIPT_OVERRIDE_WORK = WORK / "runtime_script_override"
MOD_PATCH_FF_NAME = "mod_patch.ff"

RUNTIME_RESTORE_TARGETS = [
    BASE_ZONE_DIR / RUNTIME_FF_NAME,
    GAME_MOD_ZONE_DIR / RUNTIME_FF_NAME,
    STORAGE_MOD_ZONE_DIR / RUNTIME_FF_NAME,
]

RUNTIME_IPAK_REMOVE_TARGETS = [
    BASE_ZONE_DIR / RUNTIME_IPAK_NAME,
    GAME_MOD_ZONE_DIR / RUNTIME_IPAK_NAME,
    STORAGE_MOD_ZONE_DIR / RUNTIME_IPAK_NAME,
]

PROBE_DEPLOY_TARGETS = [
    BASE_ZONE_DIR / PROBE_FF_NAME,
    GAME_MOD_ZONE_DIR / PROBE_FF_NAME,
    STORAGE_MOD_ZONE_DIR / PROBE_FF_NAME,
]

PROBE_IPAK_TARGETS = [
    BASE_ZONE_DIR / PROBE_IPAK_NAME,
    GAME_MOD_ZONE_DIR / PROBE_IPAK_NAME,
    STORAGE_MOD_ZONE_DIR / PROBE_IPAK_NAME,
]

SCRIPT_PATCH_DEPLOY_TARGETS = [
    GAME_MOD_ZONE_DIR / MOD_PATCH_FF_NAME,
    STORAGE_MOD_ZONE_DIR / MOD_PATCH_FF_NAME,
]

RUNTIME_SCRIPT_OVERRIDE_TARGETS = [
    BASE_ZONE_DIR / RUNTIME_FF_NAME,
    GAME_MOD_ZONE_DIR / RUNTIME_FF_NAME,
    STORAGE_MOD_ZONE_DIR / RUNTIME_FF_NAME,
]

LOOSE_OVERRIDE_TARGETS = [
    GAME_MOD_SCRIPT_DIR / "mod_i_am_mod.gsc",
    STORAGE_MOD_SCRIPT_DIR / "mod_i_am_mod.gsc",
    GAME_MOD_CLIENTSCRIPT_DIR / "zm_transit.csc",
    STORAGE_MOD_CLIENTSCRIPT_DIR / "zm_transit.csc",
    GAME_MOD_CLIENTSCRIPT_DIR / CLIENT_PROBE_HELPER_REL,
    STORAGE_MOD_CLIENTSCRIPT_DIR / CLIENT_PROBE_HELPER_REL,
    GAME_MOD_CLIENTSCRIPT_DIR / "_visionset_mgr.csc",
    STORAGE_MOD_CLIENTSCRIPT_DIR / "_visionset_mgr.csc",
    GAME_MOD_CLIENTSCRIPT_DIR / "zombies" / "_bo3_rev_servant_fx.csc",
    STORAGE_MOD_CLIENTSCRIPT_DIR / "zombies" / "_bo3_rev_servant_fx.csc",
    GAME_MOD_CLIENTSCRIPT_DIR / "zombies" / "_bo3_rev_servant_fx_v2.csc",
    STORAGE_MOD_CLIENTSCRIPT_DIR / "zombies" / "_bo3_rev_servant_fx_v2.csc",
    GAME_MOD_CLIENTSCRIPT_DIR / "zombies" / "_bo3_rev_servant_fx_v3.csc",
    STORAGE_MOD_CLIENTSCRIPT_DIR / "zombies" / "_bo3_rev_servant_fx_v3.csc",
]

def load_current_analysis_report() -> dict[str, object] | None:
    if not CURRENT_ANALYSIS_REPORT.exists():
        return None
    try:
        return json.loads(CURRENT_ANALYSIS_REPORT.read_text(encoding="utf-8"))
    except Exception:
        return None


def recommended_probe_fx_asset() -> str:
    report = load_current_analysis_report()
    if not report:
        return BO3_WORLD_PROBE_ASSET
    candidates = report.get("probe_candidates") or []
    if not candidates:
        return BO3_WORLD_PROBE_ASSET
    top = candidates[0]
    effect = str(top.get("effect") or "").strip()
    return effect or BO3_WORLD_PROBE_ASSET


def validate_probe_fx_asset(probe_fx_asset: str, allow_inert_probe: bool) -> dict[str, object] | None:
    report = load_current_analysis_report()
    if not report:
        return None
    for entry in report.get("effects") or []:
        if str(entry.get("effect") or "").strip() != probe_fx_asset:
            continue
        native = entry.get("native") or {}
        raw = entry.get("raw") or {}
        classification = str(entry.get("classification") or "")
        native_bucket = str(native.get("bucket") or "")
        if native_bucket == "likely_inert" and not allow_inert_probe:
            raise RuntimeError(
                "Refusing to deploy a known bad standalone BO3 render probe.\n"
                f"  effect={probe_fx_asset}\n"
                f"  classification={classification}\n"
                f"  raw_bucket={raw.get('bucket')}\n"
                f"  native_bucket={native_bucket}\n"
                f"  analysis_report={CURRENT_ANALYSIS_REPORT}\n"
                "Choose one of the recommended probe_candidates from the analysis report, "
                "or pass --allow-inert-probe to override for debugging."
            )
        return entry
    return None


def load_current_mod_load_manifest() -> dict[str, list[str]]:
    if not CURRENT_MOD_LOAD_ZONE.exists():
        raise FileNotFoundError(f"Missing current mod_load manifest: {CURRENT_MOD_LOAD_ZONE}")
    manifest = {"fx": [], "materials": [], "images": []}
    kind_map = {
        "fx": "fx",
        "material": "materials",
        "materials": "materials",
        "image": "images",
        "images": "images",
    }
    for raw in CURRENT_MOD_LOAD_ZONE.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("//") or line.startswith(">"):
            continue
        asset_type, _, asset_name = line.partition(",")
        asset_type = asset_type.strip().lower()
        asset_name = asset_name.strip()
        bucket = kind_map.get(asset_type)
        if bucket:
            manifest[bucket].append(asset_name)
    return manifest


def resolve_probe_fx_asset(case_name: str, explicit_asset: str) -> str:
    if explicit_asset:
        return explicit_asset.strip()
    lowered = case_name.strip().lower()
    if "custom_orb" in lowered:
        return CUSTOM_RAW_WORLD_PROBE_ASSET
    return recommended_probe_fx_asset()


def minimal_world_play_script(probe_fx_asset: str) -> str:
    return f"""init()
{{
    ffprobe_start();
}}

main()
{{
    ffprobe_start();
}}

ffprobe_log(message)
{{
    println("[ffprobe] " + message);
}}

ffprobe_fx_ok(fx)
{{
    return isdefined(fx) && fx;
}}

ffprobe_start()
{{
    if ( isdefined( level.ffprobe_started ) )
        return;

    level.ffprobe_started = 1;
    level.ffprobe_asset_name = "{probe_fx_asset}";
    level.ffprobe_bo3_fx = loadfx( "{probe_fx_asset}" );

    ffprobe_log(
        "init asset=" + level.ffprobe_asset_name
        + ";bo3=" + ffprobe_fx_ok( level.ffprobe_bo3_fx )
    );

    level thread ffprobe_on_connect();
}}

ffprobe_on_connect()
{{
    for ( ;; )
    {{
        level waittill( "connected", player );
        ffprobe_log( "connected ent=" + player getentitynumber() );
        player thread ffprobe_on_spawn();
    }}
}}

ffprobe_on_spawn()
{{
    self endon( "disconnect" );

    for ( ;; )
    {{
        self waittill( "spawned_player" );
        wait 1.0;

        base_origin = self.origin + vectorscale( anglestoforward( self getplayerangles() ), 144 );
        base_origin = base_origin + ( 0, 0, 64 );
        bo3_origin = base_origin;

        ffprobe_log(
            "spawn play asset=" + level.ffprobe_asset_name
            + ";bo3=" + ffprobe_fx_ok( level.ffprobe_bo3_fx )
            + ";bo3_origin=" + bo3_origin
        );

        if ( ffprobe_fx_ok( level.ffprobe_bo3_fx ) )
        {{
            playfx( level.ffprobe_bo3_fx, bo3_origin );
            wait 0.25;
            playfx( level.ffprobe_bo3_fx, bo3_origin );
            wait 0.25;
            playfx( level.ffprobe_bo3_fx, bo3_origin );
        }}
    }}
}}
"""


def client_probe_helper_script(probe_fx_asset: str) -> str:
    return f"""// Minimal clientside FF probe helper.
// Installed by deploy_t6_runtime_probe.py to validate client CSC loadfx/playfx.

init()
{{
    println("[ffprobe][csc] helper init reached");
    if ( isdefined( level.ffprobe_client_init ) )
        return;

    level.ffprobe_client_init = 1;
    level.ffprobe_asset_name = "{probe_fx_asset}";
    level.ffprobe_bo3_fx = loadfx( "{probe_fx_asset}" );
    level.ffprobe_original_playerspawned_override = level._playerspawned_override;
    level._playerspawned_override = ::ffprobe_playerspawned_override;

    println(
        "[ffprobe][csc] init asset=" + level.ffprobe_asset_name
        + ";bo3=" + ffprobe_fx_ok( level.ffprobe_bo3_fx )
    );
}}

ffprobe_fx_ok(fx)
{{
    return isdefined( fx ) && fx;
}}

ffprobe_playerspawned_override(localclientnum)
{{
    if ( isdefined( level.ffprobe_original_playerspawned_override ) )
        self thread [[ level.ffprobe_original_playerspawned_override ]]( localclientnum );

    self thread ffprobe_play_on_spawn( localclientnum );
}}

ffprobe_play_on_spawn(localclientnum)
{{
    self endon( "disconnect" );

    while ( !clienthassnapshot( localclientnum ) )
        wait 0.05;

    wait 1.0;

    bo3_origin = self.origin + vectorscale( anglestoforward( self getplayerangles() ), 144 );
    bo3_origin = bo3_origin + ( 0, 0, 64 );

    println(
        "[ffprobe][csc] spawn play asset=" + level.ffprobe_asset_name
        + ";bo3=" + ffprobe_fx_ok( level.ffprobe_bo3_fx )
        + ";localclient=" + localclientnum
        + ";bo3_origin=" + bo3_origin
    );

    if ( ffprobe_fx_ok( level.ffprobe_bo3_fx ) )
    {{
        playfx( localclientnum, level.ffprobe_bo3_fx, bo3_origin );
        wait 0.25;
        playfx( localclientnum, level.ffprobe_bo3_fx, bo3_origin );
        wait 0.25;
        playfx( localclientnum, level.ffprobe_bo3_fx, bo3_origin );
    }}
}}
"""


def stock_based_client_probe_zm_transit() -> str:
    if not STOCK_ZM_TRANSIT_CSC.exists():
        raise FileNotFoundError(f"Missing stock zm_transit clientscript: {STOCK_ZM_TRANSIT_CSC}")
    source = STOCK_ZM_TRANSIT_CSC.read_text(encoding="utf-8", errors="replace")
    include_line = "#include clientscripts\\mp\\zombies\\_ffprobe_fx;"
    if include_line not in source:
        anchor = "#include clientscripts\\mp\\zombies\\_zm_equipment;"
        if anchor not in source:
            raise RuntimeError("Failed to locate _zm_equipment include anchor in stock zm_transit.csc")
        source = source.replace(anchor, anchor + "\n" + include_line, 1)
    hook = '    clientscripts\\mp\\zombies\\_ffprobe_fx::init();'
    anchor = "register_client_fields()\n{\n"
    if hook not in source:
        if anchor not in source:
            raise RuntimeError("Failed to locate register_client_fields() in stock zm_transit.csc")
        source = source.replace(anchor, anchor + '    println( "[ffprobe][csc] zm_transit override register_client_fields" );\n' + hook + "\n", 1)
    main_anchor = "main()\n{\n"
    main_hook = '    println( "[ffprobe][csc] zm_transit override main" );\n'
    if main_hook not in source:
        if main_anchor not in source:
            raise RuntimeError("Failed to locate main() in stock zm_transit.csc")
        source = source.replace(main_anchor, main_anchor + main_hook, 1)
    return source


def build_client_probe_patch_ff(probe_fx_asset: str) -> Path:
    if not RELEASE_LINKER.exists():
        raise FileNotFoundError(f"Missing release Linker for client probe patch: {RELEASE_LINKER}")
    if not RELEASE_UNLINKER.exists():
        raise FileNotFoundError(f"Missing release Unlinker for client probe patch: {RELEASE_UNLINKER}")

    if SCRIPT_PATCH_WORK.exists():
        shutil.rmtree(SCRIPT_PATCH_WORK)

    zone_source_dir = SCRIPT_PATCH_WORK / "zone_source"
    script_dir = SCRIPT_PATCH_WORK / "clientscripts" / "mp"
    helper_dir = script_dir / "zombies"
    output_dir = SCRIPT_PATCH_WORK / "output"
    zone_source_dir.mkdir(parents=True, exist_ok=True)
    helper_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    (script_dir / CLIENT_PROBE_ZM_TRANSIT_NAME).write_text(
        stock_based_client_probe_zm_transit(),
        encoding="utf-8",
    )
    (helper_dir / CLIENT_PROBE_HELPER_REL.name).write_text(
        client_probe_helper_script(probe_fx_asset),
        encoding="utf-8",
    )

    zone_lines = [
        "// Call Of Duty: Black Ops II",
        ">game,T6",
        "",
        "script,clientscripts/mp/zm_transit.csc",
        "script,clientscripts/mp/zombies/_ffprobe_fx.csc",
        "",
    ]
    (zone_source_dir / "mod_patch.zone").write_text("\n".join(zone_lines), encoding="utf-8")

    args = [
        str(RELEASE_LINKER),
        "--verbose",
        "--base-folder",
        str(SCRIPT_PATCH_WORK),
        "--add-asset-search-path",
        str(SCRIPT_PATCH_WORK),
        "--add-source-search-path",
        str(SCRIPT_PATCH_WORK),
        "--output-folder",
        str(output_dir),
        "--load",
        str(BASELINE_RUNTIME_FF),
        "mod_patch",
    ]
    run_checked(args)

    mod_patch_ff = output_dir / MOD_PATCH_FF_NAME
    if not mod_patch_ff.exists():
        raise FileNotFoundError(f"Client probe patch FF was not built: {mod_patch_ff}")

    verify_args = [str(RELEASE_UNLINKER), "--list", str(mod_patch_ff)]
    run_checked(verify_args)
    return mod_patch_ff


def build_runtime_client_probe_ff(probe_fx_asset: str) -> Path:
    if not RELEASE_LINKER.exists():
        raise FileNotFoundError(f"Missing release Linker for runtime client probe FF: {RELEASE_LINKER}")
    if not RELEASE_UNLINKER.exists():
        raise FileNotFoundError(f"Missing release Unlinker for runtime client probe FF: {RELEASE_UNLINKER}")

    if RUNTIME_SCRIPT_OVERRIDE_WORK.exists():
        shutil.rmtree(RUNTIME_SCRIPT_OVERRIDE_WORK)

    zone_source_dir = RUNTIME_SCRIPT_OVERRIDE_WORK / "zone_source"
    script_dir = RUNTIME_SCRIPT_OVERRIDE_WORK / "clientscripts" / "mp"
    helper_dir = script_dir / "zombies"
    output_dir = RUNTIME_SCRIPT_OVERRIDE_WORK / "output"
    zone_source_dir.mkdir(parents=True, exist_ok=True)
    helper_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    (script_dir / CLIENT_PROBE_ZM_TRANSIT_NAME).write_text(
        stock_based_client_probe_zm_transit(),
        encoding="utf-8",
    )
    (helper_dir / CLIENT_PROBE_HELPER_REL.name).write_text(
        client_probe_helper_script(probe_fx_asset),
        encoding="utf-8",
    )

    zone_lines = [
        "// Call Of Duty: Black Ops II",
        ">game,T6",
        "",
        "script,clientscripts/mp/zm_transit.csc",
        "script,clientscripts/mp/zombies/_ffprobe_fx.csc",
        "",
    ]
    (zone_source_dir / f"{RUNTIME_ZONE_NAME}.zone").write_text("\n".join(zone_lines), encoding="utf-8")

    args = [
        str(RELEASE_LINKER),
        "--verbose",
        "--base-folder",
        str(RUNTIME_SCRIPT_OVERRIDE_WORK),
        "--add-asset-search-path",
        str(RUNTIME_SCRIPT_OVERRIDE_WORK),
        "--add-source-search-path",
        str(RUNTIME_SCRIPT_OVERRIDE_WORK),
        "--output-folder",
        str(output_dir),
        "--load",
        str(BASELINE_RUNTIME_FF),
        RUNTIME_ZONE_NAME,
    ]
    run_checked(args)

    runtime_ff = output_dir / RUNTIME_FF_NAME
    if not runtime_ff.exists():
        raise FileNotFoundError(f"Runtime client probe FF was not built: {runtime_ff}")

    verify_args = [str(RELEASE_UNLINKER), "--list", str(runtime_ff)]
    run_checked(verify_args)
    return runtime_ff


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run_checked(args: list[str]) -> str:
    result = subprocess.run(args, cwd=str(ROOT), text=True, capture_output=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr)
    if result.returncode != 0:
        raise RuntimeError(
            f"Command failed ({result.returncode}): {' '.join(args)}\n"
            f"{result.stdout}\n{result.stderr}"
        )
    return result.stdout


def validate_streamed_image_contract(ff_path: Path, expected_ipak_name: str) -> dict[str, object]:
    if not DEV_UNLINKER.exists():
        raise FileNotFoundError(f"Missing dev Unlinker for image validation: {DEV_UNLINKER}")
    if not ff_path.exists():
        raise FileNotFoundError(f"Missing FF for image validation: {ff_path}")

    if IMAGE_META_VALIDATION_DIR.exists():
        shutil.rmtree(IMAGE_META_VALIDATION_DIR)
    IMAGE_META_VALIDATION_DIR.mkdir(parents=True, exist_ok=True)

    args = [
        str(DEV_UNLINKER),
        "--search-path",
        f"{OUTPUT};{BASE_ZONE_DIR};{ENGLISH_ZONE_DIR}",
        "--include-assets",
        "image",
        "--output-folder",
        str(IMAGE_META_VALIDATION_DIR),
        str(ff_path),
    ]
    unlink_output = run_checked(args)

    image_dir = IMAGE_META_VALIDATION_DIR / "images"
    metadata_files = sorted(image_dir.glob("*.image-meta.json")) if image_dir.exists() else []
    issues: list[dict[str, object]] = []
    summaries: list[dict[str, object]] = []

    for meta_path in metadata_files:
        data = json.loads(meta_path.read_text(encoding="utf-8"))
        image_name = str(data.get("name") or meta_path.stem)
        hash_value = int(data.get("hash") or 0)
        texture_loaded = bool(data.get("textureLoaded"))
        delay_load = bool(data.get("delayLoadPixels"))
        ipak_entries = {
            str(entry.get("name") or ""): bool(entry.get("hasEntry"))
            for entry in (data.get("ipakProbe") or [])
        }
        has_expected_entry = ipak_entries.get(expected_ipak_name, False)
        summaries.append(
            {
                "name": image_name,
                "hash": hash_value,
                "hashHex": data.get("hashHex"),
                "streamedPartHash": data.get("streamedPartHash"),
                "streamedPartHashHex": data.get("streamedPartHashHex"),
                "textureLoaded": texture_loaded,
                "delayLoadPixels": delay_load,
                "expectedIpak": expected_ipak_name,
                "expectedIpakHasEntry": has_expected_entry,
            }
        )
        if not texture_loaded:
            issues.append({"image": image_name, "issue": "texture_not_loaded"})
        if delay_load and hash_value == 0:
            issues.append({"image": image_name, "issue": "zero_name_hash"})
        if delay_load and not has_expected_entry:
            issues.append({"image": image_name, "issue": "missing_expected_ipak_entry"})

    report = {
        "ff_path": str(ff_path),
        "expected_ipak_name": expected_ipak_name,
        "search_path": [str(OUTPUT), str(BASE_ZONE_DIR), str(ENGLISH_ZONE_DIR)],
        "image_count": len(metadata_files),
        "issues": issues,
        "images": summaries,
        "unlink_output": unlink_output,
        "output_dir": str(IMAGE_META_VALIDATION_DIR),
    }
    if issues:
        raise RuntimeError(
            "Probe FF failed streamed-image contract validation.\n"
            f"ff={ff_path}\n"
            f"expected_ipak={expected_ipak_name}\n"
            f"issues={json.dumps(issues, indent=2)}\n"
            f"metadata_dir={IMAGE_META_VALIDATION_DIR}"
        )
    return report


def archive_existing(path: Path, archive_root: Path) -> str | None:
    if not path.exists():
        return None
    rel = path.drive.replace(":", "") + path.as_posix()[2:] if path.drive else path.as_posix().lstrip("/")
    dst = archive_root / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dst)
    return str(dst)


def safe_copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_suffix(dst.suffix + ".tmp")
    shutil.copy2(src, tmp)
    tmp.replace(dst)


def remove_if_exists(path: Path) -> None:
    if not path.exists():
        return
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build a single verified ff_contract_probe case and deploy it as the "
            "only custom mod_load lane while restoring stock survival runtime assets."
        )
    )
    parser.add_argument(
        "--case",
        default="dev_bo3_hole_md_surface",
        help="Probe case name from build_t6_ff_contract_probe.py",
    )
    parser.add_argument(
        "--zone-name",
        default=PROBE_ZONE_NAME,
        help="Output zone/FF name for the probe build. Defaults to mod_load.",
    )
    parser.add_argument(
        "--keep-loose-overrides",
        action="store_true",
        help="Do not remove the loose mod script/clientscript overrides.",
    )
    parser.add_argument(
        "--deploy-world-play-script",
        action="store_true",
        help="Deploy a tiny server-side probe script that plays a stock control FX and the BO3 hole_md FX on player spawn.",
    )
    parser.add_argument(
        "--deploy-client-probe-script",
        action="store_true",
        help="Deploy a stock-based loose zm_transit.csc override plus a tiny CSC helper that loads and plays the selected probe FX clientside on player spawn.",
    )
    parser.add_argument(
        "--probe-fx-asset",
        default="",
        help="Optional explicit second probe FX asset name for the world-play script. Defaults are derived from --case.",
    )
    parser.add_argument(
        "--allow-inert-probe",
        action="store_true",
        help="Allow deployment of a BO3 probe that the current offline analysis marks as likely inert.",
    )
    parser.add_argument(
        "--build-probe-from-fx-asset",
        action="store_true",
        help=(
            "Build mod_load.ff from the requested probe FX asset plus the current BO3 "
            "material/image manifest instead of using a predefined probe case."
        ),
    )
    return parser.parse_args(argv)


def build_probe(case_name: str, zone_name: str) -> dict[str, object]:
    REPORTS.mkdir(parents=True, exist_ok=True)
    args = [
        sys.executable,
        "-u",
        str(PROBE_BUILD_SCRIPT),
        "--case",
        case_name,
        "--zone-name",
        zone_name,
        "--report-path",
        str(PROBE_REPORT),
    ]
    run_checked(args)
    report = json.loads(PROBE_REPORT.read_text(encoding="utf-8"))
    cases = report.get("cases", [])
    if len(cases) != 1:
        raise RuntimeError(f"Expected exactly one probe case in {PROBE_REPORT}, got {len(cases)}")
    case = cases[0]
    if not (case.get("build_ok") and case.get("unlink_ok") and case.get("dev_unlink_ok")):
        raise RuntimeError(
            "Probe case is not structurally safe enough for runtime deploy.\n"
            f"Case: {case_name}\n"
            f"build_ok={case.get('build_ok')}\n"
            f"unlink_ok={case.get('unlink_ok')}\n"
            f"dev_unlink_ok={case.get('dev_unlink_ok')}\n"
            f"Report: {PROBE_REPORT}"
        )
    report["image_contract_validation"] = validate_streamed_image_contract(OUTPUT / PROBE_FF_NAME, PROBE_ZONE_NAME)
    return report


def build_custom_probe(probe_fx_asset: str, zone_name: str) -> dict[str, object]:
    REPORTS.mkdir(parents=True, exist_ok=True)
    manifest = load_current_mod_load_manifest()
    if not manifest["materials"] or not manifest["images"]:
        raise RuntimeError(
            "Current mod_load manifest parser resolved an incomplete BO3 surface closure; "
            f"materials={len(manifest['materials'])} images={len(manifest['images'])} "
            f"from {CURRENT_MOD_LOAD_ZONE}"
        )
    args = [
        sys.executable,
        "-u",
        str(PROBE_BUILD_SCRIPT),
        "--custom-fx-asset",
        probe_fx_asset,
        "--custom-case-name",
        probe_fx_asset.split("/", 1)[-1],
        "--zone-name",
        zone_name,
        "--report-path",
        str(PROBE_REPORT),
        "--custom-materials",
        *manifest["materials"],
        "--custom-images",
        *manifest["images"],
    ]
    run_checked(args)
    report = json.loads(PROBE_REPORT.read_text(encoding="utf-8"))
    cases = report.get("cases", [])
    if len(cases) != 1:
        raise RuntimeError(f"Expected exactly one probe case in {PROBE_REPORT}, got {len(cases)}")
    case = cases[0]
    if not (case.get("build_ok") and case.get("unlink_ok") and case.get("dev_unlink_ok")):
        raise RuntimeError(
            "Custom probe case is not structurally safe enough for runtime deploy.\n"
            f"effect={probe_fx_asset}\n"
            f"build_ok={case.get('build_ok')}\n"
            f"unlink_ok={case.get('unlink_ok')}\n"
            f"dev_unlink_ok={case.get('dev_unlink_ok')}\n"
            f"Report: {PROBE_REPORT}"
        )
    report["custom_manifest"] = manifest
    report["image_contract_validation"] = validate_streamed_image_contract(OUTPUT / PROBE_FF_NAME, PROBE_ZONE_NAME)
    return report


def deploy_probe(
    report: dict[str, object],
    keep_loose_overrides: bool,
    deploy_world_play_script: bool,
    deploy_client_probe_script: bool,
    probe_fx_asset: str,
) -> dict[str, object]:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    archive_root = ARCHIVE_ROOT / timestamp
    archive_root.mkdir(parents=True, exist_ok=True)

    probe_ff = OUTPUT / PROBE_FF_NAME
    probe_ipak = OUTPUT / PROBE_IPAK_NAME
    if not probe_ff.exists():
        raise FileNotFoundError(f"Missing built probe FF: {probe_ff}")
    if not BASELINE_RUNTIME_FF.exists():
        raise FileNotFoundError(f"Missing baseline runtime FF: {BASELINE_RUNTIME_FF}")

    actions: dict[str, list[dict[str, object]]] = {
        "archived": [],
        "restored_runtime_ff": [],
        "removed_runtime_ipak": [],
        "deployed_probe_ff": [],
        "deployed_probe_ipak": [],
        "deployed_script_patch_ff": [],
        "deployed_runtime_script_override_ff": [],
        "removed_probe_ipak": [],
        "removed_loose_overrides": [],
        "deployed_probe_script": [],
    }

    for target in [*RUNTIME_RESTORE_TARGETS, *RUNTIME_IPAK_REMOVE_TARGETS, *PROBE_DEPLOY_TARGETS, *PROBE_IPAK_TARGETS, *SCRIPT_PATCH_DEPLOY_TARGETS, *LOOSE_OVERRIDE_TARGETS]:
        archived = archive_existing(target, archive_root)
        if archived:
            actions["archived"].append({"target": str(target), "archive": archived})

    for target in RUNTIME_RESTORE_TARGETS:
        safe_copy(BASELINE_RUNTIME_FF, target)
        actions["restored_runtime_ff"].append(
            {"target": str(target), "sha256": sha256(target), "size": target.stat().st_size}
        )

    for target in RUNTIME_IPAK_REMOVE_TARGETS:
        if target.exists():
            remove_if_exists(target)
            actions["removed_runtime_ipak"].append({"target": str(target)})

    for target in PROBE_DEPLOY_TARGETS:
        safe_copy(probe_ff, target)
        actions["deployed_probe_ff"].append(
            {"target": str(target), "sha256": sha256(target), "size": target.stat().st_size}
        )

    for target in PROBE_IPAK_TARGETS:
        if probe_ipak.exists():
            safe_copy(probe_ipak, target)
            actions["deployed_probe_ipak"].append(
                {"target": str(target), "sha256": sha256(target), "size": target.stat().st_size}
            )
        elif target.exists():
            remove_if_exists(target)
            actions["removed_probe_ipak"].append({"target": str(target)})

    if not keep_loose_overrides:
        for target in LOOSE_OVERRIDE_TARGETS:
            if target.exists():
                remove_if_exists(target)
                actions["removed_loose_overrides"].append({"target": str(target)})

    if deploy_world_play_script:
        probe_script = minimal_world_play_script(probe_fx_asset)
        probe_script_paths = [
            GAME_MOD_SCRIPT_DIR / PROBE_SCRIPT_NAME,
            STORAGE_MOD_SCRIPT_DIR / PROBE_SCRIPT_NAME,
        ]
        for path in probe_script_paths:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(probe_script, encoding="utf-8")
            actions["deployed_probe_script"].append(
                {"target": str(path), "sha256": sha256(path), "size": path.stat().st_size}
            )

    if deploy_client_probe_script:
        script_patch_ff = build_client_probe_patch_ff(probe_fx_asset)
        for target in SCRIPT_PATCH_DEPLOY_TARGETS:
            safe_copy(script_patch_ff, target)
            actions["deployed_script_patch_ff"].append(
                {"target": str(target), "sha256": sha256(target), "size": target.stat().st_size}
            )
        runtime_override_ff = build_runtime_client_probe_ff(probe_fx_asset)
        for target in RUNTIME_SCRIPT_OVERRIDE_TARGETS:
            safe_copy(runtime_override_ff, target)
            actions["deployed_runtime_script_override_ff"].append(
                {"target": str(target), "sha256": sha256(target), "size": target.stat().st_size}
            )

    report_out = {
        "timestamp": timestamp,
        "selected_case": report.get("selected_case"),
        "selected_zone_name_override": report.get("selected_zone_name_override"),
        "probe_report": str(PROBE_REPORT),
        "image_contract_validation": report.get("image_contract_validation"),
        "baseline_runtime_ff": {
            "path": str(BASELINE_RUNTIME_FF),
            "sha256": sha256(BASELINE_RUNTIME_FF),
            "size": BASELINE_RUNTIME_FF.stat().st_size,
        },
        "probe_ff": {
            "path": str(probe_ff),
            "sha256": sha256(probe_ff),
            "size": probe_ff.stat().st_size,
        },
        "probe_ipak": {
            "path": str(probe_ipak),
            "exists": probe_ipak.exists(),
            "sha256": sha256(probe_ipak) if probe_ipak.exists() else "",
            "size": probe_ipak.stat().st_size if probe_ipak.exists() else 0,
        },
        "script_patch_ff": {
            "path": str(SCRIPT_PATCH_WORK / "output" / MOD_PATCH_FF_NAME),
            "exists": (SCRIPT_PATCH_WORK / "output" / MOD_PATCH_FF_NAME).exists(),
            "sha256": sha256(SCRIPT_PATCH_WORK / "output" / MOD_PATCH_FF_NAME) if (SCRIPT_PATCH_WORK / "output" / MOD_PATCH_FF_NAME).exists() else "",
            "size": (SCRIPT_PATCH_WORK / "output" / MOD_PATCH_FF_NAME).stat().st_size if (SCRIPT_PATCH_WORK / "output" / MOD_PATCH_FF_NAME).exists() else 0,
        },
        "runtime_script_override_ff": {
            "path": str(RUNTIME_SCRIPT_OVERRIDE_WORK / "output" / RUNTIME_FF_NAME),
            "exists": (RUNTIME_SCRIPT_OVERRIDE_WORK / "output" / RUNTIME_FF_NAME).exists(),
            "sha256": sha256(RUNTIME_SCRIPT_OVERRIDE_WORK / "output" / RUNTIME_FF_NAME) if (RUNTIME_SCRIPT_OVERRIDE_WORK / "output" / RUNTIME_FF_NAME).exists() else "",
            "size": (RUNTIME_SCRIPT_OVERRIDE_WORK / "output" / RUNTIME_FF_NAME).stat().st_size if (RUNTIME_SCRIPT_OVERRIDE_WORK / "output" / RUNTIME_FF_NAME).exists() else 0,
        },
        "probe_world_fx_asset": probe_fx_asset,
        "success_criteria": {
            "offline_probe_passed": True,
            "runtime_ff_restored_to_stock_baseline": True,
            "custom_runtime_ipak_removed": True,
            "only_probe_mod_load_ff_deployed": True,
            "loose_servant_overrides_removed": not keep_loose_overrides,
            "probe_world_play_script_deployed": deploy_world_play_script,
            "probe_client_csc_deployed_via_mod_patch_ff": deploy_client_probe_script,
            "probe_client_csc_deployed_via_runtime_ff_overlay": deploy_client_probe_script,
        },
        "actions": actions,
        "archive_root": str(archive_root),
    }
    DEPLOY_REPORT.write_text(json.dumps(report_out, indent=2) + "\n", encoding="utf-8")
    return report_out


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    probe_fx_asset = resolve_probe_fx_asset(args.case, args.probe_fx_asset)
    validate_probe_fx_asset(probe_fx_asset, allow_inert_probe=args.allow_inert_probe)
    report = (
        build_custom_probe(probe_fx_asset, args.zone_name)
        if args.build_probe_from_fx_asset
        else build_probe(args.case, args.zone_name)
    )
    deploy_report = deploy_probe(
        report,
        keep_loose_overrides=args.keep_loose_overrides,
        deploy_world_play_script=args.deploy_world_play_script,
        deploy_client_probe_script=args.deploy_client_probe_script,
        probe_fx_asset=probe_fx_asset,
    )
    print(f"Wrote {DEPLOY_REPORT}")
    print("Runtime probe deployment is ready.")
    print(f"  selected_case={deploy_report['selected_case']}")
    print(f"  probe_ff={deploy_report['probe_ff']['path']}")
    print(f"  baseline_runtime_ff={deploy_report['baseline_runtime_ff']['path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
