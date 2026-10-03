from pathlib import Path
import json
import math
import os
import tempfile
import numpy as np
from .core import (ProjectError, title_settings, save_settings, validate_title,
                   read_project, Renderer, export_stems, ExportCancelled, track_key, set_stereo_split)


def atomic_json(path, data):
    path = Path(path)
    temp = None
    try:
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent, delete=False) as f:
            temp = Path(f.name)
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp, path)
    finally:
        if temp and temp.exists():
            temp.unlink()


def read_templates(path):
    if not Path(path).exists():
        return {}
    try:
        data = json.loads(Path(path).read_text(encoding='utf-8'))
        if not isinstance(data, dict):
            raise ValueError('Formato inválido')
        for name, mapping in data.items():
            validate_title(name)
            if not isinstance(mapping, dict):
                raise ValueError('Asignaciones inválidas')
            for key, value in mapping.items():
                validate_title(key)
                validate_title(value)
        return data
    except (ValueError, OSError) as exc:
        raise ProjectError(f'No se pueden leer las plantillas: {exc}') from exc


def apply_template(project, mapping):
    data = title_settings(project.path)
    labels = data.setdefault('tracks', {})
    updates = []
    mapping = {k.casefold(): validate_title(v) for k, v in mapping.items()}
    for track in project.tracks:
        key = track.clips[0].path.stem.casefold()
        if track.output_channel is not None:
            key += '.l' if track.output_channel == 0 else '.r'
        if key in mapping:
            updates.append((track, mapping[key]))
            labels[track_key(track)] = mapping[key]
    if not updates:
        raise ProjectError('La plantilla no coincide con las entradas de este proyecto.')
    save_settings(project, data)
    for track, label in updates:
        track.name = label
    return len(updates)


def analyze_project(project, cancel=None, progress=None):
    rows = []
    renderer = Renderer(project)
    try:
        for index, track in enumerate(project.tracks):
            missing = [c.path.name for c in track.clips if c.missing]
            if missing:
                rows.append(f'{track.name}: FALTA AUDIO: {", ".join(missing)}')
                continue
            peak, energy, count, near_full = 0., 0., 0, 0
            for start in range(0, project.length, 65536):
                if cancel and cancel.is_set():
                    raise ExportCancelled()
                block = renderer.track_block(track, start, min(65536, project.length-start))
                peak = max(peak, float(np.abs(block).max(initial=0)))
                energy += float(np.square(block).sum())
                count += block.size
                near_full += int(np.count_nonzero(np.abs(block) >= 10**(-.1/20)))
                if progress:
                    progress(int(100*(index+(start+len(block))/max(1,project.length))/len(project.tracks)))
            db = 20*math.log10(peak) if peak else None
            rms = 10*math.log10(energy/count) if energy and count else None
            flags = []
            if peak == 0:
                flags.append('silencio digital')
            elif rms is not None and rms < -60:
                flags.append('nivel medio muy bajo (< −60 dBFS)')
            if near_full:
                flags.append(f'posible saturación: {near_full} muestras ≥ −0,1 dBFS')
            level = f'{db:.1f} dBFS' if db is not None else '−∞ dBFS'
            rows.append(f'{track.name}: pico {level}; ' + ('; '.join(flags) or 'sin alertas de nivel'))
    finally:
        renderer.close()
    return rows + ['\nObservaciones de importación:'] + project.warnings


def export_batch(paths, parent, fmt='WAV', create_rpp=True, progress=None, cancel=None, split_stereo=None, portable=False, naming='track'):
    paths = list(dict.fromkeys(str(Path(p).resolve()) for p in paths))
    if not paths:
        raise ProjectError('Marca al menos un proyecto para exportar.')
    parent = Path(parent).resolve()
    parent.mkdir(parents=True, exist_ok=True)
    report_path = Path(tempfile.mkdtemp(prefix='Lote_', dir=parent))
    result = {'completed': [], 'failed': [], 'cancelled': False, 'pending': paths[:], 'folder': str(report_path)}
    for index, path in enumerate(paths):
        if cancel and cancel.is_set():
            result['cancelled'] = True
            break
        try:
            project = read_project(path)
            if split_stereo is not None:
                set_stereo_split(project, split_stereo, persist=False)
            def update(percent):
                if progress:
                    progress(int((index+percent/100)*100/len(paths)))
            output = export_stems(project, report_path, fmt, update, cancel, create_rpp=create_rpp, portable=portable, naming=naming)
            result['completed'].append({'source': path, 'output': str(output)})
        except ExportCancelled:
            result['cancelled'] = True
            break
        except Exception as exc:
            result['failed'].append({'source': path, 'error': str(exc)})
        result['pending'].remove(path)
        atomic_json(report_path/'lote.json', result)
    atomic_json(report_path/'lote.json', result)
    return result
