from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple


NUMERIC_RE = re.compile(r"^-?\d+(?:\.\d+)?$")


def parse_weaponfile_text(text: str) -> Tuple[List[str], Dict[str, str]]:
    payload = text.lstrip("\ufeff").strip().replace("\r", "").replace("\n", "")
    if not payload:
        raise ValueError("empty weapon file")
    parts = payload.split("\\")
    if not parts or parts[0] != "WEAPONFILE":
        raise ValueError("weapon file does not start with WEAPONFILE marker")

    ordered_keys: List[str] = []
    data: Dict[str, str] = {}
    i = 1
    while i < len(parts):
        key = parts[i]
        value = parts[i + 1] if i + 1 < len(parts) else ""
        if key:
            if key not in data:
                ordered_keys.append(key)
            data[key] = value
        i += 2

    return ordered_keys, data


def read_weaponfile(path: Path) -> Tuple[List[str], Dict[str, str]]:
    return parse_weaponfile_text(path.read_text(encoding="utf-8", errors="ignore"))


def write_weaponfile(path: Path, ordered_keys: Sequence[str], data: Dict[str, str]) -> None:
    keys = list(ordered_keys)
    seen = set(keys)
    for key in data.keys():
        if key not in seen:
            keys.append(key)
            seen.add(key)

    parts: List[str] = ["WEAPONFILE"]
    for key in keys:
        parts.append(key)
        parts.append(str(data.get(key, "")))
    text = "\\".join(parts)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def is_numeric_string(value: str) -> bool:
    return bool(NUMERIC_RE.fullmatch(value.strip()))


def parse_numeric(value: str) -> float:
    stripped = value.strip()
    if not is_numeric_string(stripped):
        raise ValueError(f"not numeric: {value}")
    return float(stripped)


def format_like(value: float, original: str) -> str:
    original = original.strip()
    if "." in original:
        decimals = max(0, len(original.split(".", 1)[1]))
        return f"{value:.{decimals}f}"
    if math.isfinite(value):
        return str(int(round(value)))
    return original


def percentile(sorted_values: Sequence[float], q: float) -> float:
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return float(sorted_values[0])
    q = max(0.0, min(1.0, q))
    idx = (len(sorted_values) - 1) * q
    low = int(math.floor(idx))
    high = int(math.ceil(idx))
    if low == high:
        return float(sorted_values[low])
    frac = idx - low
    return float(sorted_values[low] * (1.0 - frac) + sorted_values[high] * frac)


def is_anim_field(field: str) -> bool:
    name = field.lower()
    return "anim" in name or name.startswith("dtp_")


def is_model_field(field: str) -> bool:
    name = field.lower()
    return "model" in name


def normalize_token(value: str) -> str:
    return value.strip().lower()


def unique_non_empty(values: Iterable[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for raw in values:
        value = str(raw).strip()
        if not value:
            continue
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(value)
    return out
