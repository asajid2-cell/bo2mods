from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


ASSET_TYPE_DIRS: Dict[str, List[str]] = {
    "aitype": ["aitype"],
    "animstatedef": ["animstatedefs"],
    "animtree": ["animtrees"],
    "attachment": ["attachment"],
    "attachmentunique": ["attachmentunique"],
    "camo": ["camo"],
    "character": ["character"],
    "image": ["images"],
    "material": ["materials"],
    "physpreset": ["physic"],
    "rawfile": ["rawfiles"],
    "script": ["maps", "clientscripts"],
    "soundbank": ["soundbank"],
    "stringtable": ["stringtables"],
    "technique": ["techniques"],
    "techset": ["techsets"],
    "techniqueset": ["techsets"],
    "tracer": ["tracer"],
    "vehicle": ["vehicle", "vehicles"],
    "weapon": ["weapons"],
    "xanim": ["xanim", "xanimparts"],
    "xanimparts": ["xanimparts", "xanim"],
    "xmodel": ["xmodel"],
    "xmodelalias": ["xmodelalias"],
    "zbarrier": ["zbarrier"],
    # mapents is handled specially under maps/mp
}


FILE_TOKEN_RE = re.compile(r"[^A-Za-z0-9_]+")


def sanitize_name(value: str) -> str:
    cleaned = FILE_TOKEN_RE.sub("_", value).strip("_").lower()
    return cleaned or "asset"


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


def parse_zone_file(zone_path: Path) -> Tuple[List[Dict[str, str]], List[str]]:
    entries: List[Dict[str, str]] = []
    ipaks: List[str] = []

    for raw in zone_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("//"):
            continue
        if line.startswith(">"):
            if line.lower().startswith(">level.ipak_read,"):
                ipaks.append(line.split(",", 1)[1].strip())
            continue

        parts = line.split(",")
        asset_type = parts[0].strip().lower()
        asset_name = ",".join(parts[1:]).strip().lstrip(",").strip()
        if not asset_type or not asset_name:
            continue
        entries.append(
            {
                "asset_type": asset_type,
                "asset_name": asset_name,
                "raw_line": line,
            }
        )

    return entries, sorted({item for item in ipaks if item})


def discover_type_roots(root: Path, type_dirs: Sequence[str]) -> List[Path]:
    out: List[Path] = []
    for type_dir in type_dirs:
        for directory in root.rglob(type_dir):
            if directory.is_dir():
                out.append(directory)
    return out


def build_asset_index(roots: Sequence[Path], asset_type: str) -> Dict[str, str]:
    type_dirs = ASSET_TYPE_DIRS.get(asset_type.lower(), [])
    if not type_dirs:
        return {}
    index: Dict[str, str] = {}

    for root in roots:
        if not root.exists():
            continue
        for type_root in discover_type_roots(root, type_dirs):
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
                for key in list(keys):
                    if key.startswith("mc/"):
                        keys.add(key[3:])
                    elif asset_type.lower() == "material":
                        keys.add("mc/" + key)
                for key in keys:
                    if key and key not in index:
                        index[key] = str(file_path.resolve())
    return index


def find_asset_path(
    asset_type: str,
    asset_name: str,
    indexes: Dict[str, Dict[str, str]],
    source_map_name: str = "",
    source_root: Optional[Path] = None,
) -> Optional[str]:
    normalized_type = asset_type.lower()
    if normalized_type == "mapents" and source_root is not None:
        map_name = asset_name or source_map_name
        candidate = source_root / "maps" / "mp" / f"{map_name}.d3dbsp.ents"
        if candidate.exists():
            return str(candidate.resolve())
        if source_map_name:
            fallback = source_root / "maps" / "mp" / f"{source_map_name}.d3dbsp.ents"
            if fallback.exists():
                return str(fallback.resolve())
        return None

    index = indexes.get(normalized_type, {})
    if not index:
        return None
    for key in candidate_asset_keys(asset_name, normalized_type):
        if key in index:
            return index[key]
    return None


def phase_for_asset_type(asset_type: str) -> str:
    t = asset_type.lower()
    if t in {"mapents", "clipmap", "gfxworld", "comworld", "gameworldmp", "rawfile", "stringtable"}:
        return "core_map"
    if t in {"xmodel", "xmodelalias", "material", "image", "techniqueset", "techset", "technique", "skinnedverts", "camo", "tracer"}:
        return "render_assets"
    if t in {"weapon", "aitype", "animtree", "animstatedef", "xanim", "xanimparts", "character", "attachment", "attachmentunique", "vehicle", "zbarrier"}:
        return "gameplay_assets"
    if t in {"script", "menu", "menulist"}:
        return "scripts"
    return "other"
