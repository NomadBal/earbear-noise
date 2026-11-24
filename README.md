# EarBear

<img src="docs/assets/earbear-mascot.png" alt="EarBear, a charcoal bear wearing headphones and holding an orange audio mixer" width="200">

A small, fully offline ambient noise generator for Windows. It synthesises noise in real time (nothing is streamed or
downloaded), so it keeps working with no internet connection and uses very little CPU.

EarBear ships as a portable folder: no installer, no admin rights, no registry entries unless you turn on "start with Windows".

## Features

- Ten-band noise engine (random-phase spectral synthesis) with one slider per band and a stereo width control
- Presets: classic colours (white, pink, brown...), scenes (sea, rain, train, fireplace, heartbeat...) and your own saved presets
- Optional layers: binaural beats, wave swell and rhythm (drops, crackle, train, heartbeat)
- Sleep timer with an optional gentle fade-out, and an optional chime every N minutes (Bell, Glass, Marimba, Bowl)
- Volume safety: soft fade-in, slower rises above 75%, volume capped at launch; the noise ducks to half while a chime or other sound plays
- Export to WAV or MP3
- Tray icon, media keys / headset play-pause, global Ctrl+Alt+N play/pause, single instance, always on top or compact view, follows the default audio device
- Keyboard: Space play/pause, Left/Right volume, Up/Down all bands (Ctrl for fine steps, Shift for large steps), Ctrl+Q quit

## Run the portable version

Download the latest `EarBear-<version>-portable.zip` from the Releases page, unzip it anywhere and start `EarBear.exe`.
To remove it, close EarBear, run `EarBear-stop-all.bat` once, and delete the folder. Settings and the log live in
`%LOCALAPPDATA%\EarBear`.

## Run from source

Requires Windows and Python 3.12.

```powershell
pip install -r requirements.txt
python earbear.py
```

How the portable bundle and `EarBear.exe` are built is described in [docs/BUILDING.md](docs/BUILDING.md).

## Files

| File | What it is |
| --- | --- |
| `earbear.py` | The whole program: sound engine and interface |
| `smtc_helper.py` | Helper process that receives media-session commands from headsets |
| `launcher/` | Source of `EarBear.exe`, the small launcher that starts the bundled Python |
| `tools/make_icon.py` | Draws `earbear.ico` (bear with headphones) at every icon size |
| `minblas/` | Tiny replacement for numpy's 20 MB OpenBLAS library, used by the portable build |
| `EarBear-debug.bat` | Starts the program with a console to see errors |
| `EarBear-stop-all.bat` | Stops every EarBear process so the folder can be deleted |
| `CHANGELOG.txt` | Version history |

## License

EarBear is free software, released under the GNU General Public License, version 3 or (at your option) any later version.
See [LICENSE](LICENSE). Third-party components and their licenses are listed in [THIRD_PARTY.md](THIRD_PARTY.md).
