#include <windows.h>
#include <tlhelp32.h>

#include <cstdio>
#include <string>

namespace
{
DWORD find_process_id_by_name(const wchar_t* name)
{
    HANDLE snapshot = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
    if (snapshot == INVALID_HANDLE_VALUE)
        return 0;

    PROCESSENTRY32W entry {};
    entry.dwSize = sizeof(entry);

    DWORD pid = 0;
    if (Process32FirstW(snapshot, &entry))
    {
        do
        {
            if (_wcsicmp(entry.szExeFile, name) == 0)
            {
                pid = entry.th32ProcessID;
                break;
            }
        } while (Process32NextW(snapshot, &entry));
    }

    CloseHandle(snapshot);
    return pid;
}

void usage()
{
    std::fwprintf(stderr, L"Usage: dobj_probe_injector.exe --dll <path> [--pid <pid> | --name <exe_name>]\n");
}
} // namespace

int wmain(int argc, wchar_t** argv)
{
    const wchar_t* dll_path = nullptr;
    const wchar_t* proc_name = nullptr;
    DWORD pid = 0;

    for (int i = 1; i < argc; ++i)
    {
        if (_wcsicmp(argv[i], L"--dll") == 0 && i + 1 < argc)
        {
            dll_path = argv[++i];
        }
        else if (_wcsicmp(argv[i], L"--pid") == 0 && i + 1 < argc)
        {
            pid = static_cast<DWORD>(_wtoi(argv[++i]));
        }
        else if (_wcsicmp(argv[i], L"--name") == 0 && i + 1 < argc)
        {
            proc_name = argv[++i];
        }
        else
        {
            usage();
            return 1;
        }
    }

    if (!dll_path || (!pid && !proc_name))
    {
        usage();
        return 1;
    }

    if (!pid)
    {
        pid = find_process_id_by_name(proc_name);
        if (!pid)
        {
            std::fwprintf(stderr, L"Could not find process named '%s'\n", proc_name);
            return 1;
        }
    }

    wchar_t full_dll[MAX_PATH] = {};
    if (!_wfullpath(full_dll, dll_path, MAX_PATH))
    {
        std::fwprintf(stderr, L"Could not resolve DLL path '%s'\n", dll_path);
        return 1;
    }

    HANDLE proc = OpenProcess(PROCESS_CREATE_THREAD | PROCESS_QUERY_INFORMATION | PROCESS_VM_OPERATION | PROCESS_VM_WRITE | PROCESS_VM_READ, FALSE, pid);
    if (!proc)
    {
        std::fwprintf(stderr, L"OpenProcess failed for pid %lu (err=%lu)\n", pid, GetLastError());
        return 1;
    }

    const size_t bytes = (wcslen(full_dll) + 1) * sizeof(wchar_t);
    void* remote_buf = VirtualAllocEx(proc, nullptr, bytes, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE);
    if (!remote_buf)
    {
        std::fwprintf(stderr, L"VirtualAllocEx failed (err=%lu)\n", GetLastError());
        CloseHandle(proc);
        return 1;
    }

    if (!WriteProcessMemory(proc, remote_buf, full_dll, bytes, nullptr))
    {
        std::fwprintf(stderr, L"WriteProcessMemory failed (err=%lu)\n", GetLastError());
        VirtualFreeEx(proc, remote_buf, 0, MEM_RELEASE);
        CloseHandle(proc);
        return 1;
    }

    HMODULE kernel32 = GetModuleHandleW(L"kernel32.dll");
    if (!kernel32)
    {
        std::fwprintf(stderr, L"GetModuleHandleW(kernel32) failed\n");
        VirtualFreeEx(proc, remote_buf, 0, MEM_RELEASE);
        CloseHandle(proc);
        return 1;
    }

    auto* load_library = reinterpret_cast<LPTHREAD_START_ROUTINE>(GetProcAddress(kernel32, "LoadLibraryW"));
    if (!load_library)
    {
        std::fwprintf(stderr, L"GetProcAddress(LoadLibraryW) failed\n");
        VirtualFreeEx(proc, remote_buf, 0, MEM_RELEASE);
        CloseHandle(proc);
        return 1;
    }

    HANDLE thread = CreateRemoteThread(proc, nullptr, 0, load_library, remote_buf, 0, nullptr);
    if (!thread)
    {
        std::fwprintf(stderr, L"CreateRemoteThread failed (err=%lu)\n", GetLastError());
        VirtualFreeEx(proc, remote_buf, 0, MEM_RELEASE);
        CloseHandle(proc);
        return 1;
    }

    WaitForSingleObject(thread, INFINITE);

    DWORD remote_module = 0;
    GetExitCodeThread(thread, &remote_module);
    std::wprintf(L"Injected '%s' into pid %lu -> remote module 0x%08lX\n", full_dll, pid, remote_module);

    CloseHandle(thread);
    VirtualFreeEx(proc, remote_buf, 0, MEM_RELEASE);
    CloseHandle(proc);
    return 0;
}
