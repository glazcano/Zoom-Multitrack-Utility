import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
import soundfile as sf

from h8studio.core import (read_project, set_stereo_split, rename_track,
                           Renderer, export_stems, save_preparation, waveform, title_file)
from h8studio.workflows import export_batch, apply_template
from tools.synthetic_project import make_project


class ChannelTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.path = make_project(self.root/'source')
        self.project = read_project(self.path)

    def tearDown(self):
        self.temp.cleanup()

    def mix(self):
        renderer = Renderer(self.project)
        try:
            return renderer.mix(0, self.project.length)
        finally:
            renderer.close()

    def test_toggle_preserves_mix_cursor_independent_controls_and_labels(self):
        original = self.mix()
        original_bytes = self.path.read_bytes()
        set_stereo_split(self.project, True)
        self.assertEqual([t.channels for t in self.project.tracks], [1, 1, 1])
        np.testing.assert_array_equal(self.mix(), original)
        left, right, mono = self.project.tracks
        rename_track(self.project, left, 'Guitar')
        rename_track(self.project, right, 'Voice')
        left.solo = True
        isolated = self.mix()
        self.assertTrue(np.any(isolated[:, 0]))
        self.assertFalse(np.any(isolated[:, 1]))
        left.solo = False
        left.gain = .5
        set_stereo_split(self.project, False, 'Mic12.WAV')
        self.assertEqual(len(self.project.tracks), 2)
        np.testing.assert_array_equal(self.mix(), original)
        set_stereo_split(self.project, True, 'Mic12.WAV')
        self.assertIs(self.project.tracks[0], left)
        self.assertEqual(left.gain, .5)
        reopened = read_project(self.path)
        self.assertEqual([t.name for t in reopened.tracks], ['Guitar', 'Voice', 'Tr1'])
        self.assertEqual(self.path.read_bytes(), original_bytes)

    def test_exact_split_export_waveforms_ranges_and_reaper(self):
        set_stereo_split(self.project, True)
        apply_template(self.project, {'Mic12.L': 'Left guitar', 'Mic12.R': 'Right voice'})
        save_preparation(self.project, True, 'Keep this take', (123, 4567))
        original, _ = sf.read(str(self.root/'source/Mic12.WAV'), dtype='int32', always_2d=True)
        left_peaks = waveform(self.project.tracks[0].clips[0])
        right_peaks = waveform(self.project.tracks[1].clips[0])
        self.assertGreater(np.abs(left_peaks).max(), np.abs(right_peaks).max()*1.9)
        for fmt in ('WAV', 'FLAC'):
            output = export_stems(self.project, self.root, fmt, create_rpp=True)
            manifest = json.loads((output/'export.json').read_text(encoding='utf-8'))
            self.assertEqual(len(manifest['files']), 3)
            for channel in range(2):
                samples, _ = sf.read(str(output/manifest['files'][channel]), dtype='int32', always_2d=True)
                np.testing.assert_array_equal(samples, original[123:4567, channel:channel+1])
            rpp = (output/'Proyecto.rpp').read_text(encoding='utf-8')
            self.assertEqual(rpp.count('  <TRACK'), 3)
            self.assertIn('    VOLPAN 1 -1', rpp)
            self.assertIn('    VOLPAN 1 1', rpp)
            self.assertIn('Left guitar', rpp)

    def test_batch_override_does_not_change_saved_preferences(self):
        set_stereo_split(self.project, True)
        saved = title_file(self.path).read_bytes()
        for mode, count in ((None, 3), (False, 2), (True, 3)):
            result = export_batch([self.path], self.root, split_stereo=mode)
            self.assertFalse(result['failed'])
            output = Path(result['completed'][0]['output'])
            manifest = json.loads((output/'export.json').read_text(encoding='utf-8'))
            self.assertEqual(len(manifest['files']), count)
            self.assertEqual(title_file(self.path).read_bytes(), saved)

    def test_split_retains_offsets_source_trim_and_missing_audio(self):
        clip = self.project.tracks[0].clips[0]
        clip.start, clip.source_start, clip.frames = 17, 29, 200
        original = self.mix()
        set_stereo_split(self.project, True, persist=False)
        np.testing.assert_array_equal(self.mix(), original)
        for t in self.project.tracks[:2]:
            self.assertEqual((t.clips[0].start, t.clips[0].source_start, t.clips[0].frames), (17, 29, 200))
        self.assertFalse(title_file(self.path).exists())
