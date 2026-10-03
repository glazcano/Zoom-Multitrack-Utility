"""Run with QT_QPA_PLATFORM=offscreen to validate the actual Qt widgets."""
from pathlib import Path
import sys
import time
import tempfile
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from PySide6.QtWidgets import QApplication
from h8studio.ui import Window, STYLE
from h8studio.core import read_project, waveform

app = QApplication([])
app.setStyle('Fusion')
app.setStyleSheet(STYLE)
window = Window()
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
Path('test-output').mkdir(exist_ok=True)
assert window.grab().save('test-output/app.png')
window.close()
temporary.cleanup()
print('UI passed: library, waveform, seek, mute, zoom, export enablement, screenshot, clean shutdown.')
