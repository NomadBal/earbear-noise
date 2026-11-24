# SPDX-License-Identifier: GPL-3.0-or-later
"""Linux autostart, launch activation and X11 shortcuts."""
import hashlib
import json
import os
from pathlib import Path
import socket
import struct
import subprocess
import tempfile
import time

APP_ID = 'io.github.NomadBal.EarBear'


def xdg(var, default):
    path = Path(os.environ.get(var, ''))
    return path if path.is_absolute() else Path.home() / default


def autostart_path():
    return xdg('XDG_CONFIG_HOME', '.config') / 'autostart' / (APP_ID + '.desktop')


def write_autostart(path):
    launcher = str(Path(__file__).resolve().with_name('EarBear'))
    # Desktop entries have two levels of escaping, and % introduces a field code.
    launcher = launcher.replace('%', '%%').replace('\\', '\\\\')
    for c in ('"', '$', '`'):
        launcher = launcher.replace(c, '\\' + c)
    launcher = launcher.replace('\\', '\\\\').replace('\n', '\\n').replace('\r', '\\r')
    text = f'[Desktop Entry]\nType=Application\nName=EarBear\nExec="{launcher}" --hidden\nTerminal=false\n'
    if path.is_file() and path.read_text(encoding='utf-8') == text:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, delete=False) as f:
        temp = Path(f.name)
        try:
            f.write(text)
            f.close()
            temp.replace(path)
        finally:
            temp.unlink(missing_ok=True)


def activate(config, command):
    """Bind a per-profile abstract socket, or send a same-user command to its owner."""
    digest = hashlib.sha256(os.fsencode(config.resolve())).hexdigest()[:32]
    address = '\0earbear-%d-%s' % (os.getuid(), digest)
    with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as client:
        try:
            client.settimeout(0.5)
            client.sendto(command.encode(), address)
            if command == 'quit':
                # The stop helper must return only after the instance released its socket.
                deadline = time.monotonic() + 5
                while time.monotonic() < deadline:
                    client.connect(address)
                    time.sleep(0.05)
                raise TimeoutError('EarBear did not stop within five seconds')
            return None
        except ConnectionRefusedError:
            pass
        if command == 'quit':
            return None
        listener = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM | socket.SOCK_NONBLOCK)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
        try:
            listener.bind(address)
        except OSError:
            listener.close()
            client.sendto(command.encode(), address)  # another launch won the bind race
            return None
        return listener


def read_command(listener):
    size = struct.calcsize('3i')
    data, control, flags, _ = listener.recvmsg(16, socket.CMSG_SPACE(size))
    if flags & (socket.MSG_TRUNC | socket.MSG_CTRUNC):
        return None
    for level, kind, credentials in control:
        if level == socket.SOL_SOCKET and kind == socket.SCM_CREDENTIALS:
            _, uid, _ = struct.unpack('3i', credentials)
            if uid == os.getuid() and data in (b'show', b'toggle', b'quit'):
                return data.decode()
    return None


def wayland_session():
    return bool(os.environ.get('WAYLAND_DISPLAY') or os.environ.get('XDG_SESSION_TYPE') == 'wayland')


def x11_session():
    return bool(os.environ.get('DISPLAY') and not wayland_session())


def sway_socket():
    return os.environ.get('SWAYSOCK') if wayland_session() else None


def sway_inhibit_idle(sock, enabled):
    """Apply the inhibitor to EarBear's view rather than the focused window."""
    mode = 'open' if enabled else 'none'
    try:
        result = subprocess.run(['swaymsg', '-s', sock, '-r', '--',
                                 f'[pid={os.getpid()} class="(?i)^earbear$"] inhibit_idle {mode}'],
                                capture_output=True, text=True, timeout=1)
    except subprocess.TimeoutExpired as exc:
        raise TimeoutError('Sway did not respond to the idle inhibitor request') from exc
    replies = json.loads(result.stdout) if result.stdout else []
    return not result.returncode and bool(replies) and all(reply.get('success') for reply in replies)


class Hotkey:
    def __init__(self, root, key, toggle):
        from Xlib import X, XK, display, error
        self.root = root
        self.display = d = display.Display()
        self.code = d.keysym_to_keycode(XK.string_to_keysym(key.lower()))
        self.mods = X.ControlMask | X.Mod1Mask
        self.keys_down = False
        failures = error.CatchError()
        try:
            locks = {0}
            for sym in ('Num_Lock', 'Caps_Lock', 'Scroll_Lock'):
                code = d.keysym_to_keycode(XK.string_to_keysym(sym))
                for i, keys in enumerate(d.get_modifier_mapping()):
                    if code and code in keys:
                        locks |= {mask | (1 << i) for mask in locks}
            for lock in locks:
                d.screen().root.grab_key(self.code, self.mods | lock, False, X.GrabModeAsync, X.GrabModeAsync,
                                         onerror=failures)
            d.sync()
            if failures.get_error():
                raise RuntimeError('Ctrl+Alt+%s is already in use' % key.title())
            released = None

            def events(*_):
                nonlocal released
                while d.pending_events():
                    event = d.next_event()
                    if event.type == X.KeyPress and not self.keys_down:
                        self.keys_down = True
                        if event.time != released:
                            toggle()
                    elif event.type == X.KeyRelease:
                        # X11 auto-repeat delivers a release/press pair with the same timestamp.
                        released = event.time
                        self.keys_down = False
            root.createfilehandler(d, 2, events)  # tkinter.READABLE
        except Exception:
            d.close()
            raise

    def close(self):
        self.root.deletefilehandler(self.display)
        self.display.close()


def tray_available():
    try:
        found = subprocess.run(['gdbus', 'call', '--session', '--timeout', '1',
                                '--dest', 'org.kde.StatusNotifierWatcher',
                                '--object-path', '/StatusNotifierWatcher', '--method',
                                'org.freedesktop.DBus.Properties.Get', 'org.kde.StatusNotifierWatcher',
                                'IsStatusNotifierHostRegistered'], capture_output=True, text=True, timeout=2)
        return found.returncode == 0 and '<true>' in found.stdout
    except (OSError, subprocess.TimeoutExpired):
        return False


class Tray:
    def __init__(self, root, icon, dispatch):
        import gi
        gi.require_version('Gtk', '3.0')
        from gi.repository import GLib, Gtk
        try:
            gi.require_version('AyatanaAppIndicator3', '0.1')
            from gi.repository import AyatanaAppIndicator3 as Indicator
        except ValueError:
            gi.require_version('AppIndicator3', '0.1')
            from gi.repository import AppIndicator3 as Indicator
        if not Gtk.init_check()[0]:
            raise RuntimeError('GTK could not connect to the display')
        cache = xdg('XDG_CACHE_HOME', '.cache') / 'earbear'
        cache.mkdir(parents=True, exist_ok=True)
        image = cache / 'tray.png'
        image.write_bytes(icon)
        self.indicator = Indicator.Indicator.new(APP_ID, str(image), Indicator.IndicatorCategory.APPLICATION_STATUS)
        self.indicator.set_title('EarBear')
        menu = Gtk.Menu()
        for label, action in (('Open EarBear', 'show'), ('Play/Pause', 'toggle'), ('Quit', 'quit')):
            item = Gtk.MenuItem.new_with_label(label)
            item.connect('activate', lambda _, action=action: dispatch(action))
            menu.append(item)
        menu.show_all()
        self.indicator.set_menu(menu)
        self.indicator.set_status(Indicator.IndicatorStatus.ACTIVE)
        self.visible = True
        self.passive = Indicator.IndicatorStatus.PASSIVE
        self.root = root
        self.context = GLib.MainContext.default()
        self.poll()

    def poll(self):
        # Keep GTK and Tk on the same UI thread; GTK handles only tray events.
        for _ in range(32):
            if not self.context.iteration(False):
                break
        if self.visible:
            self.root.after(40, self.poll)

    def stop(self):
        self.visible = False
        self.indicator.set_status(self.passive)
        self.poll()
