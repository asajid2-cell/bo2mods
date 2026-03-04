from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple


ASSET_START_RE = re.compile(r'^\s*"([^"]+)"\s+\(\s*"([^"]+)"\s*\)\s*$')
PROP_RE = re.compile(r'^\s*"([^"]+)"\s+"([^"]*)"\s*$')


def normalize_ref(value: str) -> str:
    # Normalize separators and collapse accidental doubled slashes from dump refs.
    normalized = value.replace("\\", "/").strip()
    normalized = re.sub(r"/+", "/", normalized)
    return normalized.lstrip("/")


def normalize_for_cmp(value: str) -> str:
    return normalize_ref(value).lower()


def parse_gdt(gdt_path: Path) -> List[Dict[str, object]]:
    entries: List[Dict[str, object]] = []
    current: Optional[Dict[str, object]] = None

    for raw_line in gdt_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.rstrip("\r\n")
        if not line.strip():
            continue

        start_match = ASSET_START_RE.match(line)
        if start_match:
            current = {
                "name": start_match.group(1),
                "gdf": start_match.group(2),
                "props": {},
            }
            continue

        if line.strip() == "}":
            if current is not None:
                entries.append(current)
            current = None
            continue

        if current is None:
            continue

        prop_match = PROP_RE.match(line)
        if not prop_match:
            continue
        key = prop_match.group(1)
        value = prop_match.group(2)
        props = current["props"]
        assert isinstance(props, dict)
        props[key] = value

    return entries


def candidate_paths(t7_root: Path, ref_value: str) -> List[Path]:
    normalized = normalize_ref(ref_value)
    lowered = normalized.lower()
    candidates: List[Path] = []

    def add(p: Path) -> None:
        if p not in candidates:
            candidates.append(p)

    # Direct path in dump root.
    add(t7_root / normalized)

    # References that begin with "_midgetblaster/..." need a container root.
    if lowered.startswith("_midgetblaster/"):
        tail = normalized[len("_midgetblaster/") :].lstrip("/\\")
        add(t7_root / "model_export" / "_midgetblaster" / tail)
        add(t7_root / "xanim_export" / "_midgetblaster" / tail)
        add(t7_root / "texture_assets" / "_midgetblaster" / tail)
        add(t7_root / "source_data" / "_midgetblaster" / tail)

    # FX/raw assets usually live under share/raw.
    if lowered.startswith("fx/") or lowered.startswith("sound/") or lowered.startswith("raw/"):
        add(t7_root / "share" / "raw" / normalized)

    # Safety: when the reference already includes a root folder but mixed separators.
    if lowered.startswith("model_export/"):
        add(t7_root / normalized)
    if lowered.startswith("xanim_export/"):
        add(t7_root / normalized)
    if lowered.startswith("texture_assets/"):
        add(t7_root / normalized)

    return candidates


def resolve_reference(t7_root: Path, ref_value: str) -> Tuple[Optional[Path], List[str]]:
    tried: List[str] = []
    for candidate in candidate_paths(t7_root=t7_root, ref_value=ref_value):
        tried.append(str(candidate))
        if candidate.exists() and candidate.is_file():
            return candidate, tried
    return None, tried


def token_for_gdf(gdf_name: str) -> str:
    token = gdf_name.strip().lower()
    if token.endswith(".gdf"):
        token = token[:-4]
    mapping = {
        "xanim": "xanim",
        "projectileweapon": "weapon",
        "weapon": "weapon",
        "image": "image",
        "material": "material",
        "xmodel": "xmodel",
    }
    return mapping.get(token, token)


def build_zone_lines(entries: Sequence[Dict[str, object]]) -> List[str]:
    lines: List[str] = []
    seen = set()

    for entry in entries:
        name = str(entry.get("name", "")).strip()
        gdf = str(entry.get("gdf", "")).strip()
        if not name or not gdf:
            continue
        token = token_for_gdf(gdf)
        line = f"{token},{name}"
        key = line.lower()
        if key in seen:
            continue
        seen.add(key)
        lines.append(line)

    return lines


def write_zone(zone_path: Path, lines: Sequence[str]) -> None:
    zone_path.parent.mkdir(parents=True, exist_ok=True)
    text = ["// Auto-generated: BO3 thundergun bundle", ">game,T6", ""]
    text.extend(lines)
    zone_path.write_text("\n".join(text).rstrip() + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract and stage BO3 Thundergun bundle from a T7 dump.")
    parser.add_argument(
        "--t7-root",
        required=True,
        help="Root path of dumped T7 assets (contains model_export, xanim_export, texture_assets, source_data).",
    )
    parser.add_argument(
        "--gdt",
        default="source_data/_midgetblaster/t7_thundergun.gdt",
        help="Path to t7_thundergun.gdt (absolute or relative to --t7-root).",
    )
    parser.add_argument(
        "--output-root",
        default="_build/asset_port_pipeline/thundergun_t7_bundle",
        help="Output root for staged assets/manifests.",
    )
    parser.add_argument(
        "--no-copy",
        action="store_true",
        help="Parse and report only; do not copy referenced files.",
    )
    parser.add_argument(
        "--report",
        default="_build/asset_port_pipeline/thundergun_t7_bundle_report.json",
        help="Output report JSON path.",
    )
    args = parser.parse_args()

    repo_root = Path.cwd().resolve()
    t7_root = Path(args.t7_root)
    if not t7_root.is_absolute():
        t7_root = (repo_root / t7_root).resolve()
    if not t7_root.exists():
        raise FileNotFoundError(f"T7 root not found: {t7_root}")

    gdt_path = Path(args.gdt)
    if not gdt_path.is_absolute():
        gdt_path = (t7_root / gdt_path).resolve()
    if not gdt_path.exists():
        raise FileNotFoundError(f"GDT not found: {gdt_path}")

    output_root = Path(args.output_root)
    if not output_root.is_absolute():
        output_root = (repo_root / output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    staged_root = output_root / "staged"
    manifest_dir = output_root / "manifests"
    manifest_dir.mkdir(parents=True, exist_ok=True)

    entries = parse_gdt(gdt_path)

    weapon_entries = [
        entry
        for entry in entries
        if str(entry.get("gdf", "")).lower() == "projectileweapon.gdf"
        and "thundergun" in str(entry.get("name", "")).lower()
    ]
    xmodel_entries = [
        entry
        for entry in entries
        if str(entry.get("gdf", "")).lower() == "xmodel.gdf"
        and "thundergun" in str(entry.get("name", "")).lower()
    ]
    xanim_entries = [
        entry
        for entry in entries
        if str(entry.get("gdf", "")).lower() == "xanim.gdf"
        and "thunder_gun" in str(entry.get("name", "")).lower()
    ]
    material_entries = [
        entry
        for entry in entries
        if str(entry.get("gdf", "")).lower() == "material.gdf"
        and "thundergun" in str(entry.get("name", "")).lower()
    ]
    image_entries = [
        entry
        for entry in entries
        if str(entry.get("gdf", "")).lower() == "image.gdf"
        and "thundergun" in str(entry.get("name", "")).lower()
    ]

    refs: List[Dict[str, str]] = []
    for entry in entries:
        name = str(entry.get("name", ""))
        gdf = str(entry.get("gdf", ""))
        props = entry.get("props", {})
        if not isinstance(props, dict):
            continue
        for key in ("baseImage", "filename"):
            value = str(props.get(key, "")).strip()
            if not value:
                continue
            refs.append(
                {
                    "entry_name": name,
                    "entry_gdf": gdf,
                    "key": key,
                    "value": value,
                }
            )

    copied: List[Dict[str, str]] = []
    missing: List[Dict[str, object]] = []
    copied_sources = set()

    for ref in refs:
        source, tried = resolve_reference(t7_root=t7_root, ref_value=ref["value"])
        if source is None:
            missing.append({**ref, "tried": tried[:10]})
            continue

        if source in copied_sources:
            continue
        copied_sources.add(source)

        rel = source.relative_to(t7_root)
        destination = staged_root / rel
        if not args.no_copy:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        copied.append(
            {
                "source": str(source),
                "relative": str(rel).replace("\\", "/"),
                "destination": str(destination),
                "bytes": str(source.stat().st_size),
            }
        )

    zone_entries = weapon_entries + xmodel_entries + xanim_entries + material_entries + image_entries
    zone_lines = build_zone_lines(zone_entries)
    zone_path = output_root / "zone_source" / "thundergun_t7_bundle.zone"
    write_zone(zone_path=zone_path, lines=zone_lines)

    report_payload = {
        "generated_at_utc": dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "t7_root": str(t7_root),
        "gdt": str(gdt_path),
        "output_root": str(output_root),
        "copy_enabled": not bool(args.no_copy),
        "counts": {
            "entries_total": len(entries),
            "refs_total": len(refs),
            "copied_unique_files": len(copied),
            "missing_refs": len(missing),
            "weapon_entries": len(weapon_entries),
            "xmodel_entries": len(xmodel_entries),
            "xanim_entries": len(xanim_entries),
            "material_entries": len(material_entries),
            "image_entries": len(image_entries),
            "zone_lines": len(zone_lines),
        },
        "weapons": weapon_entries,
        "xmodels": xmodel_entries,
        "xanims": xanim_entries,
        "materials": material_entries,
        "images": image_entries,
        "copied_files": copied,
        "missing_references": missing[:2000],
        "zone_file": str(zone_path),
    }

    report_path = Path(args.report)
    if not report_path.is_absolute():
        report_path = (repo_root / report_path).resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report_payload, indent=2), encoding="utf-8")

    # Save thin manifests for quick downstream use.
    (manifest_dir / "weapons.json").write_text(json.dumps(weapon_entries, indent=2), encoding="utf-8")
    (manifest_dir / "xmodels.json").write_text(json.dumps(xmodel_entries, indent=2), encoding="utf-8")
    (manifest_dir / "xanims.json").write_text(json.dumps(xanim_entries, indent=2), encoding="utf-8")
    (manifest_dir / "materials.json").write_text(json.dumps(material_entries, indent=2), encoding="utf-8")
    (manifest_dir / "images.json").write_text(json.dumps(image_entries, indent=2), encoding="utf-8")

    print(f"Saved thundergun bundle report: {report_path}")
    print(
        "entries="
        f"{report_payload['counts']['entries_total']} "
        "refs="
        f"{report_payload['counts']['refs_total']} "
        "copied="
        f"{report_payload['counts']['copied_unique_files']} "
        "missing="
        f"{report_payload['counts']['missing_refs']}"
    )
    print(f"Saved zone source: {zone_path}")


if __name__ == "__main__":
    main()
