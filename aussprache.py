"""Text für die KI-Stimme vorbereiten: Zahlen, Daten und Abkürzungen als ausgeschriebene Wörter.

ElevenLabs Flash liest Ziffern im normalen Abo nicht zuverlässig vor (aus "3,7" wird z. B. "drei sieben").
Darum schreibt der Bot Zahlen selbst aus, bevor der Text zur Stimme geht:
  "3,7 Millionen"  -> "drei Komma sieben Millionen"
  "am 25. August"  -> "am fünfundzwanzigsten August"
  "$76.38"         -> "seventy-six dollars and thirty-eight cents"
Die Untertitel zeigen weiter die Ziffern: vorlesen() merkt sich, welche gesprochenen Wörter zu welchem
Original-Wort gehören, und untertitel() setzt die Wortzeiten wieder auf die Originalwörter zurück.
"""
import re

# ---------------------------------------------------------------- Deutsch

_DE_EINS = ["null", "eins", "zwei", "drei", "vier", "fünf", "sechs", "sieben", "acht", "neun", "zehn", "elf",
            "zwölf", "dreizehn", "vierzehn", "fünfzehn", "sechzehn", "siebzehn", "achtzehn", "neunzehn"]
_DE_ZEHN = ["", "", "zwanzig", "dreißig", "vierzig", "fünfzig", "sechzig", "siebzig", "achtzig", "neunzig"]
_DE_ORD = {1: "ersten", 3: "dritten", 7: "siebten", 8: "achten"}
_DE_MONATE = {"januar", "februar", "märz", "april", "mai", "juni", "juli", "august", "september", "oktober",
              "november", "dezember", "jan.", "feb.", "mär.", "apr.", "jun.", "jul.", "aug.", "sep.", "sept.",
              "okt.", "nov.", "dez."}
_DE_FEMININ = {"million", "milliarde", "billion", "minute", "stunde", "woche", "aktie", "schale", "dose", "portion",
               "flasche", "sekunde", "mahlzeit", "tafel", "packung", "frage", "sache", "regel", "idee", "chance"}
_DE_ABK = {"Dr.": "Doktor", "Prof.": "Professor", "ca.": "circa", "Mio.": "Millionen", "Mrd.": "Milliarden",
           "Bio.": "Billionen", "Tsd.": "tausend", "Nr.": "Nummer", "bzw.": "beziehungsweise", "usw.": "und so weiter",
           "inkl.": "inklusive", "evtl.": "eventuell", "€": "Euro", "$": "Dollar", "%": "Prozent", "&": "und",
           "kcal": "Kilokalorien", "g": "Gramm", "kg": "Kilo", "ml": "Milliliter", "Std.": "Stunden",
           "Min.": "Minuten", "Mo.": "Montag", "Di.": "Dienstag", "Mi.": "Mittwoch", "Do.": "Donnerstag",
           "Fr.": "Freitag", "Sa.": "Samstag", "So.": "Sonntag", "vs.": "gegen", "z.B.": "zum Beispiel"}
_NACH_ZAHL = {"g", "kg", "ml", "kcal", "€", "$", "%"}      # nur direkt nach einer Zahl ersetzen


def _de_unter_tausend(n, ende=True):
    """0..999; ende=False: 'ein' statt 'eins' (in Zusammensetzungen)."""
    if n < 20:
        if n == 1:
            return "eins" if ende else "ein"
        return _DE_EINS[n]
    if n < 100:
        z, e = divmod(n, 10)
        return (("ein" if e == 1 else _DE_EINS[e]) + "und" if e else "") + _DE_ZEHN[z]
    h, r = divmod(n, 100)
    return ("" if h == 1 else _DE_EINS[h]) + "hundert" + (_de_unter_tausend(r, ende) if r else "")


def de_zahl(n):
    n = int(n)
    if n < 0:
        return "minus " + de_zahl(-n)
    if n < 1000:
        return _de_unter_tausend(n)
    if n < 1_000_000:
        t, r = divmod(n, 1000)
        return ("" if t == 1 else _de_unter_tausend(t, False)) + "tausend" + (_de_unter_tausend(r) if r else "")
    teile = []
    for wert, ein, mehr in ((10 ** 12, "Billion", "Billionen"), (10 ** 9, "Milliarde", "Milliarden"),
                            (10 ** 6, "Million", "Millionen")):
        if n >= wert:
            k, n = divmod(n, wert)
            teile.append(f"eine {ein}" if k == 1 else f"{de_zahl(k)} {mehr}")
    if n:
        teile.append(de_zahl(n))
    return " ".join(teile)


def de_ordinal(n):
    n = int(n)
    if n in _DE_ORD:
        return _DE_ORD[n]
    if n < 20:
        return de_zahl(n) + "ten"
    return de_zahl(n) + "sten"


def de_dezimal(ganz, nach):
    return de_zahl(ganz) + " Komma " + " ".join(_DE_EINS[int(c)] for c in nach)


# ---------------------------------------------------------------- Englisch

_EN_EINS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven",
            "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"]
_EN_ZEHN = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
_EN_ORD = {"one": "first", "two": "second", "three": "third", "five": "fifth", "eight": "eighth", "nine": "ninth",
           "twelve": "twelfth"}
_EN_MONATE = {"january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
              "november", "december", "jan.", "feb.", "mar.", "apr.", "jun.", "jul.", "aug.", "sep.", "sept.",
              "oct.", "nov.", "dec."}
_EN_ABK = {"Dr.": "Doctor", "Prof.": "Professor", "approx.": "approximately", "vs.": "versus", "%": "percent",
           "&": "and", "kcal": "calories", "g": "grams", "ml": "milliliters", "kg": "kilos", "e.g.": "for example"}


def _en_unter_tausend(n):
    if n < 20:
        return _EN_EINS[n]
    if n < 100:
        z, e = divmod(n, 10)
        return _EN_ZEHN[z] + ("-" + _EN_EINS[e] if e else "")
    h, r = divmod(n, 100)
    return _EN_EINS[h] + " hundred" + (" " + _en_unter_tausend(r) if r else "")


def en_zahl(n):
    n = int(n)
    if n < 0:
        return "minus " + en_zahl(-n)
    if n == 0:
        return "zero"
    teile = []
    for wert, wort in ((10 ** 12, "trillion"), (10 ** 9, "billion"), (10 ** 6, "million"), (1000, "thousand")):
        if n >= wert:
            k, n = divmod(n, wert)
            teile.append(f"{_en_unter_tausend(k)} {wort}")
    if n:
        teile.append(_en_unter_tausend(n))
    return " ".join(teile)


def en_ordinal(n):
    w = en_zahl(n)
    kopf, _, letztes = w.rpartition(" ")
    vor, strich, teil = letztes.rpartition("-")
    if teil in _EN_ORD:
        teil = _EN_ORD[teil]
    elif teil.endswith("y"):
        teil = teil[:-1] + "ieth"
    else:
        teil += "th"
    letztes = vor + strich + teil
    return (kopf + " " if kopf else "") + letztes


def en_jahr(n):
    n = int(n)
    if 2000 <= n <= 2009:
        return en_zahl(n)
    a, b = divmod(n, 100)
    return en_zahl(a) + " " + ("hundred" if b == 0 else ("oh " + en_zahl(b) if b < 10 else en_zahl(b)))


def en_dezimal(ganz, nach):
    return en_zahl(ganz) + " point " + " ".join(_EN_EINS[int(c)] for c in nach)


# ---------------------------------------------------------------- Wort für Wort

_TOKEN = re.compile(r'^([("„“‚\'«»\[]*)(.*?)([)"“”‘’\'«»\].,:;!?…]*)$')


def _zerlegen(tok):
    m = _TOKEN.match(tok)
    vor, kern, nach = m.groups()
    if not kern and nach:                       # nur Satzzeichen
        return vor, nach, ""
    # Abkürzungen mit Punkt gehören zum Kern ("Dr.", "Mio.", "25." vor Monat wird gesondert behandelt)
    if nach.startswith(".") and (kern + ".") in _DE_ABK | _EN_ABK:
        kern, nach = kern + ".", nach[1:]
    return vor, kern, nach


_DE_DATIV = {"mit", "von", "bei", "nach", "aus", "zu", "seit", "vor", "in", "an"}


def _zahl_sprechen(kern, lang, naechstes, vorher=""):
    """Gibt die gesprochene Form zurück oder None, wenn der Kern keine Zahl ist."""
    de = lang == "de"
    vorz = ""
    if kern[:1] in "+-–−" and len(kern) > 1 and kern[1].isdigit():
        vorz = "plus " if kern[0] == "+" else "minus "
        kern = kern[1:]
    waehrung = ""
    if kern[:1] in "$€":
        waehrung, kern = kern[0], kern[1:]
    einheit = ""
    m = re.match(r"^(.*?\d)(%|€|\$|g|kg|ml|kcal|[kKMB])$", kern)
    if m and re.match(r"^[\d.,]+$", m.group(1)):
        kern, einheit = m.group(1), m.group(2)
    if not re.match(r"^\d[\d.,]*$", kern):
        if re.match(r"^\d{1,2}:\d{2}$", kern):                          # Uhrzeit / Ergebnis
            a, b = kern.split(":")
            return (de_zahl(a) + (" Uhr " + de_zahl(b) if b != "00" else " Uhr") if de else
                    en_zahl(a) + (" " + (en_zahl(b) if int(b) >= 10 else "oh " + en_zahl(b)) if b != "00" else " o'clock"))
        return None
    # Zahl lesen: Tausender- und Dezimaltrenner je Sprache
    tsd, dez = (".", ",") if de else (",", ".")
    if re.match(rf"^\d{{1,3}}(\{tsd}\d{{3}})+$", kern):
        ganz, nach = kern.replace(tsd, ""), ""
    elif dez in kern:
        ganz, _, nach = kern.partition(dez)
        ganz = ganz.replace(tsd, "")
        if not ganz.isdigit() or not nach.isdigit():
            return None
    elif kern.isdigit():
        ganz, nach = kern, ""
    else:
        return None
    n = int(ganz)
    nxt = (naechstes or "").strip("()\"„“.,:;!?").lower()
    if de:
        if nach:
            wort = de_dezimal(n, nach)
        elif n == 1 and nxt and naechstes[:1].isupper() and not waehrung and not einheit:
            dativ = vorher.lower().strip("(\"„") in _DE_DATIV
            wort = ("einer" if dativ else "eine") if nxt in _DE_FEMININ else ("einem" if dativ else "ein")
        else:
            wort = de_zahl(n)
    else:
        if nach and waehrung and len(nach) == 2:                          # $76.38
            cents = int(nach)
            wort = en_zahl(n) + (" dollars" if waehrung == "$" else " euros") + (
                f" and {en_zahl(cents)} cents" if cents else "")
            return vorz + wort + _einheit(einheit, lang)
        if nach:
            wort = en_dezimal(n, nach)
        elif 1900 <= n <= 2099 and len(ganz) == 4 and not waehrung and not einheit and "," not in kern:
            wort = en_jahr(n)
        else:
            wort = en_zahl(n)
    if waehrung:
        wort += " " + ({"$": "Dollar", "€": "Euro"} if de else {"$": "dollars", "€": "euros"})[waehrung]
    return vorz + wort + _einheit(einheit, lang)


def _einheit(e, lang):
    if not e:
        return ""
    if e in "kKMB" and len(e) == 1:
        return " " + ({"k": "tausend", "K": "tausend", "M": "Millionen", "B": "Milliarden"} if lang == "de" else
                      {"k": "thousand", "K": "thousand", "M": "million", "B": "billion"})[e]
    return " " + (_DE_ABK if lang == "de" else _EN_ABK).get(e, e)


def vorlesen(text, lang="de"):
    """Liste von (Originalwort, gesprochene Form). Die gesprochene Form kann mehrere Wörter enthalten."""
    toks = text.split()
    abk = _DE_ABK if lang == "de" else _EN_ABK
    monate = _DE_MONATE if lang == "de" else _EN_MONATE
    out = []
    for i, tok in enumerate(toks):
        vor, kern, nach = _zerlegen(tok)
        naechstes = toks[i + 1] if i + 1 < len(toks) else ""
        vorher = out[-1][0] if out else ""
        n_kern = _zerlegen(naechstes)[1].lower() if naechstes else ""
        gesprochen = None
        # Datum: "25. August" (de) / "August 25" (en) -> Ordinalzahl
        if kern.isdigit() and len(kern) <= 2 and 1 <= int(kern) <= 31:
            if lang == "de" and nach.startswith(".") and n_kern in monate:
                gesprochen, nach = de_ordinal(kern), nach[1:]
            elif lang == "en" and (_zerlegen(vorher)[1].lower() in monate if vorher else False):
                gesprochen = en_ordinal(kern)
        if gesprochen is None:
            gesprochen = _zahl_sprechen(kern, lang, naechstes, vorher) if kern else None
        if gesprochen is None and kern in abk:
            if kern not in _NACH_ZAHL or re.search(r"\d$", _zerlegen(vorher)[1] if vorher else ""):
                gesprochen = abk[kern]
        if gesprochen is None:
            out.append((tok, tok))
        else:
            out.append((tok, vor + gesprochen + nach))
    return out


def sprechtext(text, lang="de"):
    return " ".join(g for _, g in vorlesen(text, lang))


def untertitel(paare, woerter):
    """Wortzeiten der gesprochenen Wörter auf die Originalwörter zurückrechnen (Ziffern im Untertitel)."""
    anzahl = [len(g.split()) for _, g in paare]
    if sum(anzahl) != len(woerter):
        return woerter                                          # passt nicht zusammen -> unverändert lassen
    out, k = [], 0
    for (orig, _), n in zip(paare, anzahl):
        if n == 0:
            continue
        out.append((woerter[k][0], woerter[k + n - 1][1], orig))
        k += n
    return out
