# GGANA

_Großartiger grammatikalischer Artikel-Neu-Auswerter_

This tool attempts to correct some of the more common mistakes concerning the use of nouns in German.
In particular, it attempts to determine the gender of each used noun and to ensure that the correct article,
as well as correctly declinated adjectives and other determinants are used.

The analysis mainly relies on prepositions as well as on some of the more robust hints from spaCy's dependency parser (like the
use of a noun as a subject or in a predicate).

**Note**: This tool doesn't attempt to correct any other mistakes (like misspelled words, wrong use of verbs and pronouns). It also doesn't reliably detect the case of nouns.

Due to the complex nature of languages, please only expect it to work some (hopefully most) of the time. This is just a slightly more pragmatic proof-of-concept.

## Live demo

Available at: https://mihai3.com/ggana/

## Installation and usage

```
# Create a Python virtualenv.
virtualenv venv

# Install requirements
venv/bin/pip install -r requirements.txt

# Download and setup inflection table
venv/bin/python setup_inflection_table.py

# Run in interactive mode
venv/bin/python ./main.py -i

# See venv/bin/python ./main.py -h for more options.
```

## Server mode

Run `venv/bin/python ./main.py`

This will start an HTTP REST server (by default on http://localhost:7314/)

You can then make GET or POST requests to the root endpoint as follows:

* The query parameter `mode` will determine how ćhanges in the result are highlighted:
  * `text` to wrap them in \*asterisks\*
  * `irc` to wrap them in "bold" control codes for IRC (ASCII 0x02)
  * `html` to wrap them in `<b></b>` (and also escape other HTML characters in the result)
  * `plain` (or not specified) to do nothing
* In GET mode: specify the text using the `text` query parameter.
* In POST mode: post the plain text as the HTTP request body.
* The query parameter `format` will determine the response format:
  * `plain` will respond with the corrected text as plain text
  * `json` (the default) will respond with a JSON object containing:
    * `changed` whether the sentence changed (boolean)
    * `result` the corrected text (string)

### Examples

#### JSON

```
curl -H"Content-type: text/plain" -d"Ich sitze unter ein Baum." "http://localhost:7314?mode=text"
```

```json
{
  "result": "Ich sitze unter *einen* Baum.",
  "changed": true
}
```

#### Plain text

```
curl -H"Content-type: text/plain" -d"Wo sind die leckere kekse?" "http://localhost:7314?mode=text&format=plain"
```

```
Wo sind die *leckeren* *Kekse*?
```

## Tests

Run automated tests using:

```
venv/bin/python declension_test.py
venv/bin/python ggana_test.py
```

In general it's good to have a test for each weird edge case in the code.

## License

* GPLv3+
* This code uses [spaCy](https://spacy.io) which is licensed under the MIT License. The ML model used is licensed under the MIT License.
* This code downloads and uses data from the [Flexion tool by korrekturen.de](https://www.korrekturen.de/flexion/projekt.shtml) which is licensed as CC-BY-SA 4.0.