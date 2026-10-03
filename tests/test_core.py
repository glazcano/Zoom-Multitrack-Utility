from pathlib import Path
import struct
import tempfile
import threading
import unittest

import numpy as np
import soundfile as sf

from h8studio.core import (Clip, Track, Project, ProjectError, Renderer,
                           read_project, export_stems, ExportCancelled, bwf_reference)

ROOT = Path(__file__).resolve().parent.parent


class AudioTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def project(self):
        a = np.array([0.25, -0.5, 0.125, 0.0])[:, None]
        b = np.array([[0.5, -0.25], [0.125, 0.375]])
        sf.write(str(self.root/'a.wav'), a, 44100, subtype='PCM_24')
        sf.write(str(self.root/'b.wav'), b, 44100, subtype='PCM_24')
        tracks = [Track('Mono', [Clip(self.root/'a.wav', 3, 4, 1), Clip(self.root/'a.wav', 9, 2, 1, 1)]),
                  Track('Stereo', [Clip(self.root/'b.wav', 1, 2, 2)])]
        return Project('Fixture', self.root/'x.h8prj', 44100, 13, tracks)

    def test_sample_accurate_offsets_trim_silence_and_channels(self):
        p = self.project()
        r = Renderer(p)
        try:
            mono = r.track_block(p.tracks[0], 0, 13)
            np.testing.assert_array_equal(mono[:, 0], [0, 0, 0, .25, -.5, .125, 0, 0, 0, -.5, .125, 0, 0])
            stereo = r.track_block(p.tracks[1], 0, 13)
            self.assertEqual(stereo.shape, (13, 2))
            np.testing.assert_array_equal(stereo[1], [.5, -.25])
            # Rendering across block boundaries must be identical.
            np.testing.assert_array_equal(np.concatenate([r.mix(i, min(3, 13-i)) for i in range(0,13,3)]), r.mix(0,13))
            p.tracks[0].solo = True
            np.testing.assert_array_equal(r.mix(0,13), np.repeat(mono, 2, axis=1))
            p.tracks[0].mute = True
            self.assertFalse(r.mix(0,13).any())
        finally:
            r.close()

    def test_wav_flac_dry_lossless_equal_length_no_overwrite(self):
        p = self.project()
        p.tracks[0].mute, p.tracks[1].gain = True, 0.01
        for fmt in ('WAV', 'FLAC'):
            out = export_stems(p, self.root, fmt)
            reader = Renderer(p)
            try:
                for i, t in enumerate(p.tracks):
                    path = next(out.glob(f'{i+1:02d}_*.{fmt.lower()}'))
                    data, rate = sf.read(str(path), dtype='float64', always_2d=True)
                    self.assertEqual(rate, p.rate)
                    self.assertEqual(data.shape, (13, t.channels))
                    np.testing.assert_array_equal(data, reader.track_block(t, 0, 13))
            finally:
                reader.close()
        self.assertTrue((self.root/'Fixture_stems').is_dir())
        self.assertTrue((self.root/'Fixture_stems_2').is_dir())

    def test_cancel_and_missing_never_publish_partial_export(self):
        p = self.project()
        cancelled = threading.Event()
        cancelled.set()
        with self.assertRaises(ExportCancelled):
            export_stems(p, self.root, cancel=cancelled)
        self.assertFalse(list(self.root.glob('*stems*')))
        self.assertFalse(list(self.root.glob('.h8-export-*')))
        p.tracks[0].clips[0].missing = True
        with self.assertRaises(ProjectError):
            export_stems(p, self.root)

    def test_unknown_project_rejected(self):
        path = self.root/'bad.h8prj'
        path.write_bytes(b'Not H8')
        with self.assertRaises(ProjectError):
            read_project(path)

    def test_field_bwf_alignment_across_midnight(self):
        # Construct real RIFF/bext containers with distinct dates and sample clocks.
        # The second clip starts 0.5 s later, across midnight, not 24 hours earlier.
        for name, date, ref in [('Mic12.WAV', '2026-08-30', 86400*44100-11025),
                                ('Tr2.WAV', '2026-08-31', 11025)]:
            path = self.root/name
            sf.write(str(path), np.zeros((44100, 1)), 44100, subtype='PCM_24')
            raw = path.read_bytes()
            bext = bytearray(602)
            bext[320:330] = date.encode('ascii')
            struct.pack_into('<Q', bext, 338, ref)
            chunk = b'bext'+struct.pack('<I', len(bext))+bext
            new = bytearray(raw[:12]+chunk+raw[12:])
            struct.pack_into('<I', new, 4, len(new)-8)
            path.write_bytes(new)
        header = bytearray(10312)
        header[:32] = b'ZOOM H8 ProjectFile v001        '
        name = 'F_TEST'.encode('utf-16le')
        header[32:32+len(name)] = name
        struct.pack_into('<Q', header, 552, 44100)
        struct.pack_into('<II', header, 564, 44100, 24)
        for slot, name in [(0, 'Mic12.WAV'), (5, 'Tr2.WAV')]:
            value = name.encode('utf-16le')
            offset = 1496+slot*520
            header[offset:offset+len(value)] = value
        path = self.root/'F_TEST.h8prj'
        path.write_bytes(header)
        p = read_project(path)
        self.assertEqual([t.clips[0].start for t in p.tracks], [0, 22050])
        self.assertEqual(p.length, 66150)

    def test_real_corpus(self):
        paths = sorted((ROOT/'Projects').glob('*/*.h8prj'))
        if not paths:
            self.skipTest('Local corpus not present')
        missing, available = [], 0
        for path in paths:
            p = read_project(path)
            self.assertEqual(p.rate, 44100)
            for t in p.tracks:
                c = t.clips[0]
                if c.missing:
                    missing.append(str(c.path))
                else:
                    available += 1
                    self.assertEqual(c.frames, p.frames)
                    self.assertEqual(c.start, 0)
                    self.assertIsNotNone(bwf_reference(c.path))
        self.assertEqual(len(paths), 30)
        self.assertEqual(available, 47)
        self.assertEqual(len(missing), 7)

    def test_real_audio_wav_and_flac_roundtrip(self):
        path = ROOT/'Projects/F260830_027.zprj'
        if not path.exists():
            self.skipTest('Local corpus not present')
        p = read_project(path)
        for fmt in ('WAV', 'FLAC'):
            out = export_stems(p, self.root, fmt)
            for i, t in enumerate(p.tracks):
                source, _ = sf.read(str(t.clips[0].path), dtype='int32', always_2d=True)
                rendered, _ = sf.read(str(next(out.glob(f'{i+1:02d}_*.{fmt.lower()}'))), dtype='int32', always_2d=True)
                np.testing.assert_array_equal(source, rendered)


if __name__ == '__main__':
    unittest.main()
