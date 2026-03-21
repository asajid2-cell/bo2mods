import argparse
import ctypes
import math
import struct
from ctypes import wintypes


PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
MEM_COMMIT = 0x1000
PAGE_GUARD = 0x100
PAGE_NOACCESS = 0x01


class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BaseAddress", wintypes.LPVOID),
        ("AllocationBase", wintypes.LPVOID),
        ("AllocationProtect", wintypes.DWORD),
        ("RegionSize", ctypes.c_size_t),
        ("State", wintypes.DWORD),
        ("Protect", wintypes.DWORD),
        ("Type", wintypes.DWORD),
    ]


kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
OpenProcess = kernel32.OpenProcess
OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
OpenProcess.restype = wintypes.HANDLE

CloseHandle = kernel32.CloseHandle
CloseHandle.argtypes = [wintypes.HANDLE]
CloseHandle.restype = wintypes.BOOL

ReadProcessMemory = kernel32.ReadProcessMemory
ReadProcessMemory.argtypes = [
    wintypes.HANDLE,
    wintypes.LPCVOID,
    wintypes.LPVOID,
    ctypes.c_size_t,
    ctypes.POINTER(ctypes.c_size_t),
]
ReadProcessMemory.restype = wintypes.BOOL

VirtualQueryEx = kernel32.VirtualQueryEx
VirtualQueryEx.argtypes = [
    wintypes.HANDLE,
    wintypes.LPCVOID,
    ctypes.POINTER(MEMORY_BASIC_INFORMATION),
    ctypes.c_size_t,
]
VirtualQueryEx.restype = ctypes.c_size_t


def iter_regions(handle):
    mbi = MEMORY_BASIC_INFORMATION()
    addr = 0
    max_addr = 0x7FFFFFFF
    while addr < max_addr:
        result = VirtualQueryEx(handle, ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi))
        if not result:
            break
        base = ctypes.cast(mbi.BaseAddress, ctypes.c_void_p).value or 0
        size = int(mbi.RegionSize)
        yield {
            "base": base,
            "size": size,
            "state": int(mbi.State),
            "protect": int(mbi.Protect),
            "type": int(mbi.Type),
        }
        if size <= 0:
            break
        addr = base + size


def is_readable(region):
    if region["state"] != MEM_COMMIT:
        return False
    protect = region["protect"]
    if protect & PAGE_GUARD or protect & PAGE_NOACCESS:
        return False
    return True


def read_region(handle, base, size):
    buf = ctypes.create_string_buffer(size)
    read = ctypes.c_size_t()
    ok = ReadProcessMemory(handle, ctypes.c_void_p(base), buf, size, ctypes.byref(read))
    if not ok:
        return None
    return buf.raw[: read.value]


def find_process_id(name):
    import subprocess
    import json

    cmd = [
        "powershell",
        "-NoProfile",
        "-Command",
        (
            "Get-CimInstance Win32_Process | "
            f"Where-Object {{ $_.Name -ieq '{name}' }} | "
            "Select-Object -First 1 ProcessId | ConvertTo-Json -Compress"
        ),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0 or not proc.stdout.strip():
        return None
    try:
        payload = json.loads(proc.stdout)
    except Exception:
        return None
    if isinstance(payload, dict):
        return int(payload.get("ProcessId", 0)) or None
    return None


def search_ascii_occurrences(handle, needle):
    needle_bytes = needle.encode("ascii") + b"\x00"
    hits = []
    for region in iter_regions(handle):
        if not is_readable(region):
            continue
        if region["size"] > 32 * 1024 * 1024:
            continue
        data = read_region(handle, region["base"], region["size"])
        if not data:
            continue
        start = 0
        while True:
            idx = data.find(needle_bytes, start)
            if idx < 0:
                break
            hits.append(region["base"] + idx)
            start = idx + 1
    return hits


def search_pointer_refs(handle, value):
    needle = struct.pack("<I", value & 0xFFFFFFFF)
    hits = []
    for region in iter_regions(handle):
        if not is_readable(region):
            continue
        if region["size"] > 32 * 1024 * 1024:
            continue
        data = read_region(handle, region["base"], region["size"])
        if not data:
            continue
        start = 0
        while True:
            idx = data.find(needle, start)
            if idx < 0:
                break
            hits.append(region["base"] + idx)
            start = idx + 1
    return hits


def read_u32(data, off):
    return struct.unpack_from("<I", data, off)[0]


def read_u16(data, off):
    return struct.unpack_from("<H", data, off)[0]


def read_s8(data, off):
    return struct.unpack_from("<b", data, off)[0]


def read_f32(data, off):
    return struct.unpack_from("<f", data, off)[0]


def looks_reasonable_fx_header(blob, name_addr):
    if len(blob) < 76:
        return False
    if read_u32(blob, 0) != (name_addr & 0xFFFFFFFF):
        return False
    looping = read_u16(blob, 8)
    oneshot = read_u16(blob, 10)
    emission = read_u16(blob, 12)
    total = read_u32(blob, 16)
    elem_defs = read_u32(blob, 28)
    if looping + oneshot + emission > 64:
        return False
    if total < 76 or total > 0x100000:
        return False
    if elem_defs == 0:
        return False
    floats = [read_f32(blob, off) for off in (32, 36, 40, 44, 48, 52)]
    if any(not math.isfinite(v) or abs(v) > 1000000 for v in floats):
        return False
    return True


def dump_fx_candidate(handle, fx_addr, label):
    header = read_region(handle, fx_addr, 76)
    if not header or len(header) < 76:
        print(f"[{label}] failed to read FxEffectDef header at 0x{fx_addr:08X}")
        return

    looping = read_u16(header, 8)
    oneshot = read_u16(header, 10)
    emission = read_u16(header, 12)
    total = read_u32(header, 16)
    loop_life = read_u32(header, 20)
    nonloop_life = read_u32(header, 24)
    elem_defs = read_u32(header, 28)
    print(
        f"[{label}] fx=0x{fx_addr:08X} totalSize={total} loop={looping} oneShot={oneshot} "
        f"emission={emission} msecLoop={loop_life} msecNonLoop={nonloop_life} elemDefs=0x{elem_defs:08X}"
    )

    total_elems = looping + oneshot + emission
    if total_elems <= 0:
        return

    elem = read_region(handle, elem_defs, 292)
    if not elem or len(elem) < 292:
        print(f"[{label}] failed to read first FxElemDef at 0x{elem_defs:08X}")
        return

    flags = read_u32(elem, 0)
    elem_type = read_s8(elem, 184)
    visual_count = elem[185]
    vel_count = elem[186]
    vis_count = elem[187]
    vel_samples = read_u32(elem, 188)
    vis_samples = read_u32(elem, 192)
    visuals = read_u32(elem, 196)
    rotation_axis = read_u32(elem, 152)
    spawn_range_base = read_f32(elem, 12)
    spawn_range_amp = read_f32(elem, 16)
    fade_in_base = read_f32(elem, 20)
    fade_in_amp = read_f32(elem, 24)
    fade_out_base = read_f32(elem, 28)
    fade_out_amp = read_f32(elem, 32)
    cull_radius = read_f32(elem, 36)
    print(
        f"[{label}] elem0 flags=0x{flags:08X} type={elem_type} visualCount={visual_count} "
        f"velCount={vel_count} visCount={vis_count} velSamples=0x{vel_samples:08X} "
        f"visSamples=0x{vis_samples:08X} visuals=0x{visuals:08X} rotationAxis=0x{rotation_axis:08X}"
    )
    print(
        f"[{label}] elem0 spawnRange=({spawn_range_base:.3f},{spawn_range_amp:.3f}) "
        f"fadeIn=({fade_in_base:.3f},{fade_in_amp:.3f}) fadeOut=({fade_out_base:.3f},{fade_out_amp:.3f}) "
        f"spawnCull={cull_radius:.3f}"
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pid", type=int, default=0)
    parser.add_argument("--process-name", default="t6zm.exe")
    parser.add_argument("--effect", action="append", required=True)
    args = parser.parse_args()

    pid = args.pid or find_process_id(args.process_name)
    if not pid:
        raise SystemExit(f"Could not find process {args.process_name}")

    handle = OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    if not handle:
        raise SystemExit(f"OpenProcess failed for pid={pid} err={ctypes.get_last_error()}")

    try:
        print(f"pid={pid}")
        for effect_name in args.effect:
            print(f"\n=== {effect_name} ===")
            string_hits = search_ascii_occurrences(handle, effect_name)
            print(f"strings={len(string_hits)}")
            if not string_hits:
                continue
            for saddr in string_hits[:8]:
                print(f" string@0x{saddr:08X}")
                refs = search_pointer_refs(handle, saddr)
                print(f"  refs={len(refs)}")
                shown = 0
                for ref in refs:
                    candidate = ref
                    header = read_region(handle, candidate, 76)
                    if header and looks_reasonable_fx_header(header, saddr):
                        dump_fx_candidate(handle, candidate, effect_name)
                        shown += 1
                        if shown >= 4:
                            break
                if shown:
                    break
    finally:
        CloseHandle(handle)


if __name__ == "__main__":
    main()
