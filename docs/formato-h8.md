# Observaciones del formato H8 v001

Este documento describe evidencia de las 30 muestras locales; no es una especificación oficial del formato propietario.

| Offset decimal | Tamaño | Interpretación observada |
|---|---|---|
| 0 | 32 | Firma ASCII `ZOOM H8 ProjectFile v001` y espacios |
| 32 | 520 | Nombre de proyecto UTF-16LE terminado en NUL |
| 552 | 8 | Duración en muestras, entero little endian; coincide con cada WAV disponible |
| 564 | 4 | Frecuencia: 44100 en todo el corpus |
| 568 | 4 | Profundidad: 24 en todo el corpus |
| 1496 | 12 × 520 | Asignaciones de nombres WAV; cadenas UTF-16LE de hasta 260 unidades |

En el corpus: Mic12 ocupa la entrada 0, Tr1 la 4 y Tr2 la 5. Se usa el nombre del archivo, sin inventar nombres de entradas no observadas. Los ceros al final de cada cadena no se interpretan como posiciones de clips.

Los 47 WAV disponibles tienen un chunk `bext`, formato PCM, relleno `PAD ` y audio `data`. Los 43 WAV FIELD tienen referencias BWF absolutas de hora del día. Los 4 MUSIC tienen referencia cero. Dentro de cada proyecto todas las pistas disponibles tienen igual referencia y duración. No hay evidencia en estas muestras para deducir offsets de regiones MUSIC.

Fuentes primarias:

- [Manual Zoom H8](https://zoomcorp.com/media/documents/E_H8_v2.pdf): organización de proyectos y archivos.
- [EBU Tech 3285](https://tech.ebu.ch/docs/tech/tech3285.pdf): BWF, fecha de origen y TimeReference de 64 bits en muestras desde medianoche.
- [SoundFile](https://python-soundfile.readthedocs.io/): lectura por bloques y codificación WAV/FLAC.

No se usan las fechas del sistema de archivos, ni se deduce la posición a partir del nombre de la toma. Los offsets y silencios del motor se calculan en muestras enteras. Los proyectos futuros con otra firma o tamaño se rechazan.
