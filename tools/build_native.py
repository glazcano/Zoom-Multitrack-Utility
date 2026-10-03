"""Build on the destination OS; never relabel a foreign executable."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import plistlib
import shutil
import subprocess
import sys
import tarfile
import zipfile

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from h8studio import __version__


def source_archive():
    output = ROOT/'releases'/f'H8Studio-{__version__}-source.zip'
    output.parent.mkdir(exist_ok=True)
    files = [ROOT/p for p in ['main.py', 'requirements.txt', 'requirements-build.txt',
             'build.ps1', 'build.sh', 'Abrir H8 Studio.cmd', 'README.md', '.gitignore']]
    for directory in ('h8studio', 'tools', 'tests', 'packaging', '.github'):
        files += [p for p in (ROOT/directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    files += [ROOT/'docs/platforms.md', ROOT/'docs/formato-h8.md', ROOT/'docs/release-notes.md']
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, 'H8Studio/'+path.relative_to(ROOT).as_posix())
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--plan', action='store_true')
    parser.add_argument('--source-only', action='store_true')
    args = parser.parse_args()
    if args.source_only:
        print(source_archive())
        return
    host = platform.system()
    arch = {'AMD64': 'x86_64', 'aarch64': 'arm64'}.get(platform.machine(), platform.machine())
    if host not in ('Windows', 'Linux', 'Darwin'):
        raise SystemExit(f'Unsupported build host: {host}')
    label = {'Windows': 'windows', 'Linux': 'fedora', 'Darwin': 'macos'}[host]
    if host == 'Linux' and platform.freedesktop_os_release().get('ID') != 'fedora':
        raise SystemExit('El paquete Fedora debe compilarse en Fedora (o en el contenedor Fedora de CI).')
    command = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--windowed',
               '--onedir', '--name', 'H8Studio', '--collect-all', 'soundfile',
               '--collect-all', 'sounddevice']
    for distribution in ('numpy', 'soundfile', 'sounddevice', 'PySide6', 'shiboken6'):
        command += ['--copy-metadata', distribution]
    identity = os.environ.get('H8_CODESIGN_IDENTITY', '')
    if host == 'Darwin':
        command += ['--osx-bundle-identifier', 'local.h8studio.app', '--target-architecture', arch]
        if identity:
            command += ['--codesign-identity', identity]
    command += ['main.py']
    if args.plan:
        print(json.dumps({'platform': label, 'arch': arch, 'command': command}, indent=2))
        return
    for name in ('build', 'dist'):
        target = (ROOT/name).resolve()
        if not target.is_relative_to(ROOT.resolve()) or target == ROOT.resolve():
            raise SystemExit(f'Ruta de compilación fuera del proyecto: {target}')
        child = (target/'H8Studio').resolve()
        if not child.is_relative_to(target):
            raise SystemExit(f'Destino enlazado fuera del proyecto: {child}')
    subprocess.run(command, cwd=ROOT, check=True)
    bundle = ROOT/'dist'/('H8Studio.app' if host == 'Darwin' else 'H8Studio')
    if host == 'Windows':
        for name in ('icuuc.dll', 'icudt78.dll'):
            (bundle/'_internal'/name).unlink(missing_ok=True)
    documents = bundle/'Contents/Resources' if host == 'Darwin' else bundle
    shutil.copy2(ROOT/'README.md', documents/'LEEME.md')
    shutil.copy2(ROOT/'docs/platforms.md', documents/'PLATAFORMAS.md')
    if host == 'Linux':
        shutil.copy2(ROOT/'packaging/fedora/install.py', bundle/'install.py')
    if host == 'Darwin':
        plist_path = bundle/'Contents/Info.plist'
        with plist_path.open('rb') as f:
            info = plistlib.load(f)
        info.update(CFBundleShortVersionString=__version__, CFBundleVersion=__version__,
                    CFBundleDocumentTypes=[{'CFBundleTypeName': 'Zoom H8 Project',
                    'CFBundleTypeExtensions': ['h8prj'], 'CFBundleTypeRole': 'Viewer'}])
        with plist_path.open('wb') as f:
            plistlib.dump(info, f)
        signing = ['codesign', '--force', '--sign', identity or '-']
        if identity:
            signing += ['--options', 'runtime', '--timestamp']
        subprocess.run(signing+[str(bundle)], check=True)
        subprocess.run(['codesign', '--verify', '--deep', '--strict', str(bundle)], check=True)
    releases = ROOT/'releases'
    releases.mkdir(exist_ok=True)
    stem = f'H8Studio-{__version__}-{label}-{arch}'
    if host == 'Darwin':
        archive = releases/(stem+'.zip')
        subprocess.run(['ditto', '-c', '-k', '--sequesterRsrc', '--keepParent', str(bundle), str(archive)], check=True)
    elif host == 'Linux':
        archive = releases/(stem+'.tar.gz')
        with tarfile.open(archive, 'w:gz') as f:
            f.add(bundle, arcname=bundle.name)
    else:
        archive = Path(shutil.make_archive(str(releases/stem), 'zip', bundle.parent, bundle.name))
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_suffix(archive.suffix+'.sha256').write_text(f'{digest}  {archive.name}\n', encoding='utf-8')
    print(f'Native package: {archive}')


if __name__ == '__main__':
    main()
