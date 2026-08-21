import unittest

from commoner_analyse.names import HONORIFICS, normalize_name, slugify


class NormalizeNameTests(unittest.TestCase):

    def test_word_order_does_not_change_the_key(self):
        """The whole reason this function sorts tokens.

        Indian records write a name in whatever order the clerk chose. Four
        sibling implementations lowercase and strip punctuation and stop, so
        they return two keys for one person and a join drops the row.
        """
        self.assertEqual(normalize_name("P V Joshi"), normalize_name("Joshi P V"))
        self.assertEqual(normalize_name("Joshi, Shri P.V."), normalize_name("P V Joshi"))

    def test_honorifics_go(self):
        for written in ("Shri Ram Nath", "Dr. Ram Nath", "Smt Ram Nath", "Hon'ble Ram Nath"):
            with self.subTest(written=written):
                self.assertEqual(normalize_name(written), "nath ram")

    def test_an_extra_honorific_needs_no_second_copy_of_the_function(self):
        self.assertEqual(normalize_name("Rev Fr John Doe"), "doe fr john rev")
        self.assertEqual(
            normalize_name("Rev Fr John Doe", extra_honorifics=["Rev", "Fr"]),
            "doe john",
        )

    def test_empty_and_punctuation_only(self):
        self.assertEqual(normalize_name(""), "")
        self.assertEqual(normalize_name("..."), "")

    def test_punctuation_and_case_do_not_change_the_key(self):
        self.assertEqual(normalize_name("B.R. AMBEDKAR"), normalize_name("b r ambedkar"))


class SlugifyTests(unittest.TestCase):

    def test_word_order_is_preserved(self):
        """A slug is read by a person. `p_v_joshi` beats an alphabetised key."""
        self.assertEqual(slugify("Shri P.V. Joshi"), "p_v_joshi")
        self.assertNotEqual(slugify("P V Joshi"), slugify("Joshi P V"))

    def test_it_strips_the_same_honorifics(self):
        self.assertEqual(slugify("Dr. Ambedkar, B.R."), "ambedkar_b_r")

    def test_empty(self):
        self.assertEqual(slugify(""), "")


class ReExportTests(unittest.TestCase):

    def test_entities_still_exposes_both(self):
        """Callers and tests import these from `entities`. Keep that working."""
        from commoner_analyse import entities
        self.assertIs(entities.normalize_name, normalize_name)
        self.assertIs(entities.slugify, slugify)

    def test_the_honorific_list_has_one_home(self):
        from commoner_analyse import entities
        self.assertIs(entities.HONORIFICS, HONORIFICS)


if __name__ == "__main__":
    unittest.main()
