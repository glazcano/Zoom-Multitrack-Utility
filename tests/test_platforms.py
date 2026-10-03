from pathlib import Path
import tempfile
import unittest
from h8studio.platforms import project_files
from h8studio.core import read_project
from tools.synthetic_project import make_project


class PortableFilesTests(unittest.TestCase):
    def test_case_insensitive_extension_and_audio_lookup(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = make_project(root/'Toma con espacios y acentos')
            path.rename(path.with_suffix('.H8PRJ'))
            audio = path.parent/'Mic12.WAV'
            audio.rename(path.parent/'mic12.wav')
            (path.parent/'._extra.h8prj').write_bytes(b'AppleDouble')
            self.assertEqual(len(project_files(root, recursive=True)), 1)
            project = read_project(path.parent)
            self.assertFalse(project.tracks[0].clips[0].missing)
            self.assertEqual(project.frames, 88200)
