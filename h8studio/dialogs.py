from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox,
    QPlainTextEdit, QDoubleSpinBox, QPushButton, QDialogButtonBox, QMessageBox,
    QComboBox, QTableWidget, QTableWidgetItem, QHeaderView)
from .core import save_preparation, validate_title, ProjectError
from .workflows import read_templates, atomic_json, apply_template
from .preferences import export_options


class PreparationDialog(QDialog):
    def __init__(self, project, cursor, parent=None):
        super().__init__(parent)
        self.project = project
        self.setWindowTitle('Preparar toma')
        self.resize(560, 460)
        layout = QVBoxLayout(self)
        self.favorite = QCheckBox('★ Toma favorita')
        self.favorite.setChecked(project.favorite)
        layout.addWidget(self.favorite)
        layout.addWidget(QLabel('Notas de la toma'))
        self.notes = QPlainTextEdit(project.notes)
        self.notes.setPlaceholderText('Toma buena, instrumentos, ruido al final…')
        layout.addWidget(self.notes)
        self.trim = QCheckBox('Exportar solamente este tramo')
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
        row.addWidget(QLabel('Inicio'))
        row.addWidget(self.start)
        row.addWidget(QLabel('Fin'))
        row.addWidget(self.end)
        layout.addLayout(row)
        markers = QHBoxLayout()
        for label, widget in [('Inicio = cursor', self.start), ('Fin = cursor', self.end)]:
            button = QPushButton(label)
            button.clicked.connect(lambda checked=False, target=widget: (self.trim.setChecked(True), target.setValue(cursor/project.rate)))
            markers.addWidget(button)
        layout.addLayout(markers)
        hint = QLabel('El mismo tramo se aplica a todas las pistas. Los stems y el .rpp comienzan en cero; el original queda intacto.')
        hint.setWordWrap(True)
        layout.addWidget(hint)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def save(self):
        region = (round(self.start.value()*self.project.rate), round(self.end.value()*self.project.rate)) if self.trim.isChecked() else None
        try:
            save_preparation(self.project, self.favorite.isChecked(), self.notes.toPlainText(), region)
        except (OSError, ProjectError) as exc:
            QMessageBox.warning(self, 'No se guardó la toma', str(exc))
            return
        self.accept()


class TemplatesDialog(QDialog):
    def __init__(self, project, path, parent=None):
        super().__init__(parent)
        self.project, self.path = project, path
        self.templates = read_templates(path)
        self.applied = False
        self.setWindowTitle('Plantillas de instrumentos · esta biblioteca')
        self.resize(620, 490)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel('Elige una plantilla o escribe un nombre nuevo.'))
        self.names = QComboBox()
        self.names.setEditable(True)
        self.names.addItems(sorted(self.templates))
        layout.addWidget(self.names)
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(['Entrada (Mic12, Mic12.L, Mic12.R…)', 'Instrumento'])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)
        row = QHBoxLayout()
        for label, action in [('Añadir fila', self.add_row), ('Quitar fila', self.remove_row),
                              ('Guardar plantilla', self.save_template), ('Eliminar', self.delete_template)]:
            button = QPushButton(label)
            button.clicked.connect(action)
            row.addWidget(button)
        layout.addLayout(row)
        self.names.activated.connect(lambda _: self.show_mapping(self.templates.get(self.names.currentText(), {})))
        if self.templates:
            self.show_mapping(self.templates[self.names.currentText()])
        else:
            self.names.setEditText('Mis instrumentos')
            self.show_mapping({t.clips[0].path.stem + ('' if t.output_channel is None else '.L' if t.output_channel == 0 else '.R'): t.name for t in project.tracks})
        hint = QLabel('Aplicar reemplaza las etiquetas de las entradas coincidentes de la toma abierta. Las demás pistas conservan su nombre. Guarda la plantilla para reutilizarla.')
        hint.setWordWrap(True)
        layout.addWidget(hint)
        buttons = QHBoxLayout()
        apply = QPushButton('Aplicar a esta toma')
        apply.clicked.connect(self.apply)
        close = QPushButton('Cerrar')
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
                raise ProjectError(f'Entrada duplicada: {key}')
            result[key] = validate_title(label)
        if not result:
            raise ProjectError('Añade al menos una entrada y su instrumento.')
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
            QMessageBox.warning(self, 'Plantillas', str(exc))

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
            QMessageBox.warning(self, 'Plantillas', str(exc))

    def apply(self):
        try:
            count = apply_template(self.project, self.mapping())
            self.applied = True
            QMessageBox.information(self, 'Plantilla aplicada', f'{count} pistas etiquetadas y guardadas.')
        except (ProjectError, OSError) as exc:
            QMessageBox.warning(self, 'Plantillas', str(exc))


def show_report(parent, title, text):
    dialog = QDialog(parent)
    dialog.setWindowTitle(title)
    dialog.resize(760, 520)
    layout = QVBoxLayout(dialog)
    report = QPlainTextEdit()
    report.setReadOnly(True)
    report.setPlainText(text)
    layout.addWidget(report)
    close = QPushButton('Cerrar')
    close.clicked.connect(dialog.accept)
    layout.addWidget(close)
    dialog.exec()


class LocateDialog(QDialog):
    def __init__(self, candidates, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Asociar WAV encontrados')
        self.resize(850, 400)
        layout = QVBoxLayout(self)
        hint = QLabel('Coinciden nombre, duración, canales y frecuencia. Comprueba la carpeta y fecha: '
                      'pueden pertenecer a otra toma. Elige cada archivo; no se mueve ni se copia audio.')
        hint.setWordWrap(True)
        layout.addWidget(hint)
        table = QTableWidget(len(candidates), 2)
        table.setHorizontalHeaderLabels(['WAV faltante', 'Archivo encontrado · fecha/referencia BWF'])
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.choices = {}
        for row, (name, matches) in enumerate(candidates.items()):
            table.setItem(row, 0, QTableWidgetItem(name))
            choice = QComboBox()
            choice.addItem('Sin asociar' if matches else 'Sin coincidencias compatibles', None)
            for match in matches:
                choice.addItem(match['path']+' · '+match['bwf'], match['path'])
            self.choices[name] = choice
            table.setCellWidget(row, 1, choice)
        layout.addWidget(table)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def selections(self):
        return {name: choice.currentData() for name, choice in self.choices.items() if choice.currentData()}


class ExportOptionsDialog(QDialog):
    def __init__(self, preferences, current, parent=None):
        super().__init__(parent)
        self.preferences = preferences
        self.setWindowTitle('Exportación y presets')
        self.resize(530, 420)
        layout = QVBoxLayout(self)
        self.names = QComboBox()
        self.names.setEditable(True)
        self.names.addItems(sorted(preferences.presets()))
        self.names.setEditText('')
        self.names.setPlaceholderText('Nombre del preset')
        layout.addWidget(self.names)
        self.format = QComboBox()
        self.format.addItems(['WAV', 'FLAC'])
        layout.addWidget(self.format)
        self.channels = QComboBox()
        self.channels.addItems(['Canales guardados', 'Una pista estéreo', 'Dos pistas mono (L/R)'])
        layout.addWidget(self.channels)
        self.naming = QComboBox()
        self.naming.addItems(['01_Instrumento.wav', 'Proyecto_01_Instrumento.wav'])
        layout.addWidget(self.naming)
        self.rpp = QCheckBox('Crear proyecto REAPER (.rpp)')
        self.portable = QCheckBox('Carpeta de entrega: stems + .rpp + notas + checksums')
        self.portable.setToolTip('Incluye siempre .rpp y archivos con rutas relativas, lista para compartir.')
        layout.addWidget(self.rpp)
        layout.addWidget(self.portable)
        hint = QLabel('Los canales se aplican al abrir y exportar lotes. En una exportación individual '
                      'se usan las pistas visibles. Cada toma conserva su tramo guardado.')
        hint.setWordWrap(True)
        layout.addWidget(hint)
        row = QHBoxLayout()
        for label, action in [('Guardar preset', self.save_preset), ('Eliminar preset', self.delete_preset)]:
            button = QPushButton(label)
            button.clicked.connect(action)
            row.addWidget(button)
        layout.addLayout(row)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
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
