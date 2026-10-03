"""Find compatible missing media; associations require an explicit selection."""
from pathlib import Path
import os
import soundfile as sf
from .core import ProjectError, ExportCancelled, read_project, title_settings, save_settings, bwf_reference


def missing_sources(project):
    return {c.path.name.casefold(): c for t in (project.source_tracks or project.tracks)
            for c in t.clips if c.missing}


def compatible(project, clip, path):
    path = Path(path)
    if path.name.casefold() != clip.path.name.casefold() or path.name.startswith('._'):
        return False
    info = sf.info(str(path))
    return (info.samplerate == project.rate and info.channels == clip.channels
            and info.frames == clip.frames)


def find_candidates(project, folder, cancel=None):
    missing = missing_sources(project)
    results = {key: [] for key in missing}
    for root, directories, files in os.walk(folder):
        directories.sort()
        for name in sorted(files):
            if cancel and cancel.is_set():
                raise ExportCancelled()
            key = name.casefold()
            if key not in missing or name.startswith('._'):
                continue
            path = (Path(root)/name).resolve()
            try:
                if compatible(project, missing[key], path):
                    stamp = bwf_reference(path)
                    results[key].append(dict(path=str(path), bwf=str(stamp) if stamp else 'Sin BWF'))
            except (RuntimeError, OSError, ValueError):
                continue
    return results


def link_media(project, selections):
    missing = missing_sources(project)
    data = title_settings(project.path)
    links = dict(data.get('audio_links', {}))
    for key, value in selections.items():
        path = Path(value).resolve()
        if key not in missing or not compatible(project, missing[key], path):
            raise ProjectError(f'{path.name}: el WAV ya no coincide en nombre, duración, canales o frecuencia.')
        try:
            links[key] = str(path.relative_to(project.path.parent))
        except ValueError:
            links[key] = str(path)
    # Validate alignment and the saved range before committing any association.
    reopened = read_project(project.path, audio_links=links)
    data['audio_links'] = links
    save_settings(project, data)
    return reopened
