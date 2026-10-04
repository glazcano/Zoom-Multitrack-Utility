from .i18n import tr
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox,
    QPlainTextEdit, QDoubleSpinBox, QPushButton, QDialogButtonBox, QMessageBox,
    QComboBox, QTableWidget, QTableWidgetItem, QHeaderView)
from .core import save_preparation, save_loop_range, validate_title, ProjectError
from .workflows import read_templates, atomic_json, apply_template
from .preferences import export_options


class LocalizedButtonBox(QDialogButtonBox):
    def __init__(self, buttons, parent=None):
        super().__init__(buttons, parent)
        for standard, label in ((QDialogButtonBox.Save, 'Guardar'), (QDialogButtonBox.Cancel, 'Cancelar'),
                                (QDialogButtonBox.Ok, 'Aceptar'), (QDialogButtonBox.Close, 'Cerrar')):
            button = self.button(standard)
            if button:
                button.setText(tr(label))


class PreparationDialog(QDialog):
    def __init__(self, project, cursor, parent=None):
        super().__init__(parent)
        self.project = project
        self.setWindowTitle(tr('Preparar toma'))
        self.resize(560, 460)
        layout = QVBoxLayout(self)
        self.favorite = QCheckBox(tr('★ Toma favorita'))
        self.favorite.setChecked(project.favorite)
        layout.addWidget(self.favorite)
        layout.addWidget(QLabel(tr('Notas de la toma')))
        self.notes = QPlainTextEdit(project.notes)
        self.notes.setPlaceholderText(tr('Toma buena, instrumentos, ruido al final…'))
        layout.addWidget(self.notes)
        self.trim = QCheckBox(tr('Exportar solamente este tramo'))
        self.trim.setChecked(project.export_range is not None)
        layout.addWidget(self.trim)
        row = QHBoxLayout()
        self.start, self.end = QDoubleSpinBox(), QDoubleSpinBox()
        for widget in (self.start, self.end):
            widget.setDecimals(6)
            widget.setRange(0, project.length/project.rate)
            widget.setSuffix(' s')
        a, b = project.export_range or (0, project.length)
        self.start.setValue(a/project.rate)
        self.end.setValue(b/project.rate)
        row.addWidget(QLabel(tr('Inicio')))
        row.addWidget(self.start)
        row.addWidget(QLabel(tr('Fin')))
        row.addWidget(self.end)
        layout.addLayout(row)
        markers = QHBoxLayout()
        for label, widget in [(tr('Inicio = cursor'), self.start), (tr('Fin = cursor'), self.end)]:
            button = QPushButton(label)
            button.clicked.connect(lambda checked=False, target=widget: (self.trim.setChecked(True), target.setValue(cursor/project.rate)))
            markers.addWidget(button)
        layout.addLayout(markers)
        hint = QLabel(tr('El mismo tramo se aplica a todas las pistas. Los stems y el .rpp comienzan en cero; el original queda intacto.'))
        hint.setWordWrap(True)
        layout.addWidget(hint)
        buttons = LocalizedButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def save(self):
        region = (round(self.start.value()*self.project.rate), round(self.end.value()*self.project.rate)) if self.trim.isChecked() else None
        try:
            save_preparation(self.project, self.favorite.isChecked(), self.notes.toPlainText(), region)
        except (OSError, ProjectError) as exc:
            QMessageBox.warning(self, tr('No se guardó la toma'), str(exc))
            return
        self.accept()


class LoopDialog(PreparationDialog):
    """Reuse sample-accurate range controls, without altering export preparation."""
    def __init__(self, project, cursor, parent=None):
        super().__init__(project, cursor, parent)
        self.setWindowTitle(tr('Tramo del bucle'))
        self.favorite.hide()
        self.notes.hide()
        for label in self.findChildren(QLabel):
            if label.text() == tr('Notas de la toma'):
                label.hide()
            if label.wordWrap():
                label.setText(tr('Sin tramo personalizado se repite toda la toma. El bucle no cambia el tramo de exportación. Ámbar: bucle; verde: exportación.'))
        self.trim.setText(tr('Repetir este tramo'))
        self.trim.setChecked(project.loop_range is not None)
        a, b = project.loop_range or (0, project.length)
        self.start.setValue(a/project.rate)
        self.end.setValue(b/project.rate)
        self.start.valueChanged.connect(lambda _: self.trim.setChecked(True))
        self.end.valueChanged.connect(lambda _: self.trim.setChecked(True))
        self.resize(560, 220)

    def save(self):
        region = (round(self.start.value()*self.project.rate), round(self.end.value()*self.project.rate)) if self.trim.isChecked() else None
        try:
            save_loop_range(self.project, region)
        except (OSError, ProjectError) as exc:
            QMessageBox.warning(self, tr('No se guardó el bucle'), str(exc))
            return
        self.accept()


class TemplatesDialog(QDialog):
    def __init__(self, project, path, parent=None):
        super().__init__(parent)
        self.project, self.path = project, path
        self.templates = read_templates(path)
        self.applied = False
        self.setWindowTitle(tr('Plantillas de instrumentos · esta biblioteca'))
        self.resize(620, 490)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(tr('Elige una plantilla o escribe un nombre nuevo.')))
        self.names = QComboBox()
        self.names.setEditable(True)
        self.names.addItems(sorted(self.templates))
        layout.addWidget(self.names)
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels([tr('Entrada (Mic12, Mic12.L, Mic12.R…)'), tr('Instrumento')])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)
        row = QHBoxLayout()
        for label, action in [(tr('Añadir fila'), self.add_row), (tr('Quitar fila'), self.remove_row),
                              (tr('Guardar plantilla'), self.save_template), (tr('Eliminar'), self.delete_template)]:
            button = QPushButton(label)
            button.clicked.connect(action)
            row.addWidget(button)
        layout.addLayout(row)
        self.names.activated.connect(lambda _: self.show_mapping(self.templates.get(self.names.currentText(), {})))
        if self.templates:
            self.show_mapping(self.templates[self.names.currentText()])
        else:
            self.names.setEditText(tr('Mis instrumentos'))
            self.show_mapping({t.clips[0].path.stem + ('' if t.output_channel is None else '.L' if t.output_channel == 0 else '.R'): t.name for t in project.tracks})
        hint = QLabel(tr('Aplicar reemplaza las etiquetas de las entradas coincidentes de la toma abierta. Las demás pistas conservan su nombre. Guarda la plantilla para reutilizarla.'))
        hint.setWordWrap(True)
        layout.addWidget(hint)
        buttons = QHBoxLayout()
        apply = QPushButton(tr('Aplicar a esta toma'))
        apply.clicked.connect(self.apply)
        close = QPushButton(tr('Cerrar'))
        close.clicked.connect(self.accept)
        buttons.addWidget(apply)
        buttons.addWidget(close)
        layout.addLayout(buttons)

    def show_mapping(self, mapping):
        self.table.setRowCount(0)
        for key, value in mapping.items():
            i = self.table.rowCount()
            self.table.insertRow(i)
            self.table.setItem(i, 0, QTableWidgetItem(key))
            self.table.setItem(i, 1, QTableWidgetItem(value))

    def add_row(self):
        self.table.insertRow(self.table.rowCount())

    def remove_row(self):
        if self.table.currentRow() >= 0:
            self.table.removeRow(self.table.currentRow())

    def mapping(self):
        result = {}
        for i in range(self.table.rowCount()):
            cells = [self.table.item(i, j).text().strip() if self.table.item(i, j) else '' for j in range(2)]
            key, label = cells
            if not key and not label:
                continue
            key = validate_title(key).casefold()
            if key in result:
                raise ProjectError(tr('Entrada duplicada: {0}', key))
            result[key] = validate_title(label)
        if not result:
            raise ProjectError(tr('Añade al menos una entrada y su instrumento.'))
        return result

    def save_template(self):
        try:
            name, mapping = validate_title(self.names.currentText()), self.mapping()
            updated = dict(self.templates)
            updated[name] = mapping
            atomic_json(self.path, updated)
            self.templates = updated
            if self.names.findText(name) < 0:
                self.names.addItem(name)
            self.names.setCurrentText(name)
        except (OSError, ProjectError) as exc:
            QMessageBox.warning(self, tr('Plantillas'), str(exc))

    def delete_template(self):
        name = self.names.currentText()
        if name not in self.templates:
            return
        try:
            updated = dict(self.templates)
            del updated[name]
            atomic_json(self.path, updated)
            self.templates = updated
            self.names.removeItem(self.names.findText(name))
            self.show_mapping(self.templates.get(self.names.currentText(), {}))
        except OSError as exc:
            QMessageBox.warning(self, tr('Plantillas'), str(exc))

    def apply(self):
        try:
            count = apply_template(self.project, self.mapping())
            self.applied = True
            QMessageBox.information(self, tr('Plantilla aplicada'), tr('{0} pistas etiquetadas y guardadas.', count))
        except (ProjectError, OSError) as exc:
            QMessageBox.warning(self, tr('Plantillas'), str(exc))


def show_report(parent, title, text):
    dialog = QDialog(parent)
    dialog.setWindowTitle(title)
    dialog.resize(760, 520)
    layout = QVBoxLayout(dialog)
    report = QPlainTextEdit()
    report.setReadOnly(True)
    report.setPlainText(text)
    layout.addWidget(report)
    close = QPushButton(tr('Cerrar'))
    close.clicked.connect(dialog.accept)
    layout.addWidget(close)
    dialog.exec()


class LocateDialog(QDialog):
    def __init__(self, candidates, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr('Asociar WAV encontrados'))
        self.resize(850, 400)
        layout = QVBoxLayout(self)
        hint = QLabel(tr('Coinciden nombre, duración, canales y frecuencia. Comprueba la carpeta y fecha: pueden pertenecer a otra toma. Elige cada archivo; no se mueve ni se copia audio.'))
        hint.setWordWrap(True)
        layout.addWidget(hint)
        table = QTableWidget(len(candidates), 2)
        table.setHorizontalHeaderLabels([tr('WAV faltante'), tr('Archivo encontrado · fecha/referencia BWF')])
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.choices = {}
        for row, (name, matches) in enumerate(candidates.items()):
            table.setItem(row, 0, QTableWidgetItem(name))
            choice = QComboBox()
            choice.addItem(tr('Sin asociar') if matches else tr('Sin coincidencias compatibles'), None)
            for match in matches:
                choice.addItem(match['path']+' · '+match['bwf'], match['path'])
            self.choices[name] = choice
            table.setCellWidget(row, 1, choice)
        layout.addWidget(table)
        buttons = LocalizedButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def selections(self):
        return {name: choice.currentData() for name, choice in self.choices.items() if choice.currentData()}


class ExportOptionsDialog(QDialog):
    def __init__(self, preferences, current, parent=None):
        super().__init__(parent)
        self.preferences = preferences
        self.setWindowTitle(tr('Exportación y presets'))
        self.resize(530, 420)
        layout = QVBoxLayout(self)
        self.names = QComboBox()
        self.names.setEditable(True)
        self.names.addItems(sorted(preferences.presets()))
        self.names.setEditText('')
        self.names.setPlaceholderText(tr('Nombre del preset'))
        layout.addWidget(self.names)
        self.format = QComboBox()
        self.format.addItems(['WAV', 'FLAC'])
        layout.addWidget(self.format)
        self.channels = QComboBox()
        self.channels.addItems([tr('Canales guardados'), tr('Una pista estéreo'), tr('Dos pistas mono (L/R)')])
        layout.addWidget(self.channels)
        self.naming = QComboBox()
        self.naming.addItems([tr('01_Instrumento.wav'), tr('Proyecto_01_Instrumento.wav')])
        layout.addWidget(self.naming)
        self.rpp = QCheckBox(tr('Crear proyecto REAPER (.rpp)'))
        self.portable = QCheckBox(tr('Carpeta de entrega: stems + .rpp + notas + checksums'))
        self.portable.setToolTip(tr('Incluye siempre .rpp y archivos con rutas relativas, lista para compartir.'))
        layout.addWidget(self.rpp)
        layout.addWidget(self.portable)
        hint = QLabel(tr('Los canales se aplican al abrir y exportar lotes. En una exportación individual se usan las pistas visibles. Cada toma conserva su tramo guardado.'))
        hint.setWordWrap(True)
        layout.addWidget(hint)
        row = QHBoxLayout()
        for label, action in [(tr('Guardar preset'), self.save_preset), (tr('Eliminar preset'), self.delete_preset)]:
            button = QPushButton(label)
            button.clicked.connect(action)
            row.addWidget(button)
        layout.addLayout(row)
        buttons = LocalizedButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.names.activated.connect(lambda _: self.populate(preferences.presets()[self.names.currentText()]))
        self.populate(current)

    def populate(self, options):
        options = export_options(options)
        self.format.setCurrentText(options['format'])
        self.channels.setCurrentIndex(options['channels'])
        self.naming.setCurrentIndex(0 if options['naming'] == 'track' else 1)
        self.rpp.setChecked(options['rpp'])
        self.portable.setChecked(options['portable'])

    def options(self):
        return dict(format=self.format.currentText(), channels=self.channels.currentIndex(),
                    rpp=self.rpp.isChecked(), portable=self.portable.isChecked(),
                    naming=('track', 'project_track')[self.naming.currentIndex()])

    def save_preset(self):
        try:
            name = validate_title(self.names.currentText())
            self.preferences.put_preset(name, self.options())
            if self.names.findText(name) < 0:
                self.names.addItem(name)
            self.names.setCurrentText(name)
        except (ProjectError, OSError) as exc:
            QMessageBox.warning(self, 'Preset', str(exc))

    def delete_preset(self):
        try:
            name = self.names.currentText()
            self.preferences.delete_preset(name)
            index = self.names.findText(name)
            if index >= 0:
                self.names.removeItem(index)
        except OSError as exc:
            QMessageBox.warning(self, 'Preset', str(exc))


class AboutDialog(QDialog):
    def __init__(self, preferences, parent=None):
        super().__init__(parent)
        from . import __version__
        from .i18n import language
        from importlib.metadata import version
        import platform
        import soundfile
        import sounddevice
        from PySide6.QtCore import qVersion
        self.preferences = preferences
        self.setWindowTitle(tr('Acerca de H8 Studio'))
        self.resize(580, 460)
        layout = QVBoxLayout(self)
        title = QLabel('H8 Studio '+__version__)
        title.setStyleSheet('font-size:22px;font-weight:600')
        layout.addWidget(title)
        description = QLabel(tr('Preparación de multipistas Zoom H8 para REAPER: escucha, etiquetas y exportación de stems. Los originales se conservan intactos.'))
        description.setWordWrap(True)
        layout.addWidget(description)
        link = QLabel('<a style="color:#70b4fb" href="https://github.com/glazcano/Zoom-Multitrack-Utility">GitHub · glazcano / Zoom-Multitrack-Utility</a>')
        link.setOpenExternalLinks(True)
        layout.addWidget(link)
        layout.addWidget(QLabel(tr('Idioma de la interfaz')))
        self.languages = QComboBox()
        self.languages.addItem('English', 'en')
        self.languages.addItem('Español', 'es')
        self.languages.setCurrentIndex(1 if preferences.data.get('language', language()) == 'es' else 0)
        layout.addWidget(self.languages)
        hint = QLabel(tr('El idioma se aplica al volver a abrir la app.'))
        hint.setWordWrap(True)
        layout.addWidget(hint)
        details = QPlainTextEdit()
        details.setReadOnly(True)
        dependencies = []
        for name in ('PySide6', 'NumPy', 'SoundFile', 'sounddevice'):
            dependencies.append(name+' '+version(name))
        dependencies.extend(['Qt '+qVersion(), 'libsndfile '+soundfile.__libsndfile_version__])
        try:
            dependencies.append(sounddevice.get_portaudio_version()[1])
        except Exception:
            dependencies.append('PortAudio')
        details.setPlainText('\n'.join([
            tr('Dependencias utilizadas'), *dependencies, '',
            'Python '+platform.python_version(), platform.platform(), '',
            tr('Compatible con H8 v001 y tomas completas. Las ediciones MUSIC y overdubs no están verificados.'),
            tr('Audio: WAV/FLAC de 24 bits. Exportación sin procesar; los controles de escucha no afectan a los stems.'),
            tr('Preferencias: ')+str(preferences.path or '—'),
            tr('Proyecto independiente; sin afiliación con Zoom o Cockos.')]))
        layout.addWidget(details)
        buttons = LocalizedButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def save(self):
        old = self.preferences.data.get('language')
        self.preferences.data['language'] = self.languages.currentData()
        try:
            self.preferences.save()
        except OSError as exc:
            if old is None:
                self.preferences.data.pop('language', None)
            else:
                self.preferences.data['language'] = old
            QMessageBox.warning(self, tr('Preferencias'), str(exc))
            return
        self.accept()
