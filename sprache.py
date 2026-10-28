"""Sprachpakete: Zahlenformate und alle Bildschirm-Texte auf Deutsch und Englisch.

Neue Sprache? Einen Block in LABELS kopieren, übersetzen und in skript.py die Sprechtexte ergänzen.
"""
import re
from datetime import datetime

MONATE = {
    "de": ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober",
           "November", "Dezember"],
    "en": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
           "November", "December"],
}
MONATE_KURZ = {
    "de": ["Jan", "Feb", "Mär", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"],
    "en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
}
BRANCHEN_DE = {
    "Technology": "Technologie", "Healthcare": "Gesundheit", "Financial Services": "Finanzen",
    "Consumer Cyclical": "Konsum", "Consumer Defensive": "Basiskonsum", "Industrials": "Industrie",
    "Energy": "Energie", "Utilities": "Versorger", "Real Estate": "Immobilien",
    "Basic Materials": "Rohstoffe", "Communication Services": "Kommunikation",
}
ROLLEN_EN = {
    "Finanzchef": "CFO", "Board-Mitglied": "Director", "Großaktionär": "10% owner", "Vorstandschef": "CEO",
    "Vorstand": "Board member", "Aufsichtsrat": "Supervisory board", "Nahestehende Person": "Close associate",
    "Führungskraft": "Executive",
}

LABELS = {
    "de": {
        "brand": "AKTIEN-RADAR", "brand_insider": "INSIDER-RADAR", "disclaimer": "Keine Anlageberatung", "daten": "Daten",
        "kurs": "Kurs", "mcap": "Börsenwert", "r12": "12 Monate", "kgv": "KGV erwartet", "div": "Dividende",
        "keine": "keine", "monate": "{m} Monate", "legende": "= Insiderkauf (Größe = Betrag)",
        "kauft": "{rolle} kauft {x}", "hoch": "Hoch", "tief": "Tief",
        "wer": "Wer hat gekauft?", "wer_sub": "Offizielle {q}-Meldungen · letzte {t} Tage",
        "gesamt": "Gesamt {x} · {n} Personen · {k} Käufe",
        "netz": "Was sagt das Netz?", "netz_sub": "Reddit · StockTwits · Schlagzeilen",
        "reddit": "Reddit · Erwähnungen 24 Std.", "neu": "neu", "vortag": "Vortag", "heute": "Heute",
        "funkstille": "Fast Funkstille", "unter_radar": "nur {m} Erwähnungen · unter dem Radar",
        "st": "StockTwits · {n} markierte Beiträge", "bull": "bullisch", "bear": "bärisch",
        "news": "Schlagzeilen · {n} Meldungen", "pos": "positiv", "neg": "negativ", "mix": "gemischt",
        "hype": "Hype-Index", "hype_lab": {"heiß": "heiß", "positiv": "positiv", "neutral": "neutral", "kühl": "kühl"},
        "score": "Scanner-Score", "platz": "Platz {r} von {n} Aktien", "von100": "von 100",
        "kat": {"bewertung": "Bewertung", "qualitaet": "Qualität", "wachstum": "Wachstum", "analysten": "Analysten",
                "momentum": "Momentum", "stabilitaet": "Stabilität", "nachrichten": "Nachrichten",
                "dividende": "Dividende"},
        "pc": "Dafür & dagegen", "pc_sub": "Was die Daten sagen", "pro": "DAFÜR", "contra": "DAGEGEN",
        "nur_daten": "Nur Daten · eigene Recherche machen", "follow_liste": "Morgen: die nächste Aktie",
        "follow_insider": "Folge für tägliche Insider-Alerts", "haelt": "Offenlegung: Ich besitze diese Aktie",
        "kaeufer": "Käufer", "tage": "in {t} Tagen",
    },
    "en": {
        "brand": "STOCK RADAR", "brand_insider": "INSIDER RADAR", "disclaimer": "Not financial advice", "daten": "Data",
        "kurs": "Price", "mcap": "Market cap", "r12": "12 months", "kgv": "Forward P/E", "div": "Dividend",
        "keine": "none", "monate": "{m} months", "legende": "= insider buy (size = amount)",
        "kauft": "{rolle} buys {x}", "hoch": "High", "tief": "Low",
        "wer": "Who bought?", "wer_sub": "Official {q} filings · last {t} days",
        "gesamt": "Total {x} · {n} people · {k} buys",
        "netz": "The online buzz", "netz_sub": "Reddit · StockTwits · headlines",
        "reddit": "Reddit · mentions 24h", "neu": "new", "vortag": "Yesterday", "heute": "Today",
        "funkstille": "Radio silence", "unter_radar": "only {m} mentions · under the radar",
        "st": "StockTwits · {n} tagged posts", "bull": "bullish", "bear": "bearish",
        "news": "Headlines · {n} articles", "pos": "positive", "neg": "negative", "mix": "mixed",
        "hype": "Hype index", "hype_lab": {"heiß": "hot", "positiv": "positive", "neutral": "neutral", "kühl": "cool"},
        "score": "Scanner score", "platz": "Rank {r} of {n} stocks", "von100": "out of 100",
        "kat": {"bewertung": "Value", "qualitaet": "Quality", "wachstum": "Growth", "analysten": "Analysts",
                "momentum": "Momentum", "stabilitaet": "Stability", "nachrichten": "News", "dividende": "Dividend"},
        "pc": "Bull vs. bear", "pc_sub": "What the data says", "pro": "BULL CASE", "contra": "BEAR CASE",
        "nur_daten": "Just data · do your own research", "follow_liste": "Tomorrow: the next stock",
        "follow_insider": "Follow for daily insider alerts", "haelt": "Disclosure: I own this stock",
        "kaeufer": "buyers", "tage": "in {t} days",
    },
}


def L(lang, key, **kw):
    v = LABELS.get(lang, LABELS["de"])[key]
    return v.format(**kw) if kw and isinstance(v, str) else v


# ---------------------------------------------------------------- Zahlen

def _num(x, d, lang):
    s = f"{x:,.{d}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".") if lang == "de" else s


def geld(x, cur="USD", lang="de", sprechen=False):
    """3,7 Mio. $ | 3,7 Millionen Dollar | $3.7M | 3.7 million dollars"""
    zeichen = {"USD": "$", "EUR": "€"}.get(cur, cur + " ")
    wort = {"de": {"USD": "Dollar", "EUR": "Euro"}, "en": {"USD": "dollars", "EUR": "euros"}}[lang].get(cur, cur)
    stufen = [(1e12, "Bio.", "Billionen", "T", "trillion"), (1e9, "Mrd.", "Milliarden", "B", "billion"),
              (1e6, "Mio.", "Millionen", "M", "million"), (1e3, "Tsd.", "Tausend", "K", "thousand")]
    v, k_de, l_de, k_en, l_en = x, "", "", "", ""
    for grenze, a, b, c, e in stufen:
        if abs(x) >= grenze:
            v, k_de, l_de, k_en, l_en = x / grenze, a, b, c, e
            break
    d = 0 if abs(v) >= 100 or not k_de else 1
    z = _num(v, d, lang)
    z = re.sub(r"[.,]0$", "", z)
    if lang == "de":
        if sprechen:
            if z == "1" and l_de in ("Millionen", "Milliarden", "Billionen"):
                l_de = {"Millionen": "Million", "Milliarden": "Milliarde", "Billionen": "Billion"}[l_de]
            return " ".join(p for p in (z, l_de, wort) if p)
        return " ".join(p for p in (z, k_de, zeichen.strip()) if p)
    if sprechen:
        return " ".join(p for p in (z, l_en, wort) if p)
    return f"{zeichen.strip()}{z}{k_en}"


def kurs(x, cur="USD", lang="de", sprechen=False):
    zeichen = {"USD": "$", "EUR": "€"}.get(cur, cur)
    if lang == "en":
        return f"{zeichen}{x:,.2f}"
    if sprechen:
        e, c = int(x), int(round((x - int(x)) * 100))
        w = {"USD": "Dollar", "EUR": "Euro"}.get(cur, cur)
        return f"{e} {w} {c}" if c else f"{e} {w}"
    return f"{_num(x, 2, 'de')} {zeichen}"


def prozent(x, lang="de", sprechen=False, vorzeichen=True):
    p = x * 100
    if sprechen:
        wort = "Prozent" if lang == "de" else "percent"
        return f"{_num(abs(p), 0, lang)} {wort}"
    s = f"{p:+.0f}" if vorzeichen else f"{p:.0f}"
    return f"{s} %" if lang == "de" else f"{s}%"


def zahl(x, lang="de", d=1):
    return _num(x, d, lang)


def datum(iso, lang="de", kurz=False):
    d = datetime.strptime(iso, "%Y-%m-%d")
    m = (MONATE_KURZ if kurz else MONATE)[lang][d.month - 1]
    return f"{d.day}. {m}" if lang == "de" else f"{m} {d.day}"


def heute(lang="de"):
    d = datetime.now()
    return d.strftime("%d.%m.%Y") if lang == "de" else f"{MONATE_KURZ['en'][d.month - 1]} {d.day}, {d.year}"


def branche(name, lang="de"):
    return BRANCHEN_DE.get(name, name) if lang == "de" else (name or "")


def rolle(r, lang="de"):
    return ROLLEN_EN.get(r, r) if lang == "en" else r


# ---------------------------------------------------------------- Warnsignale aus dem Scanner

# (Muster, Bildschirm DE, gesprochen DE, Bildschirm EN, gesprochen EN)
WARN = [
    (r"Macht aktuell Verlust", "Schreibt aktuell Verluste", "aktuelle Verluste",
     "Currently unprofitable", "the company is losing money"),
    (r"Hohe Verschuldung", "Hohe Verschuldung", "hohe Schulden", "High debt load", "a heavy debt load"),
    (r"Negativer Free Cashflow", "Negativer Free Cashflow", "ein negativer Free Cashflow",
     "Negative free cash flow", "negative free cash flow"),
    (r"Dividende höher als Gewinn", "Dividende höher als Gewinn", "eine Dividende, die den Gewinn übersteigt",
     "Dividend exceeds earnings", "a dividend that exceeds earnings"),
    (r"Kurs zeitweise -?(\d+)\s?% eingebrochen", "Zeitweise -{0} % eingebrochen",
     "ein zwischenzeitlicher Kurseinbruch von {0} Prozent", "Fell up to {0}% this year",
     "a drawdown of {0} percent this year"),
    (r"Überwiegend negative Nachrichten", "Überwiegend negative Nachrichten", "überwiegend negative Schlagzeilen",
     "Mostly negative headlines", "mostly negative headlines"),
    (r"Analysten überwiegend skeptisch", "Analysten skeptisch", "skeptische Analysten",
     "Analysts are skeptical", "skeptical analysts"),
    (r"Kaum Analysten-Abdeckung", "Kaum Analysten-Abdeckung", "kaum Analysten-Abdeckung",
     "Little analyst coverage", "little analyst coverage"),
    (r"Umsatz schrumpft \(?-?(\d+)\s?%", "Umsatz schrumpft (-{0} %)", "ein um {0} Prozent schrumpfender Umsatz",
     "Revenue down {0}%", "revenue shrinking {0} percent"),
]


def warnung(text, lang="de"):
    """Scanner-Warnung -> (Bildschirmtext, gesprochener Text) in der gewünschten Sprache."""
    for muster, sd, gd, se, ge in WARN:
        m = re.search(muster, text)
        if m:
            g = m.groups()
            return (sd.format(*g), gd.format(*g)) if lang == "de" else (se.format(*g), ge.format(*g))
    return text, text
