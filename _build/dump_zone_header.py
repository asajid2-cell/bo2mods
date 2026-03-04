#!/usr/bin/env python3
"""Decrypt and dump the XFile header of a T6 .ff zone file for comparison."""
import struct
import zlib
import hashlib
import sys
import os
from Crypto.Cipher import Salsa20

SALSA20_KEY = bytes([
    0x64, 0x1D, 0x8A, 0x2F, 0xE3, 0x1D, 0x3A, 0xA6,
    0x36, 0x22, 0xBB, 0xC9, 0xCE, 0x85, 0x87, 0x22,
    0x9D, 0x42, 0xB0, 0xF8, 0xED, 0x9B, 0x92, 0x41,
    0x30, 0xBF, 0x88, 0xB6, 0x5E, 0xDC, 0x50, 0xBE,
])

STREAM_COUNT = 4
BLOCK_HASHES_COUNT = 200
SHA1_HASH_SIZE = 20
VANILLA_BUFFER_SIZE = 0x80000

def init_hash_chain(zone_name):
    """Initialize the SHA-1 hash chain from zone name (same as writer)."""
    name = zone_name[:31]
    total_size = BLOCK_HASHES_COUNT * STREAM_COUNT * SHA1_HASH_SIZE
    block_hashes = bytearray(total_size)
    name_bytes = name.encode('ascii')
    name_len = len(name_bytes)
    name_offset = 0
    for i in range(0, total_size, 4):
        ch = name_bytes[name_offset % name_len]
        remaining = min(4, total_size - i)
        for j in range(remaining):
            block_hashes[i + j] = ch
        name_offset += 1
    return block_hashes

def get_hash_block(block_hashes, stream_num, block_idx):
    offset = block_idx * STREAM_COUNT * SHA1_HASH_SIZE + stream_num * SHA1_HASH_SIZE
    return block_hashes[offset:offset + SHA1_HASH_SIZE]

def set_hash_block(block_hashes, stream_num, block_idx, data):
    offset = block_idx * STREAM_COUNT * SHA1_HASH_SIZE + stream_num * SHA1_HASH_SIZE
    block_hashes[offset:offset + SHA1_HASH_SIZE] = data[:SHA1_HASH_SIZE]

def decrypt_zone(filepath, zone_name):
    """Decrypt a T6 zone file and return the raw zone data."""
    with open(filepath, 'rb') as f:
        data = f.read()

    # Read header
    magic = data[:8]
    version = struct.unpack_from('<I', data, 8)[0]
    print(f"Magic: {magic}")
    print(f"Version: {version}")

    # Check if signed (TAff0100) - has signature data
    if magic == b"TAff0100":
        # Signed: skip 256-byte RSA signature + 1024-byte signing data
        stream_start = 12 + 256
        print(f"Signed zone - skipping 256-byte signature")
    elif magic == b"TAffu100":
        stream_start = 12
    elif magic == b"TAsvu100":
        print("Unencrypted server zone - not supported here")
        return None
    else:
        print(f"Unknown magic: {magic}")
        return None

    block_hashes = init_hash_chain(zone_name)
    block_indices = [0] * STREAM_COUNT
    current_stream = 0
    vanilla_offset = 0

    raw_data = bytearray()
    pos = stream_start
    chunk_num = 0

    while pos < len(data) - 4:
        # Check for vanilla buffer boundary
        if vanilla_offset + 4 > VANILLA_BUFFER_SIZE:
            padding = VANILLA_BUFFER_SIZE - vanilla_offset
            pos += padding
            vanilla_offset = 0

        # Read chunk size
        if pos + 4 > len(data):
            break
        chunk_size = struct.unpack_from('<I', data, pos)[0]
        pos += 4
        vanilla_offset += 4

        if chunk_size == 0:
            # End marker or padding
            break

        if pos + chunk_size > len(data):
            print(f"  Chunk {chunk_num}: size {chunk_size} exceeds file! (pos={pos}, filelen={len(data)})")
            break

        # Read encrypted data
        encrypted = data[pos:pos + chunk_size]
        pos += chunk_size
        vanilla_offset += chunk_size

        # Get nonce from hash chain
        hash_block = get_hash_block(block_hashes, current_stream, block_indices[current_stream])
        nonce = bytes(hash_block[:8])

        # Decrypt with Salsa20
        cipher = Salsa20.new(key=SALSA20_KEY, nonce=nonce)
        compressed = cipher.decrypt(encrypted)

        # Advance hash chain (hash the compressed data, same as writer)
        sha1_hash = hashlib.sha1(compressed).digest()
        current_idx = block_indices[current_stream]
        next_idx = (current_idx + 1) % BLOCK_HASHES_COUNT
        block_indices[current_stream] = next_idx
        next_block = bytearray(get_hash_block(block_hashes, current_stream, next_idx))
        for i in range(min(SHA1_HASH_SIZE, len(sha1_hash))):
            next_block[i] ^= sha1_hash[i]
        set_hash_block(block_hashes, current_stream, next_idx, bytes(next_block))

        # Decompress
        try:
            decompressed = zlib.decompress(compressed, -15)
            raw_data.extend(decompressed)
            if chunk_num < 3:
                print(f"  Chunk {chunk_num} (stream {current_stream}): {chunk_size} encrypted -> {len(compressed)} compressed -> {len(decompressed)} raw")
        except Exception as e:
            print(f"  Chunk {chunk_num}: Decompress failed: {e}")
            print(f"    First 16 bytes compressed: {compressed[:16].hex()}")
            break

        current_stream = (current_stream + 1) % STREAM_COUNT
        chunk_num += 1

    return bytes(raw_data)


def dump_header(raw_data, max_bytes=256):
    """Dump the XFile header and beginning of zone content."""
    if len(raw_data) < 40:
        print(f"Raw data too short: {len(raw_data)} bytes")
        return

    total_size = struct.unpack_from('<I', raw_data, 0)[0]
    external_size = struct.unpack_from('<I', raw_data, 4)[0]

    print(f"\n=== XFile Header ===")
    print(f"totalSize:    {total_size} (0x{total_size:08X})")
    print(f"externalSize: {external_size} (0x{external_size:08X})")

    block_names = ["TEMP", "PHYS_RUNTIME", "RUNTIME", "VIRTUAL", "LARGE", "CALLBACK", "VERTEX", "INDEX"]
    total_blocks = 0
    for i in range(8):
        bs = struct.unpack_from('<I', raw_data, 8 + i * 4)[0]
        total_blocks += bs
        if bs > 0:
            print(f"blockSize[{i}] ({block_names[i]:>13}): {bs:,} (0x{bs:08X})")
        else:
            print(f"blockSize[{i}] ({block_names[i]:>13}): 0")
    print(f"Sum of blocks: {total_blocks:,}")

    # Content starts at offset 40
    content_start = 40
    print(f"\n=== Zone Content (offset {content_start}) ===")

    # Try to read XAssetList
    if len(raw_data) >= content_start + 8:
        string_count = struct.unpack_from('<i', raw_data, content_start)[0]
        strings_ptr = struct.unpack_from('<I', raw_data, content_start + 4)[0]
        print(f"ScriptStringList.count:   {string_count}")
        print(f"ScriptStringList.strings: 0x{strings_ptr:08X} {'(FOLLOWING)' if strings_ptr == 0xFFFFFFFE else '(NULL)' if strings_ptr == 0 else ''}")

    # Hex dump first N bytes of content
    print(f"\n=== Raw hex dump (first {max_bytes} bytes of content) ===")
    for i in range(0, min(max_bytes, len(raw_data) - content_start), 16):
        offset = content_start + i
        hex_bytes = ' '.join(f'{raw_data[offset + j]:02X}' for j in range(min(16, len(raw_data) - offset)))
        ascii_chars = ''.join(chr(raw_data[offset + j]) if 32 <= raw_data[offset + j] < 127 else '.' for j in range(min(16, len(raw_data) - offset)))
        print(f"  {offset:06X}: {hex_bytes:<48} {ascii_chars}")


if __name__ == "__main__":
    # Dump our custom zone
    our_ff = r"z:\Games\pluto_t6_full_game\_build\panzer_work\output\thundergun_xanims.ff"
    print("=" * 70)
    print("OUR ZONE: thundergun_xanims.ff")
    print("=" * 70)
    raw = decrypt_zone(our_ff, "thundergun_xanims")
    if raw:
        dump_header(raw)

    # Dump a reference zone for comparison
    ref_ff = r"z:\Games\pluto_t6_full_game\zone\all\common_zm.ff"
    if os.path.exists(ref_ff):
        print("\n\n" + "=" * 70)
        print("REFERENCE ZONE: common_zm.ff")
        print("=" * 70)
        raw_ref = decrypt_zone(ref_ff, "common_zm")
        if raw_ref:
            dump_header(raw_ref)
