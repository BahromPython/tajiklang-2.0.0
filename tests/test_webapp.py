import tempfile
import unittest
from pathlib import Path

from tajiklang.webapp import WebApp


class TestTajikWebApp(unittest.TestCase):
    def test_a_button_runs_ordinary_tajiklang_and_renders_again(self):
        source = '''ворид саҳифа
бигзор шумор = 0

функсия зиёд_кун():
    шумор += 1
    саҳифа.тоза_кун()
    саҳифа.нависед(саҳифа.матн("Шумор:", шумор), саҳифа.тугма("Боз", зиёд_кун))

саҳифа.нависед(саҳифа.матн("Шумор:", шумор), саҳифа.тугма("Боз", зиёд_кун))
'''
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "app.tj"
            path.write_text(source, encoding="utf-8")
            app = WebApp(path)
            first = app.page()
            second = app.action("амал_1")
        self.assertIn("Шумор: 0", first)
        self.assertIn("Шумор: 1", second)
        self.assertIn("data-tajik-action=\"амал_2\"", second)


if __name__ == "__main__":
    unittest.main()
