"""Small, explicit EN/ES catalog. Project names and notes are never translated."""
_language = 'en'


def set_language(value):
    global _language
    _language = value if value in ('en', 'es') else 'en'


def language():
    return _language


def tr(source, *values):
    text = EN.get(source, source) if _language == 'en' else source
    return text.format(*values) if values else text


EN = {'01_Instrumento.wav': '01_Instrument.wav',
 '0:00  ↓ tiempo': '0:00  ↓ time',
 'Abre un archivo .h8prj con sus WAV en la misma carpeta.': 'Open an .h8prj file with its WAV files in the '
                                                            'same folder.',
 'Abre un proyecto .h8prj para ver sus pistas': 'Open an .h8prj project to see its tracks',
 'Abrir': 'Open',
 'Abrir proyecto Zoom H8': 'Open Zoom H8 project',
 'Abrir proyecto…': 'Open project…',
 'Aceptar': 'OK',
 'Acerca de H8 Studio': 'About H8 Studio',
 'Acerca de…': 'About…',
 'Ajustar': 'Fit',
 'Al abrir guarda la elección. Al exportar un lote solo cambia esa exportación.': 'Opening saves this '
                                                                                  'choice. Batch export '
                                                                                  'changes only that export.',
 'Alternar una pista estéreo y dos pistas mono L/R; también afecta a los stems': 'Switch between one stereo '
                                                                                 'track and two mono L/R '
                                                                                 'tracks; also affects stems',
 'Analizando proyectos marcados o la toma abierta…': 'Analyzing checked projects or the open take…',
 'Aplicar a esta toma': 'Apply to this take',
 'Aplicar canales al lote': 'Apply channels to batch',
 'Aplicar reemplaza las etiquetas de las entradas coincidentes de la toma abierta. Las demás pistas conservan su nombre. Guarda la plantilla para reutilizarla.': 'Applying '
                                                                                                                                                                  'replaces '
                                                                                                                                                                  'labels '
                                                                                                                                                                  'for '
                                                                                                                                                                  'matching '
                                                                                                                                                                  'inputs '
                                                                                                                                                                  'in '
                                                                                                                                                                  'the '
                                                                                                                                                                  'open '
                                                                                                                                                                  'take. '
                                                                                                                                                                  'Other '
                                                                                                                                                                  'tracks '
                                                                                                                                                                  'keep '
                                                                                                                                                                  'their '
                                                                                                                                                                  'names. '
                                                                                                                                                                  'Save '
                                                                                                                                                                  'the '
                                                                                                                                                                  'template '
                                                                                                                                                                  'to '
                                                                                                                                                                  'reuse '
                                                                                                                                                                  'it.',
 'Archivo encontrado · fecha/referencia BWF': 'Recovered file · BWF date/reference',
 'Asignaciones inválidas': 'Invalid assignments',
 'Asociar WAV encontrados': 'Link recovered WAV files',
 'Audio truncado: {0}': 'Truncated audio: {0}',
 'Audio: WAV/FLAC de 24 bits. Exportación sin procesar; los controles de escucha no afectan a los stems.': 'Audio: '
                                                                                                           '24-bit '
                                                                                                           'WAV/FLAC. '
                                                                                                           'Dry '
                                                                                                           'export; '
                                                                                                           'monitor '
                                                                                                           'controls '
                                                                                                           'do '
                                                                                                           'not '
                                                                                                           'affect '
                                                                                                           'stems.',
 'Avisos': 'Warnings',
 'Avisos ({0})': 'Warnings ({0})',
 'Añade al menos una entrada y su instrumento.': 'Add at least one input and its instrument.',
 'Añadir fila': 'Add row',
 'BWF · muestras relativas al primer WAV': 'BWF · samples relative to the first WAV',
 'Biblioteca': 'Library',
 'Bucle': 'Loop',
 'Buscando WAV compatibles…': 'Looking for compatible WAV files…',
 'Buscar WAV en esta carpeta y subcarpetas': 'Search this folder and subfolders for WAV files',
 'Buscar nombre, notas o carpeta…': 'Search names, notes or folders…',
 'Cabecera H8 fuera del formato comprobado.': 'H8 header is outside the validated format.',
 'Cambiar título del proyecto': 'Rename project',
 'Cambiar título…': 'Rename project…',
 'Canales al abrir / lote': 'Open / batch channels',
 'Canales del lote': 'Batch channels',
 'Canales guardados': 'Saved channels',
 'Canales guardados · la exportación usará las pistas visibles': 'Channels saved · export will use the '
                                                                 'visible tracks',
 'Cancelado': 'Cancelled',
 'Cancelado: las elecciones ya guardadas se conservan.': 'Cancelled: choices already saved are retained.',
 'Cancelar': 'Cancel',
 'Cancelar tarea': 'Cancel task',
 'Carpeta de entrega: stems + .rpp + notas + checksums': 'Delivery folder: stems + .rpp + notes + checksums',
 'Carpeta de proyectos': 'Projects folder',
 'Carpeta e informe lote.json: {0}': 'Folder and lote.json report: {0}',
 'Cerrar': 'Close',
 'Coinciden nombre, duración, canales y frecuencia. Comprueba la carpeta y fecha: pueden pertenecer a otra toma. Elige cada archivo; no se mueve ni se copia audio.': 'Name, '
                                                                                                                                                                      'duration, '
                                                                                                                                                                      'channels '
                                                                                                                                                                      'and '
                                                                                                                                                                      'sample '
                                                                                                                                                                      'rate '
                                                                                                                                                                      'match. '
                                                                                                                                                                      'Check '
                                                                                                                                                                      'the '
                                                                                                                                                                      'folder '
                                                                                                                                                                      'and '
                                                                                                                                                                      'date: '
                                                                                                                                                                      'files '
                                                                                                                                                                      'may '
                                                                                                                                                                      'belong '
                                                                                                                                                                      'to '
                                                                                                                                                                      'another '
                                                                                                                                                                      'take. '
                                                                                                                                                                      'Choose '
                                                                                                                                                                      'each '
                                                                                                                                                                      'file; '
                                                                                                                                                                      'audio '
                                                                                                                                                                      'is '
                                                                                                                                                                      'not '
                                                                                                                                                                      'moved '
                                                                                                                                                                      'or '
                                                                                                                                                                      'copied.',
 'Compatible con H8 v001 y tomas completas. Las ediciones MUSIC y overdubs no están verificados.': 'Supports '
                                                                                                   'H8 v001 '
                                                                                                   'complete '
                                                                                                   'takes. '
                                                                                                   'MUSIC '
                                                                                                   'edits '
                                                                                                   'and '
                                                                                                   'overdubs '
                                                                                                   'are not '
                                                                                                   'verified.',
 'Consola': 'Console',
 'Consola vertical': 'Vertical console',
 'Crear .rpp': 'Create .rpp',
 'Crear proyecto REAPER (.rpp)': 'Create REAPER project (.rpp)',
 'Definir el tramo del bucle': 'Set the loop range',
 'Dependencias utilizadas': 'Dependencies',
 'Destino: se creará una carpeta nueva para los stems': 'Destination: a new folder will be created for the '
                                                        'stems',
 'Doble clic: abrir · casillas: lote': 'Double-click: open · checkboxes: batch',
 'Dos pistas mono (L/R)': 'Two mono tracks (L/R)',
 'El mismo tramo se aplica a todas las pistas. Los stems y el .rpp comienzan en cero; el original queda intacto.': 'The '
                                                                                                                   'same '
                                                                                                                   'range '
                                                                                                                   'applies '
                                                                                                                   'to '
                                                                                                                   'all '
                                                                                                                   'tracks. '
                                                                                                                   'Stems '
                                                                                                                   'and '
                                                                                                                   'the '
                                                                                                                   '.rpp '
                                                                                                                   'start '
                                                                                                                   'at '
                                                                                                                   'zero; '
                                                                                                                   'originals '
                                                                                                                   'stay '
                                                                                                                   'intact.',
 'El proyecto no contiene referencias a WAV.': 'The project contains no WAV references.',
 'El tramo debe tener inicio menor que fin y estar dentro de la grabación.': 'Start must be before end, and '
                                                                             'the range must be within the '
                                                                             'recording.',
 'El título debe ser texto.': 'Title must be text.',
 'Elige una plantilla o escribe un nombre nuevo.': 'Choose a template or enter a new name.',
 'Eliminar': 'Delete',
 'Eliminar preset': 'Delete preset',
 'Entrada (Mic12, Mic12.L, Mic12.R…)': 'Input (Mic12, Mic12.L, Mic12.R…)',
 'Entrada duplicada: {0}': 'Duplicate input: {0}',
 'Entrega portátil: .rpp, notas y checksums incluidos': 'Portable delivery: .rpp, notes and checksums '
                                                        'included',
 'Escribe un título de 1 a 100 caracteres, en una sola línea.': 'Enter a single-line title of 1 to 100 '
                                                                'characters.',
 'Escucha': 'Monitor',
 'Escuchar los canales mono L/R por ambos altavoces. Solo monitoreo.': 'Listen to L/R mono channels through '
                                                                       'both speakers. Monitoring only.',
 'Espera a que termine la lectura o cancela la exportación antes de cerrar.': 'Wait for loading to finish or '
                                                                              'cancel the export before '
                                                                              'closing.',
 'Este proyecto tiene tomas de distinta duración sin alineación FIELD verificable. Se necesita analizar su disposición MUSIC antes de importarlo.': 'This '
                                                                                                                                                    'project '
                                                                                                                                                    'has '
                                                                                                                                                    'takes '
                                                                                                                                                    'of '
                                                                                                                                                    'different '
                                                                                                                                                    'lengths '
                                                                                                                                                    'without '
                                                                                                                                                    'verifiable '
                                                                                                                                                    'FIELD '
                                                                                                                                                    'alignment. '
                                                                                                                                                    'Its '
                                                                                                                                                    'MUSIC '
                                                                                                                                                    'arrangement '
                                                                                                                                                    'must '
                                                                                                                                                    'be '
                                                                                                                                                    'analyzed '
                                                                                                                                                    'before '
                                                                                                                                                    'importing.',
 'Estéreo': 'Stereo',
 'Estéreo · 2 canales': 'Stereo · 2 channels',
 'Etiquetar esta pista con el nombre del instrumento': 'Label this track with the instrument name',
 'Explorar carpeta…': 'Browse folder…',
 'Exportación': 'Export',
 'Exportación terminada': 'Export complete',
 'Exportación y presets': 'Export and presets',
 'Exportación y presets…': 'Export and presets…',
 'Exportados: {0}': 'Exported: {0}',
 'Exportando stems {0} a 24 bits…': 'Exporting {0} stems at 24 bits…',
 'Exportando {0} proyectos con sus tramos guardados…': 'Exporting {0} projects with their saved export '
                                                       'ranges…',
 'Exportar lote marcado…': 'Export checked projects…',
 'Exportar solamente este tramo': 'Export only this range',
 'Exportar {0} proyectos: destino del lote': 'Export {0} projects: batch destination',
 'Exportar…': 'Export…',
 'FALTA AUDIO': 'MISSING AUDIO',
 'FALTA AUDIO · ': 'MISSING AUDIO · ',
 'Fallidos: {0}': 'Failed: {0}',
 'Falta audio / error de lectura': 'Missing audio / read error',
 'Falta {0}. No se permite exportar hasta localizarlo.': 'Missing {0}. Locate it before exporting.',
 'Falta: ': 'Missing: ',
 'Faltan WAV': 'Missing WAV files',
 'Faltan WAV. Localiza los archivos antes de exportar.': 'Missing WAV files. Locate them before exporting.',
 'Favorita, notas y tramo…': 'Favorite, notes and export range…',
 'Favorito o notas guardadas inválidas.': 'Invalid saved favorite or notes.',
 'Fecha BWF inválida; no se puede determinar la alineación.': 'Invalid BWF date; alignment cannot be '
                                                              'determined.',
 'Fin': 'End',
 'Fin = cursor': 'End = cursor',
 'Formato inválido': 'Invalid format',
 'Formato no compatible': 'Unsupported format',
 'Guardar': 'Save',
 'Guardar plantilla': 'Save template',
 'Guardar preset': 'Save preset',
 'H8 Studio · Proyectos Zoom': 'H8 Studio · Zoom projects',
 'Idioma de la interfaz': 'Interface language',
 'Incluye siempre .rpp y archivos con rutas relativas, lista para compartir.': 'Always includes .rpp and '
                                                                               'relative paths, ready to '
                                                                               'share.',
 'Inicio': 'Start',
 'Inicio = cursor': 'Start = cursor',
 'Inicio común': 'Common start',
 'Inicio común · asignaciones H8': 'Common start · H8 assignments',
 'Instrumento': 'Instrument',
 'La carpeta debe contener exactamente un archivo .h8prj.': 'The folder must contain exactly one .h8prj '
                                                            'file.',
 'La pista no pertenece al proyecto.': 'The track does not belong to this project.',
 'La plantilla no coincide con las entradas de este proyecto.': "The template does not match this project's "
                                                                'inputs.',
 'La suma de clips de {0} satura. No se exportó audio recortado.': 'The sum of clips in {0} clips. No '
                                                                   'clipped audio was exported.',
 'Las etiquetas de pistas deben ser un objeto JSON': 'Track labels must be a JSON object',
 'Las notas admiten hasta 10 000 caracteres.': 'Notes allow up to 10,000 characters.',
 'Lectura v001 validada con tomas completas. Ediciones, overdubs y regiones MUSIC aún no verificados.': 'v001 '
                                                                                                        'reading '
                                                                                                        'validated '
                                                                                                        'with '
                                                                                                        'complete '
                                                                                                        'takes. '
                                                                                                        'MUSIC '
                                                                                                        'edits, '
                                                                                                        'overdubs '
                                                                                                        'and '
                                                                                                        'regions '
                                                                                                        'are '
                                                                                                        'not '
                                                                                                        'yet '
                                                                                                        'verified.',
 'Leyendo proyecto y formas de onda…': 'Reading project and waveforms…',
 'Listo': 'Ready',
 'Localizar WAV…': 'Locate WAV files…',
 'Los canales se aplican al abrir y exportar lotes. En una exportación individual se usan las pistas visibles. Cada toma conserva su tramo guardado.': 'Channel '
                                                                                                                                                       'choices '
                                                                                                                                                       'apply '
                                                                                                                                                       'when '
                                                                                                                                                       'opening '
                                                                                                                                                       'and '
                                                                                                                                                       'batch '
                                                                                                                                                       'exporting. '
                                                                                                                                                       'Single '
                                                                                                                                                       'exports '
                                                                                                                                                       'use '
                                                                                                                                                       'visible '
                                                                                                                                                       'tracks. '
                                                                                                                                                       'Each '
                                                                                                                                                       'take '
                                                                                                                                                       'retains '
                                                                                                                                                       'its '
                                                                                                                                                       'saved '
                                                                                                                                                       'export '
                                                                                                                                                       'range.',
 'Lote terminado': 'Batch complete',
 'Lote: {0} exportados; {1} fallidos.': 'Batch: {0} exported; {1} failed.',
 'Línea de tiempo': 'Timeline',
 'Marca al menos un proyecto para exportar.': 'Check at least one project to export.',
 'Marca las casillas de los proyectos que quieres exportar.': 'Check the projects you want to export.',
 'Marca proyectos y elige una pista estéreo o dos pistas mono.': 'Check projects and choose one stereo track '
                                                                 'or two mono tracks.',
 'Marcar favoritas para el lote': 'Select favorites for batch',
 'Mis instrumentos': 'My instruments',
 'Mono centrado': 'Center mono',
 'Mono · 1 canal': 'Mono · 1 channel',
 'Ninguna': 'None',
 'No se guardó el bucle': 'Could not save the loop',
 'No se guardó el nombre: {0}': 'Could not save the name: {0}',
 'No se guardó el título: {0}': 'Could not save the title: {0}',
 'No se guardó la toma': 'Could not save the take',
 'No se pudieron recuperar las preferencias: {0}': 'Could not restore preferences: {0}',
 'No se pudo abrir la salida de audio: {0}': 'Could not open the audio output: {0}',
 'No se pudo guardar la sesión: {0}': 'Could not save the session: {0}',
 'No se pudo leer el título guardado en {0}: {1}': 'Could not read the title saved in {0}: {1}',
 'No se puede leer {0}: {1}': 'Cannot read {0}: {1}',
 'No se pueden leer las plantillas: {0}': 'Cannot read templates: {0}',
 'Nombre de archivo no compatible': 'Unsupported file naming',
 'Nombre de pista (hasta 100 caracteres):': 'Track name (up to 100 characters):',
 'Nombre del instrumento': 'Instrument name',
 'Nombre del preset': 'Preset name',
 'Nombre…': 'Name…',
 'Notas de la toma': 'Take notes',
 'Observaciones del proyecto': 'Project warnings',
 'Opciones de exportación inválidas.': 'Invalid export options.',
 'PROYECTOS': 'PROJECTS',
 'PROYECTOS  /  {0} de {1}': 'PROJECTS  /  {0} of {1}',
 'Pendientes: {0}': 'Pending: {0}',
 'Pico de escucha en dBFS. Los medidores de pista muestran el pico de entrada.': 'Monitor peak in dBFS. '
                                                                                 'Track meters show input '
                                                                                 'peaks.',
 'Pista guardada: {0}. Los stems usarán esta etiqueta.': 'Track saved: {0}. Stems will use this label.',
 'Plantilla aplicada': 'Template applied',
 'Plantillas': 'Templates',
 'Plantillas de instrumentos · esta biblioteca': 'Instrument templates · this library',
 'Plantillas…': 'Templates…',
 'Preferencias': 'Preferences',
 'Preferencias de canales inválidas.': 'Invalid channel preferences.',
 'Preferencias de preparación inválidas: {0}': 'Invalid preparation preferences: {0}',
 'Preferencias: ': 'Preferences: ',
 'Preparación de multipistas Zoom H8 para REAPER: escucha, etiquetas y exportación de stems. Los originales se conservan intactos.': 'Prepare '
                                                                                                                                     'Zoom '
                                                                                                                                     'H8 '
                                                                                                                                     'multitracks '
                                                                                                                                     'for '
                                                                                                                                     'REAPER: '
                                                                                                                                     'monitor, '
                                                                                                                                     'label '
                                                                                                                                     'and '
                                                                                                                                     'export '
                                                                                                                                     'stems. '
                                                                                                                                     'Original '
                                                                                                                                     'recordings '
                                                                                                                                     'stay '
                                                                                                                                     'intact.',
 'Preparar toma': 'Prepare take',
 'Preset inválido.': 'Invalid preset.',
 'Proyecto': 'Project',
 'Proyecto Zoom (*.h8prj)': 'Zoom project (*.h8prj)',
 'Proyecto abierto · clic en una onda para mover el cursor · Espacio para reproducir': 'Project open · click '
                                                                                       'a waveform to seek · '
                                                                                       'Space to play',
 'Proyecto independiente; sin afiliación con Zoom o Cockos.': 'Independent project; not affiliated with Zoom '
                                                              'or Cockos.',
 'Proyecto_01_Instrumento.wav': 'Project_01_Instrument.wav',
 'Quitar fila': 'Remove row',
 'Referencia de audio no reconocida en el proyecto.': 'Unknown audio reference in the project.',
 'Referencias BWF separadas por más de un día; revise el proyecto.': 'BWF references are more than a day '
                                                                     'apart; review the project.',
 'Referencias de WAV guardadas inválidas.': 'Invalid saved WAV references.',
 'Repetir este tramo': 'Repeat this range',
 'Repite el tramo del bucle o toda la toma. Usa A–B para definir inicio y fin.': 'Repeat the loop range or '
                                                                                 'the entire take. Use A–B '
                                                                                 'to set the start and end.',
 'Resultado del lote': 'Batch result',
 'Resumen de problemas': 'Problem summary',
 'Resumen de problemas…': 'Problem summary…',
 'Se esperaba un objeto JSON': 'Expected a JSON object',
 'Se usaron tiempos BWF de grabación; no representan necesariamente ediciones hechas en la grabadora.': 'BWF '
                                                                                                        'recording '
                                                                                                        'times '
                                                                                                        'were '
                                                                                                        'used; '
                                                                                                        'they '
                                                                                                        'may '
                                                                                                        'not '
                                                                                                        'represent '
                                                                                                        'edits '
                                                                                                        'made '
                                                                                                        'on '
                                                                                                        'the '
                                                                                                        'recorder.',
 'Sin BWF': 'No BWF',
 'Sin asociar': 'Not linked',
 'Sin coincidencias compatibles': 'No compatible matches',
 'Sin tramo personalizado se repite toda la toma. El bucle no cambia el tramo de exportación. Ámbar: bucle; verde: exportación.': 'Without '
                                                                                                                                  'a '
                                                                                                                                  'custom '
                                                                                                                                  'range, '
                                                                                                                                  'the '
                                                                                                                                  'entire '
                                                                                                                                  'take '
                                                                                                                                  'repeats. '
                                                                                                                                  'Looping '
                                                                                                                                  'does '
                                                                                                                                  'not '
                                                                                                                                  'change '
                                                                                                                                  'the '
                                                                                                                                  'export '
                                                                                                                                  'range. '
                                                                                                                                  'Amber: '
                                                                                                                                  'loop; '
                                                                                                                                  'green: '
                                                                                                                                  'export.',
 'Stems guardados en {0}': 'Stems saved in {0}',
 'Stems · nombres ': 'Stems · names ',
 'Tarea cancelada. No se publicaron archivos incompletos.': 'Task cancelled. No incomplete files were '
                                                            'published.',
 'Todas': 'All',
 'Todos los proyectos': 'All projects',
 'Toma buena, instrumentos, ruido al final…': 'Good take, instruments, noise at the end…',
 'Tramo del bucle': 'Loop range',
 'Tramo guardado inválido.': 'Invalid saved range.',
 'Tu grabación, lista para continuar.': 'Your recording, ready for the next step.',
 'Título (hasta 100 caracteres):': 'Title (up to 100 characters):',
 'Título guardado. Se usará también al exportar los stems.': 'Title saved. It will also be used when '
                                                             'exporting stems.',
 'Una pista estéreo': 'One stereo track',
 'Usar elección guardada': 'Use saved choice',
 'Versión o estructura H8 no reconocida. No se adivinarán las posiciones.': 'Unknown H8 version or '
                                                                            'structure. Clip positions will '
                                                                            'not be guessed.',
 'Volumen de escucha. No modifica los stems.': 'Monitor level. Does not affect stems.',
 'Volumen de escucha; no modifica los stems. Arriba: +6 dB; abajo: −60 dB.': 'Monitor level; does not affect '
                                                                             'stems. Top: +6 dB; bottom: −60 '
                                                                             'dB.',
 'WAV asociados y guardados. Los archivos originales no se modificaron.': 'WAV links saved. Original files '
                                                                          'were not modified.',
 'WAV faltante': 'Missing WAV',
 'WAV sin asignación, no importados: ': 'Unassigned WAV files, not imported: ',
 'Zoom de la línea de tiempo. Las consolas muestran la toma completa.': 'Timeline zoom. Console views show '
                                                                        'the entire take.',
 'con prefijo de proyecto': 'with project prefix',
 'nivel medio muy bajo (< −60 dBFS)': 'very low average level (< −60 dBFS)',
 'por instrumento': 'by instrument',
 'posible saturación: {0} muestras ≥ −0,1 dBFS': 'possible clipping: {0} samples ≥ −0.1 dBFS',
 'silencio digital': 'digital silence',
 'sin alertas de nivel': 'no level warnings',
 '{0}\n\nSi activaste Crear .rpp, abre Proyecto.rpp en Reaper. También puedes importar los stems desde 00:00. Todos respetan el tramo elegido.': '{0}\n'
                                                                                                                                                 '\n'
                                                                                                                                                 'If '
                                                                                                                                                 'Create '
                                                                                                                                                 '.rpp '
                                                                                                                                                 'was '
                                                                                                                                                 'enabled, '
                                                                                                                                                 'open '
                                                                                                                                                 'Proyecto.rpp '
                                                                                                                                                 'in '
                                                                                                                                                 'REAPER. '
                                                                                                                                                 'You '
                                                                                                                                                 'can '
                                                                                                                                                 'also '
                                                                                                                                                 'import '
                                                                                                                                                 'stems '
                                                                                                                                                 'at '
                                                                                                                                                 '00:00. '
                                                                                                                                                 'All '
                                                                                                                                                 'files '
                                                                                                                                                 'use '
                                                                                                                                                 'the '
                                                                                                                                                 'selected '
                                                                                                                                                 'export '
                                                                                                                                                 'range.',
 '{0} pistas  ·  {1:g} kHz  ·  {2}  ·  {3}': '{0} tracks  ·  {1:g} kHz  ·  {2}  ·  {3}',
 '{0} pistas etiquetadas y guardadas.': '{0} tracks labelled and saved.',
 '{0} pistas · {1:g} kHz · Exportar {2} → {3}': '{0} tracks · {1:g} kHz · Export {2} → {3}',
 '{0}: FALTA AUDIO: {1}': '{0}: MISSING AUDIO: {1}',
 '{0}: canales guardados': '{0}: channels saved',
 '{0}: el WAV ya no coincide en nombre, duración, canales o frecuencia.': '{0}: WAV no longer matches name, '
                                                                          'duration, channels or sample '
                                                                          'rate.',
 '{0}: frecuencia o canales incompatibles con el proyecto.': '{0}: sample rate or channels incompatible with '
                                                             'the project.',
 '{0}: pico {1}; ': '{0}: peak {1}; ',
 'Ⅱ  Pausa': 'Ⅱ  Pause',
 '■  Inicio': '■  Start',
 '▶  Reproducir': '▶  Play',
 '★ Favoritos': '★ Favorites',
 '★ Toma favorita': '★ Favorite take'}

EN.update({'Análisis de las tomas completas. Pico ≥ −0,1 dBFS: posible saturación; RMS < −60 dBFS: nivel muy bajo.\n': 'Complete-take analysis. Peak ≥ −0.1 dBFS: possible clipping; RMS < −60 dBFS: very low level.\n', '\nObservaciones de importación:': '\nImport warnings:'})
EN['El idioma se aplica al volver a abrir la app.'] = 'Language changes take effect next time you open the app.'

EN.update({'Clic: mover cursor. Arrastrar: definir bucle. Arrastra un extremo ámbar para ajustarlo. Esc: cancelar.': 'Click: seek. Drag: select loop. Drag an amber boundary to adjust it. Esc: cancel.', '×1: toma completa. Arrastra la perilla o escribe un valor entre ×0,1 y ×50.': '×1: fit the whole take. Turn the dial or enter a value from ×0.1 to ×50.', 'Desplazar el tiempo visible en las tres vistas': 'Scroll the visible time in all three views'})
