# SPDX-License-Identifier: GPL-3.0-or-later
"""Linux audio output through PulseAudio (including PipeWire's Pulse server)."""
import ctypes as C
import os
import sys
import time

import numpy as np
import pulsectl

RATE = 48000
FRAMES = 1024


class SampleSpec(C.Structure):
    _fields_ = [('format', C.c_int), ('rate', C.c_uint32), ('channels', C.c_uint8)]


class BufferAttr(C.Structure):
    _fields_ = [(n, C.c_uint32) for n in ('maxlength', 'tlength', 'prebuf', 'minreq', 'fragsize')]


def play(engine, alive, opened):
    """Run on the audio worker; the server moves this default-routed stream between sinks."""
    pulse = C.CDLL('libpulse.so.0')
    simple = C.CDLL('libpulse-simple.so.0')
    pulse.pa_strerror.argtypes = [C.c_int]
    pulse.pa_strerror.restype = C.c_char_p
    err = C.c_int()
    ep = C.byref(err)
    simple.pa_simple_new.argtypes = [C.c_char_p, C.c_char_p, C.c_int, C.c_char_p, C.c_char_p,
                                     C.POINTER(SampleSpec), C.c_void_p, C.POINTER(BufferAttr), C.POINTER(C.c_int)]
    simple.pa_simple_new.restype = C.c_void_p
    simple.pa_simple_write.argtypes = [C.c_void_p, C.c_void_p, C.c_size_t, C.POINTER(C.c_int)]
    simple.pa_simple_free.argtypes = [C.c_void_p]
    simple.pa_simple_free.restype = None
    out = np.zeros((FRAMES, 2), np.float32)
    data = out.ctypes.data
    spec = SampleSpec(5 if sys.byteorder == 'little' else 6, RATE, 2)  # PA_SAMPLE_FLOAT32NE
    default = 0xffffffff
    attrs = BufferAttr(default, out.nbytes * 4, default, out.nbytes, default)
    stream = simple.pa_simple_new(None, b'EarBear', 1, None, b'Ambient noise', C.byref(spec), None, C.byref(attrs), ep)
    if not stream:
        raise OSError(pulse.pa_strerror(err.value).decode())
    try:
        opened()
        while alive():
            engine.callback(out, FRAMES, None, None)
            if simple.pa_simple_write(stream, data, out.nbytes, ep) < 0:
                raise OSError(pulse.pa_strerror(err.value).decode())
    finally:
        simple.pa_simple_free(stream)


def watch_duck(app, log):
    """Duck for another active, unmuted stream on the sink actually playing EarBear."""
    pid = str(os.getpid())
    while app.alive:
        try:
            with pulsectl.Pulse('EarBear audio monitor', connect=False) as pulse:
                pulse.connect(timeout=2)
                while app.alive:
                    if app.duck and app.playing:
                        streams = pulse.sink_input_list()
                        sinks = {s.sink for s in streams if s.proplist.get('application.process.id') == pid}
                        active = any(s.sink in sinks and not s.corked and not s.mute and
                                     s.volume.value_flat > 0 and s.proplist.get('application.process.id') != pid
                                     for s in streams)
                        app.update_duck(active)
                    else:
                        app.update_duck(False)
                    time.sleep(0.5)
        except (OSError, pulsectl.PulseError) as exc:
            app.duck_media, app.duck_since = False, 0.0
            log.dbg('desktop audio monitor: %s' % exc)
            time.sleep(2)
