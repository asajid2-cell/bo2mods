from __future__ import annotations

import argparse
import datetime as dt
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List

SCRIPT_DIR = Path(__file__).resolve().parent

import sys

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common import save_json  # noqa: E402


ASCII_RUN_RE = re.compile(rb"[\x20-\x7E]{4,}")
IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def discover_script_files(path: Path) -> List[Path]:
    if path.is_file():
        return [path]
    if not path.exists():
        return []
    return sorted([item for item in path.rglob("*") if item.is_file() and item.suffix.lower() in {".gsc", ".csc"}])


def extract_ascii_strings(blob: bytes) -> List[str]:
    out: List[str] = []
    seen = set()
    for match in ASCII_RUN_RE.finditer(blob):
        raw = match.group(0)
        try:
            text = raw.decode("ascii", errors="ignore").strip()
        except Exception:
            continue
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return out


def classify_strings(strings: Iterable[str]) -> Dict[str, List[str]]:
    models: List[str] = []
    animations: List[str] = []
    weapons: List[str] = []
    functions: List[str] = []
    script_refs: List[str] = []
    misc: List[str] = []

    for value in strings:
        low = value.lower()
        if "animtree" in low or low.startswith("ai_") or "viewmodel_" in low or "idle" in low and "anim" in low:
            animations.append(value)
        elif "/" in value and ("character/" in low or "model" in low or "vehicle/" in low):
            models.append(value)
        elif low.endswith("_zm") or "weapon" in low or "grenade" in low:
            weapons.append(value)
        elif ".gsc" in low or ".csc" in low or low.startswith("maps/"):
            script_refs.append(value)
        elif IDENT_RE.match(value):
            functions.append(value)
        else:
            misc.append(value)

    def uniq(items: List[str], limit: int = 400) -> List[str]:
        seen = set()
        out: List[str] = []
        for item in items:
            key = item.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(item)
            if len(out) >= limit:
                break
        return out

    return {
        "models": uniq(models),
        "animations": uniq(animations),
        "weapons": uniq(weapons),
        "functions": uniq(functions),
        "script_refs": uniq(script_refs),
        "misc": uniq(misc, limit=200),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract behavior profile from compiled GSC/CSC binaries.")
    parser.add_argument("--input", required=True, help="Input file or directory.")
    parser.add_argument("--output", default="_build/asset_port_pipeline/compiled_gsc_profile.json", help="Output profile JSON.")
    parser.add_argument("--max-files", type=int, default=0, help="Optional cap for quick runs.")
    args = parser.parse_args()

    repo_root = Path.cwd().resolve()
    input_path = Path(args.input)
    if not input_path.is_absolute():
        input_path = (repo_root / input_path).resolve()
    files = discover_script_files(input_path)
    if args.max_files > 0:
        files = files[: args.max_files]
    if not files:
        raise FileNotFoundError(f"No .gsc/.csc files found in {input_path}")

    rows: List[Dict[str, Any]] = []
    for path in files:
        blob = path.read_bytes()
        strings = extract_ascii_strings(blob)
        classified = classify_strings(strings)
        rows.append(
            {
                "script_path": str(path),
                "size_bytes": len(blob),
                "string_count": len(strings),
                "models": classified["models"],
                "animations": classified["animations"],
                "weapons": classified["weapons"],
                "functions": classified["functions"],
                "script_refs": classified["script_refs"],
                "misc": classified["misc"],
            }
        )

    aggregate = {
        "models": sorted({item for row in rows for item in row["models"]}),
        "animations": sorted({item for row in rows for item in row["animations"]}),
        "weapons": sorted({item for row in rows for item in row["weapons"]}),
        "functions": sorted({item for row in rows for item in row["functions"]}),
        "script_refs": sorted({item for row in rows for item in row["script_refs"]}),
    }

    profile = {
        "generated_at_utc": dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "input": str(input_path),
        "counts": {
            "scripts": len(rows),
            "models": len(aggregate["models"]),
            "animations": len(aggregate["animations"]),
            "weapons": len(aggregate["weapons"]),
            "functions": len(aggregate["functions"]),
            "script_refs": len(aggregate["script_refs"]),
        },
        "aggregate": aggregate,
        "rows": rows,
    }

    output = Path(args.output)
    if not output.is_absolute():
        output = (repo_root / output).resolve()
    save_json(output, profile)
    print(f"Saved compiled GSC profile: {output}")
    print(
        f"scripts={profile['counts']['scripts']} "
        f"models={profile['counts']['models']} "
        f"anims={profile['counts']['animations']} "
        f"weapons={profile['counts']['weapons']}"
    )


if __name__ == "__main__":
    main()
