"""Run with QT_QPA_PLATFORM=offscreen to validate the actual Qt widgets."""
from pathlib import Path
import sys
import time
import tempfile
import shutil
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from PySide6.QtWidgets import QApplication
from PySide6.QtWidgets import QToolButton
from PySide6.QtCore import Qt
from PySide6.QtCore import QPoint
from PySide6.QtTest import QTest
from unittest.mock import patch
from h8studio.ui import Window, STYLE
from h8studio.core import read_project, waveform
from h8studio.core import save_preparation
from h8studio.preferences import Preferences
from h8studio.dialogs import ExportOptionsDialog, LocateDialog, LoopDialog, AboutDialog

app = QApplication([])
app.setStyle('Fusion')
app.setStyleSheet(STYLE)
window = Window(state_path=False)
temporary = tempfile.TemporaryDirectory()
from tools.synthetic_project import make_project
source = Path('Projects/F260830_006.zprj')
if source.exists():
    project = read_project(source)
else:
    source = make_project(Path(temporary.name)/'synthetic')
    window.scan(source.parent)
    project = read_project(source)
window.loaded((project, {str(c.path): waveform(c) for t in project.tracks for c in t.clips}))
window.set_busy(False)
window.show()
for _ in range(10):
    app.processEvents()
    time.sleep(.03)
assert window.library.count() >= 1
assert window.export_button.isEnabled()
window.seek(44100)
window.tick()
assert '00:00:01.000' in window.time_label.text()
window.timeline.controls[0].setChecked(True)
assert project.tracks[0].mute
window.timeline.controls[0].setChecked(False)
window.zoom.setValue(2)
app.processEvents()
window.zoom.setValue(1)
window.stop()
app.processEvents()
# Use only disposable synthetic projects for checks that save channel preferences.
source = make_project(Path(temporary.name)/'channels')
window.scan(source.parent)
project = read_project(source)
window.loaded((project, window.project_peaks(project)))
window.set_busy(False)

def wait_job():
    deadline = time.monotonic()+20
    while window.job and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(.01)
    assert window.job is None, 'Channel job timed out'
    app.processEvents()

window.seek(12345)
next(w for w in window.timeline.controls if getattr(w, 'text', lambda: '')() == '2 mono').click()
wait_job()
assert len(window.project.tracks) == 3
assert window.player.position == 12345
assert len(read_project(source).tracks) == 3
window.timeline.controls[0].setChecked(True)
assert window.project.tracks[0].mute and not window.project.tracks[1].mute
Path('test-output').mkdir(exist_ok=True)
assert window.grab().save('test-output/channels-mono.png')
next(w for w in window.timeline.controls if getattr(w, 'text', lambda: '')() == 'Stereo').click()
wait_job()
assert len(window.project.tracks) == 2
assert window.player.position == 12345
window.library.item(0).setCheckState(Qt.Checked)
window.channel_mode.setCurrentIndex(2)
with patch('h8studio.ui.show_report') as report:
    window.channels_batch_button.click()
    wait_job()
    assert report.called
assert len(read_project(source).tracks) == 3
window.channel_mode.setCurrentIndex(1)
window.load(source)
wait_job()
assert len(window.project.tracks) == 2
assert len(read_project(source).tracks) == 2
# Loop is available without trimming exports. A-B edits only the loop range.
assert window.project.export_range is None
assert window.loop_button.isEnabled() and window.loop_range_button.isEnabled()
def choose_loop(dialog):
    dialog.trim.setChecked(True)
    dialog.start.setValue(.1)
    dialog.end.setValue(.3)
    dialog.save()
    return dialog.result()
with patch.object(LoopDialog, 'exec', choose_loop):
    window.loop_range_button.click()
assert window.player.loop and window.project.loop_range == (4410, 13230)
assert read_project(source).loop_range == (4410, 13230)
assert window.project.export_range is None
loop_editor = LoopDialog(window.project, 8820, window)
loop_editor.show()
app.processEvents()
assert loop_editor.grab().save('test-output/loop-range.png')
loop_editor.close()
# Space and Home must keep their text-editing meanings.
window.search.setFocus()
app.processEvents()
with patch.object(window.player, 'play') as play:
    QTest.keyClicks(window.search, 'two words')
    QTest.keyClick(window.search, Qt.Key_Home)
    assert window.search.text() == 'two words' and window.search.cursorPosition() == 0
    play.assert_not_called()
window.search.clear()
save_preparation(window.project, True, 'Acoustic guitar session', (100, 44100))
window.refresh_preparation()
window.search.setText('GUITAR')
assert not window.library.item(0).isHidden()
window.library_filter.setCurrentIndex(1)
assert not window.library.item(0).isHidden()
window.search.setText('not found')
assert window.library.item(0).isHidden()
assert not window.checked_paths()
window.search.clear()
window.library_filter.setCurrentIndex(0)
window.center_mono.setChecked(True)
window.loop_button.setChecked(True)
assert window.player.center_mono and window.player.loop
window.preferences = Preferences(Path(temporary.name)/'app-settings.json')
dialog = ExportOptionsDialog(window.preferences, window.current_export_options(), window)
dialog.names.setEditText('Portable FLAC')
dialog.format.setCurrentText('FLAC')
dialog.portable.setChecked(True)
dialog.naming.setCurrentIndex(1)
dialog.save_preset()
window.apply_export_options(dialog.options())
assert window.preferences.presets()['Portable FLAC']['portable']
window.seek(12345)
window.zoom.setValue(2)
renderer = window.player.renderer
window.view_mode.setCurrentIndex(1)
app.processEvents()
assert window.views.currentWidget() is window.console_scroll
assert window.zoom.isEnabled()
assert window.player.renderer is renderer and window.player.position == 12345
mute, solo, fader, value, _, _ = window.console.strips[0]
assert fader.orientation() == Qt.Vertical
fader.setValue(-120)
mute.setChecked(True)
assert abs(window.project.tracks[0].gain-10**(-.6)) < 1e-10
assert window.project.tracks[0].mute
QTest.mouseClick(window.console, Qt.LeftButton, pos=QPoint(120, 150))
assert window.player.position == window.console.sample_at(QPoint(120, 150))
position = window.player.position
window.view_mode.setCurrentIndex(0)
assert window.timeline.controls[0].isChecked()
assert window.timeline.controls[2].value() == -120
assert window.player.position == position and window.player.renderer is renderer
window.timeline.controls[0].setChecked(False)
window.view_mode.setCurrentIndex(1)
assert not window.console.strips[0][0].isChecked()
assert window.console.strips[0][2].value() == -120
window.seek(12345)
app.processEvents()
window.tick()
assert window.grab().save('test-output/console.png')
window.view_mode.setCurrentIndex(2)
app.processEvents()
assert window.views.currentWidget() is window.vertical_scroll
assert window.player.renderer is renderer
vertical = window.vertical_console
rect = vertical.wave_rect(0)
positions = []
for fraction in (.1, .8):
    point = QPoint(int(rect.center().x()), round(rect.top()+rect.height()*fraction))
    QTest.mouseClick(vertical, Qt.LeftButton, pos=point)
    expected = vertical.sample_at(point)
    assert window.player.position == expected
    positions.append(window.player.position)
assert positions[1] > positions[0]
position = window.player.position
QTest.mouseClick(vertical, Qt.LeftButton, pos=QPoint(235, 120))
assert window.player.position == position  # outside the waveform
vertical.strips[0][2].setValue(-80)
window.view_mode.setCurrentIndex(0)
assert window.timeline.controls[2].value() == -80
window.view_mode.setCurrentIndex(2)
assert window.vertical_console.strips[0][2].value() == -80
window.library_toggle.setChecked(False)
app.processEvents()
assert window.views.height() > window.height()*.6
window.seek(12345)
window.tick()
assert window.grab().save('test-output/vertical-console.png')
# Check the compact popups expose their original controls.
for text, widgets in [('Project', (window.rename_button, window.prepare_button, window.locate_button)),
                      ('Export', (window.format, window.rpp, window.options_button)),
                      ('Open / batch channels', (window.channel_mode, window.channels_batch_button))]:
    if text.startswith('Canales'):
        window.library_toggle.setChecked(True)
    button = next(b for b in window.findChildren(QToolButton) if b.text() == text)
    button.menu().popup(button.mapToGlobal(QPoint(0, button.height())))
    app.processEvents()
    assert all(w.isVisible() for w in widgets)
    button.menu().close()
window.library_toggle.setChecked(False)
window.resize(1000, 620)
app.processEvents()
assert window.width() <= 1000
assert window.views.height() > window.height()*.6
assert window.vertical_console.wave_rect(0).height() > 180
window.resize(1320, 800)
window.close()
window = Window(state_path=Path(temporary.name)/'app-settings.json')
window.show()
deadline = time.monotonic()+20
while (window.project is None or window.job) and time.monotonic() < deadline:
    app.processEvents()
    time.sleep(.01)
assert window.project and window.player.position == 12345
assert window.zoom.value() == 2
assert window.view_mode.currentIndex() == 2
assert not window.library_toggle.isChecked()
assert window.center_mono.isChecked() and not window.player.playing
assert window.format.currentIndex() == 1 and window.portable_delivery
assert window.preferences.presets()['Portable FLAC']['format'] == 'FLAC'

# Exercise the full missing-media UI flow with an explicitly selected candidate.
window.player.close()
recovered = Path(temporary.name)/'recovered'
recovered.mkdir()
shutil.move(str(source.parent/'Mic12.WAV'), recovered/'Mic12.WAV')
window.load(source, use_saved_channels=True)
wait_job()
assert window.locate_button.isEnabled()
def choose_candidate(dialog):
    dialog.choices['mic12.wav'].setCurrentIndex(1)
    return 1
with patch('h8studio.ui.QFileDialog.getExistingDirectory', return_value=str(recovered)), \
     patch.object(LocateDialog, 'exec', choose_candidate):
    window.locate_button.click()
    deadline = time.monotonic()+20
    while (window.job or window.after_job or window.project.tracks[0].clips[0].missing) and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(.01)
assert not window.job and not window.project.tracks[0].clips[0].missing
assert not window.locate_button.isEnabled()
window.view_mode.setCurrentIndex(1)
window.console.strips[0][5].click()
wait_job()
assert len(window.console.strips) == 3 and window.view_mode.currentIndex() == 1
window.console.strips[0][5].click()
wait_job()
assert len(window.console.strips) == 2 and window.view_mode.currentIndex() == 1
window.view_mode.setCurrentIndex(2)
window.vertical_console.strips[0][5].click()
wait_job()
assert len(window.vertical_console.strips) == 3 and window.view_mode.currentIndex() == 2
# Zoom and loop gestures use the same sample coordinates in all views.
from h8studio.core import save_loop_range
export_range = window.project.export_range
for factor in (.1, 50, 2.75):
    window.zoom.setValue(factor)
    assert window.zoom.value() == factor
    assert all(view.zoom_factor == factor for view in (window.timeline, window.console, window.vertical_console))
window.time_scroll.setValue(370000)
for index, view in enumerate((window.timeline, window.console, window.vertical_console)):
    window.view_mode.setCurrentIndex(index)
    app.processEvents()
    if index == 0:
        point = lambda f: QPoint(round(view.LEFT+f*(view.width()-view.LEFT-28)), 25)
    elif index == 1:
        point = lambda f: QPoint(round(14+f*(view.COLUMN-28)), 140)
    else:
        rect = view.wave_rect(0)
        point = lambda f: QPoint(round(rect.center().x()), round(rect.top()+f*rect.height()))
    save_loop_range(window.project, None)
    first, last = point(.2), point(.7)
    expected = tuple(sorted((view.sample_at(first), view.sample_at(last))))
    QTest.mousePress(view, Qt.LeftButton, pos=last)
    QTest.mouseMove(view, first, delay=20)
    QTest.mouseRelease(view, Qt.LeftButton, pos=first)
    assert window.project.loop_range == expected, (index, window.project.loop_range, expected)
    assert window.player.loop and read_project(source).loop_range == expected
    # Resize one amber boundary, keeping the other endpoint fixed.
    target = point(.35)
    QTest.mousePress(view, Qt.LeftButton, pos=first)
    QTest.mouseMove(view, target, delay=20)
    QTest.mouseRelease(view, Qt.LeftButton, pos=target)
    assert window.project.loop_range == (view.sample_at(target), expected[1])
    previous = window.project.loop_range
    QTest.mousePress(view, Qt.LeftButton, pos=point(.45))
    QTest.mouseMove(view, point(.6), delay=20)
    QTest.keyClick(view, Qt.Key_Escape)
    QTest.mouseRelease(view, Qt.LeftButton, pos=point(.6))
    assert window.project.loop_range == previous
    assert window.project.export_range == export_range
window.zoom.setFocus()
window.zoom.selectAll()
QTest.keyClicks(window.zoom, window.zoom.locale().toString(3.25, 'f', 2))
QTest.keyClick(window.zoom, Qt.Key_Return)
assert window.zoom.value() == 3.25
window.zoom_dial.setValue(1000)
assert window.zoom.value() == 50
window.zoom_dial.setValue(0)
assert window.zoom.value() == .1
window.library_toggle.setChecked(True)
window.zoom.setValue(1)
window.loop_button.setChecked(True)
window.timeline.meter_values = [.2, .08]
window.console.meter_values = [.2, .08]
app.processEvents()
Path('test-output').mkdir(exist_ok=True)
assert window.grab().save('test-output/app.png')
window.close()
# About shows runtime dependencies and saves language for the next launch.
assert window.about_button.text() == 'About…'
about = AboutDialog(window.preferences)
about.show()
app.processEvents()
from PySide6.QtWidgets import QPlainTextEdit, QDialogButtonBox
assert all(name in about.findChild(QPlainTextEdit).toPlainText() for name in ('PySide6', 'NumPy', 'SoundFile', 'PortAudio', 'Python'))
assert about.grab().save('test-output/about-en.png')
about.languages.setCurrentIndex(1)
about.save()
assert Preferences(window.preferences.path).data['language'] == 'es'
# Clear session so this language check does not asynchronously reopen audio.
window.preferences.data['session'] = {}
window.preferences.save()
spanish = Window(state_path=window.preferences.path)
assert spanish.about_button.text() == 'Acerca de…'
assert spanish.play_button.text() == '▶  Reproducir'
spanish_about = AboutDialog(spanish.preferences, spanish)
assert spanish_about.windowTitle() == 'Acerca de H8 Studio'
assert spanish_about.findChild(QDialogButtonBox).button(QDialogButtonBox.Save).text() == 'Guardar'
spanish_about.show()
app.processEvents()
assert spanish_about.grab().save('test-output/about-es.png')
spanish_about.reject()
spanish.close()
from h8studio.i18n import set_language
set_language('en')
temporary.cleanup()
print('UI passed: three synced views, vertical seeking/faders, compact layout, library visibility, stereo/mono, presets, session restore, relinking, screenshots.')
