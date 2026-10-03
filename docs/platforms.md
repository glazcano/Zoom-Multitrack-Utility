# H8 Studio · distribución multiplataforma

## Estado de esta entrega

Código común y recetas para Windows x64, Fedora 43 x86_64 y macOS Apple Silicon/Intel.
Windows se compila y prueba aquí. Fedora y macOS necesitan ejecutar sus recetas en
esos sistemas: no se generan binarios nativos de esos sistemas desde Windows.
La automatización está guardada, pero no se ha subido ni ejecutado en GitHub.
La reproducción física, Wayland y apertura desde Finder requieren pruebas nativas.

## Fedora

Extrae el ZIP fuente y abre una terminal en la carpeta H8Studio:

```bash
sudo dnf install python3.12 python3.12-devel gcc binutils portaudio libsndfile \
  libX11 libXext libXrender libxcb libXcursor libXi libXrandr libXtst \
  libxkbcommon libxkbcommon-x11 xcb-util-cursor xcb-util-image \
  xcb-util-keysyms xcb-util-wm mesa-libGL fontconfig dbus-libs \
  dejavu-sans-fonts alsa-plugins-pulseaudio
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-build.txt
.venv/bin/python main.py
```

Compila con `bash build.sh`: produce un `.tar.gz` en `releases/`. El paquete usa
glibc y bibliotecas de Fedora; no se promete compatibilidad con versiones anteriores
ni con otras distribuciones.

En el destino instala las dependencias de audio/interfaz anteriores (Python de
desarrollo, gcc y binutils solo son necesarios para compilar). Extrae el paquete y
ejecuta `./H8Studio/H8Studio`. Para añadirlo al menú: `python3 H8Studio/install.py`.
Instala bajo `~/.local/opt/h8-studio`, sin root y sin sobrescribir instalaciones.
Para actualizar, conserva o retira esa carpeta y
`~/.local/share/applications/h8-studio.desktop` antes de ejecutar el instalador.

Usa una sesión gráfica con audio. Si encuentras un problema específico de Wayland,
prueba `QT_QPA_PLATFORM=xcb ./H8Studio/H8Studio` en una sesión con XWayland.
PortAudio usa la salida predeterminada; la app no solicita entrada de micrófono.

## macOS

Instala Python 3.12 de python.org para tu arquitectura y las herramientas de Xcode
(`xcode-select --install`, si faltan). En una terminal dentro del código fuente:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-build.txt
.venv/bin/python main.py
bash build.sh
```

Produce `dist/H8Studio.app` y un ZIP. Compila por separado en Apple Silicon e Intel;
no se afirma que exista un binario universal. CI usa macOS 15 para ambas arquitecturas.
No se ha establecido compatibilidad mínima con versiones anteriores.

Extrae el ZIP y copia H8Studio.app a Aplicaciones. El paquete registra `.h8prj` como
documento de lectura y atiende eventos Finder. Abrir usa Cmd+O; también se pueden
arrastrar archivos a la ventana.

Por defecto se aplica firma local ad hoc, no Developer ID. Para distribución pública,
configura `H8_CODESIGN_IDENTITY` con una identidad Developer ID Application ya
instalada en el llavero antes de compilar. Después usa tu perfil notarytool:

```bash
xcrun notarytool submit releases/H8Studio-0.3.0-macos-arm64.zip --keychain-profile PERFIL --wait
xcrun stapler staple dist/H8Studio.app
ditto -c -k --sequesterRsrc --keepParent dist/H8Studio.app releases/H8Studio-0.3.0-macos-arm64-notarized.zip
```

Ajusta el nombre a x86_64 para Intel. Comprueba Accepted antes de distribuir.
Developer ID y notarización no se han realizado. No se incluyen credenciales ni
se modifica Gatekeeper.

## Windows

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\build.ps1
```

Conserva `dist/H8Studio/H8Studio.exe` y genera un ZIP completo en `releases/`.
Cada paquete nativo tiene un SHA-256 al lado. Mantén `_internal` junto al ejecutable.

## Automatización y pruebas

`.github/workflows/native-packages.yml` define cuatro compilaciones manuales:
Windows, Fedora y ambas arquitecturas macOS. Cuando el código esté en un repositorio
GitHub, ejecuta **Actions → Native desktop packages → Run workflow**. Solo genera
artefactos de ejecución, no releases públicas. Este repositorio aún no está conectado.

El ZIP fuente y los paquetes excluyen Projects y tus audios. Las pruebas portables
generan audio sintético. Las pruebas del corpus privado se omiten si no está disponible;
exportación, plantillas, favoritos, notas, recortes y lotes se prueban igualmente.

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python tools/verify_ui.py
.venv/bin/python tools/synthetic_project.py test-output/fixture
.venv/bin/python main.py --verify-no-audio test-output/fixture test-output/report.json
```

`--verify-no-audio` comprueba Qt y exportación WAV/FLAC/RPP, sin acreditar salida
de audio. En una sesión gráfica repite con `--verify` (monitor silenciado) y realiza
una escucha manual. Prueba Finder en macOS y el acceso de aplicaciones en Fedora.

Fuentes: [PyInstaller](https://pyinstaller.org/en/stable/usage.html),
[sounddevice](https://python-sounddevice.readthedocs.io/en/latest/installation.html),
[Qt en Linux](https://doc.qt.io/qt-6/linux-requirements.html).
