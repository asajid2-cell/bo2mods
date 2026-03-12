#include <windows.h>

#include <array>
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <string>
#include <string_view>
#include <vector>
#include <share.h>

namespace
{
struct HookRecord
{
    uintptr_t site = 0;
    uintptr_t format = 0;
    uintptr_t ret = 0;
    void* thunk = nullptr;
    std::array<unsigned char, 5> original{};
};

HMODULE g_module = nullptr;
HANDLE g_log_mutex = nullptr;
wchar_t g_log_path[MAX_PATH] = {};
std::vector<HookRecord> g_hooks;
PVOID g_vectored_handler = nullptr;
uintptr_t g_watched_string = 0;
uintptr_t g_guard_page = 0;
SIZE_T g_guard_page_size = 0;
DWORD g_guard_page_protect = 0;
bool g_rearm_guard = false;
SIZE_T g_watched_string_len = 0;

constexpr std::string_view kFragment = "dobj for xmodel";

void init_log_path()
{
    if (g_log_path[0] != L'\0')
        return;

    wchar_t dll_path[MAX_PATH] = {};
    GetModuleFileNameW(g_module, dll_path, MAX_PATH);

    std::wstring dir = dll_path;
    const auto slash = dir.find_last_of(L"\\/");
    if (slash != std::wstring::npos)
        dir.resize(slash + 1);
    else
        dir = L".\\";

    std::wstring full = dir + L"dobj_probe.log";
    wcsncpy_s(g_log_path, full.c_str(), _TRUNCATE);
}

void log_line(const char* fmt, ...)
{
    init_log_path();

    if (!g_log_mutex)
        g_log_mutex = CreateMutexW(nullptr, FALSE, L"Local\\bo3_rev_dobj_probe_log_mutex");

    if (g_log_mutex)
        WaitForSingleObject(g_log_mutex, INFINITE);

    FILE* fp = nullptr;
    fp = _wfsopen(g_log_path, L"a+b", _SH_DENYNO);
    if (fp)
    {
        SYSTEMTIME st {};
        GetLocalTime(&st);
        std::fprintf(fp, "[%02u:%02u:%02u.%03u] ", st.wHour, st.wMinute, st.wSecond, st.wMilliseconds);

        va_list args;
        va_start(args, fmt);
        std::vfprintf(fp, fmt, args);
        va_end(args);
        std::fprintf(fp, "\n");
        std::fclose(fp);
    }

    if (g_log_mutex)
        ReleaseMutex(g_log_mutex);
}

bool is_readable_address(const void* ptr)
{
    if (!ptr)
        return false;

    MEMORY_BASIC_INFORMATION mbi {};
    if (!VirtualQuery(ptr, &mbi, sizeof(mbi)))
        return false;
    if (mbi.State != MEM_COMMIT)
        return false;
    if ((mbi.Protect & PAGE_GUARD) || (mbi.Protect & PAGE_NOACCESS))
        return false;
    return true;
}

std::string safe_read_c_string(const char* ptr, size_t max_len = 160)
{
    if (!is_readable_address(ptr))
        return {};

    std::string out;
    out.reserve(64);

    for (size_t i = 0; i < max_len; ++i)
    {
        const unsigned char ch = static_cast<unsigned char>(ptr[i]);
        if (ch == 0)
            break;
        if (ch < 0x20 || ch > 0x7E)
            return {};
        out.push_back(static_cast<char>(ch));
    }

    return out;
}

std::vector<uintptr_t> get_section_ranges(HMODULE module, const char* section_name)
{
    std::vector<uintptr_t> ranges;
    const auto base = reinterpret_cast<unsigned char*>(module);
    const auto dos = reinterpret_cast<IMAGE_DOS_HEADER*>(base);
    if (!dos || dos->e_magic != IMAGE_DOS_SIGNATURE)
        return ranges;

    const auto nt = reinterpret_cast<IMAGE_NT_HEADERS32*>(base + dos->e_lfanew);
    if (!nt || nt->Signature != IMAGE_NT_SIGNATURE)
        return ranges;

    auto section = IMAGE_FIRST_SECTION(nt);
    for (unsigned i = 0; i < nt->FileHeader.NumberOfSections; ++i, ++section)
    {
        char name[9] = {};
        std::memcpy(name, section->Name, 8);
        if (std::strncmp(name, section_name, 8) == 0)
        {
            ranges.push_back(reinterpret_cast<uintptr_t>(base + section->VirtualAddress));
            ranges.push_back(static_cast<uintptr_t>(section->Misc.VirtualSize));
        }
    }
    return ranges;
}

std::vector<uintptr_t> find_ascii_strings(HMODULE module, std::string_view fragment)
{
    std::vector<uintptr_t> hits;
    const auto ranges = get_section_ranges(module, ".rdata");
    if (ranges.empty())
        return hits;

    const auto* start = reinterpret_cast<const unsigned char*>(ranges[0]);
    const size_t size = ranges[1];

    for (size_t i = 0; i + fragment.size() < size; ++i)
    {
        if (std::memcmp(start + i, fragment.data(), fragment.size()) == 0)
            hits.push_back(reinterpret_cast<uintptr_t>(start + i));
    }
    return hits;
}

std::vector<uintptr_t> find_push_imm32_refs(HMODULE module, uintptr_t target)
{
    std::vector<uintptr_t> hits;
    const auto ranges = get_section_ranges(module, ".text");
    if (ranges.empty())
        return hits;

    const auto* start = reinterpret_cast<const unsigned char*>(ranges[0]);
    const size_t size = ranges[1];

    for (size_t i = 0; i + 5 <= size; ++i)
    {
        if (start[i] != 0x68)
            continue;

        uint32_t imm = 0;
        std::memcpy(&imm, start + i + 1, sizeof(imm));
        if (imm == static_cast<uint32_t>(target))
            hits.push_back(reinterpret_cast<uintptr_t>(start + i));
    }
    return hits;
}

extern "C" void __stdcall BoneErrorHookLogSite(uintptr_t site, uint32_t* original_esp);

void write_rel32_jmp(uintptr_t from, uintptr_t to)
{
    DWORD old = 0;
    VirtualProtect(reinterpret_cast<void*>(from), 5, PAGE_EXECUTE_READWRITE, &old);
    *reinterpret_cast<unsigned char*>(from) = 0xE9;
    const auto rel = static_cast<int32_t>(to - (from + 5));
    std::memcpy(reinterpret_cast<void*>(from + 1), &rel, sizeof(rel));
    VirtualProtect(reinterpret_cast<void*>(from), 5, old, &old);
    FlushInstructionCache(GetCurrentProcess(), reinterpret_cast<void*>(from), 5);
}

void* build_hook_thunk(const HookRecord& hook)
{
    auto* mem = static_cast<unsigned char*>(VirtualAlloc(nullptr, 64, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE));
    if (!mem)
        return nullptr;

    size_t off = 0;
    auto emit8 = [&](unsigned char value) { mem[off++] = value; };
    auto emit32 = [&](uint32_t value) {
        std::memcpy(mem + off, &value, sizeof(value));
        off += sizeof(value);
    };

    emit8(0x60);                                   // pushad
    emit8(0x8D); emit8(0x44); emit8(0x24); emit8(0x20); // lea eax,[esp+20h]
    emit8(0x50);                                   // push eax
    emit8(0x68); emit32(static_cast<uint32_t>(hook.site)); // push imm32 site

    emit8(0xE8); // call rel32 helper
    const auto helper_call_from = reinterpret_cast<uintptr_t>(mem + off);
    const auto helper_rel = static_cast<int32_t>(reinterpret_cast<uintptr_t>(&BoneErrorHookLogSite) - (helper_call_from + 4));
    emit32(static_cast<uint32_t>(helper_rel));

    emit8(0x83); emit8(0xC4); emit8(0x08);         // add esp,8
    emit8(0x61);                                   // popad
    emit8(0x68); emit32(static_cast<uint32_t>(hook.format)); // push original format
    emit8(0xE9); // jmp back
    const auto jmp_from = reinterpret_cast<uintptr_t>(mem + off);
    const auto ret_rel = static_cast<int32_t>(hook.ret - (jmp_from + 4));
    emit32(static_cast<uint32_t>(ret_rel));

    FlushInstructionCache(GetCurrentProcess(), mem, off);
    return mem;
}

bool install_one_hook(uintptr_t site, uintptr_t format)
{
    HookRecord hook {};
    hook.site = site;
    hook.format = format;
    hook.ret = site + 5;
    std::memcpy(hook.original.data(), reinterpret_cast<void*>(site), hook.original.size());
    hook.thunk = build_hook_thunk(hook);
    if (!hook.thunk)
    {
        log_line("ERROR: failed to allocate thunk for site=0x%08X", static_cast<unsigned>(site));
        return false;
    }

    write_rel32_jmp(site, reinterpret_cast<uintptr_t>(hook.thunk));
    g_hooks.push_back(hook);
    log_line("Installed hook: site=0x%08X format=0x%08X thunk=0x%08X", static_cast<unsigned>(site), static_cast<unsigned>(format), static_cast<unsigned>(reinterpret_cast<uintptr_t>(hook.thunk)));
    return true;
}

void log_stack_slots(uint32_t* esp)
{
    std::string printable[8];
    for (size_t i = 0; i < 8; ++i)
        printable[i] = safe_read_c_string(reinterpret_cast<const char*>(esp[i]));

    log_line(
        "stack esp=0x%08X s0=0x%08X s1=0x%08X s2=0x%08X s3=0x%08X s4=0x%08X s5=0x%08X s6=0x%08X s7=0x%08X",
        static_cast<unsigned>(reinterpret_cast<uintptr_t>(esp)),
        esp[0], esp[1], esp[2], esp[3], esp[4], esp[5], esp[6], esp[7]
    );

    for (size_t i = 0; i < 8; ++i)
    {
        if (!printable[i].empty())
            log_line("stack_str[%u]=%s", static_cast<unsigned>(i), printable[i].c_str());
    }

    void* frames[16] = {};
    const USHORT frame_count = CaptureStackBackTrace(0, 16, frames, nullptr);
    for (USHORT i = 0; i < frame_count; ++i)
        log_line("backtrace[%u]=0x%08X", static_cast<unsigned>(i), static_cast<unsigned>(reinterpret_cast<uintptr_t>(frames[i])));
}

void arm_guard_page()
{
    if (!g_guard_page || !g_guard_page_size)
        return;

    DWORD old = 0;
    if (VirtualProtect(reinterpret_cast<void*>(g_guard_page), g_guard_page_size, g_guard_page_protect | PAGE_GUARD, &old))
        log_line("Guard page armed at 0x%08X size=0x%X", static_cast<unsigned>(g_guard_page), static_cast<unsigned>(g_guard_page_size));
    else
        log_line("ERROR: VirtualProtect guard arm failed err=%lu", GetLastError());
}

LONG CALLBACK vectored_handler(EXCEPTION_POINTERS* info)
{
    if (!info || !info->ExceptionRecord || !info->ContextRecord)
        return EXCEPTION_CONTINUE_SEARCH;

    const auto code = info->ExceptionRecord->ExceptionCode;
    if (code == STATUS_GUARD_PAGE_VIOLATION)
    {
        const auto accessed = static_cast<uintptr_t>(info->ExceptionRecord->NumberParameters > 1 ? info->ExceptionRecord->ExceptionInformation[1] : 0);
        if (g_guard_page && accessed >= g_watched_string && accessed < (g_watched_string + g_watched_string_len))
        {
            log_line(
                "guard_hit eip=0x%08X esp=0x%08X accessed=0x%08X watched=0x%08X",
                static_cast<unsigned>(info->ContextRecord->Eip),
                static_cast<unsigned>(info->ContextRecord->Esp),
                static_cast<unsigned>(accessed),
                static_cast<unsigned>(g_watched_string)
            );
            log_stack_slots(reinterpret_cast<uint32_t*>(info->ContextRecord->Esp));
            info->ContextRecord->EFlags |= 0x100u;
            g_rearm_guard = true;
            return EXCEPTION_CONTINUE_EXECUTION;
        }
    }
    else if (code == STATUS_SINGLE_STEP && g_rearm_guard)
    {
        g_rearm_guard = false;
        arm_guard_page();
        return EXCEPTION_CONTINUE_EXECUTION;
    }

    return EXCEPTION_CONTINUE_SEARCH;
}

void install_guard_watch(uintptr_t watched_string)
{
    MEMORY_BASIC_INFORMATION mbi {};
    if (!VirtualQuery(reinterpret_cast<void*>(watched_string), &mbi, sizeof(mbi)))
    {
        log_line("ERROR: VirtualQuery failed for watched string 0x%08X", static_cast<unsigned>(watched_string));
        return;
    }

    g_watched_string = watched_string;
    g_watched_string_len = std::strlen(reinterpret_cast<const char*>(watched_string));
    g_guard_page = reinterpret_cast<uintptr_t>(mbi.BaseAddress);
    g_guard_page_size = mbi.RegionSize;
    g_guard_page_protect = mbi.Protect & ~PAGE_GUARD;

    if (!g_vectored_handler)
        g_vectored_handler = AddVectoredExceptionHandler(1, &vectored_handler);

    if (!g_vectored_handler)
    {
        log_line("ERROR: AddVectoredExceptionHandler failed");
        return;
    }

    log_line(
        "Installed guard watch: string=0x%08X page=0x%08X size=0x%X protect=0x%08X",
        static_cast<unsigned>(g_watched_string),
        static_cast<unsigned>(g_guard_page),
        static_cast<unsigned>(g_guard_page_size),
        static_cast<unsigned>(g_guard_page_protect)
    );
    arm_guard_page();
}

DWORD WINAPI hook_thread(void*)
{
    log_line("dobj_probe_hook loaded pid=%lu", GetCurrentProcessId());

    HMODULE main_mod = GetModuleHandleW(nullptr);
    if (!main_mod)
    {
        log_line("ERROR: GetModuleHandleW(nullptr) failed");
        return 0;
    }

    char exe_path[MAX_PATH] = {};
    GetModuleFileNameA(main_mod, exe_path, MAX_PATH);
    log_line("main_module=%s base=0x%08X", exe_path, static_cast<unsigned>(reinterpret_cast<uintptr_t>(main_mod)));

    const auto strings = find_ascii_strings(main_mod, kFragment);
    if (strings.empty())
    {
        log_line("ERROR: could not find target format string fragment '%s'", std::string(kFragment).c_str());
        return 0;
    }

    log_line("Found %u matching error strings", static_cast<unsigned>(strings.size()));
    unsigned installed = 0;
    for (uintptr_t fmt : strings)
    {
        const auto refs = find_push_imm32_refs(main_mod, fmt);
        log_line("format=0x%08X refs=%u text='%s'", static_cast<unsigned>(fmt), static_cast<unsigned>(refs.size()), reinterpret_cast<const char*>(fmt));
        for (uintptr_t site : refs)
        {
            if (install_one_hook(site, fmt))
                ++installed;
        }
    }

    if (!installed)
    {
        log_line("ERROR: no hooks installed");
        install_guard_watch(strings.front());
    }
    else
        log_line("Hook install complete. installed=%u", installed);

    return 0;
}
} // namespace

extern "C" void __stdcall BoneErrorHookLogSite(uintptr_t site, uint32_t* original_esp)
{
    log_line("bone_error_ref_hit site=0x%08X", static_cast<unsigned>(site));
    if (original_esp)
        log_stack_slots(original_esp);
}

BOOL WINAPI DllMain(HINSTANCE instance, DWORD reason, LPVOID)
{
    if (reason == DLL_PROCESS_ATTACH)
    {
        g_module = instance;
        DisableThreadLibraryCalls(instance);
        HANDLE thread = CreateThread(nullptr, 0, &hook_thread, nullptr, 0, nullptr);
        if (thread)
            CloseHandle(thread);
    }
    return TRUE;
}
