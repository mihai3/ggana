# quick and dirty declension based on the https://www.korrekturen.de/flexion/download/nomen.sql.gz database extracted to mysql
import sqlite3
import os


class Declension:
    def __init__(self, db_path=f"""{os.path.join(os.path.dirname(__file__), "nomen.sqlite")}"""):
        self.db_path = db_path
        self.db = sqlite3.connect(db_path)
        self.cursor = self.db.cursor()

    def __enter__(self):
        return self

    def __exit__(self, a, b, c):
        self.close()

    def close(self):
        self.cursor.close()
        self.db.close()
    
    def lemmatize(self, word):
        self.cursor.execute("SELECT lemma FROM nomen WHERE form = ? COLLATE NOCASE", (word,))
        row = self.cursor.fetchone()
        return row if row is None else row[0]

    def get_valid(self, word):
        self.cursor.execute("SELECT form, lemma, tags FROM nomen WHERE form = ? COLLATE NOCASE", (word,))
        return [DeclensionResult(form, lemma, tags) for form, lemma, tags in self.cursor.fetchall()]

    def get_all(self, word):
        word = self.lemmatize(word)
        if word is None:
            return []

        self.cursor.execute("SELECT form, lemma, tags FROM nomen WHERE lemma = ?", (word,))
        return [DeclensionResult(form, lemma, tags) for form, lemma, tags in self.cursor.fetchall()]        

    def genders(self, word):
        return set(x.gender for x in self.get_valid(word))


class DeclensionResult:
    def __init__(self, word, lemma, tags):
        self.word = word
        self.lemma = lemma
        self.case, count, self.gender = tags.replace("NOG","NEU").split(":")[1:4]
        self.is_plural = count == "PLU"

    # genders: MAS, FEM, NEU

    def __hash__(self):
        return hash((self.word, self.lemma, self.case, self.is_plural, self.gender))

    def __repr__(self):
        return repr((self.word, self.lemma, self.case, self.is_plural, self.gender))

# ordering: prefer accusative (2nd)
DET_DECS = [DeclensionResult(w, "das", "DET:"+t) for w, t in \
    [("der", "NOM:SIN:MAS"),("den", "AKK:SIN:MAS"),("des", "GEN:SIN:MAS"),("dem", "DAT:SIN:MAS"),
    ("die", "NOM:SIN:FEM"),("die", "AKK:SIN:FEM"),("der", "GEN:SIN:FEM"),("der", "DAT:SIN:FEM"),
    ("das", "NOM:SIN:NEU"),("das", "AKK:SIN:NEU"),("des", "GEN:SIN:NEU"),("dem", "DAT:SIN:NEU"),
    ("die", "NOM:PLU:MAS"),("die", "AKK:PLU:MAS"),("der", "GEN:PLU:MAS"),("den", "DAT:PLU:MAS"),
    ("die", "NOM:PLU:FEM"),("die", "AKK:PLU:FEM"),("der", "GEN:PLU:FEM"),("den", "DAT:PLU:FEM"),
    ("die", "NOM:PLU:NEU"),("die", "AKK:PLU:NEU"),("der", "GEN:PLU:NEU"),("den", "DAT:PLU:NEU")]
]

SODS = ["ein","kein","mein","dein","sein","unser","euer","ihr","viel"]
DEFINITES = ["der","die","das","dem","den","des"]

for sod in SODS:
    DET_DECS += [DeclensionResult(w, sod, "DET:"+t) for w, t in \
        [(sod+"", "NOM:SIN:MAS"),(sod+"en", "AKK:SIN:MAS"),(sod+"es", "GEN:SIN:MAS"),(sod+"em", "DAT:SIN:MAS"),
        (sod+"e", "NOM:SIN:FEM"),(sod+"e", "AKK:SIN:FEM"),(sod+"er", "GEN:SIN:FEM"),(sod+"er", "DAT:SIN:FEM"),
        (sod+"", "NOM:SIN:NEU"),(sod+"", "AKK:SIN:NEU"),(sod+"em", "GEN:SIN:NEU"),(sod+"em", "DAT:SIN:NEU"),
        (sod+"e", "NOM:PLU:MAS"),(sod+"e", "AKK:PLU:MAS"),(sod+"er", "GEN:PLU:MAS"),(sod+"en", "DAT:PLU:MAS"),
        (sod+"e", "NOM:PLU:FEM"),(sod+"e", "AKK:PLU:FEM"),(sod+"er", "GEN:PLU:FEM"),(sod+"en", "DAT:PLU:FEM"),
        (sod+"e", "NOM:PLU:NEU"),(sod+"e", "AKK:PLU:NEU"),(sod+"er", "GEN:PLU:NEU"),(sod+"en", "DAT:PLU:NEU")
        ]
    ]

# diese, manche, wenige..
DET_SUFFIXES_E = [("er", "NOM:SIN:MAS"),("en", "AKK:SIN:MAS"),("es", "GEN:SIN:MAS"),("em", "DAT:SIN:MAS"),
    ("e", "NOM:SIN:FEM"),("e", "AKK:SIN:FEM"),("er", "GEN:SIN:FEM"),("er", "DAT:SIN:FEM"),
    ("es", "NOM:SIN:NEU"),("es", "AKK:SIN:NEU"),("es", "GEN:SIN:NEU"),("em", "DAT:SIN:NEU"),
    ("e", "NOM:PLU:MAS"),("e", "AKK:PLU:MAS"),("er", "GEN:PLU:MAS"),("en", "DAT:PLU:MAS"),
    ("e", "NOM:PLU:FEM"),("e", "AKK:PLU:FEM"),("er", "GEN:PLU:FEM"),("en", "DAT:PLU:FEM"),
    ("e", "NOM:PLU:NEU"),("e", "AKK:PLU:NEU"),("er", "GEN:PLU:NEU"),("en", "DAT:PLU:NEU")]

def desuffixize(word, goodlist=None):
    if goodlist and word in goodlist:
        return word

    if word.endswith("e"):
        word = word[:-1]
    elif any(word.endswith(suffix) for suffix in "em,er,es,en".split(",")):
        word = word[:-2]
    return word

def best_det(valid_decs, like="das"):
    valid_dec_tuples = set((d.case, d.is_plural, d.gender) for d in valid_decs)
    for det in all_dets(like):
        if (det.case, det.is_plural, det.gender) in valid_dec_tuples:
            return det

def all_dets(word):
    if word.lower() in DEFINITES or any(word.lower().startswith(sod) for sod in SODS):
        lemma = None
        for sod in SODS:
            if word.lower().startswith(sod):
                lemma = sod
                break
        
        if lemma is None:
            lemma = "das"

        return (d for d in DET_DECS if d.lemma == lemma)

    lemma = desuffixize(word)
    return [DeclensionResult(lemma+suffix, lemma, f"DET:{t}") for suffix, t in DET_SUFFIXES_E]


## hacks!
def hack_det_word_pos(orig_word, orig_pos):
    word = orig_word.lower()
    if word == "nen":
        orig_word = "einen"
    elif word == "ne":
        orig_word = "eine"

    if orig_pos == "DET":
        if word.startswith("meist") or word.startswith("wenigst"):
            return orig_word, "ADJ"
        else:
            return orig_word, "DET"

    return orig_word, orig_pos

# des schönen Kleides - wtf
# eines schönen Kleides
# ein schönes Kleid
# das schöne Kleid
# schöne Kleider
ADJ_SUFFIXES_E = [("er", "NOM:SIN:MAS"),("en", "AKK:SIN:MAS"),("en", "GEN:SIN:MAS"),("en", "DAT:SIN:MAS"),
    ("e", "NOM:SIN:FEM"),("e", "AKK:SIN:FEM"),("en", "GEN:SIN:FEM"),("en", "DAT:SIN:FEM"),
    ("es", "NOM:SIN:NEU"),("es", "AKK:SIN:NEU"),("en", "GEN:SIN:NEU"),("en", "DAT:SIN:NEU"),
    ("e", "NOM:PLU:MAS"),("e", "AKK:PLU:MAS"),("en", "GEN:PLU:MAS"),("en", "DAT:PLU:MAS"),
    ("e", "NOM:PLU:FEM"),("e", "AKK:PLU:FEM"),("en", "GEN:PLU:FEM"),("en", "DAT:PLU:FEM"),
    ("e", "NOM:PLU:NEU"),("e", "AKK:PLU:NEU"),("en", "GEN:PLU:NEU"),("en", "DAT:PLU:NEU"),
    ]
ADJ_SUFFIXES_D = [("e", "NOM:SIN:MAS"),("en", "AKK:SIN:MAS"),("en", "GEN:SIN:MAS"),("en", "DAT:SIN:MAS"),
    ("e", "NOM:SIN:FEM"),("e", "AKK:SIN:FEM"),("en", "GEN:SIN:FEM"),("en", "DAT:SIN:FEM"),
    ("e", "NOM:SIN:NEU"),("e", "AKK:SIN:NEU"),("en", "GEN:SIN:NEU"),("en", "DAT:SIN:NEU"),
    ("en", "NOM:PLU:MAS"),("en", "AKK:PLU:MAS"),("en", "GEN:PLU:MAS"),("en", "DAT:PLU:MAS"),
    ("en", "NOM:PLU:FEM"),("en", "AKK:PLU:FEM"),("en", "GEN:PLU:FEM"),("en", "DAT:PLU:FEM"),
    ("en", "NOM:PLU:NEU"),("en", "AKK:PLU:NEU"),("en", "GEN:PLU:NEU"),("en", "DAT:PLU:NEU")]

ADJ_GOODLIST = ["sicher", "tapfer", "koscher"]

def all_adjs(word, definite=False, lemma=None):
    if lemma is None:
        lemma = desuffixize(word, goodlist=ADJ_GOODLIST)
    return [DeclensionResult(lemma+suffix, lemma, f"ADJ:{t}") for suffix, t in (ADJ_SUFFIXES_D if definite else ADJ_SUFFIXES_E)]

def best_adj(valid_decs, like, definite=False, lemma=None):
    if lemma is None:
        lemma = desuffixize(like, goodlist=ADJ_GOODLIST)
    valid_dec_tuples = set((d.case, d.is_plural, d.gender) for d in valid_decs)

    for det in all_adjs(lemma, definite, lemma=lemma):
        if (det.case, det.is_plural, det.gender) in valid_dec_tuples:
            return det

def filter_decs(from_decs, like_decs):
    like_dec_tuples = set((d.case, d.is_plural, d.gender) for d in like_decs)
    return [d for d in from_decs if (d.case, d.is_plural, d.gender) in like_dec_tuples]