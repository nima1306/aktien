"""Thema Geld-Mindset: ruhige Erklärvideos mit einer überraschenden These, Deutsch + Englisch.

Die Texte schreibt jeden Tag die Claude-API neu (Secret ANTHROPIC_API_KEY). Ohne Schlüssel nimmt der
Bot die fertigen Skripte unten (ERSATZ). Die Bilder sind leuchtende Linien-Symbole (linien.py).
"""
import json
import random
from datetime import date

import linien
from mindset_szenen import FORMEN

NAME = "mindset"
BRAND = {"de": "GELD · MINDSET", "en": "MONEY · MINDSET"}
DISCLAIMER = {"de": "Keine Finanzberatung · nur ein Denkanstoß", "en": "Not financial advice · just food for thought"}
TYPEN = ["symbol", "vergleich", "kurve", "zahl", "satz", "liste"]
THEMEN_IDEEN = [
    "Zinseszins und warum Zeit wichtiger ist als die Summe", "Lifestyle-Inflation", "die 72er-Regel",
    "Opportunitätskosten bei kleinen Alltagsausgaben", "Notgroschen als Freiheit", "Einkommen steigern vs. nur sparen",
    "Verlustaversion: warum Verluste doppelt wehtun", "Sunk-Cost-Falle", "Inflation als stiller Vermögensverlust",
    "Bezahlen mit Karte vs. Bargeld und Ausgabeverhalten", "Ratenkäufe und die wahren Kosten", "Kreditkartenzinsen",
    "In Fähigkeiten investieren als beste Rendite", "Pareto-Prinzip bei Finanzen", "Belohnungsaufschub",
    "Ankereffekt bei Preisen und Rabatten", "Herdentrieb an der Börse", "Kosten von Fondsgebühren über 30 Jahre",
    "Zeit gegen Geld tauschen vs. skalierbares Einkommen", "Statuskonsum und Vergleich mit anderen",
    "Automatisieren statt Disziplin", "Mentale Buchführung", "warum Timing des Marktes selten funktioniert",
    "Diversifikation einfach erklärt", "Kosten eines Autos über 10 Jahre", "Mieten vs. Kaufen als Rechenfrage",
]

SYSTEM = """Du schreibst Skripte für kurze, hochwertige Erklärvideos (TikTok, 60-75 Sekunden) über Geld-Mindset
und persönliche Finanzen. Stil: ruhig, klug, wie ein guter Erzähler. Jede Folge hat EINE zentrale Idee.

Regeln für den Text:
- Erster Satz: eine überraschende These oder Frage, die neugierig macht. Kein "Hallo", kein "In diesem Video".
- Kurze Sätze. Rhetorische Fragen. Ein konkretes, durchgerechnetes Beispiel mit runden Zahlen, als Beispiel
  gekennzeichnet. Rechne die Zahlen korrekt. Zum Schluss ein Aha-Moment oder eine merkbare Regel.
- Keine Empfehlung bestimmter Aktien, Fonds, Kryptowährungen oder Anbieter. Keine Renditeversprechen.
  Wenn Renditen vorkommen: als Annahme formulieren ("angenommen 7 Prozent pro Jahr").
- Keine erfundenen Statistiken, keine Studien ohne Quelle, keine Zitate realer Personen.
- Pro Szene 1-3 Sätze, höchstens 40 Wörter. 6 oder 7 Szenen. Insgesamt 165-190 Wörter pro Sprache (das Video muss über 60 Sekunden lang sein).
- Zahlen im Sprechtext ausschreiben, wie man sie sagt ("rund 262.000 Euro", englisch "about 262,000 dollars").
- Englische Fassung: gleiche Aussage, natürlich formuliert (kein Wort-für-Wort), Währung Dollar.

Antworte NUR mit einem JSON-Objekt in diesem Format:
{"id": "kurzer-slug", "titel_de": [3 Titel], "titel_en": [3 Titel], "tags_de": [6 Hashtags ohne #],
 "tags_en": [6 Hashtags ohne #], "frage_kurz_de": "...", "frage_kurz_en": "...",
 "frage_lang_de": "offene Frage an die Zuschauer, 1 Satz", "frage_lang_en": "...",
 "szenen": [{"text_de": "...", "text_en": "...", "bild": BILD}]}

BILD ist eines davon (Bildschirmtexte kurz, max. 4 Wörter; Werte wie "262.000 €" / "$262,000"):
{"typ": "symbol", "icon": ICON, "label_de": "...", "label_en": "...", "wert_de": "...", "wert_en": "...", "gold": true|false}
{"typ": "vergleich", "links": {"icon": ICON, "label_de", "label_en", "wert_de", "wert_en"}, "rechts": {...}}
{"typ": "kurve", "kurven": [{"form": FORM, "label_de", "label_en"}] (1-2 Kurven), "y_de", "y_en", "x_de", "x_en"}
{"typ": "zahl", "wert_de", "wert_en", "label_de", "label_en"}
{"typ": "satz", "text_de", "text_en"}   (Bildschirmsatz, max. 10 Wörter)
{"typ": "liste", "punkte": [{"icon": ICON, "de": "...", "en": "..."}] (genau 3)}
ICON: """ + ", ".join(linien.SYMBOLE) + """
FORM: """ + ", ".join(FORMEN) + """
Wechsle die Bildtypen ab, die erste Szene sollte stark und einfach sein (symbol, zahl oder satz)."""


# ---------------------------------------------------------------- Ersatz-Skripte (ohne KI-Schlüssel / Demo)

ERSATZ = [
    {"id": "zeit-schlaegt-summe",
     "titel_de": ["Warum 100 € mit 25 mehr sind als 200 € mit 35", "Zeit schlägt Summe ⏳", "Der unfairste Trick der Mathematik"],
     "titel_en": ["Why $100 at 25 beats $200 at 35", "Time beats money ⏳", "The most unfair trick in math"],
     "tags_de": ["geld", "zinseszins", "finanzen", "mindset", "investieren", "fyp"],
     "tags_en": ["money", "compoundinterest", "personalfinance", "mindset", "investing", "fyp"],
     "frage_kurz_de": "Wann hast du angefangen?", "frage_kurz_en": "When did you start?",
     "frage_lang_de": "Wann hast du angefangen, Geld anzulegen? Oder wartest du noch auf den richtigen Moment?",
     "frage_lang_en": "When did you start investing? Or are you still waiting for the right moment?",
     "szenen": [
         {"text_de": "Wer mit 25 anfängt, 100 Euro im Monat anzulegen, hat am Ende oft mehr als jemand, der mit 35 "
                     "doppelt so viel zurücklegt. Klingt unfair? Ist Mathematik.",
          "text_en": "Someone who starts investing 100 dollars a month at 25 often ends up with more than someone who "
                     "puts away twice as much starting at 35. Sounds unfair? It's just math.",
          "bild": {"typ": "vergleich", "links": {"icon": "person", "label_de": "Start mit 25", "label_en": "Start at 25",
                                                 "wert_de": "100 €", "wert_en": "$100"},
                   "rechts": {"icon": "person", "label_de": "Start mit 35", "label_en": "Start at 35",
                              "wert_de": "200 €", "wert_en": "$200"}}},
         {"text_de": "Der Grund heißt Zinseszins. Deine Erträge bringen selbst wieder Erträge. Am Anfang passiert kaum "
                     "etwas. Und dann, plötzlich, sehr viel.",
          "text_en": "The reason is compound interest. Your returns start earning returns of their own. At first, almost "
                     "nothing happens. And then, suddenly, a lot.",
          "bild": {"typ": "kurve", "kurven": [{"form": "linear", "label_de": "Eingezahlt", "label_en": "Paid in"},
                                             {"form": "exponentiell", "label_de": "Vermögen", "label_en": "Wealth"}],
                   "y_de": "Vermögen", "y_en": "Wealth", "x_de": "Zeit", "x_en": "Time"}},
         {"text_de": "Ein Beispiel, angenommen sieben Prozent pro Jahr bis zum Alter von 65. Person eins zahlt insgesamt "
                     "48.000 Euro ein. Am Ende stehen rund 262.000 Euro.",
          "text_en": "An example, assuming seven percent a year until age 65. Person one pays in 48,000 dollars in total. "
                     "At the end: about 262,000 dollars.",
          "bild": {"typ": "zahl", "wert_de": "≈ 262.000 €", "wert_en": "≈ $262,000",
                   "label_de": "Start mit 25 · 48.000 € eingezahlt", "label_en": "Start at 25 · $48,000 paid in"}},
         {"text_de": "Person zwei zahlt 72.000 Euro ein. Also deutlich mehr. Und landet trotzdem nur bei rund 244.000.",
          "text_en": "Person two pays in 72,000 dollars. Much more. And still ends up with only about 244,000.",
          "bild": {"typ": "zahl", "wert_de": "≈ 244.000 €", "wert_en": "≈ $244,000",
                   "label_de": "Start mit 35 · 72.000 € eingezahlt", "label_en": "Start at 35 · $72,000 paid in"}},
         {"text_de": "Der größte Hebel ist also nicht die Summe. Es ist die Zeit. Und Zeit kann man nicht nachkaufen.",
          "text_en": "So the biggest lever isn't the amount. It's time. And time is the one thing you can't buy back.",
          "bild": {"typ": "symbol", "icon": "sanduhr", "label_de": "Der wahre Hebel", "label_en": "The real lever",
                   "wert_de": "Zeit", "wert_en": "Time", "gold": True}},
         {"text_de": "Wie heißt es so schön: Der beste Zeitpunkt zum Anfangen war gestern. Der zweitbeste ist heute.",
          "text_en": "As the saying goes: the best time to start was yesterday. The second best time is today.",
          "bild": {"typ": "satz", "text_de": "Der beste Zeitpunkt war gestern. Der zweitbeste ist heute.",
                   "text_en": "The best time was yesterday. The second best is today."}},
     ]},
    {"id": "lifestyle-inflation",
     "titel_de": ["Warum mehr Gehalt dich nicht reicher macht", "Die Gehaltsfalle 💸", "Wo deine Gehaltserhöhung wirklich hingeht"],
     "titel_en": ["Why a raise doesn't make you richer", "The salary trap 💸", "Where your raise really goes"],
     "tags_de": ["geld", "gehalt", "sparen", "mindset", "finanzen", "fyp"],
     "tags_en": ["money", "salary", "saving", "mindset", "personalfinance", "fyp"],
     "frage_kurz_de": "Wo ging deine letzte Erhöhung hin?", "frage_kurz_en": "Where did your last raise go?",
     "frage_lang_de": "Was ist mit deiner letzten Gehaltserhöhung passiert? Ehrlich.",
     "frage_lang_en": "What happened to your last raise? Be honest.",
     "szenen": [
         {"text_de": "Du verdienst heute mehr als vor fünf Jahren. Aber hast du auch mehr übrig? Bei den meisten lautet "
                     "die ehrliche Antwort: nein.",
          "text_en": "You earn more today than you did five years ago. But do you actually have more left over? For most "
                     "people, the honest answer is no.",
          "bild": {"typ": "symbol", "icon": "geldschein", "label_de": "Mehr Gehalt", "label_en": "More income",
                   "wert_de": "Mehr übrig?", "wert_en": "More left?"}},
         {"text_de": "Das nennt man Lifestyle-Inflation. Mit jedem Gehaltssprung wachsen die Ausgaben einfach mit. "
                     "Die Linien laufen nebeneinander her.",
          "text_en": "It's called lifestyle inflation. Every time your income goes up, your spending quietly follows. "
                     "The two lines just move together.",
          "bild": {"typ": "kurve", "kurven": [{"form": "linear", "label_de": "Einkommen", "label_en": "Income"},
                                             {"form": "zickzack", "label_de": "Ausgaben", "label_en": "Spending"}],
                   "y_de": "Euro", "y_en": "Dollars", "x_de": "Jahre", "x_en": "Years"}},
         {"text_de": "Eine größere Wohnung. Ein neueres Auto. Ein paar Abos mehr. Jede Entscheidung fühlt sich klein und "
                     "verdient an. Zusammen fressen sie fast jede Erhöhung auf.",
          "text_en": "A bigger apartment. A newer car. A few more subscriptions. Each choice feels small and deserved. "
                     "Together, they eat almost every raise.",
          "bild": {"typ": "liste", "punkte": [{"icon": "haus", "de": "Größere Wohnung", "en": "Bigger apartment"},
                                             {"icon": "auto", "de": "Neueres Auto", "en": "Newer car"},
                                             {"icon": "handy", "de": "Mehr Abos", "en": "More subscriptions"}]}},
         {"text_de": "Ein einfacher Gegentrick: Leg dir eine feste Regel fest. Zum Beispiel: Die Hälfte jeder "
                     "Gehaltserhöhung geht automatisch aufs Sparkonto oder in die Geldanlage.",
          "text_en": "One simple counter move: set a fixed rule. For example, half of every raise goes straight into "
                     "savings or investments, automatically.",
          "bild": {"typ": "zahl", "wert_de": "50 %", "wert_en": "50%", "label_de": "Jeder Gehaltserhöhung",
                   "label_en": "Of every raise"}},
         {"text_de": "So lebst du trotzdem jedes Jahr ein bisschen besser. Und dein Vermögen wächst endlich mit deinem "
                     "Einkommen mit.",
          "text_en": "You still get to live a little better every year. And your wealth finally grows along with your "
                     "income.",
          "bild": {"typ": "vergleich", "links": {"icon": "kaffee", "label_de": "Genießen", "label_en": "Enjoy",
                                                 "wert_de": "50 %", "wert_en": "50%"},
                   "rechts": {"icon": "pflanze", "label_de": "Anlegen", "label_en": "Invest",
                              "wert_de": "50 %", "wert_en": "50%"}}},
         {"text_de": "Denn Wohlstand entsteht nicht durch das, was reinkommt. Sondern durch das, was übrig bleibt.",
          "text_en": "Because wealth isn't built by what comes in. It's built by what stays.",
          "bild": {"typ": "satz", "text_de": "Wohlstand ist, was übrig bleibt.", "text_en": "Wealth is what stays."}},
     ]},
    {"id": "72er-regel",
     "titel_de": ["Die 72er-Regel in 60 Sekunden", "Wie schnell verdoppelt sich dein Geld?", "Diese Zahl solltest du kennen: 72"],
     "titel_en": ["The rule of 72 in 60 seconds", "How fast does your money double?", "The number you should know: 72"],
     "tags_de": ["geld", "finanzen", "zinseszins", "inflation", "mindset", "fyp"],
     "tags_en": ["money", "personalfinance", "ruleof72", "inflation", "mindset", "fyp"],
     "frage_kurz_de": "Kanntest du die Regel?", "frage_kurz_en": "Did you know this rule?",
     "frage_lang_de": "Kanntest du die 72er-Regel schon? Schreib es in die Kommentare.",
     "frage_lang_en": "Did you already know the rule of 72? Let me know in the comments.",
     "szenen": [
         {"text_de": "Es gibt eine Zahl, die dir in drei Sekunden zeigt, wie schnell sich dein Geld verdoppelt. Sie lautet: "
                     "zweiundsiebzig.",
          "text_en": "There's one number that tells you in three seconds how fast your money doubles. That number is "
                     "seventy-two.",
          "bild": {"typ": "zahl", "wert_de": "72", "wert_en": "72", "label_de": "Die wichtigste Zahl",
                   "label_en": "The most important number"}},
         {"text_de": "Die 72er-Regel: Teile 72 durch die jährliche Rendite. Das Ergebnis sind ungefähr die Jahre, bis sich "
                     "dein Geld verdoppelt.",
          "text_en": "The rule of 72: divide 72 by your yearly return. The result is roughly the number of years it takes "
                     "for your money to double.",
          "bild": {"typ": "satz", "text_de": "72 ÷ Rendite = Jahre bis zur Verdopplung",
                   "text_en": "72 ÷ return = years to double"}},
         {"text_de": "Bei einem Prozent Zinsen dauert das 72 Jahre. Angenommen sieben Prozent pro Jahr, sind es nur rund "
                     "zehn Jahre.",
          "text_en": "At one percent interest, that takes 72 years. Assuming seven percent a year, it's only about ten "
                     "years.",
          "bild": {"typ": "vergleich", "links": {"icon": "muenze", "label_de": "1 % Zinsen", "label_en": "1% interest",
                                                 "wert_de": "72 Jahre", "wert_en": "72 years"},
                   "rechts": {"icon": "rakete", "label_de": "7 % Rendite", "label_en": "7% return",
                              "wert_de": "≈ 10 Jahre", "wert_en": "≈ 10 years"}}},
         {"text_de": "Über ein Arbeitsleben von 40 Jahren ist das der Unterschied zwischen nicht einmal einer Verdopplung "
                     "und fast vier Verdopplungen.",
          "text_en": "Over a 40-year career, that's the difference between not even one doubling and almost four.",
          "bild": {"typ": "kurve", "kurven": [{"form": "flach", "label_de": "1 %", "label_en": "1%"},
                                             {"form": "exponentiell", "label_de": "7 %", "label_en": "7%"}],
                   "y_de": "Vermögen", "y_en": "Wealth", "x_de": "40 Jahre", "x_en": "40 years"}},
         {"text_de": "Und die Regel funktioniert auch andersherum. Bei drei Prozent Inflation halbiert sich die Kaufkraft "
                     "deines Ersparten in etwa 24 Jahren.",
          "text_en": "And it works the other way, too. With three percent inflation, the buying power of your savings is "
                     "cut in half in about 24 years.",
          "bild": {"typ": "symbol", "icon": "prozent", "label_de": "3 % Inflation", "label_en": "3% inflation",
                   "wert_de": "÷ 2 in 24 Jahren", "wert_en": "÷ 2 in 24 years", "gold": True}},
         {"text_de": "Geld, das einfach nur liegt, wird also jedes Jahr ein bisschen weniger wert. Leise, aber sicher.",
          "text_en": "So money that just sits there loses a little value every single year. Quietly, but surely.",
          "bild": {"typ": "satz", "text_de": "Geld, das nur liegt, verliert leise an Wert.",
                   "text_en": "Idle money quietly loses value."}},
     ]},
]


# ---------------------------------------------------------------- Skript holen

def ki_skript(bisher):
    import ki_text
    idee = random.Random(str(date.today())).choice([i for i in THEMEN_IDEEN if i not in bisher] or THEMEN_IDEEN)
    nutzer = (f"Schreib die heutige Folge. Themenvorschlag: {idee}. Du darfst ein verwandtes Thema wählen, wenn es "
              f"stärker ist. Diese Themen gab es schon (nicht wiederholen): {', '.join(list(bisher)[-40:]) or 'keine'}.")
    return ki_text.json_anfrage(SYSTEM, nutzer, max_tokens=5000)


def pruefen(sk):
    """Repariert kleine Fehler im KI-Skript (unbekannte Symbole, fehlende Felder)."""
    szenen = [s for s in sk.get("szenen", []) if s.get("text_de") and s.get("text_en")][:8]
    if len(szenen) < 4:
        raise ValueError("zu wenige Szenen")
    for s in szenen:
        b = s.setdefault("bild", {"typ": "satz", "text_de": "", "text_en": ""})
        if b.get("typ") not in TYPEN:
            b.update(typ="satz")
        for teil in [b, b.get("links") or {}, b.get("rechts") or {}] + list(b.get("punkte") or []):
            if "icon" in teil and teil["icon"] not in linien.SYMBOLE:
                teil["icon"] = "muenze"
        for k in b.get("kurven") or []:
            if k.get("form") not in FORMEN:
                k["form"] = "exponentiell"
    sk["szenen"] = szenen
    for f in ("titel_de", "titel_en", "tags_de", "tags_en"):
        sk.setdefault(f, [])
    return sk


def sprachfassung(obj, lang):
    """Wählt aus *_de / *_en die passende Sprache (auch verschachtelt)."""
    if isinstance(obj, list):
        return [sprachfassung(x, lang) for x in obj]
    if not isinstance(obj, dict):
        return obj
    out = {}
    for k, v in obj.items():
        if k.endswith("_de") or k.endswith("_en"):
            if k.endswith("_" + lang):
                out[k[:-3]] = sprachfassung(v, lang)
        elif k in ("de", "en"):
            if k == lang:
                out["text"] = v
        else:
            out[k] = sprachfassung(v, lang)
    return out


def video_plan(erledigt, tag_nr, sprachen=("de", "en"), demo=False):
    bisher = [e.split("@")[0] for e in erledigt]
    sk = None
    if not demo:
        import ki_text
        if ki_text.schluessel():
            try:
                sk = pruefen(ki_skript(bisher))
                print(f"  KI-Skript: {sk.get('id')}")
            except Exception as e:
                print(f"  KI-Text fehlgeschlagen ({str(e)[:100]}) -> Ersatz-Skript.")
        else:
            print("  Kein ANTHROPIC_API_KEY -> Ersatz-Skript.")
    if not sk:
        frei = [s for s in ERSATZ if s["id"] not in bisher] or ERSATZ
        sk = frei[date.today().toordinal() % len(frei)] if not demo else ERSATZ[0]
    plan = {"id": f"{sk.get('id', 'folge')}@{date.today().isoformat()}", "name": (sk.get("titel_de") or ["Mindset"])[0],
            "sprachen": {}}
    for lang in sprachen:
        szenen = []
        for s in sk["szenen"]:
            b = sprachfassung(s["bild"], lang)
            if b.get("typ") == "liste":
                b["punkte"] = [{"icon": p.get("icon"), "text": p.get("text", "")} for p in b.get("punkte", [])]
            szenen.append({"name": b.get("typ", "satz"), "text": s["text_" + lang], "daten": b})
        morgen = ""
        if tag_nr:
            morgen = f" Morgen kommt Tag {tag_nr + 1}." if lang == "de" else f" Tomorrow is day {tag_nr + 1}."
        outro = (f"Keine Finanzberatung, nur ein Denkanstoß.{morgen} Und jetzt du: {sk['frage_lang_de']}" if lang == "de"
                 else f"Not financial advice, just food for thought.{morgen} Now over to you: {sk['frage_lang_en']}")
        szenen.append({"name": "frage", "text": outro, "daten": {
            "frage": sk["frage_kurz_" + lang], "hinweis": DISCLAIMER[lang],
            "cta": (f"Morgen: Tag {tag_nr + 1}" if lang == "de" else f"Tomorrow: day {tag_nr + 1}") if tag_nr else ""}})
        plan["sprachen"][lang] = {"szenen": szenen, "titel": sk.get("titel_" + lang) or [plan["name"]],
                                  "tags": [t.lstrip("#").lower().replace(" ", "") for t in sk.get("tags_" + lang, [])][:8],
                                  "frage": sk["frage_kurz_" + lang]}
    return plan
