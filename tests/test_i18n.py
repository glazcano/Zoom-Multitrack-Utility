import string
import unittest
from h8studio.i18n import EN, language, set_language, tr


class TranslationTests(unittest.TestCase):
    def tearDown(self):
        set_language('en')

    def test_language_fallback_and_dynamic_messages(self):
        set_language('invalid')
        self.assertEqual(language(), 'en')
        self.assertEqual(tr('Pista guardada: {0}. Los stems usarán esta etiqueta.', 'Guitarra'),
                         'Track saved: Guitarra. Stems will use this label.')
        set_language('es')
        self.assertEqual(tr('Pista guardada: {0}. Los stems usarán esta etiqueta.', 'Guitar'),
                         'Pista guardada: Guitar. Los stems usarán esta etiqueta.')

    def test_translations_preserve_format_fields(self):
        formatter = string.Formatter()
        def fields(text):
            return sorted((field, spec, conversion) for _, field, spec, conversion in formatter.parse(text) if field is not None)
        for source, translated in EN.items():
            with self.subTest(source=source):
                self.assertEqual(fields(source), fields(translated))
