#define NOMINMAX
#define _CRT_SECURE_NO_WARNINGS

#include <windows.h>
#include <tlhelp32.h>
#include <intrin.h>

#include <algorithm>
#include <atomic>
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <mutex>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

#include "fx_runtime_probe_build_info.h"

namespace
{
constexpr DWORD kDispatchCallSiteRva = 0x0068E7FB;
constexpr DWORD kSpecialOpenMissContinueRva = 0x0068E802;
constexpr DWORD kSpecialOpenFlagBranchRva = 0x0068E83B;
constexpr DWORD kSpecialOpenSuccessBranchRva = 0x0068E872;
constexpr DWORD kSpecialOpenSuccessPostCallRva = 0x0068E87B;
constexpr DWORD kSpecialOpenSuccessContinueRva = 0x0068E8C3;
constexpr DWORD kSpecialOpenSuccessClass1ContinueRva = 0x0068E8D7;
constexpr DWORD kSpecialOpenSuccessClass1CallTargetRva = 0x0068E8FF78 - 0x00400000;
constexpr DWORD kSpecialOpenSuccessClass1PostCallRva = 0x0068E8E1;

struct SavedRegisters
{
    DWORD edi;
    DWORD esi;
    DWORD ebp;
    DWORD esp_saved;
    DWORD ebx;
    DWORD edx;
    DWORD ecx;
    DWORD eax;
    DWORD eflags;
};

struct ModuleInfoLite
{
    HMODULE base {};
    DWORD size {};
    std::string name;
    std::string path;
};

struct AssetTrace
{
    unsigned long long trace_id {};
    DWORD thread_id {};
    uintptr_t handle {};
    std::string image;
    std::string path;
    std::string resolved;
    uintptr_t return_addr {};
    size_t total_read {};
    int read_calls {};
    bool logged_first {};
};

struct ReturnTraceState
{
    void** slot {};
    uintptr_t original_return {};
    unsigned long long trace_id {};
    std::string path;
};

struct ExecTracePoint
{
    std::string label;
    uintptr_t addr {};
    BYTE original {};
    bool armed {};
    int hits {};
    int max_hits {8};
    unsigned long long trace_id {};
    std::string path;
};

HMODULE g_self = nullptr;
HMODULE g_main_module = nullptr;
uintptr_t g_main_base = 0;
SYSTEM_INFO g_system_info {};
std::mutex g_log_mutex;
std::mutex g_state_mutex;
FILE* g_log_file = nullptr;
std::atomic<unsigned long> g_log_seq {0};
std::atomic<unsigned long long> g_next_trace_id {1};

std::vector<ModuleInfoLite> g_modules;
std::unordered_set<std::string> g_watch_images;
std::unordered_set<std::string> g_watch_files;
std::unordered_set<std::string> g_watch_materials;
std::unordered_set<std::string> g_watch_techsets;

std::unordered_map<uintptr_t, AssetTrace> g_active_handles;
std::unordered_map<DWORD, ReturnTraceState> g_return_states;
std::unordered_map<uintptr_t, ExecTracePoint> g_exec_traces;

thread_local uintptr_t g_tls_rearm_addr = 0;

decltype(&CreateFileA) g_real_create_file_a = nullptr;
decltype(&CreateFileW) g_real_create_file_w = nullptr;
decltype(&ReadFile) g_real_read_file = nullptr;
decltype(&CloseHandle) g_real_close_handle = nullptr;

void* g_return_trace_thunk = nullptr;

HANDLE WINAPI hook_create_file_a(LPCSTR file_name, DWORD desired_access, DWORD share_mode, LPSECURITY_ATTRIBUTES sa, DWORD creation_disposition, DWORD flags, HANDLE template_file);
HANDLE WINAPI hook_create_file_w(LPCWSTR file_name, DWORD desired_access, DWORD share_mode, LPSECURITY_ATTRIBUTES sa, DWORD creation_disposition, DWORD flags, HANDLE template_file);
BOOL WINAPI hook_read_file(HANDLE handle, LPVOID buffer, DWORD bytes_to_read, LPDWORD bytes_read, LPOVERLAPPED overlapped);
BOOL WINAPI hook_close_handle(HANDLE handle);

std::string narrow_from_wide(const std::wstring& value)
{
    if (value.empty())
        return {};
    const int size = WideCharToMultiByte(CP_UTF8, 0, value.c_str(), static_cast<int>(value.size()), nullptr, 0, nullptr, nullptr);
    std::string out(size, '\0');
    WideCharToMultiByte(CP_UTF8, 0, value.c_str(), static_cast<int>(value.size()), out.data(), size, nullptr, nullptr);
    return out;
}

std::wstring wide_from_utf8(const std::string& value)
{
    if (value.empty())
        return {};
    const int size = MultiByteToWideChar(CP_UTF8, 0, value.c_str(), static_cast<int>(value.size()), nullptr, 0);
    std::wstring out(size, L'\0');
    MultiByteToWideChar(CP_UTF8, 0, value.c_str(), static_cast<int>(value.size()), out.data(), size);
    return out;
}

std::string to_lower_copy(std::string value)
{
    std::transform(value.begin(), value.end(), value.begin(), [](unsigned char c) { return static_cast<char>(std::tolower(c)); });
    return value;
}

std::string base_name_of(const std::string& path)
{
    const size_t slash = path.find_last_of("\\/");
    return slash == std::string::npos ? path : path.substr(slash + 1);
}

std::string remove_iwi_suffix(std::string file_name)
{
    const std::string lower = to_lower_copy(file_name);
    if (lower.size() >= 4 && lower.substr(lower.size() - 4) == ".iwi")
        file_name.resize(file_name.size() - 4);
    return file_name;
}

std::string normalize_image_token(const std::string& path)
{
    std::string file_name = base_name_of(path);
    if (!file_name.empty() && file_name[0] == ',')
        file_name.erase(file_name.begin());
    return remove_iwi_suffix(file_name);
}

bool path_is_watched_file(const std::string& path)
{
    const std::string file_name = base_name_of(to_lower_copy(path));
    return g_watch_files.find(file_name) != g_watch_files.end();
}

bool try_match_watched_image(const std::string& path, std::string& image_out)
{
    const std::string image = to_lower_copy(normalize_image_token(path));
    if (image.empty())
        return false;
    if (g_watch_images.find(image) == g_watch_images.end())
        return false;
    image_out = image;
    return true;
}

std::string sanitize_comma_iwi_path(const std::string& path)
{
    const size_t slash = path.find_last_of("\\/");
    if (slash == std::string::npos)
        return path;
    std::string dir = path.substr(0, slash + 1);
    std::string file_name = path.substr(slash + 1);
    if (!file_name.empty() && file_name[0] == ',')
        file_name.erase(file_name.begin());
    return dir + file_name;
}

std::string module_relative_path(const wchar_t* suffix)
{
    wchar_t self_path[MAX_PATH] {};
    GetModuleFileNameW(g_self, self_path, MAX_PATH);
    std::wstring path = self_path;
    const size_t slash = path.find_last_of(L"\\/");
    if (slash != std::wstring::npos)
        path.resize(slash + 1);
    path += suffix;
    return narrow_from_wide(path);
}

void log_line(const char* fmt, ...)
{
    std::lock_guard<std::mutex> lock(g_log_mutex);
    if (!g_log_file)
        return;

    SYSTEMTIME st {};
    GetLocalTime(&st);
    const unsigned long seq = ++g_log_seq;
    std::fprintf(g_log_file, "[%06lu][%02u:%02u:%02u.%03u] ", seq, st.wHour, st.wMinute, st.wSecond, st.wMilliseconds);

    va_list args;
    va_start(args, fmt);
    std::vfprintf(g_log_file, fmt, args);
    va_end(args);

    std::fputc('\n', g_log_file);
    std::fflush(g_log_file);
}

bool safe_copy_memory(uintptr_t addr, void* out, size_t size)
{
    __try
    {
        std::memcpy(out, reinterpret_cast<const void*>(addr), size);
        return true;
    }
    __except (EXCEPTION_EXECUTE_HANDLER)
    {
        return false;
    }
}

std::string hex_prefix(const void* data, size_t size, size_t max_bytes = 32)
{
    const unsigned char* bytes = static_cast<const unsigned char*>(data);
    const size_t count = std::min(size, max_bytes);
    char buffer[4] {};
    std::string out;
    for (size_t i = 0; i < count; ++i)
    {
        if (i)
            out.push_back(' ');
        std::snprintf(buffer, sizeof(buffer), "%02X", bytes[i]);
        out += buffer;
    }
    return out;
}

void log_bytes_around(const char* label, uintptr_t addr, size_t before = 16, size_t after = 24)
{
    uintptr_t start = addr > before ? addr - before : addr;
    unsigned char bytes[64] {};
    const size_t want = std::min(sizeof(bytes), before + after);
    if (!safe_copy_memory(start, bytes, want))
        return;
    log_line("%s around=0x%08lX start=0x%08lX data=%s", label, static_cast<unsigned long>(addr), static_cast<unsigned long>(start), hex_prefix(bytes, want, want).c_str());
}

void log_register_block(const CONTEXT& ctx)
{
    log_line("regs eip=0x%08lX eax=0x%08lX ebx=0x%08lX ecx=0x%08lX edx=0x%08lX esi=0x%08lX edi=0x%08lX ebp=0x%08lX esp=0x%08lX",
        ctx.Eip, ctx.Eax, ctx.Ebx, ctx.Ecx, ctx.Edx, ctx.Esi, ctx.Edi, ctx.Ebp, ctx.Esp);
}

void log_pointer_info(const char* name, uintptr_t value)
{
    MEMORY_BASIC_INFORMATION mbi {};
    VirtualQuery(reinterpret_cast<void*>(value), &mbi, sizeof(mbi));
    const char* module_name = "<unknown>";
    unsigned long rva = 0;
    for (const auto& module : g_modules)
    {
        const uintptr_t base = reinterpret_cast<uintptr_t>(module.base);
        if (value >= base && value < base + module.size)
        {
            module_name = module.name.c_str();
            rva = static_cast<unsigned long>(value - base);
            break;
        }
    }
    log_line("%s addr=0x%08lX module=%s%s%08lX", name, static_cast<unsigned long>(value), module_name, std::strcmp(module_name, "<unknown>") ? " rva=0x" : "", rva);
    if (mbi.BaseAddress)
        log_line("%s mem base=0x%08lX size=0x%08lX protect=0x%08lX type=0x%08lX", name, static_cast<unsigned long>(reinterpret_cast<uintptr_t>(mbi.BaseAddress)), static_cast<unsigned long>(mbi.RegionSize), static_cast<unsigned long>(mbi.Protect), static_cast<unsigned long>(mbi.Type));
    DWORD dword = 0;
    if (safe_copy_memory(value, &dword, sizeof(dword)))
        log_line("%s dword=0x%08lX", name, dword);
}

void enumerate_modules()
{
    g_modules.clear();

    HANDLE snap = CreateToolhelp32Snapshot(TH32CS_SNAPMODULE, GetCurrentProcessId());
    if (snap == INVALID_HANDLE_VALUE)
        return;

    MODULEENTRY32 me {};
    me.dwSize = sizeof(me);
    if (Module32First(snap, &me))
    {
        do
        {
            ModuleInfoLite info;
            info.base = me.hModule;
            info.size = me.modBaseSize;
            info.name = to_lower_copy(std::string(me.szModule));
            info.path = std::string(me.szExePath);
            g_modules.push_back(info);
        } while (Module32Next(snap, &me));
    }
    CloseHandle(snap);

    log_line("module_count=%u", static_cast<unsigned>(g_modules.size()));
    for (const auto& module : g_modules)
    {
        log_line("module name=%s base=0x%08lX size=0x%08lX path=%s",
            module.name.c_str(),
            static_cast<unsigned long>(reinterpret_cast<uintptr_t>(module.base)),
            static_cast<unsigned long>(module.size),
            module.path.c_str());
    }
}

void load_watchlist()
{
    const std::string watch_path = module_relative_path(L"..\\..\\..\\active_probe_watchlist.txt");
    FILE* file = std::fopen(watch_path.c_str(), "rb");
    if (!file)
    {
        log_line("watchlist_missing path=%s", watch_path.c_str());
        return;
    }

    char line[1024] {};
    unsigned count = 0;
    while (std::fgets(line, sizeof(line), file))
    {
        std::string text = line;
        while (!text.empty() && (text.back() == '\r' || text.back() == '\n'))
            text.pop_back();
        if (text.empty())
            continue;

        ++count;
        log_line("watch_entry %s", text.c_str());

        const size_t eq = text.find('=');
        if (eq == std::string::npos)
            continue;

        std::string key = to_lower_copy(text.substr(0, eq));
        std::string value = to_lower_copy(text.substr(eq + 1));
        if (key == "image")
            g_watch_images.insert(value);
        else if (key == "file")
            g_watch_files.insert(value);
        else if (key == "material")
            g_watch_materials.insert(value);
        else if (key == "techset")
            g_watch_techsets.insert(value);
    }
    std::fclose(file);
    log_line("watchlist_loaded path=%s entries=%u", watch_path.c_str(), count);

    g_watch_images.insert("fxt_debris_clump_dirt");
    g_watch_images.insert("fxt_light_glow_square");
    g_watch_images.insert("fxt_light_phosphorous");
}

bool patch_imports_in_module(HMODULE module, const char* target_name, void* replacement, void** original_out)
{
    if (!module)
        return false;

    auto* dos = reinterpret_cast<IMAGE_DOS_HEADER*>(module);
    if (dos->e_magic != IMAGE_DOS_SIGNATURE)
        return false;
    auto* nt = reinterpret_cast<IMAGE_NT_HEADERS*>(reinterpret_cast<unsigned char*>(module) + dos->e_lfanew);
    if (nt->Signature != IMAGE_NT_SIGNATURE)
        return false;

    const IMAGE_DATA_DIRECTORY& dir = nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_IMPORT];
    if (!dir.VirtualAddress || !dir.Size)
        return false;

    bool touched = false;
    auto* imports = reinterpret_cast<IMAGE_IMPORT_DESCRIPTOR*>(reinterpret_cast<unsigned char*>(module) + dir.VirtualAddress);
    for (; imports->Name; ++imports)
    {
        auto* orig = reinterpret_cast<IMAGE_THUNK_DATA*>(reinterpret_cast<unsigned char*>(module) + imports->OriginalFirstThunk);
        auto* thunk = reinterpret_cast<IMAGE_THUNK_DATA*>(reinterpret_cast<unsigned char*>(module) + imports->FirstThunk);
        if (!imports->OriginalFirstThunk)
            orig = thunk;

        for (; orig->u1.AddressOfData; ++orig, ++thunk)
        {
            if (IMAGE_SNAP_BY_ORDINAL(orig->u1.Ordinal))
                continue;
            auto* by_name = reinterpret_cast<IMAGE_IMPORT_BY_NAME*>(reinterpret_cast<unsigned char*>(module) + orig->u1.AddressOfData);
            if (std::strcmp(reinterpret_cast<const char*>(by_name->Name), target_name) != 0)
                continue;

            DWORD old = 0;
            if (!VirtualProtect(&thunk->u1.Function, sizeof(void*), PAGE_READWRITE, &old))
                continue;
            if (original_out && !*original_out)
                *original_out = reinterpret_cast<void*>(thunk->u1.Function);
            thunk->u1.Function = reinterpret_cast<ULONG_PTR>(replacement);
            VirtualProtect(&thunk->u1.Function, sizeof(void*), old, &old);
            FlushInstructionCache(GetCurrentProcess(), &thunk->u1.Function, sizeof(void*));
            touched = true;
        }
    }
    return touched;
}

void install_file_hooks()
{
    int create_w_count = 0;
    int create_a_count = 0;
    int read_count = 0;
    int close_count = 0;

    for (const auto& module : g_modules)
    {
        create_w_count += patch_imports_in_module(module.base, "CreateFileW", reinterpret_cast<void*>(&hook_create_file_w), reinterpret_cast<void**>(&g_real_create_file_w)) ? 1 : 0;
        create_a_count += patch_imports_in_module(module.base, "CreateFileA", reinterpret_cast<void*>(&hook_create_file_a), reinterpret_cast<void**>(&g_real_create_file_a)) ? 1 : 0;
        read_count += patch_imports_in_module(module.base, "ReadFile", reinterpret_cast<void*>(&hook_read_file), reinterpret_cast<void**>(&g_real_read_file)) ? 1 : 0;
        close_count += patch_imports_in_module(module.base, "CloseHandle", reinterpret_cast<void*>(&hook_close_handle), reinterpret_cast<void**>(&g_real_close_handle)) ? 1 : 0;
    }

    log_line("file_hook_install complete createfilew_modules=%d createfilea_modules=%d readfile_modules=%d closehandle_modules=%d realW=0x%08lX realA=0x%08lX realRead=0x%08lX realClose=0x%08lX",
        create_w_count,
        create_a_count,
        read_count,
        close_count,
        static_cast<unsigned long>(reinterpret_cast<uintptr_t>(g_real_create_file_w)),
        static_cast<unsigned long>(reinterpret_cast<uintptr_t>(g_real_create_file_a)),
        static_cast<unsigned long>(reinterpret_cast<uintptr_t>(g_real_read_file)),
        static_cast<unsigned long>(reinterpret_cast<uintptr_t>(g_real_close_handle)));
}

uintptr_t rva_to_va(DWORD rva)
{
    return g_main_base + rva;
}

bool patch_byte(uintptr_t addr, BYTE value, BYTE* original = nullptr)
{
    DWORD old = 0;
    if (!VirtualProtect(reinterpret_cast<void*>(addr), 1, PAGE_EXECUTE_READWRITE, &old))
        return false;
    if (original)
        *original = *reinterpret_cast<BYTE*>(addr);
    *reinterpret_cast<BYTE*>(addr) = value;
    VirtualProtect(reinterpret_cast<void*>(addr), 1, old, &old);
    FlushInstructionCache(GetCurrentProcess(), reinterpret_cast<void*>(addr), 1);
    return true;
}

void arm_exec_trace(const char* label, uintptr_t addr, unsigned long long trace_id, const std::string& path, int max_hits = 8)
{
    std::lock_guard<std::mutex> lock(g_state_mutex);
    auto& point = g_exec_traces[addr];
    point.label = label;
    point.addr = addr;
    point.trace_id = trace_id;
    point.path = path;
    point.max_hits = max_hits;
    if (!point.armed)
    {
        if (!patch_byte(addr, 0xCC, &point.original))
            return;
        point.armed = true;
        log_line("exec_trace_armed label=%s addr=0x%08lX original=%02X max_hits=%d trace=%llu path=%s",
            point.label.c_str(), static_cast<unsigned long>(point.addr), point.original, point.max_hits, point.trace_id, point.path.c_str());
        log_bytes_around("exec_trace_site bytes", addr);
    }
    else
    {
        log_line("exec_trace_rearmed label=%s addr=0x%08lX trace=%llu path=%s max_hits=%d",
            point.label.c_str(), static_cast<unsigned long>(point.addr), point.trace_id, point.path.c_str(), point.max_hits);
    }
}

void arm_branch_traces_after_return(bool success, unsigned long long trace_id, const std::string& path)
{
    if (success)
    {
        arm_exec_trace("special_open_success_branch", rva_to_va(kSpecialOpenSuccessBranchRva), trace_id, path);
        arm_exec_trace("special_open_success_postcall", rva_to_va(kSpecialOpenSuccessPostCallRva), trace_id, path);
        arm_exec_trace("special_open_success_continue", rva_to_va(kSpecialOpenSuccessContinueRva), trace_id, path);
        arm_exec_trace("special_open_success_class1_continue", rva_to_va(kSpecialOpenSuccessClass1ContinueRva), trace_id, path);
        log_line("branch_trace_request kind=success target1=0x%08lX target2=0x%08lX trace=%llu path=%s",
            static_cast<unsigned long>(rva_to_va(kSpecialOpenSuccessBranchRva)),
            static_cast<unsigned long>(rva_to_va(kSpecialOpenSuccessContinueRva)),
            trace_id,
            path.c_str());
    }
    else
    {
        arm_exec_trace("special_open_miss_continue", rva_to_va(kSpecialOpenMissContinueRva), trace_id, path);
        arm_exec_trace("special_open_flag_branch", rva_to_va(kSpecialOpenFlagBranchRva), trace_id, path);
        log_line("branch_trace_request kind=miss target1=0x%08lX target2=0x%08lX trace=%llu path=%s",
            static_cast<unsigned long>(rva_to_va(kSpecialOpenMissContinueRva)),
            static_cast<unsigned long>(rva_to_va(kSpecialOpenFlagBranchRva)),
            trace_id,
            path.c_str());
    }
}

extern "C" uintptr_t __cdecl on_return_trace_hit(SavedRegisters* saved)
{
    ReturnTraceState state {};
    {
        std::lock_guard<std::mutex> lock(g_state_mutex);
        auto it = g_return_states.find(GetCurrentThreadId());
        if (it != g_return_states.end())
        {
            state = it->second;
            g_return_states.erase(it);
        }
    }

    const bool success = saved && saved->eax != 0xFFFFFFFFu;
    log_line("return_trace_hit label=special_open_return hit=1 return=0x%08lX eax=0x%08lX ebx=0x%08lX ecx=0x%08lX edx=0x%08lX esi=0x%08lX edi=0x%08lX success=%d trace=%llu path=%s slot=0x%08lX",
        static_cast<unsigned long>(state.original_return),
        saved ? saved->eax : 0,
        saved ? saved->ebx : 0,
        saved ? saved->ecx : 0,
        saved ? saved->edx : 0,
        saved ? saved->esi : 0,
        saved ? saved->edi : 0,
        success ? 1 : 0,
        state.trace_id,
        state.path.c_str(),
        static_cast<unsigned long>(reinterpret_cast<uintptr_t>(state.slot)));
    log_bytes_around("return_trace_target bytes", state.original_return);
    arm_branch_traces_after_return(success, state.trace_id, state.path);
    return state.original_return;
}

extern "C" __declspec(naked) void return_trace_thunk()
{
    __asm
    {
        pushfd
        pushad
        mov eax, esp
        push eax
        call on_return_trace_hit
        add esp, 4
        mov [esp + 28], eax
        popad
        popfd
        jmp eax
    }
}

void maybe_install_return_trace(unsigned long long trace_id, const std::string& path)
{
    void** slot = reinterpret_cast<void**>(_AddressOfReturnAddress());
    const uintptr_t ret = reinterpret_cast<uintptr_t>(_ReturnAddress());
    if (ret != rva_to_va(kDispatchCallSiteRva))
        return;

    ReturnTraceState state;
    state.slot = slot;
    state.original_return = ret;
    state.trace_id = trace_id;
    state.path = path;

    {
        std::lock_guard<std::mutex> lock(g_state_mutex);
        g_return_states[GetCurrentThreadId()] = state;
    }

    *slot = g_return_trace_thunk;
    log_line("return_trace_installed label=special_open_return return=0x%08lX slot=0x%08lX thunk=0x%08lX trace=%llu path=%s",
        static_cast<unsigned long>(ret),
        static_cast<unsigned long>(reinterpret_cast<uintptr_t>(slot)),
        static_cast<unsigned long>(reinterpret_cast<uintptr_t>(g_return_trace_thunk)),
        trace_id,
        path.c_str());
    log_bytes_around("special_open_caller bytes", ret);
}

void begin_asset_trace(HANDLE handle, const std::string& image, const std::string& path, const std::string& resolved)
{
    AssetTrace trace;
    trace.trace_id = g_next_trace_id++;
    trace.thread_id = GetCurrentThreadId();
    trace.handle = reinterpret_cast<uintptr_t>(handle);
    trace.image = image;
    trace.path = path;
    trace.resolved = resolved;
    trace.return_addr = reinterpret_cast<uintptr_t>(_ReturnAddress());

    {
        std::lock_guard<std::mutex> lock(g_state_mutex);
        g_active_handles[trace.handle] = trace;
    }

    log_line("asset_trace_begin trace=%llu thread=%lu handle=0x%08lX image=%s path=%s resolved=%s return=0x%08lX",
        trace.trace_id, trace.thread_id, static_cast<unsigned long>(trace.handle), trace.image.c_str(), trace.path.c_str(), trace.resolved.c_str(), static_cast<unsigned long>(trace.return_addr));
    maybe_install_return_trace(trace.trace_id, path);
}

HANDLE WINAPI hook_create_file_a(LPCSTR file_name, DWORD desired_access, DWORD share_mode, LPSECURITY_ATTRIBUTES sa, DWORD creation_disposition, DWORD flags, HANDLE template_file)
{
    const std::string path = file_name ? file_name : "";
    std::string image;
    const bool watched_image = try_match_watched_image(path, image);
    const bool watched_file = path_is_watched_file(to_lower_copy(path));

    HANDLE handle = g_real_create_file_a(file_name, desired_access, share_mode, sa, creation_disposition, flags, template_file);
    std::string resolved = path;

    if (watched_image && handle == INVALID_HANDLE_VALUE && path.find("\\,") != std::string::npos)
    {
        resolved = sanitize_comma_iwi_path(path);
        handle = g_real_create_file_a(resolved.c_str(), desired_access, share_mode, sa, creation_disposition, flags, template_file);
        if (handle != INVALID_HANDLE_VALUE)
            log_line("createfilea_sanitized original=%s resolved=%s handle=0x%08lX", path.c_str(), resolved.c_str(), static_cast<unsigned long>(reinterpret_cast<uintptr_t>(handle)));
        else
            log_line("createfilea_sanitized_miss original=%s resolved=%s", path.c_str(), resolved.c_str());
    }

    if (watched_image || watched_file)
        log_line("createfilea path=%s access=0x%08lX share=0x%08lX creation=0x%08lX flags=0x%08lX handle=0x%08lX", path.c_str(), desired_access, share_mode, creation_disposition, flags, static_cast<unsigned long>(reinterpret_cast<uintptr_t>(handle)));

    if (watched_image && handle != INVALID_HANDLE_VALUE)
        begin_asset_trace(handle, image, path, resolved);

    return handle;
}

HANDLE WINAPI hook_create_file_w(LPCWSTR file_name, DWORD desired_access, DWORD share_mode, LPSECURITY_ATTRIBUTES sa, DWORD creation_disposition, DWORD flags, HANDLE template_file)
{
    const std::string path = file_name ? narrow_from_wide(file_name) : "";
    HANDLE handle = g_real_create_file_w(file_name, desired_access, share_mode, sa, creation_disposition, flags, template_file);
    if (path_is_watched_file(to_lower_copy(path)))
        log_line("createfilew path=%s access=0x%08lX share=0x%08lX creation=0x%08lX flags=0x%08lX handle=0x%08lX", path.c_str(), desired_access, share_mode, creation_disposition, flags, static_cast<unsigned long>(reinterpret_cast<uintptr_t>(handle)));
    return handle;
}

BOOL WINAPI hook_read_file(HANDLE handle, LPVOID buffer, DWORD bytes_to_read, LPDWORD bytes_read, LPOVERLAPPED overlapped)
{
    const BOOL ok = g_real_read_file(handle, buffer, bytes_to_read, bytes_read, overlapped);
    const uintptr_t key = reinterpret_cast<uintptr_t>(handle);
    std::lock_guard<std::mutex> lock(g_state_mutex);
    auto it = g_active_handles.find(key);
    if (it == g_active_handles.end())
        return ok;

    AssetTrace& trace = it->second;
    const DWORD got = bytes_read ? *bytes_read : 0;
    trace.total_read += got;
    trace.read_calls += 1;
    log_line("asset_read trace=%llu handle=0x%08lX ok=%d requested=%lu read=%lu total=%zu calls=%d image=%s resolved=%s",
        trace.trace_id, static_cast<unsigned long>(key), ok ? 1 : 0, bytes_to_read, got, trace.total_read, trace.read_calls, trace.image.c_str(), trace.resolved.c_str());
    if (got && !trace.logged_first)
    {
        log_line("asset_read_first trace=%llu image=%s bytes=%lu prefix=%s", trace.trace_id, trace.image.c_str(), got, hex_prefix(buffer, got).c_str());
        trace.logged_first = true;
    }
    else if (got)
    {
        log_line("asset_read_sample trace=%llu image=%s bytes=%lu prefix=%s", trace.trace_id, trace.image.c_str(), got, hex_prefix(buffer, got).c_str());
    }
    return ok;
}

BOOL WINAPI hook_close_handle(HANDLE handle)
{
    const uintptr_t key = reinterpret_cast<uintptr_t>(handle);
    {
        std::lock_guard<std::mutex> lock(g_state_mutex);
        auto it = g_active_handles.find(key);
        if (it != g_active_handles.end())
        {
            const AssetTrace trace = it->second;
            log_line("asset_close trace=%llu handle=0x%08lX image=%s total_read=%zu read_calls=%d resolved=%s",
                trace.trace_id, static_cast<unsigned long>(trace.handle), trace.image.c_str(), trace.total_read, trace.read_calls, trace.resolved.c_str());
            g_active_handles.erase(it);
        }
    }
    return g_real_close_handle(handle);
}

LONG CALLBACK probe_veh(EXCEPTION_POINTERS* info)
{
    if (!info || !info->ExceptionRecord || !info->ContextRecord)
        return EXCEPTION_CONTINUE_SEARCH;

    const DWORD code = info->ExceptionRecord->ExceptionCode;
    CONTEXT& ctx = *info->ContextRecord;

    if (code == STATUS_BREAKPOINT)
    {
        const uintptr_t addr = static_cast<uintptr_t>(ctx.Eip - 1);
        std::lock_guard<std::mutex> lock(g_state_mutex);
        auto it = g_exec_traces.find(addr);
        if (it == g_exec_traces.end() || !it->second.armed)
            return EXCEPTION_CONTINUE_SEARCH;

        ExecTracePoint& point = it->second;
        patch_byte(point.addr, point.original, nullptr);
        point.armed = false;
        point.hits += 1;
        g_tls_rearm_addr = point.addr;
        ctx.EFlags |= 0x100;
        ctx.Eip = static_cast<DWORD>(point.addr);

        log_line("exec_trace_hit label=%s hit=%d eip=0x%08lX addr=0x%08lX trace=%llu path=%s",
            point.label.c_str(), point.hits, static_cast<unsigned long>(point.addr), static_cast<unsigned long>(point.addr), point.trace_id, point.path.c_str());
        log_register_block(ctx);
        log_bytes_around("eip bytes", point.addr);
        log_pointer_info("eax", ctx.Eax);
        log_pointer_info("ebx", ctx.Ebx);
        log_pointer_info("ecx", ctx.Ecx);
        log_pointer_info("edx", ctx.Edx);
        log_pointer_info("esi", ctx.Esi);
        log_pointer_info("edi", ctx.Edi);
        log_pointer_info("ebp", ctx.Ebp);
        log_pointer_info("esp", ctx.Esp);

        if (point.label == "special_open_success_class1_continue")
        {
            log_line("branch_trace_request kind=class1_call target=0x%08lX postcall=0x%08lX trace=%llu path=%s",
                static_cast<unsigned long>(rva_to_va(kSpecialOpenSuccessClass1CallTargetRva)),
                static_cast<unsigned long>(rva_to_va(kSpecialOpenSuccessClass1PostCallRva)),
                point.trace_id,
                point.path.c_str());
            arm_exec_trace("special_open_class1_call_entry", rva_to_va(kSpecialOpenSuccessClass1CallTargetRva), point.trace_id, point.path);
            arm_exec_trace("special_open_class1_postcall", rva_to_va(kSpecialOpenSuccessClass1PostCallRva), point.trace_id, point.path);
        }
        return EXCEPTION_CONTINUE_EXECUTION;
    }

    if (code == STATUS_SINGLE_STEP && g_tls_rearm_addr)
    {
        std::lock_guard<std::mutex> lock(g_state_mutex);
        auto it = g_exec_traces.find(g_tls_rearm_addr);
        if (it != g_exec_traces.end() && it->second.hits < it->second.max_hits)
        {
            patch_byte(it->second.addr, 0xCC, nullptr);
            it->second.armed = true;
        }
        g_tls_rearm_addr = 0;
        ctx.EFlags &= ~0x100u;
        return EXCEPTION_CONTINUE_EXECUTION;
    }

    if (code == EXCEPTION_ACCESS_VIOLATION)
    {
        log_line("access_violation eip=0x%08lX faultAddr=0x%08lX", ctx.Eip, static_cast<unsigned long>(info->ExceptionRecord->ExceptionInformation[1]));
        log_register_block(ctx);
    }
    return EXCEPTION_CONTINUE_SEARCH;
}

DWORD WINAPI init_thread(void*)
{
    GetSystemInfo(&g_system_info);
    g_main_module = GetModuleHandleW(nullptr);
    g_main_base = reinterpret_cast<uintptr_t>(g_main_module);

    const std::string log_path = module_relative_path(L"fx_runtime_probe.log");
    g_log_file = std::fopen(log_path.c_str(), "wb");
    if (!g_log_file)
        return 0;

    log_line("fx_runtime_probe loaded pid=%lu build=%s", GetCurrentProcessId(), PROBE_BUILD_ID);
    char self_path[MAX_PATH] {};
    GetModuleFileNameA(g_self, self_path, MAX_PATH);
    log_line("probe_module=%s", self_path);
    char main_path[MAX_PATH] {};
    GetModuleFileNameA(g_main_module, main_path, MAX_PATH);
    log_line("main_module=%s base=0x%08lX", main_path, static_cast<unsigned long>(g_main_base));
    log_line("system_page_size=0x%08lX", static_cast<unsigned long>(g_system_info.dwPageSize));

    enumerate_modules();
    load_watchlist();

    g_real_create_file_a = reinterpret_cast<decltype(g_real_create_file_a)>(GetProcAddress(GetModuleHandleW(L"kernel32.dll"), "CreateFileA"));
    g_real_create_file_w = reinterpret_cast<decltype(g_real_create_file_w)>(GetProcAddress(GetModuleHandleW(L"kernel32.dll"), "CreateFileW"));
    g_real_read_file = reinterpret_cast<decltype(g_real_read_file)>(GetProcAddress(GetModuleHandleW(L"kernel32.dll"), "ReadFile"));
    g_real_close_handle = reinterpret_cast<decltype(g_real_close_handle)>(GetProcAddress(GetModuleHandleW(L"kernel32.dll"), "CloseHandle"));
    g_return_trace_thunk = reinterpret_cast<void*>(&return_trace_thunk);

    AddVectoredExceptionHandler(1, probe_veh);
    install_file_hooks();
    log_line("guard_watches=disabled");
    log_line("hook_install_complete installed=0");
    return 0;
}

} // namespace

BOOL APIENTRY DllMain(HMODULE module, DWORD reason, LPVOID)
{
    if (reason == DLL_PROCESS_ATTACH)
    {
        g_self = module;
        DisableThreadLibraryCalls(module);
        HANDLE thread = CreateThread(nullptr, 0, init_thread, nullptr, 0, nullptr);
        if (thread)
            CloseHandle(thread);
    }
    return TRUE;
}
