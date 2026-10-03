import json
from pathlib import Path
import shutil
import tempfile
import threading
import unittest
import numpy as np
import soundfile as sf
from h8studio.core import (read_project, save_preparation, export_stems, ProjectError,
                           Project, Track, Clip)
from h8studio.workflows import export_batch, apply_template, atomic_json, read_templates, analyze_project

ROOT = Path(__file__).resolve().parent.parent


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.folder = self.root/'sample'
        from tools.synthetic_project import make_project
        self.path = make_project(self.folder)
        self.project = read_project(self.path)

    def tearDown(self):
        self.temp.cleanup()

    def test_preferences_templates_and_exact_trim_roundtrip(self):
        before = self.path.read_bytes()
        save_preparation(self.project, True, 'Buena toma\nGuitarra y voz', (1000, 9000))
        apply_template(self.project, {'mic12': 'Guitarra acústica', 'tr1': 'Voz "principal"'})
        reopened = read_project(self.path)
        self.assertTrue(reopened.favorite)
        self.assertEqual(reopened.notes, 'Buena toma\nGuitarra y voz')
        self.assertEqual(reopened.export_range, (1000, 9000))
        self.assertEqual(reopened.tracks[0].name, 'Guitarra acústica')
        for fmt in ('WAV', 'FLAC'):
            out = export_stems(reopened, self.root, fmt, create_rpp=True)
            manifest = json.loads((out/'export.json').read_text(encoding='utf-8'))
            self.assertEqual(manifest['frames'], 8000)
            for track, filename in zip(reopened.tracks, manifest['files']):
                original, _ = sf.read(str(track.clips[0].path), dtype='int32', always_2d=True)
                exported, _ = sf.read(str(out/filename), dtype='int32', always_2d=True)
                np.testing.assert_array_equal(exported, original[1000:9000])
            rpp = (out/'Proyecto.rpp').read_text(encoding='utf-8')
            self.assertEqual(rpp.count('      POSITION 0'), 2)
            self.assertIn('Guitarra acústica', rpp)
            self.assertNotIn(str(self.root), rpp)
            depth = 0
            for line in rpp.splitlines():
                if line.strip().startswith('<'):
                    depth += 1
                if line.strip() == '>':
                    depth -= 1
                self.assertGreaterEqual(depth, 0)
            self.assertEqual(depth, 0)
        self.assertEqual(self.path.read_bytes(), before)

    def test_invalid_range_does_not_overwrite_preferences(self):
        save_preparation(self.project, True, 'keep', None)
        for region in ((3, 2), (-1, 4), (0, self.project.length+1), (1.5, 7)):
            with self.assertRaises(ProjectError):
                save_preparation(self.project, False, 'lose', region)
        p = read_project(self.path)
        self.assertEqual(p.notes, 'keep')
        self.assertTrue(p.favorite)

    def test_templates_edit_reopen_preserve_notes(self):
        path = self.root/'templates.json'
        atomic_json(path, {'Banda': {'Mic12': 'Ambiente'}})
        data = read_templates(path)
        data['Banda']['Mic12'] = 'Batería'
        atomic_json(path, data)
        save_preparation(self.project, True, 'nota', (10, 100))
        apply_template(self.project, read_templates(path)['Banda'])
        reopened = read_project(self.path)
        self.assertEqual(reopened.tracks[0].name, 'Batería')
        self.assertEqual(reopened.notes, 'nota')
        self.assertEqual(reopened.export_range, (10, 100))

    def test_batch_continues_after_failure_and_reports_pending_on_cancel(self):
        bad = self.root/'bad.h8prj'
        bad.write_bytes(b'unsupported')
        result = export_batch([bad, self.path], self.root)
        self.assertEqual(len(result['failed']), 1)
        self.assertEqual(len(result['completed']), 1)
        self.assertFalse(result['pending'])
        self.assertTrue((Path(result['folder'])/'lote.json').exists())
        event = threading.Event()
        event.set()
        cancelled = export_batch([self.path], self.root, cancel=event)
        self.assertTrue(cancelled['cancelled'])
        self.assertEqual(len(cancelled['pending']), 1)
        self.assertFalse(cancelled['completed'])

    def test_problem_detection_silence_near_clipping_missing(self):
        tracks = []
        for name, data in [('silence', np.zeros(128)), ('loud', np.ones(128)*.9999)]:
            path = self.root/(name+'.wav')
            sf.write(str(path), data, 44100, subtype='PCM_24')
            tracks.append(Track(name, [Clip(path, 0, 128, 1)]))
        tracks.append(Track('missing', [Clip(self.root/'missing.wav', 0, 128, 1, missing=True)]))
        p = Project('Analysis', self.path, 44100, 128, tracks)
        report = '\n'.join(analyze_project(p))
        self.assertIn('silencio digital', report)
        self.assertIn('posible saturación', report)
        self.assertIn('FALTA AUDIO', report)
