"""Худсозӣ — the language compiles itself.

`худсоз/` holds a TajikLang compiler written in TajikLang. It reads `.tj` files
and emits JavaScript. That gives three generations of the same compiler:

    насли 0   the reference implementation runs тарҷумон.tj  →  .js
    насли 1   Node runs those .js files on the same .tj sources  →  .js
    насли 2   Node runs *those* .js files on the same sources  →  .js

Two things must hold, and each catches a different class of bug:

*   насли 1 == насли 2 — the compiler is a fixed point. If the compiler had a
    bug that changed its own output, the second pass would drift from the
    first. This is the classic bootstrap test.

*   насли 0 == насли 1 — the two implementations agree exactly. The compiler
    itself is the test program, so any place where the Tajik-written lexer and
    the reference lexer disagree shows up as a byte difference. Writing the
    `\\r` escape as a literal `r` was found exactly this way: it made the
    letter r behave as a separator, and `ба_javascript` lexed as two names.

Skipped when Node is not installed; the reference implementation never needs
it, so a contributor without Node can still run the suite.
"""

import shutil
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ХУДСОЗ = ROOT / "худсоз"

# The compiler's own sources, and the two hand-written runtime files the
# generated code needs. Everything else in худсоз/ is an example or a test.
МАНБАЪҲО = ("лексер.tj", "тарҷумон.tj", "худсозӣ.tj")
ЁРИРАСОНҲО = ("асос.js", "файл.js")

NODE = shutil.which("node")


def _run(command: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )


@unittest.skipUnless(NODE, "Node.js насб нашудааст")
class TestBootstrap(unittest.TestCase):
    """Three generations, and the bytes have to line up."""

    @classmethod
    def setUpClass(cls) -> None:
        import tempfile

        cls._temp = tempfile.TemporaryDirectory()
        cls.кор = Path(cls._temp.name)

        for name in МАНБАЪҲО + ЁРИРАСОНҲО:
            shutil.copy2(ХУДСОЗ / name, cls.кор / name)

        # насли 0 — the reference implementation compiles the compiler.
        нол = _run([sys.executable, "-m", "tajiklang", "худсозӣ.tj"], cls.кор)
        if нол.returncode != 0:
            raise AssertionError("насли 0 иҷро нашуд:\n" + нол.stdout + нол.stderr)
        cls.насли0 = cls._snapshot()

        # насли 1 and насли 2 — the compiler compiles itself, twice.
        for насл in (1, 2):
            натиҷа = _run([NODE, "худсозӣ.js"], cls.кор)
            if натиҷа.returncode != 0:
                raise AssertionError(
                    f"насли {насл} иҷро нашуд:\n" + натиҷа.stdout + натиҷа.stderr
                )
            setattr(cls, f"насли{насл}", cls._snapshot())

    @classmethod
    def _snapshot(cls) -> dict[str, str]:
        return {
            name.replace(".tj", ".js"): (cls.кор / name.replace(".tj", ".js"))
            .read_text(encoding="utf-8")
            for name in МАНБАЪҲО
        }

    @classmethod
    def tearDownClass(cls) -> None:
        cls._temp.cleanup()

    def test_the_compiler_is_a_fixed_point(self):
        """Compiling the compiler with itself changes nothing."""
        for name in self.насли1:
            with self.subTest(файл=name):
                self.assertEqual(self.насли1[name], self.насли2[name])

    def test_both_implementations_agree(self):
        """Node and the reference implementation emit identical bytes."""
        for name in self.насли0:
            with self.subTest(файл=name):
                self.assertEqual(self.насли0[name], self.насли1[name])

    def test_the_output_is_not_empty(self):
        """A compiler that emits only a header would pass the tests above."""
        for name, text in self.насли1.items():
            with self.subTest(файл=name):
                self.assertGreater(len(text), 1000, name)
                self.assertIn("module.exports", text)


@unittest.skipUnless(NODE, "Node.js насб нашудааст")
class TestGeneratedCodeMatchesTheReference(unittest.TestCase):
    """A student's program must mean the same thing in either runtime."""

    def test_a_program_gives_the_same_output_in_both(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            кор = Path(tmp)
            for name in МАНБАЪҲО + ЁРИРАСОНҲО + ("намуна.tj", "санҷиш.tj"):
                shutil.copy2(ХУДСОЗ / name, кор / name)

            аз_асос = _run(
                [sys.executable, "-m", "tajiklang", "намуна.tj"], кор
            )
            self.assertEqual(аз_асос.returncode, 0, аз_асос.stderr)

            сохтан = _run(
                [sys.executable, "-m", "tajiklang", "санҷиш.tj"], кор
            )
            self.assertEqual(сохтан.returncode, 0, сохтан.stderr)

            аз_js = _run([NODE, "намуна.js"], кор)
            self.assertEqual(аз_js.returncode, 0, аз_js.stderr)

            self.assertEqual(
                аз_асос.stdout.replace("\r\n", "\n"),
                аз_js.stdout.replace("\r\n", "\n"),
            )

    def test_exact_arithmetic_survives_the_translation(self):
        """JavaScript has no decimals. 0.1 + 0.2 must still be 0.3."""
        with_node = _run(
            [
                NODE,
                "-e",
                "const r=require('./асос.js');"
                "r.__навис(r.__ҷамъ(0.1,0.2));"
                "r.__навис(r.__баробар(r.__ҷамъ(0.1,0.2),0.3));",
            ],
            ХУДСОЗ,
        )
        self.assertEqual(with_node.returncode, 0, with_node.stderr)
        self.assertEqual(with_node.stdout.split(), ["0.3", "рост"])

    def test_tajik_letters_keep_their_own_order(self):
        """ғ comes after г, not after я — in JavaScript too."""
        натиҷа = _run(
            [
                NODE,
                "-e",
                "const r=require('./асос.js');"
                "r.__навис(r.__тартиб(['ям','ғоз','гул','ӯзум','анор']));",
            ],
            ХУДСОЗ,
        )
        self.assertEqual(натиҷа.returncode, 0, натиҷа.stderr)
        self.assertIn('["анор", "гул", "ғоз", "ӯзум", "ям"]', натиҷа.stdout)

    def test_nothing_is_true_by_accident(self):
        """`агар 5:` is an error in TajikLang, and stays one here."""
        натиҷа = _run(
            [NODE, "-e", "require('./асос.js').__шарт(5)"], ХУДСОЗ
        )
        self.assertNotEqual(натиҷа.returncode, 0)
        self.assertIn("рост ё дурӯғ", натиҷа.stderr)


if __name__ == "__main__":
    unittest.main()
