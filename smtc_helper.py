# EarBear - local ambient noise generator
# Copyright (C) 2026 NomadBal
# SPDX-License-Identifier: GPL-3.0-or-later
"""EarBear helper process: registers a Windows media session so play/pause commands sent by headsets and
media controls reach the program, which it forwards over stdout. It exits as soon as the parent goes away
and quietly if anything is unavailable."""
import os
import sys
import threading


def exit_with_parent():
    """Terminate when the EarBear process ends, however it ends, so nothing is left running."""
    try:
        import ctypes
        k = ctypes.windll.kernel32
        k.OpenProcess.restype = ctypes.c_void_p
        k.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
        h = k.OpenProcess(0x00100000, False, os.getppid())   # SYNCHRONIZE
        if h:
            k.WaitForSingleObject(ctypes.c_void_p(h), 0xFFFFFFFF)
    except Exception:
        return
    os._exit(0)


threading.Thread(target=exit_with_parent, daemon=True).start()

try:
    from winrt.windows.media.playback import MediaPlayer
    from winrt.windows.media import MediaPlaybackStatus as S, MediaPlaybackType as T, SystemMediaTransportControlsButton as B
    mp = MediaPlayer()
    mp.command_manager.is_enabled = False
    sm = mp.system_media_transport_controls
    sm.is_enabled = True
    sm.is_play_enabled = True
    sm.is_pause_enabled = True
    try:
        sm.is_stop_enabled = True
        u = sm.display_updater
        u.type = T.MUSIC
        u.music_properties.title = 'EarBear'
        u.music_properties.artist = 'Ambient noise'
        u.update()
    except Exception:
        pass
    names = {B.PLAY: 'play', B.PAUSE: 'pause', B.STOP: 'pause'}

    def pressed(sender, args):
        n = names.get(args.button)
        if n:
            print(n, flush=True)
    sm.add_button_pressed(pressed)
except Exception:
    os._exit(1)

for line in sys.stdin:
    cmd = line.strip()
    if cmd == 'playing':
        sm.playback_status = S.PLAYING
    elif cmd == 'paused':
        sm.playback_status = S.PAUSED
    elif cmd == 'quit':
        break
os._exit(0)     # never wait for runtime threads at shutdown
