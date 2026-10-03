"""H8 v001 reader and sample-accurate, bounded-memory audio rendering."""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from contextlib import ExitStack
import datetime as dt
import json
import os
import re
import shutil
import struct
import tempfile
import threading

import numpy as np
import soundfile as sf
from .platforms import project_files


class ProjectError(ValueError):
    pass


def title_file(path: Path) -> Path:
    return Path(path).with_suffix('.h8studio.json')


def title_settings(path: Path) -> dict:
    sidecar = title_file(path)
    if not sidecar.exists():
        return {}
    try:
        data = json.loads(sidecar.read_text(encoding='utf-8'))
        if not isinstance(data, dict):
            raise ValueError('Se esperaba un objeto JSON')
        if 'title' in data:
            data['title'] = validate_title(data['title'])
        if 'tracks' in data:
            if not isinstance(data['tracks'], dict):
                raise ValueError('Las etiquetas de pistas deben ser un objeto JSON')
            data['tracks'] = {key: validate_title(value) for key, value in data['tracks'].items()}
        return data
    except (ValueError, OSError) as exc:
        raise ProjectError(f'No se pudo leer el título guardado en {sidecar.name}: {exc}') from exc


def validate_title(value: str) -> str:
    if not isinstance(value, str):
        raise ProjectError('El título debe ser texto.')
    value = value.strip()
    if not value or len(value) > 100 or any(ord(c) < 32 for c in value):
        raise ProjectError('Escribe un título de 1 a 100 caracteres, en una sola línea.')
    return value


def rename_project(project: 'Project', title: str):
    title = validate_title(title)
    data = title_settings(project.path)
    data['title'] = title
    save_settings(project, data)
    project.name = title


def rename_track(project: 'Project', track: 'Track', title: str):
    title = validate_title(title)
    if not any(t is track for t in project.tracks) or not track.clips:
        raise ProjectError('La pista no pertenece al proyecto.')
    data = title_settings(project.path)
    data.setdefault('tracks', {})[track_key(track)] = title
    save_settings(project, data)
    track.name = title


def save_settings(project: 'Project', data: dict):
    destination = title_file(project.path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=destination.parent,
                                         prefix='.h8-title-', suffix='.tmp', delete=False) as f:
            temporary = Path(f.name)
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporary, destination)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


@dataclass
class Clip:
    path: Path
    start: int
    frames: int
    channels: int
    source_start: int = 0
    missing: bool = False
    channel: int | None = None


@dataclass
class Track:
    name: str
    clips: list[Clip] = field(default_factory=list)
    gain: float = 1.0
    mute: bool = False
    solo: bool = False
    peak: float = 0.0

    @property
    def output_channel(self):
        return self.clips[0].channel if self.clips else None

    @property
    def channels(self):
        return max((c.channels for c in self.clips), default=1)


@dataclass
class Project:
    name: str
    path: Path
    rate: int
    frames: int
    tracks: list[Track]
    warnings: list[str] = field(default_factory=list)
    alignment: str = "Inicio común"
    favorite: bool = False
    notes: str = ''
    export_range: tuple[int, int] | None = None
    source_tracks: list[Track] = field(default_factory=list, repr=False)
    split_pairs: dict = field(default_factory=dict, repr=False)

    @property
    def length(self):
        return max([self.frames] + [c.start + c.frames for t in self.tracks for c in t.clips])


def track_key(track):
    key = track.clips[0].path.name.casefold()
    return key if track.output_channel is None else key + ('#L' if track.output_channel == 0 else '#R')


def set_stereo_split(project, split, filename=None, persist=True):
    """Switch source stereo tracks to virtual L/R tracks without rewriting audio.

    Keep both representations in memory so monitor controls survive toggling.
    Only channel layout and labels persist across application sessions.
    """
    if not project.source_tracks:
        project.source_tracks = list(project.tracks)
    settings = title_settings(project.path)
    modes = dict(settings.get('split_stereo', {}))
    labels = settings.get('tracks', {})
    for source in project.source_tracks:
        key = source.clips[0].path.name.casefold()
        if source.channels == 2 and (filename is None or key == filename.casefold()):
            modes[key] = bool(split)
    if persist:
        settings['split_stereo'] = modes
        save_settings(project, settings)
    tracks = []
    for source in project.source_tracks:
        key = source.clips[0].path.name.casefold()
        if source.channels != 2 or not modes.get(key, False):
            tracks.append(source)
            continue
        if key not in project.split_pairs:
            pair = []
            for channel, suffix in enumerate(('L', 'R')):
                clips = [replace(c, channels=1, channel=channel) for c in source.clips]
                track = Track(source.name + ' ' + suffix, clips, source.gain, source.mute, source.solo)
                track.name = labels.get(track_key(track), track.name)
                pair.append(track)
            project.split_pairs[key] = pair
        tracks.extend(project.split_pairs[key])
    project.tracks = tracks


def bwf_reference(path: Path):
    """Return (origination date, 64-bit sample reference), EBU Tech 3285."""
    with path.open('rb') as f:
        head = f.read(12)
        if len(head) != 12 or head[:4] not in (b'RIFF', b'RF64') or head[8:] != b'WAVE':
            return None
        size = path.stat().st_size
        while f.tell() + 8 <= size:
            tag, length = struct.unpack('<4sI', f.read(8))
            if length > size - f.tell():
                return None
            if tag == b'bext' and length >= 346:
                b = f.read(346)
                date = b[320:330].decode('ascii', errors='replace').rstrip('\0')
                return date, struct.unpack_from('<Q', b, 338)[0]
            f.seek(length + (length & 1), 1)
    return None


def read_project(path: str | Path, audio_links=None) -> Project:
    path = Path(path).resolve()
    if path.is_dir():
        choices = project_files(path)
        if len(choices) != 1:
            raise ProjectError('La carpeta debe contener exactamente un archivo .h8prj.')
        path = choices[0]
    b = path.read_bytes()
    links = title_settings(path).get('audio_links', {}) if audio_links is None else audio_links
    if not isinstance(links, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in links.items()):
        raise ProjectError('Referencias de WAV guardadas inválidas.')
    if len(b) != 10312 or b[:32] != b'ZOOM H8 ProjectFile v001        ':
        raise ProjectError('Versión o estructura H8 no reconocida. No se adivinarán las posiciones.')
    name = b[32:552].decode('utf-16le').split('\0')[0]
    frames = struct.unpack_from('<Q', b, 552)[0]
    rate, bits = struct.unpack_from('<II', b, 564)
    if rate not in (44100, 48000, 96000) or bits not in (16, 24) or frames > rate * 86400:
        raise ProjectError('Cabecera H8 fuera del formato comprobado.')
    # 12 fixed filename slots, each 260 UTF-16 code units. These are NOT clip offsets.
    names = [b[1496+i*520:1496+(i+1)*520].decode('utf-16le').split('\0')[0] for i in range(12)]
    lookup = {p.name.casefold(): p for p in path.parent.iterdir() if p.is_file() and not p.name.startswith('._')}
    warnings, tracks, refs = [], [], []
    seen = set()
    for filename in names:
        if not filename or filename.casefold() in seen:
            continue
        seen.add(filename.casefold())
        if '/' in filename or '\\' in filename or ':' in filename or not filename.lower().endswith('.wav'):
            raise ProjectError('Referencia de audio no reconocida en el proyecto.')
        audio = lookup.get(filename.casefold(), path.parent / filename)
        if not audio.exists() and filename.casefold() in links:
            linked = Path(links[filename.casefold()])
            linked = linked if linked.is_absolute() else path.parent/linked
            if linked.is_file():
                audio = linked.resolve()
        missing = not audio.exists()
        channels = 2 if re.search(r'(12|34|LR)', filename, re.I) else 1
        n = frames
        ref = None
        if missing:
            warnings.append(f'Falta {filename}. No se permite exportar hasta localizarlo.')
        else:
            try:
                info = sf.info(str(audio))
                if info.samplerate != rate or info.channels not in (1, 2):
                    raise ProjectError(f'{filename}: frecuencia o canales incompatibles con el proyecto.')
                n, channels = info.frames, info.channels
                ref = bwf_reference(audio)
            except (RuntimeError, OSError) as exc:
                raise ProjectError(f'No se puede leer {filename}: {exc}') from exc
        tracks.append(Track(Path(filename).stem, [Clip(audio, 0, n, channels, missing=missing)]))
        refs.append(ref)
    if not tracks:
        raise ProjectError('El proyecto no contiene referencias a WAV.')
    alignment = 'Inicio común · asignaciones H8'
    present = [(t, r) for t, r in zip(tracks, refs) if not t.clips[0].missing]
    # FIELD timestamps are wall clock. MUSIC uses project-relative/zero references;
    # do not reinterpret MUSIC recording dates as arrangement offsets.
    if name.startswith('F') and present and all(r is not None for _, r in present):
        try:
            stamps = [(t, dt.date.fromisoformat(r[0]).toordinal()*86400*rate+r[1]) for t, r in present]
        except ValueError as exc:
            raise ProjectError('Fecha BWF inválida; no se puede determinar la alineación.') from exc
        origin = min(s for _, s in stamps)
        if max(s for _, s in stamps) - origin > rate*86400:
            raise ProjectError('Referencias BWF separadas por más de un día; revise el proyecto.')
        for t, s in stamps:
            t.clips[0].start = s-origin
        alignment = 'BWF · muestras relativas al primer WAV'
    elif any(t.clips[0].frames != frames for t, _ in present):
        raise ProjectError('Este proyecto tiene tomas de distinta duración sin alineación FIELD verificable. Se necesita analizar su disposición MUSIC antes de importarlo.')
    if any(t.clips[0].start or t.clips[0].frames != frames for t, _ in present):
        warnings.append('Se usaron tiempos BWF de grabación; no representan necesariamente ediciones hechas en la grabadora.')
    extras = [p.name for p in lookup.values() if p.suffix.lower() == '.wav' and p.name.casefold() not in seen]
    if extras:
        warnings.append('WAV sin asignación, no importados: ' + ', '.join(extras))
    warnings.append('Lectura v001 validada con tomas completas. Ediciones, overdubs y regiones MUSIC aún no verificados.')
    # Apply the display title only AFTER interpreting the recorder's original name.
    # A custom title must never change FIELD/MUSIC alignment behavior.
    try:
        settings = title_settings(path)
        name = settings.get('title', name or path.stem)
        for track in tracks:
            track.name = settings.get('tracks', {}).get(track.clips[0].path.name.casefold(), track.name)
    except ProjectError as exc:
        warnings.append(str(exc))
    project = Project(name or path.stem, path, rate, frames, tracks, warnings, alignment)
    try:
        settings = title_settings(path)
        favorite, notes = settings.get('favorite', False), settings.get('notes', '')
        if not isinstance(favorite, bool) or not isinstance(notes, str) or len(notes) > 10000:
            raise ProjectError('Favorito o notas guardadas inválidas.')
        region = settings.get('export_range')
        if region is not None:
            if not isinstance(region, list) or len(region) != 2:
                raise ProjectError('Tramo guardado inválido.')
            validate_range(project, *region)
            project.export_range = tuple(region)
        project.favorite, project.notes = favorite, notes
    except ProjectError as exc:
        raise ProjectError(f'Preferencias de preparación inválidas: {exc}') from exc
    modes = settings.get('split_stereo', {})
    if not isinstance(modes, dict) or any(not isinstance(k, str) or type(v) is not bool for k, v in modes.items()):
        raise ProjectError('Preferencias de canales inválidas.')
    set_stereo_split(project, False, filename='', persist=False)
    return project


def validate_range(project, start, end):
    if type(start) is not int or type(end) is not int or not 0 <= start < end <= project.length:
        raise ProjectError('El tramo debe tener inicio menor que fin y estar dentro de la grabación.')


def save_preparation(project, favorite, notes, region):
    if not isinstance(favorite, bool) or not isinstance(notes, str) or len(notes) > 10000:
        raise ProjectError('Las notas admiten hasta 10 000 caracteres.')
    if region is not None:
        validate_range(project, *region)
    data = title_settings(project.path)
    data.update(favorite=favorite, notes=notes, export_range=list(region) if region else None)
    save_settings(project, data)
    project.favorite, project.notes, project.export_range = favorite, notes, region


class Renderer:
    """Shared playback/export rendering. Integer sample positions throughout."""
    def __init__(self, project: Project):
        self.project = project
        self.stack = ExitStack()
        self.files = {}
        try:
            for track in project.tracks:
                for clip in track.clips:
                    if not clip.missing and clip.path not in self.files:
                        self.files[clip.path] = self.stack.enter_context(sf.SoundFile(str(clip.path)))
        except Exception:
            self.close()
            raise

    def close(self):
        self.stack.close()

    def track_block(self, track: Track, start: int, count: int):
        out = np.zeros((count, track.channels), dtype=np.float64)
        for c in track.clips:
            lo, hi = max(start, c.start), min(start+count, c.start+c.frames)
            if c.missing or hi <= lo:
                continue
            f = self.files[c.path]
            f.seek(c.source_start+lo-c.start)
            data = f.read(hi-lo, dtype='float64', always_2d=True)
            if len(data) != hi-lo:
                raise ProjectError(f'Audio truncado: {c.path.name}')
            if c.channel is not None:
                data = data[:, c.channel:c.channel+1]
            if c.channels == 1 and track.channels == 2:
                data = np.repeat(data, 2, axis=1)
            out[lo-start:hi-start] += data
        return out

    def mix(self, start: int, count: int, master: float = 1.0, center_mono=False):
        out = np.zeros((count, 2), dtype=np.float64)
        solo = any(t.solo for t in self.project.tracks)
        for t in self.project.tracks:
            block = self.track_block(t, start, count)
            t.peak = float(np.abs(block).max(initial=0))
            if t.mute or (solo and not t.solo):
                continue
            block *= t.gain
            if t.channels == 1:
                if t.output_channel is None or center_mono:
                    block = np.repeat(block, 2, axis=1)
                else:
                    routed = np.zeros((count, 2), dtype=np.float64)
                    routed[:, t.output_channel] = block[:, 0]
                    block = routed
            out += block
        return out*master


class ExportCancelled(Exception):
    pass


def export_stems(project: Project, parent: Path, fmt='WAV', progress=None, cancel=None, create_rpp=False, portable=False, naming='track'):
    """Export dry 24-bit stems atomically into a NEW directory. No source writes."""
    if fmt not in ('WAV', 'FLAC'):
        raise ValueError('Formato no compatible')
    if naming not in ('track', 'project_track'):
        raise ValueError('Nombre de archivo no compatible')
    if any(c.missing for t in project.tracks for c in t.clips):
        raise ProjectError('Faltan WAV. Localiza los archivos antes de exportar.')
    start, end = project.export_range or (0, project.length)
    validate_range(project, start, end)
    length = end-start
    parent = Path(parent).resolve()
    parent.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r'[^\w\-]+', '_', project.name)[:80] or 'Proyecto'
    target = parent / (safe + '_stems')
    index = 2
    while target.exists():
        target = parent / f'{safe}_stems_{index}'
        index += 1
    staging = Path(tempfile.mkdtemp(prefix='.h8-export-', dir=parent))
    renderer = None
    total = length*len(project.tracks)
    done, files = 0, []
    try:
        renderer = Renderer(project)
        for i, t in enumerate(project.tracks):
            label = re.sub(r'[^\w\-]+', '_', t.name)[:80] or 'Pista'
            filename = f'{i+1:02d}_{label}.{fmt.lower()}'
            if naming == 'project_track':
                filename = safe + '_' + filename
            container = 'RF64' if fmt == 'WAV' and length*t.channels*3+4096 >= 2**32 else fmt
            with sf.SoundFile(str(staging/filename), 'w', samplerate=project.rate,
                              channels=t.channels, subtype='PCM_24', format=container) as f:
                for pos in range(start, end, 65536):
                    if cancel and cancel.is_set():
                        raise ExportCancelled()
                    count = min(65536, end-pos)
                    block = renderer.track_block(t, pos, count)
                    if np.any(block > 1-2**-23) or np.any(block < -1):
                        raise ProjectError(f'La suma de clips de {t.name} satura. No se exportó audio recortado.')
                    f.write(block)
                    done += count
                    if progress:
                        progress(round(done/max(1,total)*100))
            files.append(filename)
        manifest = {'project': project.name, 'source': project.path.name if portable else str(project.path), 'sample_rate': project.rate,
                    'frames': length, 'source_range_samples': [start, end],
                    'favorite': project.favorite, 'notes': project.notes,
                    'format': fmt, 'bits': 24, 'alignment': project.alignment,
                    'processing': 'Dry stems; gain, mute, solo and monitor level ignored.',
                    'warnings': project.warnings, 'files': files}
        manifest['tracks'] = [{'name': t.name, 'file': filename,
                               'source': t.clips[0].path.name,
                               'source_channel': None if t.output_channel is None else ('L', 'R')[t.output_channel]}
                              for t, filename in zip(project.tracks, files)]
        (staging/'export.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')
        if create_rpp or portable:
            from .reaper import write_rpp
            write_rpp(staging/'Proyecto.rpp', project, files, length, fmt)
        if portable:
            (staging/'Notes.txt').write_text(project.name+'\n\n'+project.notes+'\n', encoding='utf-8')
            (staging/'README.txt').write_text(
                'H8 Studio — portable delivery\n\nOpen Proyecto.rpp in REAPER. Keep all files together.\n'
                'Alternatively, import the audio files on separate tracks at 00:00.\n'
                'Stems are dry 24-bit audio; monitor gain, mute, solo and centering were not applied.\n'
                'The export range starts at zero. Notes are in Notes.txt; details are in export.json.\n', encoding='utf-8')
            import hashlib
            checksums = []
            for asset in sorted(staging.iterdir()):
                digest = hashlib.sha256()
                with asset.open('rb') as stream:
                    for chunk in iter(lambda: stream.read(1024*1024), b''):
                        if cancel and cancel.is_set():
                            raise ExportCancelled()
                        digest.update(chunk)
                checksums.append(f'{digest.hexdigest()}  {asset.name}')
            (staging/'SHA256SUMS.txt').write_text('\n'.join(checksums)+'\n', encoding='utf-8')
        if cancel and cancel.is_set():
            raise ExportCancelled()
        staging.rename(target)
        return target
    finally:
        if renderer:
            renderer.close()
        if staging.exists() and staging.resolve().parent == parent:
            shutil.rmtree(staging)


def waveform(clip: Clip, bins=1600):
    if clip.missing or not clip.frames:
        return np.zeros((0, 2))
    # Scan in bounded chunks; min/max includes every sample, even on long takes.
    step = max(1, (clip.frames+bins-1)//bins)
    peaks = []
    with sf.SoundFile(str(clip.path)) as f:
        f.seek(clip.source_start)
        remaining = clip.frames
        while remaining:
            count = min(step*128, remaining)
            data = f.read(count, dtype='float32', always_2d=True)
            if clip.channel is not None:
                data = data[:, clip.channel:clip.channel+1]
            if not len(data):
                break
            for j in range(0, len(data), step):
                chunk = data[j:j+step]
                peaks.append((float(chunk.min()), float(chunk.max())))
            remaining -= len(data)
    return np.array(peaks)
