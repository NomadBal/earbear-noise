#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Assemble the portable ZIP from the build host's Linux runtime."""
import ast
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import sysconfig
import tempfile
import tkinter

import gi
from gi import _gi


APP = ('EarBear', 'EarBear-debug.sh', 'EarBear-stop-all.sh', 'earbear.py',
       'linux_audio.py', 'linux_desktop.py', 'linux_session.py', 'earbear.ico',
       'LICENSE', 'THIRD_PARTY.md', 'CHANGELOG.txt')
GLIBC = {'libc.so.6', 'libm.so.6', 'libmvec.so.1', 'libpthread.so.0', 'libdl.so.2',
         'librt.so.1', 'libresolv.so.2', 'libutil.so.1', 'ld-linux-x86-64.so.2'}


def run(*args):
    return subprocess.check_output(args, text=True)


def copy(source, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, dest)


def tree(source, dest, *ignored):
    shutil.copytree(source, dest, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc', *ignored))


def build(app):
    for name in APP:
        copy(name, app / name)
    runtime = app / 'python'
    native = runtime / 'lib'
    stdlib = runtime / sys.platlibdir / f'python{sys.version_info.major}.{sys.version_info.minor}'
    packages = stdlib / 'site-packages'
    tree(sysconfig.get_path('stdlib', vars={'base': sys.base_prefix}), stdlib, 'site-packages')
    tree(Path(gi.__file__).parent, packages / 'gi')
    subprocess.run(['uv', '--no-config', 'pip', 'install', '--link-mode', 'copy', '--python', sys.executable,
                    '--only-binary', ':all:', '--target', str(packages), '-r', 'requirements.txt'], check=True)

    executables = {'python': Path(sys.executable).resolve()}
    for name in ('gdbus', 'swaymsg'):
        path = shutil.which(name)
        if path is None:
            raise SystemExit(f'{name} is required on the build host.')
        executables[name] = Path(path).resolve()
    for name, source in executables.items():
        copy(source, runtime / 'bin' / name)
    tcl = Path(tkinter.Tcl().eval('info library'))
    tree(tcl, runtime / 'share' / 'tcl')
    tree(tcl.with_name(tcl.name.replace('tcl', 'tk', 1)), runtime / 'share' / 'tk')

    # GI loads these at runtime; the ELF dependency graph alone cannot find them.
    repo = _gi.Repository.get_default()
    repo.require('AyatanaAppIndicator3', '0.1')
    repo.require('GdkX11', '3.0')
    typelibs = [Path(repo.get_typelib_path(name)) for name in repo.get_loaded_namespaces()]
    for path in typelibs:
        copy(path, native / 'girepository-1.0' / path.name)
    schemas = sorted(Path('/usr/share/glib-2.0/schemas').glob('org.gtk.*.gschema.xml'))
    schemas += sorted(Path('/usr/share/glib-2.0/schemas').glob('org.gnome.desktop.*.gschema.xml'))
    schemas += sorted(Path('/usr/share/glib-2.0/schemas').glob('org.gnome.desktop*.enums.xml'))
    schema_dir = runtime / 'share' / 'glib-2.0' / 'schemas'
    for path in schemas:
        copy(path, schema_dir / path.name)
    subprocess.run(['glib-compile-schemas', '--strict', str(schema_dir)], check=True)

    cache = dict(re.findall(r'^\s*(\S+) \([^\n]+x86-64[^\n]*\) => (\S+)$',
                            run('ldconfig', '-p'), re.MULTILINE))
    libraries = {name: Path(cache[name]).resolve() for name in
                 ('libpulse.so.0', 'libpulse-simple.so.0', 'libayatana-appindicator3.so.1',
                  'libgtk-3.so.0', 'libgmodule-2.0.so.0')}
    elfs = [*executables.values(), *libraries.values(), *stdlib.rglob('*.so'), *stdlib.rglob('*.so.*')]
    for elf in elfs:
        for line in run('ldd', str(elf)).splitlines():
            name, arrow, target = line.strip().partition(' => ')
            if not arrow or name in GLIBC:
                continue
            if target.startswith('not found'):
                raise RuntimeError(f'{elf}: {name} not found')
            source = Path(target.split()[0]).resolve()
            if not source.is_relative_to(runtime) and libraries.setdefault(name, source) != source:
                raise RuntimeError(f'{elf}: conflicting copies of {name}')
    for name, source in libraries.items():
        copy(source, native / name)

    # Preserve notices and source RPM identities for the host files we redistribute.
    files = {*executables.values(), *libraries.values(), *typelibs, *schemas, tcl / 'init.tcl',
             tcl.with_name(tcl.name.replace('tcl', 'tk', 1)) / 'tk.tcl', Path(gi.__file__)}
    host_stdlib = Path(sysconfig.get_path('stdlib', vars={'base': sys.base_prefix}))
    files.update(host_stdlib / p.relative_to(stdlib) for p in stdlib.glob('lib-dynload/*.so'))
    if shutil.which('rpm'):
        notices = app / 'licenses' / 'host'
        notices.mkdir(parents=True)
        owners = set(run('rpm', '-qf', '--qf', '%{NAME}\n', *sorted(map(str, files))).splitlines())
        (notices / 'packages.tsv').write_text(run('rpm', '-q', '--qf', '%{NEVRA}\t%{SOURCERPM}\n', *sorted(owners)))
        for name in owners:
            directory = Path('/usr/share/licenses') / name
            if directory.is_dir():
                tree(directory, notices / name)


def main():
    if sys.platform != 'linux' or os.uname().machine != 'x86_64':
        raise SystemExit('Build on a glibc-based x86-64 Linux host.')
    version = next(ast.literal_eval(stmt.value) for stmt in ast.parse(Path('earbear.py').read_text()).body
                   if isinstance(stmt, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'VERSION'
                                                         for t in stmt.targets))
    dist = Path('dist').resolve()
    dist.mkdir(exist_ok=True)
    name = f'EarBear-{version}-linux-x86_64-portable'
    with tempfile.TemporaryDirectory(dir=dist) as folder:
        stage = Path(folder)
        build(stage / 'EarBear')
        archive = shutil.make_archive(str(stage / name), 'zip', root_dir=stage, base_dir='EarBear')
        Path(archive).replace(dist / (name + '.zip'))
    print(dist / (name + '.zip'))


if __name__ == '__main__':
    main()
