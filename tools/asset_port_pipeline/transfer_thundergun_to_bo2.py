from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List


LOGIC_REL_PATHS = [
    "maps/mp/zombies/_zm_weap_thundergun.gsc",
    "clientscripts/mp/zombies/_zm_weap_thundergun.csc",
    "weapons/thundergun_zm",
    "weapons/thundergun_upgraded_zm",
]


def normalize_line(value: str) -> str:
    return value.strip().replace("\\", "/")


def run_extractor(
    repo_root: Path,
    t7_root: Path,
    bundle_root: Path,
    bundle_report: Path,
) -> None:
    extractor = repo_root / "tools" / "asset_port_pipeline" / "extract_t7_thundergun_bundle.py"
    cmd = [
        sys.executable,
        str(extractor),
        "--t7-root",
        str(t7_root),
        "--output-root",
        str(bundle_root),
        "--report",
        str(bundle_report),
    ]
    subprocess.run(cmd, check=True, cwd=repo_root)


def copy_logic_files(source_mod: Path, target_mod_raw: Path) -> List[Dict[str, str]]:
    copied: List[Dict[str, str]] = []
    for rel in LOGIC_REL_PATHS:
        src = source_mod / rel
        # Common local layout keeps weapon files under weapons_backup/.
        if (not src.exists() or not src.is_file()) and rel.startswith("weapons/"):
            alt = source_mod / "weapons_backup" / Path(rel).name
            if alt.exists() and alt.is_file():
                src = alt
        if not src.exists() or not src.is_file():
            raise FileNotFoundError(f"Missing required BO2 logic file: {src}")
        dst = target_mod_raw / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied.append(
            {
                "source": str(src),
                "destination": str(dst),
                "relative": rel,
            }
        )
    return copied


def read_zone_lines(zone_file: Path) -> List[str]:
    lines: List[str] = []
    for raw in zone_file.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = normalize_line(raw)
        if not line or line.startswith("//") or line.startswith(">"):
            continue
        lines.append(line)
    return lines


def write_zone_patch(zone_out: Path, lines: List[str]) -> None:
    seen = set()
    deduped: List[str] = []
    for line in lines:
        key = line.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(line)

    zone_out.parent.mkdir(parents=True, exist_ok=True)
    payload = [
        "// Auto-generated: BO3 Thundergun transfer bundle for BO2 integration",
        ">game,T6",
        "",
    ]
    payload.extend(deduped)
    zone_out.write_text("\n".join(payload).rstrip() + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Transfer BO3 Thundergun assets + BO2 logic into an integration-ready BO2 bundle."
    )
    parser.add_argument(
        "--t7-root",
        required=True,
        help="Root path of dumped T7 assets.",
    )
    parser.add_argument(
        "--source-mod",
        default="mods/zm_roguelike_panzer",
        help="BO2 mod root that already contains working Thundergun logic files.",
    )
    parser.add_argument(
        "--output-root",
        default="_build/asset_port_pipeline/thundergun_bo2_transfer",
        help="Transfer output root.",
    )
    parser.add_argument(
        "--skip-extract",
        action="store_true",
        help="Reuse existing extracted bundle instead of re-running extractor.",
    )
    parser.add_argument(
        "--report",
        default="_build/asset_port_pipeline/thundergun_bo2_transfer_report.json",
        help="Output transfer report JSON path.",
    )
    args = parser.parse_args()

    repo_root = Path.cwd().resolve()
    t7_root = Path(args.t7_root)
    if not t7_root.is_absolute():
        t7_root = (repo_root / t7_root).resolve()
    if not t7_root.exists():
        raise FileNotFoundError(f"T7 root not found: {t7_root}")

    source_mod = Path(args.source_mod)
    if not source_mod.is_absolute():
        source_mod = (repo_root / source_mod).resolve()
    if not source_mod.exists():
        raise FileNotFoundError(f"Source mod root not found: {source_mod}")

    output_root = Path(args.output_root)
    if not output_root.is_absolute():
        output_root = (repo_root / output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    bundle_root = output_root / "t7_bundle"
    bundle_report = output_root / "t7_bundle_report.json"
    if not args.skip_extract:
        run_extractor(repo_root=repo_root, t7_root=t7_root, bundle_root=bundle_root, bundle_report=bundle_report)
    if not bundle_report.exists():
        raise FileNotFoundError(f"Bundle report not found: {bundle_report}")

    bundle_data = json.loads(bundle_report.read_text(encoding="utf-8"))
    counts = bundle_data.get("counts", {})
    missing_refs = int(counts.get("missing_refs", -1))
    if missing_refs != 0:
        raise RuntimeError(
            f"Thundergun bundle has unresolved references (missing_refs={missing_refs}). "
            "Fix extractor/reference mapping before transfer."
        )

    target_mod_raw = output_root / "mod_raw"
    copied_logic = copy_logic_files(source_mod=source_mod, target_mod_raw=target_mod_raw)

    bundle_zone = bundle_root / "zone_source" / "thundergun_t7_bundle.zone"
    if not bundle_zone.exists():
        raise FileNotFoundError(f"Expected bundle zone file not found: {bundle_zone}")

    zone_lines = read_zone_lines(bundle_zone)
    zone_lines.extend(
        [
            "script,maps/mp/zombies/_zm_weap_thundergun.gsc",
            "script,clientscripts/mp/zombies/_zm_weap_thundergun.csc",
            "weapon,thundergun_zm",
            "weapon,thundergun_upgraded_zm",
        ]
    )
    zone_out = output_root / "zone_source" / "thundergun_town_transfer.zone"
    write_zone_patch(zone_out=zone_out, lines=zone_lines)

    report_path = Path(args.report)
    if not report_path.is_absolute():
        report_path = (repo_root / report_path).resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)

    report_payload = {
        "generated_at_utc": dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "t7_root": str(t7_root),
        "source_mod": str(source_mod),
        "output_root": str(output_root),
        "bundle_report": str(bundle_report),
        "zone_patch": str(zone_out),
        "counts": {
            "t7_entries_total": int(counts.get("entries_total", 0)),
            "t7_refs_total": int(counts.get("refs_total", 0)),
            "t7_copied_unique_files": int(counts.get("copied_unique_files", 0)),
            "t7_missing_refs": missing_refs,
            "logic_files_copied": len(copied_logic),
            "zone_lines": len(read_zone_lines(zone_out)),
        },
        "copied_logic_files": copied_logic,
        "known_blockers": [
            "T7 .XMODEL_BIN and .xanim_bin still require conversion to BO2-linkable raw assets before final ff compile."
        ],
    }
    report_path.write_text(json.dumps(report_payload, indent=2), encoding="utf-8")

    print(f"Transfer output root: {output_root}")
    print(f"Bundle copied files: {report_payload['counts']['t7_copied_unique_files']}")
    print(f"Logic files copied: {report_payload['counts']['logic_files_copied']}")
    print(f"Zone patch: {zone_out}")
    print(f"Saved transfer report: {report_path}")


if __name__ == "__main__":
    main()
