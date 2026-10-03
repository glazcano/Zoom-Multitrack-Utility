"""Install an extracted Fedora bundle for the current user, without root."""
from pathlib import Path
import shutil
import sys

if not sys.platform.startswith('linux'):
    raise SystemExit('Este instalador es para Linux.')
source = Path(__file__).resolve().parent
prefix = Path.home()/'.local'
target = prefix/'opt/h8-studio'
desktop = prefix/'share/applications/h8-studio.desktop'
if not (source/'H8Studio').is_file():
    raise SystemExit('Ejecuta install.py dentro del paquete Fedora extraído.')
if target.exists() or desktop.exists():
    raise SystemExit('Ya existe una instalación. Conserva o retira ~/.local/opt/h8-studio y su .desktop antes de instalar otra versión.')
target.parent.mkdir(parents=True, exist_ok=True)
desktop.parent.mkdir(parents=True, exist_ok=True)
shutil.copytree(source, target, symlinks=True)
executable = str(target/'H8Studio').replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$')
desktop.write_text('[Desktop Entry]\nType=Application\nName=H8 Studio\nComment=Preparar proyectos Zoom H8 para Reaper\n'
                   f'Exec="{executable}" %f\nTerminal=false\nCategories=AudioVideo;Audio;\n', encoding='utf-8')
print(f'Instalado: {target}\nAcceso de aplicaciones: {desktop}')
