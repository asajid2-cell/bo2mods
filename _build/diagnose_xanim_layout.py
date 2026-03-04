#!/usr/bin/env python3
"""
Diagnostic script to examine XAnimParts binary layout in T6 zones.
Compares empty OAT stubs vs vanilla entries vs our patched entries.
"""
import struct
import sys
import os

# Reuse decryption from patcher
sys.path.insert(0, os.path.dirname(__file__))
from patch_zone_xanims import decrypt_zone, parse_string_table, find_empty_xanim_stubs

ZONE_NAME = "so_zsurvival_zm_transit"


def hex_dump(data, offset=0, width=16):
    """Pretty hex dump with ASCII."""
    lines = []
    for i in range(0, len(data), width):
        chunk = data[i:i + width]
        hexpart = ' '.join(f'{b:02X}' for b in chunk)
        ascpart = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        lines.append(f"  {offset + i:08X}: {hexpart:<{width*3}}  {ascpart}")
    return '\n'.join(lines)


def find_real_xanim(data, min_offset, exclude_prefix="vm_thunder_gun_"):
    """Find a REAL (non-empty) XAnimParts by looking for PTR_FOLLOWING headers
    where the rest of the header has non-zero data (indicating real anim data)."""
    pos = min_offset
    results = []
    while pos < len(data) - 104:
        # Look for PTR_FOLLOWING at start
        if struct.unpack_from('<I', data, pos)[0] != 0xFFFFFFFF:
            pos += 1
            continue

        # Check if it could be an XAnimParts header by verifying some fields
        # The name pointer is PTR_FOLLOWING, and there's a names pointer at 0x40
        names_ptr = struct.unpack_from('<I', data, pos + 0x40)[0]
        notify_ptr = struct.unpack_from('<I', data, pos + 0x60)[0]
        delta_ptr = struct.unpack_from('<I', data, pos + 0x64)[0]

        # Check boneCount[9] (totalBoneCount) at offset 0x18+9 = 0x21
        total_bones = data[pos + 0x21]
        numframes = struct.unpack_from('<H', data, pos + 0x0E)[0]

        # Only interested in entries with real data (non-zero bones AND non-zero frames)
        if total_bones > 0 and numframes > 0 and names_ptr == 0xFFFFFFFF:
            # Try to read the name after the header
            name_start = pos + 104
            # Skip any gap bytes
            for g in range(8):
                if name_start + g < len(data) and data[name_start + g] > 0x20:
                    break

            # Check if this looks like a valid name string
            try:
                null_pos = data.index(b'\x00', name_start + g, name_start + g + 200)
                name = data[name_start + g:null_pos].decode('ascii')
                if name and not name.startswith(exclude_prefix) and len(name) > 3:
                    # Check for reasonable values
                    framerate = struct.unpack_from('<f', data, pos + 0x30)[0]
                    if 0.5 < framerate < 120:
                        results.append({
                            'name': name,
                            'offset': pos,
                            'bones': total_bones,
                            'numframes': numframes,
                            'gap': g,
                            'framerate': framerate,
                        })
                        if len(results) >= 5:
                            return results
            except (ValueError, UnicodeDecodeError):
                pass

        pos += 1

    return results


def analyze_xanim_header(data, offset, label=""):
    """Parse and display an XAnimParts header at the given offset."""
    h = data[offset:offset + 104]
    if len(h) < 104:
        print(f"  [Insufficient data at 0x{offset:X}]")
        return

    name_ptr = struct.unpack_from('<I', h, 0x00)[0]
    dataByteCount = struct.unpack_from('<H', h, 0x04)[0]
    dataShortCount = struct.unpack_from('<H', h, 0x06)[0]
    dataIntCount = struct.unpack_from('<H', h, 0x08)[0]
    randomDataByteCount = struct.unpack_from('<H', h, 0x0A)[0]
    randomDataIntCount = struct.unpack_from('<H', h, 0x0C)[0]
    numframes = struct.unpack_from('<H', h, 0x0E)[0]

    bLoop = h[0x10]
    bDelta = h[0x11]
    bDelta3D = h[0x12]
    bLeftHandGripIK = h[0x13]
    streamedFileSize = struct.unpack_from('<I', h, 0x14)[0]

    boneCount = [h[0x18 + i] for i in range(10)]
    notifyCount = h[0x22]
    assetType = h[0x23]  # signed char
    if assetType > 127:
        assetType -= 256
    isDefault = h[0x24]

    randomDataShortCount = struct.unpack_from('<I', h, 0x28)[0]
    indexCount = struct.unpack_from('<I', h, 0x2C)[0]
    framerate = struct.unpack_from('<f', h, 0x30)[0]
    frequency = struct.unpack_from('<f', h, 0x34)[0]
    primedLength = struct.unpack_from('<f', h, 0x38)[0]
    loopEntryTime = struct.unpack_from('<f', h, 0x3C)[0]

    names_ptr = struct.unpack_from('<I', h, 0x40)[0]
    dataByte_ptr = struct.unpack_from('<I', h, 0x44)[0]
    dataShort_ptr = struct.unpack_from('<I', h, 0x48)[0]
    dataInt_ptr = struct.unpack_from('<I', h, 0x4C)[0]
    randomDataShort_ptr = struct.unpack_from('<I', h, 0x50)[0]
    randomDataByte_ptr = struct.unpack_from('<I', h, 0x54)[0]
    randomDataInt_ptr = struct.unpack_from('<I', h, 0x58)[0]
    indices_ptr = struct.unpack_from('<I', h, 0x5C)[0]
    notify_ptr = struct.unpack_from('<I', h, 0x60)[0]
    deltaPart_ptr = struct.unpack_from('<I', h, 0x64)[0]

    ptr_name = lambda v: "FOLLOWING" if v == 0xFFFFFFFF else ("NULL" if v == 0 else f"0x{v:08X}")

    print(f"\n{'='*60}")
    print(f"XAnimParts @ 0x{offset:X} {label}")
    print(f"{'='*60}")
    print(f"  name ptr:           {ptr_name(name_ptr)}")
    print(f"  dataByteCount:      {dataByteCount}")
    print(f"  dataShortCount:     {dataShortCount}")
    print(f"  dataIntCount:       {dataIntCount}")
    print(f"  randomDataByteCount:{randomDataByteCount}")
    print(f"  randomDataIntCount: {randomDataIntCount}")
    print(f"  numframes:          {numframes}")
    print(f"  bLoop/bDelta/b3D/bLHGIK: {bLoop}/{bDelta}/{bDelta3D}/{bLeftHandGripIK}")
    print(f"  streamedFileSize:   {streamedFileSize}")
    print(f"  boneCount[10]:      {boneCount}")
    print(f"    sum rot:  {sum(boneCount[0:5])}")
    print(f"    sum trans:{sum(boneCount[5:9])}")
    print(f"    total:    {boneCount[9]}")
    print(f"  notifyCount:        {notifyCount}")
    print(f"  assetType:          {assetType}")
    print(f"  isDefault:          {isDefault}")
    print(f"  randomDataShortCount:{randomDataShortCount}")
    print(f"  indexCount:         {indexCount}")
    print(f"  framerate:          {framerate}")
    print(f"  frequency:          {frequency}")
    print(f"  primedLength:       {primedLength}")
    print(f"  loopEntryTime:      {loopEntryTime}")
    print(f"  Pointers:")
    print(f"    names:            {ptr_name(names_ptr)}")
    print(f"    dataByte:         {ptr_name(dataByte_ptr)}")
    print(f"    dataShort:        {ptr_name(dataShort_ptr)}")
    print(f"    dataInt:          {ptr_name(dataInt_ptr)}")
    print(f"    randomDataShort:  {ptr_name(randomDataShort_ptr)}")
    print(f"    randomDataByte:   {ptr_name(randomDataByte_ptr)}")
    print(f"    randomDataInt:    {ptr_name(randomDataInt_ptr)}")
    print(f"    indices:          {ptr_name(indices_ptr)}")
    print(f"    notify:           {ptr_name(notify_ptr)}")
    print(f"    deltaPart:        {ptr_name(deltaPart_ptr)}")

    # Show bytes around the header boundary
    print(f"\n  Bytes before header (offset-16..offset):")
    if offset >= 16:
        print(hex_dump(data[offset-16:offset], offset-16))
    print(f"  Last 8 header bytes + first 32 bytes after header:")
    print(hex_dump(data[offset+96:offset+136], offset+96))

    return {
        'dataByteCount': dataByteCount,
        'dataShortCount': dataShortCount,
        'dataIntCount': dataIntCount,
        'numframes': numframes,
        'boneCount': boneCount,
        'assetType': assetType,
        'isDefault': isDefault,
        'names_ptr': names_ptr,
        'dataByte_ptr': dataByte_ptr,
        'dataShort_ptr': dataShort_ptr,
        'dataInt_ptr': dataInt_ptr,
    }


def trace_data_sections(data, offset, info):
    """Trace the pointer-followed data sections after an XAnimParts header."""
    pos = offset + 104  # After header
    total_bones = info['boneCount'][9]

    print(f"\n  Data trace from 0x{pos:X}:")

    # 1) Name (PTR_FOLLOWING for name)
    # Find null terminator
    null_pos = data.index(b'\x00', pos, pos + 300)
    name_bytes = data[pos:null_pos + 1]
    name_str = name_bytes[:-1].decode('ascii', errors='replace')
    print(f"    name @ 0x{pos:X}: \"{name_str}\" ({len(name_bytes)} bytes)")
    pos = null_pos + 1

    # 2) Names (PTR_FOLLOWING for names if non-null)
    if info['names_ptr'] == 0xFFFFFFFF and total_bones > 0:
        # Check for alignment padding
        expected_names_bytes = total_bones * 2
        print(f"    names @ 0x{pos:X}: {total_bones} entries, {expected_names_bytes} bytes")
        # Show first few uint16 values
        indices = []
        for i in range(min(total_bones, 8)):
            idx = struct.unpack_from('<H', data, pos + i * 2)[0]
            indices.append(idx)
        print(f"      first indices: {indices}")
        # Show bytes around the boundary
        print(f"      bytes at start:")
        print(hex_dump(data[pos:pos + min(32, expected_names_bytes)], pos))
        pos += expected_names_bytes

    # 3) Notify (before dataByte in reorder)
    # notify comes before dataByte/dataShort/dataInt in the reorder
    # but after names. It's at ptr offset 0x60
    notify_ptr = struct.unpack_from('<I', data, offset + 0x60)[0]
    notify_count = data[offset + 0x22]
    if notify_ptr == 0xFFFFFFFF and notify_count > 0:
        notify_size = notify_count * 8  # XAnimNotifyInfo is 8 bytes
        print(f"    notify @ 0x{pos:X}: {notify_count} entries, {notify_size} bytes")
        pos += notify_size

    # 4) DeltaPart
    delta_ptr = struct.unpack_from('<I', data, offset + 0x64)[0]
    if delta_ptr == 0xFFFFFFFF:
        print(f"    deltaPart @ 0x{pos:X}: PTR_FOLLOWING (complex, skipping)")
        # Can't easily trace delta part size
        return

    # 5) dataByte
    if info['dataByte_ptr'] == 0xFFFFFFFF and info['dataByteCount'] > 0:
        count = info['dataByteCount']
        print(f"    dataByte @ 0x{pos:X}: {count} bytes")
        print(f"      bytes: {list(data[pos:pos + min(count, 16)])}")
        pos += count

    # Check for padding between dataByte and dataShort
    if info['dataShort_ptr'] == 0xFFFFFFFF and info['dataShortCount'] > 0:
        # Check if there's a padding byte
        if pos % 2 != 0:
            print(f"    [ALIGNMENT PAD @ 0x{pos:X}: 1 byte = 0x{data[pos]:02X}]")
        # Show boundary bytes
        print(f"    boundary dataByte->dataShort @ 0x{pos:X}:")
        print(hex_dump(data[pos:pos + 8], pos))

    # 6) dataShort
    if info['dataShort_ptr'] == 0xFFFFFFFF and info['dataShortCount'] > 0:
        count = info['dataShortCount']
        byte_size = count * 2
        print(f"    dataShort @ 0x{pos:X}: {count} entries, {byte_size} bytes")
        shorts = []
        for i in range(min(count, 8)):
            v = struct.unpack_from('<h', data, pos + i * 2)[0]
            shorts.append(v)
        print(f"      first values: {shorts}")
        pos += byte_size

    # Check padding before dataInt
    if info['dataInt_ptr'] == 0xFFFFFFFF and info['dataIntCount'] > 0:
        misalign = pos % 4
        if misalign != 0:
            pad = 4 - misalign
            print(f"    [ALIGNMENT PAD @ 0x{pos:X}: {pad} bytes = {list(data[pos:pos+pad])}]")
        print(f"    boundary dataShort->dataInt @ 0x{pos:X}:")
        print(hex_dump(data[pos:pos + 8], pos))

    # 7) dataInt
    if info['dataInt_ptr'] == 0xFFFFFFFF and info['dataIntCount'] > 0:
        count = info['dataIntCount']
        byte_size = count * 4
        print(f"    dataInt @ 0x{pos:X}: {count} entries, {byte_size} bytes")
        floats = []
        for i in range(min(count, 6)):
            v = struct.unpack_from('<f', data, pos + i * 4)[0]
            floats.append(round(v, 3))
        print(f"      first floats: {floats}")
        pos += byte_size

    # Show what comes next
    print(f"    end of data @ 0x{pos:X}")
    print(f"    next 16 bytes:")
    print(hex_dump(data[pos:pos + 16], pos))


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--ff", required=True, help="Path to .ff file")
    parser.add_argument("--mode", choices=["stubs", "vanilla", "patched", "all"], default="all")
    args = parser.parse_args()

    print(f"Decrypting {args.ff}...")
    magic, data = decrypt_zone(args.ff, ZONE_NAME)
    print(f"  {len(data):,} bytes decrypted")

    result = parse_string_table(data)
    string_table, string_count, asset_count, asset_data_offset = result[0], result[1], result[2], result[3]

    if args.mode in ("stubs", "all"):
        print(f"\n{'#'*60}")
        print(f"# EMPTY STUBS (vm_thunder_gun_*)")
        print(f"{'#'*60}")
        stubs = find_empty_xanim_stubs(data, "vm_thunder_gun_", min_search_offset=asset_data_offset)
        print(f"Found {len(stubs)} empty stubs")
        for i, stub in enumerate(stubs[:3]):  # Show first 3
            print(f"\n--- Stub {i}: '{stub['name']}' ---")
            print(f"  header_start=0x{stub['header_start']:X}, gap={stub['gap']}, gap_bytes={list(stub['gap_bytes'])}")
            info = analyze_xanim_header(data, stub['header_start'], f"[EMPTY STUB: {stub['name']}]")

    if args.mode in ("vanilla", "all"):
        print(f"\n{'#'*60}")
        print(f"# REAL (NON-EMPTY) XAnimParts")
        print(f"{'#'*60}")
        reals = find_real_xanim(data, asset_data_offset)
        print(f"Found {len(reals)} real XAnimParts candidates")
        for i, entry in enumerate(reals[:3]):  # Show first 3
            print(f"\n--- Real {i}: '{entry['name']}' ---")
            print(f"  offset=0x{entry['offset']:X}, bones={entry['bones']}, frames={entry['numframes']}")
            info = analyze_xanim_header(data, entry['offset'], f"[REAL: {entry['name']}]")
            if info:
                trace_data_sections(data, entry['offset'], info)

    if args.mode in ("patched", "all"):
        print(f"\n{'#'*60}")
        print(f"# PATCHED ENTRIES (looking for non-empty vm_thunder_gun_*)")
        print(f"{'#'*60}")
        # Search for vm_thunder_gun_ headers that are NOT empty
        pos = asset_data_offset
        prefix = b"vm_thunder_gun_"
        found = 0
        while pos < len(data) - 200 and found < 3:
            # Look for the name string
            idx = data.find(prefix, pos)
            if idx == -1:
                break
            # Check if there's a valid XAnimParts header ~104 bytes before
            for back in range(90, 120):
                hstart = idx - back
                if hstart < 0:
                    continue
                name_ptr = struct.unpack_from('<I', data, hstart)[0]
                if name_ptr == 0xFFFFFFFF:
                    # Check if this is NOT empty (has non-zero bone data)
                    total_bones = data[hstart + 0x21]
                    if total_bones > 0:
                        null_pos = data.index(b'\x00', idx, idx + 200)
                        name = data[idx:null_pos].decode('ascii', errors='replace')
                        print(f"\n--- Patched: '{name}' (total_bones={total_bones}) ---")
                        info = analyze_xanim_header(data, hstart, f"[PATCHED: {name}]")
                        if info:
                            trace_data_sections(data, hstart, info)
                        found += 1
                        break
            pos = idx + len(prefix)


if __name__ == "__main__":
    main()
