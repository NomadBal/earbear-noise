<p align="center"><img src="docs/earbear.png" width="128" alt="EarBear icon"></p>

<h1 align="center">EarBear</h1>

A small, fully offline ambient noise generator for Linux and Windows. It synthesises noise in real time (nothing is streamed or
downloaded), so it keeps working with no internet connection and uses very little CPU.

EarBear ships as a portable folder: no installer, no admin rights, no registry entries unless you turn on "start with Windows".

## Features

- Ten-band noise engine (random-phase spectral synthesis) with one slider per band and a stereo width control
- Presets: classic colours (white, pink, brown...), scenes (sea, rain, train, fireplace, heartbeat...) and your own saved presets
- Optional layers: binaural beats, wave swell and rhythm (drops, crackle, train, heartbeat)
- Sleep timer with an optional gentle fade-out, and an optional chime every N minutes (Bell, Glass, Marimba, Bowl)
- Volume safety: soft fade-in, slower rises above 75%, volume capped at launch; the noise ducks to half while a chime or other sound plays
- Export to WAV or MP3
- Tray icon, media keys / headset play-pause, global play/pause shortcut, single instance, always on top or compact view, follows the default audio device
- Keyboard: Space play/pause, Left/Right volume, Up/Down all bands (Ctrl for fine steps, Shift for large steps), Ctrl+Q quit

## Linux portable version

Download `EarBear-<version>-linux-x86_64-portable.zip`, unpack the entire folder, and run `./EarBear` inside it.
Python and the application dependencies are included. EarBear uses your existing desktop and PulseAudio or
PipeWire-Pulse session. See [the build guide](docs/BUILDING.md#linux) to build the ZIP from source.

Run `./EarBear-debug.sh` to see startup errors in the terminal. To remove EarBear, turn off **start at login**
in Settings → Window if enabled, run `./EarBear-stop-all.sh`, then delete the folder.
Settings live in `${XDG_CONFIG_HOME:-~/.config}/earbear`; the log lives in `${XDG_STATE_HOME:-~/.local/state}/earbear`.

- On X11, Ctrl+Alt+N toggles playback by default. On Wayland, the Tk window requires XWayland. Set the global shortcut in your compositor using the absolute path to `EarBear`. On Sway, add `bindsym --no-repeat Ctrl+Alt+n exec "/path/to/EarBear" --toggle` to your Sway config. Media controls use MPRIS on both.
- **Close to tray** requires a desktop with a StatusNotifier/AppIndicator tray. Without a tray, closing the window quits; `--hidden` starts minimized.
- **Keep awake** uses logind for system sleep. For display idle it uses Sway's idle inhibitor while the window is mapped, or the desktop's ScreenSaver D-Bus service on other desktops. Without those services or permissions, playback still works.

## Windows portable version

Download the latest `EarBear-<version>-portable.zip` from the Releases page, unzip it anywhere and start `EarBear.exe`.
To remove it, close EarBear, run `EarBear-stop-all.bat` once, and delete the folder. Settings and the log live in
`%LOCALAPPDATA%\EarBear`.

## Windows from source

Requires Windows and Python 3.12.

```powershell
pip install -r requirements.txt
python earbear.py
```

How the portable bundle and `EarBear.exe` are built is described in [docs/BUILDING.md](docs/BUILDING.md).

## Files

| File | What it is |
| --- | --- |
| `earbear.py` | Sound engine and interface |
| `linux_audio.py`, `linux_desktop.py`, `linux_session.py` | Linux audio, launch and desktop integration |
| `smtc_helper.py` | Helper process that receives media-session commands from headsets |
| `launcher/`, `EarBear` | Windows launcher source and Linux launcher; both start Python from the adjacent `python/` folder |
| `tools/make_icon.py` | Draws `earbear.ico` (bear with headphones) at every icon size |
| `minblas/` | Tiny replacement for numpy's 20 MB OpenBLAS library, used by the portable build |
| `EarBear-debug.bat`, `EarBear-debug.sh` | Starts EarBear with diagnostics in the terminal |
| `EarBear-stop-all.bat`, `EarBear-stop-all.sh` | Stops EarBear so the folder can be deleted |
| `CHANGELOG.txt` | Version history |

## License

EarBear is free software, released under the GNU General Public License, version 3 or (at your option) any later version.
See [LICENSE](LICENSE). Third-party components and their licenses are listed in [THIRD_PARTY.md](THIRD_PARTY.md).
