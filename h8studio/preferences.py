"""Application preferences, kept separately from recorder projects."""
from .i18n import tr
import json
from pathlib import Path
from .core import ProjectError, validate_title
from .workflows import atomic_json


DEFAULT_EXPORT = dict(format='WAV', channels=0, rpp=True, portable=False, naming='track')


def export_options(value):
    if not isinstance(value, dict):
        raise ProjectError(tr('Preset inválido.'))
    options = DEFAULT_EXPORT | value
    if (options['format'] not in ('WAV', 'FLAC') or type(options['channels']) is not int
            or options['channels'] not in (0, 1, 2)
            or type(options['rpp']) is not bool or type(options['portable']) is not bool
            or options['naming'] not in ('track', 'project_track')):
        raise ProjectError(tr('Opciones de exportación inválidas.'))
    return {key: options[key] for key in DEFAULT_EXPORT}


class Preferences:
    def __init__(self, path):
        self.path = Path(path) if path else None
        self.data = {}
        self.error = ''
        if self.path and self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding='utf-8'))
                if not isinstance(data, dict):
                    raise ValueError(tr('Se esperaba un objeto JSON'))
                self.data = data
            except (ValueError, OSError) as exc:
                self.error = tr('No se pudieron recuperar las preferencias: {0}', exc)

    def save(self):
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            atomic_json(self.path, self.data)

    def presets(self):
        valid = {}
        data = self.data.get('presets', {})
        if isinstance(data, dict):
            for name, options in data.items():
                try:
                    valid[validate_title(name)] = export_options(options)
                except ProjectError:
                    continue
        return valid

    def put_preset(self, name, options):
        presets = self.presets()
        presets[validate_title(name)] = export_options(options)
        self.data['presets'] = presets
        self.save()

    def delete_preset(self, name):
        presets = self.presets()
        presets.pop(name, None)
        self.data['presets'] = presets
        self.save()


def library_entry(path):
    from .core import read_project, title_settings
    path = Path(path)
    entry = dict(path=str(path), name=path.stem, notes='', favorite=False, problem=False, detail='')
    try:
        settings = title_settings(path)
        entry.update(name=settings.get('title', path.stem), notes=str(settings.get('notes', '')),
                     favorite=bool(settings.get('favorite', False)))
        project = read_project(path)
        missing = sorted({c.path.name for t in project.tracks for c in t.clips if c.missing})
        entry['problem'] = bool(missing)
        entry['detail'] = tr('Falta: ')+', '.join(missing) if missing else ''
    except (OSError, ValueError, RuntimeError) as exc:
        entry.update(problem=True, detail=str(exc))
    return entry


def matches_entry(entry, query='', mode=0):
    text = ' '.join(str(entry.get(k, '')) for k in ('name', 'notes', 'path')).casefold()
    return (all(word in text for word in query.casefold().split())
            and (mode != 1 or entry.get('favorite', False))
            and (mode != 2 or entry.get('problem', False)))
