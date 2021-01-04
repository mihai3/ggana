import unittest
import main

class GganaTest(unittest.TestCase):
    
    def compare(self, io_string, ignore_case=False):
        if "|" in io_string:
            i, o = io_string.split("|")
        else:
            i, o = io_string, io_string

        result = main.get_sentence(i)
        if ignore_case:
            o, result = o.lower(), result.lower()
            
        self.assertEqual(o, result)
    
    def test_kein(self):
        self.compare("das hotel ist keinen gebäude|das Hotel ist kein Gebäude")
    
    def test_dependent_nouns(self):
        self.compare("in diese Teil der Welt wird diese Teil für die Maschine gar nicht hergestellt|in diesem Teil der Welt wird dieser Teil für die Maschine gar nicht hergestellt")

    def test_subject(self):
        self.compare("alles wörter werden zufällig gewählt|alle Wörter werden zufällig gewählt")

    def test_adverb(self):
        self.compare("ich würd gern wissen ob jetzt auch das Aktionen richtig funktionieren|ich würd gern wissen ob jetzt auch die Aktionen richtig funktionieren")

    #def test_compound(self):
    #    self.compare("das satzbau|der Satzbau")

    def test_sicher(self):
        self.compare("ja, ich hab auch diese Idee, die sicher nach hinten losgehen wird, gehabt")

    def test_viel(self):
        self.compare("viel Erfolg mit Wachstube")

    def test_meist(self):
        self.compare("die meisten wörter dort sind halt wirklich dumm gebaut|die meisten Wörter dort sind halt wirklich dumm gebaut")

    def test_nouns_with_dash(self):
        self.compare("Wach-Stube, Wachs-Tube")

    def test_adverb2(self):
        self.compare("nimm so viele Buchstaben von hinten wie möglich")

    def test_predicate(self):
        self.compare("es ist eh der richtige Monat für Bugs")

    def test_dependent_sentence(self):
        self.compare("wenn du dir ein Beispiel von einer Sprache wünschst, die nicht kontextfrei ist, kriegst du nur Symbolsalat")

    def test_no_contractions(self):
        self.compare("wie lange dauerts eigentlich noch bis zu dem Punkt, an dem du den Hut draufhaust und dich stattdessen ansäufst?", ignore_case=True)

    def test_der_meinung_sein(self):
        self.compare("wenn er der Meinung ist, dass die Grammatik nicht stimmt")

    def test_ein_paar(self):
        self.compare("das ist ein paar Schuhe")

    def test_ein_singular(self):
        self.compare("ich mache das für eine großen, saubere Haufen|ich mache das für einen großen, sauberen Haufen")

    def test_was_fuer(self):
        self.compare("was ist das für eine kluge Haufen|was ist das für ein kluger Haufen")

    def test_was_fuer_pl(self):
        self.compare("was sind das für kluges Sätze|was sind das für kluge Sätze")

    def test_dep_pronoun(self):
        self.compare("die Kutsche, der vorbei fährt, ist schön|die Kutsche, die vorbei fährt, ist schön")

    def test_dep_pronoun2(self):
        self.compare("Ich gebe dem Mensch, die vorbei fährt, etwas|Ich gebe dem Mensch, der vorbei fährt, etwas")

    def test_adj(self):
        self.compare("oder mir irgendwas anderes einfallen lassen, wo es einfach nur erkennt, ob man den falschen genus verwendet|oder mir irgendwas anderes einfallen lassen, wo es einfach nur erkennt, ob man das falsche Genus verwendet")

    def test_quote(self):
        self.compare('woher hast du überhaupt das wort "kältlich"', ignore_case=True)

    def test_sitzen(self):
        self.compare("ich sitze unter ein Baum|ich sitze unter einem Baum")

if __name__ == "__main__":
    unittest.main()