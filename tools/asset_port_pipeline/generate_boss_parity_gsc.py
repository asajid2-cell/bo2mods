from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any, Dict, List

SCRIPT_DIR = Path(__file__).resolve().parent

import sys

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common import save_json  # noqa: E402
from linker_oracle import sanitize_name  # noqa: E402


def as_int(value: Any, default: int) -> int:
    try:
        return int(float(value))
    except Exception:
        return int(default)


def as_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def build_script(profile: Dict[str, Any]) -> str:
    boss_name = sanitize_name(str(profile.get("boss_name", "custom_boss")))
    model = str(profile.get("model", "zombie_base_model"))
    health = as_int(profile.get("health", 5000), 5000)
    speed = as_float(profile.get("speed_scale", 1.0), 1.0)
    melee_damage = as_int(profile.get("melee_damage", 50), 50)
    melee_range = as_int(profile.get("melee_range", 80), 80)
    think_interval = as_float(profile.get("think_interval", 0.05), 0.05)
    spawn_fx = str(profile.get("spawn_fx", ""))
    death_fx = str(profile.get("death_fx", ""))

    ability_blocks: List[str] = []
    abilities = profile.get("abilities", [])
    if isinstance(abilities, list):
        for idx, raw_ability in enumerate(abilities, start=1):
            if not isinstance(raw_ability, dict):
                continue
            ability_name = sanitize_name(str(raw_ability.get("name", f"ability_{idx}")))
            cooldown = as_float(raw_ability.get("cooldown", 10.0), 10.0)
            radius = as_int(raw_ability.get("radius", 160), 160)
            damage = as_int(raw_ability.get("damage", 40), 40)
            delay = as_float(raw_ability.get("startup_delay", 0.1), 0.1)
            fx_name = str(raw_ability.get("fx", ""))
            fx_line = f'        playfx(level._effect["{fx_name}"], boss.origin);' if fx_name else ""
            ability_blocks.append(
                f"""
{boss_name}_ability_{ability_name}(boss)
{{
    boss endon("death");
    level endon("game_ended");
    for(;;)
    {{
        wait {cooldown:.3f};
        if (!isDefined(boss) || !isAlive(boss))
        {{
            return;
        }}
        wait {delay:.3f};
        if (!isDefined(boss) || !isAlive(boss))
        {{
            return;
        }}
{fx_line}
        RadiusDamage(boss.origin, {radius}, {damage}, {int(max(1, damage // 3))}, boss);
    }}
}}
""".strip()
            )

    ability_thread_lines = "\n".join(
        f'    boss thread {boss_name}_ability_{sanitize_name(str(item.get("name", "ability")))}(boss);'
        for item in abilities
        if isinstance(item, dict)
    )

    if spawn_fx:
        spawn_fx_line = f'    playfx(level._effect["{spawn_fx}"], boss.origin);'
    else:
        spawn_fx_line = ""
    if death_fx:
        death_fx_line = f'    playfx(level._effect["{death_fx}"], self.origin);'
    else:
        death_fx_line = ""

    blocks = "\n\n".join(ability_blocks)
    if blocks:
        blocks = "\n\n" + blocks

    script = f"""init_{boss_name}()
{{
    level._{boss_name}_settings = SpawnStruct();
    level._{boss_name}_settings.model = "{model}";
    level._{boss_name}_settings.health = {health};
    level._{boss_name}_settings.speed_scale = {speed:.3f};
    level._{boss_name}_settings.melee_damage = {melee_damage};
    level._{boss_name}_settings.melee_range = {melee_range};
}}

spawn_{boss_name}(origin, angles)
{{
    if (!isDefined(level._{boss_name}_settings))
    {{
        init_{boss_name}();
    }}
    boss = spawn("script_model", origin);
    boss.angles = angles;
    boss setModel(level._{boss_name}_settings.model);
    boss.health = level._{boss_name}_settings.health;
    boss.maxhealth = level._{boss_name}_settings.health;
    boss.speed_scale = level._{boss_name}_settings.speed_scale;
    boss.melee_damage = level._{boss_name}_settings.melee_damage;
    boss.melee_range = level._{boss_name}_settings.melee_range;
{spawn_fx_line}
    boss thread {boss_name}_brain();
{ability_thread_lines}
    boss thread {boss_name}_death_fx();
    return boss;
}}

{boss_name}_death_fx()
{{
    self endon("disconnect");
    self waittill("death");
{death_fx_line}
}}

{boss_name}_brain()
{{
    self endon("disconnect");
    self endon("death");
    level endon("game_ended");
    for(;;)
    {{
        wait {think_interval:.3f};
        target = get_closest_player(self.origin);
        if (!isDefined(target))
        {{
            continue;
        }}
        dist = Distance(self.origin, target.origin);
        if (dist <= self.melee_range)
        {{
            if (isAlive(target))
            {{
                target DoDamage(self, self.origin, self.melee_damage, 0, "MOD_MELEE");
            }}
        }}
        else
        {{
            step = 14 * self.speed_scale;
            dir = VectorNormalize(target.origin - self.origin);
            self.origin = self.origin + (dir * step);
        }}
    }}
}}

get_closest_player(origin)
{{
    players = GetPlayers();
    if (!isDefined(players) || players.size <= 0)
    {{
        return undefined;
    }}
    best = undefined;
    best_dist = 9999999;
    for(i = 0; i < players.size; i++)
    {{
        p = players[i];
        if (!isDefined(p) || !isAlive(p))
        {{
            continue;
        }}
        d = Distance(origin, p.origin);
        if (d < best_dist)
        {{
            best_dist = d;
            best = p;
        }}
    }}
    return best;
}}{blocks}
"""
    return script.strip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate BO2 GSC boss behavior script from JSON profile.")
    parser.add_argument("--profile", required=True, help="Input JSON profile.")
    parser.add_argument("--output", required=True, help="Output .gsc file path.")
    parser.add_argument(
        "--report",
        default="_build/asset_port_pipeline/boss_parity_report.json",
        help="Output report JSON path.",
    )
    args = parser.parse_args()

    repo_root = Path.cwd().resolve()
    profile_path = Path(args.profile)
    if not profile_path.is_absolute():
        profile_path = (repo_root / profile_path).resolve()
    if not profile_path.exists():
        raise FileNotFoundError(f"Profile not found: {profile_path}")

    profile = json.loads(profile_path.read_text(encoding="utf-8-sig"))
    script = build_script(profile)

    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = (repo_root / output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(script, encoding="utf-8")

    report = {
        "generated_at_utc": dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "profile": str(profile_path),
        "output": str(output_path),
        "boss_name": sanitize_name(str(profile.get("boss_name", "custom_boss"))),
        "abilities": [item.get("name", "") for item in profile.get("abilities", []) if isinstance(item, dict)],
    }

    report_path = Path(args.report)
    if not report_path.is_absolute():
        report_path = (repo_root / report_path).resolve()
    save_json(report_path, report)

    print(f"Saved boss GSC: {output_path}")
    print(f"Saved boss parity report: {report_path}")


if __name__ == "__main__":
    main()
