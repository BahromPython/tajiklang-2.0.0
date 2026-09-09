import unittest

from tajiklang import run_source
from tajiklang.syntax_next import normalize


class TestTajikLangNext(unittest.TestCase):
    def test_data_show_and_brace_condition_run(self):
        output: list[str] = []
        run_source(
            'дода ном <- "Баҳром"\n'
            'дода синну <- 16\n'
            'агар синну >= 16 {\n'
            '    нишон "Салом", ном\n'
            '} дигар {\n'
            '    нишон "хурд"\n'
            '}\n',
            output=output.append,
        )
        self.assertEqual(output, ["Салом Баҳром"])

    def test_update_is_explicit(self):
        output: list[str] = []
        run_source('дода ном <- "А"\nтағйир ном <- "Б"\nнишон ном\n', output=output.append)
        self.assertEqual(output, ["Б"])

    def test_unclosed_brace_is_explained(self):
        with self.assertRaises(ValueError):
            normalize('агар рост {\n    нишон "ҳа"\n')
