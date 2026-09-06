import unicodedata
import unittest

from tajiklang.errors import LexerError
from tajiklang.lexer import Lexer
from tajiklang.tokens import TokenType


def types(source):
    return [t.type for t in Lexer(source).tokenize()]


def values(source):
    return [t.value for t in Lexer(source).tokenize()]


class TestLexer(unittest.TestCase):
    def test_hello_world(self):
        self.assertEqual(
            types('навис("Салом")'),
            [
                TokenType.IDENT,
                TokenType.LPAREN,
                TokenType.STRING,
                TokenType.RPAREN,
                TokenType.NEWLINE,
                TokenType.EOF,
            ],
        )

    def test_tajik_identifier(self):
        tokens = Lexer("ҳарорат").tokenize()
        self.assertEqual(tokens[0].type, TokenType.IDENT)
        self.assertEqual(tokens[0].value, "ҳарорат")

    def test_identifier_with_underscore_and_digits(self):
        self.assertEqual(Lexer("синну_сол2").tokenize()[0].value, "синну_сол2")

    def test_nfd_and_nfc_produce_the_same_identifier(self):
        """ӣ typed as one code point and as и + macron must be one name."""
        nfc = unicodedata.normalize("NFC", "мебошӣ")
        nfd = unicodedata.normalize("NFD", "мебошӣ")
        self.assertNotEqual(nfc, nfd)  # the raw text really does differ
        self.assertEqual(
            Lexer(nfc).tokenize()[0].value, Lexer(nfd).tokenize()[0].value
        )

    def test_integers_and_floats(self):
        self.assertEqual(values("10")[0], 10)
        self.assertEqual(values("3.5")[0], 3.5)

    def test_comments_are_skipped(self):
        self.assertEqual(types("# танҳо шарҳ\n"), [TokenType.NEWLINE, TokenType.EOF])

    def test_string_escapes(self):
        source = '"сатр' + chr(92) * 2 + 'nнав"'
        self.assertEqual(values(source)[0], "сатр" + chr(92) + "nнав")

    def test_positions_are_one_based(self):
        token = Lexer('навис("Салом")').tokenize()[0]
        self.assertEqual((token.line, token.column), (1, 1))

    def test_unterminated_string_is_an_error(self):
        with self.assertRaises(LexerError) as ctx:
            Lexer('навис("Салом)').tokenize()
        self.assertIn("пӯшида нашудааст", ctx.exception.message)

    def test_unknown_character_is_an_error(self):
        with self.assertRaises(LexerError):
            Lexer("навис$").tokenize()


class TestOperators(unittest.TestCase):
    def test_arithmetic_operators(self):
        self.assertEqual(
            types("1 + 2 - 3 * 4 / 5 % 6")[:11],
            [
                TokenType.NUMBER,
                TokenType.PLUS,
                TokenType.NUMBER,
                TokenType.MINUS,
                TokenType.NUMBER,
                TokenType.STAR,
                TokenType.NUMBER,
                TokenType.SLASH,
                TokenType.NUMBER,
                TokenType.PERCENT,
                TokenType.NUMBER,
            ],
        )

    def test_declaration_tokens(self):
        self.assertEqual(
            types("бигзор x = 10"),
            [
                TokenType.LET,
                TokenType.IDENT,
                TokenType.ASSIGN,
                TokenType.NUMBER,
                TokenType.NEWLINE,
                TokenType.EOF,
            ],
        )

    def test_comparison_operators(self):
        pairs = [
            ("==", TokenType.EQ),
            ("!=", TokenType.NEQ),
            ("<", TokenType.LT),
            (">", TokenType.GT),
            ("<=", TokenType.LTE),
            (">=", TokenType.GTE),
        ]
        for text, expected in pairs:
            with self.subTest(operator=text):
                self.assertEqual(types("1 " + text + " 2")[1], expected)

    def test_two_char_operators_are_not_split(self):
        """`<=` must be one token, never `<` followed by `=`."""
        self.assertEqual(len(types("1 <= 2")), 5)  # NUMBER LTE NUMBER NEWLINE EOF

    def test_logical_keywords(self):
        self.assertEqual(
            types("рост ва дурӯғ ё не холӣ")[:6],
            [
                TokenType.TRUE,
                TokenType.AND,
                TokenType.FALSE,
                TokenType.OR,
                TokenType.NOT,
                TokenType.NULL,
            ],
        )

    def test_operators_from_other_languages_are_redirected(self):
        for source, expected in (
            ("рост && дурӯғ", '"ва"'),
            ("рост || дурӯғ", '"ё"'),
            ("!рост", '"не"'),
            ("1 === 1", '"=="'),
        ):
            with self.subTest(source=source):
                with self.assertRaises(LexerError) as ctx:
                    Lexer(source).tokenize()
                self.assertIn(expected, ctx.exception.hint)


class TestIndentation(unittest.TestCase):
    def test_a_block_produces_indent_and_dedent(self):
        source = 'агар x:\n    навис("а")\nнавис("б")\n'
        kinds = [t for t in types(source) if t in (TokenType.INDENT, TokenType.DEDENT)]
        self.assertEqual(kinds, [TokenType.INDENT, TokenType.DEDENT])

    def test_nested_blocks(self):
        source = "агар x:\n    агар y:\n        навис(1)\n"
        kinds = [t for t in types(source) if t in (TokenType.INDENT, TokenType.DEDENT)]
        self.assertEqual(
            kinds,
            [TokenType.INDENT, TokenType.INDENT, TokenType.DEDENT, TokenType.DEDENT],
        )

    def test_blocks_open_at_end_of_file_are_closed(self):
        """No DEDENT here would leave the parser waiting forever."""
        tokens = types("агар x:\n    навис(1)")
        self.assertEqual(tokens[-2], TokenType.DEDENT)
        self.assertEqual(tokens[-1], TokenType.EOF)

    def test_closing_two_levels_at_once(self):
        source = "агар x:\n    агар y:\n        навис(1)\nнавис(2)\n"
        kinds = [t for t in types(source) if t is TokenType.DEDENT]
        self.assertEqual(len(kinds), 2)

    def test_blank_lines_do_not_affect_indentation(self):
        source = 'агар x:\n\n    навис(1)\n\n    навис(2)\n'
        kinds = [t for t in types(source) if t in (TokenType.INDENT, TokenType.DEDENT)]
        self.assertEqual(kinds, [TokenType.INDENT, TokenType.DEDENT])

    def test_comment_lines_do_not_affect_indentation(self):
        source = 'агар x:\n# шарҳ дар канор\n    навис(1)\n'
        kinds = [t for t in types(source) if t in (TokenType.INDENT, TokenType.DEDENT)]
        self.assertEqual(kinds, [TokenType.INDENT, TokenType.DEDENT])

    def test_tabs_are_rejected(self):
        with self.assertRaises(LexerError) as ctx:
            Lexer("агар x:\n\tнавис(1)\n").tokenize()
        self.assertIn("tab", ctx.exception.message)

    def test_indent_must_be_exactly_four_spaces(self):
        for width in (2, 3, 8):
            with self.subTest(width=width):
                with self.assertRaises(LexerError) as ctx:
                    Lexer("агар x:\n" + " " * width + "навис(1)\n").tokenize()
                self.assertIn("Фосилаи нодуруст", ctx.exception.message)

    def test_dedent_must_land_on_an_open_level(self):
        source = "агар x:\n    агар y:\n        навис(1)\n      навис(2)\n"
        with self.assertRaises(LexerError) as ctx:
            Lexer(source).tokenize()
        self.assertIn("мувофиқ намеояд", ctx.exception.message)


class TestImplicitLineJoining(unittest.TestCase):
    def test_a_list_may_span_lines(self):
        source = "бигзор х = [\n    1,\n    2,\n]\n"
        self.assertEqual(types(source).count(TokenType.NEWLINE), 1)

    def test_indentation_inside_brackets_means_nothing(self):
        """The 4-space rule must not apply to a wrapped literal."""
        source = "бигзор х = [\n  1,\n      2,\n]\n"
        kinds = [t for t in types(source) if t in (TokenType.INDENT, TokenType.DEDENT)]
        self.assertEqual(kinds, [])

    def test_a_call_may_span_lines(self):
        source = 'навис(\n    "а",\n    "б",\n)\n'
        self.assertEqual(types(source).count(TokenType.NEWLINE), 1)

    def test_newlines_matter_again_after_the_bracket_closes(self):
        source = "бигзор х = [1]\nбигзор у = 2\n"
        self.assertEqual(types(source).count(TokenType.NEWLINE), 2)


class TestReservedWords(unittest.TestCase):
    def test_implemented_keyword_becomes_its_own_token(self):
        self.assertEqual(Lexer("бигзор").tokenize()[0].type, TokenType.LET)

    def test_every_reserved_word_is_now_implemented(self):
        """The staged-rollout mechanism still exists; nothing is waiting."""
        from tajiklang.tokens import KEYWORD_TOKENS, KEYWORD_VERSIONS, KEYWORDS

        self.assertEqual(KEYWORD_VERSIONS, {})
        self.assertEqual(set(KEYWORDS), set(KEYWORD_TOKENS))

    def test_common_tajik_words_are_left_alone(self):
        """`синф` and `худ` are words a school program needs — see tokens.py."""
        for word in ("синф", "худ", "ном", "баҳо", "давра"):
            with self.subTest(word=word):
                self.assertEqual(
                    Lexer(word).tokenize()[0].type, TokenType.IDENT
                )

    def test_the_class_keyword(self):
        self.assertEqual(Lexer("қолиб").tokenize()[0].type, TokenType.CLASS)
        self.assertEqual(Lexer("мерос").tokenize()[0].type, TokenType.INHERITS)

    def test_implemented_keywords_are_not_rejected(self):
        for word in ("барои", "функсия", "то_вақте", "баргардон", "ворид",
                     "шикан", "давом", "кӯшиш", "хато", "худ"):
            with self.subTest(word=word):
                Lexer(word).tokenize()   # must not raise


if __name__ == "__main__":
    unittest.main()
