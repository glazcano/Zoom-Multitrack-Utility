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
from h8studio.dialogs import ExportOptionsDialog, LocateDialog

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
window.zoom.setCurrentIndex(1)
app.processEvents()
window.zoom.setCurrentIndex(0)
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
next(w for w in window.timeline.controls if getattr(w, 'text', lambda: '')() == 'Estéreo').click()
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
window.zoom.setCurrentIndex(1)
renderer = window.player.renderer
window.view_mode.setCurrentIndex(1)
app.processEvents()
assert window.views.currentWidget() is window.console_scroll
assert not window.zoom.isEnabled()
assert window.player.renderer is renderer and window.player.position == 12345
mute, solo, fader, value, _, _ = window.console.strips[0]
assert fader.orientation() == Qt.Vertical
fader.setValue(-120)
mute.setChecked(True)
assert abs(window.project.tracks[0].gain-10**(-.6)) < 1e-10
assert window.project.tracks[0].mute
QTest.mouseClick(window.console, Qt.LeftButton, pos=QPoint(120, 150))
assert abs(window.player.position-window.project.length//2) <= 1
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
    expected = round((point.y()-rect.top())/rect.height()*window.project.length)
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
for text, widgets in [('Proyecto', (window.rename_button, window.prepare_button, window.locate_button)),
                      ('Exportación', (window.format, window.rpp, window.options_button)),
                      ('Canales al abrir / lote', (window.channel_mode, window.channels_batch_button))]:
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
assert window.zoom.currentIndex() == 1
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
window.library_toggle.setChecked(True)
window.zoom.setCurrentIndex(0)
window.loop_button.setChecked(True)
window.timeline.meter_values = [.2, .08]
window.console.meter_values = [.2, .08]
app.processEvents()
Path('test-output').mkdir(exist_ok=True)
assert window.grab().save('test-output/app.png')
window.close()
temporary.cleanup()
print('UI passed: three synced views, vertical seeking/faders, compact layout, library visibility, stereo/mono, presets, session restore, relinking, screenshots.')
