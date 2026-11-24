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

numpy's OpenBLAS library is not shipped: it is replaced by minblas (`minblas/`), part of this project.

The license files shipped inside each package stay in the bundle next to the component. LGPL components are used
unmodified as separate libraries.

The Linux installation uses the system's PulseAudio client libraries (LGPL-2.1-or-later) and installs
pulsectl (MIT), dbus-next (MIT), and python-xlib (LGPL-2.1-or-later) for desktop integration.
