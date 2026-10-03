from pathlib import Path
import hashlib
import json
import shutil
import tempfile
import threading
import unittest
import numpy as np
import soundfile as sf
import sounddevice as sd

from h8studio.audio import Player
from h8studio.core import read_project, set_stereo_split, Renderer, export_stems, save_preparation, ProjectError, ExportCancelled
from h8studio.preferences import Preferences, library_entry, matches_entry
from h8studio.relink import find_candidates, link_media
from tools.synthetic_project import make_project
from tools.release_draft import release_assets, validate_existing


class PreparationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.path = make_project(self.root/'take')
        self.project = read_project(self.path)

    def tearDown(self):
        self.temp.cleanup()

    def test_centered_monitor_meters_and_dry_stems(self):
        set_stereo_split(self.project, True)
        left, right, mono = self.project.tracks
        left.solo = True
        renderer = Renderer(self.project)
        try:
            stereo = renderer.mix(0, 1024)
            centered = renderer.mix(0, 1024, center_mono=True)
            self.assertFalse(np.any(stereo[:, 1]))
            np.testing.assert_array_equal(centered[:, 0], centered[:, 1])
            np.testing.assert_array_equal(centered[:, 0], stereo[:, 0])
            left.mute = True
            self.assertFalse(np.any(renderer.mix(0, 1024, center_mono=True)))
            self.assertGreater(left.peak, .1)
            self.assertGreater(right.peak, .05)
        finally:
            renderer.close()
        output = export_stems(self.project, self.root)
        samples, _ = sf.read(str(next(output.glob('01_*.wav'))))
        self.assertGreater(np.abs(samples).max(), .1)

    def test_loop_crosses_multiple_boundaries_exactly(self):
        player = Player()
        player.load(self.project)
        try:
            player.master = 1
            player.loop = True
            self.project.export_range = (15, 22)
            player.position = 20
            expected = player.renderer.mix(15, 7)
            output = np.zeros((23, 2), dtype=np.float32)
            player.callback(output, 23, None, False)
            indices = (np.arange(23)+5) % 7
            np.testing.assert_allclose(output, expected[indices], atol=1e-7)
            self.assertEqual(player.position, 15)
            player.position = 500
            player.callback(output, 23, None, False)
            np.testing.assert_allclose(output, expected[np.arange(23)%7], atol=1e-7)
            self.project.export_range = None
            player.position = self.project.length
            with self.assertRaises(sd.CallbackStop):
                player.callback(output, 23, None, False)
            self.assertEqual(player.error, '')
        finally:
            player.close()

    def test_missing_media_candidates_require_selection_and_persist(self):
        save_preparation(self.project, True, 'Good guitar take', (10, 100))
        recovery = self.root/'recover'
        for name in ('a', 'b'):
            (recovery/name).mkdir(parents=True)
            shutil.copy2(self.path.parent/'Mic12.WAV', recovery/name/'Mic12.WAV')
        (recovery/'bad').mkdir()
        sf.write(str(recovery/'bad/Mic12.WAV'), np.zeros((10, 2)), 48000)
        (self.path.parent/'Mic12.WAV').unlink()
        project = read_project(self.path)
        self.assertTrue(library_entry(self.path)['problem'])
        matches = find_candidates(project, recovery)
        self.assertEqual(len(matches['mic12.wav']), 2)
        self.assertTrue(read_project(self.path).tracks[0].clips[0].missing)
        before = self.path.read_bytes()
        with self.assertRaises(ProjectError):
            link_media(project, {'mic12.wav': recovery/'bad/Mic12.WAV'})
        reopened = link_media(project, {'mic12.wav': matches['mic12.wav'][1]['path']})
        self.assertFalse(reopened.tracks[0].clips[0].missing)
        self.assertEqual(reopened.notes, 'Good guitar take')
        self.assertEqual(reopened.export_range, (10, 100))
        self.assertFalse(read_project(self.path).tracks[0].clips[0].missing)
        self.assertFalse(library_entry(self.path)['problem'])
        self.assertEqual(self.path.read_bytes(), before)
        Path(matches['mic12.wav'][1]['path']).unlink()
        self.assertTrue(read_project(self.path).tracks[0].clips[0].missing)
        cancelled = threading.Event()
        cancelled.set()
        with self.assertRaises(ExportCancelled):
            find_candidates(read_project(self.path), recovery, cancelled)

    def test_presets_roundtrip_edit_delete_and_validation(self):
        path = self.root/'prefs.json'
        prefs = Preferences(path)
        prefs.put_preset('Delivery', dict(format='FLAC', channels=2, portable=True, naming='project_track'))
        loaded = Preferences(path)
        self.assertEqual(loaded.presets()['Delivery']['format'], 'FLAC')
        loaded.put_preset('Delivery', dict(format='WAV'))
        self.assertEqual(Preferences(path).presets()['Delivery']['format'], 'WAV')
        with self.assertRaises(ProjectError):
            loaded.put_preset('Invalid', dict(channels=9))
        loaded.delete_preset('Delivery')
        self.assertEqual(Preferences(path).presets(), {})
        path.write_text('not json', encoding='utf-8')
        self.assertTrue(Preferences(path).error)

    def test_search_notes_favorites_and_missing(self):
        save_preparation(self.project, True, 'Acoustic guitar', None)
        entry = library_entry(self.path)
        self.assertTrue(matches_entry(entry, 'GUITAR', 1))
        self.assertFalse(matches_entry(entry, 'guitar', 2))
        self.assertFalse(matches_entry(entry, 'drums', 0))
        (self.path.parent/'Tr1.WAV').unlink()
        self.assertTrue(matches_entry(library_entry(self.path), 'acoustic', 2))

    def test_delivery_can_move_without_originals(self):
        save_preparation(self.project, True, 'A useful note', (123, 4567))
        for fmt in ('WAV', 'FLAC'):
            output = export_stems(self.project, self.root, fmt, portable=True, create_rpp=False, naming='project_track')
            moved = self.root/('moved-'+fmt)
            output.rename(moved)
            self.assertIn('A useful note', (moved/'Notes.txt').read_text(encoding='utf-8'))
            manifest = json.loads((moved/'export.json').read_text(encoding='utf-8'))
            self.assertNotIn(str(self.root), json.dumps(manifest))
            rpp = (moved/'Proyecto.rpp').read_text(encoding='utf-8')
            for name in manifest['files']:
                self.assertTrue(name.startswith('M_SYNTHETIC_'))
                self.assertIn(name, rpp)
                self.assertEqual(sf.info(str(moved/name)).frames, 4444)
            for line in (moved/'SHA256SUMS.txt').read_text().splitlines():
                digest, name = line.split('  ', 1)
                self.assertEqual(hashlib.sha256((moved/name).read_bytes()).hexdigest(), digest)


class ReleaseTests(unittest.TestCase):
    def test_assets_require_all_platforms_and_valid_checksums(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for platform in ('windows-x86_64.zip', 'fedora-x86_64.tar.gz', 'macos-arm64.zip', 'macos-x86_64.zip'):
                archive = root/f'H8Studio-0.5.0-{platform}'
                archive.write_bytes(b'package')
                archive.with_name(archive.name+'.sha256').write_text(hashlib.sha256(b'package').hexdigest()+'  '+archive.name+'\n')
            self.assertEqual(len(release_assets(root, '0.5.0')), 8)
            archive.write_bytes(b'corrupted')
            with self.assertRaises(ValueError):
                release_assets(root, '0.5.0')
            with self.assertRaises(ValueError):
                release_assets(root, '0.6.0')

    def test_published_or_different_commit_drafts_are_not_overwritten(self):
        validate_existing(dict(isDraft=True, targetCommitish='abc'), 'abc')
        for release in (dict(isDraft=False, targetCommitish='abc'), dict(isDraft=True, targetCommitish='other')):
            with self.assertRaises(ValueError):
                validate_existing(release, 'abc')
