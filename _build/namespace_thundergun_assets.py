#!/usr/bin/env python3
"""Namespace thundergun image/material asset names to avoid vanilla collisions.

Creates namespaced copies:
  tg_*                                -> rogue_tg_*
  mtl_wpn_t7_zmb_hd_thundergun_*      -> mtl_rogue_tg_*

Also patches thundergun GLBs and zone source entries to the namespaced assets.
"""

import glob
import json
import os
import shutil
import struct
from typing import Dict

ROOT = r"z:\Games\pluto_t6_full_game\_build\panzer_work\so_zsurvival_zm_transit"
IMAGES_DIR = os.path.join(ROOT, "images")
MATERIALS_DIR = os.path.join(ROOT, "materials")
MODELS_DIR = os.path.join(ROOT, "model_export")
ZONE_FILE = os.path.join(ROOT, "zone_source", "so_zsurvival_zm_transit.zone")

OLD_MAT_PREFIX = "mtl_wpn_t7_zmb_hd_thundergun_"
NEW_MAT_PREFIX = "mtl_rogue_tg_"
OLD_IMG_PREFIX = "tg_"
NEW_IMG_PREFIX = "rogue_tg_"


def build_image_map() -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    for p in sorted(glob.glob(os.path.join(IMAGES_DIR, "tg_*.iwi"))):
        name = os.path.splitext(os.path.basename(p))[0]
        mapping[name] = name.replace(OLD_IMG_PREFIX, NEW_IMG_PREFIX, 1)
    return mapping


def build_material_map() -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    for p in sorted(glob.glob(os.path.join(MATERIALS_DIR, f"{OLD_MAT_PREFIX}*.json"))):
        name = os.path.splitext(os.path.basename(p))[0]
        suffix = name[len(OLD_MAT_PREFIX) :]
        mapping[name] = f"{NEW_MAT_PREFIX}{suffix}"
    return mapping


def copy_images(image_map: Dict[str, str]) -> int:
    count = 0
    for old_name, new_name in image_map.items():
        src = os.path.join(IMAGES_DIR, f"{old_name}.iwi")
        dst = os.path.join(IMAGES_DIR, f"{new_name}.iwi")
        shutil.copy2(src, dst)
        count += 1
    return count


def copy_and_patch_materials(image_map: Dict[str, str], material_map: Dict[str, str]) -> int:
    count = 0
    for old_name, new_name in material_map.items():
        src = os.path.join(MATERIALS_DIR, f"{old_name}.json")
        dst = os.path.join(MATERIALS_DIR, f"{new_name}.json")
        with open(src, "r", encoding="utf-8") as f:
            mat = json.load(f)

        for tex in mat.get("textures", []):
            img = tex.get("image")
            if img in image_map:
                tex["image"] = image_map[img]

        if "debugName" in mat:
            mat["debugName"] = new_name

        with open(dst, "w", encoding="utf-8", newline="\n") as f:
            json.dump(mat, f, indent=4)
            f.write("\n")
        count += 1
    return count


def patch_glb_material_names(glb_path: str, material_map: Dict[str, str]) -> int:
    with open(glb_path, "rb") as f:
        data = f.read()

    if data[:4] != b"glTF":
        raise RuntimeError(f"Not a GLB file: {glb_path}")

    version = struct.unpack_from("<I", data, 4)[0]
    if version != 2:
        raise RuntimeError(f"Unsupported GLB version {version} in {glb_path}")

    json_len = struct.unpack_from("<I", data, 12)[0]
    json_type = data[16:20]
    if json_type != b"JSON":
        raise RuntimeError(f"First GLB chunk is not JSON in {glb_path}")

    json_start = 20
    json_end = json_start + json_len
    json_text = data[json_start:json_end].decode("utf-8").rstrip("\x00 \t\r\n")
    gltf = json.loads(json_text)

    changed = 0
    for mat in gltf.get("materials", []):
        name = mat.get("name")
        if name in material_map:
            mat["name"] = material_map[name]
            changed += 1

    if changed == 0:
        return 0

    out_json = json.dumps(gltf, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    pad = (4 - (len(out_json) % 4)) % 4
    out_json_padded = out_json + (b" " * pad)

    remainder = data[json_end:]
    out = bytearray()
    out.extend(b"glTF")
    out.extend(struct.pack("<I", 2))
    out.extend(struct.pack("<I", 12 + 8 + len(out_json_padded) + len(remainder)))
    out.extend(struct.pack("<I", len(out_json_padded)))
    out.extend(b"JSON")
    out.extend(out_json_padded)
    out.extend(remainder)

    bak = glb_path + ".bak_before_namespace"
    if not os.path.exists(bak):
        shutil.copy2(glb_path, bak)

    with open(glb_path, "wb") as f:
        f.write(out)

    return changed


def patch_zone(zone_file: str, image_map: Dict[str, str], material_map: Dict[str, str]) -> int:
    with open(zone_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    changed = 0
    out_lines = []
    for line in lines:
        stripped = line.strip()
        replaced = line

        if stripped.startswith("image,"):
            parts = stripped.split(",")
            if len(parts) >= 2 and parts[1] in image_map:
                replaced = f"image,{image_map[parts[1]]}\n"
                changed += 1
        elif stripped.startswith("material,"):
            parts = stripped.split(",")
            if len(parts) >= 2 and parts[1] in material_map:
                replaced = f"material,{material_map[parts[1]]}\n"
                changed += 1

        out_lines.append(replaced)

    if changed:
        bak = zone_file + ".bak_before_namespace"
        if not os.path.exists(bak):
            shutil.copy2(zone_file, bak)
        with open(zone_file, "w", encoding="utf-8", newline="\n") as f:
            f.writelines(out_lines)

    return changed


def main() -> None:
    image_map = build_image_map()
    material_map = build_material_map()

    print(f"Images to namespace: {len(image_map)}")
    print(f"Materials to namespace: {len(material_map)}")

    copied_images = copy_images(image_map)
    copied_materials = copy_and_patch_materials(image_map, material_map)
    print(f"Copied images: {copied_images}")
    print(f"Copied+patched materials: {copied_materials}")

    glb_files = [
        os.path.join(MODELS_DIR, "thundergun_view_lod0.glb"),
        os.path.join(MODELS_DIR, "thundergun_world_lod0.glb"),
    ]
    for glb in glb_files:
        changed = patch_glb_material_names(glb, material_map)
        print(f"Patched {os.path.basename(glb)} material names: {changed}")

    zone_changed = patch_zone(ZONE_FILE, image_map, material_map)
    print(f"Zone entries changed: {zone_changed}")

    print("Done.")


if __name__ == "__main__":
    main()
