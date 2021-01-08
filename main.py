import spacy
from spacy import displacy
import spacy.lemmatizer
import declension
import logging
import re
from aiohttp import web
import html
import json
import argparse

nlp = spacy.load('de_core_news_md')
dec = declension.Declension()

prepositions = {
    "AKK": "bis,um,durch,entlang,für,gegen,ohne".split(","),
    "DAT": "aus,außer,bei,zu,bis zu,entgegen,entsprechend,gemäß,getreu,gegenüber,nahe,mit,nach,samt,mitsamt,seit,von,zufolge,zuliebe".split(","),
    "GEN": "aufgrund,wegen,trotz,ungeachtet,beiderseits,diesseits,jenseits,abseits,entlang,oberhalb,unterhalb,außerhalb,innerhalb,längs,seitlich,links,rechts,nördlich,östlich,südlich,westlich,unweit,weitab,während,anlässlich,angesichts,infolge,abzüglich,zuzüglich,anhand,mithilfe,dank,zugunsten".split(",")
}

akkdat_prepositions = "an,auf,in,über,unter,hinter,neben,vor,zwischen".split(",")

prepositions["AKK"] += akkdat_prepositions
prepositions["DAT"] += akkdat_prepositions

gendered_prepositions = {
    "fürn": "für den",
    "fürs": "für das",
    "beim": "bei dem",
    "zum": "zu dem",
    "zur": "zu der",
    "mitm": "mit dem",
    "nachm": "nach dem",
    "vom": "von dem",
    "am": "an dem",
    "im": "in dem",
    "ins": "in das"
}

gendered_rev = {
    "in das": "ins",
    "in dem": "im",
    "an dem": "am",
    "von dem": "vom",
    "zu der": "zur",
    "zu dem": "zum",
    "bei dem": "beim"
}

immobile_verbs = "sitzen,sitzen,sein,stehen,hängen,bleiben,verweilen,liegen,finden,herstellen,erzeugen,machen,singen,tanzen,haben".split(",")
mobile_verbs = "gehen,fahren,fliegen,müssen,sollen,können,bewegen,schieben,ziehen,schicken,senden,transportieren".split(",")

immobile_verbs += [i[:-1] for i in immobile_verbs] # lemmatizer sometimes generates the word with "e"
mobile_verbs += [i[:-1] for i in mobile_verbs] # lemmatizer sometimes generates the word with "e"

for k,v in gendered_prepositions.items():
    vp, vg = v.split(" ")
    vcase = {"dem": "DAT", "den": "AKK", "das": "AKK", "der": "DAT"}[vg]
    if vp in prepositions[vcase]:
        prepositions[vcase].append(k)

def get_corrected_dependent(word, pos, valid_decs, mode=declension.Mode.OTHER):
    """
    returns (corrected dependent, list of matches)
    """
    word, pos = declension.hack_det_word_pos(word, pos)

    valid_dec_tuples = set((d.case, d.is_plural, d.gender) for d in valid_decs)
    if pos == "DET":
        matching_valid_tuples = list(d for d in declension.all_dets(word) if d.word == word and (d.case, d.is_plural, d.gender) in valid_dec_tuples)
        
        if matching_valid_tuples:
            return word, matching_valid_tuples
        else:
            res = declension.best_det(valid_decs, like=word)
            logging.info("found best replacement for det %s in %s: %s", word, valid_decs, res)
            if res:
                return res.word, [res]
    elif pos == "ADJ":
        matching_valid_tuples = list(d for d in declension.all_adjs(word, mode=mode) if d.word == word and (d.case, d.is_plural, d.gender) in valid_dec_tuples)

        if matching_valid_tuples:
            return word, matching_valid_tuples
        else:
            res = declension.best_adj(valid_decs, like=word, mode=mode)
            logging.info("found best replacement for adj %s in %s: %s (mode %s)", word, valid_decs, res, mode)
            if res:
                return res.word, [res]

    return word, valid_decs

def get_subjects(token):
    subjects = []

    # find root or verb
    while token.pos_ != "VERB" and token.dep_ != "ROOT" and token.head != token:
        token = token.head

    if token.pos_ != "VERB":
        subjects.append(token)

    for child in token.children:
        if child.dep_ == "sb":
            subjects.append(child)

    return subjects

def tid(token):
    return (token.i, token.orth)

def proper_capitalize(word):
    ret = ""
    lastc = None
    for i, c in enumerate(word):
        if i == 0:
            c = c.upper()
        elif lastc in "-.,'/" and not word[i:] in ["in", "innen"]:
            c = c.upper()

        lastc = c
        ret += c
    return ret

def get_valid_decs(token, modified_tokens): # should be a noun token
    valid_decs = dec.get_valid(token.text)

    correct_word = valid_decs[0].word
    if correct_word != token.text:
        modified_tokens[tid(token)] = correct_word

    # check which case this should be (only adpositions)
    required_cases = []
    if token.head is not None and token.head.pos_ == "ADP":
        tt = token.head.text.lower()
        for k, v in prepositions.items():
            if tt in v:
                required_cases.append(k)

        if required_cases:
            # try to see if we can obtain the verb so we can guess if it's dative or accusative
            root = token.head
            while root.head is not None and root != root.head:
                root = root.head
                logging.info("searching for head %s", root)
                if root.pos_ == "VERB" or root.pos_ == "AUX":
                    break
            logging.info("found root token %s lemma %s", root, root.lemma_)
            
            if root.pos_ in ("VERB", "AUX") and tt in akkdat_prepositions:
                if root.lemma_ in immobile_verbs:
                    logging.info("found immobile verb")
                    required_cases = ["DAT"]
                elif root.lemma_ in mobile_verbs:
                    logging.info("found mobile verb")
                    required_cases = ["AKK"]

            new_valid_decs = [v for v in valid_decs if v.case in required_cases]

            # note: removing stuff from valid_decs
            #       but if it becomes empty retry with all possible declensions
            #       (cause someone got the word wrong)
            if not new_valid_decs:
                new_valid_decs = [v for v in dec.get_all(token.text) if v.case in required_cases] 

            if new_valid_decs:
                valid_decs = new_valid_decs

        # special handling of "was für", which is its own thing and not accusative
        if tt == "für":
            th = token.head
            if (was_is_subject := any(st.text.lower() == "was" for st in get_subjects(th))) or (list(th.lefts) and list(th.lefts)[:-1].text.lower() == "was"):
                valid_decs = dec.get_valid(token.text)
                if was_is_subject:
                    new_valid_decs = [v for v in valid_decs if v.case == "NOM"]
                    if new_valid_decs:
                        valid_decs = new_valid_decs
            # TODO some guesses at "was für" in other contexts..
            # end of "was für"

        if tt in gendered_prepositions:
            corr_d, matches = get_corrected_dependent(gendered_prepositions[tt].split(" ")[1], "DET", valid_decs)
            if corr_d != gendered_prepositions[tt].split(" ")[1]:
                modified_tokens[tid(token.head)] = gendered_prepositions[tt].split(" ")[0] + " " + corr_d
                valid_decs = declension.filter_decs(valid_decs, matches)

    # remove nominative declensions if this is not a subject or predicate ("beta")
    if token.dep_ not in ["sb", "ROOT", "pd", "sp"]:
        new_valid_decs = [v for v in valid_decs if v.case != "NOM"]
    elif token.dep_ in ["sb", "ROOT"]:
        new_valid_decs = [v for v in valid_decs if v.case == "NOM"]
    else:
        new_valid_decs = [v for v in valid_decs if v.case in ("NOM", "GEN")] # bin der Meinung, dass..

    # it gets even more experimental with these...
    if token.dep_ == "da":
        new_valid_decs = [v for v in valid_decs if v.case == "DAT"]
    if token.dep_ in ["go", "ag", "pg"]:
        new_valid_decs = [v for v in valid_decs if v.case == "GEN"]
    if token.dep_ == "oa":
        new_valid_decs = [v for v in valid_decs if v.case == "AKK"]

    if new_valid_decs:
        valid_decs = new_valid_decs

    # check if "ein" was used and remove plural forms
    for child in token.children:
        if child.text.lower() in ["ein","eine","einem","eines","einer","einen"]:
            new_valid_decs = [v for v in valid_decs if not v.is_plural]
            break

    if new_valid_decs:
        valid_decs = new_valid_decs

    return valid_decs


def get_sentence_and_doc(text, fmt="{}"):
    doc = nlp(text)
    modified_tokens = {}

    for token in doc:
        logging.info("%s [pos:]%s [dep:]%s [parent]%s", token.text, token.pos_, token.dep_, token.head.text)
        if token.pos_ in ("NOUN", "PROPN") and dec.lemmatize(token.text) is not None:
            valid_decs = get_valid_decs(token, modified_tokens)

            # check dependents if they follow the correct declension
            mode = declension.Mode.OTHER
            worklist = []

            # first scan if we need to go into a special mode
            for d in token.children:
                if (child_mode := declension.get_mode(d.text.lower())) is not None:
                    mode = child_mode
                    break

            for d in token.children:
                if d.pos_ in ("NOUN", "PROPN"):
                    continue # skip nouns, they will be processed linearly
                
                if any(dd.text in "\"'" for dd in d.children):
                    continue # skip quoted stuff

                # special case
                if d.text.lower() == "paar": # TODO this should be parsed on its own similar to a noun even though it's a DET, for now we just don't correct it..
                    continue

                corr_d, matches = get_corrected_dependent(d.text, d.pos_, valid_decs, mode=mode)
                if corr_d != d.text:
                    modified_tokens[tid(d)] = corr_d
                valid_decs = declension.filter_decs(valid_decs, matches)

                worklist += d.children

            while worklist:
                child, worklist = worklist[0], worklist[1:]
                logging.info("parsing item %s which is %s", child, child.pos_)

                # special case: fix definite pronoun in sub-sentence too
                # todo more than just subjects...
                if child.dep_ == "sb" and child.pos_ == "PRON" and child.text.lower() in declension.DEFINITES:
                    pronoun_decs = [dec for dec in dec.get_all(token.text) if dec.case == "NOM" and dec.is_plural in set(vd.is_plural for vd in valid_decs)]
                    
                    # TODO apply matches from get_corrected_dependent here too
                    corr_d, _ = get_corrected_dependent(child.text, "DET", pronoun_decs, mode=mode)
                    if corr_d != child.text:
                        modified_tokens[tid(child)] = corr_d
                    continue

                if child.pos_ in ("NOUN", "PROPN", "VERB", "AUX") or child.dep_ == "sb":
                    continue # skip nouns / verbs / subjects (=other sentences), they will be processed linearly

                if any(d.text in "\"'" for d in child.children):
                    continue # skip quoted stuff

                worklist += child.children

                # TODO apply matches from get_corrected_dependent here too
                corr_d, _ = get_corrected_dependent(child.text, child.pos_, valid_decs, mode=mode)
                if corr_d != child.text:
                    modified_tokens[tid(child)] = corr_d
            # worklist done

        else:
            if token.pos_ == "NOUN":
                logging.info("noun not found: %s", token.text)
                if token.text != proper_capitalize(token.text):
                    modified_tokens[tid(token)] = proper_capitalize(token.text)

    fixed_sentence = ""

    # TODO perform contraction on the modifications only
    
    first_letter_was_capitalized = text.strip() and text.strip()[0] == text.strip()[0].upper()

    for token in doc:
        # token.i == 0 or
        # if (token.pos_ == "PROPN") and token.text != proper_capitalize(token.text): # some last minute quick fixes
        #    modified_tokens[tid(token)] = proper_capitalize(token.text)

        new_modified_token = modified_tokens[tid(token)] if tid(token) in modified_tokens else None
        if token.i == 0 and first_letter_was_capitalized and new_modified_token is not None:
            new_modified_token = proper_capitalize(new_modified_token)

        fixed_sentence += fmt.format(new_modified_token) if new_modified_token is not None else token.text
        if token.text_with_ws != token.text:
            fixed_sentence += " "

    return fixed_sentence, doc

def get_sentence(text,*args,**kwargs):
    sentence, _ = get_sentence_and_doc(text,*args,**kwargs)
    return sentence

def main(args=None):
    while True:
        sentence, doc = get_sentence_and_doc(input("Enter text: "), fmt="*{}*")
        print(sentence)
        if args and args.visualize:
            displacy.serve(doc)


def server(host="localhost", port=7314):
    async def sentence_request(request):
        fmt = "{}"
        mode =  request.query["mode"] if "mode" in request.query else "plain"
        
        if mode == "irc":
            fmt = "\002{}\002"
        elif mode == "text":
            fmt = "*{}*"
        elif mode == "html":
            fmt = "§§§§{}§§#§"
            
        if request.method == "GET":
            text = request.query["text"]
        else:
            text = await request.text()

        ret = get_sentence(text, fmt=fmt)
        ret_for_change = get_sentence(text)

        if mode == "html":
            ret = html.escape(ret)
            ret = ret.replace("§§§§", "<b>").replace("§§#§", "</b>") # ugly but pragmatic?

        format = "json"
        if "format" in request.query and request.query["format"] in ["plain"]:
            format = request.query["format"]

        if format == "plain":
            return web.Response(body=ret, content_type="text/plain", charset="UTF-8")
        elif format == "json":
            return web.Response(body=json.dumps({
                "result": ret, "changed":(ret_for_change.lower() != text.lower())
            }, indent=2), content_type="application/json", headers={"Access-Control-Allow-Origin": "*"})

    # configure webserver
    app = web.Application()
    app.add_routes([web.get("/", sentence_request), web.post("/", sentence_request)])

    web.run_app(app, host=host, port=port)

if __name__ == "__main__":
    _p = argparse.ArgumentParser()
    _p.add_argument("-i", "--interactive", action="store_true", help="Start an interactive session (starts an API server without this option)")
    _p.add_argument("-z", "--visualize", action="store_true", help="Run a displaCy server after each result in interactive mode to visualize dependencies")
    _p.add_argument("-p", "--port", default=7314, help="API server port")
    _p.add_argument("-H", "--host", default="localhost", help="API server host to bind to")
    _p.add_argument("-v", "--verbose", action="store_true", help="Output debug information")
    
    _a = _p.parse_args()
    logging.basicConfig(level=logging.INFO if _a.verbose else logging.WARN)
    
    if _a.interactive:
        main(_a)
    else:
        server(host=_a.host, port=_a.port)