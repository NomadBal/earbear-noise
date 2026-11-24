# Third-party components

The source in this repository does not include any third-party code. The portable build bundles the components below,
each under its own license.

| Component | Used for | License |
| --- | --- | --- |
| CPython 3.12 (with Tcl/Tk) | Runtime and interface | PSF License / Tcl/Tk license |
| NumPy | Sound synthesis | BSD-3-Clause |
| Pillow | Tray icon image | MIT-CMU (HPND) |
| pystray | Tray icon | LGPL-3.0 |
| sounddevice (with PortAudio) | Audio output | MIT |
| cffi, pycparser | Required by sounddevice | MIT, BSD-3-Clause |
| six, typing_extensions | Required by pystray and the winrt packages | MIT, PSF License |
| winrt packages | Media-session commands from headsets | MIT |
| lameenc (LAME) | MP3 export | LGPL-3.0-or-later |
| Microsoft Visual C++ runtime | Required by Python and NumPy | Microsoft redistributable terms |

In the Windows bundle, numpy's OpenBLAS library is replaced by minblas (`minblas/`), part of this project.

The license files shipped inside each package stay in the bundle next to the component. LGPL components are used
unmodified as separate libraries.

The Linux bundle includes CPython with Tcl/Tk, NumPy with OpenBLAS, Pillow, lameenc, pulsectl,
dbus-next, and python-xlib. It includes the build host's PulseAudio client libraries, GTK 3,
PyGObject, Ayatana AppIndicator, `gdbus`, `swaymsg`, and their runtime dependencies. Python package
notices are kept with the packages. On RPM build hosts, `licenses/host/` contains the host package
notices and a list of the binary and source RPM versions.
