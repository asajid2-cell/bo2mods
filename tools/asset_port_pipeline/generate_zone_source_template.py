from __future__ import annotations

import argparse
from pathlib import Path

SCRIPT_TEMPLATE = """// Auto-generated BO2 patch zone template
>game,T6

>level.ipak_read,base
>level.ipak_read,lowmip
>level.ipak_read,common_zm
{ipak_reads}
>level.ipak_write,{project_name}

// ---- Core map ----
// mapents,{project_name}
// stringtable,mp/configstrings/configstrings_{source_map}.csv

// ---- Render assets ----
// techniqueset,<techset_name>
// image,<image_name>
// material,mc/<material_name>
// xmodel,<xmodel_name>

// ---- Gameplay assets ----
// weapon,<weapon_name>
// aitype,<aitype_name>
// animtree,<animtree_name>
// animstatedef,<animstatedef_name>
// xanim,<xanim_name>
// xmodelalias,<xmodelalias_name>

// ---- Scripts/raw ----
// rawfile,maps/mp/{project_name}.gsc
// script,maps/mp/{project_name}.gsc
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a BO2 patch zone_source template.")
    parser.add_argument("--project-name", required=True, help="Target BO2 patch project name.")
    parser.add_argument("--source-map", default="zm_tomb", help="Source map name for template hints.")
    parser.add_argument(
        "--ipak-reads",
        nargs="*",
        default=[],
        help="Extra level.ipak_read entries (e.g. zm_tomb zm_transit).",
    )
    parser.add_argument("--output", required=True, help="Output .zone path.")
    args = parser.parse_args()

    project_name = args.project_name.strip().lower()
    source_map = args.source_map.strip().lower()
    extra_ipaks = sorted({item.strip().lower() for item in args.ipak_reads if item.strip()})
    ipak_lines = "\n".join([f">level.ipak_read,{item}" for item in extra_ipaks])
    if ipak_lines:
        ipak_lines += "\n"

    text = SCRIPT_TEMPLATE.format(
        ipak_reads=ipak_lines,
        project_name=project_name,
        source_map=source_map,
    )

    output = Path(args.output)
    if not output.is_absolute():
        output = (Path.cwd().resolve() / output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8")
    print(f"Saved zone template: {output}")


if __name__ == "__main__":
    main()
