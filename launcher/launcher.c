/*
 * EarBear launcher (EarBear.exe)
 * Copyright (C) 2026 NomadBal
 * SPDX-License-Identifier: GPL-3.0-or-later
 *
 * Starts the bundled Python (folder "python" next to EarBear.exe) and runs earbear.py with it, without a console window.
 *
 * - Single instance: creates the mutex Local\EarBear.SingleInstance. If it already exists, the running copy is asked to
 *   show its window through the event Local\EarBear.ShowWindow and this process exits.
 * - Points Python and Tcl/Tk at the bundled folders and ignores any Python installed on the machine.
 * - Loads python312.dll from the bundle and calls Py_Main, so no python.exe console is involved.
 *
 * Build (MinGW-w64, see docs/BUILDING.md):
 *   x86_64-w64-mingw32-windres launcher.rc -O coff -o launcher_rc.o
 *   x86_64-w64-mingw32-gcc -Os -s -mwindows -o EarBear.exe launcher.c launcher_rc.o
 */
#include <windows.h>
#include <shellapi.h>
#include <wchar.h>

typedef int (*PyMainFn)(int, wchar_t **);

int main(void)
{
    HANDLE mutex = CreateMutexW(NULL, FALSE, L"Local\\EarBear.SingleInstance");
    HANDLE show = CreateEventW(NULL, FALSE, FALSE, L"Local\\EarBear.ShowWindow");
    if (mutex && GetLastError() == ERROR_ALREADY_EXISTS) {
        AllowSetForegroundWindow(ASFW_ANY);          /* let the running copy bring its window to the front */
        if (show)
            SetEvent(show);
        return 0;
    }

    wchar_t exe[MAX_PATH], dir[MAX_PATH], py[MAX_PATH + 16], buf[MAX_PATH + 32], script[MAX_PATH + 16];
    DWORD len = GetModuleFileNameW(NULL, exe, MAX_PATH);
    if (len == 0 || len >= MAX_PATH - 32) {         /* leave room for "\\python\\tcl\\tcl8.6" and the like */
        MessageBoxW(NULL, L"The folder path is too long: move the EarBear folder somewhere shorter.", L"EarBear", MB_ICONERROR);
        return 1;
    }
    wcscpy(dir, exe);
    wchar_t *slash = wcsrchr(dir, L'\\');
    if (slash)
        *slash = 0;
    SetCurrentDirectoryW(dir);

    _snwprintf(py, MAX_PATH + 16, L"%ls\\python", dir);
    SetEnvironmentVariableW(L"PYTHONHOME", py);
    SetEnvironmentVariableW(L"PYTHONNOUSERSITE", L"1");
    SetEnvironmentVariableW(L"PYTHONPATH", NULL);
    SetEnvironmentVariableW(L"EARBEAR_LAUNCHER", L"1");   /* tells earbear.py that the mutex is already held */
    _snwprintf(buf, MAX_PATH + 32, L"%ls\\tcl\\tcl8.6", py);
    SetEnvironmentVariableW(L"TCL_LIBRARY", buf);
    _snwprintf(buf, MAX_PATH + 32, L"%ls\\tcl\\tk8.6", py);
    SetEnvironmentVariableW(L"TK_LIBRARY", buf);
    SetDllDirectoryW(py);

    _snwprintf(buf, MAX_PATH + 32, L"%ls\\python312.dll", py);
    HMODULE dll = LoadLibraryExW(buf, NULL, LOAD_WITH_ALTERED_SEARCH_PATH);
    if (!dll) {
        MessageBoxW(NULL, L"python312.dll not found: the 'python' folder must sit next to EarBear.exe.", L"EarBear", MB_ICONERROR);
        return 1;
    }
    PyMainFn py_main = (PyMainFn)GetProcAddress(dll, "Py_Main");
    if (!py_main) {
        MessageBoxW(NULL, L"Py_Main not found in python312.dll.", L"EarBear", MB_ICONERROR);
        return 1;
    }

    /* argv for Python: EarBear.exe, earbear.py, then any arguments given to EarBear.exe */
    _snwprintf(script, MAX_PATH + 16, L"%ls\\earbear.py", dir);
    int argc = 0;
    wchar_t **args = CommandLineToArgvW(GetCommandLineW(), &argc);
    wchar_t *argv[32];
    int n = 0;
    argv[n++] = exe;
    argv[n++] = script;
    for (int i = 1; args && i < argc && n < 31; i++)
        argv[n++] = args[i];
    argv[n] = NULL;
    return py_main(n, argv);
}
