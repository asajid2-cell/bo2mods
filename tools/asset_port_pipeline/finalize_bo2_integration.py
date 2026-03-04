from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent

import sys

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common import save_json  # noqa: E402
from linker_oracle import parse_load_zones, resolve_paths, run_linker, sanitize_name  # noqa: E402


def parse_zone_lines(zone_path: Path) -> Tuple[List[str], Dict[str, int]]:
    zone_lines: List[str] = []
    type_counts: Dict[str, int] = {}
    for raw in zone_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("//") or line.startswith(">"):
            continue
        zone_lines.append(line)
        token = line.split(",", 1)[0].strip().lower()
        if token:
            type_counts[token] = type_counts.get(token, 0) + 1
    return zone_lines, type_counts


def safe_rmtree(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)


def copy_project_tree(src_root: Path, dst_root: Path) -> None:
    if not src_root.exists():
        raise FileNotFoundError(f"Source tree not found: {src_root}")
    shutil.copytree(src_root, dst_root)


def rewrite_zone_for_bundle(
    source_zone_path: Path,
    bundle_zone_path: Path,
    source_project_name: str,
    bundle_name: str,
) -> None:
    text = source_zone_path.read_text(encoding="utf-8", errors="ignore")
    if source_project_name == bundle_name:
        bundle_zone_path.write_text(text, encoding="utf-8")
        return

    rewritten: List[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if line.lower() == f"mapents,{source_project_name.lower()}":
            rewritten.append(f"mapents,{bundle_name}")
        else:
            rewritten.append(raw)
    bundle_zone_path.write_text("\n".join(rewritten).rstrip() + "\n", encoding="utf-8")


def maybe_copy_compiled_ff(output_folder: Path, bundle_name: str, install_zone_dir: Path) -> Dict[str, str]:
    candidates = [
        output_folder / "zone" / "all" / f"{bundle_name}.ff",
        output_folder / f"{bundle_name}.ff",
    ]
    ff_src = next((path for path in candidates if path.exists()), None)
    if ff_src is None:
        return {}
    install_zone_dir.mkdir(parents=True, exist_ok=True)
    ff_dst = install_zone_dir / ff_src.name
    shutil.copy2(ff_src, ff_dst)
    return {"ff_source": str(ff_src), "ff_installed_to": str(ff_dst)}


def file_count(root: Path) -> int:
    if not root.exists():
        return 0
    return sum(1 for _ in root.rglob("*") if _.is_file())


def resolve_optional_path(path_value: str, repo_root: Path) -> Path:
    path = Path(path_value)
    if not path.is_absolute():
        path = (repo_root / path).resolve()
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Finalize a remediated asset-port project into a BO2 integration bundle.")
    parser.add_argument("--project-root", required=True, help="Path to map-port project root.")
    parser.add_argument("--project-name", default="", help="Project name (defaults to project-root folder name).")
    parser.add_argument(
        "--output-root",
        default="_build/asset_port_pipeline/integration_ready",
        help="Root where finalized integration bundles are written.",
    )
    parser.add_argument(
        "--bundle-name",
        default="",
        help="Bundle/output zone name (defaults to project-name).",
    )
    parser.add_argument("--compile", action="store_true", help="Compile the finalized bundle with Linker.")
    parser.add_argument("--linker", default="tools/oat/Linker.exe", help="Path to Linker.exe")
    parser.add_argument(
        "--load-zones",
        nargs="*",
        default=["zone/all/common_zm.ff"],
        help="Preload zones for linker compile (supports semicolon-separated values).",
    )
    parser.add_argument(
        "--install-zone-dir",
        default="",
        help="Optional destination directory (for example mods/<mod>/zone/all) to copy compiled ff.",
    )
    parser.add_argument(
        "--output-report",
        default="_build/asset_port_pipeline/finalize_bo2_integration_report.json",
        help="Output report JSON path.",
    )
    args = parser.parse_args()

    repo_root = Path.cwd().resolve()

    project_root = resolve_optional_path(args.project_root, repo_root)
    if not project_root.exists():
        raise FileNotFoundError(f"project-root not found: {project_root}")

    source_project_name = sanitize_name(args.project_name or project_root.name)
    source_zone_path = project_root / "zone_source" / f"{source_project_name}.zone"
    source_zone_root = project_root / "zone_raw" / source_project_name
    if not source_zone_path.exists():
        raise FileNotFoundError(f"Zone file not found: {source_zone_path}")
    if not source_zone_root.exists():
        raise FileNotFoundError(f"zone_raw project root not found: {source_zone_root}")

    bundle_name = sanitize_name(args.bundle_name or source_project_name)
    output_root = resolve_optional_path(args.output_root, repo_root)
    bundle_root = output_root / bundle_name
    bundle_zone_source = bundle_root / "zone_source"
    bundle_zone_path = bundle_zone_source / f"{bundle_name}.zone"
    bundle_zone_root = bundle_root / "zone_raw" / bundle_name
    linker_output_root = bundle_root / "out"

    safe_rmtree(bundle_root)
    bundle_zone_source.mkdir(parents=True, exist_ok=True)
    copy_project_tree(source_zone_root, bundle_zone_root)
    # Copy top-level support directories (accuracy graphs, etc.) if present.
    for support_dir in ("accuracy",):
        src_support = project_root / support_dir
        dst_support = bundle_root / support_dir
        if src_support.is_dir():
            shutil.copytree(src_support, dst_support)
    rewrite_zone_for_bundle(
        source_zone_path=source_zone_path,
        bundle_zone_path=bundle_zone_path,
        source_project_name=source_project_name,
        bundle_name=bundle_name,
    )

    if source_project_name != bundle_name:
        old_ents = bundle_zone_root / "maps" / "mp" / f"{source_project_name}.d3dbsp.ents"
        new_ents = bundle_zone_root / "maps" / "mp" / f"{bundle_name}.d3dbsp.ents"
        if old_ents.exists() and not new_ents.exists():
            new_ents.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(old_ents), str(new_ents))

    linker_result: Dict[str, Any] = {}
    installed: Dict[str, str] = {}
    resolved_load_zones: List[str] = []

    if args.compile:
        linker_path = resolve_optional_path(args.linker, repo_root)
        if not linker_path.exists():
            raise FileNotFoundError(f"Linker not found: {linker_path}")
        load_zone_items = parse_load_zones(args.load_zones)
        load_zone_paths = resolve_paths(load_zone_items, base=repo_root)
        missing_loads = [str(path) for path in load_zone_paths if not path.exists()]
        if missing_loads:
            raise FileNotFoundError("Missing load zones: " + ", ".join(missing_loads))

        linker_output_root.mkdir(parents=True, exist_ok=True)
        linker_result = run_linker(
            linker_path=linker_path,
            project_name=bundle_name,
            base_folder=bundle_root,
            output_folder=linker_output_root,
            load_zones=load_zone_paths,
            verbose=False,
        )
        resolved_load_zones = [str(path) for path in load_zone_paths]

        if args.install_zone_dir and linker_result.get("status") == "pass":
            install_zone_dir = resolve_optional_path(args.install_zone_dir, repo_root)
            installed = maybe_copy_compiled_ff(linker_output_root, bundle_name=bundle_name, install_zone_dir=install_zone_dir)

    zone_lines, zone_type_counts = parse_zone_lines(bundle_zone_path)

    report = {
        "generated_at_utc": dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "source": {
            "project_root": str(project_root),
            "project_name": source_project_name,
            "zone_file": str(source_zone_path),
        },
        "bundle": {
            "bundle_root": str(bundle_root),
            "bundle_name": bundle_name,
            "zone_file": str(bundle_zone_path),
            "zone_raw_root": str(bundle_zone_root),
            "zone_line_count": len(zone_lines),
            "zone_asset_type_counts": zone_type_counts,
            "zone_raw_file_count": file_count(bundle_zone_root),
        },
        "compile": {
            "enabled": bool(args.compile),
            "load_zones": resolved_load_zones,
            "linker_result": linker_result,
            "linker_output_root": str(linker_output_root) if args.compile else "",
        },
        "install": installed,
    }

    report_path = resolve_optional_path(args.output_report, repo_root)
    save_json(report_path, report)

    compile_status = report["compile"]["linker_result"].get("status", "skipped") if args.compile else "skipped"
    print(f"Saved integration report: {report_path}")
    print(
        f"bundle={bundle_name} "
        f"zone_lines={report['bundle']['zone_line_count']} "
        f"zone_raw_files={report['bundle']['zone_raw_file_count']} "
        f"compile={compile_status}"
    )


if __name__ == "__main__":
    main()
