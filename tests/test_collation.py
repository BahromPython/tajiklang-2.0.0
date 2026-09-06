import unittest

from tajiklang import collation


class TestTajikAlphabet(unittest.TestCase):
    def test_the_alphabet_has_35_letters(self):
        self.assertEqual(len(collation.ALPHABET), 35)
        self.assertEqual(len(set(collation.ALPHABET)), 35)

    def test_tajik_letters_follow_their_base_letter(self):
        """ғ after г, ӣ after и, қ after к, ӯ after у, ҳ after х, ҷ after ч."""
        for base, extra in (("г", "ғ"), ("и", "ӣ"), ("к", "қ"), ("у", "ӯ"),
                            ("х", "ҳ"), ("ч", "ҷ")):
            with self.subTest(pair=(base, extra)):
                self.assertEqual(collation.compare(base, extra), -1)

    def test_code_point_order_would_be_wrong(self):
        """The bug this module exists to prevent."""
        self.assertGreater("ғ", "я")                      # raw Unicode
        self.assertEqual(collation.compare("ғ", "я"), -1)  # Tajik order

    def test_surnames_sort_the_way_a_reader_expects(self):
        names = ["Яқубов", "Ғафуров", "Аҳмадов", "Ҷӯраев", "Комилов"]
        self.assertEqual(
            sorted(names, key=collation.sort_key),
            ["Аҳмадов", "Ғафуров", "Комилов", "Ҷӯраев", "Яқубов"],
        )
        # what you would have got for free, and why it is not good enough
        self.assertEqual(sorted(names)[0], "Аҳмадов")
        self.assertEqual(sorted(names)[-1], "Ҷӯраев")

    def test_equal_strings(self):
        self.assertEqual(collation.compare("ном", "ном"), 0)

    def test_a_prefix_sorts_first(self):
        self.assertEqual(collation.compare("ном", "номи"), -1)

    def test_upper_and_lower_case_stay_adjacent(self):
        self.assertEqual(collation.compare("Анор", "анор"), -1)
        self.assertEqual(collation.compare("Анор", "бед"), -1)

    def test_non_letters_sort_before_letters(self):
        self.assertEqual(collation.compare("1", "а"), -1)
        self.assertEqual(collation.compare(" ", "а"), -1)


if __name__ == "__main__":
    unittest.main()
