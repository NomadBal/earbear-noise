# SPDX-License-Identifier: GPL-3.0-or-later
"""Linux session bus: MPRIS transport and desktop sleep inhibitors."""
import asyncio
import os
import threading

from dbus_next import BusType, Message, MessageType, NameFlag, RequestNameReply, Variant
from dbus_next.aio import MessageBus
from dbus_next.constants import PropertyAccess as Access
from dbus_next.service import ServiceInterface, dbus_property, method

from linux_desktop import sway_inhibit_idle, sway_socket

PATH = '/org/mpris/MediaPlayer2'
NAME = 'org.mpris.MediaPlayer2.EarBear'


class MediaRoot(ServiceInterface):
    def __init__(self, app):
        super().__init__('org.mpris.MediaPlayer2')
        self.app = app

    @method()
    def Raise(self):
        self.app.cmds.put(('mpris', 'show'))

    @method()
    def Quit(self):
        self.app.cmds.put(('mpris', 'quit'))

    @dbus_property(access=Access.READ)
    def CanQuit(self) -> 'b': return True

    @dbus_property(access=Access.READ)
    def CanRaise(self) -> 'b': return True

    @dbus_property(access=Access.READ)
    def HasTrackList(self) -> 'b': return False

    @dbus_property(access=Access.READ)
    def Identity(self) -> 's': return 'EarBear'


    @dbus_property(access=Access.READ)
    def SupportedUriSchemes(self) -> 'as': return []

    @dbus_property(access=Access.READ)
    def SupportedMimeTypes(self) -> 'as': return []


class Player(ServiceInterface):
    def __init__(self, app):
        super().__init__('org.mpris.MediaPlayer2.Player')
        self.app = app

    @method()
    def Play(self): self.app.cmds.put(('mpris', 'play'))

    @method()
    def Pause(self): self.app.cmds.put(('mpris', 'pause'))

    @method()
    def PlayPause(self): self.app.cmds.put(('mpris', 'toggle'))

    @method()
    def Stop(self): self.app.cmds.put(('mpris', 'pause'))

    @method()
    def Next(self): pass

    @method()
    def Previous(self): pass

    @method()
    def Seek(self, offset: 'x'): pass

    @method()
    def SetPosition(self, track: 'o', position: 'x'): pass

    @method()
    def OpenUri(self, uri: 's'): pass

    @dbus_property(access=Access.READ)
    def PlaybackStatus(self) -> 's': return 'Playing' if self.app.playing else 'Paused'

    @dbus_property(access=Access.READ)
    def Metadata(self) -> 'a{sv}':
        return {'mpris:trackid': Variant('o', PATH + '/Noise'),
                'xesam:title': Variant('s', self.app.cur_preset or 'Ambient noise')}

    @dbus_property()
    def Volume(self) -> 'd': return self.app.vol

    @Volume.setter
    def Volume(self, value: 'd'): self.app.cmds.put(('mpris_volume', value))

    @dbus_property(access=Access.READ)
    def Position(self) -> 'x': return 0

    @dbus_property(access=Access.READ)
    def Rate(self) -> 'd': return 1.0

    @dbus_property(access=Access.READ)
    def MinimumRate(self) -> 'd': return 1.0

    @dbus_property(access=Access.READ)
    def MaximumRate(self) -> 'd': return 1.0

    @dbus_property(access=Access.READ)
    def CanGoNext(self) -> 'b': return False

    @dbus_property(access=Access.READ)
    def CanGoPrevious(self) -> 'b': return False

    @dbus_property(access=Access.READ)
    def CanSeek(self) -> 'b': return False

    @dbus_property(access=Access.READ)
    def CanPlay(self) -> 'b': return True

    @dbus_property(access=Access.READ)
    def CanPause(self) -> 'b': return True

    @dbus_property(access=Access.READ)
    def CanControl(self) -> 'b': return True


async def call(bus, destination, path, interface, member, signature='', body=None):
    reply = await asyncio.wait_for(bus.call(Message(destination=destination, path=path, interface=interface,
                                                    member=member, signature=signature, body=body or [])), 2)
    if reply.message_type == MessageType.ERROR:
        raise RuntimeError(str(reply.body))
    return reply


async def session(app, log):
    bus = await asyncio.wait_for(MessageBus().connect(), 2)
    player, media_root = Player(app), MediaRoot(app)
    published, previous, awake, system, fd, cookie = False, {}, 0, None, None, None
    screen = ('org.freedesktop.ScreenSaver', '/ScreenSaver', 'org.freedesktop.ScreenSaver')
    sway = sway_socket()
    sway_state = (0, False)
    try:
        while app.alive:
            if app.media != published:
                if app.media:
                    bus.export(PATH, media_root)
                    bus.export(PATH, player)
                    if await bus.request_name(NAME, NameFlag.DO_NOT_QUEUE) == RequestNameReply.PRIMARY_OWNER:
                        published, previous = True, {}
                    else:
                        bus.unexport(PATH)
                else:
                    await bus.release_name(NAME)
                    bus.unexport(PATH)
                    published = False
            if published:
                props = {k: getattr(player, k) for k in ('PlaybackStatus', 'Metadata', 'Volume')}
                changed = {k: v for k, v in props.items() if previous.get(k) != v}
                if changed:
                    player.emit_properties_changed(changed)
                    previous = props
            want = app.keep_awake if app.playing else 0
            if want != awake:
                awake = want
                if want and fd is None:
                    try:
                        if system is None:
                            system = await asyncio.wait_for(MessageBus(bus_type=BusType.SYSTEM, negotiate_unix_fd=True).connect(), 2)
                        reply = await call(system, 'org.freedesktop.login1', '/org/freedesktop/login1',
                                           'org.freedesktop.login1.Manager', 'Inhibit', 'ssss',
                                           ['sleep', 'EarBear', 'Playing ambient noise', 'block'])
                        fd = reply.unix_fds[reply.body[0]]
                    except Exception as exc:
                        log.dbg('system sleep inhibitor: %s' % exc)
                elif not want and fd is not None:
                    os.close(fd)
                    fd = None
                try:
                    if not sway and want >= 2 and cookie is None:
                        cookie = (await call(bus, *screen, 'Inhibit', 'ss', ['EarBear', 'Playing ambient noise'])).body[0]
                    elif want < 2 and cookie is not None:
                        await call(bus, *screen, 'UnInhibit', 'u', [cookie])
                        cookie = None
                except Exception as exc:
                    log.dbg('screen idle inhibitor: %s' % exc)
            if sway:
                # Sway drops a withdrawn view's inhibitor. Apply it again when the window maps.
                desired = (app.window_maps, want >= 2)
                if app.window_mapped and desired != sway_state:
                    try:
                        if not (desired[1] or sway_state[1]) or await asyncio.to_thread(sway_inhibit_idle, sway, desired[1]):
                            sway_state = desired
                    except (OSError, ValueError) as exc:
                        log.dbg('Sway idle inhibitor: %s' % exc)
                        sway_state = desired
            await asyncio.sleep(0.15)
    finally:
        if cookie is not None:
            try:
                await call(bus, *screen, 'UnInhibit', 'u', [cookie])
            except Exception:
                pass  # Disconnecting also releases connection-scoped inhibitors.
        if fd is not None:
            os.close(fd)
        if system:
            system.disconnect()
        bus.disconnect()


def start(app, log):
    def run():
        try:
            asyncio.run(session(app, log))
        except Exception as exc:
            log.write('WARN', 'Desktop session integration unavailable: %s' % exc)
    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return thread
