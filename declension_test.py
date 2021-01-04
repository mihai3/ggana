import unittest
from declension import Declension, DeclensionResult

class DeclensionTest(unittest.TestCase):
    def test_lemmatizer(self):
        with Declension() as d:
            self.assertEqual(d.lemmatize("Chinesinnen"), "Chinesin")
            self.assertIsNone(d.lemmatize("Erfundeneswortdasesnichtgibt"))

    def test_declensions(self):
        with Declension() as d:
            self.assertEqual(d.get_valid("Chinesinnen")[0].is_plural, True)
            self.assertGreaterEqual(len(d.get_valid("Fenster")), 5) # w/o "den Fenstern"
            self.assertGreaterEqual(len(d.get_valid("Fenstern")), 1)

    def test_nocase(self):
        with Declension() as d:
            self.assertEqual(d.lemmatize("computer"), "Computer")

    def test_genders(self):
        with Declension() as d:
            self.assertSetEqual(d.genders("Virus"), set(("MAS", "NEU")))

if __name__ == "__main__":
    unittest.main()