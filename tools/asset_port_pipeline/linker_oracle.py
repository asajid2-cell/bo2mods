from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent

import sys

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common import save_json  # noqa: E402


ERROR_RE = re.compile(r"(?i)\b(error|failed|exception|could not|missing)\b")
WARN_RE = re.compile(r"(?i)\b(warn|warning)\b")
FILE_TOKEN_RE = re.compile(r"[^A-Za-z0-9_]+")
MISSING_ASSET_RE = re.compile(r'Missing asset "([^"]+)" of type "([^"]+)"')

ASSET_TYPE_DIRS = {
    "material": "materials",
    "image": "images",
    "techset": "techsets",
    "techniqueset": "techsets",
    "technique": "techniques",
    "xanim": "xanim",
    "xanimparts": "xanimparts",
    "xmodel": "xmodel",
    "xmodelalias": "xmodelalias",
    "rawfile": "rawfiles",
    "script": "maps",
}

_ASSET_INDEX_CACHE: Dict[Tuple[Tuple[str, ...], str], Dict[str, Dict[str, str]]] = {}


def sanitize_name(value: str) -> str:
    cleaned = FILE_TOKEN_RE.sub("_", value).strip("_").lower()
    return cleaned or "asset"


def parse_load_zones(value: Sequence[str]) -> List[str]:
    out: List[str] = []
    for item in value:
        parts = [part.strip() for part in item.split(";") if part.strip()]
        out.extend(parts)
    return out


def normalize_asset_key(value: str) -> str:
    return value.strip().replace("\\", "/").strip("/").lower()


def candidate_asset_keys(asset_name: str, asset_type: str) -> List[str]:
    raw = normalize_asset_key(asset_name)
    keyset: List[str] = []
    if raw:
        keyset.append(raw)
        if "." in raw:
            keyset.append(raw.rsplit(".", 1)[0])
        keyset.append(Path(raw).name)
        keyset.append(Path(raw).stem)
    if raw.startswith("mc/"):
        keyset.append(raw[3:])
    if asset_type.lower() == "material" and raw and not raw.startswith("mc/"):
        keyset.append("mc/" + raw)
    deduped: List[str] = []
    seen = set()
    for key in keyset:
        nkey = normalize_asset_key(key)
        if nkey and nkey not in seen:
            seen.add(nkey)
            deduped.append(nkey)
    return deduped


def infer_source_zone_name(source_path: Path, dependency_roots: Sequence[Path]) -> Optional[str]:
    source_resolved = source_path.resolve()
    for root in dependency_roots:
        root_resolved = root.resolve()
        try:
            rel = source_resolved.relative_to(root_resolved)
        except ValueError:
            continue

        if root_resolved.name.lower() == "zone_raw" and rel.parts:
            return rel.parts[0]
        if root_resolved.parent.name.lower() == "zone_raw":
            return root_resolved.name
        if rel.parts:
            return rel.parts[0]
    return None


def build_asset_index(roots: Sequence[Path], asset_type: str) -> Dict[str, Dict[str, str]]:
    type_dir = ASSET_TYPE_DIRS.get(asset_type.lower())
    if not type_dir:
        return {}

    key = (tuple(sorted(str(root.resolve()) for root in roots)), type_dir)
    cached = _ASSET_INDEX_CACHE.get(key)
    if cached is not None:
        return cached

    index: Dict[str, Dict[str, str]] = {}
    for root in roots:
        if not root.exists():
            continue
        for type_root in root.rglob(type_dir):
            if not type_root.is_dir():
                continue
            for file_path in type_root.rglob("*"):
                if not file_path.is_file():
                    continue
                rel = file_path.relative_to(type_root).as_posix()
                rel_no_ext = Path(rel).with_suffix("").as_posix()
                base = Path(rel).stem
                keys = {
                    normalize_asset_key(rel),
                    normalize_asset_key(rel_no_ext),
                    normalize_asset_key(base),
                }
                for item in list(keys):
                    if item.startswith("mc/"):
                        keys.add(item[3:])
                    elif type_dir == "materials":
                        keys.add("mc/" + item)
                for lookup in keys:
                    if lookup and lookup not in index:
                        index[lookup] = {"source": str(file_path), "rel": rel}
    _ASSET_INDEX_CACHE[key] = index
    return index


def extract_missing_assets(log_text: str) -> List[Tuple[str, str]]:
    missing: List[Tuple[str, str]] = []
    seen = set()
    for match in MISSING_ASSET_RE.finditer(log_text):
        name = match.group(1).strip()
        asset_type = match.group(2).strip().lower()
        key = (name, asset_type)
        if key not in seen:
            seen.add(key)
            missing.append(key)
    return missing


def stage_missing_assets(
    missing_assets: Sequence[Tuple[str, str]],
    dependency_roots: Sequence[Path],
    project_zone_root: Path,
) -> List[Dict[str, Any]]:
    staged: List[Dict[str, Any]] = []
    visited: set[Tuple[str, str]] = set()

    def stage_asset(asset_name: str, asset_type: str, depth: int = 0) -> None:
        if depth > 3:
            return
        key = (normalize_asset_key(asset_name), asset_type.lower())
        if key in visited:
            return
        visited.add(key)

        type_dir = ASSET_TYPE_DIRS.get(asset_type.lower())
        if not type_dir:
            return
        index = build_asset_index(dependency_roots, asset_type=asset_type)

        source_entry: Optional[Dict[str, str]] = None
        for lookup in candidate_asset_keys(asset_name, asset_type):
            if lookup in index:
                source_entry = index[lookup]
                break
        if source_entry is None:
            return

        src = Path(source_entry["source"])
        dst = project_zone_root / type_dir / source_entry["rel"]
        source_zone = infer_source_zone_name(src, dependency_roots)
        copied = False
        if not dst.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            copied = True

        staged.append(
            {
                "asset_name": asset_name,
                "asset_type": asset_type.lower(),
                "source": str(src),
                "destination": str(dst),
                "copied": copied,
                "source_zone": source_zone or "",
            }
        )

        # Stage transitive dependencies for material, techniqueset, and xmodel files.
        try:
            if asset_type.lower() == "xmodel" and dst.suffix.lower() == ".json":
                # Copy model_export GLB/XMODEL_EXPORT files referenced by LODs.
                payload = json.loads(dst.read_text(encoding="utf-8"))
                source_root = src.parent.parent  # parent of xmodel/ dir
                for lod in payload.get("lods", []):
                    lod_file = str(lod.get("file", "")).strip()
                    if not lod_file:
                        continue
                    lod_src = source_root / lod_file
                    lod_dst = project_zone_root / lod_file
                    if lod_src.exists() and not lod_dst.exists():
                        lod_dst.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(lod_src, lod_dst)
            elif asset_type.lower() == "material" and dst.suffix.lower() == ".json":
                payload = json.loads(dst.read_text(encoding="utf-8"))
                technique_set = str(payload.get("techniqueSet", "")).strip()
                if technique_set:
                    stage_asset(technique_set, "techniqueset", depth + 1)
                textures = payload.get("textures", [])
                if isinstance(textures, list):
                    for texture in textures:
                        if not isinstance(texture, dict):
                            continue
                        image_name = str(texture.get("image", "")).strip()
                        if image_name:
                            stage_asset(image_name, "image", depth + 1)
            elif asset_type.lower() in {"techset", "techniqueset"}:
                text = dst.read_text(encoding="utf-8", errors="ignore")
                for match in re.finditer(r":\s*([A-Za-z0-9_]+)\s*;", text):
                    technique_name = match.group(1).strip()
                    if technique_name:
                        stage_asset(technique_name, "technique", depth + 1)
        except Exception:
            # Keep resolver resilient: dependency parse errors should not kill linking attempts.
            pass

    for asset_name, asset_type in missing_assets:
        stage_asset(asset_name, asset_type, depth=0)
    return staged


ACCU_GRAPH_RE = re.compile(r"Failed to open file for accuracy graph:\s*(.+)", re.IGNORECASE)


def extract_missing_accuracy_graphs(log_text: str) -> List[str]:
    """Extract accuracy graph relative paths from linker warnings."""
    paths: List[str] = []
    seen: set[str] = set()
    for match in ACCU_GRAPH_RE.finditer(log_text):
        rel = match.group(1).strip().strip("\"'")
        if rel and rel not in seen:
            seen.add(rel)
            paths.append(rel)
    return paths


def stage_accuracy_graphs(
    log_text: str,
    dependency_roots: Sequence[Path],
    project_zone_root: Path,
) -> int:
    """Copy missing accuracy graph files from dependency roots into the project.

    Accuracy graphs must sit at ``<project_root>/accuracy/`` (linker base folder),
    NOT inside ``zone_raw/``.  ``project_zone_root`` points to
    ``<project_root>/zone_raw/<name>/``, so we walk two levels up.
    """
    graph_paths = extract_missing_accuracy_graphs(log_text)
    # project_zone_root = .../zone_raw/<name>  → project_root = ...
    project_root = project_zone_root.parent.parent
    # Expand requested paths to also cover counterpart dirs (aivsai ↔ aivsplayer).
    all_rels: set[str] = set()
    for rel in graph_paths:
        all_rels.add(rel)
        parts = Path(rel).parts
        if len(parts) >= 2:
            basename = "/".join(parts[1:])
            all_rels.add(f"aivsai/{basename}")
            all_rels.add(f"aivsplayer/{basename}")
    copied = 0
    for rel in sorted(all_rels):
        dst = project_root / "accuracy" / rel
        if dst.exists():
            continue
        found = False
        for root in dependency_roots:
            # Accuracy files may sit directly under root or inside zone subdirs
            # (e.g. zone_dump/zone_raw/zm_tomb/accuracy/aivsai/pistol.accu).
            candidates = [root / "accuracy" / rel]
            if root.is_dir():
                for zone_dir in root.iterdir():
                    if zone_dir.is_dir():
                        candidates.append(zone_dir / "accuracy" / rel)
            for src in candidates:
                if src.exists():
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)
                    copied += 1
                    found = True
                    break
            if found:
                break
    return copied


def candidate_zone_dirs_from_loads(load_zones: Sequence[Path]) -> List[Path]:
    dirs: List[Path] = []
    seen = set()
    for load_zone in load_zones:
        for candidate in (load_zone.parent, load_zone.parent.parent / "all"):
            resolved = candidate.resolve()
            key = str(resolved).lower()
            if candidate.exists() and key not in seen:
                seen.add(key)
                dirs.append(resolved)
    return dirs


def infer_dependency_load_zones(
    staged_dependencies: Sequence[Dict[str, Any]],
    active_load_zones: Sequence[Path],
) -> List[Path]:
    if not staged_dependencies:
        return []

    zone_hints = sorted(
        {
            str(item.get("source_zone", "")).strip()
            for item in staged_dependencies
            if str(item.get("source_zone", "")).strip()
        }
    )
    if not zone_hints:
        return []

    existing = {str(path.resolve()).lower() for path in active_load_zones}
    candidate_dirs = candidate_zone_dirs_from_loads(active_load_zones)
    additions: List[Path] = []
    for zone_name in zone_hints:
        for zone_dir in candidate_dirs:
            candidate = (zone_dir / f"{zone_name}.ff").resolve()
            key = str(candidate).lower()
            if candidate.exists() and key not in existing:
                existing.add(key)
                additions.append(candidate)
                break
    return additions


def load_xmodel_json(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("_type") != "xmodel":
        raise ValueError(f"Not an xmodel descriptor: {path}")
    if "lods" not in payload or not isinstance(payload["lods"], list):
        raise ValueError(f"xmodel has no 'lods' list: {path}")
    return payload


def resolve_lod_source(xmodel_json_path: Path, lod_file: str) -> Path:
    rel = Path(lod_file)
    candidates = [
        xmodel_json_path.parent / rel,
        xmodel_json_path.parent.parent / rel,
        xmodel_json_path.parent.parent / "model_export" / rel.name,
    ]
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate
    raise FileNotFoundError(
        f"Could not resolve LOD file '{lod_file}' referenced by '{xmodel_json_path}'. "
        f"Checked: {', '.join(str(item) for item in candidates)}"
    )


def stage_xmodel_assets(
    xmodel_jsons: Sequence[Path],
    stage_project_root: Path,
) -> List[str]:
    xmodel_dir = stage_project_root / "xmodel"
    model_export_dir = stage_project_root / "model_export"
    xmodel_dir.mkdir(parents=True, exist_ok=True)
    model_export_dir.mkdir(parents=True, exist_ok=True)

    staged_names: List[str] = []
    used_names: set[str] = set()

    for source_path in xmodel_jsons:
        payload = load_xmodel_json(source_path)
        base_name = sanitize_name(source_path.stem)
        name = base_name
        suffix = 1
        while name in used_names:
            suffix += 1
            name = f"{base_name}_{suffix}"
        used_names.add(name)

        staged_lods: List[Dict[str, Any]] = []
        for idx, lod in enumerate(payload.get("lods", [])):
            lod_file = str(lod.get("file", ""))
            if not lod_file:
                continue
            src_lod_file = resolve_lod_source(source_path, lod_file)
            dst_lod_name = f"{name}_lod{idx}{src_lod_file.suffix.lower() or '.glb'}"
            dst_lod_file = model_export_dir / dst_lod_name
            shutil.copy2(src_lod_file, dst_lod_file)
            staged_lod = dict(lod)
            staged_lod["file"] = f"model_export/{dst_lod_name}"
            staged_lods.append(staged_lod)

        if not staged_lods:
            raise ValueError(f"No valid LOD entries in {source_path}")

        payload["lods"] = staged_lods
        staged_xmodel_path = xmodel_dir / f"{name}.json"
        staged_xmodel_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        staged_names.append(name)

    return staged_names


def write_zone_file(zone_path: Path, xmodel_names: Sequence[str], game: str = "T6") -> None:
    zone_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "// Auto-generated by linker_oracle.py",
        f">game,{game}",
        "",
    ]
    lines.extend([f"xmodel,{name}" for name in xmodel_names])
    zone_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


ZONE_TYPE_TOKEN_MAP = {
    "material": "material",
    "image": "image",
    "techset": "techniqueset",
    "techniqueset": "techniqueset",
    "xmodel": "xmodel",
    "xmodelalias": "xmodel",
    "xanim": "xanim",
    "xanimparts": "xanim",
    "rawfile": "rawfile",
    "script": "script",
}


def zone_type_token(asset_type: str) -> Optional[str]:
    normalized = asset_type.lower().strip()
    return ZONE_TYPE_TOKEN_MAP.get(normalized)


def append_zone_asset_lines(zone_path: Path, assets: Sequence[Dict[str, Any]]) -> None:
    if not assets:
        return
    existing_lines = zone_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    existing_set = {line.strip().lower() for line in existing_lines}
    appended: List[str] = []
    for item in assets:
        token = zone_type_token(item.get("asset_type", ""))
        name = item.get("asset_name", "").strip()
        if not token or not name:
            continue
        line = f"{token},{name}"
        if line.lower() not in existing_set:
            existing_set.add(line.lower())
            appended.append(line)
    if not appended:
        return
    new_text = "\n".join(existing_lines).rstrip() + "\n" + "\n".join(appended) + "\n"
    zone_path.write_text(new_text, encoding="utf-8")


def parse_log_lines(log_text: str) -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []
    for raw in log_text.splitlines():
        line = raw.strip()
        if not line:
            continue
        lowered = line.lower()
        if "failed to open file for accuracy graph" in lowered:
            warnings.append(line)
            continue
        if ERROR_RE.search(line):
            errors.append(line)
        elif WARN_RE.search(line):
            warnings.append(line)
    return errors, warnings


def run_linker(
    linker_path: Path,
    project_name: str,
    base_folder: Path,
    output_folder: Path,
    load_zones: Sequence[Path],
    verbose: bool = False,
) -> Dict[str, Any]:
    cmd: List[str] = [
        str(linker_path),
        "--base-folder",
        str(base_folder),
        "--output-folder",
        str(output_folder),
        "--add-asset-search-path",
        str(base_folder),
        "--add-source-search-path",
        str(base_folder),
    ]
    if verbose:
        cmd.append("--verbose")
    for load_zone in load_zones:
        cmd.extend(["--load", str(load_zone)])
    cmd.append(project_name)

    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    output_text = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
    errors, warnings = parse_log_lines(output_text)
    return {
        "exit_code": proc.returncode,
        "status": "pass" if proc.returncode == 0 else "fail",
        "errors": errors[:400],
        "warnings": warnings[:400],
        "log": output_text,
        "command": cmd,
    }


def compile_xmodels(
    xmodel_jsons: Sequence[Path],
    project_name: str,
    workspace: Path,
    linker_path: Path,
    load_zones: Sequence[Path],
    clean_workspace: bool = True,
    verbose: bool = False,
    auto_resolve_missing: bool = False,
    max_retries: int = 2,
    dependency_roots: Optional[Sequence[Path]] = None,
) -> Dict[str, Any]:
    project_name = sanitize_name(project_name)
    base_folder = workspace / project_name
    project_zone_root = base_folder / "zone_raw" / project_name
    output_folder = workspace / "zone_out"

    if clean_workspace and base_folder.exists():
        shutil.rmtree(base_folder)
    project_zone_root.mkdir(parents=True, exist_ok=True)
    output_folder.mkdir(parents=True, exist_ok=True)

    staged_names = stage_xmodel_assets(xmodel_jsons, stage_project_root=project_zone_root)
    zone_path = base_folder / "zone_source" / f"{project_name}.zone"
    write_zone_file(zone_path, staged_names, game="T6")

    dep_roots = [root.resolve() for root in (dependency_roots or []) if root.exists()]
    active_load_zones = [path.resolve() for path in load_zones]
    attempts: List[Dict[str, Any]] = []
    max_attempts = max(1, int(max_retries) + 1)

    for attempt in range(1, max_attempts + 1):
        linker_result = run_linker(
            linker_path=linker_path,
            project_name=project_name,
            base_folder=base_folder,
            output_folder=output_folder,
            load_zones=active_load_zones,
            verbose=verbose,
        )
        linker_result["attempt"] = attempt
        linker_result["load_zones_used"] = [str(path) for path in active_load_zones]
        linker_result["missing_assets"] = [
            {"asset_name": name, "asset_type": asset_type}
            for name, asset_type in extract_missing_assets(linker_result.get("log", ""))
        ]

        staged_dependencies: List[Dict[str, Any]] = []
        added_load_zones: List[Path] = []
        can_retry = attempt < max_attempts
        if (
            linker_result["status"] == "fail"
            and auto_resolve_missing
            and can_retry
            and dep_roots
            and linker_result["missing_assets"]
        ):
            staged_dependencies = stage_missing_assets(
                missing_assets=[(item["asset_name"], item["asset_type"]) for item in linker_result["missing_assets"]],
                dependency_roots=dep_roots,
                project_zone_root=project_zone_root,
            )
            append_zone_asset_lines(zone_path, staged_dependencies)
            added_load_zones = infer_dependency_load_zones(
                staged_dependencies=staged_dependencies,
                active_load_zones=active_load_zones,
            )
            active_load_zones.extend(added_load_zones)
        linker_result["staged_dependencies"] = staged_dependencies
        linker_result["added_load_zones"] = [str(path) for path in added_load_zones]
        attempts.append(linker_result)

        if linker_result["status"] == "pass":
            break
        if not (auto_resolve_missing and can_retry and (staged_dependencies or added_load_zones)):
            break

    result = {
        "generated_at_utc": dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "project_name": project_name,
        "workspace": str(base_folder),
        "staged_assets": staged_names,
        "xmodel_inputs": [str(path) for path in xmodel_jsons],
        "load_zones": [str(path) for path in active_load_zones],
        "auto_resolve_missing": auto_resolve_missing,
        "max_retries": max_retries,
        "dependency_roots": [str(root) for root in dep_roots],
        "linker_attempts": attempts,
        "linker": attempts[-1] if attempts else {},
    }
    return result


def resolve_paths(items: Iterable[str], base: Path) -> List[Path]:
    out: List[Path] = []
    for item in items:
        path = Path(item)
        if not path.is_absolute():
            path = (base / path).resolve()
        out.append(path)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Compile xmodel assets with OAT Linker and emit pass/fail diagnostics.")
    parser.add_argument("--xmodels", nargs="+", required=True, help="Input xmodel json files.")
    parser.add_argument("--project-name", default="oracle_candidate", help="Linker project name.")
    parser.add_argument("--workspace", default="_build/asset_port_pipeline/linker_oracle", help="Workspace directory.")
    parser.add_argument("--linker", default="tools/oat/Linker.exe", help="Path to Linker.exe")
    parser.add_argument(
        "--load-zones",
        nargs="*",
        default=["zone/all/common_zm.ff"],
        help="FF zones to preload for dependencies (can also use semicolon-separated entries).",
    )
    parser.add_argument("--auto-resolve-missing", action="store_true", help="Retry failed links by staging missing assets.")
    parser.add_argument("--max-retries", type=int, default=2, help="Maximum linker retries when auto-resolve is enabled.")
    parser.add_argument(
        "--dependency-roots",
        nargs="*",
        default=["zone_dump/zone_raw", "_build/t6_asset_dump/zone_raw"],
        help="Roots scanned for missing assets (supports semicolon-separated entries).",
    )
    parser.add_argument("--output", default="_build/asset_port_pipeline/linker_oracle_report.json", help="Output JSON report.")
    parser.add_argument("--keep-workspace", action="store_true", help="Do not clean project workspace before staging.")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose linker output.")
    args = parser.parse_args()

    repo_root = Path.cwd().resolve()
    linker_path = Path(args.linker)
    if not linker_path.is_absolute():
        linker_path = (repo_root / linker_path).resolve()
    if not linker_path.exists():
        raise FileNotFoundError(f"Linker not found: {linker_path}")

    xmodel_paths = resolve_paths(args.xmodels, base=repo_root)
    for path in xmodel_paths:
        if not path.exists():
            raise FileNotFoundError(f"xmodel not found: {path}")

    load_zone_items = parse_load_zones(args.load_zones)
    load_zone_paths = resolve_paths(load_zone_items, base=repo_root)
    missing_loads = [str(path) for path in load_zone_paths if not path.exists()]
    if missing_loads:
        raise FileNotFoundError("Missing load zones: " + ", ".join(missing_loads))

    dependency_root_items = parse_load_zones(args.dependency_roots)
    dependency_roots = [path for path in resolve_paths(dependency_root_items, base=repo_root) if path.exists()]
    if args.auto_resolve_missing and not dependency_roots:
        print("Warning: --auto-resolve-missing enabled but no valid --dependency-roots were found.")

    workspace = Path(args.workspace)
    if not workspace.is_absolute():
        workspace = (repo_root / workspace).resolve()
    workspace.mkdir(parents=True, exist_ok=True)

    result = compile_xmodels(
        xmodel_jsons=xmodel_paths,
        project_name=args.project_name,
        workspace=workspace,
        linker_path=linker_path,
        load_zones=load_zone_paths,
        clean_workspace=not args.keep_workspace,
        verbose=args.verbose,
        auto_resolve_missing=args.auto_resolve_missing,
        max_retries=max(0, args.max_retries),
        dependency_roots=dependency_roots,
    )

    output = Path(args.output)
    if not output.is_absolute():
        output = (repo_root / output).resolve()
    save_json(output, result)

    linker = result["linker"]
    print(f"Saved linker oracle report: {output}")
    print(
        f"status={linker['status']} "
        f"exit_code={linker['exit_code']} "
        f"errors={len(linker['errors'])} "
        f"warnings={len(linker['warnings'])}"
    )


if __name__ == "__main__":
    main()
