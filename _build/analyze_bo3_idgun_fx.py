#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, field
from pathlib import Path


ATTACHMENT_RE = re.compile(r'^\s*attachment\s+"([^"]*)";')
FX_ON_IMPACT_RE = re.compile(r'^\s*fxOnImpact\s+"([^"]*)";')
FX_ON_DEATH_RE = re.compile(r'^\s*fxOnDeath\s+"([^"]*)";')
EMISSION_RE = re.compile(r'^\s*emission\s+"([^"]*)";')
BLOCK_START_RE = re.compile(
    r"^\s*(billboardSprite|orientedSprite|rotatedSprite|line|tail|trail|cloud|model|decal|runner|dynamicLight2)\s*$"
)
QUOTED_VALUE_RE = re.compile(r'^\s*"([^"]+)"\s*$')

SUPPORTED_T6_VISUAL_TYPES = {
    "billboardSprite",
    "orientedSprite",
    "rotatedSprite",
    "line",
    "tail",
    "cloud",
    "decal",
}
EXPERIMENTAL_T6_VISUAL_TYPES = {"trail"}
UNSUPPORTED_T6_VISUAL_TYPES = {"model", "runner"}
IGNORED_T6_FEATURES = {"dynamicLight2"}


@dataclass
class FxNode:
    name: str
    file: str
    attachments: list[str] = field(default_factory=list)
    fx_on_impact: list[str] = field(default_factory=list)
    fx_on_death: list[str] = field(default_factory=list)
    emissions: list[str] = field(default_factory=list)
    billboard_sprites: list[str] = field(default_factory=list)
    line_materials: list[str] = field(default_factory=list)
    tail_materials: list[str] = field(default_factory=list)
    trail_materials: list[str] = field(default_factory=list)
    cloud_materials: list[str] = field(default_factory=list)
    decal_materials: list[str] = field(default_factory=list)
    models: list[str] = field(default_factory=list)
    unsupported_visual_types: list[str] = field(default_factory=list)
    ignored_features: list[str] = field(default_factory=list)
    visual_types: list[str] = field(default_factory=list)


def parse_efx(path: Path) -> FxNode:
    node = FxNode(name=path.stem, file=str(path))
    capture_block: str | None = None

    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if match := ATTACHMENT_RE.match(line):
            value = match.group(1)
            if value:
                node.attachments.append(value)
            continue
        if match := FX_ON_IMPACT_RE.match(line):
            value = match.group(1)
            if value:
                node.fx_on_impact.append(value)
            continue
        if match := FX_ON_DEATH_RE.match(line):
            value = match.group(1)
            if value:
                node.fx_on_death.append(value)
            continue
        if match := EMISSION_RE.match(line):
            value = match.group(1)
            if value:
                node.emissions.append(value)
            continue
        if match := BLOCK_START_RE.match(line):
            capture_block = match.group(1)
            if capture_block not in node.visual_types:
                node.visual_types.append(capture_block)
            if capture_block in UNSUPPORTED_T6_VISUAL_TYPES and capture_block not in node.unsupported_visual_types:
                node.unsupported_visual_types.append(capture_block)
            if capture_block in IGNORED_T6_FEATURES and capture_block not in node.ignored_features:
                node.ignored_features.append(capture_block)
            continue
        if capture_block and (match := QUOTED_VALUE_RE.match(line)):
            value = match.group(1)
            if capture_block in {"billboardSprite", "orientedSprite", "rotatedSprite"}:
                node.billboard_sprites.append(value)
            elif capture_block == "line":
                node.line_materials.append(value)
            elif capture_block == "tail":
                node.tail_materials.append(value)
            elif capture_block == "trail":
                node.trail_materials.append(value)
            elif capture_block == "cloud":
                node.cloud_materials.append(value)
            elif capture_block == "decal":
                node.decal_materials.append(value)
            elif capture_block == "model":
                node.models.append(value)
            continue
        if line.strip() == "}":
            capture_block = None

    node.attachments = sorted(set(node.attachments))
    node.fx_on_impact = sorted(set(node.fx_on_impact))
    node.fx_on_death = sorted(set(node.fx_on_death))
    node.emissions = sorted(set(node.emissions))
    node.billboard_sprites = sorted(set(node.billboard_sprites))
    node.line_materials = sorted(set(node.line_materials))
    node.tail_materials = sorted(set(node.tail_materials))
    node.trail_materials = sorted(set(node.trail_materials))
    node.cloud_materials = sorted(set(node.cloud_materials))
    node.decal_materials = sorted(set(node.decal_materials))
    node.models = sorted(set(node.models))
    node.unsupported_visual_types = sorted(set(node.unsupported_visual_types))
    node.ignored_features = sorted(set(node.ignored_features))
    node.visual_types = sorted(set(node.visual_types))
    return node


def resolve_fx_path(raw_fx_root: Path, fx_name: str) -> Path:
    return raw_fx_root / (fx_name.replace("/", "\\") + ".efx")


def walk_graph(raw_fx_root: Path, root_fx_names: list[str]) -> tuple[dict[str, FxNode], set[str]]:
    nodes: dict[str, FxNode] = {}
    missing: set[str] = set()
    queue = list(root_fx_names)

    while queue:
        fx_name = queue.pop(0)
        if fx_name in nodes:
            continue

        fx_path = resolve_fx_path(raw_fx_root, fx_name)
        if not fx_path.exists():
            missing.add(fx_name)
            continue

        node = parse_efx(fx_path)
        nodes[fx_name] = node

        for child in node.attachments + node.fx_on_impact + node.fx_on_death + node.emissions:
            if child and child not in nodes and child not in queue:
                queue.append(child)

    return nodes, missing


def build_report(raw_fx_root: Path) -> dict:
    roots = [
        "zombie/fx_idgun_muz_1p_zmb",
        "zombie/fx_idgun_muz_3p_zmb",
        "zombie/fx_idgun_projectile_zod_zmb",
        "zombie/fx_idgun_vortex_explo_zod_zmb",
        "zombie/fx_idgun_vortex_zod_zmb",
    ]
    nodes, missing = walk_graph(raw_fx_root, roots)

    all_visual_materials = sorted(
        {
            material
            for node in nodes.values()
            for material in (
                node.billboard_sprites
                + node.line_materials
                + node.tail_materials
                + node.trail_materials
                + node.cloud_materials
                + node.decal_materials
            )
            if material
        }
    )
    all_billboard_sprites = sorted(
        {sprite for node in nodes.values() for sprite in node.billboard_sprites if sprite}
    )
    all_models = sorted({model for node in nodes.values() for model in node.models if model})
    all_visual_types = sorted({visual for node in nodes.values() for visual in node.visual_types if visual})
    all_unsupported_visual_types = sorted(
        {visual for node in nodes.values() for visual in node.unsupported_visual_types if visual}
    )
    all_ignored_features = sorted(
        {feature for node in nodes.values() for feature in node.ignored_features if feature}
    )

    fatal_effects = []
    warning_effects = []
    for name, node in sorted(nodes.items()):
        fatal_reasons: list[str] = []
        warning_reasons: list[str] = []
        if node.unsupported_visual_types:
            fatal_reasons.append(f"unsupported visuals: {', '.join(node.unsupported_visual_types)}")
        if node.trail_materials:
            fatal_reasons.append("trail visuals require FxTrailDef support, which the current T6 raw loader does not serialize")
        if node.ignored_features:
            warning_reasons.append(f"ignored features: {', '.join(node.ignored_features)}")
        if fatal_reasons:
            fatal_effects.append({"effect": name, "reasons": fatal_reasons})
        elif warning_reasons:
            warning_effects.append({"effect": name, "reasons": warning_reasons})

    return {
        "raw_fx_root": str(raw_fx_root),
        "root_effects": roots,
        "resolved_effect_count": len(nodes),
        "missing_effects": sorted(missing),
        "all_visual_materials": all_visual_materials,
        "all_billboard_sprites": all_billboard_sprites,
        "all_models": all_models,
        "all_visual_types": all_visual_types,
        "all_unsupported_visual_types": all_unsupported_visual_types,
        "all_ignored_features": all_ignored_features,
        "t6_compatibility": {
            "supported_visual_types": sorted(SUPPORTED_T6_VISUAL_TYPES),
            "experimental_visual_types": sorted(EXPERIMENTAL_T6_VISUAL_TYPES),
            "unsupported_visual_types": sorted(UNSUPPORTED_T6_VISUAL_TYPES),
            "ignored_features": sorted(IGNORED_T6_FEATURES),
            "fatal_effects": fatal_effects,
            "warning_effects": warning_effects,
        },
        "effects": {
            name: {
                "file": node.file,
                "attachments": node.attachments,
                "fx_on_impact": node.fx_on_impact,
                "fx_on_death": node.fx_on_death,
                "emissions": node.emissions,
                "billboard_sprites": node.billboard_sprites,
                "line_materials": node.line_materials,
                "tail_materials": node.tail_materials,
                "trail_materials": node.trail_materials,
                "cloud_materials": node.cloud_materials,
                "decal_materials": node.decal_materials,
                "models": node.models,
                "unsupported_visual_types": node.unsupported_visual_types,
                "ignored_features": node.ignored_features,
                "visual_types": node.visual_types,
            }
            for name, node in sorted(nodes.items())
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--raw-fx-root",
        type=Path,
        default=Path(
            r"C:\Users\Ahmed\Downloads\hb21_elemental_bows_v1.0.0\hb21_black_ops_3_fx_library_v2.1.0\share\raw\fx"
        ),
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(r"z:\Games\pluto_t6_full_game\_build\bo3_idgun_fx_graph.json"),
    )
    args = parser.parse_args()

    report = build_report(args.raw_fx_root)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote {args.out}")
    print(
        f"Resolved {report['resolved_effect_count']} effects, "
        f"{len(report['all_visual_materials'])} visual materials, "
        f"{len(report['missing_effects'])} missing effect refs, "
        f"{len(report['t6_compatibility']['fatal_effects'])} fatal T6 compatibility blockers"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
