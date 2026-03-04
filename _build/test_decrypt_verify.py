#!/usr/bin/env python3
"""Encrypt then decrypt a zone and verify the content matches."""
import struct
import os
from compile_xanim_zone import (
    XChunkWriter, T6_ZONE_MAGIC_UNSIGNED, T6_ZONE_VERSION,
    XFILE_BLOCK_COUNT
)
from dump_zone_header import decrypt_zone

PTR_FOLLOWING = 0xFFFFFFFE
PTR_NULL = 0x00000000
OUTPUT_DIR = r"z:\Games\pluto_t6_full_game\_build\panzer_work\output"

def build_and_verify(name, raw_data, zone_name):
    """Build a .ff, then decrypt it and compare."""
    print(f"\n=== {name} ===")

    # Hex dump of raw data
    print(f"  Raw data ({len(raw_data)} bytes):")
    for i in range(0, len(raw_data), 16):
        hex_bytes = ' '.join(f'{raw_data[i + j]:02X}' for j in range(min(16, len(raw_data) - i)))
        print(f"    {i:04X}: {hex_bytes}")

    # Write encrypted zone
    ff_path = os.path.join(OUTPUT_DIR, f"{zone_name}.ff")
    xchunk = XChunkWriter(zone_name)
    xchunk.write_data(raw_data)
    encrypted = xchunk.get_output()

    with open(ff_path, 'wb') as f:
        f.write(T6_ZONE_MAGIC_UNSIGNED)
        f.write(struct.pack('<I', T6_ZONE_VERSION))
        f.write(encrypted)
        padding = 0x40 - (f.tell() % 0x40)
        if padding < 0x40:
            padding += 0x40
        f.write(b'\x00' * padding)

    print(f"  Encrypted file: {os.path.getsize(ff_path)} bytes")

    # Decrypt and compare
    decrypted = decrypt_zone(ff_path, zone_name)
    if decrypted is None:
        print("  FAILED to decrypt!")
        return

    print(f"  Decrypted ({len(decrypted)} bytes):")
    for i in range(0, min(len(decrypted), len(raw_data) + 16), 16):
        hex_bytes = ' '.join(f'{decrypted[i + j]:02X}' for j in range(min(16, len(decrypted) - i)))
        print(f"    {i:04X}: {hex_bytes}")

    # Compare
    if decrypted[:len(raw_data)] == raw_data:
        print(f"  MATCH: Decrypted content matches raw data perfectly!")
    else:
        print(f"  MISMATCH! First difference at:")
        for i in range(min(len(raw_data), len(decrypted))):
            if raw_data[i] != decrypted[i]:
                print(f"    Offset {i}: expected 0x{raw_data[i]:02X}, got 0x{decrypted[i]:02X}")
                break
        if len(decrypted) < len(raw_data):
            print(f"    Decrypted is shorter ({len(decrypted)} vs {len(raw_data)})")


def main():
    # Working: empty zone, 10 blocks
    buf1 = bytearray()
    buf1.extend(struct.pack('<I', 0))
    buf1.extend(struct.pack('<I', 0))
    for _ in range(10):
        buf1.extend(struct.pack('<I', 0))
    content_start = len(buf1)
    buf1.extend(struct.pack('<i', 0))
    buf1.extend(struct.pack('<I', PTR_NULL))
    buf1.extend(struct.pack('<i', 0))
    buf1.extend(struct.pack('<I', PTR_NULL))
    total_size = len(buf1) - content_start
    struct.pack_into('<I', buf1, 0, total_size)
    struct.pack_into('<I', buf1, 8 + 3*4, total_size)

    build_and_verify("Working: Empty zone (10 blocks)", bytes(buf1), "test_format")

    # Failing: 1 string zone, 10 blocks
    buf2 = bytearray()
    buf2.extend(struct.pack('<I', 0))
    buf2.extend(struct.pack('<I', 0))
    for _ in range(10):
        buf2.extend(struct.pack('<I', 0))
    content_start = len(buf2)
    buf2.extend(struct.pack('<i', 1))
    buf2.extend(struct.pack('<I', PTR_FOLLOWING))
    buf2.extend(struct.pack('<I', PTR_FOLLOWING))
    buf2.extend(b'tag_view\x00')
    while len(buf2) % 4 != 0:
        buf2.append(0)
    buf2.extend(struct.pack('<i', 0))
    buf2.extend(struct.pack('<I', PTR_NULL))
    total_size = len(buf2) - content_start
    struct.pack_into('<I', buf2, 0, total_size)
    struct.pack_into('<I', buf2, 8 + 3*4, total_size)

    build_and_verify("Failing: 1 string zone (10 blocks)", bytes(buf2), "test_format")


if __name__ == "__main__":
    main()
