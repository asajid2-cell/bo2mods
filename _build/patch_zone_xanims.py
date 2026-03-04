#!/usr/bin/env python3
"""
Post-build zone patcher: Replace empty XAnimParts stubs in an OAT-built
T6 zone with real animation data from xanim_export files.

OAT v0.26.1 has AssetLoaderXAnim commented out for T6, resulting in empty
default stubs (zero bones, zero frames, zero data). This patcher:

  1. Decrypts the OAT-built zone (.ff)
  2. Parses the script string table to get bone name -> index mapping
  3. Finds empty XAnimParts stubs matching a name pattern
  4. Parses xanim_export files to get frame 0 animation data
  5. Builds replacement XAnimParts data (model bones only)
  6. Splices replacements into the decrypted stream
  7. Updates XFile header (totalSize, block sizes)
  8. Re-encrypts and writes the patched .ff
"""

import struct
import zlib
import hashlib
import os
import re
import math
import glob
import argparse
from Crypto.Cipher import Salsa20

try:
    import strict_xanim_parser as strict_xanim
except Exception:
    strict_xanim = None


# ============================================================================
# T6 Zone Constants
# ============================================================================

T6_ZONE_MAGIC_UNSIGNED = b"TAffu100"
T6_ZONE_VERSION = 147

SALSA20_KEY = bytes([
    0x64, 0x1D, 0x8A, 0x2F, 0xE3, 0x1D, 0x3A, 0xA6,
    0x36, 0x22, 0xBB, 0xC9, 0xCE, 0x85, 0x87, 0x22,
    0x9D, 0x42, 0xB0, 0xF8, 0xED, 0x9B, 0x92, 0x41,
    0x30, 0xBF, 0x88, 0xB6, 0x5E, 0xDC, 0x50, 0xBE,
])

STREAM_COUNT = 4
BLOCK_HASHES_COUNT = 200
SHA1_HASH_SIZE = 20
XCHUNK_SIZE = 0x8000
XCHUNK_MAX_WRITE = XCHUNK_SIZE - 0x40  # 0x7FC0
VANILLA_BUFFER_SIZE = 0x80000  # 512KB

PTR_FOLLOWING = 0xFFFFFFFF
PTR_NULL = 0x00000000
DELTA_PART_STUB_SIZE = 12  # XAnimDeltaPart: 3 pointers (trans, quat2, quat)

BLOCK_TEMP = 0
BLOCK_VIRTUAL = 5
XFILE_BLOCK_COUNT = 8
XFILE_HEADER_SIZE = 40  # totalSize(4) + externalSize(4) + blockSizes(8*4)
FASTFILE_HEADER_SIZE = 12  # magic(8) + version(4)

# Add conservative virtual-block headroom to mirror prior stable loader behavior.
# For 28 patched stubs this yields +288 bytes (8 + 28*10).
VIRTUAL_ALIGN_SAFETY_BASE = 8
VIRTUAL_ALIGN_SAFETY_PER_STUB = 10


# ============================================================================
# XChunk Crypto — Writer (Encrypt)
# ============================================================================

class XChunkWriter:
    """T6 XChunk stream writer with Salsa20 hash-chain encryption."""

    def __init__(self, zone_name):
        self.zone_name = zone_name[:31]
        self.current_stream = 0
        self.block_indices = [0] * STREAM_COUNT
        # OAT tracks vanilla-buffer boundaries from absolute file position.
        # XChunk data starts immediately after the 12-byte fastfile header.
        self.vanilla_buffer_offset = FASTFILE_HEADER_SIZE
        self.output = bytearray()
        self._init_hashes()

    def _init_hashes(self):
        total = BLOCK_HASHES_COUNT * STREAM_COUNT * SHA1_HASH_SIZE
        self.block_hashes = bytearray(total)
        name_bytes = self.zone_name.encode('ascii')
        nlen = len(name_bytes)
        name_offset = 0
        for i in range(0, total, 4):
            ch = name_bytes[name_offset % nlen]
            for j in range(min(4, total - i)):
                self.block_hashes[i + j] = ch
            name_offset += 1

    def _get_hash(self, stream):
        idx = self.block_indices[stream]
        off = idx * STREAM_COUNT * SHA1_HASH_SIZE + stream * SHA1_HASH_SIZE
        return self.block_hashes[off:off + SHA1_HASH_SIZE]

    def _set_hash(self, stream, block_idx, data):
        off = block_idx * STREAM_COUNT * SHA1_HASH_SIZE + stream * SHA1_HASH_SIZE
        self.block_hashes[off:off + SHA1_HASH_SIZE] = data[:SHA1_HASH_SIZE]

    def _advance(self, stream, plaintext):
        sha1 = hashlib.sha1(plaintext).digest()
        cur = self.block_indices[stream]
        nxt = (cur + 1) % BLOCK_HASHES_COUNT
        self.block_indices[stream] = nxt
        blk = bytearray(self._get_hash(stream))
        for i in range(SHA1_HASH_SIZE):
            blk[i] ^= sha1[i]
        self._set_hash(stream, nxt, bytes(blk))

    def write_chunk(self, data):
        co = zlib.compressobj(9, zlib.DEFLATED, -15)
        compressed = co.compress(data) + co.flush()

        nonce = bytes(self._get_hash(self.current_stream)[:8])
        cipher = Salsa20.new(key=SALSA20_KEY, nonce=nonce)
        encrypted = cipher.encrypt(compressed)

        self._advance(self.current_stream, compressed)

        # Match OAT OutputProcessorXChunks exactly:
        # only pad when the *size field* would cross the vanilla boundary.
        if self.vanilla_buffer_offset + 4 > VANILLA_BUFFER_SIZE:
            padding = VANILLA_BUFFER_SIZE - self.vanilla_buffer_offset
            if padding > 0:
                self.output.extend(b'\x00' * padding)
            self.vanilla_buffer_offset = 0

        self.output.extend(struct.pack('<I', len(encrypted)))
        self.vanilla_buffer_offset += 4
        self.output.extend(encrypted)
        self.vanilla_buffer_offset += len(encrypted)
        self.vanilla_buffer_offset %= VANILLA_BUFFER_SIZE
        self.current_stream = (self.current_stream + 1) % STREAM_COUNT

    def write_data(self, raw):
        off = 0
        while off < len(raw):
            sz = min(XCHUNK_MAX_WRITE, len(raw) - off)
            self.write_chunk(raw[off:off + sz])
            off += sz

    def get_output(self):
        return bytes(self.output)


# ============================================================================
# XChunk Crypto — Reader (Decrypt)
# ============================================================================

def _init_decrypt_hashes(zone_name):
    name_bytes = zone_name[:31].encode('ascii')
    nlen = len(name_bytes)
    total = BLOCK_HASHES_COUNT * STREAM_COUNT * SHA1_HASH_SIZE
    hashes = bytearray(total)
    name_offset = 0
    for i in range(0, total, 4):
        ch = name_bytes[name_offset % nlen]
        for j in range(min(4, total - i)):
            hashes[i + j] = ch
        name_offset += 1
    return hashes


def decrypt_zone(ff_path, zone_name):
    """Decrypt a T6 .ff zone file. Returns (magic, raw_data)."""
    with open(ff_path, 'rb') as f:
        magic = f.read(8)
        version = struct.unpack('<I', f.read(4))[0]
        enc_data = f.read()

    hashes = _init_decrypt_hashes(zone_name)
    block_indices = [0] * STREAM_COUNT
    current_stream = 0
    # Mirror OAT loader: boundary handling starts at absolute stream position
    # (12 bytes after magic+version header).
    vanilla_offset = FASTFILE_HEADER_SIZE
    decrypted = bytearray()
    pos = 0

    while pos < len(enc_data) - 4:
        chunk_size = struct.unpack_from('<I', enc_data, pos)[0]
        pos += 4
        vanilla_offset += 4

        if chunk_size == 0:
            remain = VANILLA_BUFFER_SIZE - vanilla_offset
            if 0 < remain < VANILLA_BUFFER_SIZE:
                pos += remain
                vanilla_offset = 0
                continue
            break

        if pos + chunk_size > len(enc_data):
            break

        encrypted = enc_data[pos:pos + chunk_size]
        pos += chunk_size
        vanilla_offset += chunk_size

        bidx = block_indices[current_stream]
        h_off = bidx * STREAM_COUNT * SHA1_HASH_SIZE + current_stream * SHA1_HASH_SIZE
        nonce = bytes(hashes[h_off:h_off + 8])
        cipher = Salsa20.new(key=SALSA20_KEY, nonce=nonce)
        compressed = cipher.decrypt(encrypted)

        sha1 = hashlib.sha1(compressed).digest()
        nxt = (bidx + 1) % BLOCK_HASHES_COUNT
        block_indices[current_stream] = nxt
        n_off = nxt * STREAM_COUNT * SHA1_HASH_SIZE + current_stream * SHA1_HASH_SIZE
        for i in range(SHA1_HASH_SIZE):
            hashes[n_off + i] ^= sha1[i]

        try:
            decompressed = zlib.decompress(compressed, -15)
            decrypted.extend(decompressed)
        except Exception:
            break

        current_stream = (current_stream + 1) % STREAM_COUNT

    return magic, bytes(decrypted)


# ============================================================================
# xanim_export Parser
# ============================================================================

def parse_xanim_export(filepath):
    """Parse an xanim_export text file into structured data."""
    with open(filepath, 'r') as f:
        content = f.read()
    lines = content.split('\n')

    anim = {
        'name': os.path.splitext(os.path.basename(filepath))[0],
        'numparts': 0,
        'parts': [],
        'framerate': 30,
        'numframes': 0,
        'frames': {},
    }

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith('NUMPARTS'):
            anim['numparts'] = int(line.split()[1])
        elif re.match(r'^PART\s+\d+\s+"', line):
            m = re.match(r'^PART\s+(\d+)\s+"([^"]+)"', line)
            if m:
                anim['parts'].append(m.group(2))
        elif line.startswith('FRAMERATE'):
            anim['framerate'] = int(line.split()[1])
        elif line.startswith('NUMFRAMES') or line.startswith('NUMKEYS'):
            anim['numframes'] = int(line.split()[1])
        elif line.startswith('FRAME '):
            frame_num = int(line.split()[1])
            frame_data = {}
            i += 1
            while i < len(lines):
                fline = lines[i].strip()
                if fline.startswith('FRAME ') or not fline:
                    if not fline:
                        i += 1
                        continue
                    i -= 1
                    break
                if fline.startswith('PART '):
                    pm = re.match(r'^PART\s+(\d+)$', fline)
                    if pm:
                        pidx = int(pm.group(1))
                        bone = {'offset': [0, 0, 0], 'rot': [[1, 0, 0], [0, 1, 0], [0, 0, 1]]}
                        for _ in range(5):
                            i += 1
                            if i >= len(lines):
                                break
                            bline = lines[i].strip()
                            if bline.startswith('OFFSET'):
                                bone['offset'] = [float(v) for v in bline.split()[1:4]]
                            elif bline.startswith('X '):
                                bone['rot'][0] = [float(v) for v in bline.split()[1:4]]
                            elif bline.startswith('Y '):
                                bone['rot'][1] = [float(v) for v in bline.split()[1:4]]
                            elif bline.startswith('Z '):
                                bone['rot'][2] = [float(v) for v in bline.split()[1:4]]
                        frame_data[pidx] = bone
                i += 1
            anim['frames'][frame_num] = frame_data
        i += 1

    return anim


def rotation_matrix_to_quat(m):
    """Convert 3x3 rotation matrix to quaternion [x, y, z, w]."""
    trace = m[0][0] + m[1][1] + m[2][2]
    if trace > 0:
        s = 0.5 / math.sqrt(trace + 1.0)
        w = 0.25 / s
        x = (m[2][1] - m[1][2]) * s
        y = (m[0][2] - m[2][0]) * s
        z = (m[1][0] - m[0][1]) * s
    elif m[0][0] > m[1][1] and m[0][0] > m[2][2]:
        s = 2.0 * math.sqrt(1.0 + m[0][0] - m[1][1] - m[2][2])
        w = (m[2][1] - m[1][2]) / s
        x = 0.25 * s
        y = (m[0][1] + m[1][0]) / s
        z = (m[0][2] + m[2][0]) / s
    elif m[1][1] > m[2][2]:
        s = 2.0 * math.sqrt(1.0 + m[1][1] - m[0][0] - m[2][2])
        w = (m[0][2] - m[2][0]) / s
        x = (m[0][1] + m[1][0]) / s
        y = 0.25 * s
        z = (m[1][2] + m[2][1]) / s
    else:
        s = 2.0 * math.sqrt(1.0 + m[2][2] - m[0][0] - m[1][1])
        w = (m[1][0] - m[0][1]) / s
        x = (m[0][2] + m[2][0]) / s
        y = (m[1][2] + m[2][1]) / s
        z = 0.25 * s
    length = math.sqrt(x * x + y * y + z * z + w * w)
    if length > 0:
        x /= length; y /= length; z /= length; w /= length
    return [x, y, z, w]


def quat_multiply(a, b):
    """Quaternion multiply with [x, y, z, w] layout."""
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return [
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
        aw * bw - ax * bx - ay * by - az * bz,
    ]


def quat_normalize(q):
    n = math.sqrt(sum(c * c for c in q))
    if n < 1e-10:
        return [0.0, 0.0, 0.0, 1.0]
    return [c / n for c in q]


SQRT2_OVER_2 = math.sqrt(2.0) / 2.0
QUAT_NEG90X = [-SQRT2_OVER_2, 0.0, 0.0, SQRT2_OVER_2]  # -90 deg X


def lhc_to_rhc_position(p):
    """T6 LHC (X,Y,Z) -> glTF RHC (X,Z,-Y)."""
    return [p[0], p[2], -p[1]]


def lhc_to_rhc_quaternion(q_lhc):
    """T6 LHC quaternion -> RHC quaternion (pre-multiply by -90 deg X)."""
    return quat_normalize(quat_multiply(QUAT_NEG90X, q_lhc))


def quat_to_int16(q):
    return max(-32767, min(32767, int(round(q * 32767.0))))


# ============================================================================
# Zone Parsing
# ============================================================================

def parse_string_table(data):
    """Parse the zone's ScriptStringList.

    Returns (string_map, string_count, asset_count, asset_data_offset,
             ptr_array_start, string_data_start, string_data_end).
    """
    pos = XFILE_HEADER_SIZE  # Skip XFile header (40 bytes)

    string_count = struct.unpack_from('<i', data, pos)[0]; pos += 4
    strings_ptr = struct.unpack_from('<I', data, pos)[0]; pos += 4
    depend_count = struct.unpack_from('<i', data, pos)[0]; pos += 4
    _depends_ptr = struct.unpack_from('<I', data, pos)[0]; pos += 4
    asset_count = struct.unpack_from('<i', data, pos)[0]; pos += 4
    _assets_ptr = struct.unpack_from('<I', data, pos)[0]; pos += 4

    print(f"  XAssetList: {string_count} strings, {depend_count} depends, {asset_count} assets")

    # Skip depend data (if any)
    if depend_count > 0:
        for _ in range(depend_count):
            pos += 4  # pointer
        for _ in range(depend_count):
            while pos < len(data) and data[pos] != 0:
                pos += 1
            pos += 1  # skip null

    # String pointer array start
    ptr_array_start = pos
    if strings_ptr == PTR_FOLLOWING and string_count > 0:
        pos += string_count * 4

    # String data start
    string_data_start = pos

    # Read string data
    string_map = {}
    for i in range(string_count):
        end = data.index(b'\x00', pos)
        name = data[pos:end].decode('ascii', errors='replace')
        if name not in string_map:
            string_map[name] = i
        pos = end + 1

    string_data_end = pos
    print(f"  String table: ptrs@0x{ptr_array_start:X}, data@0x{string_data_start:X}..0x{string_data_end:X}")

    # Skip XAsset array (type + pointer per asset)
    if _assets_ptr == PTR_FOLLOWING and asset_count > 0:
        pos += asset_count * 8

    asset_data_offset = pos
    print(f"  Asset data begins at offset 0x{asset_data_offset:X}")

    return (string_map, string_count, asset_count, asset_data_offset,
            ptr_array_start, string_data_start, string_data_end)


def expand_string_table(data, new_strings, ptr_array_start, string_data_end, old_count):
    """Insert new script strings into the zone's string table.

    Adds new PTR_FOLLOWING entries to the pointer array and appends new
    null-terminated strings after the existing string data.  Everything
    after the insertion points is shifted accordingly.

    Returns (modified_data, updated_string_map_additions) where the map
    maps new string names to their indices (old_count, old_count+1, ...).
    """
    if not new_strings:
        return data, {}

    n = len(new_strings)

    # Build the bytes to insert
    # 1) N new PTR_FOLLOWING entries at end of pointer array
    new_ptrs = struct.pack('<I', PTR_FOLLOWING) * n
    # 2) N null-terminated strings at end of string data
    new_str_data = bytearray()
    additions = {}
    for i, s in enumerate(new_strings):
        additions[s] = old_count + i
        new_str_data.extend(s.encode('ascii') + b'\x00')

    # Pointer array ends where string data begins.
    # Insert new pointer entries at that boundary (shifts string data right).
    ptr_insert_pos = ptr_array_start + old_count * 4
    buf = bytearray(data)
    buf[ptr_insert_pos:ptr_insert_pos] = new_ptrs  # insert, shifting right

    # Now string data has shifted right by len(new_ptrs).
    # Append new string data after existing strings.
    str_insert_pos = string_data_end + len(new_ptrs)
    buf[str_insert_pos:str_insert_pos] = new_str_data  # insert

    # Update stringCount in XAssetList header (offset 40)
    struct.pack_into('<i', buf, XFILE_HEADER_SIZE, old_count + n)

    # Update XFile header: totalSize and VIRTUAL block size
    total_added = len(new_ptrs) + len(new_str_data)
    old_total = struct.unpack_from('<I', buf, 0)[0]
    struct.pack_into('<I', buf, 0, old_total + total_added)

    virtual_off = 8 + BLOCK_VIRTUAL * 4
    old_virtual = struct.unpack_from('<I', buf, virtual_off)[0]
    struct.pack_into('<I', buf, virtual_off, old_virtual + total_added)

    print(f"  Expanded string table: +{n} strings, +{total_added} bytes")
    print(f"    Ptr entries: +{len(new_ptrs)} bytes at 0x{ptr_insert_pos:X}")
    print(f"    String data: +{len(new_str_data)} bytes at 0x{str_insert_pos:X}")
    print(f"    totalSize: {old_total} -> {old_total + total_added}")

    return bytes(buf), additions


def find_empty_xanim_stubs(data, name_prefix, min_search_offset=0):
    """Find empty XAnimParts stubs in the decrypted zone data.

    OAT's DefaultAssetCreator creates a zeroed struct with only the name pointer
    set to PTR_FOLLOWING. This gives us a highly distinctive 104-byte pattern:
    [0xFFFFFFFF][100 bytes of 0x00]. We search for this exact pattern, then
    check if a matching name string follows.

    Returns list of dicts with stub locations and metadata.
    """
    stubs = []
    prefix_bytes = name_prefix.encode('ascii')

    # The exact byte pattern of an OAT empty XAnimParts stub:
    # 4 bytes PTR_FOLLOWING + 100 bytes of zeros = 104 bytes total
    empty_header = b'\xff\xff\xff\xff' + b'\x00' * 100

    search_pos = max(min_search_offset, 0)
    while True:
        # Find the next empty header pattern
        pos = data.find(empty_header, search_pos)
        if pos == -1:
            break

        header_start = pos

        # After the 104-byte header, there may be a leading comma (asset ref name)
        # or other prefix bytes before the actual name text.
        # Search window must be large enough for gap + full prefix match
        name_search_start = header_start + 104
        name_search_end = min(name_search_start + len(prefix_bytes) + 8, len(data))
        name_region = data[name_search_start:name_search_end]

        # Find where the name string starts (skip any gap bytes like block switch indicators)
        name_start = -1
        for offset in range(len(name_region)):
            if name_region[offset:offset + len(prefix_bytes)] == prefix_bytes:
                name_start = name_search_start + offset
                break

        if name_start == -1:
            # No matching name after this header — not our target
            search_pos = header_start + 4
            continue

        # Read the full name
        null_pos = data.index(b'\x00', name_start)
        name = data[name_start:null_pos].decode('ascii', errors='replace')
        gap_bytes = data[header_start + 104:name_start]

        stubs.append({
            'name': name,
            'header_start': header_start,
            'name_start': name_start,
            'data_end': null_pos + 1,
            'gap': len(gap_bytes),
            'gap_bytes': gap_bytes,
        })

        search_pos = null_pos + 1

    return stubs


# ============================================================================
# Replacement Builder
# ============================================================================

def _align_buffer(buf, alignment):
    """Pad a bytearray to the requested alignment."""
    if alignment <= 1:
        return
    pad = (-len(buf)) % alignment
    if pad:
        buf.extend(b'\x00' * pad)


STUB_ONLY_MODE = False  # When True, write empty stubs with correct names (diagnostic)
PATCH_ONLY_NAMES = None  # When set to a list, only patch these names (rest become stubs)
DONOR_ANIM_NAME = None  # When set, all patched entries use this source anim payload
DONOR_ASSET_NAME = None  # Default donor asset name from --donor-ff
DONOR_OVERRIDE_MAP = {}  # target anim name -> donor asset name
DONOR_CONTEXT = None     # Loaded donor ff context dict
DONOR_ALLOW_MISSING_STRINGS = False
DONOR_MISSING_STRINGS = set()

def _append_align(buf, alignment):
    if alignment <= 1:
        return
    while (len(buf) % alignment) != 0:
        buf.append(0)


def _read_indexed_strings(data, count, string_data_start):
    """Read indexed script strings in order from string_data_start."""
    out = []
    pos = string_data_start
    for _ in range(count):
        end = data.index(b'\x00', pos)
        out.append(data[pos:end].decode('ascii', errors='replace'))
        pos = end + 1
    return out


def _parse_donor_override_args(values):
    """Parse repeated --donor-override target=donor arguments."""
    out = {}
    for raw in values or []:
        if "=" not in raw:
            raise ValueError(f"Invalid --donor-override '{raw}' (expected target=donor)")
        target, donor = raw.split("=", 1)
        target = target.strip()
        donor = donor.strip()
        if not target or not donor:
            raise ValueError(f"Invalid --donor-override '{raw}' (empty target or donor)")
        out[target] = donor
    return out


def _load_donor_context(donor_ff, donor_zone_name, donor_asset_names, target_string_table):
    """Load and strict-parse donor assets from donor fastfile."""
    if strict_xanim is None:
        raise RuntimeError("strict_xanim_parser import failed; cannot use donor ff mode")

    _, donor_raw = decrypt_zone(donor_ff, donor_zone_name)
    donor_result = parse_string_table(donor_raw)
    donor_string_count = donor_result[1]
    donor_asset_data_offset = donor_result[3]
    donor_string_data_start = donor_result[5]
    donor_index_to_string = _read_indexed_strings(
        donor_raw,
        donor_string_count,
        donor_string_data_start
    )

    payloads = {}
    needed = sorted(set(donor_asset_names))
    for donor_name in needed:
        matches = strict_xanim.find_xanim_by_name(
            donor_raw,
            donor_name,
            min_offset=donor_asset_data_offset
        )
        if not matches:
            raise RuntimeError(f"Donor asset '{donor_name}' not found in donor ff")
        payloads[donor_name] = matches[0]

    return {
        "raw": donor_raw,
        "payloads": payloads,
        "donor_index_to_string": donor_index_to_string,
        "target_string_table": target_string_table,
    }


def _collect_required_donor_strings(donor_ctx, donor_asset_names):
    """Collect donor scriptstrings referenced by names/notify payloads."""
    required = set()
    donor_raw = donor_ctx["raw"]
    donor_index_to_string = donor_ctx["donor_index_to_string"]

    for donor_name in sorted(set(donor_asset_names)):
        parsed = donor_ctx["payloads"][donor_name]
        header = parsed["header"]
        sections = parsed["sections"]

        if header["names_ptr"] == PTR_FOLLOWING and "names" in sections:
            s = sections["names"]
            src = donor_raw[s["offset"]:s["offset"] + s["size"]]
            count = header["boneCount"][9]
            if len(src) == count * 2:
                for i in range(count):
                    donor_idx = struct.unpack_from("<H", src, i * 2)[0]
                    if donor_idx < len(donor_index_to_string):
                        required.add(donor_index_to_string[donor_idx])

        if header["notify_ptr"] == PTR_FOLLOWING and "notify" in sections:
            s = sections["notify"]
            src = donor_raw[s["offset"]:s["offset"] + s["size"]]
            count = header["notifyCount"]
            if len(src) == count * 8:
                for i in range(count):
                    off = i * 8
                    donor_idx = struct.unpack_from("<H", src, off)[0]
                    if donor_idx < len(donor_index_to_string):
                        required.add(donor_index_to_string[donor_idx])

    return sorted(required)


def _build_replacement_from_donor(target_name, donor_asset_name, gap_bytes):
    """Build replacement bytes using strict-parsed donor payload from donor ff."""
    del gap_bytes  # OAT comma gap is ignored; target name is always bare.
    if DONOR_CONTEXT is None:
        raise RuntimeError("DONOR_CONTEXT not loaded")
    if donor_asset_name not in DONOR_CONTEXT["payloads"]:
        raise RuntimeError(f"Donor asset '{donor_asset_name}' missing from DONOR_CONTEXT")

    donor_raw = DONOR_CONTEXT["raw"]
    donor_parsed = DONOR_CONTEXT["payloads"][donor_asset_name]
    donor_header = donor_parsed["header"]
    donor_sections = donor_parsed["sections"]
    donor_index_to_string = DONOR_CONTEXT["donor_index_to_string"]
    target_string_table = DONOR_CONTEXT["target_string_table"]
    align_mode = donor_parsed["options"]["align_mode"]

    # Start from donor header bytes; keep donor semantic fields/counters.
    header_off = donor_parsed["header_offset"]
    header = bytearray(donor_raw[header_off:header_off + 104])
    struct.pack_into("<I", header, 0x00, PTR_FOLLOWING)  # name is always following

    out = bytearray()

    # 1) name (target asset name)
    out.extend(target_name.encode("ascii") + b"\x00")

    # 2) names remap
    if donor_header["names_ptr"] == PTR_FOLLOWING:
        if align_mode == "standard":
            _append_align(out, 2)
        s = donor_sections["names"]
        src = donor_raw[s["offset"]:s["offset"] + s["size"]]
        count = donor_header["boneCount"][9]
        if len(src) != count * 2:
            raise RuntimeError(f"Donor names size mismatch for '{donor_asset_name}'")
        for i in range(count):
            donor_idx = struct.unpack_from("<H", src, i * 2)[0]
            if donor_idx >= len(donor_index_to_string):
                raise RuntimeError(f"Donor names idx out of range ({donor_idx}) in '{donor_asset_name}'")
            sname = donor_index_to_string[donor_idx]
            if sname not in target_string_table:
                if DONOR_ALLOW_MISSING_STRINGS:
                    DONOR_MISSING_STRINGS.add(sname)
                    out.extend(struct.pack("<H", 0))
                else:
                    raise RuntimeError(
                        f"Target zone missing script string '{sname}' needed by donor '{donor_asset_name}'"
                    )
            else:
                out.extend(struct.pack("<H", target_string_table[sname]))

    # 3) notify remap
    if donor_header["notify_ptr"] == PTR_FOLLOWING:
        if align_mode == "standard":
            _append_align(out, 4)
        s = donor_sections["notify"]
        src = donor_raw[s["offset"]:s["offset"] + s["size"]]
        count = donor_header["notifyCount"]
        if len(src) != count * 8:
            raise RuntimeError(f"Donor notify size mismatch for '{donor_asset_name}'")
        for i in range(count):
            off = i * 8
            donor_idx = struct.unpack_from("<H", src, off)[0]
            if donor_idx >= len(donor_index_to_string):
                raise RuntimeError(f"Donor notify idx out of range ({donor_idx}) in '{donor_asset_name}'")
            sname = donor_index_to_string[donor_idx]
            if sname not in target_string_table:
                if DONOR_ALLOW_MISSING_STRINGS:
                    DONOR_MISSING_STRINGS.add(sname)
                    out.extend(struct.pack("<H", 0))
                else:
                    raise RuntimeError(
                        f"Target zone missing notify script string '{sname}' from donor '{donor_asset_name}'"
                    )
            else:
                out.extend(struct.pack("<H", target_string_table[sname]))
            out.extend(src[off + 2:off + 8])  # preserve pad/time bytes

    # 4) deltaPart copy
    if donor_header["deltaPart_ptr"] == PTR_FOLLOWING:
        if align_mode == "standard":
            _append_align(out, 4)
        s = donor_sections["deltaPart"]
        out.extend(donor_raw[s["offset"]:s["offset"] + s["size"]])

    # 5) dataByte copy
    if donor_header["dataByte_ptr"] == PTR_FOLLOWING:
        s = donor_sections["dataByte"]
        out.extend(donor_raw[s["offset"]:s["offset"] + s["size"]])

    # 6) dataShort copy
    if donor_header["dataShort_ptr"] == PTR_FOLLOWING:
        if align_mode == "standard":
            _append_align(out, 2)
        s = donor_sections["dataShort"]
        out.extend(donor_raw[s["offset"]:s["offset"] + s["size"]])

    # 7) dataInt copy
    if donor_header["dataInt_ptr"] == PTR_FOLLOWING:
        if align_mode == "standard":
            _append_align(out, 4)
        s = donor_sections["dataInt"]
        out.extend(donor_raw[s["offset"]:s["offset"] + s["size"]])

    # 8) randomDataShort copy
    if donor_header["randomDataShort_ptr"] == PTR_FOLLOWING:
        if align_mode == "standard":
            _append_align(out, 2)
        s = donor_sections["randomDataShort"]
        out.extend(donor_raw[s["offset"]:s["offset"] + s["size"]])

    # 9) randomDataByte copy
    if donor_header["randomDataByte_ptr"] == PTR_FOLLOWING:
        s = donor_sections["randomDataByte"]
        out.extend(donor_raw[s["offset"]:s["offset"] + s["size"]])

    # 10) randomDataInt copy
    if donor_header["randomDataInt_ptr"] == PTR_FOLLOWING:
        if align_mode == "standard":
            _append_align(out, 4)
        s = donor_sections["randomDataInt"]
        out.extend(donor_raw[s["offset"]:s["offset"] + s["size"]])

    # 11) indices copy
    if donor_header["indices_ptr"] == PTR_FOLLOWING:
        idx_elem = 1 if donor_header["numframes"] < 256 else 2
        if align_mode == "standard":
            _append_align(out, idx_elem)
        s = donor_sections["indices"]
        out.extend(donor_raw[s["offset"]:s["offset"] + s["size"]])

    return bytes(header) + bytes(out)


def build_replacement_data(anim, string_table, gap_bytes, target_name=None):
    """Build replacement XAnimParts binary data for a single animation.

    Only includes bones present in the zone's string table (model bones).
    Uses frame 0 static pose data.

    Returns the complete replacement bytes: header + gap + name + arrays.
    """
    name = target_name or anim['name']
    parts = anim['parts']
    framerate = max(1.0, float(anim.get('framerate', 30)))

    # In stub-only mode, write empty stubs with correct names (no data)
    if STUB_ONLY_MODE:
        return _build_empty_stub(name, gap_bytes, framerate)

    # If only specific names should get real data, stub the rest
    if PATCH_ONLY_NAMES is not None and name not in PATCH_ONLY_NAMES:
        return _build_empty_stub(name, gap_bytes, framerate)

    # Filter to model bones (those in string table)
    included = []
    for orig_idx, bone_name in enumerate(parts):
        if bone_name in string_table:
            included.append((orig_idx, bone_name))

    num_bones = len(included)
    if num_bones == 0:
        print(f"    WARNING: No model bones found for '{name}', writing stub")
        return _build_empty_stub(name, gap_bytes, framerate)

    # Get frame 0 data
    frame0 = {}
    if anim['frames']:
        frame0 = anim['frames'][min(anim['frames'].keys())]

    # xanim_export data is already in T6-native LHC coordinates.
    # Write values directly to the zone — NO coordinate conversion needed.
    # (LHC->RHC is only for GLB files, not for zone binary data.)

    # Build bone data arrays
    bone_string_indices = []
    rot_quats_i16 = []
    trans_vec_f32 = []
    trans_bone_ids = []

    for new_idx, (orig_idx, bone_name) in enumerate(included):
        bone_string_indices.append(string_table[bone_name])

        bone = frame0.get(orig_idx)
        if bone:
            off = [float(v) for v in bone.get('offset', [0.0, 0.0, 0.0])[:3]]
            rot_m = bone.get('rot', [[1, 0, 0], [0, 1, 0], [0, 0, 1]])
            # Transpose: xanim_export rows are basis vectors (R^T)
            rot_m_t = [
                [rot_m[0][0], rot_m[1][0], rot_m[2][0]],
                [rot_m[0][1], rot_m[1][1], rot_m[2][1]],
                [rot_m[0][2], rot_m[1][2], rot_m[2][2]],
            ]
            quat = rotation_matrix_to_quat(rot_m_t)
        else:
            off = [0.0, 0.0, 0.0]
            quat = [0.0, 0.0, 0.0, 1.0]

        # Emit static frame-0 rotation + translation channels.
        rot_quats_i16.extend([quat_to_int16(c) for c in quat])
        trans_vec_f32.extend([float(v) for v in off[:3]])
        trans_bone_ids.append(new_idx & 0xFF)

    data_byte_count = len(trans_bone_ids)
    data_short_count = len(rot_quats_i16)
    data_int_count = len(trans_vec_f32)

    # Build 104-byte header
    header = bytearray(104)
    struct.pack_into('<I', header, 0x00, PTR_FOLLOWING)       # name
    struct.pack_into('<H', header, 0x04, data_byte_count)     # dataByteCount
    struct.pack_into('<H', header, 0x06, data_short_count)    # dataShortCount
    struct.pack_into('<H', header, 0x08, data_int_count)      # dataIntCount
    struct.pack_into('<H', header, 0x0A, 0)                   # randomDataByteCount
    struct.pack_into('<H', header, 0x0C, 0)                   # randomDataIntCount
    struct.pack_into('<H', header, 0x0E, 2)                   # numframes (min 2 — engine divides by numframes-1)

    header[0x10] = 0  # bLoop
    header[0x11] = 0  # bDelta
    header[0x12] = 0  # bDelta3D
    header[0x13] = 0  # bLeftHandGripIK
    struct.pack_into('<I', header, 0x14, 0)  # streamedFileSize

    # boneCount categories (cumulative)
    header[0x18 + 4] = num_bones   # NormalStaticRotated
    header[0x18 + 7] = num_bones   # StaticTranslated
    header[0x18 + 9] = num_bones   # TotalBoneCount

    header[0x22] = 0   # notifyCount
    header[0x23] = 2   # assetType (2 = real animation, matches vanilla T6 XAnimParts)
    header[0x24] = 0   # isDefault (NOT default — has real data)

    struct.pack_into('<I', header, 0x28, 0)              # randomDataShortCount
    struct.pack_into('<I', header, 0x2C, 0)              # indexCount
    struct.pack_into('<f', header, 0x30, framerate)       # framerate
    struct.pack_into('<f', header, 0x34, 1.0)             # frequency
    struct.pack_into('<f', header, 0x38, 0.0)             # primedLength
    struct.pack_into('<f', header, 0x3C, 0.0)             # loopEntryTime

    # Pointer fields
    struct.pack_into('<I', header, 0x40, PTR_FOLLOWING)   # names
    struct.pack_into('<I', header, 0x44, PTR_FOLLOWING if data_byte_count > 0 else PTR_NULL)
    struct.pack_into('<I', header, 0x48, PTR_FOLLOWING if data_short_count > 0 else PTR_NULL)
    struct.pack_into('<I', header, 0x4C, PTR_FOLLOWING if data_int_count > 0 else PTR_NULL)
    struct.pack_into('<I', header, 0x50, PTR_NULL)        # randomDataShort
    struct.pack_into('<I', header, 0x54, PTR_NULL)        # randomDataByte
    struct.pack_into('<I', header, 0x58, PTR_NULL)        # randomDataInt
    struct.pack_into('<I', header, 0x5C, PTR_NULL)        # indices
    struct.pack_into('<I', header, 0x60, PTR_NULL)        # notify
    # Keep deltaPart absent for generated frame-0 static poses.
    # Earlier stable idle-only builds used PTR_NULL here.
    struct.pack_into('<I', header, 0x64, PTR_NULL)        # deltaPart

    # Build pointer-resolved data in zone stream order.
    # Block management (TEMP/VIRTUAL) is hard-coded in the zone loading template,
    # NOT encoded as stream bytes. Data sections are packed contiguously.
    #
    # IMPORTANT: Do NOT include gap_bytes (the comma from OAT's zone source format
    # "xanim,,name"). The comma is an OAT artifact, not part of the asset name.
    # Including it makes the name ",vm_thunder_gun_idle" which doesn't match the
    # weapon file reference "vm_thunder_gun_idle".
    pointer_data = bytearray()

    # 1) name string (NO comma prefix — just the bare asset name)
    pointer_data.extend(name.encode('ascii') + b'\x00')

    # 2) names (script string indices, uint16 each)
    for idx in bone_string_indices:
        pointer_data.extend(struct.pack('<H', idx))

    # 3) notify (none)
    # 4) dataByte (translation bone IDs, uint8 each)
    if data_byte_count > 0:
        _append_align(pointer_data, 1)
        pointer_data.extend(bytes(trans_bone_ids))

    # 5) dataShort (static quaternions, int16 each)
    if data_short_count > 0:
        for q in rot_quats_i16:
            pointer_data.extend(struct.pack('<h', q))

    # 6) dataInt (static translations as float32 bit-patterns)
    if data_int_count > 0:
        for v in trans_vec_f32:
            pointer_data.extend(struct.pack('<f', v))

    return bytes(header) + bytes(pointer_data)


def _build_empty_stub(name, gap_bytes, framerate):
    """Build an empty stub (fallback if no bones match)."""
    header = bytearray(104)
    struct.pack_into('<I', header, 0x00, PTR_FOLLOWING)
    struct.pack_into('<f', header, 0x30, framerate)
    struct.pack_into('<f', header, 0x34, 1.0)
    header[0x24] = 0  # isDefault=0 matches OAT DefaultAssetCreator
    # No gap_bytes — the comma is an OAT artifact, not part of the name
    vdata = name.encode('ascii') + b'\x00'
    return bytes(header) + vdata


# ============================================================================
# Zone Patching
# ============================================================================

def patch_zone(data, stubs, anims_by_name, string_table):
    """Replace empty xanim stubs with real data. Returns (patched, bytes_added)."""
    # Process in reverse order to preserve offsets
    sorted_stubs = sorted(stubs, key=lambda s: s['header_start'], reverse=True)

    patched = bytearray(data)
    total_added = 0
    patched_count = 0

    for stub in sorted_stubs:
        name = stub['name']
        if PATCH_ONLY_NAMES is not None and name not in PATCH_ONLY_NAMES:
            # Keep non-selected entries as clean empty stubs (name-correct).
            replacement = _build_empty_stub(name, stub['gap_bytes'], 30.0)
        elif DONOR_CONTEXT is not None:
            donor_name = DONOR_OVERRIDE_MAP.get(name, DONOR_ASSET_NAME)
            try:
                replacement = _build_replacement_from_donor(name, donor_name, stub['gap_bytes'])
            except Exception as e:
                print(f"    SKIP '{name}' - donor build failed: {e}")
                continue
        else:
            if name not in anims_by_name:
                print(f"    SKIP '{name}' - no xanim_export file")
                continue

            source_name = DONOR_ANIM_NAME if DONOR_ANIM_NAME else name
            if source_name not in anims_by_name:
                print(f"    SKIP '{name}' - source anim '{source_name}' not found")
                continue

            anim = anims_by_name[source_name]
            replacement = build_replacement_data(
                anim,
                string_table,
                stub['gap_bytes'],
                target_name=name
            )

        old_start = stub['header_start']
        old_end = stub['data_end']
        old_size = old_end - old_start
        new_size = len(replacement)
        delta = new_size - old_size
        total_added += delta
        patched_count += 1

        patched[old_start:old_end] = replacement
        print(f"    '{name}': {old_size} -> {new_size} bytes (delta {delta:+d})")

    # Update XFile header
    if total_added != 0:
        old_total = struct.unpack_from('<I', patched, 0)[0]
        new_total = old_total + total_added
        struct.pack_into('<I', patched, 0, new_total)

        # XAnimParts pointer payload lives in VIRTUAL at load time.
        # Add stream delta plus safety for loader-only alignment growth.
        virtual_off = 8 + BLOCK_VIRTUAL * 4
        old_virtual = struct.unpack_from('<I', patched, virtual_off)[0]
        virtual_align_extra = VIRTUAL_ALIGN_SAFETY_BASE + (patched_count * VIRTUAL_ALIGN_SAFETY_PER_STUB)
        new_virtual = old_virtual + total_added + virtual_align_extra
        struct.pack_into('<I', patched, virtual_off, new_virtual)

        print(f"\n  XFile header updated:")
        print(f"    totalSize: {old_total} -> {new_total} ({total_added:+d})")
        print(f"    VIRTUAL:   {old_virtual} -> {new_virtual} (+{total_added} stream, +{virtual_align_extra} align)")

    return bytes(patched), total_added, patched_count


def write_patched_zone(raw_data, zone_name, magic, output_path):
    """Re-encrypt and write the patched zone file."""
    writer = XChunkWriter(zone_name)
    writer.write_data(raw_data)
    encrypted = writer.get_output()

    with open(output_path, 'wb') as f:
        f.write(magic)
        f.write(struct.pack('<I', T6_ZONE_VERSION))
        f.write(encrypted)
        # Pad to 0x40 alignment
        pad = 0x40 - (f.tell() % 0x40)
        if pad < 0x40:
            pad += 0x40
        f.write(b'\x00' * pad)

    return os.path.getsize(output_path)


# ============================================================================
# Verification
# ============================================================================

def verify_patched_zone(ff_path, zone_name, name_prefix):
    """Decrypt patched zone and verify no empty stubs remain for the prefix."""
    print(f"\nVerifying patched zone...")
    _, data = decrypt_zone(ff_path, zone_name)
    print(f"  Decrypted {len(data):,} bytes")
    result = parse_string_table(data)
    asset_data_offset = result[3]
    remaining = find_empty_xanim_stubs(data, name_prefix, min_search_offset=asset_data_offset)

    if not remaining:
        print(f"  Verification: 0 empty stubs remain for prefix '{name_prefix}'")
        return True

    print(f"  Verification FAILED: {len(remaining)} empty stubs remain:")
    for stub in remaining[:16]:
        print(f"    '{stub['name']}' at 0x{stub['header_start']:X}")
    if len(remaining) > 16:
        print(f"    ... and {len(remaining) - 16} more")
    return False


# ============================================================================
# Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Patch empty XAnimParts stubs in a T6 zone with real animation data."
    )
    parser.add_argument(
        "--input-ff",
        required=True,
        help="Path to the OAT-built .ff zone file to patch.",
    )
    parser.add_argument(
        "--zone-name",
        required=True,
        help="Zone name (used for encryption key derivation).",
    )
    parser.add_argument(
        "--xanim-dir",
        required=True,
        help="Directory containing xanim_export files.",
    )
    parser.add_argument(
        "--xanim-pattern",
        default="vm_thunder_gun_*.xanim_export",
        help="Glob pattern for xanim_export files.",
    )
    parser.add_argument(
        "--name-prefix",
        default="vm_thunder_gun_",
        help="Name prefix to match XAnimParts stubs in the zone.",
    )
    parser.add_argument(
        "--output-ff",
        default=None,
        help="Output path (default: overwrite input).",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        default=True,
        help="Verify the patched zone after writing.",
    )
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="Skip verification.",
    )
    parser.add_argument(
        "--stub-only",
        action="store_true",
        help="Write empty stubs with correct names (diagnostic mode).",
    )
    parser.add_argument(
        "--patch-only",
        nargs="+",
        default=None,
        help="Only patch these animation names with real data (rest become stubs).",
    )
    parser.add_argument(
        "--donor-anim",
        default=None,
        help="Use one source animation payload for all patched entries (keeps each target name).",
    )
    parser.add_argument(
        "--donor-ff",
        default=None,
        help="Optional donor fastfile path for strict donor-blob replacement mode.",
    )
    parser.add_argument(
        "--donor-zone-name",
        default=None,
        help="Zone name for donor ff decryption hash chain.",
    )
    parser.add_argument(
        "--donor-asset",
        default=None,
        help="Default donor asset name from donor ff (used for all targets unless overridden).",
    )
    parser.add_argument(
        "--donor-override",
        action="append",
        default=[],
        help="Per-target donor override in form target_name=donor_asset. Repeatable.",
    )
    parser.add_argument(
        "--donor-allow-missing-strings",
        action="store_true",
        help="Allow donor scriptstring names missing from target zone (maps to scriptstring index 0).",
    )
    args = parser.parse_args()

    global STUB_ONLY_MODE, PATCH_ONLY_NAMES, DONOR_ANIM_NAME
    global DONOR_ASSET_NAME, DONOR_OVERRIDE_MAP, DONOR_CONTEXT
    global DONOR_ALLOW_MISSING_STRINGS, DONOR_MISSING_STRINGS
    PATCH_ONLY_NAMES = args.patch_only
    STUB_ONLY_MODE = args.stub_only
    DONOR_ANIM_NAME = args.donor_anim
    DONOR_ASSET_NAME = args.donor_asset
    DONOR_ALLOW_MISSING_STRINGS = args.donor_allow_missing_strings
    DONOR_MISSING_STRINGS = set()

    output_ff = args.output_ff or args.input_ff

    try:
        DONOR_OVERRIDE_MAP = _parse_donor_override_args(args.donor_override)
    except ValueError as e:
        print(f"  ERROR: {e}")
        return False

    donor_ff_mode = bool(args.donor_ff or args.donor_zone_name or args.donor_asset or DONOR_OVERRIDE_MAP)
    if donor_ff_mode:
        if not (args.donor_ff and args.donor_zone_name and args.donor_asset):
            print("  ERROR: donor ff mode requires --donor-ff, --donor-zone-name, and --donor-asset")
            return False
        if DONOR_ANIM_NAME:
            print("  ERROR: choose either --donor-anim or donor ff mode, not both")
            return False

    print("=" * 70)
    print("T6 Zone XAnimParts Patcher")
    print("=" * 70)
    print(f"  Input:   {args.input_ff}")
    print(f"  Output:  {output_ff}")
    print(f"  Zone:    {args.zone_name}")
    print(f"  Prefix:  {args.name_prefix}")
    if DONOR_ANIM_NAME:
        print(f"  Donor:   {DONOR_ANIM_NAME}")
    if donor_ff_mode:
        print(f"  DonorFF: {args.donor_ff}")
        print(f"  DonorZN: {args.donor_zone_name}")
        print(f"  DonorAs: {args.donor_asset}")
        if DONOR_OVERRIDE_MAP:
            print(f"  Overrides: {len(DONOR_OVERRIDE_MAP)} entries")
        if DONOR_ALLOW_MISSING_STRINGS:
            print("  Missing donor scriptstrings: allowed (fallback index 0)")
    print()

    # Step 1: Decrypt
    print("Step 1: Decrypting zone...")
    magic, raw = decrypt_zone(args.input_ff, args.zone_name)
    print(f"  Decrypted {len(raw):,} bytes (magic: {magic})")

    # Step 2: Parse xanim_export files first (need bone names before expanding)
    print("\nStep 2: Parsing xanim_export files...")
    pattern = os.path.join(args.xanim_dir, args.xanim_pattern)
    files = sorted(glob.glob(pattern))
    if not files:
        print(f"  ERROR: No files matching {pattern}")
        return False

    anims_by_name = {}
    for fp in files:
        anim = parse_xanim_export(fp)
        anims_by_name[anim['name']] = anim
    print(f"  {len(files)} xanim_export files parsed")
    if DONOR_ANIM_NAME and DONOR_ANIM_NAME not in anims_by_name:
        print(f"  ERROR: donor anim '{DONOR_ANIM_NAME}' not found in parsed xanim exports")
        return False

    # Collect ALL unique bone names across all animations
    all_bone_names = set()
    for anim in anims_by_name.values():
        all_bone_names.update(anim['parts'])
    print(f"  {len(all_bone_names)} unique bone names across all animations")

    # Step 3: Parse string table
    print("\nStep 3: Parsing string table...")
    (string_table, string_count, asset_count, asset_data_offset,
     ptr_array_start, string_data_start, string_data_end) = parse_string_table(raw)
    print(f"  {len(string_table)} unique strings parsed")

    # Determine which bone names are missing
    missing_bones = sorted(b for b in all_bone_names if b not in string_table)
    existing_bones = sorted(b for b in all_bone_names if b in string_table)
    print(f"  {len(existing_bones)} bone names already in string table")
    print(f"  {len(missing_bones)} bone names MISSING from string table")

    # Step 4: Skip string table expansion — inserting bytes mid-stream corrupts
    # scriptparsetree assets.  The existing string table already contains all gun
    # bone names (added by OAT when writing the XModel).  Missing bones are
    # hand/finger/camera bones from viewmodel_hands which we don't include.
    print(f"\nStep 4: Using existing string table only ({len(existing_bones)} model bones)")
    if missing_bones:
        print(f"  Skipping {len(missing_bones)} hand/finger/camera bones not in string table")

    # Report bone coverage using the largest animation
    largest_anim = max(anims_by_name.values(), key=lambda a: len(a['parts']))
    matched = [b for b in largest_anim['parts'] if b in string_table]
    unmatched = [b for b in largest_anim['parts'] if b not in string_table]
    print(f"\n  Bone coverage ({largest_anim['name']}, {len(largest_anim['parts'])} bones):")
    print(f"    {len(matched)} matched, {len(unmatched)} unmatched")

    # Optional donor-ff context for strict donor-blob replacement mode.
    if donor_ff_mode:
        donor_asset_names = [DONOR_ASSET_NAME] + list(DONOR_OVERRIDE_MAP.values())
        print(f"\nStep 4b: Loading donor ff context ({len(set(donor_asset_names))} donor assets)...")
        try:
            DONOR_CONTEXT = _load_donor_context(
                args.donor_ff,
                args.donor_zone_name,
                donor_asset_names,
                string_table
            )
        except Exception as e:
            print(f"  ERROR: failed loading donor ff context: {e}")
            return False
        print("  Donor ff context loaded successfully")

        required_donor_strings = _collect_required_donor_strings(DONOR_CONTEXT, donor_asset_names)
        missing_donor_strings = sorted(s for s in required_donor_strings if s not in string_table)
        if missing_donor_strings:
            if DONOR_ALLOW_MISSING_STRINGS:
                print(f"  Donor strings missing in target zone: {len(missing_donor_strings)}"
                      " (fallback index 0 enabled)")
            else:
                print(f"  Expanding target string table for {len(missing_donor_strings)} donor strings...")
                raw, _added = expand_string_table(
                    raw,
                    missing_donor_strings,
                    ptr_array_start,
                    string_data_end,
                    string_count
                )
                # Re-parse after insertion to refresh offsets/tables.
                (string_table, string_count, asset_count, asset_data_offset,
                 ptr_array_start, string_data_start, string_data_end) = parse_string_table(raw)
                print(f"  String table expanded; now {string_count} strings total")
                DONOR_CONTEXT["target_string_table"] = string_table

    # Step 5: Find empty stubs
    print(f"\nStep 5: Finding empty XAnimParts stubs (prefix='{args.name_prefix}')...")
    print(f"  Searching from offset 0x{asset_data_offset:X}")
    stubs = find_empty_xanim_stubs(raw, args.name_prefix, min_search_offset=asset_data_offset)
    print(f"  Found {len(stubs)} empty stubs:")
    for s in stubs:
        print(f"    '{s['name']}' at 0x{s['header_start']:X} (gap={s['gap']} bytes,"
              f" stub_size={s['data_end'] - s['header_start']})")

    if not stubs:
        print("\n  No empty stubs found — nothing to patch!")
        return True

    # Step 6: Patch stubs with real animation data
    print(f"\nStep 6: Patching {len(stubs)} stubs...")
    patched, bytes_added, patched_count = patch_zone(raw, stubs, anims_by_name, string_table)
    print(f"\n  Patched {patched_count}/{len(stubs)} animations, added {bytes_added:,} bytes")
    if DONOR_CONTEXT is not None and DONOR_MISSING_STRINGS:
        print(f"  Donor mode fallback: {len(DONOR_MISSING_STRINGS)} missing scriptstrings mapped to index 0")
        sample = sorted(DONOR_MISSING_STRINGS)[:8]
        print(f"    sample: {sample}")

    # Step 7: Re-encrypt and write
    print(f"\nStep 7: Re-encrypting and writing...")
    file_size = write_patched_zone(patched, args.zone_name, magic, output_ff)
    print(f"  Written: {output_ff} ({file_size:,} bytes)")

    # Step 8: Verify
    if not args.no_verify:
        ok = verify_patched_zone(output_ff, args.zone_name, args.name_prefix)
        if ok:
            print("\n  SUCCESS: All animations patched correctly!")
        else:
            print("\n  WARNING: Some animations still empty — check output above")
        return ok

    return True


if __name__ == "__main__":
    ok = main()
    raise SystemExit(0 if ok else 1)
