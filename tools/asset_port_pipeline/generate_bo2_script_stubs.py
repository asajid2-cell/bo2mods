from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

SCRIPT_DIR = Path(__file__).resolve().parent

import sys

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common import save_json  # noqa: E402
from linker_oracle import sanitize_name  # noqa: E402


def unique_sorted(values: Iterable[str], max_items: int = 300) -> List[str]:
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
        if len(out) >= max_items:
            break
    return sorted(out, key=lambda item: item.lower())


def gsc_array(name: str, values: List[str]) -> str:
    lines = [f"    level._port_{name} = [];"]
    for value in values:
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        lines.append(f'    level._port_{name}[level._port_{name}.size] = "{escaped}";')
    return "\n".join(lines)


def build_script(project_name: str, models: List[str], anims: List[str], weapons: List[str], functions: List[str]) -> str:
    models_block = gsc_array("models", models)
    anims_block = gsc_array("anims", anims)
    weapons_block = gsc_array("weapons", weapons)
    fn_comments = "\n".join([f"// {item}" for item in functions[:120]])

    return f"""init_{project_name}_port_stubs()
{{
{models_block}
{anims_block}
{weapons_block}
    thread {project_name}_port_precache();
}}

{project_name}_port_precache()
{{
    level endon("game_ended");
    for(i = 0; i < level._port_models.size; i++)
    {{
        precacheModel(level._port_models[i]);
    }}
    for(i = 0; i < level._port_anims.size; i++)
    {{
        precacheAnim(level._port_anims[i]);
    }}
    for(i = 0; i < level._port_weapons.size; i++)
    {{
        precacheItem(level._port_weapons[i]);
    }}
}}

// ---- Extracted function symbols (for manual behavior translation) ----
{fn_comments}
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate BO2 GSC stub from extracted compiled script profile.")
    parser.add_argument("--profile", required=True, help="Input JSON profile from extract_compiled_gsc_profile.py")
    parser.add_argument("--project-name", default="map_port", help="Project/map name prefix for generated functions.")
    parser.add_argument("--output", required=True, help="Output .gsc path.")
    parser.add_argument("--max-models", type=int, default=200, help="Max model refs to emit.")
    parser.add_argument("--max-anims", type=int, default=300, help="Max anim refs to emit.")
    parser.add_argument("--max-weapons", type=int, default=120, help="Max weapon refs to emit.")
    parser.add_argument("--report", default="_build/asset_port_pipeline/script_stub_report.json", help="Output report JSON.")
    args = parser.parse_args()

    repo_root = Path.cwd().resolve()
    profile_path = Path(args.profile)
    if not profile_path.is_absolute():
        profile_path = (repo_root / profile_path).resolve()
    if not profile_path.exists():
        raise FileNotFoundError(f"Profile not found: {profile_path}")

    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    aggregate = profile.get("aggregate", {})
    models = unique_sorted(aggregate.get("models", []), max_items=max(1, int(args.max_models)))
    anims = unique_sorted(aggregate.get("animations", []), max_items=max(1, int(args.max_anims)))
    weapons = unique_sorted(aggregate.get("weapons", []), max_items=max(1, int(args.max_weapons)))
    functions = unique_sorted(aggregate.get("functions", []), max_items=500)

    project_name = sanitize_name(args.project_name)
    script = build_script(project_name=project_name, models=models, anims=anims, weapons=weapons, functions=functions)

    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = (repo_root / output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(script, encoding="utf-8")

    report = {
        "generated_at_utc": dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "profile": str(profile_path),
        "output": str(output_path),
        "project_name": project_name,
        "counts": {
            "models": len(models),
            "anims": len(anims),
            "weapons": len(weapons),
            "functions": len(functions),
        },
    }
    report_path = Path(args.report)
    if not report_path.is_absolute():
        report_path = (repo_root / report_path).resolve()
    save_json(report_path, report)

    print(f"Saved BO2 script stub: {output_path}")
    print(f"Saved script stub report: {report_path}")
    print(
        f"models={report['counts']['models']} "
        f"anims={report['counts']['anims']} "
        f"weapons={report['counts']['weapons']}"
    )


if __name__ == "__main__":
    main()
