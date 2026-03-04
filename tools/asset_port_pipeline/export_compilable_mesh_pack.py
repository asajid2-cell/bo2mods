from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
from pathlib import Path
from typing import Any, Dict, List, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent

import sys

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common import save_json  # noqa: E402
from linker_oracle import sanitize_name  # noqa: E402


def parse_zone_assets(zone_path: Path) -> List[Tuple[str, str]]:
    assets: List[Tuple[str, str]] = []
    for raw in zone_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("//") or line.startswith(">"):
            continue
        if "," not in line:
            continue
        token, name = line.split(",", 1)
        token = token.strip().lower()
        name = name.strip()
        if token and name:
            assets.append((token, name))
    return assets


def resolve_xmodel_json(xmodel_root: Path, asset_name: str) -> Path:
    rel = Path(asset_name.strip().replace("\\", "/"))
    candidates = [
        xmodel_root / rel.with_suffix(".json"),
        xmodel_root / (rel.name + ".json"),
    ]
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate
    raise FileNotFoundError(f"xmodel json not found for '{asset_name}' under {xmodel_root}")


def resolve_lod_source(project_zone_root: Path, xmodel_json_path: Path, lod_file: str) -> Path:
    rel = Path(str(lod_file).replace("\\", "/"))
    candidates = [
        xmodel_json_path.parent / rel,
        project_zone_root / rel,
        project_zone_root / "model_export" / rel.name,
    ]
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate
    raise FileNotFoundError(
        f"LOD source '{lod_file}' not found for '{xmodel_json_path.name}' "
        f"(checked: {', '.join(str(path) for path in candidates)})"
    )


def export_mesh_pack(
    project_root: Path,
    project_name: str,
    output_root: Path,
) -> Dict[str, Any]:
    zone_path = project_root / "zone_source" / f"{project_name}.zone"
    project_zone_root = project_root / "zone_raw" / project_name
    xmodel_root = project_zone_root / "xmodel"
    if not zone_path.exists():
        raise FileNotFoundError(f"Zone file not found: {zone_path}")
    if not xmodel_root.exists():
        raise FileNotFoundError(f"xmodel root not found: {xmodel_root}")

    mesh_root = output_root / project_name
    export_xmodel_root = mesh_root / "xmodel"
    export_model_root = mesh_root / "model_export"
    export_xmodel_root.mkdir(parents=True, exist_ok=True)
    export_model_root.mkdir(parents=True, exist_ok=True)

    zone_assets = parse_zone_assets(zone_path)
    xmodel_assets = [name for token, name in zone_assets if token in {"xmodel", "xmodelalias"}]

    rows: List[Dict[str, Any]] = []
    copied_lods = 0
    missing_xmodels: List[str] = []
    missing_lods: List[Dict[str, str]] = []

    seen_xmodels = set()
    for asset_name in xmodel_assets:
        key = asset_name.lower()
        if key in seen_xmodels:
            continue
        seen_xmodels.add(key)
        try:
            src_json = resolve_xmodel_json(xmodel_root, asset_name)
        except FileNotFoundError:
            missing_xmodels.append(asset_name)
            continue

        try:
            payload = json.loads(src_json.read_text(encoding="utf-8"))
        except Exception:
            missing_xmodels.append(asset_name)
            continue

        export_name = sanitize_name(Path(asset_name).stem)
        dst_json = export_xmodel_root / f"{export_name}.json"

        new_lods: List[Dict[str, Any]] = []
        for idx, lod in enumerate(payload.get("lods", [])):
            lod_file = str(lod.get("file", "")).strip()
            if not lod_file:
                continue
            try:
                src_lod = resolve_lod_source(project_zone_root, src_json, lod_file)
            except FileNotFoundError:
                missing_lods.append({"xmodel": asset_name, "lod_file": lod_file})
                continue
            ext = src_lod.suffix.lower() or ".glb"
            dst_lod_name = f"{export_name}_lod{idx}{ext}"
            dst_lod = export_model_root / dst_lod_name
            if not dst_lod.exists():
                shutil.copy2(src_lod, dst_lod)
                copied_lods += 1
            staged_lod = dict(lod)
            staged_lod["file"] = f"model_export/{dst_lod_name}"
            new_lods.append(staged_lod)

        if not new_lods:
            missing_xmodels.append(asset_name)
            continue

        payload["lods"] = new_lods
        dst_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        rows.append(
            {
                "asset_name": asset_name,
                "source_json": str(src_json),
                "export_json": str(dst_json),
                "lod_count": len(new_lods),
            }
        )

    return {
        "generated_at_utc": dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "project_root": str(project_root),
        "project_name": project_name,
        "zone_file": str(zone_path),
        "output_root": str(mesh_root),
        "counts": {
            "zone_assets": len(zone_assets),
            "xmodel_assets": len(seen_xmodels),
            "exported_xmodels": len(rows),
            "copied_lods": copied_lods,
            "missing_xmodels": len(missing_xmodels),
            "missing_lods": len(missing_lods),
        },
        "rows": rows,
        "missing_xmodels": sorted(set(missing_xmodels)),
        "missing_lods": missing_lods,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Export final compilable xmodel mesh pack from remediated map project.")
    parser.add_argument("--project-root", required=True, help="Path to remediated map project root.")
    parser.add_argument("--project-name", default="", help="Project/map name (defaults to project-root folder name).")
    parser.add_argument(
        "--output-root",
        default="_build/asset_port_pipeline/mesh_packs",
        help="Output root for exported mesh pack.",
    )
    parser.add_argument(
        "--output-report",
        default="_build/asset_port_pipeline/mesh_pack_export_report.json",
        help="Output JSON report path.",
    )
    args = parser.parse_args()

    repo_root = Path.cwd().resolve()

    project_root = Path(args.project_root)
    if not project_root.is_absolute():
        project_root = (repo_root / project_root).resolve()
    if not project_root.exists():
        raise FileNotFoundError(f"project-root not found: {project_root}")

    project_name = sanitize_name(args.project_name or project_root.name)

    output_root = Path(args.output_root)
    if not output_root.is_absolute():
        output_root = (repo_root / output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    report = export_mesh_pack(project_root=project_root, project_name=project_name, output_root=output_root)

    output_report = Path(args.output_report)
    if not output_report.is_absolute():
        output_report = (repo_root / output_report).resolve()
    save_json(output_report, report)

    print(f"Saved mesh pack report: {output_report}")
    print(
        f"exported_xmodels={report['counts']['exported_xmodels']} "
        f"copied_lods={report['counts']['copied_lods']} "
        f"missing_xmodels={report['counts']['missing_xmodels']} "
        f"missing_lods={report['counts']['missing_lods']}"
    )


if __name__ == "__main__":
    main()
