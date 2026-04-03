#!/usr/bin/env python3
"""
Compile xanim_export text files into a T6 .ff zone file.

Creates a minimal zone containing XAnimParts assets that OAT can load
via --load when building the main zone.

T6 Zone format:
  - 12-byte header (magic + version)
  - XChunk stream: raw deflate compressed, Salsa20 encrypted
  - 4 streams round-robin, SHA-1 hash chain for IV derivation
"""
import struct
import zlib
import hashlib
import os
import re
import glob
import math
import argparse
import copy
import json
from Crypto.Cipher import Salsa20

# Prefer the proven XChunk writer implementation used by patch_zone_xanims.
try:
    from patch_zone_xanims import XChunkWriter as SharedXChunkWriter  # type: ignore
except Exception:
    SharedXChunkWriter = None

try:
    import strict_xanim_parser as strict_xanim  # type: ignore
except Exception:
    strict_xanim = None

try:
    from patch_zone_xanims import decrypt_zone as donor_decrypt_zone  # type: ignore
    from patch_zone_xanims import parse_string_table as donor_parse_string_table  # type: ignore
except Exception:
    donor_decrypt_zone = None
    donor_parse_string_table = None

# ============================================================================
# T6 Zone Constants
# ============================================================================

T6_ZONE_MAGIC_UNSIGNED = b"TAffu100"  # Unsigned encrypted
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
FASTFILE_HEADER_SIZE = 12      # magic(8) + version(4)

ASSET_TYPE_XANIMPARTS = 4
XFILE_BLOCK_COUNT = 8  # T6 has 8 block types

# T6 Block indices:
# 0=TEMP, 1=RUNTIME_VIRTUAL, 2=RUNTIME_PHYSICAL,
# 3=DELAY_VIRTUAL, 4=DELAY_PHYSICAL,
# 5=VIRTUAL (INSERT_BLOCK), 6=PHYSICAL, 7=STREAMER_RESERVE
BLOCK_TEMP = 0
BLOCK_VIRTUAL = 5  # NOT 3!

# Pointer encoding (32-bit):
# 0xFFFFFFFF = PTR_FOLLOWING (data follows in stream)
# 0xFFFFFFFE = PTR_INSERT (reuse previously cached data)
# 0x00000000 = PTR_NULL
PTR_FOLLOWING = 0xFFFFFFFF
PTR_NULL = 0x00000000

# Emit modes:
#   static_pose                -> write real static rot/trans channels from frame 0
#   donor_template_static_pose -> keep donor header/section semantics and fill
#                                 those stable slots with source frame-0 data
#   donor_semantic_static_pose -> keep donor-like runtime semantics but rebuild
#                                 names/category layout for the target rig
#   stub                       -> write no channel data (diagnostic mode only)
#   donor_clone                -> copy known-good donor XAnimParts payloads (real curves)
#   bo3_frames                 -> emit BO3-driven keyframes for selected anims (idle first), fallback for others
EMIT_MODE = "static_pose"
# Diagnostics: when True, force zero-bone output regardless of source anim.
DIAG_ZERO_BONES = False
FORCE_IDENTITY_POSE = False
# Stub/default toggles
STUB_NUMFRAMES = 0
STUB_IS_DEFAULT = 1
BONE_COUNT_PROFILE = "cumulative_none"
NEUTRALIZE_BONES = set()

# Donor/oracle clone mode:
# Build vm_thunder_gun_* assets with known-good T6 dynamic payloads so we can
# validate real (non-stub) XAnimParts lane deterministically before full BO3
# per-frame conversion lands.
DONOR_FF = None
DONOR_ZONE_NAME = None
DONOR_DEFAULT_ASSET = "viewmodel_ak74u_t6_idle"
DONOR_OVERRIDE_MAP = {}
DONOR_CONTEXT = None
DONOR_FALLBACK_IDLE = True
DONOR_MAP_HITS = 0
DONOR_MAP_FALLBACKS = 0
REQUIRE_NO_DONOR_FALLBACK = False
BO3_FRAMES_TARGETS = {"vm_thunder_gun_idle"}
BO3_FRAMES_FALLBACK_MODE = "donor_clone"
BO3_ROOT_BONE_PRIORITY = [
    "tag_weapon_right",
    "j_mainroot",
    "tag_player",
    "tag_camera",
    "tag_origin",
]
BO3_NONROOT_BONE_PRIORITY = [
    "j_gun",
    "j_bolt",
    "j_clip",
    "j_stripper",
    "j_switch",
    "j_pump",
    "j_drum",
    "j_mag",
]
BO3_MOTION_BONE_REPORT_TOP = 3
BO3_IDLE_DIAG_BONE = ""
BO3_IDLE_DIAG_TRANSLATE = [0.0, 0.0, 0.0]
BO3_IDLE_DIAG_FREQUENCY = 0.0
BO3_IDLE_DIAG_STATIC_BONE = ""
BO3_IDLE_DIAG_STATIC_TRANSLATE = [0.0, 0.0, 0.0]
BO3_DISABLE_NOTIFY = os.environ.get("ROGUE_BO3_DISABLE_NOTIFY", "0") not in ("0", "false", "False", "")
FORCE_LOOP_ANIM_NAMES = {
    str(token).strip().lower()
    for token in str(os.environ.get("ROGUE_XANIM_FORCE_LOOP_NAMES", "") or "").split(",")
    if str(token).strip()
}
try:
    BO3_FORCE_ASSETTYPE = int(str(os.environ.get("ROGUE_BO3_FORCE_ASSETTYPE", "0") or "0").strip() or "0")
except Exception:
    BO3_FORCE_ASSETTYPE = 0
THUNDER_TO_AK74U_SUFFIX = {
    "idle": "idle",
    "fire": "fire",
    "fire_ads": "ads_fire",
    "reload_empty": "reload_empty",
    "pullout": "pullout",
    "putaway": "putaway",
    "first_raise": "first_raise",
    "pullout_quick": "pullout_quick",
    "putaway_quick": "putaway_quick",
    "sprint_in": "sprint_in",
    "sprint_loop": "sprint_loop",
    "sprint_out": "sprint_out",
    "ads_base_up": "ads_up",
    "ads_base_down": "ads_down",
    "crawl_in": "crawl_in",
    "crawl_f": "crawl_forward",
    "crawl_b": "crawl_back",
    "crawl_r": "crawl_right",
    "crawl_l": "crawl_left",
    "crawl_out": "crawl_out",
    "slide_air_in": "d2p_in",
    "slide_in": "d2p_in",
    "slide_loop": "d2p_loop",
    "slide_out": "d2p_out",
    # No direct AK74U donor states; map to close movement states as oracle fallback.
    "walk_f": "sprint_loop",
    "jump": "sprint_in",
    "jump_land": "sprint_out",
    "fall": "sprint_loop",
}

# Required vm states to keep T6 weapon state machine from transitioning into null anims.
REQUIRED_THUNDER_ANIMS = [
    "vm_thunder_gun_idle",
    "vm_thunder_gun_fire",
    "vm_thunder_gun_fire_ads",
    "vm_thunder_gun_reload_empty",
    "vm_thunder_gun_pullout",
    "vm_thunder_gun_putaway",
    "vm_thunder_gun_first_raise",
    "vm_thunder_gun_pullout_quick",
    "vm_thunder_gun_putaway_quick",
    "vm_thunder_gun_sprint_in",
    "vm_thunder_gun_sprint_loop",
    "vm_thunder_gun_sprint_out",
    "vm_thunder_gun_ads_base_up",
    "vm_thunder_gun_ads_base_down",
    "vm_thunder_gun_crawl_in",
    "vm_thunder_gun_crawl_f",
    "vm_thunder_gun_crawl_b",
    "vm_thunder_gun_crawl_r",
    "vm_thunder_gun_crawl_l",
    "vm_thunder_gun_crawl_out",
    "vm_thunder_gun_slide_air_in",
    "vm_thunder_gun_slide_in",
    "vm_thunder_gun_slide_loop",
    "vm_thunder_gun_slide_out",
    "vm_thunder_gun_walk_f",
    "vm_thunder_gun_jump",
    "vm_thunder_gun_jump_land",
    "vm_thunder_gun_fall",
]


# ============================================================================
# XChunk Writer with Salsa20 Hash Chain
# ============================================================================

class XChunkWriter:
    """Implements T6's XChunk stream format with Salsa20 encryption."""

    def __init__(self, zone_name):
        self.zone_name = zone_name[:31]  # Truncate to 31 chars
        self.current_stream = 0
        self.block_indices = [0] * STREAM_COUNT
        # Match loader accounting: chunk stream starts after 12-byte ff header.
        self.vanilla_buffer_offset = FASTFILE_HEADER_SIZE
        self.output = bytearray()

        # Initialize hash block chain from zone name
        total_size = BLOCK_HASHES_COUNT * STREAM_COUNT * SHA1_HASH_SIZE
        self.block_hashes = bytearray(total_size)

        name_bytes = self.zone_name.encode('ascii')
        name_len = len(name_bytes)
        name_offset = 0
        for i in range(0, total_size, 4):
            ch = name_bytes[name_offset % name_len]
            remaining = min(4, total_size - i)
            for j in range(remaining):
                self.block_hashes[i + j] = ch
            name_offset += 1

    def _get_hash_block(self, stream_num):
        """Get the current hash block for a stream."""
        block_idx = self.block_indices[stream_num]
        offset = block_idx * STREAM_COUNT * SHA1_HASH_SIZE + stream_num * SHA1_HASH_SIZE
        return self.block_hashes[offset:offset + SHA1_HASH_SIZE]

    def _set_hash_block(self, stream_num, block_idx, data):
        """Set a hash block for a stream."""
        offset = block_idx * STREAM_COUNT * SHA1_HASH_SIZE + stream_num * SHA1_HASH_SIZE
        self.block_hashes[offset:offset + SHA1_HASH_SIZE] = data[:SHA1_HASH_SIZE]

    def _advance_stream(self, stream_num, plaintext_data):
        """Advance the hash chain after processing a chunk."""
        # SHA-1 hash the plaintext (post-compression, pre-encryption)
        sha1_hash = hashlib.sha1(plaintext_data).digest()

        # Advance block index
        current_idx = self.block_indices[stream_num]
        next_idx = (current_idx + 1) % BLOCK_HASHES_COUNT
        self.block_indices[stream_num] = next_idx

        # XOR the NEXT hash block with the SHA-1 hash
        next_block = bytearray(self._get_hash_block(stream_num))
        for i in range(min(SHA1_HASH_SIZE, len(sha1_hash))):
            next_block[i] ^= sha1_hash[i]
        self._set_hash_block(stream_num, next_idx, bytes(next_block))

    def write_chunk(self, data):
        """Write a single chunk of data through the XChunk pipeline."""
        # Step 1: Compress with raw deflate (no zlib header)
        compress_obj = zlib.compressobj(9, zlib.DEFLATED, -15)
        compressed = compress_obj.compress(data)
        compressed += compress_obj.flush()

        # Step 2: Get IV from current hash block for this stream
        hash_block = self._get_hash_block(self.current_stream)
        nonce = bytes(hash_block[:8])  # First 8 bytes as nonce

        # Step 3: Encrypt with Salsa20
        cipher = Salsa20.new(key=SALSA20_KEY, nonce=nonce)
        encrypted = cipher.encrypt(compressed)

        # Step 4: Advance hash chain with the compressed (pre-encryption) data
        self._advance_stream(self.current_stream, compressed)

        # Step 5: Handle 512KB vanilla buffer alignment
        chunk_size_bytes = struct.pack('<I', len(encrypted))
        if self.vanilla_buffer_offset + 4 > VANILLA_BUFFER_SIZE:
            # Pad to next 512KB boundary
            padding = VANILLA_BUFFER_SIZE - self.vanilla_buffer_offset
            self.output.extend(b'\x00' * padding)
            self.vanilla_buffer_offset = 0

        # Write chunk: [4-byte size][encrypted data]
        self.output.extend(chunk_size_bytes)
        self.vanilla_buffer_offset += 4
        self.output.extend(encrypted)
        self.vanilla_buffer_offset += len(encrypted)
        self.vanilla_buffer_offset %= VANILLA_BUFFER_SIZE

        # Advance to next stream (round-robin)
        self.current_stream = (self.current_stream + 1) % STREAM_COUNT

    def write_data(self, raw_data):
        """Write raw data through the XChunk pipeline, splitting into chunks."""
        offset = 0
        while offset < len(raw_data):
            chunk_size = min(XCHUNK_MAX_WRITE, len(raw_data) - offset)
            chunk = raw_data[offset:offset + chunk_size]
            self.write_chunk(chunk)
            offset += chunk_size

    def get_output(self):
        """Get the complete encrypted stream."""
        return bytes(self.output)


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
        'frames': {},  # frame_num -> {part_idx -> {offset, rot_matrix}}
        'local_basis_frames': {},
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
        elif line.startswith('NUMFRAMES'):
            anim['numframes'] = int(line.split()[1])
        elif line.startswith('NUMKEYS'):
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
                        part_idx = int(pm.group(1))
                        bone = {'offset': [0,0,0], 'rot': [[1,0,0],[0,1,0],[0,0,1]]}
                        for _ in range(5):  # OFFSET, SCALE, X, Y, Z
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
                        frame_data[part_idx] = bone
                i += 1
            anim['frames'][frame_num] = frame_data
        i += 1

    basis_path = os.path.splitext(filepath)[0] + ".basis.json"
    if os.path.exists(basis_path):
        try:
            with open(basis_path, "r", encoding="utf-8") as f:
                basis_payload = json.load(f)
            basis_parts = list(basis_payload.get("part_names") or [])
            if basis_parts == list(anim["parts"]):
                local_frames = {}
                for frame_key, frame_parts in (basis_payload.get("frames") or {}).items():
                    try:
                        frame_idx = int(frame_key)
                    except Exception:
                        continue
                    if not isinstance(frame_parts, dict):
                        continue
                    parsed_frame = {}
                    for part_key, payload in frame_parts.items():
                        try:
                            part_idx = int(part_key)
                        except Exception:
                            continue
                        if not isinstance(payload, dict):
                            continue
                        offset = payload.get("offset") or [0.0, 0.0, 0.0]
                        quat = payload.get("quat") or [0.0, 0.0, 0.0, 1.0]
                        parsed_frame[part_idx] = {
                            "offset": [_sanitize_float(v) for v in offset[:3]],
                            "quat": [_sanitize_float(v) for v in quat[:4]],
                        }
                    local_frames[frame_idx] = parsed_frame
                anim["local_basis_frames"] = local_frames
        except Exception as exc:
            print(f"Warning: failed to load local-basis sidecar for {filepath}: {exc}")

    return anim


def _identity_bone_state():
    return {
        "offset": [0.0, 0.0, 0.0],
        "rot": [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
    }


def _identity_local_basis_state():
    return {
        "offset": [0.0, 0.0, 0.0],
        "quat": [0.0, 0.0, 0.0, 1.0],
    }


def ensure_anim_has_bones(anim, required_bones):
    """Inject required bones into PART table and frame tracks if missing."""
    requested = [str(x).strip() for x in (required_bones or []) if str(x).strip()]
    if not requested:
        return 0

    parts = list(anim.get("parts") or [])
    index_by_name = {str(name).strip().lower(): idx for idx, name in enumerate(parts)}
    added_indices = []
    for bone_name in requested:
        key = bone_name.lower()
        if key in index_by_name:
            continue
        index_by_name[key] = len(parts)
        parts.append(bone_name)
        added_indices.append(index_by_name[key])

    if not added_indices:
        anim["numparts"] = int(len(parts))
        anim["parts"] = parts
        return 0

    frames = anim.get("frames") or {}
    if not frames:
        frames = {0: {}}
        anim["frames"] = frames
    for frame_idx, frame_data in list(frames.items()):
        if not isinstance(frame_data, dict):
            frame_data = {}
            frames[frame_idx] = frame_data
        for bone_idx in added_indices:
            if bone_idx not in frame_data:
                frame_data[bone_idx] = _identity_bone_state()

    anim["parts"] = parts
    anim["numparts"] = int(len(parts))
    return len(added_indices)


def prune_anim_to_bones(anim, keep_bones):
    """Drop PART/frame tracks not present in keep_bones and renumber densely."""
    requested = [str(x).strip() for x in (keep_bones or []) if str(x).strip()]
    if not requested:
        return 0

    keep_set = {name.lower() for name in requested}
    old_parts = list(anim.get("parts") or [])
    if not old_parts:
        anim["numparts"] = 0
        return 0

    new_parts = []
    remap = {}
    removed = 0
    for old_idx, name in enumerate(old_parts):
        if str(name).strip().lower() in keep_set:
            remap[old_idx] = len(new_parts)
            new_parts.append(name)
        else:
            removed += 1

    frames = anim.get("frames") or {}
    for frame_idx, frame_data in list(frames.items()):
        if not isinstance(frame_data, dict):
            frames[frame_idx] = {}
            continue
        new_frame = {}
        for old_idx, bone in frame_data.items():
            if old_idx in remap:
                new_frame[remap[old_idx]] = bone
        frames[frame_idx] = new_frame

    anim["parts"] = new_parts
    anim["numparts"] = int(len(new_parts))
    return removed


def load_keep_bones_from_file(path):
    if not path:
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        if isinstance(data.get("present_anim_bones"), list):
            return [str(x).strip() for x in data["present_anim_bones"] if str(x).strip()]
        if isinstance(data.get("joint_names"), list):
            return [str(x).strip() for x in data["joint_names"] if str(x).strip()]
    if isinstance(data, list):
        return [str(x).strip() for x in data if str(x).strip()]
    return []


def neutralize_anim_root_tracks(anim, neutralize_bones):
    """Zero offset + identity rotation for selected bones across all frames."""
    if not neutralize_bones:
        return 0
    if not anim.get("frames") and not anim.get("local_basis_frames"):
        return 0

    name_to_idx = {name: i for i, name in enumerate(anim.get("parts", []))}
    target_indices = [name_to_idx[n] for n in neutralize_bones if n in name_to_idx]
    if not target_indices:
        return 0

    changed = 0
    for _, frame_data in anim["frames"].items():
        for pidx in target_indices:
            if pidx not in frame_data:
                frame_data[pidx] = {}
            frame_data[pidx]["offset"] = [0.0, 0.0, 0.0]
            frame_data[pidx]["rot"] = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
            changed += 1
    for _, frame_data in (anim.get("local_basis_frames") or {}).items():
        for pidx in target_indices:
            if pidx not in frame_data:
                frame_data[pidx] = {}
            frame_data[pidx]["offset"] = [0.0, 0.0, 0.0]
            frame_data[pidx]["quat"] = [0.0, 0.0, 0.0, 1.0]
            changed += 1
    return changed


def _clone_anim_from_idle(idle_anim, new_name):
    c = copy.deepcopy(idle_anim)
    c["name"] = new_name
    return c


def _normalize_numframes(anim):
    """Ensure numframes is sane and non-zero."""
    nf = int(anim.get("numframes", 0) or 0)
    if nf > 0:
        return nf
    frames = anim.get("frames", {})
    if frames:
        return max(frames.keys()) + 1
    return 1


def semantic_state_prepare(anims_by_name, required_names):
    """Guarantee required states exist; fill missing/empty from idle."""
    idle_name = "vm_thunder_gun_idle"
    if idle_name not in anims_by_name:
        raise RuntimeError("Semantic audit failed: missing vm_thunder_gun_idle")

    idle_anim = anims_by_name[idle_name]
    filled_missing = []
    replaced_empty = []

    for name in required_names:
        if name not in anims_by_name:
            anims_by_name[name] = _clone_anim_from_idle(idle_anim, name)
            filled_missing.append(name)
            continue

        anim = anims_by_name[name]
        nf = _normalize_numframes(anim)
        has_frames = bool(anim.get("frames"))
        if (not has_frames) or nf <= 0:
            anims_by_name[name] = _clone_anim_from_idle(idle_anim, name)
            anims_by_name[name]["name"] = name
            replaced_empty.append(name)
        else:
            anim["numframes"] = nf

    return filled_missing, replaced_empty


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
    length = math.sqrt(x*x + y*y + z*z + w*w)
    if length > 0:
        x /= length; y /= length; z /= length; w /= length
    return [x, y, z, w]


# ============================================================================
# Donor/Oracle Helpers
# ============================================================================

def _parse_donor_override_args(values):
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


def _read_indexed_strings(data, count, string_data_start):
    out = []
    pos = string_data_start
    for _ in range(int(count)):
        end = data.index(b'\x00', pos)
        out.append(data[pos:end].decode('ascii', errors='replace'))
        pos = end + 1
    return out


def _default_donor_asset_for_target(target_name):
    if target_name in DONOR_OVERRIDE_MAP:
        return DONOR_OVERRIDE_MAP[target_name]
    prefix = "vm_thunder_gun_"
    if target_name.startswith(prefix):
        suffix = target_name[len(prefix):]
        mapped = THUNDER_TO_AK74U_SUFFIX.get(suffix)
        if mapped:
            return f"viewmodel_ak74u_t6_{mapped}"
        return f"viewmodel_ak74u_t6_{suffix}"
    return DONOR_DEFAULT_ASSET


def _resolve_loaded_donor_asset_for_target(target_name):
    donor_name = _default_donor_asset_for_target(target_name)
    if DONOR_CONTEXT is None or "payloads" not in DONOR_CONTEXT:
        return donor_name
    payloads = DONOR_CONTEXT["payloads"]
    candidates = []
    for candidate in (target_name, donor_name, DONOR_DEFAULT_ASSET):
        candidate = str(candidate or "").strip()
        if candidate and candidate not in candidates:
            candidates.append(candidate)
    for candidate in candidates:
        if candidate in payloads:
            return candidate
    return donor_name


def _load_donor_context(donor_ff, donor_zone_name, donor_asset_names):
    if strict_xanim is None or donor_decrypt_zone is None or donor_parse_string_table is None:
        raise RuntimeError("donor_clone mode requires strict_xanim_parser + patch_zone_xanims imports")

    if not os.path.exists(donor_ff):
        raise RuntimeError(f"donor ff not found: {donor_ff}")

    _, donor_raw = donor_decrypt_zone(donor_ff, donor_zone_name)
    if not donor_raw:
        raise RuntimeError(f"failed to decrypt donor ff: {donor_ff}")

    donor_result = donor_parse_string_table(donor_raw)
    donor_string_count = donor_result[1]
    donor_asset_data_offset = donor_result[3]
    donor_string_data_start = donor_result[5]
    donor_index_to_string = _read_indexed_strings(donor_raw, donor_string_count, donor_string_data_start)

    payloads = {}
    missing = []
    for donor_name in sorted(set(donor_asset_names)):
        matches = strict_xanim.find_xanim_by_name(
            donor_raw,
            donor_name,
            min_offset=donor_asset_data_offset
        )
        if not matches:
            missing.append(donor_name)
            continue
        payloads[donor_name] = matches[0]

    return {
        "raw": donor_raw,
        "payloads": payloads,
        "missing": missing,
        "index_to_string": donor_index_to_string,
    }


def _map_script_string(name, string_table):
    if name not in string_table:
        string_table[name] = len(string_table)
    return string_table[name]


def _read_donor_name_order(donor_header, donor_sections, donor_raw, donor_index_to_string):
    if donor_header["names_ptr"] != PTR_FOLLOWING or "names" not in donor_sections:
        return []
    total = int(donor_header["boneCount"][9])
    s = donor_sections["names"]
    src = donor_raw[s["offset"]:s["offset"] + s["size"]]
    if len(src) != total * 2:
        raise RuntimeError("donor names section size mismatch")
    out = []
    for i in range(total):
        donor_idx = struct.unpack_from("<H", src, i * 2)[0]
        if donor_idx >= len(donor_index_to_string):
            raise RuntimeError(f"donor name idx out of range: {donor_idx}")
        out.append(donor_index_to_string[donor_idx])
    return out


def _copy_following_section(out, donor_raw, sections, key):
    if key not in sections:
        return
    s = sections[key]
    off = int(s["offset"])
    size = int(s["size"])
    out.extend(donor_raw[off:off + size])


def _append_remapped_donor_notify(out, donor_header, donor_sections, donor_raw, donor_index_to_string, string_table, donor_name):
    """Append donor notify payload while remapping scriptstring indices into the target table."""
    count = int(donor_header["notifyCount"])
    if count <= 0:
        return 0
    if donor_header["notify_ptr"] != PTR_FOLLOWING or "notify" not in donor_sections:
        return 0

    s = donor_sections["notify"]
    src = donor_raw[s["offset"]:s["offset"] + s["size"]]
    if len(src) != count * 8:
        raise RuntimeError(f"donor notify size mismatch for '{donor_name}'")

    for i in range(count):
        off = i * 8
        donor_idx = struct.unpack_from("<H", src, off)[0]
        if donor_idx >= len(donor_index_to_string):
            raise RuntimeError(f"donor notify idx out of range in '{donor_name}': {donor_idx}")
        sname = donor_index_to_string[donor_idx]
        out.extend(struct.pack("<H", _map_script_string(sname, string_table)))
        out.extend(src[off + 2:off + 8])
    return count


def _build_donor_clone_xanimparts_data(anim, string_table):
    global DONOR_MAP_HITS, DONOR_MAP_FALLBACKS
    if DONOR_CONTEXT is None:
        raise RuntimeError("donor_clone mode: donor context not initialized")

    target_name = anim['name']
    donor_name = _default_donor_asset_for_target(target_name)

    if donor_name not in DONOR_CONTEXT["payloads"]:
        if DONOR_FALLBACK_IDLE and DONOR_DEFAULT_ASSET in DONOR_CONTEXT["payloads"]:
            DONOR_MAP_FALLBACKS += 1
            donor_name = DONOR_DEFAULT_ASSET
        else:
            raise RuntimeError(f"donor asset missing for target '{target_name}': {donor_name}")

    donor_parsed = DONOR_CONTEXT["payloads"][donor_name]
    donor_raw = DONOR_CONTEXT["raw"]
    donor_header = donor_parsed["header"]
    donor_sections = donor_parsed["sections"]
    donor_index_to_string = DONOR_CONTEXT["index_to_string"]
    DONOR_MAP_HITS += 1

    header_off = donor_parsed["header_offset"]
    header = bytearray(donor_raw[header_off:header_off + 104])
    struct.pack_into('<I', header, 0x00, PTR_FOLLOWING)  # name ptr

    out = bytearray()

    # 1) name
    out.extend(target_name.encode('ascii', errors='ignore') + b'\x00')

    # 2) names remap
    if donor_header["names_ptr"] == PTR_FOLLOWING and "names" in donor_sections:
        s = donor_sections["names"]
        src = donor_raw[s["offset"]:s["offset"] + s["size"]]
        count = int(donor_header["boneCount"][9])
        if len(src) != count * 2:
            raise RuntimeError(f"donor names size mismatch for '{donor_name}'")
        for i in range(count):
            donor_idx = struct.unpack_from("<H", src, i * 2)[0]
            if donor_idx >= len(donor_index_to_string):
                raise RuntimeError(f"donor name idx out of range in '{donor_name}': {donor_idx}")
            sname = donor_index_to_string[donor_idx]
            out.extend(struct.pack("<H", _map_script_string(sname, string_table)))

    # 3) notify remap (uint16 scriptstring + pad + float)
    if donor_header["notify_ptr"] == PTR_FOLLOWING and "notify" in donor_sections:
        s = donor_sections["notify"]
        src = donor_raw[s["offset"]:s["offset"] + s["size"]]
        count = int(donor_header["notifyCount"])
        if len(src) != count * 8:
            raise RuntimeError(f"donor notify size mismatch for '{donor_name}'")
        for i in range(count):
            off = i * 8
            donor_idx = struct.unpack_from("<H", src, off)[0]
            if donor_idx >= len(donor_index_to_string):
                raise RuntimeError(f"donor notify idx out of range in '{donor_name}': {donor_idx}")
            sname = donor_index_to_string[donor_idx]
            out.extend(struct.pack("<H", _map_script_string(sname, string_table)))
            out.extend(src[off + 2:off + 8])

    # 4) deltaPart + remaining pointer-follow sections are copied byte-exact.
    for key in (
        "deltaPart",
        "dataByte",
        "dataShort",
        "dataInt",
        "randomDataShort",
        "randomDataByte",
        "randomDataInt",
        "indices",
    ):
        _copy_following_section(out, donor_raw, donor_sections, key)

    return bytes(header), bytes(out)


def _build_donor_template_static_pose_xanimparts_data(anim, string_table):
    if DONOR_CONTEXT is None:
        raise RuntimeError("donor_template_static_pose mode: donor context not initialized")

    target_name = anim["name"]
    donor_name = _resolve_loaded_donor_asset_for_target(target_name)

    if donor_name not in DONOR_CONTEXT["payloads"]:
        if DONOR_FALLBACK_IDLE and DONOR_DEFAULT_ASSET in DONOR_CONTEXT["payloads"]:
            donor_name = DONOR_DEFAULT_ASSET
        else:
            raise RuntimeError(f"donor template asset missing for target '{target_name}': {donor_name}")

    donor_parsed = DONOR_CONTEXT["payloads"][donor_name]
    donor_raw = DONOR_CONTEXT["raw"]
    donor_header = donor_parsed["header"]
    donor_sections = donor_parsed["sections"]
    donor_index_to_string = DONOR_CONTEXT["index_to_string"]

    donor_names = _read_donor_name_order(donor_header, donor_sections, donor_raw, donor_index_to_string)
    total_bones = int(donor_header["boneCount"][9])
    if len(donor_names) != total_bones:
        raise RuntimeError("donor template names list mismatch")

    donor_data_byte = b""
    if donor_header["dataByte_ptr"] == PTR_FOLLOWING and "dataByte" in donor_sections:
        s = donor_sections["dataByte"]
        donor_data_byte = donor_raw[s["offset"]:s["offset"] + s["size"]]
    if len(donor_data_byte) != int(donor_header["dataByteCount"]):
        raise RuntimeError("donor template dataByte size mismatch")
    rotated_count = int(sum(int(donor_header["boneCount"][i]) for i in range(1, 5)))
    translated_count = int(sum(int(donor_header["boneCount"][i]) for i in range(5, 8)))
    required_perm_count = max(rotated_count, translated_count)
    if len(donor_data_byte) < required_perm_count:
        raise RuntimeError(
            "donor template dataByte table too short: "
            f"got {len(donor_data_byte)} need at least {required_perm_count} "
            f"(rotated={rotated_count} translated={translated_count} total={total_bones})"
        )

    donor_perm = [int(b) for b in donor_data_byte]

    donor_data_short = b""
    if donor_header["dataShort_ptr"] == PTR_FOLLOWING and "dataShort" in donor_sections:
        s = donor_sections["dataShort"]
        donor_data_short = donor_raw[s["offset"]:s["offset"] + s["size"]]
    if len(donor_data_short) != int(donor_header["dataShortCount"]) * 2:
        raise RuntimeError("donor template dataShort size mismatch")
    preserve_donor_rotations = int(donor_header["dataShortCount"]) != rotated_count * 4
    donor_data_int = b""
    if donor_header["dataInt_ptr"] == PTR_FOLLOWING and "dataInt" in donor_sections:
        s = donor_sections["dataInt"]
        donor_data_int = donor_raw[s["offset"]:s["offset"] + s["size"]]
    if len(donor_data_int) != int(donor_header["dataIntCount"]) * 4:
        raise RuntimeError("donor template dataInt size mismatch")
    normal_translated_count = int(donor_header["boneCount"][5])
    precise_translated_count = int(donor_header["boneCount"][6])
    static_translated_count = int(donor_header["boneCount"][7])
    dynamic_translated_count = normal_translated_count + precise_translated_count
    donor_data_int_count = int(donor_header["dataIntCount"])
    preserve_donor_translations = False
    mixed_dynamic_translations = False
    if donor_data_int_count == translated_count * 3:
        preserve_donor_translations = False
    elif donor_data_int_count == (static_translated_count * 3) + (dynamic_translated_count * 6):
        mixed_dynamic_translations = True
    else:
        raise RuntimeError(
            "donor template unsupported dataInt layout: "
            f"count={donor_header['dataIntCount']} translated={translated_count} "
            f"staticTranslated={static_translated_count} dynamicTranslated={dynamic_translated_count}"
        )

    frame0 = _pick_frame(anim)
    source_name_to_idx = {str(name).strip().lower(): idx for idx, name in enumerate(anim.get("parts", []))}
    static_diag_key = str(BO3_IDLE_DIAG_STATIC_BONE).strip().lower()
    static_diag_translate = [float(v) for v in (BO3_IDLE_DIAG_STATIC_TRANSLATE or [0.0, 0.0, 0.0])[:3]]
    static_diag_applied = False

    def source_state_for_name(name):
        idx = source_name_to_idx.get(str(name).strip().lower())
        if idx is None:
            return None
        return frame0.get(idx)

    header_off = donor_parsed["header_offset"]
    header = bytearray(donor_raw[header_off:header_off + 104])
    struct.pack_into("<I", header, 0x00, PTR_FOLLOWING)

    out = bytearray()
    out.extend(target_name.encode("ascii", errors="ignore") + b"\x00")

    # 1) names: preserve donor order exactly, remapped into the target string table
    for sname in donor_names:
        out.extend(struct.pack("<H", _map_script_string(sname, string_table)))

    # 2) notify: preserve donor notify semantics verbatim, remapped into the target string table
    if donor_header["notify_ptr"] == PTR_FOLLOWING and "notify" in donor_sections:
        s = donor_sections["notify"]
        src = donor_raw[s["offset"]:s["offset"] + s["size"]]
        count = int(donor_header["notifyCount"])
        if len(src) != count * 8:
            raise RuntimeError(f"donor notify size mismatch for '{donor_name}'")
        for i in range(count):
            off = i * 8
            donor_idx = struct.unpack_from("<H", src, off)[0]
            if donor_idx >= len(donor_index_to_string):
                raise RuntimeError(f"donor notify idx out of range in '{donor_name}': {donor_idx}")
            sname = donor_index_to_string[donor_idx]
            out.extend(struct.pack("<H", _map_script_string(sname, string_table)))
            out.extend(src[off + 2:off + 8])

    # 3) deltaPart: preserved as absent for this template lane

    # 4) dataByte: donor category permutation stays intact
    out.extend(donor_data_byte)

    # 5) dataShort:
    # Some stock T6 viewmodel xanims use a mixed rotation contract where the
    # raw dataShort count is not simply rotated_count * 4. Preserve that donor
    # payload until the full codec split is implemented, but still allow custom
    # translation injection via dataInt below.
    if preserve_donor_rotations:
        out.extend(donor_data_short)
    else:
        for donor_bone_idx in donor_perm[:rotated_count]:
            bone_name = donor_names[donor_bone_idx]
            bone = source_state_for_name(bone_name)
            if bone:
                rot_m = bone.get("rot", [[1, 0, 0], [0, 1, 0], [0, 0, 1]])
                rot_m_t = [
                    [rot_m[0][0], rot_m[1][0], rot_m[2][0]],
                    [rot_m[0][1], rot_m[1][1], rot_m[2][1]],
                    [rot_m[0][2], rot_m[1][2], rot_m[2][2]],
                ]
                quat = rotation_matrix_to_quat(rot_m_t)
            else:
                quat = [0.0, 0.0, 0.0, 1.0]
            for q in quat:
                out.extend(struct.pack("<h", quat_to_int16(_sanitize_float(q))))

    # 6) dataInt:
    #   - simple/static donor layouts: translated-set order sampled from the source anim
    #   - mixed dynamic donor layouts: keep donor dynamic mins/size tail intact, but still
    #     allow source/static diagnostic injection into the leading static-translation slice
    if not mixed_dynamic_translations:
        for donor_bone_idx in donor_perm[:translated_count]:
            bone_name = donor_names[donor_bone_idx]
            bone = source_state_for_name(bone_name)
            if bone:
                off = bone.get("offset", [0.0, 0.0, 0.0])
            else:
                off = [0.0, 0.0, 0.0]
            ox, oy, oz = (_sanitize_float(v) for v in off[:3])
            if static_diag_key and str(bone_name).strip().lower() == static_diag_key and any(abs(v) > 1e-6 for v in static_diag_translate):
                ox = _sanitize_float(ox + static_diag_translate[0])
                oy = _sanitize_float(oy + static_diag_translate[1])
                oz = _sanitize_float(oz + static_diag_translate[2])
                static_diag_applied = True
            out.extend(struct.pack("<f", ox))
            out.extend(struct.pack("<f", oy))
            out.extend(struct.pack("<f", oz))
    else:
        donor_data_int_values = list(struct.unpack("<" + ("f" * donor_data_int_count), donor_data_int))
        static_value_count = static_translated_count * 3
        static_values = donor_data_int_values[:static_value_count]
        dynamic_tail_values = donor_data_int_values[static_value_count:]

        # We do not yet have the exact donor translation-bone mapping for animated backend
        # layouts. Until that mapping is decoded, preserve the donor static slice shape and
        # apply any requested diagnostic translation uniformly so the runtime win is still
        # observable without corrupting the donor dynamic tail.
        if any(abs(v) > 1e-6 for v in static_diag_translate):
            for i in range(0, len(static_values), 3):
                static_values[i + 0] = _sanitize_float(static_values[i + 0] + static_diag_translate[0])
                static_values[i + 1] = _sanitize_float(static_values[i + 1] + static_diag_translate[1])
                static_values[i + 2] = _sanitize_float(static_values[i + 2] + static_diag_translate[2])
            static_diag_applied = True

        for value in static_values:
            out.extend(struct.pack("<f", _sanitize_float(value)))
        for value in dynamic_tail_values:
            out.extend(struct.pack("<f", _sanitize_float(value)))

    # 7) randomDataShort: preserve donor payload exactly. Stock T6 weapon
    # xanims can require this section even when we are only injecting custom
    # translation into dataInt.
    if donor_header["randomDataShort_ptr"] == PTR_FOLLOWING and "randomDataShort" in donor_sections:
        s = donor_sections["randomDataShort"]
        src = donor_raw[s["offset"]:s["offset"] + s["size"]]
        expected = int(donor_header["randomDataShortCount"]) * 2
        if len(src) != expected:
            raise RuntimeError(f"donor randomDataShort size mismatch for '{donor_name}'")
        out.extend(src)

    if static_diag_applied:
        print(
            f"  donor_template_static_pose diagnostic ({anim.get('name','?')}): "
            f"bone={BO3_IDLE_DIAG_STATIC_BONE} translate={static_diag_translate}"
        )

    return bytes(header), bytes(out)


def _quat_near_identity(quat, eps=1e-4):
    qx, qy, qz, qw = (_sanitize_float(v) for v in quat[:4])
    return (
        abs(qx) <= eps
        and abs(qy) <= eps
        and abs(qz) <= eps
        and abs(qw - 1.0) <= eps
    )


def _offset_near_zero(offset, eps=1e-4):
    ox, oy, oz = (_sanitize_float(v) for v in offset[:3])
    return abs(ox) <= eps and abs(oy) <= eps and abs(oz) <= eps


def _frame0_bone_quat_and_offset(anim, bone_idx, zero_local_basis_offset=False):
    if FORCE_IDENTITY_POSE:
        return [0.0, 0.0, 0.0, 1.0], [0.0, 0.0, 0.0]
    local_basis_frames = anim.get("local_basis_frames") or {}
    if local_basis_frames:
        bone = _get_local_basis_bone_state(anim, 0, bone_idx)
        off = [_sanitize_float(v) for v in (bone.get("offset") or [0.0, 0.0, 0.0])[:3]]
        if zero_local_basis_offset:
            off = [0.0, 0.0, 0.0]
        quat = [_sanitize_float(v) for v in (bone.get("quat") or [0.0, 0.0, 0.0, 1.0])[:4]]
        if len(quat) < 4:
            quat = [0.0, 0.0, 0.0, 1.0]
        return quat, off

    frame0 = _pick_frame(anim)
    bone = frame0.get(bone_idx)
    if bone:
        off = bone.get("offset", [0.0, 0.0, 0.0])
        rot_m = bone.get("rot", [[1, 0, 0], [0, 1, 0], [0, 0, 1]])
        rot_m_t = [
            [rot_m[0][0], rot_m[1][0], rot_m[2][0]],
            [rot_m[0][1], rot_m[1][1], rot_m[2][1]],
            [rot_m[0][2], rot_m[1][2], rot_m[2][2]],
        ]
        quat = rotation_matrix_to_quat(rot_m_t)
    else:
        off = [0.0, 0.0, 0.0]
        quat = [0.0, 0.0, 0.0, 1.0]

    quat = [_sanitize_float(v) for v in quat[:4]]
    off = [_sanitize_float(v) for v in off[:3]]
    return quat, off


def _build_donor_semantic_static_pose_xanimparts_data(anim, string_table):
    """
    Emit a target-rig static pose using donor-style T6 weapon animation
    semantics:
      - assetType=1
      - 2-frame header / 15Hz frequency
      - donor-style notify payload
      - target-rig names table
      - full static rotation/translation channel coverage for the target rig

    This keeps the stable donor runtime contract but does not reuse the donor's
    71-bone names table. It rebuilds the names and section counts for the actual
    reduced Servant rig.
    """
    if DONOR_CONTEXT is None:
        raise RuntimeError("donor_semantic_static_pose mode: donor context not initialized")

    target_name = anim["name"]
    donor_name = _default_donor_asset_for_target(target_name)
    if donor_name not in DONOR_CONTEXT["payloads"]:
        if DONOR_FALLBACK_IDLE and DONOR_DEFAULT_ASSET in DONOR_CONTEXT["payloads"]:
            donor_name = DONOR_DEFAULT_ASSET
        else:
            raise RuntimeError(f"donor semantic asset missing for target '{target_name}': {donor_name}")

    donor_parsed = DONOR_CONTEXT["payloads"][donor_name]
    donor_raw = DONOR_CONTEXT["raw"]
    donor_header = donor_parsed["header"]
    donor_sections = donor_parsed["sections"]
    donor_index_to_string = DONOR_CONTEXT["index_to_string"]

    parts = list(anim.get("parts") or [])
    num_bones = len(parts)
    if DIAG_ZERO_BONES:
        num_bones = 0
        parts = []

    if num_bones > 255:
        raise RuntimeError("donor_semantic_static_pose currently supports <=255 bones only")

    bone_string_indices = []
    for bone_name in parts[:num_bones]:
        if bone_name not in string_table:
            string_table[bone_name] = len(string_table)
        bone_string_indices.append(string_table[bone_name])

    ordered_entries = []
    for bone_idx in range(num_bones):
        quat, off = _frame0_bone_quat_and_offset(anim, bone_idx, zero_local_basis_offset=True)
        ordered_entries.append((bone_idx, quat, off))

    rotated_count = num_bones
    translated_count = num_bones
    none_rotated_count = 0
    none_translated_count = 0

    data_byte = bytearray()
    data_short = bytearray()
    data_int = bytearray()

    for bone_idx, _quat, _off in ordered_entries:
        data_byte.append(bone_idx & 0xFF)

    for _bone_idx, quat, _off in ordered_entries:
        for q in quat:
            data_short.extend(struct.pack("<h", quat_to_int16(q)))

    for _bone_idx, _quat, off in ordered_entries:
        data_int.extend(struct.pack("<f", off[0]))
        data_int.extend(struct.pack("<f", off[1]))
        data_int.extend(struct.pack("<f", off[2]))

    notify_count = int(donor_header["notifyCount"])

    header = bytearray(104)
    struct.pack_into("<I", header, 0x00, PTR_FOLLOWING)
    struct.pack_into("<H", header, 0x04, len(data_byte))
    struct.pack_into("<H", header, 0x06, len(data_short) // 2)
    struct.pack_into("<H", header, 0x08, len(data_int) // 4)
    struct.pack_into("<H", header, 0x0A, 0)
    struct.pack_into("<H", header, 0x0C, 0)
    struct.pack_into("<H", header, 0x0E, 2)

    header[0x10] = 0
    header[0x11] = 0
    header[0x12] = 0
    header[0x13] = 0
    struct.pack_into("<I", header, 0x14, 0)

    for bc in range(10):
        header[0x18 + bc] = 0
    header[0x18 + 0] = none_rotated_count
    header[0x18 + 4] = rotated_count
    header[0x18 + 7] = translated_count
    header[0x18 + 8] = none_translated_count
    header[0x18 + 9] = num_bones

    header[0x22] = notify_count
    header[0x23] = 1
    header[0x24] = 0

    struct.pack_into("<I", header, 0x28, 0)
    struct.pack_into("<I", header, 0x2C, 0)
    struct.pack_into("<f", header, 0x30, 30.0)
    struct.pack_into("<f", header, 0x34, 15.0)
    struct.pack_into("<f", header, 0x38, 0.0)
    struct.pack_into("<f", header, 0x3C, 0.0)

    struct.pack_into("<I", header, 0x40, PTR_FOLLOWING if num_bones > 0 else PTR_NULL)
    struct.pack_into("<I", header, 0x44, PTR_FOLLOWING if len(data_byte) > 0 else PTR_NULL)
    struct.pack_into("<I", header, 0x48, PTR_FOLLOWING if len(data_short) > 0 else PTR_NULL)
    struct.pack_into("<I", header, 0x4C, PTR_FOLLOWING if len(data_int) > 0 else PTR_NULL)
    struct.pack_into("<I", header, 0x50, PTR_NULL)
    struct.pack_into("<I", header, 0x54, PTR_NULL)
    struct.pack_into("<I", header, 0x58, PTR_NULL)
    struct.pack_into("<I", header, 0x5C, PTR_NULL)
    struct.pack_into("<I", header, 0x60, PTR_FOLLOWING if notify_count > 0 else PTR_NULL)
    struct.pack_into("<I", header, 0x64, PTR_NULL)

    out = bytearray()
    out.extend(target_name.encode("ascii", errors="ignore") + b"\x00")

    for idx in bone_string_indices:
        out.extend(struct.pack("<H", idx))

    if notify_count > 0 and donor_header["notify_ptr"] == PTR_FOLLOWING and "notify" in donor_sections:
        s = donor_sections["notify"]
        src = donor_raw[s["offset"]:s["offset"] + s["size"]]
        if len(src) != notify_count * 8:
            raise RuntimeError(f"donor notify size mismatch for '{donor_name}'")
        for i in range(notify_count):
            off = i * 8
            donor_idx = struct.unpack_from("<H", src, off)[0]
            if donor_idx >= len(donor_index_to_string):
                raise RuntimeError(f"donor notify idx out of range in '{donor_name}': {donor_idx}")
            sname = donor_index_to_string[donor_idx]
            out.extend(struct.pack("<H", _map_script_string(sname, string_table)))
            out.extend(src[off + 2:off + 8])

    out.extend(data_byte)
    out.extend(data_short)
    out.extend(data_int)
    return bytes(header), bytes(out)


def _pick_bo3_delta_part_index(anim):
    parts = list(anim.get("parts") or [])
    if not parts:
        return None
    name_to_idx = {str(name).strip().lower(): idx for idx, name in enumerate(parts)}
    for preferred in BO3_ROOT_BONE_PRIORITY:
        idx = name_to_idx.get(preferred.lower())
        if idx is not None:
            return idx
    return 0


def _quat_angle_delta(a, b):
    d = max(-1.0, min(1.0, _quat_dot(a, b)))
    # q and -q represent same rotation; use abs(dot) to avoid false spikes.
    d = abs(d)
    return 2.0 * math.acos(d)


def _compute_bo3_motion_score(anim, part_idx, numframes):
    if numframes < 2:
        return 0.0
    offsets = []
    quats = []
    for frame_idx in range(numframes):
        q, off = _get_emit_frame_quat_and_offset(anim, frame_idx, part_idx)
        offsets.append([
            _sanitize_float(off[0]),
            _sanitize_float(off[1]),
            _sanitize_float(off[2]),
        ])
        quats.append([
            _sanitize_float(q[0]),
            _sanitize_float(q[1]),
            _sanitize_float(q[2]),
            _sanitize_float(q[3]),
        ])

    mins = [min(v[c] for v in offsets) for c in range(3)]
    maxs = [max(v[c] for v in offsets) for c in range(3)]
    trans_span = math.sqrt(
        (maxs[0] - mins[0]) ** 2 + (maxs[1] - mins[1]) ** 2 + (maxs[2] - mins[2]) ** 2
    )

    q0 = quats[0]
    max_ang = 0.0
    for q in quats[1:]:
        max_ang = max(max_ang, _quat_angle_delta(q0, q))

    # Blend translation units + radians into one stable ranking score.
    return trans_span + (0.25 * max_ang)


def _pick_bo3_nonroot_motion_part_index(anim, numframes):
    parts = list(anim.get("parts") or [])
    if not parts:
        return None, []

    name_to_idx = {str(name).strip().lower(): idx for idx, name in enumerate(parts)}
    root_exclude = {str(x).strip().lower() for x in BO3_ROOT_BONE_PRIORITY}

    diag_key = str(BO3_IDLE_DIAG_BONE).strip().lower()
    if diag_key:
        idx = name_to_idx.get(diag_key)
        if idx is not None and diag_key not in root_exclude:
            score = _compute_bo3_motion_score(anim, idx, numframes)
            return idx, [(parts[idx], score)]

    # 1) Deterministic preferred weapon-bone list first.
    for preferred in BO3_NONROOT_BONE_PRIORITY:
        key = str(preferred).strip().lower()
        idx = name_to_idx.get(key)
        if idx is not None and key not in root_exclude:
            score = _compute_bo3_motion_score(anim, idx, numframes)
            return idx, [(parts[idx], score)]

    # 2) Fallback: best-motion non-root bone.
    scored = []
    for idx, name in enumerate(parts):
        key = str(name).strip().lower()
        if key in root_exclude:
            continue
        score = _compute_bo3_motion_score(anim, idx, numframes)
        scored.append((idx, score))
    scored.sort(key=lambda t: t[1], reverse=True)
    top = [(parts[idx], score) for idx, score in scored[: max(1, BO3_MOTION_BONE_REPORT_TOP)]]
    if not scored:
        return None, top
    return scored[0][0], top


def _get_frame_bone_state(anim, frame_idx, part_idx):
    frames = anim.get("frames") or {}
    direct = frames.get(frame_idx, {})
    if isinstance(direct, dict) and part_idx in direct:
        return direct[part_idx]

    # Backward search first for stable continuity; forward as last resort.
    for f in range(frame_idx - 1, -1, -1):
        fd = frames.get(f, {})
        if isinstance(fd, dict) and part_idx in fd:
            return fd[part_idx]
    max_frame = int(anim.get("numframes", 0) or 0)
    for f in range(frame_idx + 1, max(1, max_frame)):
        fd = frames.get(f, {})
        if isinstance(fd, dict) and part_idx in fd:
            return fd[part_idx]
    return _identity_bone_state()


def _get_local_basis_bone_state(anim, frame_idx, part_idx):
    frames = anim.get("local_basis_frames") or {}
    direct = frames.get(frame_idx, {})
    if isinstance(direct, dict) and part_idx in direct:
        return direct[part_idx]

    for f in range(frame_idx - 1, -1, -1):
        fd = frames.get(f, {})
        if isinstance(fd, dict) and part_idx in fd:
            return fd[part_idx]
    max_frame = int(anim.get("numframes", 0) or 0)
    for f in range(frame_idx + 1, max(1, max_frame)):
        fd = frames.get(f, {})
        if isinstance(fd, dict) and part_idx in fd:
            return fd[part_idx]
    return _identity_local_basis_state()


def _get_emit_frame_quat_and_offset(anim, frame_idx, bone_idx, *, zero_local_basis_offset=False):
    local_basis_frames = anim.get("local_basis_frames") or {}
    if local_basis_frames:
        bone = _get_local_basis_bone_state(anim, frame_idx, bone_idx)
        off = [_sanitize_float(v) for v in (bone.get("offset") or [0.0, 0.0, 0.0])[:3]]
        if zero_local_basis_offset:
            off = [0.0, 0.0, 0.0]
        quat = [_sanitize_float(v) for v in (bone.get("quat") or [0.0, 0.0, 0.0, 1.0])[:4]]
        if len(quat) < 4:
            quat = [0.0, 0.0, 0.0, 1.0]
        return quat, off

    bone = _get_frame_bone_state(anim, frame_idx, bone_idx)
    off = bone.get("offset", [0.0, 0.0, 0.0])
    rot_m = bone.get("rot", [[1, 0, 0], [0, 1, 0], [0, 0, 1]])
    rot_m_t = [
        [rot_m[0][0], rot_m[1][0], rot_m[2][0]],
        [rot_m[0][1], rot_m[1][1], rot_m[2][1]],
        [rot_m[0][2], rot_m[1][2], rot_m[2][2]],
    ]
    quat = rotation_matrix_to_quat(rot_m_t)
    return (
        [_sanitize_float(v) for v in quat[:4]],
        [_sanitize_float(v) for v in off[:3]],
    )


def _quantize_u16(v):
    return max(0, min(65535, int(round(float(v)))))


def _quat_dot(a, b):
    return (a[0] * b[0]) + (a[1] * b[1]) + (a[2] * b[2]) + (a[3] * b[3])


def _build_bo3_idle_delta_part(anim, numframes):
    """
    Build XAnimDeltaPart bytes for one keyframed bone track.
    bo3_frames milestone: prefer a visible non-root weapon bone first,
    then fall back to root-priority list.
    """
    if numframes < 2:
        return b"", False, False, ""

    part_name = ""
    top_motion = []
    part_idx, top_motion = _pick_bo3_nonroot_motion_part_index(anim, numframes)
    if part_idx is None:
        part_idx = _pick_bo3_delta_part_index(anim)
    if part_idx is None:
        return b"", False, False, ""
    parts = list(anim.get("parts") or [])
    if 0 <= int(part_idx) < len(parts):
        part_name = str(parts[int(part_idx)])
    if top_motion:
        sample = ", ".join([f"{n}:{s:.4f}" for n, s in top_motion[: max(1, BO3_MOTION_BONE_REPORT_TOP)]])
        print(f"  bo3_frames motion candidates ({anim.get('name','?')}): {sample}")
    print(f"  bo3_frames delta bone ({anim.get('name','?')}): {part_name or part_idx}")

    offsets = []
    quats = []
    for frame_idx in range(numframes):
        q, off = _get_emit_frame_quat_and_offset(anim, frame_idx, part_idx)
        offsets.append([
            _sanitize_float(off[0]),
            _sanitize_float(off[1]),
            _sanitize_float(off[2]),
        ])
        quats.append([
            _sanitize_float(q[0]),
            _sanitize_float(q[1]),
            _sanitize_float(q[2]),
            _sanitize_float(q[3]),
        ])

    # Enforce quaternion sign continuity to avoid sudden flips.
    for i in range(1, len(quats)):
        if _quat_dot(quats[i - 1], quats[i]) < 0.0:
            quats[i] = [-quats[i][0], -quats[i][1], -quats[i][2], -quats[i][3]]

    diag_translate = [float(v) for v in (BO3_IDLE_DIAG_TRANSLATE or [0.0, 0.0, 0.0])[:3]]
    if any(abs(v) > 1e-6 for v in diag_translate):
        frame_span = max(1, numframes - 1)
        for frame_idx in range(numframes):
            phase = (float(frame_idx) / float(frame_span)) * (2.0 * math.pi)
            pulse = math.sin(phase)
            offsets[frame_idx] = [
                _sanitize_float(offsets[frame_idx][0] + (diag_translate[0] * pulse)),
                _sanitize_float(offsets[frame_idx][1] + (diag_translate[1] * pulse)),
                _sanitize_float(offsets[frame_idx][2] + (diag_translate[2] * pulse)),
            ]
        print(
            f"  bo3_frames idle diagnostic ({anim.get('name','?')}): "
            f"bone={part_name or part_idx} translate={diag_translate}"
        )

    idx_elem = 1 if numframes < 256 else 2
    indices = bytearray()
    for i in range(numframes):
        if idx_elem == 1:
            indices.extend(struct.pack("<B", i & 0xFF))
        else:
            indices.extend(struct.pack("<H", i))

    # Translation stream: use ushort vec3 quantization.
    mins = [min(v[c] for v in offsets) for c in range(3)]
    maxs = [max(v[c] for v in offsets) for c in range(3)]
    spans = []
    for c in range(3):
        span = maxs[c] - mins[c]
        spans.append(span if span > 1e-8 else 1.0)

    trans_frames = bytearray()
    for off in offsets:
        for c in range(3):
            qv = (off[c] - mins[c]) / spans[c]
            trans_frames.extend(struct.pack("<H", _quantize_u16(qv * 65535.0)))

    trans_struct = bytearray(36)
    struct.pack_into("<H", trans_struct, 0x00, numframes - 1)  # size
    struct.pack_into("<b", trans_struct, 0x02, 0)  # smallTrans=0 => ushort vec3
    struct.pack_into("<f", trans_struct, 0x04, mins[0])
    struct.pack_into("<f", trans_struct, 0x08, mins[1])
    struct.pack_into("<f", trans_struct, 0x0C, mins[2])
    struct.pack_into("<f", trans_struct, 0x10, spans[0])
    struct.pack_into("<f", trans_struct, 0x14, spans[1])
    struct.pack_into("<f", trans_struct, 0x18, spans[2])
    struct.pack_into("<I", trans_struct, 0x1C, PTR_FOLLOWING)  # frames ptr
    struct.pack_into("<I", trans_struct, 0x20, PTR_FOLLOWING)  # indices ptr

    # Rotation stream: full quaternion per keyframe (int16 x4).
    quat_struct = bytearray(12)
    struct.pack_into("<H", quat_struct, 0x00, numframes - 1)  # size
    struct.pack_into("<I", quat_struct, 0x04, PTR_FOLLOWING)  # frames ptr
    struct.pack_into("<I", quat_struct, 0x08, PTR_FOLLOWING)  # indices ptr

    quat_frames = bytearray()
    for q in quats:
        quat_frames.extend(struct.pack("<h", quat_to_int16(q[0])))
        quat_frames.extend(struct.pack("<h", quat_to_int16(q[1])))
        quat_frames.extend(struct.pack("<h", quat_to_int16(q[2])))
        quat_frames.extend(struct.pack("<h", quat_to_int16(q[3])))

    delta = bytearray()
    # XAnimDeltaPart struct: trans, quat2, quat pointers
    delta.extend(struct.pack("<I", PTR_FOLLOWING))  # trans
    delta.extend(struct.pack("<I", PTR_NULL))       # quat2
    delta.extend(struct.pack("<I", PTR_FOLLOWING))  # quat

    # Payload follows the observed serialized order used by T6 tooling/loader
    # (and modeled by `_build/strict_xanim_parser.py`):
    #   trans_struct -> indices -> frames, then quat_struct -> indices -> frames
    delta.extend(trans_struct)
    delta.extend(indices)
    delta.extend(trans_frames)
    delta.extend(quat_struct)
    delta.extend(indices)
    delta.extend(quat_frames)
    return bytes(delta), True, True, part_name


def _build_bo3_frames_idle_xanimparts_data(anim, string_table):
    """
    bo3_frames idle path:
    - keep a donor-safe semantic T6 header/pointer contract
    - use a stable frame-0 baseline pose for all bones
    - add a real BO3-driven deltaPart stream for visible idle motion

    This avoids the earlier malformed hybrid contract where we wrote only
    frame-0 static channels but advertised the full BO3 frame count without
    any matching playback payload.
    """
    if DONOR_CONTEXT is None:
        raise RuntimeError("bo3_frames mode: donor context not initialized")

    name = anim["name"]
    parts = anim["parts"]
    framerate = max(1.0, float(anim.get("framerate", 30)))
    src_numframes = int(anim.get("numframes", 1))
    numframes = max(1, min(65535, src_numframes if src_numframes > 0 else 1))
    num_bones = len(parts)
    if DIAG_ZERO_BONES:
        num_bones = 0

    donor_name = _default_donor_asset_for_target(name)
    if donor_name not in DONOR_CONTEXT["payloads"]:
        if DONOR_FALLBACK_IDLE and DONOR_DEFAULT_ASSET in DONOR_CONTEXT["payloads"]:
            donor_name = DONOR_DEFAULT_ASSET
        else:
            raise RuntimeError(f"bo3_frames donor semantic asset missing for target '{name}': {donor_name}")

    donor_parsed = DONOR_CONTEXT["payloads"][donor_name]
    donor_raw = DONOR_CONTEXT["raw"]
    donor_header = donor_parsed["header"]
    donor_sections = donor_parsed["sections"]
    donor_index_to_string = DONOR_CONTEXT["index_to_string"]

    bone_string_indices = []
    rot_quats_i16 = []
    trans_vec_f32 = []
    trans_bone_ids_u8 = []
    trans_bone_ids_u16 = []
    static_diag_key = str(BO3_IDLE_DIAG_STATIC_BONE).strip().lower()
    static_diag_translate = [float(v) for v in (BO3_IDLE_DIAG_STATIC_TRANSLATE or [0.0, 0.0, 0.0])[:3]]
    static_diag_applied = False

    for bone_idx, bone_name in enumerate(parts[:num_bones]):
        if bone_name not in string_table:
            string_table[bone_name] = len(string_table)
        bone_string_indices.append(string_table[bone_name])

        # Use the stable local-basis-neutralized pose for the baseline channels.
        quat, off = _frame0_bone_quat_and_offset(anim, bone_idx, zero_local_basis_offset=True)

        qx, qy, qz, qw = (_sanitize_float(v) for v in quat)
        ox, oy, oz = (_sanitize_float(v) for v in off[:3])
        if static_diag_key and str(bone_name).strip().lower() == static_diag_key and any(abs(v) > 1e-6 for v in static_diag_translate):
            ox = _sanitize_float(ox + static_diag_translate[0])
            oy = _sanitize_float(oy + static_diag_translate[1])
            oz = _sanitize_float(oz + static_diag_translate[2])
            static_diag_applied = True
        rot_quats_i16.extend([quat_to_int16(qx), quat_to_int16(qy), quat_to_int16(qz), quat_to_int16(qw)])
        trans_vec_f32.extend([ox, oy, oz])

        if num_bones > 255:
            trans_bone_ids_u16.append(bone_idx)
        else:
            trans_bone_ids_u8.append(bone_idx & 0xFF)

    data_byte_count = len(trans_bone_ids_u8)
    data_short_count = len(rot_quats_i16) + len(trans_bone_ids_u16)
    data_int_count = len(trans_vec_f32)

    delta_bytes = b""
    has_delta_trans = False
    has_delta_quat = False
    has_delta = False
    delta_part_name = ""
    if numframes >= 2 and num_bones > 0:
        delta_bytes, has_delta_trans, has_delta_quat, delta_part_name = _build_bo3_idle_delta_part(anim, numframes)
        has_delta = bool(delta_bytes)
    if static_diag_applied:
        print(
            f"  bo3_frames idle static diagnostic ({anim.get('name','?')}): "
            f"bone={BO3_IDLE_DIAG_STATIC_BONE} translate={static_diag_translate}"
        )

    header = bytearray(104)
    struct.pack_into("<I", header, 0x00, PTR_FOLLOWING)  # name
    struct.pack_into("<H", header, 0x04, data_byte_count)
    struct.pack_into("<H", header, 0x06, data_short_count)
    struct.pack_into("<H", header, 0x08, data_int_count)
    struct.pack_into("<H", header, 0x0A, 0)  # randomDataByteCount
    struct.pack_into("<H", header, 0x0C, 0)  # randomDataIntCount
    struct.pack_into("<H", header, 0x0E, numframes if has_delta else 2)

    header[0x10] = 1 if _force_loop_for_anim(name) else 0  # bLoop
    header[0x11] = 1 if has_delta else 0  # bDelta
    header[0x12] = 1 if has_delta_trans else 0  # bDelta3D
    header[0x13] = 0  # bLeftHandGripIK
    struct.pack_into("<I", header, 0x14, 0)  # streamedFileSize

    # Donor-safe semantic layout: full static rot/trans coverage on the target rig.
    for bc in range(10):
        header[0x18 + bc] = 0
    if num_bones > 0:
        header[0x18 + 0] = 0          # NoneRotated
        header[0x18 + 4] = num_bones  # NormalStaticRotated
        header[0x18 + 5] = 0          # NormalTranslated
        header[0x18 + 6] = 0          # PreciseTranslated
        header[0x18 + 7] = num_bones  # StaticTranslated
        header[0x18 + 8] = 0          # NoneTranslated
        header[0x18 + 9] = num_bones  # TotalBoneCount

    notify_count = 0 if BO3_DISABLE_NOTIFY else int(donor_header["notifyCount"])
    header[0x22] = notify_count
    header[0x23] = int(BO3_FORCE_ASSETTYPE or int(donor_header["assetType"]))  # match donor weapon semantic lane
    header[0x24] = 0  # isDefault

    struct.pack_into("<I", header, 0x28, 0)  # randomDataShortCount
    struct.pack_into("<I", header, 0x2C, 0)  # indexCount
    struct.pack_into("<f", header, 0x30, framerate)
    effective_numframes = numframes if has_delta else 2
    if has_delta and effective_numframes > 2:
        # Long custom clips should advance at their authored frame rate; the
        # old framerate/numframes formula makes them effectively static live.
        frequency = framerate
    else:
        frequency = (framerate / float(effective_numframes)) if effective_numframes > 0 else 1.0
    if BO3_IDLE_DIAG_FREQUENCY > 0.0:
        frequency = float(BO3_IDLE_DIAG_FREQUENCY)
    struct.pack_into("<f", header, 0x34, frequency)
    struct.pack_into("<f", header, 0x38, 0.0)
    struct.pack_into("<f", header, 0x3C, 0.0)

    struct.pack_into("<I", header, 0x40, PTR_FOLLOWING if num_bones > 0 else PTR_NULL)        # names
    struct.pack_into("<I", header, 0x44, PTR_FOLLOWING if data_byte_count > 0 else PTR_NULL)   # dataByte
    struct.pack_into("<I", header, 0x48, PTR_FOLLOWING if data_short_count > 0 else PTR_NULL)  # dataShort
    struct.pack_into("<I", header, 0x4C, PTR_FOLLOWING if data_int_count > 0 else PTR_NULL)    # dataInt
    struct.pack_into("<I", header, 0x50, PTR_NULL)  # randomDataShort
    struct.pack_into("<I", header, 0x54, PTR_NULL)  # randomDataByte
    struct.pack_into("<I", header, 0x58, PTR_NULL)  # randomDataInt
    struct.pack_into("<I", header, 0x5C, PTR_NULL)  # indices
    struct.pack_into("<I", header, 0x60, PTR_FOLLOWING if notify_count > 0 else PTR_NULL)  # notify
    struct.pack_into("<I", header, 0x64, PTR_FOLLOWING if has_delta else PTR_NULL)  # deltaPart

    # IMPORTANT: Pointer-follow stream order must match the real T6 loader.
    # See `_build/strict_xanim_parser.py` which models the serialized order as:
    #   name -> names -> notify -> deltaPart -> dataByte -> dataShort -> dataInt -> ... -> indices
    # (with notify/indices often absent). Getting this wrong can crash the engine
    # and also breaks OAT Unlinker parsing.
    data = bytearray()
    data.extend(name.encode("ascii", errors="ignore") + b"\x00")

    # names (uint16 scriptstring indices)
    for idx in bone_string_indices:
        data.extend(struct.pack("<H", idx))

    if notify_count > 0:
        _append_remapped_donor_notify(
            data,
            donor_header,
            donor_sections,
            donor_raw,
            donor_index_to_string,
            string_table,
            donor_name,
        )

    # deltaPart (serialized before dataByte/dataShort/dataInt)
    if has_delta:
        data.extend(delta_bytes)

    # dataByte (uint8 bone ids for translations when boneCount <= 255)
    if data_byte_count > 0:
        data.extend(bytes(trans_bone_ids_u8))

    # dataShort (int16 quats + optional uint16 bone ids when boneCount > 255)
    if data_short_count > 0:
        for q in rot_quats_i16:
            data.extend(struct.pack("<h", q))
        for bone_id in trans_bone_ids_u16:
            data.extend(struct.pack("<H", bone_id))

    # dataInt (float32 translations)
    if data_int_count > 0:
        for v in trans_vec_f32:
            data.extend(struct.pack("<f", v))

    return bytes(header), bytes(data)


def _build_bo3_frames_xanimparts_data(anim, string_table):
    name = anim.get("name", "")
    if name in BO3_FRAMES_TARGETS:
        return _build_bo3_frames_idle_xanimparts_data(anim, string_table)
    if BO3_FRAMES_FALLBACK_MODE == "donor_clone":
        return _build_donor_clone_xanimparts_data(anim, string_table)
    if BO3_FRAMES_FALLBACK_MODE == "stub":
        return _build_stub_xanimparts_data(anim, string_table)
    return _build_static_pose_xanimparts_data(anim, string_table)


# ============================================================================
# XAnimParts Binary Builder
# ============================================================================

def quat_to_int16(q):
    """Convert quaternion component [-1,1] to int16 [-32767,32767]."""
    return max(-32767, min(32767, int(round(q * 32767.0))))


def _sanitize_float(v, fallback=0.0):
    if isinstance(v, (int, float)) and math.isfinite(v):
        return float(v)
    return float(fallback)


def _force_loop_for_anim(anim_name: str) -> bool:
    key = str(anim_name or "").strip().lower()
    if not key:
        return False
    if "idle" in key:
        return True
    if key in FORCE_LOOP_ANIM_NAMES:
        return True
    for token in FORCE_LOOP_ANIM_NAMES:
        if token.endswith("*") and key.startswith(token[:-1]):
            return True
    return False


def _pick_frame(anim):
    if anim['frames']:
        k = min(anim['frames'].keys())
        return anim['frames'][k]
    return {}


def _append_align(buf, alignment):
    if alignment <= 1:
        return
    while (len(buf) % alignment) != 0:
        buf.append(0)


def _build_stub_xanimparts_data(anim, string_table):
    """
    Build diagnostic/stub XAnimParts serialized data.

    Returns (header_bytes, pointer_data_bytes).
    """
    name = anim['name']
    parts = anim['parts']
    num_bones = len(parts)
    framerate = anim['framerate']

    if DIAG_ZERO_BONES:
        num_bones = 0

    # Register bone names in string table
    bone_string_indices = []
    for bone_name in parts:
        if DIAG_ZERO_BONES:
            break
        if bone_name not in string_table:
            string_table[bone_name] = len(string_table)
        bone_string_indices.append(string_table[bone_name])

    header = bytearray(104)

    struct.pack_into('<I', header, 0x00, PTR_FOLLOWING)   # name
    struct.pack_into('<H', header, 0x04, 0)               # dataByteCount
    struct.pack_into('<H', header, 0x06, 0)               # dataShortCount
    struct.pack_into('<H', header, 0x08, 0)               # dataIntCount
    struct.pack_into('<H', header, 0x0A, 0)               # randomDataByteCount
    struct.pack_into('<H', header, 0x0C, 0)               # randomDataIntCount
    struct.pack_into('<H', header, 0x0E, max(0, min(65535, int(STUB_NUMFRAMES))))  # numframes

    header[0x10] = 1 if _force_loop_for_anim(name) else 0  # bLoop
    header[0x11] = 0  # bDelta
    header[0x12] = 0  # bDelta3D
    header[0x13] = 0  # bLeftHandGripIK
    struct.pack_into('<I', header, 0x14, 0)  # streamedFileSize

    # boneCount[10] categories:
    # [0]=NoneRotated [1]=TwoDRotated [2]=NormalRotated
    # [3]=TwoDStaticRotated [4]=NormalStaticRotated
    # [5]=NormalTranslated [6]=PreciseTranslated [7]=StaticTranslated
    # [8]=NoneTranslated [9]=TotalBoneCount
    for bc in range(10):
        header[0x18 + bc] = 0

    if BONE_COUNT_PROFILE == "zero":
        # Full zero profile for diagnostics.
        pass
    elif BONE_COUNT_PROFILE == "split_none":
        # Legacy interpretation: explicit none-rot and none-translated counts.
        header[0x18 + 0] = num_bones
        header[0x18 + 8] = num_bones
        header[0x18 + 9] = num_bones
    else:
        # Monotonic cumulative profile for "all bones unanimated" stubs.
        # This is safer for engines that interpret these as category boundaries.
        for off in (0, 1, 2, 3, 4):
            header[0x18 + off] = num_bones
        header[0x18 + 5] = 0
        header[0x18 + 6] = 0
        header[0x18 + 7] = 0
        header[0x18 + 8] = num_bones
        header[0x18 + 9] = num_bones

    header[0x22] = 0   # notifyCount
    header[0x23] = 2   # assetType (matches vanilla real XAnimParts in T6)
    header[0x24] = 1 if STUB_IS_DEFAULT else 0  # isDefault
    # 0x25-0x27: padding

    struct.pack_into('<I', header, 0x28, 0)            # randomDataShortCount
    struct.pack_into('<I', header, 0x2C, 0)            # indexCount
    struct.pack_into('<f', header, 0x30, float(framerate))  # framerate
    struct.pack_into('<f', header, 0x34, 1.0)               # frequency
    struct.pack_into('<f', header, 0x38, 0.0)               # primedLength
    struct.pack_into('<f', header, 0x3C, 0.0)               # loopEntryTime

    # Pointer fields - only name and names are non-null
    if num_bones > 0:
        struct.pack_into('<I', header, 0x40, PTR_FOLLOWING)  # names
    else:
        struct.pack_into('<I', header, 0x40, PTR_NULL)       # names
    struct.pack_into('<I', header, 0x44, PTR_NULL)       # dataByte
    struct.pack_into('<I', header, 0x48, PTR_NULL)       # dataShort
    struct.pack_into('<I', header, 0x4C, PTR_NULL)       # dataInt
    struct.pack_into('<I', header, 0x50, PTR_NULL)       # randomDataShort
    struct.pack_into('<I', header, 0x54, PTR_NULL)       # randomDataByte
    struct.pack_into('<I', header, 0x58, PTR_NULL)       # randomDataInt
    struct.pack_into('<I', header, 0x5C, PTR_NULL)       # indices
    struct.pack_into('<I', header, 0x60, PTR_NULL)       # notify
    struct.pack_into('<I', header, 0x64, PTR_NULL)       # deltaPart

    data = bytearray()

    # 1. Name string
    data.extend(name.encode('ascii') + b'\x00')

    # 2. Names array - uint16 script string indices
    if num_bones > 0:
        for idx in bone_string_indices:
            data.extend(struct.pack('<H', idx))

    return bytes(header), bytes(data)


def _build_static_pose_xanimparts_data(anim, string_table):
    """
    Build XAnimParts using frame-0 static channels:
      - NormalStaticRotatedBoneCount = N
      - StaticTranslatedBoneCount = N
      - No dynamic/random/index tables
    """
    name = anim['name']
    parts = anim['parts']
    framerate = max(1.0, float(anim.get('framerate', 30)))
    src_numframes = int(anim.get('numframes', 1))
    numframes = max(1, min(65535, src_numframes if src_numframes > 0 else 1))
    num_bones = len(parts)

    if DIAG_ZERO_BONES:
        num_bones = 0

    bone_string_indices = []
    for bone_name in parts[:num_bones]:
        if bone_name not in string_table:
            string_table[bone_name] = len(string_table)
        bone_string_indices.append(string_table[bone_name])

    # Static channels.
    rot_quats_i16 = []   # 4 * N int16
    trans_vec_f32 = []   # 3 * N float
    trans_bone_ids_u8 = []
    trans_bone_ids_u16 = []
    static_diag_key = str(BO3_IDLE_DIAG_STATIC_BONE).strip().lower()
    static_diag_translate = [float(v) for v in (BO3_IDLE_DIAG_STATIC_TRANSLATE or [0.0, 0.0, 0.0])[:3]]
    static_diag_applied = False

    for bone_idx in range(num_bones):
        bone_name = str(parts[bone_idx])
        quat, off = _frame0_bone_quat_and_offset(anim, bone_idx, zero_local_basis_offset=True)
        qx, qy, qz, qw = (_sanitize_float(v) for v in quat)
        ox, oy, oz = (_sanitize_float(v) for v in off[:3])
        if static_diag_key and bone_name.strip().lower() == static_diag_key and any(abs(v) > 1e-6 for v in static_diag_translate):
            ox = _sanitize_float(ox + static_diag_translate[0])
            oy = _sanitize_float(oy + static_diag_translate[1])
            oz = _sanitize_float(oz + static_diag_translate[2])
            static_diag_applied = True

        rot_quats_i16.extend([
            quat_to_int16(qx),
            quat_to_int16(qy),
            quat_to_int16(qz),
            quat_to_int16(qw),
        ])
        trans_vec_f32.extend([ox, oy, oz])

        if num_bones > 255:
            trans_bone_ids_u16.append(bone_idx)
        else:
            trans_bone_ids_u8.append(bone_idx & 0xFF)

    if static_diag_applied:
        print(
            f"  static_pose diagnostic ({anim.get('name','?')}): "
            f"bone={BO3_IDLE_DIAG_STATIC_BONE} translate={static_diag_translate}"
        )

    data_byte_count = len(trans_bone_ids_u8)
    data_short_count = len(rot_quats_i16) + len(trans_bone_ids_u16)
    data_int_count = len(trans_vec_f32)  # count of 32-bit items

    header = bytearray(104)
    struct.pack_into('<I', header, 0x00, PTR_FOLLOWING)  # name
    struct.pack_into('<H', header, 0x04, data_byte_count)
    struct.pack_into('<H', header, 0x06, data_short_count)
    struct.pack_into('<H', header, 0x08, data_int_count)
    struct.pack_into('<H', header, 0x0A, 0)  # randomDataByteCount
    struct.pack_into('<H', header, 0x0C, 0)  # randomDataIntCount
    struct.pack_into('<H', header, 0x0E, numframes)

    # Keep these conservative for stability while validating the compiler.
    header[0x10] = 1 if _force_loop_for_anim(name) else 0  # bLoop
    header[0x11] = 0  # bDelta
    header[0x12] = 0  # bDelta3D
    header[0x13] = 0  # bLeftHandGripIK
    struct.pack_into('<I', header, 0x14, 0)  # streamedFileSize

    # boneCount categories.
    # [0]=NoneRotated [1]=TwoDRotated [2]=NormalRotated
    # [3]=TwoDStaticRotated [4]=NormalStaticRotated
    # [5]=NormalTranslated [6]=PreciseTranslated [7]=StaticTranslated
    # [8]=NoneTranslated [9]=TotalBoneCount
    for bc in range(10):
        header[0x18 + bc] = 0
    if num_bones > 0:
        header[0x18 + 4] = num_bones  # NormalStaticRotated (all bones)
        # [5],[6] = 0 -> no NormalTranslated or PreciseTranslated
        header[0x18 + 7] = num_bones  # StaticTranslated (all bones)
        # [8] = 0 -> no NoneTranslated
        header[0x18 + 9] = num_bones  # Total

    header[0x22] = 0  # notifyCount
    header[0x23] = 2  # assetType (matches vanilla real XAnimParts in T6)
    header[0x24] = 0  # isDefault

    struct.pack_into('<I', header, 0x28, 0)  # randomDataShortCount
    struct.pack_into('<I', header, 0x2C, 0)  # indexCount
    struct.pack_into('<f', header, 0x30, framerate)
    struct.pack_into('<f', header, 0x34, 1.0)
    struct.pack_into('<f', header, 0x38, 0.0)
    struct.pack_into('<f', header, 0x3C, 0.0)

    # Pointers in serialized order.
    struct.pack_into('<I', header, 0x40, PTR_FOLLOWING if num_bones > 0 else PTR_NULL)       # names
    struct.pack_into('<I', header, 0x44, PTR_FOLLOWING if data_byte_count > 0 else PTR_NULL) # dataByte
    struct.pack_into('<I', header, 0x48, PTR_FOLLOWING if data_short_count > 0 else PTR_NULL) # dataShort
    struct.pack_into('<I', header, 0x4C, PTR_FOLLOWING if data_int_count > 0 else PTR_NULL)   # dataInt
    struct.pack_into('<I', header, 0x50, PTR_NULL)  # randomDataShort
    struct.pack_into('<I', header, 0x54, PTR_NULL)  # randomDataByte
    struct.pack_into('<I', header, 0x58, PTR_NULL)  # randomDataInt
    struct.pack_into('<I', header, 0x5C, PTR_NULL)  # indices
    struct.pack_into('<I', header, 0x60, PTR_NULL)  # notify
    struct.pack_into('<I', header, 0x64, PTR_NULL)  # deltaPart

    data = bytearray()

    # 1) name
    data.extend(name.encode('ascii', errors='ignore') + b'\x00')

    # 2) names (script string indices)
    for idx in bone_string_indices:
        data.extend(struct.pack('<H', idx))

    # 3) notify (none)
    # 4) deltaPart (none)

    # 5) dataByte (translation bone IDs for <=255 skeletons)
    if data_byte_count > 0:
        data.extend(bytes(trans_bone_ids_u8))

    # 6) dataShort (static quats, then optional u16 translation bone IDs)
    # Do NOT add implicit alignment padding here; zone loader consumes arrays
    # strictly by count and order.
    if data_short_count > 0:
        for q in rot_quats_i16:
            data.extend(struct.pack('<h', q))
        for bone_id in trans_bone_ids_u16:
            data.extend(struct.pack('<H', bone_id))

    # 7) dataInt (static translations as float bits)
    # Do NOT add implicit alignment padding here; zone loader consumes arrays
    # strictly by count and order.
    if data_int_count > 0:
        for v in trans_vec_f32:
            data.extend(struct.pack('<f', v))

    return bytes(header), bytes(data)


def build_xanimparts_data(anim, string_table):
    if EMIT_MODE == "stub":
        return _build_stub_xanimparts_data(anim, string_table)
    if EMIT_MODE == "donor_template_static_pose":
        return _build_donor_template_static_pose_xanimparts_data(anim, string_table)
    if EMIT_MODE == "donor_semantic_static_pose":
        return _build_donor_semantic_static_pose_xanimparts_data(anim, string_table)
    if EMIT_MODE == "donor_clone":
        return _build_donor_clone_xanimparts_data(anim, string_table)
    if EMIT_MODE == "bo3_frames":
        return _build_bo3_frames_xanimparts_data(anim, string_table)
    return _build_static_pose_xanimparts_data(anim, string_table)


# ============================================================================
# Zone Builder
# ============================================================================

def count_insert_pointers(header_bytes):
    """Count PTR_FOLLOWING pointers in an XAnimParts header (insert pointer overhead)."""
    count = 0
    # Check all pointer fields in the 104-byte header
    ptr_offsets = [0x00, 0x40, 0x44, 0x48, 0x4C, 0x50, 0x54, 0x58, 0x5C, 0x60, 0x64]
    for off in ptr_offsets:
        val = struct.unpack_from('<I', header_bytes, off)[0]
        if val == PTR_FOLLOWING:
            count += 1
    return count


def build_zone_data(anims, zone_name):
    """Build the raw zone data stream (before XChunk processing).

    T6 Zone layout:
      1. XFile header (40 bytes): totalSize + externalSize + blockSizes[8]
      2. XAssetList RAW (24 bytes): loaded outside any block
      3. VIRTUAL block: scriptstring table + XAsset array
      4. TEMP block: XAnimParts struct + pointer-resolved payloads

    The standalone carrier must follow the same effective load contract that
    our minimal-zone experiments and patched-zone lane use:
      - the VIRTUAL stream is 4-byte aligned before the XAsset array
      - the TEMP-backed XAnimParts region contains the full serialized asset
        payload, not just the 104-byte header
      - the VIRTUAL block size must account for the hidden insert-pointer
        bookkeeping for every PTR_FOLLOWING field in the zone
    """
    string_table = {}  # name -> index
    asset_headers = []  # (header_bytes, data_bytes) per asset
    temp_insert_pointer_bytes = 0
    use_legacy_carrier_layout = EMIT_MODE in (
        "static_pose",
        "stub",
        "donor_clone",
        "donor_template_static_pose",
        "donor_semantic_static_pose",
    )

    # Build all assets and collect string table entries
    for anim in anims:
        header, data = build_xanimparts_data(anim, string_table)
        asset_headers.append((header, data))
        temp_insert_pointer_bytes += count_insert_pointers(header) * 4

    # Now build the complete zone data
    buf = bytearray()

    # ---- XFile Header (40 bytes) ----
    total_size_pos = len(buf)
    buf.extend(struct.pack('<I', 0))  # totalSize placeholder
    buf.extend(struct.pack('<I', 0))  # externalSize = 0

    block_sizes_pos = len(buf)
    for _ in range(XFILE_BLOCK_COUNT):
        buf.extend(struct.pack('<I', 0))

    content_start = len(buf)  # = 40

    # ---- RAW: XAssetList (24 bytes, NOT in any block) ----
    string_count = len(string_table)
    asset_count = len(anims)

    buf.extend(struct.pack('<i', string_count))                                      # stringList.count
    buf.extend(struct.pack('<I', PTR_FOLLOWING if string_count > 0 else PTR_NULL))   # stringList.strings
    buf.extend(struct.pack('<i', 0))                                                 # dependCount
    buf.extend(struct.pack('<I', PTR_NULL))                                          # depends
    buf.extend(struct.pack('<i', asset_count))                                       # assetCount
    buf.extend(struct.pack('<I', PTR_FOLLOWING if asset_count > 0 else PTR_NULL))    # assets

    # ---- VIRTUAL block data ----
    virtual_start = len(buf)

    # Script string pointer array + string data
    if string_count > 0:
        sorted_strings = sorted(string_table.items(), key=lambda x: x[1])
        for name, idx in sorted_strings:
            buf.extend(struct.pack('<I', PTR_FOLLOWING))
        for name, idx in sorted_strings:
            buf.extend(name.encode('ascii') + b'\x00')

    # Historical standalone custom-xanim carriers that OAT can actually load in
    # this repo do not stream-pad between the scriptstring table and the XAsset
    # array. The bo3_frames lane needs the tighter explicit layout below, but
    # donor/static lanes should stay on the proven broad-carrier contract.
    if not use_legacy_carrier_layout:
        _append_align(buf, 4)

    # XAsset array entries
    if asset_count > 0:
        for i in range(asset_count):
            buf.extend(struct.pack('<i', ASSET_TYPE_XANIMPARTS))
            buf.extend(struct.pack('<I', PTR_FOLLOWING))

    virtual_stream_size = len(buf) - virtual_start

    # ---- Per-asset data (full serialized asset goes to TEMP) ----
    temp_start = len(buf)
    for header, data in asset_headers:
        buf.extend(header)
        buf.extend(data)

    temp_stream_size = len(buf) - temp_start

    # ---- Patch header ----
    total_size = len(buf) - content_start
    struct.pack_into('<I', buf, total_size_pos, total_size)

    block_sizes = [0] * XFILE_BLOCK_COUNT
    if use_legacy_carrier_layout:
        # Broad-carrier contract used by the known-good standalone xanim FFs in
        # this repo. It is intentionally loose, but OAT can --load it reliably
        # for donor/static payloads.
        block_sizes[BLOCK_TEMP] = 104
        block_sizes[BLOCK_VIRTUAL] = total_size
        insert_overhead = total_size - virtual_stream_size
    else:
        # Hidden XBlock insert-pointer bookkeeping is charged against VIRTUAL
        # for every PTR_FOLLOWING the loader must materialize while walking this
        # zone.
        raw_insert_pointer_bytes = 0
        if string_count > 0:
            raw_insert_pointer_bytes += 4  # XAssetList.stringList.strings
        if asset_count > 0:
            raw_insert_pointer_bytes += 4  # XAssetList.assets
            raw_insert_pointer_bytes += asset_count * 4  # XAsset.header
        if string_count > 0:
            raw_insert_pointer_bytes += string_count * 4  # scriptstring pointer array

        virtual_insert_pointer_bytes = raw_insert_pointer_bytes + temp_insert_pointer_bytes
        block_sizes[BLOCK_TEMP] = temp_stream_size
        block_sizes[BLOCK_VIRTUAL] = virtual_stream_size + virtual_insert_pointer_bytes
        insert_overhead = virtual_insert_pointer_bytes

    for i in range(XFILE_BLOCK_COUNT):
        struct.pack_into('<I', buf, block_sizes_pos + i * 4, block_sizes[i])

    print(
        f"  TEMP(block 0)={block_sizes[BLOCK_TEMP]}, "
        f"VIRTUAL(block 5)={block_sizes[BLOCK_VIRTUAL]} "
        f"(virtual_stream={virtual_stream_size}, "
        f"insert_overhead={insert_overhead}, "
        f"layout={'legacy' if use_legacy_carrier_layout else 'tight'})"
    )
    print(f"  totalSize={total_size}")

    return bytes(buf)


def write_zone_file(raw_data, zone_name, output_path, crypto_seed=None):
    """Write the complete .ff zone file with XChunk encryption."""
    seed_name = (crypto_seed or zone_name).strip()
    # Use shared writer when available to avoid stream-format drift.
    writer_cls = SharedXChunkWriter or XChunkWriter
    xchunk = writer_cls(seed_name)

    # Write all data through XChunk pipeline
    xchunk.write_data(raw_data)

    encrypted_stream = xchunk.get_output()

    # Write file
    with open(output_path, 'wb') as f:
        # Zone header (12 bytes)
        f.write(T6_ZONE_MAGIC_UNSIGNED)
        f.write(struct.pack('<I', T6_ZONE_VERSION))

        # Encrypted XChunk stream
        f.write(encrypted_stream)

        # File suffix: 0x40 zero bytes aligned to 0x40
        padding_needed = 0x40 - (f.tell() % 0x40)
        if padding_needed < 0x40:
            padding_needed += 0x40
        f.write(b'\x00' * padding_needed)

    return os.path.getsize(output_path)


# ============================================================================
# Main
# ============================================================================

def parse_args():
    parser = argparse.ArgumentParser(description="Compile xanim_export files into a standalone T6 .ff zone.")
    parser.add_argument(
        "--xanim-dir",
        default=r"z:\Games\pluto_t6_full_game\_build\panzer_work\so_zsurvival_zm_transit\xanim_export",
        help="Directory containing xanim_export files.",
    )
    parser.add_argument(
        "--pattern",
        default="vm_thunder_gun_*.xanim_export",
        help="Glob pattern relative to --xanim-dir.",
    )
    parser.add_argument(
        "--output-dir",
        default=r"z:\Games\pluto_t6_full_game\_build\panzer_work\output",
        help="Output directory for generated .ff.",
    )
    parser.add_argument(
        "--zone-name",
        default="thundergun_xanims",
        help="Output fastfile name (without extension).",
    )
    parser.add_argument(
        "--crypto-seed",
        default=None,
        help="Optional fastfile crypto seed name (defaults to --zone-name).",
    )
    parser.add_argument(
        "--emit-mode",
        choices=["static_pose", "donor_template_static_pose", "donor_semantic_static_pose", "stub", "donor_clone", "bo3_frames"],
        default="static_pose",
        help="Animation emit mode: static_pose writes frame-0 static channels; donor_template_static_pose keeps donor runtime semantics while filling static source pose; donor_semantic_static_pose uses donor-safe weapon semantics with target-rig names; stub writes no channels; donor_clone copies real donor payloads; bo3_frames emits idle keyframes + fallback mode for others.",
    )
    parser.add_argument(
        "--donor-ff",
        default=r"z:\Games\pluto_t6_full_game\_build\ff_backup\20260213-125735\zm_transit.ff",
        help="Donor fastfile path for --emit-mode donor_clone.",
    )
    parser.add_argument(
        "--donor-zone-name",
        default="zm_transit",
        help="Zone name used to decrypt --donor-ff.",
    )
    parser.add_argument(
        "--donor-asset",
        default="viewmodel_ak74u_t6_idle",
        help="Fallback donor asset name for unresolved target mappings.",
    )
    parser.add_argument(
        "--donor-override",
        action="append",
        default=[],
        help="Per-target donor mapping in form target_name=donor_name. Repeatable.",
    )
    parser.add_argument(
        "--donor-fallback-idle",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="When donor target is missing, fall back to --donor-asset if enabled.",
    )
    parser.add_argument(
        "--require-no-donor-fallback",
        action="store_true",
        help="Fail compilation if any target animation used donor fallback.",
    )
    parser.add_argument(
        "--bo3-frames-targets",
        nargs="*",
        default=["vm_thunder_gun_idle"],
        help="When --emit-mode bo3_frames, animation names to encode via bo3_frames path.",
    )
    parser.add_argument(
        "--bo3-fallback-mode",
        choices=["donor_clone", "static_pose", "stub"],
        default="donor_clone",
        help="When --emit-mode bo3_frames, emit mode for non-target animations.",
    )
    parser.add_argument(
        "--bo3-root-bone-priority",
        nargs="*",
        default=["tag_weapon_right", "j_mainroot", "tag_player", "tag_camera", "tag_origin"],
        help="Root-bone priority list used to derive bo3_frames idle deltaPart track.",
    )
    parser.add_argument(
        "--bo3-nonroot-bone-priority",
        nargs="*",
        default=["j_gun", "j_bolt", "j_clip", "j_stripper", "j_switch", "j_pump", "j_drum", "j_mag"],
        help="Preferred visible non-root bones for bo3_frames idle delta source.",
    )
    parser.add_argument(
        "--bo3-motion-bone-report-top",
        type=int,
        default=3,
        help="How many top-motion non-root bones to log in bo3_frames idle path.",
    )
    parser.add_argument(
        "--bo3-idle-diagnostic-bone",
        default="",
        help="Optional preferred bone for bo3_frames idle diagnostic motion.",
    )
    parser.add_argument(
        "--bo3-idle-diagnostic-translate",
        nargs=3,
        type=float,
        default=[0.0, 0.0, 0.0],
        metavar=("X", "Y", "Z"),
        help="Optional additive sinusoidal translation diagnostic applied to the chosen bo3_frames idle delta bone.",
    )
    parser.add_argument(
        "--bo3-idle-diagnostic-frequency",
        type=float,
        default=0.0,
        help="Optional playback frequency override for bo3_frames idle diagnostics.",
    )
    parser.add_argument(
        "--bo3-idle-static-bone",
        default="",
        help="Optional bone for a static pose translation diagnostic in bo3_frames idle mode.",
    )
    parser.add_argument(
        "--bo3-idle-static-translate",
        nargs=3,
        type=float,
        default=[0.0, 0.0, 0.0],
        metavar=("X", "Y", "Z"),
        help="Optional additive translation applied to the chosen bo3_frames idle static baseline bone.",
    )
    parser.add_argument(
        "--diag-zero-bones",
        action="store_true",
        help="Force zero bones for diagnostics.",
    )
    parser.add_argument(
        "--force-identity-pose",
        action="store_true",
        help="Force all emitted static-pose channels to identity rotation and zero translation.",
    )
    parser.add_argument(
        "--stub-numframes",
        type=int,
        default=0,
        help="Stub numframes value written into XAnimParts.",
    )
    parser.add_argument(
        "--stub-is-default",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Set XAnimParts::isDefault=1 in emitted assets.",
    )
    parser.add_argument(
        "--bone-count-profile",
        choices=["split_none", "cumulative_none", "zero"],
        default="cumulative_none",
        help="boneCount[10] profile for emitted stub XAnimParts.",
    )
    parser.add_argument(
        "--neutralize-bones",
        nargs="*",
        default=["tag_player", "tag_camera", "tag_origin"],
        help="Bone names to neutralize (offset=0, rot=identity) before emit.",
    )
    parser.add_argument(
        "--ensure-bones",
        nargs="*",
        default=["tag_view", "tag_camera", "tag_player", "tag_origin"],
        help="Bone names to inject into PART/frame data when missing.",
    )
    parser.add_argument(
        "--keep-bones-file",
        default="",
        help="JSON file containing allowed target bone names (present_anim_bones or joint_names).",
    )
    parser.add_argument(
        "--no-semantic-fill",
        action="store_true",
        help="Disable semantic state fill (missing/empty required states from idle).",
    )
    return parser.parse_args()


def main():
    global EMIT_MODE, DIAG_ZERO_BONES, FORCE_IDENTITY_POSE, STUB_NUMFRAMES, STUB_IS_DEFAULT, BONE_COUNT_PROFILE, NEUTRALIZE_BONES
    global DONOR_FF, DONOR_ZONE_NAME, DONOR_DEFAULT_ASSET, DONOR_OVERRIDE_MAP, DONOR_CONTEXT
    global DONOR_FALLBACK_IDLE, DONOR_MAP_HITS, DONOR_MAP_FALLBACKS, REQUIRE_NO_DONOR_FALLBACK
    global BO3_FRAMES_TARGETS, BO3_FRAMES_FALLBACK_MODE, BO3_ROOT_BONE_PRIORITY
    global BO3_NONROOT_BONE_PRIORITY, BO3_MOTION_BONE_REPORT_TOP
    global BO3_IDLE_DIAG_BONE, BO3_IDLE_DIAG_TRANSLATE, BO3_IDLE_DIAG_FREQUENCY
    global BO3_IDLE_DIAG_STATIC_BONE, BO3_IDLE_DIAG_STATIC_TRANSLATE
    global BO3_DISABLE_NOTIFY, BO3_FORCE_ASSETTYPE

    args = parse_args()
    EMIT_MODE = str(args.emit_mode)
    DIAG_ZERO_BONES = bool(args.diag_zero_bones)
    FORCE_IDENTITY_POSE = bool(args.force_identity_pose)
    STUB_NUMFRAMES = max(0, int(args.stub_numframes))
    STUB_IS_DEFAULT = bool(args.stub_is_default)
    BONE_COUNT_PROFILE = str(args.bone_count_profile)
    NEUTRALIZE_BONES = set(str(x).strip() for x in (args.neutralize_bones or []) if str(x).strip())
    DONOR_FF = os.path.abspath(args.donor_ff)
    DONOR_ZONE_NAME = str(args.donor_zone_name).strip() or "zm_transit"
    DONOR_DEFAULT_ASSET = str(args.donor_asset).strip() or "viewmodel_ak74u_t6_idle"
    DONOR_OVERRIDE_MAP = _parse_donor_override_args(args.donor_override)
    DONOR_FALLBACK_IDLE = bool(args.donor_fallback_idle)
    REQUIRE_NO_DONOR_FALLBACK = bool(args.require_no_donor_fallback)
    DONOR_CONTEXT = None
    DONOR_MAP_HITS = 0
    DONOR_MAP_FALLBACKS = 0
    BO3_FRAMES_TARGETS = set(str(x).strip() for x in (args.bo3_frames_targets or []) if str(x).strip())
    BO3_FRAMES_FALLBACK_MODE = str(args.bo3_fallback_mode)
    BO3_ROOT_BONE_PRIORITY = [str(x).strip() for x in (args.bo3_root_bone_priority or []) if str(x).strip()]
    BO3_NONROOT_BONE_PRIORITY = [str(x).strip() for x in (args.bo3_nonroot_bone_priority or []) if str(x).strip()]
    BO3_MOTION_BONE_REPORT_TOP = max(1, int(args.bo3_motion_bone_report_top))
    BO3_IDLE_DIAG_BONE = str(args.bo3_idle_diagnostic_bone).strip()
    BO3_IDLE_DIAG_TRANSLATE = [float(v) for v in (args.bo3_idle_diagnostic_translate or [0.0, 0.0, 0.0])[:3]]
    BO3_IDLE_DIAG_FREQUENCY = max(0.0, float(args.bo3_idle_diagnostic_frequency or 0.0))
    BO3_IDLE_DIAG_STATIC_BONE = str(args.bo3_idle_static_bone).strip()
    BO3_IDLE_DIAG_STATIC_TRANSLATE = [float(v) for v in (args.bo3_idle_static_translate or [0.0, 0.0, 0.0])[:3]]
    BO3_DISABLE_NOTIFY = bool(os.environ.get("ROGUE_BO3_DISABLE_NOTIFY", "1" if BO3_DISABLE_NOTIFY else "0") not in ("0", "false", "False", ""))
    try:
        BO3_FORCE_ASSETTYPE = int(str(os.environ.get("ROGUE_BO3_FORCE_ASSETTYPE", str(BO3_FORCE_ASSETTYPE)) or "0").strip() or "0")
    except Exception:
        BO3_FORCE_ASSETTYPE = 0
    keep_bones = load_keep_bones_from_file(args.keep_bones_file) if str(args.keep_bones_file).strip() else []

    xanim_dir = os.path.abspath(args.xanim_dir)
    output_dir = os.path.abspath(args.output_dir)
    zone_name = args.zone_name.strip() or "thundergun_xanims"
    output_ff = os.path.join(output_dir, f"{zone_name}.ff")
    crypto_seed = (args.crypto_seed.strip() if isinstance(args.crypto_seed, str) and args.crypto_seed.strip() else zone_name)

    pattern = os.path.join(xanim_dir, args.pattern)
    files = sorted(glob.glob(pattern, recursive=True))

    if not files:
        print("ERROR: No xanim_export files found!")
        return False

    print(f"Found {len(files)} xanim_export files")
    print(f"  xanim_dir={xanim_dir}")
    print(f"  pattern={args.pattern}")
    print(f"  emit_mode={EMIT_MODE}")
    print(f"  stub_numframes={STUB_NUMFRAMES}")
    print(f"  stub_is_default={1 if STUB_IS_DEFAULT else 0}")
    print(f"  diag_zero_bones={1 if DIAG_ZERO_BONES else 0}")
    print(f"  force_identity_pose={1 if FORCE_IDENTITY_POSE else 0}\n")
    print(f"  bone_count_profile={BONE_COUNT_PROFILE}\n")
    print(f"  crypto_seed={crypto_seed}\n")
    if EMIT_MODE in ("donor_clone", "donor_template_static_pose", "donor_semantic_static_pose", "bo3_frames"):
        print(f"  donor_ff={DONOR_FF}")
        print(f"  donor_zone_name={DONOR_ZONE_NAME}")
        print(f"  donor_asset={DONOR_DEFAULT_ASSET}")
        print(f"  donor_fallback_idle={1 if DONOR_FALLBACK_IDLE else 0}")
        print(f"  require_no_donor_fallback={1 if REQUIRE_NO_DONOR_FALLBACK else 0}")
        if DONOR_OVERRIDE_MAP:
            print(f"  donor_override_count={len(DONOR_OVERRIDE_MAP)}")
        print("")
    if EMIT_MODE == "bo3_frames":
        print(f"  bo3_frames_targets={sorted(BO3_FRAMES_TARGETS)}")
        print(f"  bo3_fallback_mode={BO3_FRAMES_FALLBACK_MODE}")
        if BO3_ROOT_BONE_PRIORITY:
            print(f"  bo3_root_bone_priority={BO3_ROOT_BONE_PRIORITY}")
        if BO3_NONROOT_BONE_PRIORITY:
            print(f"  bo3_nonroot_bone_priority={BO3_NONROOT_BONE_PRIORITY}")
        print(f"  bo3_motion_bone_report_top={BO3_MOTION_BONE_REPORT_TOP}")
        if BO3_IDLE_DIAG_BONE:
            print(f"  bo3_idle_diagnostic_bone={BO3_IDLE_DIAG_BONE}")
        if any(abs(v) > 1e-6 for v in BO3_IDLE_DIAG_TRANSLATE):
            print(f"  bo3_idle_diagnostic_translate={BO3_IDLE_DIAG_TRANSLATE}")
        if BO3_IDLE_DIAG_FREQUENCY > 0.0:
            print(f"  bo3_idle_diagnostic_frequency={BO3_IDLE_DIAG_FREQUENCY}")
        if BO3_IDLE_DIAG_STATIC_BONE:
            print(f"  bo3_idle_static_bone={BO3_IDLE_DIAG_STATIC_BONE}")
        if any(abs(v) > 1e-6 for v in BO3_IDLE_DIAG_STATIC_TRANSLATE):
            print(f"  bo3_idle_static_translate={BO3_IDLE_DIAG_STATIC_TRANSLATE}")
        print(f"  bo3_disable_notify={1 if BO3_DISABLE_NOTIFY else 0}")
        if BO3_FORCE_ASSETTYPE:
            print(f"  bo3_force_assettype={BO3_FORCE_ASSETTYPE}")
        print("")
    if NEUTRALIZE_BONES:
        print(f"  neutralize_bones={sorted(NEUTRALIZE_BONES)}\n")
    ensure_bones = [str(x).strip() for x in (args.ensure_bones or []) if str(x).strip()]
    if keep_bones:
        keep_bone_set = {name.lower() for name in keep_bones}
        ensure_bones = [name for name in ensure_bones if name.lower() in keep_bone_set]
        NEUTRALIZE_BONES = {name for name in NEUTRALIZE_BONES if name.lower() in keep_bone_set}
        print(f"  keep_bones_file={args.keep_bones_file}")
        print(f"  keep_bone_count={len(keep_bones)}\n")
    if ensure_bones:
        print(f"  ensure_bones={sorted(set(ensure_bones))}\n")

    # Parse all xanims
    anims = []
    anims_by_name = {}
    max_parts = 0
    total_neutralized = 0
    total_pruned = 0
    for filepath in files:
        name = os.path.basename(filepath)
        anim = parse_xanim_export(filepath)
        if keep_bones:
            total_pruned += prune_anim_to_bones(anim, keep_bones)
        anims_by_name[anim["name"]] = anim
        nf = anim['numframes']
        if anim['numparts'] > max_parts:
            max_parts = anim['numparts']
        print(f"  {name}: {anim['numparts']} bones, {nf} frames, {anim['framerate']} fps")

    # Semantic state audit/fill before neutralization
    if not args.no_semantic_fill:
        filled_missing, replaced_empty = semantic_state_prepare(anims_by_name, REQUIRED_THUNDER_ANIMS)
        if filled_missing:
            print(f"\n  Semantic fill: added {len(filled_missing)} missing states from idle")
            print(f"    {filled_missing}")
        if replaced_empty:
            print(f"  Semantic fill: replaced {len(replaced_empty)} empty states from idle")
            print(f"    {replaced_empty}")
    else:
        print("\n  Semantic fill disabled (--no-semantic-fill)")

    injected_bone_tracks = 0
    for anim in anims_by_name.values():
        injected_bone_tracks += ensure_anim_has_bones(anim, ensure_bones)
    if ensure_bones:
        print(f"  Ensure bones: injected {injected_bone_tracks} missing PART entries across states")

    # Apply root/camera neutralization after semantic fill so cloned states are also sanitized.
    for anim in anims_by_name.values():
        total_neutralized += neutralize_anim_root_tracks(anim, NEUTRALIZE_BONES)
        anim["numframes"] = _normalize_numframes(anim)
        anims.append(anim)

    print(f"\n  Canonical vm skeleton size: {max_parts} bones")
    if keep_bones:
        print(f"  Pruned bone tracks: {total_pruned}")
    if NEUTRALIZE_BONES:
        print(f"  Neutralized track writes: {total_neutralized}")

    if EMIT_MODE in ("donor_clone", "donor_template_static_pose", "donor_semantic_static_pose", "bo3_frames"):
        needed_donor_assets = set([DONOR_DEFAULT_ASSET])
        for anim in anims:
            needed_donor_assets.add(str(anim["name"]))
            needed_donor_assets.add(_default_donor_asset_for_target(anim["name"]))
        print(f"\n  Loading donor context ({len(needed_donor_assets)} assets)...")
        DONOR_CONTEXT = _load_donor_context(
            DONOR_FF,
            DONOR_ZONE_NAME,
            sorted(needed_donor_assets),
        )
        missing = DONOR_CONTEXT.get("missing") or []
        if missing:
            print(f"  Donor assets missing: {len(missing)}")
            for nm in missing[:12]:
                print(f"    missing: {nm}")
            if len(missing) > 12:
                print(f"    ... {len(missing) - 12} more")

    # Build zone data
    print(f"\nBuilding zone '{zone_name}' with {len(anims)} xanim assets...")
    raw_data = build_zone_data(anims, zone_name)
    print(f"  Raw zone data: {len(raw_data):,} bytes")

    # Write encrypted zone file
    os.makedirs(output_dir, exist_ok=True)
    file_size = write_zone_file(raw_data, zone_name, output_ff, crypto_seed=crypto_seed)
    print(f"  Output: {output_ff} ({file_size:,} bytes)")
    if EMIT_MODE in ("donor_clone", "donor_template_static_pose", "donor_semantic_static_pose") or (EMIT_MODE == "bo3_frames" and BO3_FRAMES_FALLBACK_MODE == "donor_clone"):
        print(f"  donor_clone mapped={DONOR_MAP_HITS} fallback={DONOR_MAP_FALLBACKS}")
        if REQUIRE_NO_DONOR_FALLBACK and DONOR_MAP_FALLBACKS > 0:
            print("ERROR: donor fallback used while --require-no-donor-fallback is enabled")
            return False

    print(f"\nDone! To use:")
    print(f"  OAT: --load {output_ff}")
    print(f"  Plutonium: Copy to %localappdata%/Plutonium/storage/t6/zone/")
    return True


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
