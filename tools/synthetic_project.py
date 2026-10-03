"""Generate a non-private two-second H8 fixture for native CI and package checks."""
from pathlib import Path
import struct
import sys
import numpy as np
import soundfile as sf


def make_project(folder):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    rate, frames = 44100, 88200
    signal = .2*np.sin(2*np.pi*440*np.arange(frames)/rate)
    sf.write(str(folder/'Mic12.WAV'), np.column_stack((signal, signal*.5)), rate, subtype='PCM_24')
    sf.write(str(folder/'Tr1.WAV'), signal, rate, subtype='PCM_24')
    header = bytearray(10312)
    header[:32] = b'ZOOM H8 ProjectFile v001        '
    name = 'M_SYNTHETIC'.encode('utf-16le')
    header[32:32+len(name)] = name
    struct.pack_into('<Q', header, 552, frames)
    struct.pack_into('<II', header, 564, rate, 24)
    for slot, name in [(0, 'Mic12.WAV'), (4, 'Tr1.WAV')]:
        encoded = name.encode('utf-16le')
        offset = 1496+slot*520
        header[offset:offset+len(encoded)] = encoded
    path = folder/'M_SYNTHETIC.h8prj'
    path.write_bytes(header)
    return path


if __name__ == '__main__':
    print(make_project(sys.argv[1]))
