"""Portable REAPER projects referencing consolidated stems in the same directory."""
import uuid


def quoted(value):
    # REAPER accepts double, single or backtick delimiters (WDL LineParser).
    value = str(value).replace('\r', ' ').replace('\n', ' ')
    for delimiter in ('"', "'", '`'):
        if delimiter not in value:
            return delimiter + value + delimiter
    return '"' + value.replace('"', '＂') + '"'


def write_rpp(path, project, files, frames, fmt):
    rows = ['<REAPER_PROJECT 0.1 "7.0" 0', f'  SAMPLERATE {project.rate} 1 0',
            '  TEMPO 120', '  MASTER_VOLUME 1', '  TIMELOCKMODE 1']
    for track, filename in zip(project.tracks, files):
        rows += [f'  <TRACK {{{str(uuid.uuid4()).upper()}}}', f'    NAME {quoted(track.name)}',
                 '    VOLPAN 1 0', '    MUTESOLO 0 0 0', '    <ITEM', '      POSITION 0',
                 f'      LENGTH {frames/project.rate:.12f}', '      SOFFS 0', '      LOOP 0',
                 '      VOLPAN 1 0 1 -1', '      FADEIN 1 0 0', '      FADEOUT 1 0 0',
                 f'      NAME {quoted(track.name)}', f'      <SOURCE {"FLAC" if fmt == "FLAC" else "WAVE"}',
                 f'        FILE {quoted(filename)}', '      >', '    >', '  >']
    rows.append('>')
    path.write_text('\n'.join(rows)+'\n', encoding='utf-8')
