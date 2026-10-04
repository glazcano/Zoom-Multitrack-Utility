# H8 Studio

**From Zoom H8 recordings to a session ready for REAPER.**

Open `.h8prj` projects, listen to their tracks, and export aligned WAV or FLAC stems. A small preparation tool for recorded takes, with no editing or effects engine.

## Quick start

1. Keep each `.h8prj` beside its original WAV files, inside its `.zprj` folder.
2. Open a project, drop it onto the window, or browse a folder to build a project list.
3. Press **Space** to play or pause. Click the timeline to seek; use mute, solo, and gain to check each track.
4. Choose WAV or FLAC, leave **Crear .rpp** enabled, and export.
5. Open `Proyecto.rpp` in REAPER, or import all stems on separate tracks at **00:00**.

The interface currently uses Spanish labels.

Choose **Línea de tiempo**, **Consola**, or **Consola vertical**. Console shows side-by-side channels with waveforms above vertical faders; Vertical Console runs each waveform **from top to bottom**, alongside its fader and meter. Click or drag on any waveform to move the shared playhead. Switching views keeps playback and listening settings intact; the chosen view is remembered. Timeline zoom applies to Timeline; both consoles show the full take.

Compact **Abrir**, **Proyecto**, **Canales al abrir / lote**, and **Exportación** menus group the less frequent controls. **Avisos** opens import warnings; missing audio remains clearly indicated. Uncheck **Biblioteca** to give the viewer the full window width. Preparation tools (notes, range, templates, missing WAVs) are in **Proyecto**; format, `.rpp`, and presets are in **Exportación**.

## Prepare your takes

- **Names and templates:** rename projects and instruments, or save reusable input-to-instrument mappings.
- **Favorites and notes:** mark good takes and keep recording notes with the project.
- **Export range:** choose one section for every track; exports start at zero and have matching lengths.
- **Batch processing:** check projects in the library and export them together. A report lists completed, failed, and pending takes.
- **Problem summary:** check for missing audio, silence, very low levels, and possible clipping.
- **Find missing WAVs:** use **Localizar WAV…** to search a folder and its subfolders. Choose each match explicitly; matching checks name, duration, sample rate, and channels. Associations are saved without moving audio.
- **Search and filters:** find projects by name, notes, or folder; show favorites or missing/unreadable projects. Batch actions use checked, visible projects.
- **Listening tools:** per-track input peak meters remain active on muted tracks. **Mono centrado** places split mono channels in both speakers; **Repetir tramo** loops the saved export range. Both affect monitoring only.
- **Resume your session:** the last library, project, cursor, zoom, search, listening level, and export options return on the next launch, with playback paused.

### Stereo or two mono tracks

Use **2 mono** on a stereo track to split it into **L** and **R**. Use **Estéreo** on either channel to join the view again. Each mono channel has its own name, mute, solo, and listening gain. Playback retains left/right placement; switching pauses playback and keeps the cursor position.

The library's channel selector also supports bulk use:

| Choice | Behavior |
| --- | --- |
| **Usar elección guardada** | Keep each project's saved layout. |
| **Una pista estéreo** | Open or export stereo files as one track. |
| **Dos pistas mono (L/R)** | Open or export each stereo file as two mono tracks. |

Choose a mode before opening projects, or select projects and click **Aplicar canales al lote** to save it across the selection. During batch export, the selector overrides the output layout without changing saved preferences. Single-project export follows the visible tracks.

Split channels produce separate mono stems and REAPER tracks, panned left/right in the `.rpp`. Templates can label them individually with `Mic12.L` and `Mic12.R`; use `Mic12` for the stereo track.

### Export presets and portable delivery

Open **Exportación y presets…** to save, edit, apply, or delete presets for WAV/FLAC, channel layout, filename style, `.rpp`, and portable delivery. Channel choices apply to opening projects and batch export; individual export follows the visible tracks.

Enable **Carpeta de entrega** for a self-contained folder with stems, `Proyecto.rpp`, `Notes.txt`, instructions, export details, and SHA-256 checksums. Move or share the whole folder; REAPER uses relative media paths. This option always includes `.rpp`.

## Your recordings stay intact

Exports are dry **24-bit WAV or FLAC**, at the project's sample rate, with matching lengths and silence where needed. Listening gain, mute, and solo do not affect exported audio. Large WAVs use RF64.

Original audio and H8 project files are never rewritten. Names, notes, ranges, and channel choices live in a companion `.h8studio.json`; copy it with the project to keep your settings. Templates live in `.h8studio-templates.json` in the library folder. Each export gets a new folder and an `export.json` report.

Export presets and the last session are stored in the application's configuration folder. Linked WAVs outside the project remain external dependencies until you export a portable delivery.

## Compatibility

- Reads the tested **H8 v001** format. FIELD takes align using BWF timestamps; supported MUSIC takes share a common start and duration.
- MUSIC edits, regions, and overdubs are **not yet verified**. Separate project folders remain independent sessions.
- Missing WAVs allow partial listening but block export. Unassigned WAVs are reported and excluded.
- Windows builds have been tested locally. Fedora and macOS builds run through GitHub Actions; native playback still needs platform testing. macOS packages are not notarized.

See [platform setup and packaging](docs/platforms.md) and [format notes](docs/formato-h8.md) for details (in Spanish).

## Run or build

For a packaged Windows build, run `H8Studio.exe` and keep its `_internal` folder alongside it. Python is not needed for packaged builds.

For development, use **Python 3.12**:

```sh
python -m venv .venv
# Activate the environment: .venv\Scripts\Activate.ps1 on Windows,
# or source .venv/bin/activate on Fedora/macOS.
python -m pip install -r requirements-build.txt
python main.py
python -m unittest discover -s tests -v
python tools/verify_ui.py
python tools/build_native.py
```

Build on the target operating system, or run **Actions → Native desktop packages → Run workflow** on GitHub. Once all four builds pass, it creates a **draft release** for the app version, with native packages and checksums attached. Open **Releases**, review the draft, and click **Publish release** when ready. Fedora requires the system packages listed in the platform guide.

Increase `h8studio.__version__` and update `docs/release-notes.md` for a new release. Reruns may update the same draft only for the same commit; published releases are never overwritten.

Built with PySide6, NumPy, SoundFile, and sounddevice.
