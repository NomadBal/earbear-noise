# Building the portable version

## Linux

From the source checkout on a glibc-based x86-64 Linux build host, run:

```sh
/usr/bin/python3 tools/build_linux.py
```

The build host needs Python 3.12 or newer with Tk and PyGObject, GTK 3 and Ayatana AppIndicator
with their typelibs, the GNOME desktop schemas, the PulseAudio client libraries, `gdbus`, `swaymsg`,
`glib-compile-schemas`, and `uv`. The script copies the runtime and its shared libraries from the
host and installs the Python packages into the staged folder. It writes
`dist/EarBear-<version>-linux-x86_64-portable.zip`. The target system supplies glibc and the running
desktop and audio services. It does not need the build tools or a separately installed Python.

## Windows

The portable folder has this layout:

```
EarBear/
  EarBear.exe          launcher (built from launcher/launcher.c)
  earbear.py
  smtc_helper.py
  earbear.ico
  CHANGELOG.txt
  EarBear-debug.bat
  EarBear-stop-all.bat
  python/              Python 3.12 runtime for Windows x64, with Tcl/Tk (python/tcl)
    Lib/site-packages/ numpy, Pillow, pystray, sounddevice, cffi, pycparser, six, typing_extensions, winrt, lameenc
```

## 1. The Python runtime

Use the 64-bit Windows Python 3.12 runtime (the "embeddable package" or a copy of an installed Python 3.12) and keep
`python312.dll`, `python3.dll`, `vcruntime140*.dll`, the standard library, `DLLs/` and the `tcl/` folder. Everything
else can be pruned; the launcher sets `PYTHONHOME`, `TCL_LIBRARY` and `TK_LIBRARY` to this folder and ignores any
Python installed on the machine.

## 2. The packages

Install the requirements into the bundled runtime:

```powershell
python\python.exe -m pip install --target python\Lib\site-packages -r requirements.txt
```

The 0.12.0.0 release was built with numpy 2.5.5, Pillow 13.0.0, pystray 0.19.5, sounddevice 0.5.6 and lameenc 1.9.0.

Optional size reductions used for the releases (the program runs without these parts):

- numpy: `polynomial`, `ma`, `ctypeslib`, `doc`, `matlib.py`, `conftest.py`, the test extension modules in `_core`
  (`_multiarray_tests`, `_umath_tests`, `_rational_tests`, `_operand_flag_tests`, `_struct_ufunc_tests`, `_simd`) and all `*.lib` files
- Pillow: image format plugins other than the ones used by the tray icon
- pystray: the back ends other than `_win32`
- unused standard-library modules, SQLite, OpenSSL, test folders and `*.dist-info` folders

Keep the license files of the packages you ship (see [THIRD_PARTY.md](../THIRD_PARTY.md)).

Replace numpy's OpenBLAS (`python\Lib\site-packages\numpy.libs\libscipy_openblas64_-<hash>.dll`, about 20 MB) with
minblas, built from `minblas/minblas.c` under exactly the same file name as the DLL it replaces:

```
x86_64-w64-mingw32-gcc -O2 -shared -s -static-libgcc -o libscipy_openblas64_-<hash>.dll minblas.c
```

minblas implements the BLAS functions numpy calls outside of `numpy.linalg` with plain loops (EarBear itself no longer
calls any of them); the `numpy.linalg` functions stop the program with a message if called. The hash in the name changes
with every numpy release, so check the file name in `numpy.libs` first.

## 3. The launcher

`EarBear.exe` is built with MinGW-w64 (any recent GCC for `x86_64-w64-mingw32`). From the `launcher` folder:

```
x86_64-w64-mingw32-windres launcher.rc -O coff -o launcher_rc.o
x86_64-w64-mingw32-gcc -Os -s -mwindows -o EarBear.exe launcher.c launcher_rc.o
```

`launcher.rc` embeds `earbear.ico` as the program icon. Copy the resulting `EarBear.exe` to the root of the portable folder.

## 4. Zip

Zip the `EarBear` folder as `EarBear-<version>-portable.zip`.
