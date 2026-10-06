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
        from .core import read_project, export_stems
        from .ui import Window, STYLE
        from .dialogs import AboutDialog, ExportDialog
        app = QApplication([])
        app.setStyle('Fusion')
        app.setStyleSheet(STYLE)
        project = read_project(project_path)
        window = Window(state_path=False)
        window.loaded((project, window.project_peaks(project)))
        window.set_busy(False)
        window.resize(1320, 800)
        app.processEvents()
        assert window.export_button.isEnabled()
        about = AboutDialog(window.preferences, window)
        assert about.windowTitle() == 'About H8 Studio'
        about.close()
        dialog = ExportDialog(window.preferences, window.current_export_options(), report_path.parent, window)
        dialog.format.setCurrentText('FLAC')
        assert dialog.options()['format'] == 'FLAC'
        dialog.close()
        window.view_mode.setCurrentIndex(2)
        for strip in window.vertical_console.strips:
            assert not strip[0].icon().isNull()
            strip[2].set_peak(.5)
        assert not window.vertical_console.grab().isNull()
        assert window.loop_button.isEnabled() and window.loop_range_button.isEnabled()
        project.loop_range = (15, 22)
        window.player.loop = True
        window.player.callback(np.zeros((2048, 2), dtype=np.float32), 2048, None, False)
        assert 15 <= window.player.position < 22 and not window.player.error
        project.loop_range = None
        window.player.loop = False
        window.player.position = 0
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
                    if t.output_channel is not None:
                        source = source[:, t.output_channel:t.output_channel+1]
                    target, _ = sf.read(str(next(output.glob(f'{i+1:02d}_*.{fmt.lower()}'))), dtype='int32', always_2d=True)
                    a, b = project.export_range or (0, project.length)
                    assert np.array_equal(source[a:b], target)
        window.close()
        report = {'ok': True, 'project': project.name, 'checks': [
            'packaged imports and DLLs', 'Qt window, waveform and About dependencies', 'export dialog, icons and combined meter/faders', 'short loop callback', 'WAV and FLAC lossless roundtrip',
            'silent playback, pause and seek' if audio else 'audio device test SKIPPED', 'clean shutdown']}
        report_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
        return 0
    except Exception:
        report_path.write_text(json.dumps({'ok': False, 'error': traceback.format_exc()}, indent=2), encoding='utf-8')
        return 1
