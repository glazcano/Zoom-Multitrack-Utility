# H8 Studio

Reproductor multipista y exportador de stems para proyectos Zoom H8. Paquete Windows
verificado y código común preparado para empaquetar en Fedora y macOS.
Consulta [los pasos por plataforma](docs/platforms.md) y sus pruebas pendientes.

## Abrir

Haz doble clic en **Abrir H8 Studio.cmd**, o abre `dist/H8Studio/H8Studio.exe`.
No hace falta instalar Python ni FFmpeg para usar la versión compilada.
Para mover la aplicación a otro equipo, copia **toda la carpeta H8Studio**, incluido `_internal`.

1. Pulsa **Explorar carpeta** para listar los proyectos de una carpeta o tarjeta copiada.
2. Haz doble clic en un proyecto de la lista, usa **Abrir proyecto**, o arrastra un `.h8prj` o carpeta `.zprj`.
3. Pulsa **Reproducir** o Espacio. Haz clic en la línea de tiempo para cambiar de posición.
4. Usa volumen, mute y solo por pista, y el nivel de escucha general. **Inicio** detiene y vuelve a cero.
5. Elige WAV o FLAC y pulsa **Exportar stems**. Se crea una carpeta nueva en el destino elegido.
6. En Reaper importa todos los stems en pistas separadas desde **00:00**.

Los stems tienen igual duración, silencios de relleno y 24 bits. Conservan el número de canales de cada pista.
Se exporta el audio original: los controles de escucha no alteran los stems. No se normaliza ni se aplican efectos.
Para WAV mayores de 4 GiB se usa el contenedor RF64. La exportación se puede cancelar sin publicar archivos parciales.
Los originales nunca se escriben y las exportaciones anteriores no se sobrescriben.

### Cambiar el título del proyecto

Abre un proyecto y pulsa **Cambiar título…**, junto al nombre. El título se actualiza
en la lista de proyectos y se usa para nombrar la carpeta de stems y su informe de exportación.
Se conserva al volver a abrir la app mediante un archivo `.h8studio.json` junto al `.h8prj`.
Copia también ese archivo si trasladas el proyecto. No se renombran la carpeta original,
el `.h8prj` ni los WAV, y el nombre que muestra la grabadora Zoom no cambia.

En cada pista pulsa **Nombre…** para poner la etiqueta del instrumento (por ejemplo,
Guitarra, Voz o Batería). Se guarda en el mismo archivo auxiliar y se utiliza para
nombrar el stem exportado. Los WAV originales conservan sus nombres.

## Preparar y exportar sesiones

- **Favorita, notas y tramo…** guarda una estrella, notas de hasta 10 000 caracteres
  y, opcionalmente, el inicio y fin de exportación en segundos. Los botones de cursor
  permiten usar la posición actual. Se guardan en el archivo auxiliar del proyecto.
  Desmarca el tramo para volver a exportar la toma completa. La reproducción sigue
  mostrando la grabación entera; una barra verde señala el tramo elegido.
- **Plantillas…** permite crear, editar, guardar, eliminar y aplicar asignaciones de
  entradas originales a instrumentos: `Mic12 → Ambiente`, `Tr1 → Guitarra`, etc.
  El nombre de la entrada se escribe sin extensión y no distingue mayúsculas.
  Se guardan en `.h8studio-templates.json` dentro de la carpeta explorada como biblioteca.
  Aplicar afecta la toma abierta y conserva las etiquetas de entradas sin coincidencia.
- **Exportar lote marcado…** procesa los proyectos cuyas casillas estén marcadas.
  Los botones Todas, Ninguna y ★ facilitan la selección. Se usa el formato WAV/FLAC
  y la opción Crear .rpp de la ventana principal, junto al tramo y etiquetas guardados
  de cada proyecto. Cada lote tiene su propia carpeta y un informe `lote.json` con
  proyectos completados, fallidos y pendientes. Un fallo no detiene los demás proyectos.
  Al cancelar se conservan los proyectos ya terminados y se descarta la exportación
  incompleta en curso; los pendientes quedan identificados.
- **Crear .rpp**, activado por defecto, añade `Proyecto.rpp` junto a los stems.
  Contiene pistas etiquetadas, mono/estéreo, sin efectos y con inicio en cero.
  Abre ese archivo en Reaper y conserva junto a él los stems; usa rutas relativas.
  Si recortaste, la duración del proyecto exportado corresponde solamente a ese tramo.
- **Resumen de problemas…** analiza los proyectos marcados, o la toma abierta si
  no hay ninguno marcado. Revisa las tomas completas, no solo el tramo de exportación.
  Muestra WAV faltantes, errores de lectura, silencio digital, nivel RMS menor de
  −60 dBFS y muestras cercanas al máximo (≥ −0,1 dBFS). Estas últimas son un indicio
  de posible saturación, no una prueba concluyente. Incluye observaciones de importación.

Las exportaciones incluyen `export.json` con notas, favorito, frecuencia, duración
y los límites originales del tramo en muestras. No se aplica la mezcla de escucha.

## Compatibilidad comprobada y límites

Versión **0.3.0**. Se analizaron 30 archivos reales `ZOOM H8 ProjectFile v001` de 10 312 bytes:
28 FIELD y 2 MUSIC, 44,1 kHz/24 bits, con 47 WAV disponibles.

- Se leen nombre, duración en muestras, frecuencia, profundidad y las 12 asignaciones de archivos del H8.
- En FIELD, se leen fecha y referencia temporal BWF y se resta el tiempo del primer WAV disponible del proyecto.
- En las muestras MUSIC, los WAV son tomas completas de idéntica duración, con inicio común en cero.
- Las carpetas se abren como **proyectos independientes**. La hora BWF no junta automáticamente grabaciones de distintas carpetas.
- **No se ha descifrado una tabla de regiones, recortes ni overdubs MUSIC.** Ninguna muestra recibida contiene varias tomas desplazadas por pista. Esta versión no promete reconstruir ese tipo de edición. Muestra ese límite al abrir y rechaza MUSIC de duración desigual.
- No se reproducen efectos, paneo o mezcla de la grabadora; los controles de escucha parten de valores propios.
- WAV adicionales no asignados por el `.h8prj` se notifican y no se añaden por orden de nombre.
- Los archivos `._*` de macOS no son audio y se ignoran.
- Si faltan WAV se pueden escuchar las pistas disponibles, pero se bloquea la exportación para evitar stems incompletos. Restaura los WAV en la carpeta correspondiente y vuelve a abrir el proyecto.
- La salida usa el dispositivo predeterminado de Windows; no requiere hardware Zoom conectado.

Los 7 archivos faltantes del material recibido están en:

| Proyecto | WAV faltantes |
|---|---|
| F260830_020 | Mic12.WAV |
| F260830_022 | Mic12.WAV, Tr2.WAV |
| F260830_023 | Mic12.WAV |
| F260830_024 | Mic12.WAV |
| F260830_028 | Mic12.WAV, Tr2.WAV |

Para ampliar el lector a ediciones MUSIC hace falta una muestra con posiciones conocidas, idealmente el mismo proyecto antes y después de desplazar o recortar una toma.

## Desarrollo y verificación

Python 3.12 de Windows:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\.venv\Scripts\python.exe main.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe tools\verify_ui.py
.\build.ps1
```

Pruebas: lectura de los 30 proyectos, detección de 7 archivos faltantes, posiciones/recortes/silencios con muestras sintéticas, mute/solo, exportaciones WAV/FLAC idénticas muestra a muestra al WAV real de prueba, cancelación y ausencia de sobrescritura.
La interfaz se comprobó con Qt en Windows; el motor de reproducción se probó con la salida predeterminada y monitor silenciado, incluida pausa y búsqueda.

La versión 0.2 añade pruebas de recorte muestra a muestra, persistencia de favorito/notas,
edición de plantillas, lotes con fallos/cancelación y detección de niveles. La estructura
de los `.rpp` y las referencias a sus stems están comprobadas; la apertura automática
en Reaper quedó pendiente porque la instancia de prueba se detuvo al escanear plugins.

Tecnologías: Python, PySide6/Qt, NumPy, SoundFile/libsndfile y sounddevice/PortAudio. Dependencias instaladas exclusivamente en `.venv`.

## Notas del formato

El mapa observado del archivo y las fuentes se documentan en `docs/formato-h8.md`.
