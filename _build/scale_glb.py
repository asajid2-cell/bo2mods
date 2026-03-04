#!/usr/bin/env python3
"""Scale all vertex positions in a GLB file by a given factor."""
import struct
import sys
import shutil
from pathlib import Path

import pygltflib


def scale_glb(input_path: str, output_path: str, scale: float):
    """Scale all vertex POSITION data in a GLB file."""
    gltf = pygltflib.GLTF2().load(input_path)
    blob = bytearray(gltf.binary_blob())

    scaled_accessors = set()

    for mesh in gltf.meshes:
        for prim in mesh.primitives:
            if prim.attributes.POSITION is None:
                continue

            acc_idx = prim.attributes.POSITION
            if acc_idx in scaled_accessors:
                continue
            scaled_accessors.add(acc_idx)

            acc = gltf.accessors[acc_idx]
            bv = gltf.bufferViews[acc.bufferView]

            # Calculate byte offset
            byte_offset = (bv.byteOffset or 0) + (acc.byteOffset or 0)
            byte_stride = bv.byteStride or 12  # 3 floats * 4 bytes

            count = acc.count
            print(f"  Scaling accessor {acc_idx}: {count} vertices, stride={byte_stride}")

            for i in range(count):
                offset = byte_offset + i * byte_stride
                x, y, z = struct.unpack_from('<fff', blob, offset)
                x *= scale
                y *= scale
                z *= scale
                struct.pack_into('<fff', blob, offset, x, y, z)

            # Update accessor min/max
            if acc.min:
                acc.min = [v * scale for v in acc.min]
            if acc.max:
                acc.max = [v * scale for v in acc.max]

    # Update the binary blob
    gltf.set_binary_blob(bytes(blob))
    gltf.save(output_path)

    # Verify
    verify = pygltflib.GLTF2().load(output_path)
    for mesh in verify.meshes:
        for prim in mesh.primitives:
            if prim.attributes.POSITION is not None:
                acc = verify.accessors[prim.attributes.POSITION]
                if acc.min and acc.max:
                    size = [acc.max[i] - acc.min[i] for i in range(3)]
                    print(f"  Verified size: ({size[0]:.1f}, {size[1]:.1f}, {size[2]:.1f})")
                    break


def main():
    scale = 1.6
    base = Path(r"z:\Games\pluto_t6_full_game\_build\panzer_work\so_zsurvival_zm_transit\model_export")

    view_glb = base / "thundergun_view_lod0.glb"
    world_glb = base / "thundergun_world_lod0.glb"

    # Backup originals if not already backed up
    view_bak = base / "thundergun_view_lod0.glb.prescale_bak"
    world_bak = base / "thundergun_world_lod0.glb.prescale_bak"

    if not view_bak.exists():
        shutil.copy2(view_glb, view_bak)
        print(f"Backed up view model to {view_bak.name}")
    if not world_bak.exists():
        shutil.copy2(world_glb, world_bak)
        print(f"Backed up world model to {world_bak.name}")

    print(f"\nScaling view model by {scale}x...")
    scale_glb(str(view_glb), str(view_glb), scale)

    print(f"\nScaling world model by {scale}x...")
    scale_glb(str(world_glb), str(world_glb), scale)

    print(f"\nDone! Both models scaled by {scale}x")


if __name__ == "__main__":
    main()
