"""Packaged-runtime smoke test; invoked explicitly with --verify PROJECT REPORT."""
def verify(project_path, report_path, audio=True):
    from pathlib import Path
    import json
    import tempfile
    import time
    import traceback
    report_path = Path(report_path).resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        import numpy as np
        import soundfile as sf
        from PySide6.QtWidgets import QApplication
        from .core import read_project, waveform, export_stems
        from .ui import Window, STYLE
        app = QApplication([])
        app.setStyle('Fusion')
        app.setStyleSheet(STYLE)
        project = read_project(project_path)
        window = Window()
        window.loaded((project, {str(c.path): waveform(c) for t in project.tracks for c in t.clips}))
        window.set_busy(False)
        window.resize(1320, 800)
        app.processEvents()
        assert window.export_button.isEnabled()
        if audio:
            window.player.master = 0
            window.player.play()
            time.sleep(.35)
            window.player.pause()
            assert window.player.position > 0 and not window.player.error
            window.player.seek(44100)
            window.player.play()
            time.sleep(.2)
            window.player.pause()
            assert window.player.position > 44100 and not window.player.error
        with tempfile.TemporaryDirectory(dir=report_path.parent) as directory:
            for fmt in ('WAV', 'FLAC'):
                output = export_stems(project, Path(directory), fmt, create_rpp=True)
                assert (output/'Proyecto.rpp').exists()
                for i, t in enumerate(project.tracks):
                    source, _ = sf.read(str(t.clips[0].path), dtype='int32', always_2d=True)
                    target, _ = sf.read(str(next(output.glob(f'{i+1:02d}_*.{fmt.lower()}'))), dtype='int32', always_2d=True)
                    a, b = project.export_range or (0, project.length)
                    assert np.array_equal(source[a:b], target)
        window.close()
        report = {'ok': True, 'project': project.name, 'checks': [
            'packaged imports and DLLs', 'Qt window and waveform', 'WAV and FLAC lossless roundtrip',
            'silent playback, pause and seek' if audio else 'audio device test SKIPPED', 'clean shutdown']}
        report_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
        return 0
    except Exception:
        report_path.write_text(json.dumps({'ok': False, 'error': traceback.format_exc()}, indent=2), encoding='utf-8')
        return 1
